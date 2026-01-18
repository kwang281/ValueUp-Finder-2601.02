# Task: Streamlit Secrets TOML 포맷 에러 해결 가이드

## 1. 개요
Streamlit Cloud의 Secrets 입력란은 **TOML**이라는 설정 파일 형식을 따릅니다. 
"Invalid format" 에러는 텍스트가 TOML 문법 규칙에 맞지 않을 때 발생합니다.

## 2. 해결 방법
가장 흔한 원인은 값(API Key) 주변에 **큰따옴표(")**가 없거나, 형식이 잘못된 경우입니다.

### 올바른 예시 (O) - 복사해서 사용하세요
```toml
OPENDART_API = "12345678abcdefg12345678abcdefg"
```
> **포인트:** 
> 1. 변수명(`OPENDART_API`)과 값 사이에 등호(`=`)가 있어야 함
> 2. 실제 키 값은 반드시 **큰따옴표("")**로 감싸져야 함

### 자주 하는 실수 (X)
*   `OPENDART_API = 12345abcdef` (따옴표 없음 ❌)
*   `OPENDART_API: "12345abcdef"` (등호 대신 콜론 사용 ❌ - 이건 YAML 방식입니다)
*   `"OPENDART_API" = 12345abcdef` (키에도 따옴표는 가능하지만 값에 따옴표가 중요)
*   `12345678abcdef` (키 없이 값만 입력 ❌)

## 3. 조치 단계
1.  Streamlit Cloud > App Settings > Secrets 탭으로 이동합니다.
2.  입력창의 내용을 모두 지웁니다.
3.  위의 **[올바른 예시]**를 복사하여 붙여넣습니다.
4.  따옴표 안의 내용을 본인의 실제 API Key로 변경합니다. (따옴표는 지우지 마세요!)
5.  Save 버튼을 누릅니다.
