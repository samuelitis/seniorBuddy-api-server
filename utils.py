import os
import jwt
from re import search, match
from passlib.context import CryptContext
from datetime import datetime, timedelta
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, RefreshToken

SECRET_KEY = os.getenv("HASH_KEY")
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
    payload = decode_token(token)
    user_id = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

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

# 기존 리프레시 토큰 무효화 함수
def revoke_refresh_token(db: Session, token: str):
    refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if refresh_token:
        db.delete(refresh_token)
        db.commit()


# 비밀번호 강도 확인 함수 (특수문자, 영어 대소문자, 숫자만 허용)
def validate_password_strength(password: str):
    # 비밀번호 최소 길이 8자 확인
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")
    
    # 영어 대문자, 소문자, 숫자, 특수문자만 포함되었는지 확인
    if not match(r"^[A-Za-z0-9@$!%*?&#]+$", password):
        raise HTTPException(status_code=400, detail="Password can only contain letters, numbers, and special characters: @$!%*?&#")
    
    # 대문자, 소문자, 숫자, 특수문자가 모두 포함되었는지 확인
    if not search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter.")
    
    if not search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter.")
    
    if not search(r"[0-9]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number.")
    
    if not search(r"[@$!%*?&#]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character: @$!%*?&#")