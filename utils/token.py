from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from jose import jwt, ExpiredSignatureError, JWTError
from sqlalchemy.orm import Session
from utils.config import variables
from models import get_user_by_id
from database import get_db

from models import RefreshToken

# 헷갈려서 매니지먼트 클래스로 변경
# 또한 토큰에 expire 날짜 정보도 포함하였음
class TokenManager:
    def __init__(self, secret_key: str = variables.HASH_KEY, 
                 algorithm: str = variables.ALGORITHM, 
                 access_token_expiry_minutes: int = variables.ACCESS_TOKEN_EXPIRE_MINUTES, 
                 refresh_token_expiry_days: int = variables.REFRESH_TOKEN_EXPIRE_DAYS):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expiry_minutes = access_token_expiry_minutes
        self.refresh_token_expiry_days = refresh_token_expiry_days

    def _create_token(self, user_id: int, expires_delta: timedelta, additional_claims: dict = None) -> str:
        expire = datetime.utcnow() + expires_delta
        to_encode = {"sub": str(user_id), "exp": expire, "iat": datetime.utcnow()}
        
        if additional_claims:
            to_encode.update(additional_claims)
            
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_access_token(self, user_id: int) -> str:
        """
        액세스 토큰 생성
        """
        return self._create_token(user_id, timedelta(minutes=self.access_token_expiry_minutes))

    def create_refresh_token(self, user_id: int) -> str:
        """
        리프레시 토큰 생성
        """
        return self._create_token(user_id, timedelta(days=self.refresh_token_expiry_days))

    def decode_token(self, token: str, refresh: bool=False) -> dict:
        """
        토큰 검증 및 디코딩
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except ExpiredSignatureError:
            if refresh:
                payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
                return payload
            else:
                raise HTTPException(status_code=401, detail="토근이 유효하지 않습니다")

        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"토근이 유효하지 않습니다")

    def store_refresh_token(self, db: Session, token: str, user_id: int, expires_at: datetime = None):
        """
        리프레시 토큰 저장.
        """
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(days=self.refresh_token_expiry_days)
        
        refresh_token = RefreshToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        db.add(refresh_token)
        db.commit()
        db.refresh(refresh_token)
        return refresh_token

    def get_valid_refresh_token(self, db: Session, token: str) -> RefreshToken:
        """
        DB에서 유효한 리프레시 토큰 조회
        """
        refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
        if not refresh_token:
            raise HTTPException(status_code=401, detail="토근이 유효하지 않습니다")
        
        if refresh_token.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="토근이 유효하지 않습니다")
        
        return refresh_token
    
    def del_refresh_token(self, db: Session, token: str):
        """
        리프레시 토큰 무효화 (DB에서 삭제)
        """
        refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
        if refresh_token:
            db.delete(refresh_token)
            db.commit()


token_manager = TokenManager()
authorization_scheme = APIKeyHeader(name="Authorization")

def get_current_user(authorization: str = Depends(authorization_scheme), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=400, detail="인증 정보가 없습니다")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Bearer 토큰이 필요합니다")

    token = authorization.split(" ")[1]
    
    try:
        payload = token_manager.decode_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="토근이 유효하지 않습니다")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=404, detail="사용자 정보가 없습니다")
        
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자 정보가 없습니다")
        
        return user
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토근이 유효하지 않습니다")

    except HTTPException as e:
        raise e
    
    except Exception as e: # 임시 예외처리, 발생가능한 예외처리 추가 필요
        raise HTTPException(status_code=403, detail=f"예상치 못한 오류가 발생했습니다: {str(e)}")