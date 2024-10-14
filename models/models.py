from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, TEXT
from sqlalchemy import Enum as SQLAEnum
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr
from typing import Optional
from database import Base
from datetime import time, datetime
from enum import Enum

# 사용자 유형 Enum 정의
class UserType(str, Enum):
    senior = 'senior'
    guardian = 'guardian'
    external_company = 'external_company'
    admin = 'admin'

# 메시지 전송자 유형 Enum 정의
class SenderType(str, Enum):
    user = 'user'
    system = 'system'
    assistant = 'assistant'

# Users 테이블 모델 정의
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    user_real_name = Column(String(100), nullable=False)
    user_uuid = Column(String(36), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    user_type = Column(SQLAEnum(UserType), nullable=False)
    phone_number = Column(String(20), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    last_update_location = Column(DateTime, nullable=True)

    thread = relationship("AssistantThread", back_populates="user", uselist=False)

# AssistantThreads 테이블 모델 정의
class AssistantThread(Base):
    __tablename__ = "assistant_threads"

    thread_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    run_state = Column(String(50), nullable=False)
    run_id = Column(String(100), nullable=True)

    user = relationship("User", back_populates="thread")
    message = relationship("AssistantMessage", back_populates="thread", uselist=False)

# AssistantMessages 테이블 모델 정의
class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    message_id = Column(String(36), primary_key=True, index=True)
    thread_id = Column(String(36), ForeignKey('assistant_threads.thread_id'), unique=True, nullable=False)
    sender_type = Column(SQLAEnum(SenderType), nullable=False)
    status_type = Column(TEXT, nullable=False)
    content = Column(TEXT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    thread = relationship("AssistantThread", back_populates="message")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


# 사용자 생성/조회 스키마
class UserCreate(BaseModel):
    user_real_name: str
    password: str
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

class UserResponse(BaseModel):
    user_real_name: str
    user_type: UserType
    phone_number: str
    email: Optional[EmailStr] = None

    class Config:
        from_attributes = True
class RegisterResponse(BaseModel):
    user_real_name: str
    user_type: str
    phone_number: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginData(BaseModel):
    identifier: str  # 이메일 또는 전화번호 그냥 문자열로 받음
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "identifier": "user@example.com or 010-1234-5678",
                "password": "password123"
            }
        }

class MedicationTimeCreate(BaseModel):
    medication_name: str
    dosage: str
    medication_time: time

class MedicationTimeUpdate(BaseModel):
    medication_name: str = None
    dosage: str = None
    medication_time: time = None

class ReminderCreate(BaseModel):
    content: str
    mind_date: str
    mind_time: time
    type: str

class ReminderUpdate(BaseModel):
    content: str = None
    mind_date: str = None
    mind_time: time = None
    type: str = None