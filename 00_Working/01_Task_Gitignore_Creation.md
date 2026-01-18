# Task: .gitignore 파일 생성

## 1. 개요
사용자의 요청에 따라 일반적인 개발 환경(Python, Windows, macOS 등)과 IDE(VSCode 등)에서 발생하는 불필요한 파일들을 git 추적에서 제외하기 위한 `.gitignore` 파일을 생성합니다.

## 2. 목표
- Python 프로젝트에 필요한 표준 ignore 패턴 적용
- OS 시스템 파일 (Windows, macOS) 제외
- IDE 설정 파일 (VSCode, JetBrains 등) 제외
- 가상 환경 및 캐시 파일 제외

## 3. 구현 계획
1.  **파일 생성**: 프로젝트 루트 경로에 `.gitignore` 파일 생성 (현재 존재하지 않음 확인 완료)
2.  **내용 작성**:
    - **Python**: `__pycache__/`, `*.py[cod]`, `venv/`, `.env` 등
    - **OS**: `.DS_Store`, `Thumbs.db` 등
    - **IDE**: `.vscode/`, `.idea/` 등
3.  **검증**: 파일 생성 확인
