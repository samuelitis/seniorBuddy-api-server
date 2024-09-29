from sqlalchemy.orm import Session
from models import User

# 사용자 ID로 사용자 조회
def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.user_id == user_id).first()

# 전화번호로 사용자 조회
def get_user_by_phone(db: Session, phone_number: str):
    return db.query(User).filter(User.phone_number == phone_number).first()

# 모든 사용자 조회
def get_all_users(db: Session):
    return db.query(User).all()

# 사용자 업데이트
def update_user(db: Session, user_id: int, user_update: dict):
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        for key, value in user_update.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
    return user

# 사용자 삭제
def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return user
    return None