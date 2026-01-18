# Task: Secrets 관리 로직 개선 및 GitHub Actions CI 수정

## 1. 개요
Streamlit Cloud와 GitHub Actions 환경 모두에서 안전하게 API Key를 로드할 수 있도록 로직을 개선하고, 잘못 작성된 GitHub Actions 워크플로우를 수정합니다.

## 2. 문제점 및 해결 방안

### A. Secrets 로딩 로직 개선 (`utils/security.py`)
- **문제**: 현재 `load_from_env`는 `os.environ`만 확인합니다. Streamlit Cloud는 `st.secrets`를 사용하는 것이 표준입니다.
- **해결**: `st.secrets`를 우선 확인하고, 없으면 `os.environ`을 확인하도록 순위를 변경합니다.

### B. GitHub Actions 수정 (`.github/workflows/deploy.yml`)
- **문제**: `streamlit run value-up.py` 명령은 서버를 실행하고 무한 대기하므로, CI 빌드가 끝나지 않고 타임아웃됩니다.
- **해결**: 실제 앱 실행 대신, 구문 오류(Syntax Error)를 체크하거나 간단한 실행 테스트(Dry Run)로 대체해야 합니다. 여기서는 의존성 설치 및 기본 임포트 테스트로 변경합니다.

### C. Streamlit Cloud 연동 가이드
- GitHub Repository Secrets는 Streamlit Cloud로 자동 전달되지 않음을 사용자에게 알려야 합니다.
- Streamlit Cloud 설정 페이지에서 Secrets를 입력해야 함을 명시하는 문서를 작성합니다.

## 3. 구현 계획
1.  `utils/security.py`: `load_from_env` 수정 (`st.secrets` 지원)
2.  In `value-up.py`, ensure API key loading via `load_from_env` is prioritized or integrated properly. (Checking usage in line 27/main)
3.  `.github/workflows/deploy.yml`: `streamlit run` 제거, `python -c "import value-up"` 또는 린트 체크로 변경.
4.  문서 작성: "GitHub Secrets와 Streamlit Cloud Secrets 설정 가이드"
