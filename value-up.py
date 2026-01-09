import streamlit as st
import pandas as pd

import numpy as np

import plotly.graph_objects as go

import plotly.express as px

from plotly.subplots import make_subplots
import time
import os

import json

import glob
import datetime

from api.opendart_client import OpenDartClient

from api.market_data import get_market_metrics, get_krx_listing, get_stock_history

from api.company_guide import get_batch_company_data

from api.naver_news import fetch_naver_news_search

from utils.security import save_credentials, load_credentials, verify_pin, check_credentials_exist, load_from_env

from utils.logger import log_transition

from utils.state_manager import save_state, load_state

import atexit


# Register exit handler for state saving

atexit.register(save_state)


# --- [Global Constants] ---

# GLOBAL_API_KEY Removed for security management via Sidebar



# --- [Configuration] 페이지 설정 ---
st.set_page_config(
    page_title="Value-Up Finder (2601.02)",
    page_icon="📈",
    layout="wide",

    initial_sidebar_state="expanded"
)



# --- [Caching Layer] JSON File Management ---

# --- [Caching Layer] JSON File Management ---

CACHE_DIR = "data"
FAVORITES_FILE = os.path.join(CACHE_DIR, "favorites.json")

def load_favorites_from_disk():
    if not os.path.exists(FAVORITES_FILE):
        return {"analysis": [], "trend": []}
    try:
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading favorites: {e}")
        return {"analysis": [], "trend": []}

def save_favorites_to_disk(analysis_favs, trend_favs):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        data = {
            "analysis": analysis_favs,
            "trend": trend_favs
        }
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving favorites: {e}")


def get_valid_cache():
    """

    매일 16:00 기준으로 유효한 캐시 파일이 있는지 확인하고 로드합니다.

    파일명 형식: company_data_YYYYMMDD_HHMMSS.json
    """

    if not os.path.exists(CACHE_DIR):

        os.makedirs(CACHE_DIR, exist_ok=True)

        return None


    # 기준 시간 설정 (매일 16:00)

    now = datetime.datetime.now()

    cutoff_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
    

    # 현재 시간이 16:00 이전이면, 어제 16:00가 기준

    if now < cutoff_time:

        cutoff_time = cutoff_time - datetime.timedelta(days=1)
        

    # 캐시 파일 검색

    files = glob.glob(os.path.join(CACHE_DIR, "company_data_*.json"))

    if not files:

        return None
        

    # 최신 파일 찾기

    latest_file = max(files, key=os.path.getctime)
    

    # 파일명에서 시간 파싱 (company_data_20241220_160500.json)

    try:

        filename = os.path.basename(latest_file)

        time_str = filename.replace("company_data_", "").replace(".json", "")

        file_time = datetime.datetime.strptime(time_str, "%Y%m%d_%H%M%S")
        

        # 유효성 검사 (기준 시간 이후 생성된 파일인가?)

        if file_time >= cutoff_time:

            with open(latest_file, 'r', encoding='utf-8') as f:

                data = json.load(f)

                # st.toast removed to prevent CacheReplayClosureError

                print(f"Loaded cache from {filename}")

                return pd.DataFrame(data)

    except Exception as e:

        print(f"Cache Load Error: {e}")

        return None
        

    return None


def save_daily_cache(df):
    """

    데이터프레임을 JSON 형식으로 저장합니다. (파일명: company_data_YYYYMMDD_HHMMSS.json)
    """

    if df.empty: return
    

    if not os.path.exists(CACHE_DIR):

        os.makedirs(CACHE_DIR, exist_ok=True)
        

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    filepath = os.path.join(CACHE_DIR, f"company_data_{now_str}.json")
    

    try:

        # DataFrame -> Dict

        data = df.to_dict('records')

        with open(filepath, 'w', encoding='utf-8') as f:

            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"Cache Saved: {filepath}")

    except Exception as e:

        print(f"Cache Save Error: {e}")



# --- [Data Layer] Hybrid Data Generation (FinanceDataReader) ---

@st.cache_data(ttl=3600)  # Re-enabled for Legacy Mode (CompanyGuide)

def fetch_real_dashboard_data(api_key=None):
    """

    FinanceDataReader(fdr)와 FnGuide 크롤링을 사용하여 시가총액 상위 300개 종목의 주요 지표를 수집합니다.

    (Company Guide 크롤링 적용 - 배당수익률 포함 풍부한 데이터)
    """

    # 0. Daily Cache Check (JSON) - 매일 16:00 기준 유효한 파일이 있으면 즉시 반환

    cached_df = get_valid_cache()

    if cached_df is not None:

        return cached_df


    # 1. KRX 상장 리스트 가져오기

    df_krx = get_krx_listing()

    if df_krx.empty:

        return pd.DataFrame()
    

    # 2. 시가총액 상위 300개 (확장)

    # 2. 시가총액 상위 (KOSPI 200 + KOSDAQ 100)
    df_kospi = df_krx[df_krx['Market'].str.contains('KOSPI')].sort_values(by='Marcap', ascending=False).head(200)
    df_kosdaq = df_krx[df_krx['Market'].str.contains('KOSDAQ')].sort_values(by='Marcap', ascending=False).head(100)
    top_n = pd.concat([df_kospi, df_kosdaq])

    target_codes = top_n['Code'].tolist()
    

    # 3. 데이터 수집

    final_data = []


    if not api_key:

        # API Key 없으면 KRX 기본 정보만 리턴

        for idx, row in top_n.iterrows():

            final_data.append({

                "종목명": row['Name'],

                "종목코드": row['Code'],

                "시장": row['Market'],  # [Added] Market

                "업종": row.get('Sector', '미분류'),

                "시가총액(억)": round(row['Marcap'] / 100000000),

                "PBR(배)": 0, "PER(배)": 0, "배당수익률(%)": 0, "ROE(%)": 0,

                "종합점수": 0

            })

        return pd.DataFrame(final_data)


    # [CompanyGuide Crawling]

    if not target_codes:

        return pd.DataFrame()


    with st.spinner("CompanyGuide에서 300개 기업 데이터 수집 중... (약 120~300초 소요, 매일 16:00 업데이트)"):

        df_guide = get_batch_company_data(target_codes)
        

    if df_guide.empty:

        # Fail-Safe: If CompanyGuide fails, fall back to basic KRX data

        # Initialize final_data with basic KRX info if it's empty

        if not final_data: 

             for idx, row in top_n.iterrows():

                final_data.append({

                        "종목명": row['Name'],

                        "종목코드": row['Code'],

                        "시장": row['Market'],

                        "업종": row.get('Sector', '미분류'),

                        "시가총액(억)": round(row['Marcap'] / 100000000),

                        "PBR(배)": 0, "배당수익률(%)": 0, "ROE(%)": 0,

                        "종합점수": 0, "이익잉여금비율(%)": 0, "현금비중(%)": 0, "PER(배)": 0

                })

        result_df = pd.DataFrame(final_data).sort_values(by="종합점수", ascending=False)

        # Don't cache empty fail-safe results to avoid persisting bad state
        return result_df


    # 3. Merge

    guide_map = df_guide.set_index('code').to_dict('index')

    final_data = []
    

    for idx, row in top_n.iterrows():

        code = row['Code']

        g_data = guide_map.get(code, {})
        

        pbr = g_data.get('pbr', 0) or 0

        div = g_data.get('dividend_yield', 0) or 0

        roe = g_data.get('roe', 0) or 0
        

        ret_rate = g_data.get('retained_rate', 0)

        cash_rate = g_data.get('cash_ratio', 0)
        

        # Score Logic

        score = ((3 - min(pbr, 3)) * 30) + (div * 5) + (roe * 1.5)
        

        final_data.append({

            "종목명": row['Name'],

            "종목코드": code,

            "시장": row['Market'], # [Added] Market

            "업종": row.get('Sector', '미분류'),

            "시가총액(억)": round(row['Marcap'] / 100000000),

            "PBR(배)": round(pbr, 2),

            "PER(배)": round(g_data.get('per', 0) or 0, 2),

            "배당수익률(%)": round(div, 2), 

            "ROE(%)": round(roe, 1),

            "종합점수": round(score, 1),

            "이익잉여금비율(%)": float(ret_rate), 

            "현금비중(%)": float(cash_rate)

        })
        

    result_df = pd.DataFrame(final_data).sort_values(by="종합점수", ascending=False)
    

    # [Save Daily Cache]

    if not result_df.empty:

        save_daily_cache(result_df)
        
    return result_df




