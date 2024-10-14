import os, re
from passlib.context import CryptContext
from fastapi import HTTPException
from utils.config import variables

SECRET_KEY = variables.HASH_KEY

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 비밀번호 해싱 함수
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# 비밀번호 검증 함수
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def is_valid_email(email: str) -> bool:
    email_regex = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    return re.match(email_regex, email) is not None

def is_valid_phone(phone_number: str) -> bool:
    phone_regex = re.compile(r'^\d{2,3}-\d{3,4}-\d{4}$')
    return re.match(phone_regex, phone_number) is not None

# 비밀번호 강도 확인 함수 (특수문자, 영어 대소문자, 숫자만 허용)
def validate_password_strength(password: str):
    if len(password) < 8 or len(password) > 20:
        raise HTTPException(status_code=400, detail="비밀번호는 8자에서 20자 사이여야 합니다.")
    
    # 영어 대문자, 소문자, 숫자, 특수문자만 포함되었는지 확인
    if not re.match(r"^[A-Za-z0-9@$!%*?&#]+$", password):
        raise HTTPException(status_code=400, detail="비밀번호는 영문자, 숫자, 특수 문자로만 구성할 수 있습니다: @$!%*?&#")
    
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="비밀번호에는 하나 이상의 소문자가 포함되어야 합니다.")
    
    if not re.search(r"[0-9]", password):
        raise HTTPException(status_code=400, detail="비밀번호에는 하나 이상의 숫자가 포함되어야 합니다.")
    return True