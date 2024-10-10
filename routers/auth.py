from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models import RefreshToken, User, UserType, UserCreate, UserResponse, TokenResponse, LoginData, RegisterResponse, get_user_by_id
from utils import verify_password, create_access_token, create_refresh_token, get_user_from_token, is_valid_phone, is_valid_email, validate_password_strength, hash_password
from database import get_db
from datetime import datetime, timedelta
from utils import REFRESH_TOKEN_EXPIRE_DAYS
import uuid

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
    
    revoke_refresh_token(db, refresh_token)
    
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    access_token = create_access_token({"sub": user.user_id})
    new_refresh_token = create_refresh_token({"sub": user.user_id})
    refresh_token_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    store_refresh_token(db, new_refresh_token, user.user_id, refresh_token_expires_at)
    
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)



#      .oooooo..o  o8o                                                    
#     d8P'    `Y8  `"'                                                    
#     Y88bo.      oooo   .oooooooo ooo. .oo.        oooo  oooo  oo.ooooo. 
#      `"Y8888o.  `888  888' `88b  `888P"Y88b       `888  `888   888' `88b
#          `"Y88b  888  888   888   888   888        888   888   888   888
#     oo     .d8P  888  `88bod8P'   888   888        888   888   888   888
#     8""88888P'  o888o `8oooooo.  o888o o888o       `V88V"V8P'  888bod8P'
#                       d"     YD                                888      
#                       "Y88888P'                               o888o     
# 사용자 생성 API
@router.post("/register", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # 이메일 및 전화번호 형식 확인
    if not is_valid_email(user.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")
    if not is_valid_phone(user.phone_number):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number format")
    
    existing_user = db.query(User).filter(User.phone_number == user.phone_number).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already registered")

    if user.email:
        existing_email_user = db.query(User).filter(User.email == user.email).first()
        if existing_email_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    if not validate_password_strength(user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password strength")
    hashed_password = hash_password(user.password)

    new_user = User(
        user_uuid=str(uuid.uuid4()),
        user_real_name=user.user_real_name,
        password_hash=hashed_password,
        phone_number=user.phone_number,
        user_type=user.user_type,
        email=user.email,
        created_at=datetime.utcnow(),
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # JWT 토큰 생성 (액세스 토큰 및 리프레시 토큰)
    access_token = create_access_token({"sub": new_user.user_id})
    refresh_token = create_refresh_token({"sub": new_user.user_id})
    refresh_token_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    # 리프레시 토큰 저장
    store_refresh_token(db, refresh_token, new_user.user_id, refresh_token_expires_at)

    return RegisterResponse(
        user_real_name=new_user.user_real_name,
        user_type=new_user.user_type,
        phone_number=new_user.phone_number,
        access_token=access_token,
        refresh_token=refresh_token
    )


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
        user = db.query(User).filter(
            User.email == data.identifier,
            User.user_type != UserType.senior
        ).first()
    elif is_valid_phone(data.identifier):  # 전화번호로 로그인 시 시니어 유저만
        user = db.query(User).filter(
            User.phone_number == data.identifier,
            User.user_type == UserType.senior
        ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")

    existing_refresh_token = get_valid_refresh_token(db, user.user_id)

    # Refresh Token Rotation 적용: 기존 토큰이 유효해도 새로운 리프레시 토큰 발급
    if existing_refresh_token:
        revoke_refresh_token(db, existing_refresh_token.token)

    access_token = create_access_token({"sub": user.user_id})
    refresh_token = create_refresh_token({"sub": user.user_id})
    refresh_token_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

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