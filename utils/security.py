import json
import os
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import streamlit as st

SECRETS_FILE = "secrets.json"

def _generate_key_from_pin(pin: str, salt: bytes) -> bytes:
    """PIN과 Salt를 사용하여 암호화 키를 생성합니다."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(pin.encode()))

def save_credentials(api_key: str, pin: str):
    """API Key를 PIN으로 암호화하여 저장합니다."""
    salt = os.urandom(16)
    key = _generate_key_from_pin(pin, salt)
    f = Fernet(key)
    
    encrypted_api_key = f.encrypt(api_key.encode())
    
    # PIN 검증을 위한 해시 저장 (Salted Hash)
    pin_salt = os.urandom(16)
    pin_hash = hashlib.pbkdf2_hmac('sha256', pin.encode(), pin_salt, 100000)
    
    data = {
        "salt": base64.b64encode(salt).decode('utf-8'),
        "encrypted_key": base64.b64encode(encrypted_api_key).decode('utf-8'),
        "pin_salt": base64.b64encode(pin_salt).decode('utf-8'),
        "pin_hash": base64.b64encode(pin_hash).decode('utf-8')
    }
    
    with open(SECRETS_FILE, "w") as file:
        json.dump(data, file)
        
    return True

def load_credentials(pin: str):
    """PIN을 사용하여 저장된 API Key를 복호화합니다."""
    if not os.path.exists(SECRETS_FILE):
        return None
        
    try:
        with open(SECRETS_FILE, "r") as file:
            data = json.load(file)
            
        salt = base64.b64decode(data["salt"])
        encrypted_key = base64.b64decode(data["encrypted_key"])
        
        # 입력된 PIN으로 키 생성 시도
        key = _generate_key_from_pin(pin, salt)
        f = Fernet(key)
        
        # 복호화 시도
        decrypted_api_key = f.decrypt(encrypted_key).decode()
        return decrypted_api_key
        
    except Exception:
        return None # 복호화 실패 (PIN 불일치 등)

def load_from_env():
    """환경 변수에서 API Key를 로드합니다 (GitHub Actions 등)."""
    return os.environ.get("OPENDART_API")

def check_credentials_exist():
    """자격 증명 파일이 존재하는지 확인합니다."""
    return os.path.exists(SECRETS_FILE)

def verify_pin(pin: str) -> bool:
    """PIN이 올바른지 확인합니다 (키 복호화 없이 검증만)."""
    if not os.path.exists(SECRETS_FILE):
        return False
        
    try:
        with open(SECRETS_FILE, "r") as file:
            data = json.load(file)
            
        pin_salt = base64.b64decode(data["pin_salt"])
        stored_hash = base64.b64decode(data["pin_hash"])
        
        # 입력된 PIN 해시 계산
        input_hash = hashlib.pbkdf2_hmac('sha256', pin.encode(), pin_salt, 100000)
        
        return input_hash == stored_hash
    except Exception:
        return False