# --- [Logic Layer] Real Data Integration ---

def fetch_real_company_data(corp_code, api_key, base_year=2024):
    """

    실제 OpenDart API와 FinanceDataReader를 연동하여 데이터를 가져옵니다.

    base_year: 분석 기준 연도
    """

    if not api_key:

        return None, "API Key가 설정되지 않았습니다."


    with st.spinner(f"'{corp_code}' 데이터 분석 중... (OpenDart + KRX)"):

        # 1. Market Data (Price, Market Cap)

        market_info = get_market_metrics(corp_code)

        if not market_info:

            return None, f"시장 데이터를 찾을 수 없습니다. (Code: {corp_code})"
        

        # 2. Financial Data (OpenDart)

        client = OpenDartClient(api_key)

        if client.init_error:

            return None, f"OpenDart 초기화 실패: {client.init_error} (API Key 확인 필요)"
            

        # 선택된 사업보고서 기준

        financials = client.get_financial_summary(corp_code, base_year)
        

        if not financials:

            return None, f"{base_year}년도 OpenDart 재무 데이터를 찾을 수 없습니다. (API Key 확인 또는 공시 누락)"


        # 3. Combine & Calculate Metrics
        

        # 데이터 추출 (List: [Current, Prev, PrevPrev])

        assets_list = financials.get('자산총계', [0, 0, 0])

        equity_list = financials.get('자본총계', [0, 0, 0])

        liabilities_list = financials.get('부채총계', [0, 0, 0])

        retained_list = financials.get('이익잉여금', [0, 0, 0])

        cash_list = financials.get('현금성자산', [0, 0, 0])

        short_fin_list = financials.get('단기금융상품', [0, 0, 0])

        net_income_list = financials.get('당기순이익', [0, 0, 0])

        current_assets_list = financials.get('유동자산', [0, 0, 0])
        

        market_cap = market_info['Marcap'] # 현재 시가총액 (원)


        # 단위 보정 (억 원)

        def to_100m(val): return round(val / 100000000)


        metrics_years = []

        years = [base_year, base_year-1, base_year-2] # [Year, Year-1, Year-2]


        for i in range(3):

            eq = equity_list[i]

            ret = retained_list[i]

            # 현금성자산 + 단기금융상품

            cash_plus_short = cash_list[i] + short_fin_list[i]

            net_income = net_income_list[i]

            cur_asset = current_assets_list[i]
            

            # 1) 이익잉여금 비율

            retained_rate = (ret / eq) * 100 if eq > 0 else 0
            

        # 2) 현금비중 (수정됨: (현금+단기금융) / 유동자산 * 100)

            # 유동자산이 0이면 0 처리

            cash_ratio = (cash_plus_short / cur_asset) * 100 if cur_asset > 0 else 0
            

            # ROE

            roe_val = (net_income / eq) * 100 if eq > 0 else 0
            

            metrics_years.append({

                "year": years[i],

                "assets": to_100m(assets_list[i]),

                "equity": to_100m(equity_list[i]),

                "liabilities": to_100m(liabilities_list[i]),

                "retained": to_100m(ret),

                "cash_equivalents": to_100m(cash_plus_short), # 현금+금융상품

                "current_assets": to_100m(cur_asset),

                "net_income": to_100m(net_income),

                "retained_rate": round(retained_rate, 1),

                "cash_ratio": round(cash_ratio, 1),

                "roe": round(roe_val, 1)

            })


        # 현재 기준 주요 지표 (KPI)

        current_metrics = metrics_years[0]
        

        # PBR

        current_equity = equity_list[0]

        pbr = market_cap / current_equity if current_equity > 0 else 0
        

        # 주주 현황

        shareholders = client.get_major_shareholders(corp_code)
        

        return {

            "meta": {"name": market_info['Name'], "code": corp_code},

            "metrics": {

                "retained_rate": current_metrics['retained_rate'],

                "cash_ratio": current_metrics['cash_ratio'], 

                "pbr": round(pbr, 2),

                "roe": current_metrics['roe']

            },

            "history": metrics_years, # 3년치 재무 데이터

            "market_cap": to_100m(market_cap),

            "shareholders": shareholders

        }, None




# --- [View Layer] UI Components ---


