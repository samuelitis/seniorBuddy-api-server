# 일단은 기본적인 부분 제외하고 예외처리 없이 수행한 뒤 필요한 부분을 추가하는 식으로 할것.
#
# openai assistant api 부분 미완성되어있음
# - 음성인식의 결과가 이상한 경우 어떻게 처리할것인지?
# - 내부적으로 쓰레드 삭제를 어떻게 할것인지?
# - 사용자 메모리를 어떻게 구현할것인지?
# - 메모리 구성을 하겠다면, 어떻게 파인튜닝할것인지?


import nest_asyncio
nest_asyncio.apply()

import sqlite3
from utils.config import variables
from routers import medication, reminder, user, assistant, auth
from database import engine, Base
from middleware import sql_injection_middleware

from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from base64 import b64encode
# 환경변수 호출
assistant_id = variables.OPENAI_ASSISTANT_ID
weather_key = variables.WEATHER_KEY
hash_key = variables.HASH_KEY

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=variables.ORIGINS,
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
app.include_router(medication.router, prefix="/medication", tags=["Medication"])
app.include_router(reminder.router, prefix="/reminer", tags=["Reminer"])

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={"X-Error": "Error Detail"}
    )

# if __name__ == "__main__":
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
# bash > uvicorn main:app --host [host] --port [port] --reload