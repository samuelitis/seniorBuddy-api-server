from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
import models
from utils import verify_password, create_access_token, create_refresh_token, get_user_from_token, revoke_refresh_token, get_valid_refresh_token, store_refresh_token, is_valid_phone, is_valid_email
from pydantic import BaseModel
from database import get_db
from datetime import datetime, timedelta
from utils import REFRESH_TOKEN_EXPIRE_DAYS
from schemas import TokenResponse, LoginData

router = APIRouter()

### JWT 인증 및 토큰 관리 API ###

#     ooooooooo.              .o88o.                             oooo       
#     `888   `Y88.            888 `"                             `888       
#      888   .d88'  .ooooo.  o888oo  oooo d8b  .ooooo.   .oooo.o  888 .oo.  
#      888ooo88P'  d88' `88b  888    `888""8P d88' `88b d88(  "8  888P"Y88b 
#      888`88b.    888ooo888  888     888     888ooo888 `"Y88b.   888   888 
#      888  `88b.  888    .o  888     888     888    .o o.  )88b  888   888 
#     o888o  o888o `Y8bod8P' o888o   d888b    `Y8bod8P' 8""888P' o888o o888o

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
    
    # 새로운 토큰 생성
    access_token = create_access_token({"sub": user.user_id})
    new_refresh_token = create_refresh_token({"sub": user.user_id})
    refresh_token_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    store_refresh_token(db, new_refresh_token, user.user_id, refresh_token_expires_at)
    
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)




#    
#     .oooooo..o  o8o                               o8o             
#     d8P'    `Y8  `"'                               `"'             
#     Y88bo.      oooo   .oooooooo ooo. .oo.        oooo  ooo. .oo.  
#      `"Y8888o.  `888  888' `88b  `888P"Y88b       `888  `888P"Y88b 
#          `"Y88b  888  888   888   888   888        888   888   888 
#     oo     .d8P  888  `88bod8P'   888   888        888   888   888 
#     8""88888P'  o888o `8oooooo.  o888o o888o      o888o o888o o888o
#                       d"     YD                                    
#                       "Y88888P'                                    

# 로그인 및 토큰 발급 (리프레시 토큰 저장)
@router.post("/login", response_model=TokenResponse)
def login_for_access_token(data: LoginData, db: Session = Depends(get_db)):
    user = None

    if is_valid_email(data.identifier):  # 이메일로 로그인 시 일반 유저만
        user = db.query(models.User).filter(
            models.User.email == data.identifier,
            models.User.user_type != models.UserType.senior
        ).first()
    elif is_valid_phone(data.identifier):  # 전화번호로 로그인 시 시니어 유저만
        user = db.query(models.User).filter(
            models.User.phone_number == data.identifier,
            models.User.user_type == models.UserType.senior
        ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")

    existing_refresh_token = get_valid_refresh_token(db, user.user_id)

    # Refresh Token Rotation 적용: 기존 토큰이 유효해도 새로운 리프레시 토큰 발급
    if existing_refresh_token:
        revoke_refresh_token(db, existing_refresh_token.token)

    # 새로운 토큰 발급
    access_token = create_access_token({"sub": user.user_id})
    refresh_token = create_refresh_token({"sub": user.user_id})
    refresh_token_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    # 새로운 Refresh Token 저장
    store_refresh_token(db, refresh_token, user.user_id, refresh_token_expires_at)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


#    .oooooo..o  o8o                                                        .  
#   d8P'    `Y8  `"'                                                      .o8  
#   Y88bo.      oooo   .oooooooo ooo. .oo.         .ooooo.  oooo  oooo  .o888oo
#    `"Y8888o.  `888  888' `88b  `888P"Y88b       d88' `88b `888  `888    888  
#        `"Y88b  888  888   888   888   888       888   888  888   888    888  
#   oo     .d8P  888  `88bod8P'   888   888       888   888  888   888    888 .
#   8""88888P'  o888o `8oooooo.  o888o o888o      `Y8bod8P'  `V88V"V8P'   "888"
#                    d"     YD                                                
#                    "Y88888P'                                                

# 로그아웃
@router.post("/logout")
def logout(refresh_token: str, db: Session = Depends(get_db)):
    revoke_refresh_token(db, refresh_token)

    # 로그아웃 성공 응답
    # 해당 부분은 NextJS 에서 쿠키 삭제를 하도록 해야함
    return JSONResponse(content={"message": "Logged out successfully"})