def render_dashboard(api_key):

    st.header("🚀 저평가 우량주 발굴 (Top 300)"
)
    st.caption("시가총액 상위 300개 기업 중 PBR, 현금흐름, 주주환원 등을 종합적으로 분석하여 점수를 산출합니다.")
    

    # 데이터 로드

    df_result = fetch_real_dashboard_data(api_key)
    

    if df_result.empty:

        st.warning("데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
        return


    # --- SideBar Filters (Matching Request) ---

    # --- SideBar Filters (Matching Request) ---

    with st.sidebar:

        # [State Initialization - Moved to Top]

        # 1. Retained Earnings (Default 80)

        if "num_ret" not in st.session_state: st.session_state["num_ret"] = 80.0

        if "slide_ret" not in st.session_state: st.session_state["slide_ret"] = 80.0

        # 2. Cash Ratio (Default 10)

        if "num_cash" not in st.session_state: st.session_state["num_cash"] = 10.0

        if "slide_cash" not in st.session_state: st.session_state["slide_cash"] = 10.0

        # 3. PBR (Default 3.0)

        if "num_pbr" not in st.session_state: st.session_state["num_pbr"] = 3.0

        if "slide_pbr" not in st.session_state: st.session_state["slide_pbr"] = 3.0

        # 4. Dividend (Default 1.0)

        if "num_div" not in st.session_state: st.session_state["num_div"] = 1.0

        if "slide_div" not in st.session_state: st.session_state["slide_div"] = 1.0

        # 5. PER (Default 20.0) [New]

        if "num_per" not in st.session_state: st.session_state["num_per"] = 20.0

        if "slide_per" not in st.session_state: st.session_state["slide_per"] = 20.0


        # Initialize 'Applied' states

        if "applied_ret" not in st.session_state: st.session_state["applied_ret"] = 80.0

        if "applied_cash" not in st.session_state: st.session_state["applied_cash"] = 10.0

        if "applied_pbr" not in st.session_state: st.session_state["applied_pbr"] = 3.0

        if "applied_div" not in st.session_state: st.session_state["applied_div"] = 1.0

        if "applied_per" not in st.session_state: st.session_state["applied_per"] = 20.0


        # [Layout: Header + Apply Button]

        c_head, c_btn = st.columns([2, 1])

        with c_head:

            st.subheader("스크리닝 조건 설정")

        with c_btn:

             btn_apply = st.button("적용")


        # [Market Filter]

        market_options = ['KOSPI', 'KOSDAQ']

        if "selected_markets" not in st.session_state: 

            st.session_state["selected_markets"] = market_options
            

        selected_markets = st.multiselect("시장 선택", market_options, default=market_options, key="select_market_widget")

        # Sync widget to state immediately or on Apply?

        # Usually Multiselect is instant, but users might expect "Apply" to cover it.

        # Let's make it Instant for usability, or bind to session state.

        # If I bind `key`, it updates `st.session_state.select_market_widget` automatically.
        

        # [Apply Logic]

        if btn_apply:

            st.session_state["applied_ret"] = st.session_state["num_ret"]

            st.session_state["applied_cash"] = st.session_state["num_cash"]

            st.session_state["applied_pbr"] = st.session_state["num_pbr"]

            st.session_state["applied_div"] = st.session_state["num_div"]

            st.session_state["applied_per"] = st.session_state["num_per"]

            st.session_state["applied_markets"] = selected_markets # Store applied markets

            st.success("조건이 적용되었습니다!")
            

        if "applied_markets" not in st.session_state:

            st.session_state["applied_markets"] = market_options


        # Helper function for syncing

        def update_slider(key_slider, key_input):

            st.session_state[key_slider] = st.session_state[key_input]
            

        def update_input(key_input, key_slider):

            st.session_state[key_input] = st.session_state[key_slider]


        # 1. Retained Earnings

        c1_1, c1_2 = st.columns([2, 1])

        with c1_2:

            st.number_input("입력 (%)", min_value=0.0, max_value=300.0, step=10.0, key="num_ret", on_change=update_slider, args=("slide_ret", "num_ret"))

        with c1_1:

            st.slider("이익잉여금 비율", 0.0, 300.0, key="slide_ret", on_change=update_input, args=("num_ret", "slide_ret"), help="자본총계 대비 이익잉여금 비율")
        

        # 2. Cash Ratio

        c2_1, c2_2 = st.columns([2, 1])

        with c2_2:

            st.number_input("입력 (%)", min_value=0.0, max_value=100.0, step=1.0, key="num_cash", on_change=update_slider, args=("slide_cash", "num_cash"))

        with c2_1:

            st.slider("현금성자산 비중", 0.0, 100.0, key="slide_cash", on_change=update_input, args=("num_cash", "slide_cash"), help="유동자산 대비 현금성자산 비율")


        # 3. PBR

        c3_1, c3_2 = st.columns([2, 1])

        with c3_2:

            st.number_input("입력 (배)", min_value=0.1, max_value=20.0, step=0.1, key="num_pbr", on_change=update_slider, args=("slide_pbr", "num_pbr"))

        with c3_1:

            st.slider("PBR (배) 이하", 0.1, 20.0, key="slide_pbr", on_change=update_input, args=("num_pbr", "slide_pbr"))
        

        # 4. PER [New]

        c5_1, c5_2 = st.columns([2, 1])

        with c5_2:

            st.number_input("입력 (배)", min_value=1.0, max_value=100.0, step=1.0, key="num_per", on_change=update_slider, args=("slide_per", "num_per"))

        with c5_1:

            st.slider("PER (배) 이하", 1.0, 100.0, key="slide_per", on_change=update_input, args=("num_per", "slide_per"), help="주가수익비율")


        # 5. Dividend

        c4_1, c4_2 = st.columns([2, 1])

        with c4_2:

            st.number_input("입력 (%)", min_value=0.0, max_value=10.0, step=0.1, key="num_div", on_change=update_slider, args=("slide_div", "num_div"))

        with c4_1:

            st.slider("배당수익률", 0.0, 10.0, key="slide_div", on_change=update_input, args=("num_div", "slide_div"))
            

    # --- Filtering Logic (Applied Only) ---

    filtered_df = df_result.copy()


    # Retrieve applied filter values

    app_pbr = st.session_state["applied_pbr"]

    app_ret = st.session_state["applied_ret"]

    app_cash = st.session_state["applied_cash"]

    app_div = st.session_state["applied_div"]

    app_per = st.session_state["applied_per"]

    app_markets = st.session_state.get("applied_markets", ['KOSPI', 'KOSDAQ'])


    # 0. Market Filter

    if '시장' in filtered_df.columns:

        filtered_df = filtered_df[filtered_df['시장'].isin(app_markets)]


    # 1. PBR Filter

    filtered_df = filtered_df[filtered_df['PBR(배)'] <= app_pbr]


    # 2. PER Filter [New]

    if 'PER(배)' in filtered_df.columns:

         filtered_df = filtered_df[filtered_df['PER(배)'] <= app_per]


    # 3. Advanced Filters (Retained Earnings, Cash Ratio)

    # Check if columns exist (safety)

    if '이익잉여금비율(%)' in filtered_df.columns:

        filtered_df = filtered_df[filtered_df['이익잉여금비율(%)'] >= app_ret]
    

    if '현금비중(%)' in filtered_df.columns:

         filtered_df = filtered_df[filtered_df['현금비중(%)'] >= app_cash]


    # 3. Dividend Filter (with Graceful Handling)

    # If all items have 0 dividend (missing data), getting filtered out is bad UX.

    max_div = filtered_df['배당수익률(%)'].max() if not filtered_df.empty else 0
    

    if max_div == 0 and app_div > 0:

        st.warning("⚠️ 배당 데이터가 수집되지 않아 배당수익률 필터가 해제되었습니다. (API 제한 또는 데이터 부재)")

        # Do NOT apply dividend filter

    else:

        filtered_df = filtered_df[filtered_df['배당수익률(%)'] >= app_div]

    

    # --- Top Metrics ---

    # 검색된 기업, 평균 PBR, 평균 배당수익률, 평균 종합점수
    

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("검색된 기업", f"{len(filtered_df)}개", f"전체 {len(df_result)}종목 중")
    

    avg_pbr = filtered_df['PBR(배)'].mean() if not filtered_df.empty else 0

    m2.metric("평균 PBR", f"{avg_pbr:.2f}배")
    

    avg_div = filtered_df['배당수익률(%)'].mean() if not filtered_df.empty else 0

    m3.metric("평균 배당수익률", f"{avg_div:.1f}%")


    avg_score = filtered_df['종합점수'].mean() if not filtered_df.empty else 0

    m4.metric("평균 종합점수", f"{avg_score:.1f}점")


    st.divider()


    # --- Main Table ---

    st.subheader("📋 발굴 기업 목록")
    

    if filtered_df.empty and not df_result.empty:

        st.error("⚠️ 검색 조건에 맞는 기업이 없습니다. (필터 조건이 너무 엄격하거나 데이터 수집 실패)")

        st.markdown("**[DEBUG] Raw Data Check (상위 5개)**")

        st.dataframe(df_result.head(5), hide_index=True) # Validates if data exists at all

    else:

        # Columns to show: Name, Code, Sector, PBR, Div, ROE, Cap, Score, RetainedRate, CashRate

        # Remove: Major Shareholder (as requested)
        

        display_cols = [

            "종목명", "종목코드", "업종", "PBR(배)", "PER(배)", "배당수익률(%)", "ROE(%)", 

            "시가총액(억)", "종합점수", "이익잉여금비율(%)", "현금비중(%)"

        ]
        

        # Check if cols exist (safety)

        final_cols = [c for c in display_cols if c in filtered_df.columns]
        
        st.dataframe(

            filtered_df[final_cols].style.background_gradient(subset=['종합점수'], cmap='Blues'),

            use_container_width=True,

            height=400,

            hide_index=True
        )
    

    st.divider()
    

    # --- Detailed Analysis Section (Bottom) ---

    st.subheader("📊 상세 분석")
    

    # 1. Select Company

    if filtered_df.empty:

        st.info("검색된 기업이 없습니다.")

    else:

        # Create list for dropdown: "Name (Code)"

        options = filtered_df.apply(lambda x: f"{x['종목명']} ({x['종목코드']})", axis=1).tolist()

        selected_option = st.selectbox("분석할 기업 선택", options)
        

        if selected_option:

            # Parse Code

            selected_code = selected_option.split('(')[-1].replace(')', '')

            selected_name = selected_option.split(' (')[0]
            

            # Draw Tabs: Comprehensive Diagnosis, Related News

            # Draw Tabs: Comprehensive Diagnosis, OpenDart, News, Research
            d_tab1, d_tab2, d_tab3, d_tab4 = st.tabs(["종합 진단", "전자공시", "뉴스", "리서치"])
            

            with d_tab1:

                # Reuse data from 'filtered_df' for this company to show Radar or basic info logic

                # For full analysis, we might usually call 'fetch_real_company_data' (OpenDart) 

                # but to be fast, let's show what we have + a button to "Go into Deep Dive".
                

                # Fetch row

                row_data = filtered_df[filtered_df['종목코드'] == selected_code].iloc[0]
                

                # Radar Chart Data

                # PBR (Inverse for score), Div, ROE, Retained, Cash

                # Normalize roughly for visibility: 

                # PBR: Lower is better. Score = (3-PBR)/3 * 100.

                # Div: 5% = 100.

                # ROE: 15% = 100.


                # Retained: 1000% = 100.

                # Cash: 50% = 100.
                

                r_pbr = max(0, min(100, (3 - row_data.get('PBR(배)',0))/3 * 100 ))

                r_div = max(0, min(100, row_data.get('배당수익률(%)',0) * 20))

                r_roe = max(0, min(100, row_data.get('ROE(%)',0) * 6.6))

                r_ret = max(0, min(100, row_data.get('이익잉여금비율(%)',0) / 10))

                r_cash = max(0, min(100, row_data.get('현금비중(%)',0) * 2))
                

                categories = ['저평가(PBR)', '배당수익률', 'ROE', '이익잉여금', '현금여력']

                values = [r_pbr, r_div, r_roe, r_ret, r_cash]
                

                fig_radar = go.Figure(data=go.Scatterpolar(

                    r=values,

                    theta=categories,

                    fill='toself',

                    name=selected_name
                ))

                fig_radar.update_layout(

                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),

                    showlegend=False,

                    height=400
                )
                

                c_col1, c_col2 = st.columns([1, 1])

                with c_col1:

                    st.plotly_chart(fig_radar, use_container_width=True)

                with c_col2:

                    st.markdown(f"### {selected_name}")

                    st.write(f"- **PBR**: {row_data['PBR(배)']}배")

                    st.write(f"- **배당수익률**: {row_data['배당수익률(%)']}%")

                    st.write(f"- **ROE**: {row_data['ROE(%)']}%")

                    st.write(f"- **이익잉여금비율**: {row_data['이익잉여금비율(%)']}%")

                    st.write(f"- **현금비중**: {row_data['현금비중(%)']}%")


            with d_tab2:
                # OpenDart (Electronic Disclosure)
                st.markdown("##### 📢 전자공시 (OpenDart - 최근 1년)")
                
                if not api_key:
                    st.warning("API Key가 필요합니다.")
                else:
                    client = OpenDartClient(api_key)
                    # 1년치 데이터 (Pagination을 위해 전체 가져옴)
                    if f"disclosures_{selected_code}" not in st.session_state:
                        with st.spinner("공시 조회 중..."):
                            st.session_state[f"disclosures_{selected_code}"] = client.get_disclosure_list(selected_code, months=12)
                    
                    disclosures = st.session_state.get(f"disclosures_{selected_code}", [])

                    if disclosures:
                        # Pagination Logic
                        items_per_page = 10
                        total_items = len(disclosures)
                        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
                        
                        # Page Selector
                        page_key = f"page_num_{selected_code}"
                        if page_key not in st.session_state:
                            st.session_state[page_key] = 1
                            
                        # Callback to reset page if code changes is handled by unique keys or user action, 
                        # but simple unique key for widget is enough for now.
                        
                        col_p1, col_p2 = st.columns([1, 3])
                        with col_p1:
                             current_page = st.number_input("페이지", min_value=1, max_value=total_pages, step=1, key=page_key)
                        
                        start_idx = (current_page - 1) * items_per_page
                        end_idx = start_idx + items_per_page
                        
                        page_items = disclosures[start_idx:end_idx]
                        
                        for d in page_items:
                            title = d.get('title', '-')
                            url = d.get('url', '#')
                            date = d.get('date', '')
                            # Display: [Title](URL) (Date)
                            st.markdown(f"- [{title}]({url}) ({date})")
                            
                    else:
                        st.info("최근 1년 공시가 없습니다.")

            with d_tab3:
                 # News
                 st.markdown("##### 📰 관련 뉴스 (Naver 증권)")
                 
                 news_query = st.text_input("검색어 (기업명)", value=selected_name, key=f"news_q_{selected_code}")
                 
                 # Encoding for URL
                 # Naver Finance News Search URL: https://finance.naver.com/news/news_search.naver?q={query}
                 # We can use st.link_button in newer Streamlit, or markdown link. 
                 # User requested "New Window". Markdown target='_blank' works best.
                 
                 import urllib.parse
                 encoded_query = urllib.parse.quote(news_query, encoding='euc-kr') # Naver uses EUC-KR often, but let's check. 
                 # Actually Finance News Search often works with UTF-8 or EUC-KR. Let's try standard quoting.
                 # Python's urllib.parse.quote uses utf-8 by default. 
                 # Naver Finance search query param 'q' usually accepts EUC-KR encoded string.
                 
                 try:
                    encoded_query_euc = urllib.parse.quote(news_query.encode('euc-kr'))
                 except:
                    encoded_query_euc = urllib.parse.quote(news_query)

                 link_url = f"https://finance.naver.com/news/news_search.naver?q={encoded_query_euc}"
                 
                 st.markdown(f"👉 **[{news_query} 뉴스 검색 결과 보기 (새창)]({link_url})**")
                 st.info("클릭 시 네이버 금융 뉴스 검색 페이지로 이동합니다.")


            with d_tab4:
                 # Research
                 st.markdown("##### 🧪 리서치 (Naver 증권)")

                 res_query = st.text_input("검색어 (기업명)", value=selected_name, key=f"res_q_{selected_code}")
                 
                 # Naver Research Search: https://finance.naver.com/research/search.naver?keyword={query}
                 try:
                    encoded_res_euc = urllib.parse.quote(res_query.encode('euc-kr'))
                 except:
                    encoded_res_euc = urllib.parse.quote(res_query)
                    
                 # Use itemCode for precise filtering, but also pass itemName to populate the UI input box
                 # Naver uses EUC-KR for itemName.
                 try:
                    encoded_name_euc = urllib.parse.quote(selected_name.encode('euc-kr'))
                 except:
                    encoded_name_euc = urllib.parse.quote(selected_name)

                 res_link_url = f"https://finance.naver.com/research/company_list.naver?searchType=itemCode&itemCode={selected_code}&itemName={encoded_name_euc}"

                 st.markdown(f"👉 **[{selected_name} 리서치 검색 결과 보기 (새창)]({res_link_url})**")
                 st.info("클릭 시 네이버 금융 종목분석 리포트(종목명 검색) 페이지로 이동합니다.")




