# Walkthrough: Streamlit Cloud 및 GitHub Actions 비밀키 연동 가이드

## 1. 개요
Streamlit Cloud와 GitHub Actions에서 API Key(`OPENDART_API`)를 안전하게 사용하는 방법을 안내합니다. 
GitHub Repository Secret 설정만으로는 Streamlit Cloud 앱에 키가 전달되지 않으므로, **두 곳 모두 설정이 필요합니다.**

---

## 2. GitHub Actions (CI/테스트용) 설정
GitHub 웹사이트에서 설정합니다. 이 설정은 코드가 푸시될 때 자동으로 실행되는 테스트(CI)에서 API Key를 사용하기 위함입니다.

1.  GitHub 저장소 이동 -> **Settings** 클릭
2.  왼쪽 메뉴 **Secrets and variables** -> **Actions** 선택
3.  **New repository secret** 버튼 클릭
4.  정보 입력:
    *   **Name**: `OPENDART_API`
    *   **Secret**: (발급받은 실제 OpenDart API Key)
5.  **Add secret** 클릭하여 저장.

---

## 3. Streamlit Cloud (실제 배포용) 설정 (필수!)
실제 배포된 웹사이트에서 API Key가 동작하려면 **반드시 이곳에 설정해야 합니다.**

1.  [Streamlit Cloud 대시보드](https://share.streamlit.io/) 접속
2.  해당 앱(App)의 오른쪽 점 3개 메뉴 -> **Settings** 클릭
3.  **Secrets** 탭 클릭
4.  아래와 같이 TOML 형식으로 입력:
    ```toml
    OPENDART_API = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    ```
    *(따옴표 안에 실제 키를 입력하세요)*
5.  **Save** 버튼 클릭. (앱이 자동으로 재시작되며 적용됩니다)

---

## 4. 코드 변경 사항 요약
이번 작업을 통해 코드가 다음과 같이 개선되었습니다:

1.  **`utils/security.py`**:
    *   기존에는 로컬 파일이나 환경변수만 확인했으나, 이제 **Streamlit Secrets (`st.secrets`)를 최우선으로 확인**합니다.
    *   따라서 Streamlit Cloud에 배포되면 자동으로 위에서 설정한 TOML 설정값을 읽어옵니다.

2.  **GitHub Workflow (`deploy.yml`)**:
    *   기존의 `streamlit run` (무한 대기) 명령을 제거했습니다.
    *   대신, API Key가 올바르게 설정되었는지 확인하고 코 문법을 검사하는 테스트 스크립트(`tests/test_ci.py`)를 실행합니다.
    *   이제 커밋을 푸시할 때마다 GitHub Actions 탭에서 "초록색 체크(성공)"를 볼 수 있습니다.
