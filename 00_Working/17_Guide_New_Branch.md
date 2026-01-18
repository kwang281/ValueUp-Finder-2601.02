# 가이드: 새로운 개발 작업을 위한 Git 브랜치 전략

## 1. 개요
현재의 **안정된 버전(Main)** 은 그대로 유지하면서, 이 코드를 기반으로 **새로운 기능(예: 아키텍처 변경, Git Scraping 도입 등)** 을 개발하는 가장 안전하고 표준적인 방법은 **Git 브랜치(Branch)** 를 사용하는 것입니다.

## 2. 왜 브랜치인가요?
- **안전함**: `main` 브랜치는 건드리지 않으므로, 언제든지 현재 상태로 돌아올 수 있습니다.
- **자유로움**: 새로운 브랜치에서는 코드를 마음껏 망가뜨리고 수정해도 기존 서비스에 영향을 주지 않습니다.
- **병합 가능**: 작업이 성공적으로 끝나면, 나중에 `main`과 합칠 수 있습니다.

## 3. 실행 단계

### 1단계: 현재 상태 저장 (Main)
먼저 지금의 작업물을 `main` 브랜치에 확실히 저장해 둡니다.
```bash
git add .
git commit -m "Finish v1 cleanup: Ready for next version"
git push origin main
```

### 2단계: 새 브랜치 생성 및 이동
새로운 작업 공간(브랜치)을 만들고 그쪽으로 넘어갑니다. 이름은 `v2-upgrade`로 하겠습니다.
```bash
# 브랜치 생성하고 이동 (checkout -b)
git checkout -b v2-upgrade
```
이제 터미널 프롬프트나 VS Code 왼쪽 하단에 `main` 대신 `v2-upgrade`라고 뜰 것입니다.

### 3단계: 작업 및 저장
이제 마음껏 코드를 수정하세요. 작업을 저장할 때는 똑같이 하시면 됩니다.
```bash
git add .
git commit -m "Start implementing new scraping architecture"
# 새 브랜치를 GitHub에도 올리기
git push origin v2-upgrade
```

## 4. 나중에 원복하고 싶다면?
혹시 새 작업이 마음에 안 들어서 예전으로 돌아가고 싶다면:
```bash
git checkout main
```
이 명령어 한 번이면 모든 파일이 작업 전 상태로 싹 돌아옵니다.
