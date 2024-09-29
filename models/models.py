from sqlalchemy import Column, Integer, String, Enum, Float, DateTime, ForeignKey, TEXT
from sqlalchemy.orm import relationship
from database import Base
import enum
from datetime import datetime

# 사용자 유형 Enum 정의
class UserType(enum.Enum):
    senior = 'senior'
    guardian = 'guardian'
    external_company = 'external_company'
    admin = 'admin'

# 메시지 전송자 유형 Enum 정의
class SenderType(enum.Enum):
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
    user_type = Column(Enum(UserType), nullable=False)
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
    run_id = Column(String(100), nullable=False)

    user = relationship("User", back_populates="thread")
    message = relationship("AssistantMessage", back_populates="thread", uselist=False)

# AssistantMessages 테이블 모델 정의
class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    message_id = Column(String(36), primary_key=True, index=True)
    thread_id = Column(String(36), ForeignKey('assistant_threads.thread_id'), unique=True, nullable=False)
    sender_type = Column(Enum(SenderType), nullable=False)
    content = Column(TEXT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    thread = relationship("AssistantThread", back_populates="message")


# RefreshTokens 테이블 정의
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)