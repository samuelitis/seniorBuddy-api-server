from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
from utils import verify_password, create_access_token, create_refresh_token, get_user_from_token, revoke_refresh_token, get_valid_refresh_token, store_refresh_token
from pydantic import BaseModel
from database import get_db
from datetime import datetime, timedelta
from utils import REFRESH_TOKEN_EXPIRE_DAYS

router = APIRouter()

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class SeniorLoginData(BaseModel):
    phone_number: str
    password: str
    
class LoginData(BaseModel):
    user_id: str
    password: str
### JWT 인증 및 토큰 관리 API ###

# 로그인 ㅁ및 토큰 발급 (리프레시 토큰 저장)
@router.post("/token", response_model=TokenResponse)
def login_for_access_token(data: LoginData, db: Session = Depends(get_db)):
    user = models.get_user_by_phone(db, data.phone_number)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"sub": user.user_id})
    
    refresh_token = create_refresh_token({"sub": user.user_id})
    refresh_token_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # 리프레시 토큰 저장
    store_refresh_token(db, refresh_token, user.user_id, refresh_token_expires_at)
    
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

# 리프레시 토큰을 통한 액세스 토큰 재발급
@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    valid_token = get_valid_refresh_token(db, refresh_token)
    user_id = valid_token.user_id
    
    # 기존 리프레시 토큰 무효화
    revoke_refresh_token(db, refresh_token)
    
    user = models.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 새로운 토큰
    access_token = create_access_token({"sub": user.user_id})
    new_refresh_token = create_refresh_token({"sub": user.user_id})
    refresh_token_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    store_refresh_token(db, new_refresh_token, user.user_id, refresh_token_expires_at)
    
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


# 로그아웃
@router.post("/logout")
def logout(refresh_token: str, db: Session = Depends(get_db)):
    revoke_refresh_token(db, refresh_token) # 리프레쉬 토큰 무효화
    # 이후 어떤 추가처리가 필요한지?
    return {"message": "Logged out successfully"}

# 현재 로그인한 사용자 정보 조회
@router.get("/users/me")
def read_users_me(current_user: models.User = Depends(get_user_from_token)):
    return current_user