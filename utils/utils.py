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
        raise HTTPException(status_code=400, detail="password length must be between 8 and 20 characters", headers={"X-Error": "password length must be between 8 and 20 characters"})

    if not re.match(r"^[A-Za-z0-9@$!%*?&#]+$", password):
        raise HTTPException(status_code=400, detail="password must contain only alphanumeric characters and special characters", headers={"X-Error": "password must contain only alphanumeric characters and special characters"})
    
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="password must contain at least one lowercase letter", headers={"X-Error": "password must contain at least one lowercase letter"})
    
    if not re.search(r"[0-9]", password):
        raise HTTPException(status_code=400, detail="password must contain at least one number", headers={"X-Error": "password must contain at least one number"})
    return True