def render_analysis(api_key):

    st.header("🔬 개별 종목 정밀 진단"
)
    st.caption("기업명 또는 종목코드를 입력하여 재무제표 기반 3년치 추이를 진단합니다.")


    if not api_key:

        st.error("좌측 사이드바에서 OpenDart API Key를 먼저 입력해주세요.")
        return


    # 1. Session State for History & Favorites
    if 'analysis_history' not in st.session_state:
        st.session_state['analysis_history'] = []

    # Initialize Favorites from Disk if not already in session
    if 'favorites_analysis' not in st.session_state:
        # Load from disk
        disk_favs = load_favorites_from_disk()
        st.session_state['favorites_analysis'] = disk_favs.get('analysis', [])  


    # --- [Favorites Logic - Scoped to Analysis] ---
    def toggle_favorite(name, code):
        """Add or remove from favorites (Analysis)"""
        target_key = 'favorites_analysis'
        fav_list = st.session_state[target_key]
        if any(f['code'] == code for f in fav_list):
            st.session_state[target_key] = [f for f in fav_list if f['code'] != code]
            st.toast(f"⭐ '{name}' 진단 즐겨찾기 해제됨")
        else:
            # Explicit new list creation to ensure state update detection
            new_fav = {'name': name, 'code': code}
            st.session_state[target_key] = fav_list + [new_fav]
            st.toast(f"⭐ '{name}' 진단 즐겨찾기 등록됨")
        
        # Save immediately to disk
        # We need current trend favorites to save the complete object, or just update the relevant part if we refactor.
        # But here we need to read session state for trend too.
        # Ensure trend favored exists in session, or load it.
        if 'favorites_trend' not in st.session_state:
             disk_data = load_favorites_from_disk()
             st.session_state['favorites_trend'] = disk_data.get('trend', [])

        save_favorites_to_disk(st.session_state['favorites_analysis'], st.session_state['favorites_trend'])
        save_state()

    def is_favorite(code):
        return any(f['code'] == code for f in st.session_state['favorites_analysis'])

    def render_favorites_section(key_suffix):
        """Render chips for favorites"""
        favs = st.session_state['favorites_analysis']
        clicked_result = (None, None)
        
        if favs:
            st.markdown("##### ⭐ 진단 즐겨찾기")
            cols = st.columns(8) # Grid-like
            for idx, fav in enumerate(favs):
                with cols[idx % 8]:
                    if st.button(fav['name'], key=f"fav_btn_{key_suffix}_{fav['code']}", help=f"{fav['code']} 조회"):
                        clicked_result = (fav['code'], fav['name'])
        
        return clicked_result[0], clicked_result[1]

    
    # 2. Search & Reset UI
    clicked_code, clicked_name = render_favorites_section("analysis")
    
    # Auto-fill if favorite clicked
    initial_query = ""
    if clicked_code:
        initial_query = clicked_code




    # 2. Search & Reset UI (Form for Enter Key Support)

    with st.container():

        # Using st.form allows handling "Enter" key submission

        with st.form(key='search_form'):

            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            # If clicked Favorite, use that. Else empty or user input.
            search_query = col1.text_input("기업명 또는 종목코드 (예: 삼성전자, 005930)", value=initial_query)

            base_year = col2.number_input("기준 년도", min_value=2015, max_value=2030, value=2024, step=1)
            

            # Button Alignment Fix (Spacer)

            col3.write("") 

            col3.write("")

            # Form submit button

            do_search = col3.form_submit_button("🔍 진단 실행", type="primary", use_container_width=True)
            

        # Reset button outside form (optional, or separate small form)

        # To align nicely, we might need to put it outside or use a trick.

        # Since columns are defined inside form, putting reset outside breaks layout alignment.

        # But 'st.form' column layout is isolated.

        # Let's keep reset simple outside or use a callback clear.
        

        if st.button("🔄 초기화", type="secondary"):
            st.session_state['analysis_history'] = []
            st.rerun()


    # 3. Handle Search Logic (Indent fixed due to form removal context, kept logic same)

    # 3. Handle Search Logic
    # Trigger if button clicked OR favorite clicked
    if do_search or clicked_code:
        
        # Use clicked_code if available (Override)
        if clicked_code:
            search_query = clicked_code

        # Determine if Code or Name

        target_code = search_query.strip()
        

        if not target_code.isdigit():

            # Search by Name

            df_krx = get_krx_listing()

            # Exact match first

            exact_match = df_krx[df_krx['Name'] == target_code]

            if not exact_match.empty:

                target_code = exact_match.iloc[0]['Code']

            else:

                # Contains match

                contains_match = df_krx[df_krx['Name'].str.contains(target_code)]

                if len(contains_match) == 1:

                    target_code = contains_match.iloc[0]['Code']

                elif len(contains_match) > 1:

                    st.warning(f"'{search_query}'(으)로 검색된 기업이 여러 개입니다. 정확한 이름을 입력해주세요: {', '.join(contains_match['Name'].tolist()[:5])}...")
                    return

                else:

                    st.error(f"'{search_query}' 기업을 찾을 수 없습니다. (KRX 리스트 기준)")
                    return


        # Fetch Data

        with st.spinner(f"'{target_code}' 데이터를 분석 중입니다... ({base_year}년 기준)"):

            result, error = fetch_real_company_data(target_code, api_key, base_year)
            

            if error:
                st.error(error)

            else:

                # Add to history (prevent duplicates at top)

                # Remove existing if same code

                st.session_state['analysis_history'] = [item for item in st.session_state['analysis_history'] if item['meta']['code'] != target_code]

                st.session_state['analysis_history'].insert(0, result)


    # 4. Render History List

    st.divider()
    

    if not st.session_state['analysis_history']:

        st.info("검색된 기록이 없습니다. 기업명이나 코드로 검색을 시작하세요.")

    else:

        for idx, item in enumerate(st.session_state['analysis_history']):

            metrics = item['metrics']

            history = item['history']

            meta = item['meta']

            shareholders = item.get('shareholders', [])
            

            with st.expander(f"📌 {meta['name']} ({meta['code']}) 진단 결과", expanded=(idx==0)):
                
                # Favorite Toggle (Using Columns for layout)
                c_head, c_star = st.columns([0.9, 0.1])
                with c_star:
                    is_fav = is_favorite(meta['code'])
                    btn_label = "★" if is_fav else "☆"
                    if st.button(btn_label, key=f"star_analysis_{meta['code']}_{idx}", help="즐겨찾기 토글"):
                        toggle_favorite(meta['name'], meta['code'])
                        st.rerun()

                # KPI Cards

                k1, k2, k3, k4 = st.columns(4)
                

                k1.metric("이익잉여금 비율", f"{metrics['retained_rate']}%", 

                          delta="양호" if metrics['retained_rate'] > 500 else "부족")
                

                # 유동자산 KPI (Replace Cash Ratio)

                cur_assets_now = history[0]['current_assets']

                cur_assets_prev = history[1]['current_assets'] if len(history) > 1 else 0

                diff = cur_assets_now - cur_assets_prev

                k2.metric("유동자산", f"{cur_assets_now:,}억", 

                          delta=f"{diff:,}억" if cur_assets_prev > 0 else None)


                k3.metric("PBR", f"{metrics['pbr']}배", 

                          delta="저평가" if metrics['pbr'] < 1.0 else "적정", delta_color="inverse")

                k4.metric("시가총액", f"{item['market_cap']:,}억")


                # Shareholders Table (Moved Above Trend)

                if shareholders:

                    st.subheader("👥 주요 주주 현황 (본인 및 특수관계인)"
)
                    df_share = pd.DataFrame(shareholders)

                    # Columns already match: 성명, 관계, 총지분율 (from OpenDartClient)

                    st.table(df_share)


                # 3-Year Trend Table

                st.subheader("📊 최근 3년 재무 추이"
)
                df_history = pd.DataFrame(history)

                # Reorder and Rename columns for display

                # Removed: cash_equivalents, cash_ratio, net_income as per request ("Delete")

                # Kept: year, assets, equity, liabilities, retained, retained_rate, current_assets, roe

                df_disp = df_history[['year', 'assets', 'equity', 'liabilities', 'retained', 'retained_rate', 'current_assets', 'roe']]

                df_disp.columns = ['연도', '자산총계(억)', '자본총계(억)', '부채총계(억)', '이익잉여금(억)', '이익잉여금비율(%)', '유동자산(억)', 'ROE(%)']

                st.dataframe(df_disp.style.format("{:,}"), use_container_width=True, hide_index=True)
                

                

                st.caption(f"* 데이터 출처: OpenDart 사업보고서 (선택 연도 ({base_year}) 기준)")
                

                # Simple Visualization for Trend (Retained Rate)

                fig_trend = px.line(df_history, x='year', y='retained_rate', title=f"{meta['name']} 이익잉여금비율 추이", markers=True)

                fig_trend.update_layout(yaxis_title="비율(%)", xaxis_title="연도", height=300)

                st.plotly_chart(fig_trend, use_container_width=True)




