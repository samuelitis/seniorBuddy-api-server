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
@router.get("/dev/search/{user_id}", response_model=UserResponse) # 엔드포인트 우선순위 에러
def get_user(user_id: int, db: Session = Depends(get_db)):
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
    if user_update.user_real_name !=     None and user_update.user_real_name != "":
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
# 사용자 삭제
# 그저 삭제하는 것이 아니라 개인정보 및 사용정보들은 
# 다른 테이블로 이동을 시켜줘야하지않는지?
# 이런 부분은 어떻게 구현할지 고민해보아야함
# user id 말고 다른 정보로 삭제를 할 수 있어야하지 않을까?
@handle_exceptions
@router.delete("/me")
def delete_user(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()
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

@handle_exceptions
@router.post("/me/password")
def reset_password(new_password: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
    return {"message": "Location updated successfully"}

### 유저 프로필 API ###

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
    return {"message": "user's ai profile updated successfully"} 