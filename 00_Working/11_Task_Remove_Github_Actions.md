# Task: GitHub Actions 관련 파일 및 코드 제거

## 1. 개요
사용자 요청에 따라 프로젝트 내에서 불필요해진 GitHub Actions 관련 설정 파일과 코드 내 언급을 모두 제거하였습니다.

## 2. 수행 내역
1.  **폴더 삭제**:
    -   `.github` (워크플로우 설정)
    -   `tests` (CI 테스트용 스크립트)
2.  **코드 정리 (`utils/security.py`)**:
    -   `load_from_env` 함수에서 `os.environ` 참조 로직 삭제.
    -   Streamlit Cloud의 `st.secrets`만 사용하도록 단순화.
    -   GitHub Actions 관련 주석 삭제.
3.  **코드 정리 (`value-up.py`)**:
    -   사이드바 메시지 변경: "시스템/환경변수" -> "Streamlit Secrets"
    -   주석 업데이트.

## 3. 결과
이제 프로젝트는 GitHub Actions CI에 의존하지 않으며, API Key 관리는 전적으로 **Streamlit Cloud Secrets** (배포 시) 또는 **로컬 암호화 파일** (로컬 실행 시)을 통해 이루어집니다.
