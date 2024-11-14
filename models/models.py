from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey, TEXT, Date, Time
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index
from pydantic import BaseModel, validator
from typing import Optional, List
from database import Base
from datetime import datetime, date as dt_date, time as dt_time, datetime as dt_datetime
from enum import Enum

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
    fcm_token = Column(String(255), nullable=True)

    thread = relationship("AssistantThread", back_populates="user", uselist=False)
    medication_reminders = relationship("MedicationReminder", back_populates="user")
    hospital_reminders = relationship("HospitalReminder", back_populates="user")
    user_schedule = relationship("UserSchedule", back_populates="user", uselist=False)
    scheduled_messages = relationship("ScheduledMessage", back_populates="user")

    @validator('email')
    def check_contact(cls, v, values, **kwargs):
        if 'phone_number' in values and v is None and values['phone_number'] is None:
            raise ValueError('이메일 혹은 휴대폰 번호 둘중 하나는 입력되어야합니다.')
        return v
    
class ScheduledMessage(Base):
    __tablename__ = "scheduled_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    title = Column(TEXT, nullable=False)
    content = Column(TEXT, nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(String(20), default="pending")  # pending, sent, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="scheduled_messages")

class UserSchedule(Base):
    __tablename__ = "user_schedule"

    user_id = Column(Integer, ForeignKey('users.user_id', ondelete="CASCADE"), primary_key=True, index=True)
    morning_time = Column(Time, nullable=True)
    breakfast_time = Column(Time, nullable=True)
    lunch_time = Column(Time, nullable=True)
    dinner_time = Column(Time, nullable=True)
    bedtime_time = Column(Time, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="user_schedule")

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

class MedicationReminder(Base):
    __tablename__ = "medication_reminders"
    __table_args__ = (Index('idx_user_id_medication_reminders', 'user_id'),)

    reminder_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    content = Column(TEXT, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    dose_morning = Column(Boolean, nullable=False)
    dose_breakfast_before = Column(Boolean, nullable=False)
    dose_breakfast_after = Column(Boolean, nullable=False)
    dose_lunch_before = Column(Boolean, nullable=False)
    dose_lunch_after = Column(Boolean, nullable=False)
    dose_dinner_before = Column(Boolean, nullable=False)
    dose_dinner_after = Column(Boolean, nullable=False)
    dose_bedtime = Column(Boolean, nullable=False)
    additional_info = Column(TEXT, nullable=True)

    user = relationship("User", back_populates="medication_reminders")

class HospitalReminder(Base):
    __tablename__ = "hospital_reminders"
    __table_args__ = (Index('idx_user_id_hospital_reminders', 'user_id'),)

    reminder_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    content = Column(TEXT, nullable=False)
    start_date = Column(Date, nullable=False)
    reminder_time = Column(Time, nullable=False)
    additional_info = Column(TEXT, nullable=True)

    user = relationship("User", back_populates="hospital_reminders")

# 사용자 생성/조회 스키마
class UserCreate(BaseModel):
    user_real_name: str
    password: str
    user_type: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    fcm_token: Optional[str] = None

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
    sender_type: str = "user"
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
    fcm_token: Optional[str] = None

    class Config: 
        json_schema_extra = {
            "example": {
                "identifier": "user@example.com or 010-1234-5678",
                "password": "password123",
                "fcm_token": "fcm_token"
            }
        }
class MedicationReminderCreate(BaseModel):
    content: str
    start_date: dt_date
    day: int
    frequency: List[str] = ["아침식후", "점심식후", "저녁식후"]
    additional_info: Optional[str] = None
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "content": "감기약",
                "start_date": "2024-10-24",
                "day": 7,
                "frequency": ["기상", "아침식전", "아침식후", "점심식전", "점심식후", "저녁시전", "저녁식후", "취침전"],
                "additional_info": "물많이 먹기",
            }
        }
class HospitalReminderCreate(BaseModel):
    content: str
    start_date_time: dt_datetime
    additional_info: Optional[str] = None
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "content": "경산 하양읍 미르치과 예약",
                "start_date": "2024-11-24 15:00:00",
                "additional_info": "양치하기",
            }
        }

class MedicationReminderResponse(BaseModel):
    content: Optional[str]
    start_date: Optional[dt_date]
    repeat_day: Optional[int]
    frequency: Optional[List[str]]
    additional_info: Optional[str]
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "content": "감기약",
                "start_date": "2024-10-24",
                "day": 7,
                "frequency": ["기상", "아침식전", "아침식후", "점심식전", "점심식후", "저녁시전", "저녁식후", "취침전"],
                "additional_info": "물많이 먹기",
            }
        }
class HospitalReminderResponse(BaseModel):
    content: Optional[str]
    start_date_time: Optional[dt_datetime]
    additional_info: Optional[str]
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "content": "경산 하양읍 미르치과 예약",
                "start_date": "2024-11-24 15:00:00",
                "additional_info": "양치하기",
            }
        }

        
class UserScheduleResponse(BaseModel):
    breakfast_time: Optional[dt_time]
    lunch_time: Optional[dt_time]
    dinner_time: Optional[dt_time]
    bedtime_time: Optional[dt_time]
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "breakfast_time": "08:00:00",
                "lunch_time": "13:00:00",
                "dinner_time": "18:00:00",
                "bedtime_time": "22:00:00",
            }
        }