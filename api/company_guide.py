import requests
from bs4 import BeautifulSoup
import pandas as pd
import concurrent.futures
import time

def get_company_snapshot(code):
    """
    Company Guide(FnGuide)에서 기업의 주요 지표(PER, PBR, ROE, 배당수익률 등)를 스크래핑합니다.
    URL: https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?gicode=A{code}
    """
    try:
        url = f"https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?pGB=1&gicode=A{code}&cID=&MenuYn=Y&ReportGB=&NewMenuID=101&stkGb=701"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 데이터 추출 로직 (Selector는 사이트 구조에 따라 변동 가능)
        # Snapshot 페이지의 'CorpGroup' 클래스 활용 또는 특정 테이블 위치
        
        # 1. 시세 현황 (PBR, PER, 배당수익률)
        # 보통 #corp_group2 하위 테이블에 위치
        
        data = {
            "code": code,
            "pbr": None,
            "per": None,
            "dividend_yield": 0.0,
            "roe": None,
            "treasury_shares": 0.0 # 자사주 비중 (Optional)
        }
        
        # PBR/PER/배당수익률 찾기 (ID 기반 검색이 안정적)
        # FnGuide는 동적으로 생성되기도 하지만, 기본 HTML에 포함됨.
        
        # Table Parsing Helper
        def parse_metric(soup, label_list):
            for label in label_list:
                # dl, dt, dd 구조 혹은 table 구조 확인
                # FnGuide Snapshot 쪽 '재무비율' 섹션 확인
                pass
        
        # CorpInfo (우측 상단 요약) - PER, 12M PER, 업종 PER, PBR, 배당수익률
        corp_group2 = soup.find('div', {'id': 'corp_group2'})
        if corp_group2:
            dts = corp_group2.find_all('dt')
            dds = corp_group2.find_all('dd')
            
            for dt, dd in zip(dts, dds):
                text = dt.text.strip()
                val_text = dd.text.strip().replace(',', '')
                
                if 'PER' in text and '12M' not in text and '업종' not in text:
                    try: data['per'] = float(val_text)
                    except: pass
                elif 'PBR' in text:
                    try: data['pbr'] = float(val_text)
                    except: pass
                elif '배당수익률' in text:
                    try: data['dividend_yield'] = float(val_text.replace('%', ''))
                    except: pass
        
        # ROE 찾기 (Highlight D 테이블 - Main Page)
        highlight_d_div = soup.find('div', {'id': 'highlight_D_Y'})
        if highlight_d_div:
            trs = highlight_d_div.find_all('tr')
            for tr in trs:
                th = tr.find('th')
                if th and 'ROE' in th.text:
                    tds = tr.find_all('td')
                    valid_roes = []
                    for td in tds:
                        try:
                            val = float(td.text.replace(',', '').strip())
                            valid_roes.append(val)
                        except:
                            pass
                    if valid_roes:
                        data['roe'] = valid_roes[-1]

        # --- [Add] Financial Statement Parsing (SVD_Finance.asp) ---
        # 이익잉여금, 현금및현금성자산, 유동자산, 자본총계 추출
        try:
            url_fin = f"https://comp.fnguide.com/SVO2/ASP/SVD_Finance.asp?pGB=1&gicode=A{code}&cID=&MenuYn=Y&ReportGB=&NewMenuID=103&stkGb=701"
            res_fin = requests.get(url_fin, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            
            if res_fin.status_code == 200:
                soup_fin = BeautifulSoup(res_fin.text, 'html.parser')
                
                # 대차대조표 (연간) - divDaechaY
                div_bs = soup_fin.find('div', {'id': 'divDaechaY'})
                if div_bs:
                    # Helper to find value in table
                    def find_val(soup_obj, keywords):
                        # Find all trs, check first th/td for keyword
                        # Then get the last valid column (Recent Year)
                        trs = soup_obj.find_all('tr')
                        for tr in trs:
                            # Header usually in 'th' or 'td' with class 'l' (left aligned)
                            header = tr.find(['th', 'td']) 
                            
                            if header:
                                # Clean text
                                txt = header.text.strip().replace(' ', '').replace('\n', '').replace('\xa0', '')
                                
                                # Check partial match for any keyword
                                matched = False
                                for k in keywords:
                                    if k in txt:
                                        matched = True
                                        break
                                
                                if matched:
                                    # Get values (usually tds not class 'l')
                                    # FnGuide structure: 
                                    # <tr> <th class="l">Label</th> <td class="r">Val1</td> <td class="r">Val2</td> ... </tr>
                                    cols = tr.find_all('td')
                                    
                                    # Filter columns that look like data (class 'r' or just numbers)
                                    # And filter out class 'l' if it was a td header
                                    data_cols = [c for c in cols if 'l' not in c.get('class', [])]
                                    
                                    # Extract values
                                    vals = []
                                    for c in data_cols:
                                        try:
                                            # remove commas, check if valid number
                                            t_val = c.text.strip().replace(',', '')
                                            if t_val and t_val != '-':
                                                vals.append(float(t_val))
                                            else:
                                                vals.append(0.0) # explicit missing
                                        except: 
                                            pass
                                            
                                    # Return the most recent valid value (usually last column is latest year, or second to last if estimate exists)
                                    # FnGuide Annual: Usually 4 columns. Last one might be 'Last Year' or 'Current Year Estimate'??
                                    # Usually columns are [Y-3, Y-2, Y-1, Y(Recent)]
                                    if vals:
                                        return vals[-1]
                        return 0.0

                    # 1. 자본총계 (Total Equity)
                    equity = find_val(div_bs, ['자본총계', '자본'])
                    
                    # 2. 이익잉여금 (Retained Earnings)
                    retained = find_val(div_bs, ['이익잉여금', '미처분이익잉여금', '이익잉여금(결손금)'])
                    
                    # 3. 유동자산 (Current Assets)
                    cur_asset = find_val(div_bs, ['유동자산'])
                    
                    # 4. 현금및현금성자산 (Cash)
                    cash = find_val(div_bs, ['현금및현금성자산', '현금', '현금및해당자산', '현금및예치금'])

                    data['equity'] = equity
                    data['retained'] = retained
                    data['current_assets'] = cur_asset
                    data['cash_equivalents'] = cash
                    
                    # Calculate Ratios
                    # 이익잉여금비율 (%) = (이익잉여금 / 자본총계) * 100
                    if equity > 0 and retained > 0:
                        data['retained_rate'] = round((retained / equity) * 100, 1)
                    else:
                        data['retained_rate'] = 0.0
                        
                    # 현금비중 (%) = (현금 / 유동자산) * 100
                    if cur_asset > 0 and cash > 0:
                        data['cash_ratio'] = round((cash / cur_asset) * 100, 1)
                    else:
                        data['cash_ratio'] = 0.0

        except Exception as e:
            # print(f"Fin details parsing error {code}: {e}")
            pass

        return data

    except Exception as e:
        print(f"Error scraping {code}: {e}")
        return None

def get_batch_company_data(codes, max_workers=10):
    """
    여러 기업의 데이터를 병렬로 수집합니다.
    (Blocking 방지를 위해 worker 수 조정: 4 -> 20)
    """
    results = []
    # max_workers reduced to 8 for stability (Code Review Feedback)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_code = {executor.submit(get_company_snapshot, code): code for code in codes}
        
        for future in concurrent.futures.as_completed(future_to_code):
            code = future_to_code[future]
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                print(f"Exception for {code}: {e}")
                
    return pd.DataFrame(results)
