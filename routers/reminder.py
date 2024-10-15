from urllib import request
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from datetime import time

from sqlalchemy.orm import Session
from database import get_db
from models import ReminderCreate, ReminderUpdate, User
from utils import token_manager, get_current_user

router = APIRouter()

@router.post("/", response_model=int)
async def create_reminder(reminder_time: ReminderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    """
    """
    pass

@router.get("/", response_model=List[ReminderCreate])
async def get_reminder(user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    """
    """
    pass

@router.get("/{reminder_id}", response_model=ReminderCreate)
async def get_reminder(reminder_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    """
    """
    pass

@router.put("/{reminder_id}")
async def update_reminder(reminder_id: int, reminder_time: ReminderUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    """
    """

    pass

@router.delete("/{reminder_id}")
async def delete_reminder(reminder_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    """
    """

    pass

@router.post("/{reminder_id}/notify")
async def set_reminder(reminder_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    """
    """

    pass