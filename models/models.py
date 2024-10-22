from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey, TEXT, Date, Time
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, validator
from typing import Optional
from database import Base
from datetime import datetime, date as dt_date, time as dt_time
from enum import Enum

# 메세지 전송자 유형 Enum 정의
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
    user_type = Column(String(16), nullable=False)
    phone_number = Column(String(20), nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    last_update_location = Column(DateTime, nullable=True)
    ai_profile = Column(Integer, default=1)

    thread = relationship("AssistantThread", back_populates="user", uselist=False)
    reminders = relationship("Reminder", back_populates="user")

    @validator('email')
    def check_contact(cls, v, values, **kwargs):
        if 'phone_number' in values and v is None and values['phone_number'] is None:
            raise ValueError('이메일 혹은 휴대폰 번호 둘중 하나는 입력되어야합니다.')
        return v
# AssistantThreads 테이블 모델 정의
class AssistantThread(Base):
    __tablename__ = "assistant_threads"

    thread_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete="CASCADE"), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    run_state = Column(String(50), nullable=True)
    run_id = Column(String(100), nullable=True)

    user = relationship("User", back_populates="thread")
    message = relationship("AssistantMessage", back_populates="thread", uselist=True)

# AssistantMessages 테이블 모델 정의
class AssistantMessage(Base):
    __tablename__ = "assistant_messages"
    
    message_id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(36), ForeignKey('assistant_threads.thread_id', ondelete="SET NULL"), nullable=True)
    sender_type = Column(String(18), nullable=False)
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

class Reminder(Base):
    __tablename__ = "reminders"

    reminder_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    content = Column(TEXT, nullable=False)
    reminder_type = Column(String(16), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    reminder_time = Column(Time, nullable=False)
    repeat_interval = Column(String(16), nullable=True)
    repeat_day = Column(Integer, nullable=True)
    additional_info = Column(TEXT, nullable=True)
    notify = Column(Boolean, nullable=False)

    user = relationship("User", back_populates="reminders")

# 사용자 생성/조회 스키마
class UserCreate(BaseModel):
    user_real_name: str
    password: str
    user_type: str
    phone_number: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True

# 스레드 생성/조회 스키마
class AssistantThreadCreate(BaseModel):
    run_state: Optional[str] = None
    run_id: Optional[str] = None

    class Config:
        from_attributes = True

# 메세지 생성/조회 스키마
class AssistantMessageCreate(BaseModel):
    sender_type: SenderType
    content: str
    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    user_real_name: str
    user_type: str
    phone_number: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True
class RegisterResponse(BaseModel):
    user_real_name: str
    user_type: str
    phone_number: Optional[str] = None
    access_token: Optional[str] = None
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


class ReminderCreate(BaseModel):
    content: str
    reminder_type: str
    start_date: dt_date
    end_date: Optional[dt_date] = None
    reminder_time: dt_time
    repeat_interval: Optional[str] = None
    repeat_day: Optional[int] = None
    additional_info: Optional[str] = None
    notify: bool = True

class ReminderUpdate(BaseModel):
    content: Optional[str] = None
    reminder_type: Optional[str] = None
    start_date: Optional[dt_date] = None
    end_date: Optional[dt_date] = None
    reminder_time: Optional[dt_time] = None
    repeat_interval: Optional[str] = None
    repeat_day: Optional[int] = None
    additional_info: Optional[str] = None
    notify: Optional[bool] = None

class ReminderResponse(BaseModel):
    reminder_id: int
    content: str
    reminder_type: str
    start_date: dt_date
    end_date: Optional[dt_date] = None
    reminder_time: dt_time
    repeat_interval: Optional[str] = None
    repeat_day: Optional[int] = None
    additional_info: Optional[str] = None
    notify: bool = True

    class Config:
        from_attributes = True

class ReminderFilter(BaseModel):
    reminder_type: Optional[str] = None
    start_date: Optional[dt_date] = None
    end_date: Optional[dt_date] = None
    repeat_interval: Optional[str] = None
    notify: Optional[bool] = None 