from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum
from datetime import datetime

# 사용자 유형 Enum 정의
class UserType(str, Enum):
    senior = 'senior'
    guardian = 'guardian'
    external_company = 'external_company'
    admin = 'admin'

# 사용자 생성/조회 스키마
class UserCreate(BaseModel):
    user_real_name: str
    password: str  # 원시 비밀번호를 받도록 수정
    user_type: UserType
    phone_number: str
    email: Optional[EmailStr] = None

    class Config:
        from_attributes = True

# 스레드 생성/조회 스키마
class AssistantThreadCreate(BaseModel):
    run_state: str
    run_id: str

    class Config:
        from_attributes = True

# 메시지 생성/조회 스키마
class AssistantMessageCreate(BaseModel):
    sender_type: str
    content: str

    class Config:
        from_attributes = True
