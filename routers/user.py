from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import UserCreate, UserResponse, TokenResponse, get_user_by_id, get_user_by_phone, del_user
from database import get_db
from datetime import datetime, timedelta
import uuid
from utils import hash_password, is_valid_phone, is_valid_email, REFRESH_TOKEN_EXPIRE_DAYS

router = APIRouter()
### 사용자 관리 API ###

# 특정 사용자 조회 <관리용> 
@router.get("/info/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

### 사용자 정보 수정 API ###
@router.put("/update-info/{user_id}", response_model=UserResponse)
def update_user_info(user_id: int, user_update: UserResponse, db: Session = Depends(get_db)):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 업데이트할 정보가 있을 때만 수정
    # 무엇이 업데이트 되었는지 정보를 넘겨줄 필요가 있는지?
    # 넘겨줄 필요가 없다면 그냥 리턴만 해주면 됨
    if user_update.user_real_name is not None or user_update.user_real_name is "":
        user.user_real_name = user_update.user_real_name
    if user_update.phone_number is not None or user_update.phone_number is "":
        if is_valid_phone(user_update.phone_number):
            user.phone_number = user_update.phone_number
        else:
            raise HTTPException(status_code=400, detail="Invalid phone number")
    if user_update.email is not None or user_update.email is "":
        if is_valid_email(user_update.email):
            user.email = user_update.email
        else:
            raise HTTPException(status_code=400, detail="Invalid email")
         
    
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
@router.delete("/delete/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    deleted_user = del_user(db, user_id)
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
    user = get_user_by_phone(db, phone_number)
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
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.latitude = latitude
    user.longitude = longitude
    user.last_update_location = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return {"message": "Location updated successfully"}

