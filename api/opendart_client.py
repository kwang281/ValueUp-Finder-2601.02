import OpenDartReader
import pandas as pd

class OpenDartClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.init_error = None
        self.dart = None
        if api_key:
            try:
                self.dart = OpenDartReader(api_key)
            except Exception as e:
                self.init_error = str(e)
                print(f"Error initializing OpenDartReader: {e}")

    def get_financial_summary(self, corp_code, year, reprt_code=None):
        """
        특정 기업의 재무제표 주요 항목을 가져옵니다.
        reprt_code가 지정되지 않으면 연말(11011) -> 3분기(11014) -> 반기(11012) -> 1분기(11013) 순으로 조회합니다.
        """
        if not self.dart:
            return None

        # 순회할 보고서 코드 리스트 (우선순위: 사업 > 3분기 > 반기 > 1분기)
        if reprt_code:
            search_codes = [reprt_code]
        else:
            search_codes = ['11011', '11014', '11012', '11013']

        finstate = None
        used_reprt_code = None

        try:
            for code in search_codes:
                try:
                    # 재무제표 조회 (연결 재무제표 우선, 없으면 별도)
                    # fs_div: CFS(연결), OFS(별도)
                    temp_finstate = self.dart.finstate(corp_code, year, reprt_code=code)
                    if temp_finstate is not None and not temp_finstate.empty:
                        finstate = temp_finstate
                        used_reprt_code = code
                        break
                except Exception:
                    continue
            
            if finstate is None or finstate.empty:
                return None

            # 필요한 계정 항목 추출 로직
            # OpenDart API는 계정명이 '자산총계', '자본총계' 등으로 나옴.
            
            # 관심 있는 계정명 리스트
            target_accounts = {
                '자산총계': ['자산총계', '자산'],
                '부채총계': ['부채총계', '부채'],
                '자본총계': ['자본총계', '자본'],
                '유동자산': ['유동자산'], 
                '이익잉여금': ['이익잉여금', '미처분이익잉여금', '결손금', '미처리결손금', '이익잉여금(결손금)'], 
                '현금성자산': ['현금및현금성자산', '현금 및 현금성자산', '현금', '현금성자산'],
                '단기금융상품': ['단기금융상품', '유동금융자산', '기타유동금융자산', '단기매매증권', '단기투자자산', '금융기관예치금'],
                '당기순이익': [
                    '당기순이익', '법인세비용차감전순이익', '연결당기순이익', '보통주당기순이익', '당기순손익', 
                    '지배기업소유주지분순이익', '지배기업의 소유주에게 귀속되는 당기순이익', '당기순이익(손실)', 
                    '분기순이익', '분기순이익(손실)', '반기순이익', '반기순이익(손실)', '지배기업의 소유주에게 귀속되는 분기순이익',
                    '지배기업의 소유주에게 귀속되는 반기순이익'
                ] 
            }
            # Note: For Net Income, often '당기순이익' is the key. 
            # In 'CFS' (Consolidated), it is usually '당기순이익'.

            
            result = {}
            
            # 1. 메인 데이터프레임 선택 (연결 우선)
            # CFS: 연결, OFS: 별도
            df_main = finstate[finstate['fs_div'] == 'CFS']
            if df_main.empty:
                df_main = finstate[finstate['fs_div'] == 'OFS']
                
            if df_main.empty:
                return getattr(self, "_mock_fail_data", None)

            # 2. 계정명 매핑을 위한 Lookup Dictionary 생성
            # Main Report (Current Data)
            account_map = df_main.set_index('account_nm').to_dict('index')

            # Secondary Report (Historical Data) - If Main is NOT Annual
            account_map_prev = {}
            if used_reprt_code != '11011':
                try:
                    # Fetch Previous Year's Annual Report
                    finstate_prev = self.dart.finstate(corp_code, year - 1, reprt_code='11011')
                    if finstate_prev is not None and not finstate_prev.empty:
                        # Prefer CFS, fallback to OFS
                        df_prev = finstate_prev[finstate_prev['fs_div'] == 'CFS']
                        if df_prev.empty:
                            df_prev = finstate_prev[finstate_prev['fs_div'] == 'OFS']
                        
                        if not df_prev.empty:
                            account_map_prev = df_prev.set_index('account_nm').to_dict('index')
                except Exception as e:
                    print(f"Error fetching historical annual report: {e}")

            result = {}

            # 3. 데이터 추출 함수 (Map 기반)
            def get_values_from_map(target_names):
                # Search Priority: Try to find any matching name in current map first
                matched_name_current = None
                for name in target_names:
                    if name in account_map:
                        matched_name_current = name
                        break
                
                # Try to find match in prev map
                matched_name_prev = None
                if account_map_prev:
                    for name in target_names:
                        if name in account_map_prev:
                            matched_name_prev = name
                            break
                
                vals = [0, 0, 0] # [Current, Prev, PrevPrev]

                # --- 1. Current Year Value ---
                if matched_name_current:
                    row_data = account_map[matched_name_current]
                    
                    # Accumulation Logic for Interim
                    val_current_str = None
                    if used_reprt_code != '11011': 
                         val_current_str = row_data.get('thstrm_add_amount')
                    
                    if not val_current_str or pd.isna(val_current_str) or str(val_current_str).strip() == '':
                        val_current_str = row_data.get('thstrm_amount', '0')
                        
                    try:
                        vals[0] = int(str(val_current_str).replace(',', ''))
                    except:
                        vals[0] = 0
                
                # --- 2. Historical Values (Prev, PrevPrev) ---
                if used_reprt_code != '11011' and matched_name_prev:
                    # If we have a Previous Annual Report, use it for Year-1 and Year-2
                    row_data_prev = account_map_prev[matched_name_prev]
                    
                    # Year-1 (thstrm_amount of Prev Annual)
                    try:
                        t_val = row_data_prev.get('thstrm_amount', '0')
                        vals[1] = int(str(t_val).replace(',', ''))
                    except:
                        vals[1] = 0
                        
                    # Year-2 (frmtrm_amount of Prev Annual)
                    try:
                        f_val = row_data_prev.get('frmtrm_amount', '0')
                        vals[2] = int(str(f_val).replace(',', ''))
                    except:
                        vals[2] = 0
                        
                elif matched_name_current:
                    # Fallback: Use columns from Current Report (Standard Logic)
                    row_data = account_map[matched_name_current]
                    
                    # Year-1
                    cols_y1 = ['frmtrm_amount', 'frmtrm_add_amount'] # Fallback
                    for c in cols_y1:
                        try:
                            v = row_data.get(c, '0')
                            if v and not pd.isna(v):
                                vals[1] = int(str(v).replace(',', ''))
                                break
                        except: pass
                        
                    # Year-2
                    cols_y2 = ['bfefrmtrm_amount', 'bfefrmtrm_add_amount']
                    for c in cols_y2:
                        try:
                            v = row_data.get(c, '0')
                            if v and not pd.isna(v):
                                vals[2] = int(str(v).replace(',', ''))
                                break
                        except: pass

                return vals

            for key, names in target_accounts.items():
                result[key] = get_values_from_map(names)

            return result

        except Exception as e:
            print(f"Error fetching financial data: {e}")
            return None

    def get_corp_name(self, corp_code):
        if not self.dart: 
            return corp_code
        try:
            return corp_code 
        except:
            return corp_code

    def get_major_shareholders(self, corp_code):
        """
        최대주주 및 특수관계인 지분율을 가져옵니다.
        '본인' 또는 '최대주주의 특수관계인'만 필터링하여 
        보통주/우선주 합산 지분율 상위 5명 반환.
        """
        if not self.dart:
            return []

        try:
            # OpenDartReader: major_shareholders(corp_code)
            # API: /api/major_shareholders.json (사업보고서 내 최대주주 현황)
            df = self.dart.major_shareholders(corp_code)
            
            if df is None or df.empty:
                return []
            
            # --- 1. 컬럼 확인 및 정제 ---
            # 필요한 컬럼: nm(성명), relate(관계), stock_knd(주식종류), 
            # 주식수 또는 지분율 컬럼: trmend_possession_stock_qota_rt (기말소유주식지분율)
            # trmend_possession_stock_co (기말소유주식수) - for checking
            
            # API 응답에 따라 컬럼명이 다를 수 있으므로 체크 (주요 패턴)
            # 보통 'trmend_possession_stock_qota_rt' 가 지분율
            
            target_col = 'trmend_possession_stock_qota_rt'
            if target_col not in df.columns:
                return [] # 핵심 데이터 없음

            if 'relate' not in df.columns or 'nm' not in df.columns:
                return []

            # --- 2. 필터링 (관계) ---
            target_rels = ['본인', '최대주주의 특수관계인']
            # 데이터 정제: 공백 제거
            df['relate'] = df['relate'].astype(str).str.strip()
            df['nm'] = df['nm'].astype(str).str.strip()
            
            # 검색
            filtered_df = df[df['relate'].isin(target_rels)].copy()
            
            if filtered_df.empty:
                return []

            # --- 3. 지분율 수치 변환 ---
            def clean_float(x):
                try:
                    return float(str(x).replace(',', '').replace('-', ''))
                except:
                    return 0.0
            
            filtered_df['stake_val'] = filtered_df[target_col].apply(clean_float)
            
            # --- 4. 합산 로직 (이름 + 관계 기준) ---
            # 보통 주식 종류(stock_knd)가 '보통주', '우선주' 등으로 나뉘어 들어옴.
            # 이를 구분하지 않고 '이름'과 '관계'가 같으면 지분율을 단순 합산한다.
            # (총 발행 주식수 기준 지분율이므로 단순 합산 가능)
            
            # Group by Name and Relation
            grouped_df = filtered_df.groupby(['nm', 'relate'])['stake_val'].sum().reset_index()
            
            # 소수점 처리 (깔끔하게)
            grouped_df['stake_val'] = grouped_df['stake_val'].round(2)
            
            # --- 5. 순위 선정 (상위 5명) ---
            # 지분율 내림차순
            grouped_df = grouped_df.sort_values(by='stake_val', ascending=False)
            top_5 = grouped_df.head(5)
            
            # --- 6. 결과 반환 ---
            result = []
            for _, row in top_5.iterrows():
                result.append({
                    "성명": row['nm'],
                    "관계": row['relate'],
                    "총지분율": f"{row['stake_val']}%" # 문자열 포맷팅
                })
                
            return result

        except Exception as e:
            print(f"Error fetching shareholders: {e}")
            return []

    def get_disclosure_list(self, corp_code, months=6):
        """
        최근 n개월간의 공시 목록을 가져옵니다.
        """
        if not self.dart:
            return []
            
        try:
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30*months)
            
            # YYYYMMDD string format
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")
            
            # Fetch list
            disc_list = self.dart.list(corp_code, start=start_str, end=end_str)
            
            if disc_list is None or disc_list.empty:
                return []
            
            # Select relevant columns: report_nm, rcept_no, rcept_dt
            # Map to list of dicts
            results = []
            for _, row in disc_list.iterrows():
                # Report URL: http://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}
                url = f"http://dart.fss.or.kr/dsaf001/main.do?rcpNo={row['rcept_no']}"
                results.append({
                    "title": row['report_nm'],
                    "date": row['rcept_dt'],
                    "url": url,
                    "submitter": row.get('flr_nm', '')
                })
                
            return results # Return all fetched results
            
        except Exception as e:
            print(f"Error fetching disclosures: {e}")
            return []
