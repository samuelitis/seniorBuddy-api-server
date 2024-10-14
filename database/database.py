from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from utils.config import variables

DATABASE_URL = f"mysql+mysqlconnector://{variables.MYSQL_USER}:{variables.MYSQL_PASSWORD}@{variables.MYSQL_HOST}:{variables.MYSQL_PORT}/seniorbuddy_db"

# DB 연결 설정
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DB 세션을 가져오는 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()