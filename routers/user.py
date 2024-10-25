from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session
from models import UserResponse, get_user_by_id, User
from database import get_db, handle_exceptions
from datetime import datetime
import uuid
from utils import hash_password, is_valid_phone, is_valid_email, get_current_user, token_manager

router = APIRouter()
### 사용자 관리 API ###

# 특정 사용자 조회 <관리용> 
@handle_exceptions
@router.get("/dev/search/{user_id}", response_model=UserResponse)
def get_user(admin_password: str, user_id: int, db: Session = Depends(get_db)):
    if admin_password is not "seniorbuddy-admin!":
        raise HTTPException(status_code=500, detail="알수없는 에러 발생")
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
    return user

# 사용자 정보 조회
@handle_exceptions
@router.get("/me", response_model=UserResponse)
def get_user_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user


### 사용자 정보 수정 API ###
@handle_exceptions
@router.put("/me", response_model=UserResponse)
def update_user_info(user_update: UserResponse, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_update.user_type != None and user_update.user_type != "":
        if user_update.user_type != "senior" and user_update.user_type != "guardian":
            raise HTTPException(status_code=400, detail="유저 타입은 'senior' 또는 'guardian'이어야 합니다.")
        user.user_type = user_update.user_type

    if user_update.user_real_name != None and user_update.user_real_name != "":
        user.user_real_name = user_update.user_real_name

    if user_update.phone_number != None and user_update.phone_number != "":
        if is_valid_phone(user_update.phone_number):
            user.phone_number = user_update.phone_number
        else:
            raise HTTPException(status_code=400, detail="전화번호 형식이 올바르지 않습니다.")
    if user_update.email != None and user_update.email != "":
        if is_valid_email(user_update.email):
            user.email = user_update.email
        else:
            raise HTTPException(status_code=400, detail="이메일 형식이 올바르지 않습니다.")
        
    
    db.commit()
    db.refresh(user)
    return user

#     oooooooooo.             oooo                .            
#     `888'   `Y8b            `888              .o8            
#      888      888  .ooooo.   888   .ooooo.  .o888oo  .ooooo. 
#      888      888 d88' `88b  888  d88' `88b   888   d88' `88b
#      888      888 888ooo888  888  888ooo888   888   888ooo888
#      888     d88' 888    .o  888  888    .o   888 . 888    .o
#     o888bood8P'   `Y8bod8P' o888o `Y8bod8P'   "888" `Y8bod8P'

@handle_exceptions
@router.delete("/me")
def delete_user(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()
    return {"message": "회원 정보를 삭제했습니다."}

#                                             .o8                                   
#     oooo d8b  .ooooo.   .oooo.o  .ooooo.  .o888oo      oo.ooooo.  oooo oooo    ooo
#     `888""8P d88' `88b d88(  "8 d88' `88b   888         888' `88b  `88. `88.  .8' 
#      888     888ooo888 `"Y88b.  888ooo888   888         888   888   `88..]88..8'  
#      888     888    .o o.  )88b 888    .o   888 .       888   888    `888'`888'   
#     d888b    `Y8bod8P' 8""888P' `Y8bod8P'   "888"       888bod8P'     `8'  `8'    
#                                                         888                       
#                                                        o888o                      
### 비밀번호 재설정 API ###

@handle_exceptions
@router.post("/me/password")
def reset_password(new_password: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)

    return {"message": "비밀번호를 변경했습니다."}

#     ooooo                                          .    o8o                       
#     `888'                                        .o8    `"'                       
#      888          .ooooo.   .ooooo.   .oooo.   .o888oo oooo   .ooooo.  ooo. .oo.  
#      888         d88' `88b d88' `"Y8 `P  )88b    888   `888  d88' `88b `888P"Y88b 
#      888         888   888 888        .oP"888    888    888  888   888  888   888 
#      888       o 888   888 888   .o8 d8(  888    888 .  888  888   888  888   888 
#     o888ooooood8 `Y8bod8P' `Y8bod8P' `Y888""8o   "888" o888o `Y8bod8P' o888o o888o

@handle_exceptions
@router.get("/me/location")
def get_location(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"latitude": user.latitude, "longitude": user.longitude}

@handle_exceptions
@router.put("/me/location")
def update_location(latitude: float, longitude: float, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.latitude = latitude
    user.longitude = longitude
    user.last_update_location = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return {"message": "위치 정보를 업데이트했습니다."}

#         .o.        .o8        .o8                        ooooooooo.                       .o88o.  o8o  oooo           
#        .888.      "888       "888                        `888   `Y88.                     888 `"  `"'  `888           
#       .8"888.      888oooo.   888oooo.  oooo    ooo       888   .d88' oooo d8b  .ooooo.  o888oo  oooo   888   .ooooo. 
#      .8' `888.     d88' `88b  d88' `88b  `88.  .8'        888ooo88P'  `888""8P d88' `88b  888    `888   888  d88' `88b
#     .88ooo8888.    888   888  888   888   `88..8'         888          888     888   888  888     888   888  888ooo888
#    .8'     `888.   888   888  888   888    `888'          888          888     888   888  888     888   888  888    .o
#   o88o     o8888o  `Y8bod8P'  `Y8bod8P'     .8'          o888o        d888b    `Y8bod8P' o888o   o888o o888o `Y8bod8P'
#                                         .o..P'                                                                        
#                                         `Y8P'                                                                         

@handle_exceptions
@router.get("/me/ai_profile")
def get_user_ai_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"profile_number" : user.ai_profile}

@handle_exceptions
@router.put("/me/ai_profile")
def change_user_ai_profile(image_num: int = 0, user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    user.ai_profile = image_num
    db.commit()
    db.refresh(user)
    return {"message": "사용자 프로필을 변경했습니다."}