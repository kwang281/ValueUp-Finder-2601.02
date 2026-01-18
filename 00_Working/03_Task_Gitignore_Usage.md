# Task: .gitignore 적용 가이드 작성

## 1. 개요
사용자가 `.gitignore` 파일의 GitHub 적용 방법에 대해 문의하였습니다. 이에 대해 GitHub 웹사이트 설정이 아닌 Git 사용 흐름에서의 적용 방법을 설명하는 가이드를 작성합니다.

## 2. 목표
- GitHub 별도 설정이 필요 없음을 명확히 설명
- `.gitignore` 파일의 커밋 및 푸시 필요성 설명
- 이미 Git이 추적 중인 파일(Tracked files)에 뒤늦게 ignore 규칙을 적용하는 방법(`git rm --cached`) 안내

## 3. 구현 계획
1.  **가이드 문서 작성**: `00_Working/04_Walkthrough_Gitignore_Guide.md` 생성
    -   GitHub 설정 여부 (없음)
    -   적용 절차 (Commit & Push)
    -   캐시 삭제 방법 (Troubleshooting)
2.  **사용자 응답**: 문서 내용 요약 전달
