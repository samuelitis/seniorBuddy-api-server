from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import UserCreate
import models
from database import get_db
from datetime import datetime
from typing import List
import uuid
from utils import hash_password, validate_password_strength

router = APIRouter()
### 사용자 관리 API ###
# 10월 2일까지는 최종완성할것

# 특정 사용자 조회 <관리용> 
# 시니어를 제외한 관리자 혹은 보호자 계정을 통해 관리할 수 있도록
# 소속 시니어 목록을 추출하는 api 필요
@router.get("/users/{user_id}", response_model=UserCreate)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = models.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# 모든 사용자 조회
# 관리자용으로 개발 후에는 삭제 필요
@router.get("/users/", response_model=List[UserCreate])
def get_all_users(db: Session = Depends(get_db)):
    return models.get_all_users(db)

# 사용자 정보 업데이트
# 일단은 전체 정보를 업데이트 할 수 있도록?
@router.put("/users/{user_id}", response_model=UserCreate)
def update_user(user_id: int, user_update: UserCreate, db: Session = Depends(get_db)):
    updated_user = models.update_user(db, user_id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

# 사용자 생성 API
# 일반 유저의 가입과 관리자, 기업용을 구별할 필요가 있음
# 만약 프론트에서 기업 가입자를 채택하지 않을 경우 삭제
@router.post("/users/register", response_model=UserCreate)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # 전화번호 중복 확인
    existing_user = db.query(models.User).filter(models.User.phone_number == user.phone_number).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    # 이메일 중복 확인
    if user.email:
        existing_email_user = db.query(models.User).filter(models.User.email == user.email).first()
        if existing_email_user:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # 비밀번호 강도 체크 (비밀번호 규칙 적용)
    validate_password_strength(user.password)
    
    # 비밀번호 해싱
    hashed_password = hash_password(user.password)
    
    # 사용자 생성
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
    
    return new_user

# 사용자 삭제
@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    deleted_user = models.delete_user(db, user_id)
    if not deleted_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}


### 비밀번호 재설정 API ###

@router.post("/users/reset-password")
def reset_password(phone_number: str, new_password: str, db: Session = Depends(get_db)):
    user = models.get_user_by_phone(db, phone_number)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return {"message": "Password reset successful"}


### 사용자 정보 수정 API ###

@router.put("/users/{user_id}/update-info", response_model=UserCreate)
def update_user_info(user_id: int, user_update: UserCreate, db: Session = Depends(get_db)):
    user = models.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.user_real_name = user_update.user_real_name
    user.phone_number = user_update.phone_number
    user.email = user_update.email
    db.commit()
    db.refresh(user)
    return user


### 경도와 위도 정보 업데이트 API ###

@router.put("/users/{user_id}/update-location")
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

