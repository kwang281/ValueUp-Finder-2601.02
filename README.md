
# Value-Up Finder (v2601.02) 애플리케이션 가이드
  

**Value-Up Finder**는 소위 '저평가 우량주(Value-Up)'를 발굴하기 위한 **주식 분석 대시보드**입니다.

한국 주식 시장(KOSPI, KOSDAQ, KONEX)의 시가총액 상위 300개 기업을 대상으로 다양한 재무 지표를 스크리닝하고, 특정 기업에 대한 정밀 진단(전자공시 기반) 기능을 제공합니다.

  

### 주요 기능

1.  **발굴 대시보드 (Screening Dashboard)**

    *   **대상**: 시가총액 상위 300개 기업 (FinanceDataReader + KRX 기준).

    *   **데이터 출처**: CompanyGuide (FnGuide) 웹 스크래핑 (PER, PBR, 배당수익률, ROE, 이익잉여금비율, 현금비중).

    *   **기능**: 사용자가 설정한 재무 조건(PBR, 배당수익률 등)에 맞는 기업을 필터링하여 리스트업.

    *   **최적화**: 매일 16:00 기준으로 데이터를 수집 및 캐싱(`data/` 폴더)하여 로딩 속도 최적화.

  

2.  **개별 종목 정밀 진단 (Deep Analysis)**

    *   **데이터 출처**: OpenDart (금융감독원 전자공시시스템) API.

    *   **기능**: 선택한 기업의 최근 3년치 재무제표(자산, 자본, 부채, 이익잉여금 등)를 조회하고 3년 추이를 시각화.

    *   **주주 현황**: 최대주주 및 특수관계인의 지분율을 조회.

    *   **필수 조건**: 개인 OpenDart API Key 필요 (암호화되어 로컬 저장).

  

3.  **주가 시세 추이 (Trend Analysis)**

    *   **데이터 출처**: Naver Finance (via FinanceDataReader).

    *   **기능**: 최근 1개월~12개월 주가 흐름(캔들 차트, 거래량) 및 최고가 대비 하락률 분석.

  

---

  

## 2. 코드 구조 및 파일 설명

  

프로젝트는 모듈화된 구조를 가지고 있으며, 유지보수와 확장성을 고려하여 설계되었습니다.

  

### 📂 폴더 구조

```text

d:/01_Codes/ValueUp-2512.01/

├── value-up.py           # [Main] 메인 애플리케이션 실행 파일 (Streamlit UI 구성)

├── setup_and_run.bat     # [Batch] 윈도우 원클릭 설치 및 실행 스크립트

├── requirements.txt      # [Config] 필수 파이썬 라이브러리 목록

├── secrets.json          # [Data] (자동생성) 암호화된 API Key 저장 파일

├── api/                  # [Module] 외부 데이터 연동 모듈

│   ├── opendart_client.py  # OpenDart API 연동 (재무제표, 공시, 주주현황)

│   ├── company_guide.py    # FnGuide 웹 크롤링 (실시간 지표 수집)

│   ├── market_data.py      # FinanceDataReader 래퍼 (시세, 시총)

│   └── naver_news.py       # 네이버 뉴스 검색 크롤러

└── utils/                # [Module] 유틸리티 모듈

    ├── security.py         # API Key 암호화/복호화 (Cryptography)

    ├── state_manager.py    # Streamlit 세션 상태 관리

    └── logger.py           # 로그 기록 (현재는 단순 출력)

```

  

### 📝 주요 파일 분석

  

#### 1. `value-up.py` (메인)

*   프로그램의 진입점입니다.

*   `st.set_page_config`로 UI 기본 설정을 하고, 사이드바에서 필터링 옵션과 API Key 설정을 처리합니다.

*   3개의 탭(대시보드, 상세 분석, 주가 추이)을 렌더링합니다.

*   **캐싱 전략**: `fetch_real_dashboard_data` 함수에서 매일 16시 기준의 JSON 파일을 확인하여 불필요한 크롤링을 방지합니다.

  

#### 2. `api/company_guide.py` (크롤링)

