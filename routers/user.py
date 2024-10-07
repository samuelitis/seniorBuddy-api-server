from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas import UserCreate, UserResponse, TokenResponse
import models
from database import get_db
from datetime import datetime, timedelta
import uuid
from utils import hash_password, validate_password_strength, is_valid_email, is_valid_phone, create_access_token, create_refresh_token, store_refresh_token, REFRESH_TOKEN_EXPIRE_DAYS

router = APIRouter()
### 사용자 관리 API ###

# 특정 사용자 조회 <관리용> 
@router.get("/info/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = models.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

### 사용자 정보 수정 API ###
@router.put("/update-info/{user_id}", response_model=UserResponse)
def update_user_info(user_id: int, user_update: UserResponse, db: Session = Depends(get_db)):
    user = models.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 업데이트할 정보가 있을 때만 수정
    # 무엇이 업데이트 되었는지 정보를 넘겨줄 필요가 있는지?
    # 넘겨줄 필요가 없다면 그냥 리턴만 해주면 됨
    if user_update.user_real_name is not None:
        user.user_real_name = user_update.user_real_name
    if user_update.phone_number is not None:
        user.phone_number = user_update.phone_number
    if user_update.email is not None:
        user.email = user_update.email
    
    db.commit()
    db.refresh(user)
    return user

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
# 일반 유저의 가입과 관리자, 기업용을 구별할 필요가 있음
# 만약 프론트에서 기업 가입자를 채택하지 않을 경우 삭제
@router.post("/register", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # 이메일 및 전화번호 형식 확인
    if not is_valid_email(user.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")
    if not is_valid_phone(user.phone_number):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number format")
    
    # 기존 유저 여부 확인
    existing_user = db.query(models.User).filter(models.User.phone_number == user.phone_number).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already registered")

    if user.email: 
        existing_email_user = db.query(models.User).filter(models.User.email == user.email).first()
        if existing_email_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # 비밀번호 유효성 검사 및 해싱
    validate_password_strength(user.password)
    hashed_password = hash_password(user.password)

    # 새 사용자 생성
    new_user = models.User(
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

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


#     oooooooooo.             oooo                .            
#     `888'   `Y8b            `888              .o8            
#      888      888  .ooooo.   888   .ooooo.  .o888oo  .ooooo. 
#      888      888 d88' `88b  888  d88' `88b   888   d88' `88b
#      888      888 888ooo888  888  888ooo888   888   888ooo888
#      888     d88' 888    .o  888  888    .o   888 . 888    .o
#     o888bood8P'   `Y8bod8P' o888o `Y8bod8P'   "888" `Y8bod8P'
# 사용자 삭제
@router.delete("/delete/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    deleted_user = models.delete_user(db, user_id)
    if not deleted_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}


#                                             .o8                                   
#     oooo d8b  .ooooo.   .oooo.o  .ooooo.  .o888oo      oo.ooooo.  oooo oooo    ooo
#     `888""8P d88' `88b d88(  "8 d88' `88b   888         888' `88b  `88. `88.  .8' 
#      888     888ooo888 `"Y88b.  888ooo888   888         888   888   `88..]88..8'  
#      888     888    .o o.  )88b 888    .o   888 .       888   888    `888'`888'   
#     d888b    `Y8bod8P' 8""888P' `Y8bod8P'   "888"       888bod8P'     `8'  `8'    
#                                                         888                       
#                                                        o888o                      
### 비밀번호 재설정 API ###

@router.post("/reset-password")
def reset_password(phone_number: str, new_password: str, db: Session = Depends(get_db)):
    user = models.get_user_by_phone(db, phone_number)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return {"message": "Password reset successful"}


#     ooooo                                          .    o8o                       
#     `888'                                        .o8    `"'                       
#      888          .ooooo.   .ooooo.   .oooo.   .o888oo oooo   .ooooo.  ooo. .oo.  
#      888         d88' `88b d88' `"Y8 `P  )88b    888   `888  d88' `88b `888P"Y88b 
#      888         888   888 888        .oP"888    888    888  888   888  888   888 
#      888       o 888   888 888   .o8 d8(  888    888 .  888  888   888  888   888 
#     o888ooooood8 `Y8bod8P' `Y8bod8P' `Y888""8o   "888" o888o `Y8bod8P' o888o o888o

### 경도와 위도 정보 업데이트 API ###

@router.put("/{user_id}/update-location")
def update_location(user_id: int, latitude: float, longitude: float, db: Session = Depends(get_db)):
    user = models.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.latitude = latitude
    user.longitude = longitude
    user.last_update_location = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return {"message": "Location updated successfully"}

