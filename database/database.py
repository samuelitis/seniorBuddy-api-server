from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError, InvalidRequestError, NoResultFound, MultipleResultsFound, OperationalError
from fastapi import HTTPException
from requests import Session

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

def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        for arg in args:
            if isinstance(arg, Session):
                db = arg
                break
        try:
            return func(*args, **kwargs)
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"데이터 무결성 오류: {str(e)}")
        except DataError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"잘못된 데이터 입력: {str(e)}")
        except InvalidRequestError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"잘못된 요청: {str(e)}")
        except NoResultFound as e:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"결과를 찾을 수 없습니다: {str(e)}")
        except MultipleResultsFound as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"여러 결과가 발견되었습니다: {str(e)}")
        except OperationalError as e:
            db.rollback()
            raise HTTPException(status_code=503, detail=f"데이터베이스 연결 오류: {str(e)}")
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"알 수 없는 오류: {str(e)}")
    return wrapper