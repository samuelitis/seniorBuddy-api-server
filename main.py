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

# SERVER/
# ├── main.py
# ├── routers/
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

import os
import sqlite3

import models
from routers import user, assistant, auth
from database import engine, Base

from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import FastAPI, HTTPException

# 환경변수 호출
assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
weather_key = os.getenv("WEATHER_KEY")
hash_key = os.getenv("HASH_KEY")

# 내부 DB 연결
try:
    weather_db = sqlite3.connect('./database/location_grid.db')
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
    "http://175.113.69.58:8000/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
Base.metadata.create_all(bind=engine)

app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(assistant.router, prefix="/assistant", tags=["Assistant"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# if __name__ == "__main__":
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
# bash > uvicorn main:app --host [host] --port [port] --reload