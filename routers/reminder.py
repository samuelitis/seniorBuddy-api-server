from urllib import request
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from datetime import time

from pytest import Session
from database import get_db
from models import ReminderCreate, ReminderUpdate, User
from utils import token_manager

router = APIRouter()

@router.post("/", response_model=int)
async def create_reminder(reminder_time: ReminderCreate, db: Session = Depends(get_db)):
    
    """
    """

    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token missing")

    token = authorization.split(" ")[1]
    payload = token_manager.decode_token(token)

    user_id = payload.get("sub")
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    pass

@router.get("/", response_model=List[ReminderCreate])
async def get_reminder(user_id: int, db: Session = Depends(get_db)):
    
    """
    """

    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token missing")

    token = authorization.split(" ")[1]
    payload = token_manager.decode_token(token)

    user_id = payload.get("sub")
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    pass

@router.get("/{reminder_id}", response_model=ReminderCreate)
async def get_reminder(reminder_id: int, db: Session = Depends(get_db)):
    
    """
    """

    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token missing")

    token = authorization.split(" ")[1]
    payload = token_manager.decode_token(token)

    user_id = payload.get("sub")
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    pass

@router.put("/{reminder_id}")
async def update_reminder(reminder_id: int, reminder_time: ReminderUpdate, db: Session = Depends(get_db)):
    
    """
    """

    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token missing")

    token = authorization.split(" ")[1]
    payload = token_manager.decode_token(token)

    user_id = payload.get("sub")
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    pass

@router.delete("/{reminder_id}")
async def delete_reminder(reminder_id: int, db: Session = Depends(get_db)):
    
    """
    """

    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token missing")

    token = authorization.split(" ")[1]
    payload = token_manager.decode_token(token)

    user_id = payload.get("sub")
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    pass

@router.post("/{reminder_id}/notify")
async def set_reminder(reminder_id: int, db: Session = Depends(get_db)):
    
    """
    """

    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token missing")

    token = authorization.split(" ")[1]
    payload = token_manager.decode_token(token)

    user_id = payload.get("sub")
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    pass