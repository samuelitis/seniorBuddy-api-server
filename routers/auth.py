from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from urllib.parse import unquote
from sqlalchemy.exc import SQLAlchemyError
from models import RefreshToken, User, UserCreate, UserResponse, TokenResponse, LoginData, RegisterResponse, UserSchedule
from utils import verify_password, is_valid_phone, is_valid_email, validate_password_strength, hash_password
from database import get_db, handle_exceptions
from datetime import datetime, time
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
@handle_exceptions
@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if user.user_type == "senior" and user.phone_number == None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="전화번호를 입력해주세요")
    if user.user_type == "guardian" and user.email == None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이메일을 입력해주세요")
    if user.email == None and user.phone_number == None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 혹은 전화번호를 입력해주세요")
    # 이메일 및 전화번호 형식 확인
    if user.email != None and not is_valid_email(user.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 형식이 올바르지 않습니다")
    if user.phone_number != None and not is_valid_phone(user.phone_number):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="전화번호 형식이 올바르지 않습니다")
    
    existing_user = db.query(User).filter(User.phone_number == user.phone_number).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="전화번호가 이미 등록되어 있습니다")

    if user.email:
        existing_email_user = db.query(User).filter(User.email == user.email).first()
        if existing_email_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이메일이 이미 등록되어 있습니다")

    if not validate_password_strength(user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="비밀번호는 8자 이상이어야 하며, 영문, 숫자, 특수문자를 포함해야 합니다")
    
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
    init_meal_time(db, user.user_id)

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
@handle_exceptions
@router.post("/login", response_model=TokenResponse)
def login(data: LoginData, db: Session = Depends(get_db)):
    user = None
    if is_valid_email(data.identifier):     # 이메일로 로그인 시
        user = db.query(User).filter(User.email == data.identifier).first()
    elif is_valid_phone(data.identifier):   # 전화번호로 로그인 시
        user = db.query(User).filter(User.phone_number == data.identifier).first()

    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다")

    if data.fcm_token is not None:
        store_fcm_token(user, data.fcm_token, db)

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


def init_meal_time(db: Session, user_id):
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if user_id is None:
            return {"status": "failed", "message": "사용자 정보가 없습니다."}
        
        new_schedule = UserSchedule(
            user_id = user.user_id,
            morning_time = time(7, 0),
            breakfast_time = time(8, 0),
            lunch_time = time(12, 0),
            dinner_time = time(18, 0),
            bedtime_time = time(22, 0)
        )
        db.add(new_schedule)
        db.commit()
        db.refresh(new_schedule)
        return new_schedule
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}

def store_fcm_token(user: User, fcm_token: str, db: Session):
    try:
        user.fcm_token = unquote(fcm_token)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="FCM 토큰 저장 중 오류가 발생했습니다")
#    ooooooooo.              .o88o.                             oooo       
#    `888   `Y88.            888 `"                             `888       
#     888   .d88'  .ooooo.  o888oo  oooo d8b  .ooooo.   .oooo.o  888 .oo.  
#     888ooo88P'  d88' `88b  888    `888""8P d88' `88b d88(  "8  888P"Y88b 
#     888`88b.    888ooo888  888     888     888ooo888 `"Y88b.   888   888 
#     888  `88b.  888    .o  888     888     888    .o o.  )88b  888   888 
#    o888o  o888o `Y8bod8P' o888o   d888b    `Y8bod8P' 8""888P' o888o o888o

@handle_exceptions
@router.post("/refresh")
def refresh(access_token: str = Header(None), refresh_token: str = Header(None), db: Session = Depends(get_db)):
    if not access_token or not refresh_token:
        raise HTTPException(status_code=400, detail="토큰이 누락되었습니다")

    try:
        access_payload = token_manager.decode_token(access_token, refresh=True)
        user_id = access_payload.get("sub")
    except Exception as e:
        raise HTTPException(status_code=401, detail="토근이 유효하지 않습니다")


    if not user_id:
        raise HTTPException(status_code=401, detail="토근이 유효하지 않습니다")
        # 보안적인 이유로 인해 더 많은 정보를 제공하지 않음
        # 예외 추가 X
        # 아래의 토큰 미일치도 안넣는게 좋을 수 있으나
        # NextJS에서 필요할 수 있으므로 넣어둠


    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다")

    valid_refresh_token = token_manager.get_valid_refresh_token(db, refresh_token)
    
    if valid_refresh_token.user_id != user.user_id:
        raise HTTPException(status_code=401, detail="토근이 유효하지 않습니다")

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
@handle_exceptions
@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    refresh_token = db.query(RefreshToken).filter(RefreshToken.user_id == user.user_id).first()
    
    if not refresh_token:
        raise HTTPException(status_code=404, detail="리프레시 토큰을 찾을 수 없습니다")
    
    token_manager.del_refresh_token(db, refresh_token.token)

    return JSONResponse(content={"message": "로그아웃 되었습니다"})