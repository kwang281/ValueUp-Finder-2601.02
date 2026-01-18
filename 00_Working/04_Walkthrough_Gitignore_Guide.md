# Walkthrough: .gitignore GitHub 적용 가이드

## 1. 질문 답변: GitHub에서 설정이 필요한가요?
**아니요, GitHub 웹사이트에서 별도로 설정할 것은 없습니다.**

`.gitignore` 파일은 Git이라는 버전 관리 시스템 자체가 사용하는 **설정 파일**입니다. 
따라서 이 파일을 프로젝트에 포함시키고(`add`), 커밋(`commit`)하여 GitHub에 올리기만(`push`) 하면 자동으로 적용됩니다.

## 2. 적용을 위한 필수 단계
생성된 `.gitignore` 파일이 효력을 발휘하려면 다음 단계가 필요합니다.

### 2.1. 로컬 저장소 적용
파일을 생성하는 것만으로는 부족하며, Git이 이 파일의 존재를 알아야 합니다.
```bash
git add .gitignore
git commit -m "Add .gitignore file"
```

### 2.2. GitHub에 반영
```bash
git push origin <your-branch-name>
```
이제 팀원들이나 다른 컴퓨터에서 코드를 `pull` 받을 때, 이 규칙이 동일하게 적용됩니다.

---

## 3. 주의사항: 이미 파일이 올라가 버린 경우 (중요!)
`.gitignore`를 만들기 **전에** 이미 커밋되어 GitHub에 올라간 파일들은, 뒤늦게 `.gitignore`에 규칙을 추가해도 **자동으로 사라지지 않습니다.**

만약 무시하고 싶은 파일(예: `.env`, `__pycache__` 등)이 이미 GitHub에 올라가 있다면, 다음 명령어로 "Git의 추적 목록(Index)"에서만 제거해야 합니다.

### 캐시 삭제 및 재적용 방법
터미널에서 다음 명령어를 순서대로 실행하세요. (파일 자체는 삭제되지 않고, Git 추적에서만 빠집니다)

```bash
# 1. 모든 파일의 스테이징 해제 (실제 파일 삭제 X)
git rm -r --cached .

# 2. .gitignore 규칙에 따라 다시 스테이징
git add .

# 3. 변경사항 커밋
git commit -m "Apply .gitignore rules and remove ignored files from git cache"

# 4. GitHub로 푸시
git push origin <your-branch-name>
```

이렇게 하면 `.gitignore`에 정의된 파일들은 Git 추적에서 제외되고, GitHub 저장소에서도 사라집니다.
