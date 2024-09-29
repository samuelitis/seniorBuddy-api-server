# 일단은 기본적인 부분 제외하고 예외처리 없이 수행한 뒤 필요한 부분을 추가하는 식으로 할것.
#
# 보호자 및 시니어 회원가입 및 로그인
# 보호자의 시니어 위치 확인 api 추가
# openai assistant api 부분 미완성되어있음
# - 음성인식의 결과가 이상한 경우 어떻게 처리할것인지?
# - 내부적으로 쓰레드 삭제를 어떻게 할것인지?
# - 주제별로 쓰레드를 나누기? 매일 삭제? 흠..
# - 사용자 메모리를 어떻게 구현할것인지?
# - 메모리 구성을 하겠다면, 어떻게 파인튜닝할것인지?
# - 파인튜닝 데이터 누가 만들것인지?

# 라우터를 통한 엔드포인트별 구별이 필요
# SERVER/
# ├── main.py
# ├── apis/
# │   ├── __init__.py
# │   ├── user.py
# │   ├── assistant.py
# │   ├── auth.py
# ├── models/             # 데이터베이스 모델
# │   ├── __init__.py
# │   ├── models.py
# ├── schemas/            # Pydantic 스키마
# │   ├── __init__.py
# │   ├── schemas.py
# ├── utils/              # 유틸리티 함수
# │   ├── __init__.py
# │   ├── auth_utils.py
# ├── database/           # 데이터베이스 설정 및 세션 관리
# │   ├── __init__.py
# │   ├── database.py
# └── .env                # 환경 변수 파일

import nest_asyncio
nest_asyncio.apply()
from dotenv import load_dotenv
load_dotenv()

#
import models, schemas

import os, json, requests
import openai, uvicorn
import sqlite3

import numpy as np
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta
from pydantic import BaseModel

from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from typing_extensions import override
from typing import Any, List
from openai import AsyncAssistantEventHandler, AsyncOpenAI, AssistantEventHandler, OpenAI
from openai.types.beta.threads import Text, TextDelta
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import ToolCall, RunStep
from openai.types.beta import AssistantStreamEvent
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import engine, get_db
import uuid
from utils import hash_password, verify_password, create_access_token, create_refresh_token, decode_token, get_user_from_token, revoke_refresh_token, get_valid_refresh_token, store_refresh_token, validate_password_strength
from utils import REFRESH_TOKEN_EXPIRE_DAYS

# 환경변수 호출
assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
weather_key = os.getenv("WEATHER_KEY")
hash_key = os.getenv("HASH_KEY")

# 내부 DB 연결
try:
    weather_db = sqlite3.connect('./db/location_grid.db')
except sqlite3.Error as e:
    print(f"sqlite3.Error : {e}")
