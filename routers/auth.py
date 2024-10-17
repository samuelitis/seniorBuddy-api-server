from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import RefreshToken, User, UserCreate, UserResponse, TokenResponse, LoginData, RegisterResponse, get_user_by_id
from utils import verify_password, is_valid_phone, is_valid_email, validate_password_strength, hash_password
from database import get_db
from datetime import datetime, timedelta
from jose import jwt, ExpiredSignatureError, JWTError
from utils.config import variables
from utils import token_manager, get_current_user
import uuid


router = APIRouter()

### JWT 인증 및 토큰 관리 API ###


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
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # 이메일 및 전화번호 형식 확인
        if user.email is not None and not is_valid_email(user.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format", headers={"X-Error": "Invalid email format"})
        if not is_valid_phone(user.phone_number):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number format", headers={"X-Error": "Invalid phone number format"})
        
        existing_user = db.query(User).filter(User.phone_number == user.phone_number).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already registered", headers={"X-Error": "Phone number already registered"})

        if user.email:
            existing_email_user = db.query(User).filter(User.email == user.email).first()
            if existing_email_user:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered", headers={"X-Error": "Email already registered"})

        if not validate_password_strength(user.password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password strength", headers={"X-Error": "Invalid password strength"})
        
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

        access_token = token_manager.create_access_token(new_user.user_id)
        refresh_token = token_manager.create_refresh_token(new_user.user_id)

        token_manager.store_refresh_token(db, refresh_token, new_user.user_id)

        return RegisterResponse(
            user_real_name=new_user.user_real_name,
            user_type=new_user.user_type,
            phone_number=new_user.phone_number,
            access_token=access_token,
            refresh_token=refresh_token
        )
    except HTTPException as e:
        db.rollback()
        raise e
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"User register failed: {str(e)}", headers={"X-Error": f"User register failed: {str(e)}"})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
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
def login(data: LoginData, db: Session = Depends(get_db)):
    user = None

    if is_valid_email(data.identifier):     # 이메일로 로그인 시
        user = db.query(User).filter(User.email == data.identifier).first()
    elif is_valid_phone(data.identifier):   # 전화번호로 로그인 시
        user = db.query(User).filter(User.phone_number == data.identifier).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found", headers={"X-Error": "User not found"})
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password", headers={"X-Error": "Incorrect password"})

    # 기존 리프레시 토큰 무효화
    existing_refresh_token = db.query(RefreshToken).filter(RefreshToken.user_id == user.user_id).first()
    if existing_refresh_token:
        return TokenResponse(access_token=token_manager.create_access_token(user.user_id),
                            refresh_token=existing_refresh_token.token)

    # 새로운 액세스 토큰 및 리프레시 토큰 발급
    access_token = token_manager.create_access_token(user.user_id)
    refresh_token = token_manager.create_refresh_token(user.user_id)

    # 리프레시 토큰 저장
    token_manager.store_refresh_token(db, refresh_token, user.user_id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh")
def refresh(access_token: str = Header(None), refresh_token: str = Header(None), db: Session = Depends(get_db)):
    if not access_token or not refresh_token:
        raise HTTPException(status_code=400, detail="Access or refresh token missing", headers={"X-Error": "Access or refresh token missing"})

    try:
        access_payload = token_manager.decode_token(access_token, refresh=True)
        user_id = access_payload.get("sub")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid access token", headers={"X-Error": "Invalid access token"})


    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid access token", headers={"X-Error": "Invalid access token"})
        # 보안적인 이유로 인해 더 많은 정보를 제공하지 않음
        # 예외 추가 X
        # 아래의 토큰 미일치도 안넣는게 좋을 수 있으나
        # NextJS에서 필요할 수 있으므로 넣어둠


    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found", headers={"X-Error": "User not found"})

    valid_refresh_token = token_manager.get_valid_refresh_token(db, refresh_token)
    
    if valid_refresh_token.user_id != user.user_id:
        raise HTTPException(status_code=401, detail="Refresh token does not match user", headers={"X-Error": "Refresh token does not match user"})

    new_access_token = token_manager.create_access_token(user.user_id)
    new_refresh_token = token_manager.create_refresh_token(user.user_id)

    token_manager.del_refresh_token(db, refresh_token)
    
    token_manager.store_refresh_token(db, new_refresh_token, user.user_id)

    return {"access_token": new_access_token, "refresh_token": new_refresh_token}


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
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    refresh_token = db.query(RefreshToken).filter(RefreshToken.user_id == user.user_id).first()
    
    if not refresh_token:
        raise HTTPException(status_code=404, detail="Refresh token not found", headers={"X-Error": "Refresh token not found"})
    
    token_manager.del_refresh_token(db, refresh_token.token)

    return JSONResponse(content={"message": "Logged out successfully"})