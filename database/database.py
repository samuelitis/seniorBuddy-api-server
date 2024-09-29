from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

db_name, db_pwd = os.getenv("MYSQL_USER"), os.getenv("MYSQL_PASSWORD")

DATABASE_URL = f"mysql+mysqlconnector://{db_name}:{db_pwd}@localhost:3306/seniorbuddy_db"


# DB 연결 설정
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DB 세션을 가져오는 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()