cursor = weather_db.cursor()

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="SeniorBuddy API",
    description="This is the API documentation for the Senior Buddy Assistant",
    version="1.0.0",
    contact={
        "name": "SeniorBuddy",
        "url": "https://github.com/seniorBuddy/seniorBuddy-api-server",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# CORS (Cross Origin Resource Sharing, 교차 출처 리소스 공유) 설정
# 
origins = [
    "http://localhost:8000",
]
app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,  # 허용된 도메인으로 제한
    allow_origins=["*"],  # 모든 도메인을 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTPS 리다이렉트
# app.add_middleware(HTTPSRedirectMiddleware)
# 음.. 인증서랑 어떻게 해야할지 몰겠네요 좀 걸릴것같습니다.
# 일단은 api완성부터하겠습니다.

# 레이트 리미팅 설정
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# DB 연결
models.Base.metadata.create_all(bind=engine)

### 사용자 관리 API ###
# 10월 2일까지는 최종완성할것

# 특정 사용자 조회 <관리용> 
# 시니어를 제외한 관리자 혹은 보호자 계정을 통해 관리할 수 있도록
# 소속 시니어 목록을 추출하는 api 필요
@app.get("/users/{user_id}", response_model=schemas.UserCreate)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = models.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# 모든 사용자 조회
# 관리자용으로 개발 후에는 삭제 필요
@app.get("/users/", response_model=List[schemas.UserCreate])
def get_all_users(db: Session = Depends(get_db)):
    return models.get_all_users(db)

# 사용자 정보 업데이트
# 일단은 전체 정보를 업데이트 할 수 있도록?
@app.put("/users/{user_id}", response_model=schemas.UserCreate)
def update_user(user_id: int, user_update: schemas.UserCreate, db: Session = Depends(get_db)):
    updated_user = models.update_user(db, user_id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

# 사용자 생성 API
# 일반 유저의 가입과 관리자, 기업용을 구별할 필요가 있음
# 만약 프론트에서 기업 가입자를 채택하지 않을 경우 삭제
@app.post("/users/register", response_model=schemas.UserCreate)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
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
@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    deleted_user = models.delete_user(db, user_id)
    if not deleted_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}


### 비밀번호 재설정 API ###

@app.post("/users/reset-password")
def reset_password(phone_number: str, new_password: str, db: Session = Depends(get_db)):
    user = models.get_user_by_phone(db, phone_number)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return {"message": "Password reset successful"}


### 사용자 정보 수정 API ###

@app.put("/users/{user_id}/update-info", response_model=schemas.UserCreate)
def update_user_info(user_id: int, user_update: schemas.UserCreate, db: Session = Depends(get_db)):
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

@app.put("/users/{user_id}/update-location")
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






### 스레드 관리 API ###

# 스레드 생성
@app.post("/assistant/threads", response_model=schemas.AssistantThreadCreate)
def create_assistant_thread(user_id: int, db: Session = Depends(get_db)):
    # OpenAI API로 새로운 Assistant 쓰레드를 생성
    thread_id = str(uuid.uuid4())
    assistant_thread = models.AssistantThread(
        user_id=user_id,
        assistant_id=assistant_id,
        thread_id=thread_id,
        created_at=datetime.utcnow()
    )
    db.add(assistant_thread)
    db.commit()
    db.refresh(assistant_thread)
    return assistant_thread

# 특정 사용자의 스레드 조회
@app.get("/threads/{user_id}")
def get_thread(user_id: int, db: Session = Depends(get_db)):
    thread = models.get_thread_by_user(db, user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread

# 스레드 삭제
@app.delete("/assistant/threads/{thread_id}")
def delete_assistant_thread(thread_id: str, db: Session = Depends(get_db)):
    thread = models.delete_thread(db, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"message": "Thread deleted successfully"}

# 메세지 생성
# 구조 확인후 필요한 정보만 저장할것,
@app.post("/assistant/threads/{thread_id}/messages", response_model=schemas.AssistantMessageCreate)
def add_message_to_thread(thread_id: str, message: schemas.AssistantMessageCreate, db: Session = Depends(get_db)):
    # OpenAI API로 메시지 전송
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": message.content}],
        thread_id=thread_id,
        assistant_id=assistant_id
    )
    
    # 응답을 AssistantMessages 테이블에 저장
    assistant_message = models.AssistantMessage(
        thread_id=thread_id,
        sender="user",
        content=message.content,
        created_at=datetime.utcnow()
    )
    db.add(assistant_message)
    
    # Assistant 응답 메시지도 저장
    assistant_response = models.AssistantMessage(
        thread_id=thread_id,
        sender="assistant",
        content=response['choices'][0]['message']['content'],
        created_at=datetime.utcnow()
    )
    db.add(assistant_response)
    
    db.commit()

    db.refresh(assistant_message)
    return assistant_message

# 메세지 실행
# 스트리밍으로 할 시 프론트에서 처리할것이 많아집니다.
# 하지만 사용자경험이 향상하므로 채택할 필요성을 느낌
# 음.. 일단은 보류..
@app.post("/assistant/threads/{thread_id}/messages/{message_id}/run")
def run_assistant_message(thread_id: str, message_id: str, db: Session = Depends(get_db)):
    # # 특정 메시지에 대해 OpenAI의 ToolCall을 실행
    # message = db.query(models.AssistantMessage).filter(models.AssistantMessage.message_id == message_id).first()
    # if not message:
    #     raise HTTPException(status_code=404, detail="Message not found")
    
    # response = openai.ToolCall.create(
    #     assistant_id=assistant_id,
    #     thread_id=thread_id,
    #     message_id=message_id
    # )
    
    # # 실행 결과 저장
    # message.status = "executed"
    # db.commit()
    
    # return {"status": "Run executed", "result": response}
    return {"status": "Run executed", "result": "response"}

# 메세지 상태 조회
@app.get("/assistant/threads/{thread_id}/messages/{message_id}/status")
def get_message_status(thread_id: str, message_id: str, db: Session = Depends(get_db)):
    message = db.query(models.AssistantMessage).filter(models.AssistantMessage.message_id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"message_id": message_id, "status": message.status}

# 특정 스레드의 메시지 조회
@app.get("/threads/{thread_id}/messages/")
def get_messages(thread_id: str, db: Session = Depends(get_db)):
    messages = models.get_messages_by_thread(db, thread_id)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for this thread")
    return messages

# 메시지 삭제
@app.delete("/messages/{message_id}")
def delete_message(message_id: str, db: Session = Depends(get_db)):
    deleted_message = models.delete_message(db, message_id)
    if not deleted_message:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Message deleted"}


### JWT 인증 및 토큰 관리 API ###

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginData(BaseModel):
    phone_number: str
    password: str

# 로그인 ㅁ및 토큰 발급 (리프레시 토큰 저장)
@app.post("/token", response_model=TokenResponse)
def login_for_access_token(data: LoginData, db: Session = Depends(get_db)):
    user = models.get_user_by_phone(db, data.phone_number)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"sub": user.user_id})
    
    refresh_token = create_refresh_token({"sub": user.user_id})
    refresh_token_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # 리프레시 토큰 저장
    store_refresh_token(db, refresh_token, user.user_id, refresh_token_expires_at)
    
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

# 리프레시 토큰을 통한 액세스 토큰 재발급
@app.post("/refresh", response_model=TokenResponse)
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    valid_token = get_valid_refresh_token(db, refresh_token)
    user_id = valid_token.user_id
    
    # 기존 리프레시 토큰 무효화
    revoke_refresh_token(db, refresh_token)
    
    user = models.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 새로운 토큰
    access_token = create_access_token({"sub": user.user_id})
    new_refresh_token = create_refresh_token({"sub": user.user_id})
    refresh_token_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    store_refresh_token(db, new_refresh_token, user.user_id, refresh_token_expires_at)
    
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


# 로그아웃
@app.post("/logout")
def logout(refresh_token: str, db: Session = Depends(get_db)):
    revoke_refresh_token(db, refresh_token) # 리프레쉬 토큰 무효화
    # 이후 어떤 추가처리가 필요한지?
    return {"message": "Logged out successfully"}

# 현재 로그인한 사용자 정보 조회
@app.get("/users/me")
def read_users_me(current_user: models.User = Depends(get_user_from_token)):
    return current_user

# if __name__ == "__main__":
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
# bash > uvicorn main:app --host [host] --port [port] --reload