# --- [Render Layer] Stock Trend Tab ---

def render_stock_trend():

    st.header("📈 주가 시세 추이"
)
    st.caption("개별 종목의 일별 시세와 주가 변동 추이를 확인합니다.")
    

    # 0. Session State for History
    if 'trend_history' not in st.session_state:
        st.session_state['trend_history'] = []

    # 1. Session State for Favorites (Trend)
    if 'favorites_trend' not in st.session_state:
        # Load from Disk
        disk_favs = load_favorites_from_disk()
        st.session_state['favorites_trend'] = disk_favs.get('trend', [])


    # --- [Favorites Logic - Scoped to Trend] ---
    def toggle_favorite(name, code):
        target_key = 'favorites_trend'
        fav_list = st.session_state[target_key]
        if any(f['code'] == code for f in fav_list):
            st.session_state[target_key] = [f for f in fav_list if f['code'] != code]
            st.toast(f"⭐ '{name}' 시세 즐겨찾기 해제됨")
        else:
            # Explicit new list creation
            new_fav = {'name': name, 'code': code}
            st.session_state[target_key] = fav_list + [new_fav]
            st.toast(f"⭐ '{name}' 시세 즐겨찾기 등록됨")
            
        # Save immediately to disk
        if 'favorites_analysis' not in st.session_state:
             disk_data = load_favorites_from_disk()
             st.session_state['favorites_analysis'] = disk_data.get('analysis', [])
             
        save_favorites_to_disk(st.session_state['favorites_analysis'], st.session_state['favorites_trend'])
        save_state()

    def is_favorite(code):
        return any(f['code'] == code for f in st.session_state['favorites_trend'])

    def render_favorites_section(key_suffix):
        favs = st.session_state['favorites_trend']
        clicked_result = (None, None)

        if favs:
            st.markdown("##### ⭐ 시세 즐겨찾기")
            cols = st.columns(8)
            for idx, fav in enumerate(favs):
                with cols[idx % 8]:
                    if st.button(fav['name'], key=f"fav_btn_{key_suffix}_{fav['code']}", help=f"{fav['code']} 조회"):
                        clicked_result = (fav['code'], fav['name'])
        
        return clicked_result[0], clicked_result[1]


    # 1. Search Bar & Controls
    clicked_code, clicked_name = render_favorites_section("trend")
    initial_query = clicked_code if clicked_code else ""

    with st.container():

        # Using st.form allows handling "Enter" key submission

        with st.form(key='trend_search_form'):

            c1, c2, c3 = st.columns([3, 1, 1])

            search_query = c1.text_input("기업명 또는 종목코드 (예: 현대백화점, 069960)", value=initial_query)
            

            # Period Selector in Form

            # Period Selector in Form

            period_map = {

                "1개월": 30,

                "3개월": 90,

                "6개월": 180,

                "12개월": 365

            }

            selected_period = c2.selectbox("조회 기간", list(period_map.keys()), index=3) # Default 12 Months
            

            with c3:

                st.write("") # Label Spacer

                st.write("") 

                do_search = st.form_submit_button("🔍 조회", type="primary", use_container_width=True)
            

        # Reset Button (Outside Form to work independently)

        if st.button("🔄 초기화", key='trend_reset'):
            st.session_state['trend_history'] = []
            st.rerun()


    # 2. Search Logic

    # 2. Search Logic
    if (do_search or clicked_code) and (search_query or clicked_code):
        
        if clicked_code: search_query = clicked_code

        target_code = search_query.strip()
        

        # Name to Code Logic (Simple version)

        if not target_code.isdigit():

             df_krx = get_krx_listing()

             match = df_krx[df_krx['Name'] == target_code]

             if not match.empty:

                 target_code = match.iloc[0]['Code']

             else:

                 # Fuzzy match

                 matches = df_krx[df_krx['Name'].str.contains(target_code)]

                 if len(matches) == 1:

                     target_code = matches.iloc[0]['Code']

                 elif len(matches) > 1:

                     st.warning(f"검색된 기업이 여러 개입니다: {', '.join(matches['Name'].tolist()[:5])}...")
                     return

                 else:

                     st.error("기업을 찾을 수 없습니다.")
                     return


        days_to_fetch = period_map[selected_period]


        # Fetch Data

        with st.spinner(f"'{target_code}' 주가 데이터 조회 중... ({selected_period})"):

            df_history = get_stock_history(target_code, days=days_to_fetch)
            

        if df_history.empty:

            st.error("데이터가 없거나 조회에 실패했습니다.")

        else:

            # Get Name for Title

            try:

                 df_krx = get_krx_listing()

                 name_row = df_krx[df_krx['Code'] == target_code]

                 corp_name = name_row.iloc[0]['Name'] if not name_row.empty else target_code

            except:

                corp_name = target_code # Fallback
            

            # Add to History (Dedup logic: Remove if same code exists to bring to top? Or just stack? Let's stack or move to top)

            # Preference: Move to top if exists, or add new

            st.session_state['trend_history'] = [item for item in st.session_state['trend_history'] if item['code'] != target_code]
            

            new_item = {

                "name": corp_name,

                "code": target_code,

                "period": selected_period,

                "df": df_history

            }

            st.session_state['trend_history'].insert(0, new_item)



    # 3. Render History

    st.divider()
    

    if not st.session_state['trend_history']:

        st.info("조회된 내역이 없습니다. 기업을 검색해보세요.")

    else:

        for idx, item in enumerate(st.session_state['trend_history']):

            code = item['code']

            name = item['name']

            period = item['period']

            df = item['df']
            

            # Using Expander for cleaner history
            with st.expander(f"📈 {name} ({code}) - {period}", expanded=(idx==0)):
                
                # Favorite Toggle
                c_head, c_star = st.columns([0.9, 0.1])
                with c_star:
                    is_fav = is_favorite(code)
                    btn_label = "★" if is_fav else "☆"
                    if st.button(btn_label, key=f"star_trend_{code}_{idx}", help="즐겨찾기 토글"):
                        toggle_favorite(name, code)
                        st.rerun()

                # Chart

                st.markdown(f"##### 🕯️ 캔들 차트 ({period})")
                

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 

                                    vertical_spacing=0.03, subplot_titles=('Price', 'Volume'), 

                                    row_width=[0.2, 0.7])


                # Candle

                fig.add_trace(go.Candlestick(x=df['Date'],

                        open=df['Open'],

                        high=df['High'],

                        low=df['Low'],

                        close=df['Close'], name='Price'), row=1, col=1)


                # Volume

                colors = ['red' if row['Open'] - row['Close'] >= 0 else 'green' for index, row in df.iterrows()]

                fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], showlegend=False, marker_color=colors, name='Volume'), row=2, col=1)
                        

                fig.update_layout(xaxis_rangeslider_visible=False, height=500)

                st.plotly_chart(fig, use_container_width=True)
                

                # Calculate Highest (Close Basis)

                if not df.empty:

                    max_close_price = df['Close'].max()

                    # df is likely sorted by Date desc (from get_stock_history)

                    max_row = df[df['Close'] == max_close_price].iloc[0] 

                    max_date_str = max_row['Date'].strftime('%Y-%m-%d')
                    

                    # Current (Latest) Close Price

                    current_close = df.iloc[0]['Close']

                    if max_close_price > 0:

                        rate = ((current_close - max_close_price) / max_close_price) * 100

                    else:

                        rate = 0.0
                    

                    st.markdown(f"##### 📋 일별 시세 데이터 <span style='color:dodgerblue; font-size:0.9em; margin-left:10px;'>기간 내 최고가(종가): {int(max_close_price):,}원 ({max_date_str}) [최고가 대비 {rate:+.2f}%]</span>", unsafe_allow_html=True
)
                else:

                    st.markdown("##### 📋 일별 시세 데이터"
)
                df_display = df.copy()

                df_display['Date'] = df_display['Date'].dt.strftime('%Y-%m-%d')

                df_display.columns = ['날짜', '시가', '고가', '저가', '종가', '거래량']
                

                st.dataframe(df_display, use_container_width=True, hide_index=True, height=720)