*   FnGuide(`comp.fnguide.com`)에서 기업별 스냅샷 및 재무비율을 스크래핑합니다.

*   `BeautifulSoup`를 사용하여 HTML을 파싱하며, 멀티스레딩(`concurrent.futures`)을 사용하여 300개 기업 데이터를 병렬로 빠르게 수집합니다.

  

#### 3. `api/opendart_client.py` (API 클라이언트)

*   `OpenDartReader` 라이브러리를 감싸서 사용하기 쉽게 만든 클래스입니다.

*   `get_financial_summary`: 재무상태표(BS)와 손익계산서(IS)에서 특정 계정(자산, 자본, 이익잉여금 등)만 추출하여 정리합니다.

  

---

  

## 3. 실행 방법 (How to Run)

  

### 방법 A: 간편 실행 (Windows)

제공된 배치 파일을 사용하면 파이썬 가상환경 생성부터 라이브러리 설치, 실행까지 자동으로 진행됩니다.

1.  탐색기에서 **`setup_and_run.bat`** 파일을 더블 클릭합니다.

2.  자동으로 브라우저가 열리며 앱이 실행됩니다.

  

### 방법 B: 수동 실행 (개발자 모드)

터미널(CMD 또는 PowerShell)에서 직접 실행하는 방법입니다.

  

1.  **프로젝트 폴더 이동**

    ```bash
    cd d:/01_Codes/ValueUp-2512.01
    ```

  

2.  **가상환경 생성 (최초 1회)**

    ```bash
    python -m venv venv
    ```

  

3.  **가상환경 활성화**

    *   Windows: `venv\Scripts\activate`

    *   Mac/Linux: `source venv/bin/activate`

  

4.  **필수 라이브러리 설치**

    ```bash
    pip install -r requirements.txt
    ```

  

5.  **애플리케이션 실행**

    ```bash
    streamlit run value-up.py
    ```

  

---

  

## 4. 필수 라이브러리 (Requirements)
 

`requirements.txt`에 명시된 주요 라이브러리와 용도는 다음과 같습니다.
  
| 라이브러리 | 용도 | 비고 |
| :--- | :--- | :--- |
| **streamlit** | 웹 UI 프레임워크 | 대시보드 화면 구성 |
| **pandas** | 데이터 처리 | 데이터프레임 조작 및 분석 |
| **numpy** | 수치 연산 | 데이터 계산 |
| **plotly** | 데이터 시각화 | 반응형 차트 (레이더 차트, 캔들 차트) |
| **finance-datareader**| 금융 데이터 수집 | KRX 상장 리스트, 주가 데이터 |
| **opendartreader** | OpenDart API 래퍼 | 금융감독원 전자공시 데이터 조회 |
| **requests** | HTTP 요청 | 정적 웹 페이지 크롤링 |
| **beautifulsoup4** | HTML 파싱 | 웹 크롤링 데이터 추출 |
| **cryptography** | 암호화 | API Key 로컬 보안 저장 (암호화) |
| **matplotlib** | 시각화 (보조) | `opendartreader` 등 내부 의존성 |

---

  

## 5. 초기 설정 및 주의사항

  

1.  **OpenDart API Key 발급**

    *   [Open DART](https://opendart.fss.or.kr/) 사이트에서 회원가입 후 API Key를 발급받아야 '개별 종목 정밀 진단' 기능을 사용할 수 있습니다.

    *   발급받은 키는 앱 실행 후 사이드바의 **[API 설정]** 메뉴에서 입력 및 저장합니다.

  

2.  **데이터 로딩 시간**

    *   최초 실행 시 '발굴 대시보드' 탭에서 300개 기업의 데이터를 크롤링하므로 약 **30~60초** 정도 소요될 수 있습니다.

    *   이후에는 캐시된 파일(`data/company_data_*.json`)을 사용하여 즉시 로딩됩니다.

  

3.  **크롤링 제한**

    *   `api/company_guide.py`는 FnGuide 사이트를 크롤링하므로, 너무 잦은 요청 시 차단될 수 있어 캐싱 시스템을 도입했습니다. (하루 1회 권장)
