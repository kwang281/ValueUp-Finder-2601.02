# Task: OpenDartClient 초기화 버그 수정

## 1. 문제점 분석 (Bug Analysis)
`api/opendart_client.py` 파일의 `OpenDartClient` 클래스 초기화(`__init__`) 과정에서 잠재적인 `AttributeError`가 발견되었습니다.
- **현상**: `OpenDartReader` 객체 생성 실패 시(예: API Key 오류), `self.dart` 변수가 정의되지 않은 상태로 남습니다.
- **결과**: 이후 `get_financial_summary` 등의 메서드에서 `if not self.dart:` 접근 시 `AttributeError: 'OpenDartClient' object has no attribute 'dart'` 에러가 발생하여 프로그램이 비정상 종료될 위험이 있습니다.

## 2. 해결 방안 (Solution)
- `__init__` 메서드 시작 부분에 `self.dart = None`을 명시하여, 예외 발생 여부와 관계없이 속성이 항상 존재하도록 보장합니다.

## 3. 구현 계획
1.  **대상 파일**: `e:\GDrive\00_PrivateShare\02_Github_repository\ValueUp-Finder-2601.02\api\opendart_client.py`
2.  **수정 내용**: `__init__` 메서드 수정

```python
    def __init__(self, api_key):
        self.api_key = api_key
        self.init_error = None
        self.dart = None  # [Fix] 초기화 추가
        
        if api_key:
            try:
                self.dart = OpenDartReader(api_key)
            except Exception as e:
                self.init_error = str(e)
                print(f"Error initializing OpenDartReader: {e}")
```
