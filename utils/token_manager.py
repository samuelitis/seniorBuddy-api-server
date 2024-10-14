from datetime import datetime, timedelta
from jose import jwt, ExpiredSignatureError, JWTError
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import RefreshToken, User
from utils.config import variables

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

    def decode_token(self, token: str) -> dict:
        """
        토큰 검증 및 디코딩
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

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
            raise HTTPException(status_code=401, detail="Refresh token not found")
        
        if refresh_token.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Refresh token has expired")
        
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