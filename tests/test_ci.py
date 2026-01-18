import os
import sys
from utils.security import load_from_env

def test_secrets_loading():
    print("Testing Secrets Loading...")
    api_key = load_from_env()
    
    if api_key:
        # 보안을 위해 앞 4자리만 출력 (전체 출력 절대 금지)
        masked_key = api_key[:4] + "*" * (len(api_key)-4)
        print(f"SUCCESS: API Key loaded successfully! ({masked_key})")
    else:
        print("WARNING: API Key not found in environment variables.")
        # GitHub Actions에서 Secret 설정이 안되어 있어도 빌드는 성공하게 할지, 실패하게 할지 결정
        # 여기서는 경고만 하고 성공 처리 (Optional)
        
    print("Import 'value-up' module test...")
    try:
        # value-up.py는 streamlit 스크립트라 import 시 사이드 이펙트(st.set_page_config 등)가 있을 수 있음.
        # 단순 문법 체크(compile)만 수행
        with open("value-up.py", "r", encoding="utf-8") as f:
            compile(f.read(), "value-up.py", "exec")
        print("SUCCESS: Syntax check passed for 'value-up.py'")
    except Exception as e:
        print(f"FAILURE: Syntax error in 'value-up.py': {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_secrets_loading()