def main():

    # Load previous state on startup
    load_state()


    # Sidebar Input (Global)

    st.sidebar.markdown("---")

    st.sidebar.subheader("🔐 API 설정 (보안)")


    # 1. Environment Variable Check (GitHub Actions / DotEnv)
    env_key = load_from_env()
    
    # 2. Existing Credentials Check (Local)
    has_creds = check_credentials_exist()
    

    # Session Initialize
    if 'api_key' not in st.session_state: 
        st.session_state['api_key'] = env_key if env_key else None
        
    current_key = st.session_state['api_key']

    # Decide UI Flow
    if env_key:
        st.sidebar.success("🔐 API Key (시스템/환경변수)")
        # Skip Setup/Unlock forms if Env Key is present and active
        current_key = env_key # Ensure it's set
        st.session_state['api_key'] = env_key

    elif has_creds:

        if current_key:

            st.sidebar.success("✅ API Key 활성화됨")
            

            # Change / Reset

            with st.sidebar.expander("API Key / 비밀번호 변경"):

                with st.form("reset_creds_form"):

                    st.caption("기존 비밀번호로 검증 후 변경합니다.")

                    verify_pw = st.text_input("현재 비밀번호", type="password")

                    new_api_key = st.text_input("새 API Key", type="password")

                    new_pin = st.text_input("새 비밀번호", type="password")
                    

                    btn_change = st.form_submit_button("변경 적용")
                    

                    if btn_change:

                        if verify_pin(verify_pw):

                            if new_api_key and new_pin:

                                save_credentials(new_api_key, new_pin)

                                st.session_state['api_key'] = new_api_key

                                st.success("변경되었습니다.")

                            else:

                                st.error("새 값을 입력해주세요.")

                        else:

                            st.error("현재 비밀번호가 틀립니다.")

        else:

            st.sidebar.warning("🔒 API Key 잠김"
)
            with st.sidebar.form("unlock_form"):

                unlock_pw = st.text_input("비밀번호 입력", type="password")

                btn_unlock = st.form_submit_button("잠금 해제")
                

                if btn_unlock:

                    decrypted_key = load_credentials(unlock_pw)

                    if decrypted_key:

                        st.session_state['api_key'] = decrypted_key
                        st.rerun()

                    else:

                        st.error("비밀번호가 일치하지 않습니다.")

    else:

        st.sidebar.info("🛠️ API Key 최초 설정"
)
        with st.sidebar.form("setup_form"):

            st.caption("OpenDart API Key를 안전하게 저장합니다.")

            input_key = st.text_input("API Key 입력", type="password")

            input_pw = st.text_input("관리용 비밀번호 설정", type="password")

            btn_setup = st.form_submit_button("저장 및 적용")
            

            if btn_setup:

                if input_key and input_pw:

                    save_credentials(input_key, input_pw)

                    st.session_state['api_key'] = input_key

                    st.sidebar.success("저장되었습니다.")
                    st.rerun()

                else:

                    st.error("API Key와 비밀번호를 모두 입력해주세요.")
            

    # Check if credentials exist (Mocking the variable for logic flow if needed, but we use session state directly)

    opendart_api_key = st.session_state.get('api_key')
                        

    # Tabs

    tab1, tab2, tab3 = st.tabs(["🚀 발굴 대시보드", "📊 개별 종목 분석", "📈 주가 시세 추이"])
    

    with tab1:

        log_transition("View Dashboard")

        # Dashboard는 Mock Data 사용 (API Key 불필요 -> Hybrid로 변경)

        render_dashboard(opendart_api_key) 
    

    with tab2:

        log_transition("View Analysis")

        render_analysis(opendart_api_key)
        

    with tab3:

        log_transition("View Trends")

        render_stock_trend()


if __name__ == "__main__":
    main()