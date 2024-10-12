import os, re
from jose import jwt, JWTError, ExpiredSignatureError
from re import search, match
from passlib.context import CryptContext
from datetime import datetime, timedelta
from fastapi import Header, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from database import get_db
from models import User, RefreshToken
from utils.config import Config

SECRET_KEY = Config.HASH_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

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


# JWT 토큰 생성 함수 (액세스 토큰)
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# JWT 토큰 생성 함수 (리프레시 토큰)
def create_refresh_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# JWT 토큰 디코딩 (검증 및 사용자 추출)
def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# JWT 토큰을 가져와서 사용자 정보 확인
def get_user_from_token(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization[len("Bearer "):]
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    except jwt.ExpiredSignatureError:
        # 토큰 만료 시 리프레시 토큰으로 재발행 절차를 처리
        raise HTTPException(status_code=401, detail="Token expired, please refresh")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

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

# 액세스 토큰 유효성 검사 및 갱신
# 로직 맞는지 확인할것
def check_access_token(request: Request, db: Session = Depends(get_db)):
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    access_token = authorization[len("Bearer "):]

    try:
        # 액세스 토큰 유효성 검사
        payload = decode_token(access_token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # 유효한 액세스 토큰이면 유저 반환
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    except ExpiredSignatureError:
        # 액세스 토큰 만료 -> 리프레시 토큰으로 갱신
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token missing")

        # 리프레시 토큰 유효성 검사
        valid_refresh_token = get_valid_refresh_token(db, refresh_token)
        user_id = valid_refresh_token.user_id

        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 새로운 액세스 토큰 및 리프레시 토큰 발급
        new_access_token = create_access_token({"sub": user.user_id})
        new_refresh_token = create_refresh_token({"sub": user.user_id})
        refresh_token_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        # 새 리프레시 토큰 저장
        store_refresh_token(db, new_refresh_token, user.user_id, refresh_token_expires_at)

        # 새로운 토큰 반환
        return {"access_token": new_access_token, "refresh_token": new_refresh_token}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
# 기존 리프레시 토큰 무효화 함수
def revoke_refresh_token(db: Session, token: str):
    refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if refresh_token:
        db.delete(refresh_token)
        db.commit()

# 리프레시 토큰 저장 함수
def store_refresh_token(db: Session, token: str, user_id: int, expires_at: datetime):
    refresh_token = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    return refresh_token

# 리프레시 토큰 조회 및 검증 함수
def get_valid_refresh_token(db: Session, token: str):
    refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if refresh_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    return refresh_token