from urllib import request
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from datetime import time

from sqlalchemy.orm import Session
from database import get_db, handle_exceptions
from models import User, Reminder, ReminderCreate, ReminderUpdate, ReminderResponse, ReminderFilter
from utils import token_manager, get_current_user

router = APIRouter()

@handle_exceptions
@router.post("/")
async def create_reminder(Reminder: ReminderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = user.user_id
    Reminder = ReminderCreate(**Reminder.dict(), user_id=user_id)
    db.add(Reminder)
    db.commit()
    db.refresh(Reminder)
    return Reminder

@router.get("/", response_model=List[ReminderResponse])
async def get_reminders(filter: ReminderFilter, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    리마인더 리스트 조회
        - 필터 O : 해당 필터에 맞는 리마인더 리스트 반환
        - 필터 X : 해당 유저의 모든 리마인더 리스트 반환
    """
    
    query = db.query(Reminder).filter(Reminder.user_id == user.user_id)
    
    for key, value in filter.dict().items():
        if value is not None:
            query = query.filter(getattr(Reminder, key) == value)
    reminders = query.all()
    if not reminders:
        raise HTTPException(status_code=404, detail="리마인더를 찾지 못했습니다.")
    return reminders

@handle_exceptions
@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(reminder_id: int, Reminder: ReminderUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminder = db.query(Reminder).filter(Reminder.user_id == user.user_id, Reminder.reminder_id == reminder_id).first()
    if reminder is None:
        raise HTTPException(status_code=404, detail="리마인더를 찾지 못했습니다.")
    for key, value in Reminder.dict().items():
        if value is not None:
            setattr(reminder, key, value)
    db.commit()
    db.refresh(reminder)
    return reminder

@handle_exceptions
@router.delete("/", response_model=dict)
async def delete_reminders(fillter: ReminderFilter, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Reminder).filter(Reminder.user_id == user.user_id)
    for key, value in filter.dict().items():
        if value is not None:
            query = query.filter(getattr(Reminder, key) == value)
    reminders = query.all()
    if not reminders:
        raise HTTPException(status_code=404, detail="리마인더를 찾지 못했습니다.")

    query.delete(synchronize_session=False)
    return reminders

@handle_exceptions
@router.post("/{reminder_id}/notify", response_model=ReminderResponse)
async def set_reminder_reminder(reminder_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminder = db.query(Reminder).filter(Reminder.user_id == user.user_id, Reminder.reminder_id == reminder_id).first()
    if reminder is None:
        raise HTTPException(status_code=404, detail="리마인더를 찾지 못했습니다.")
    reminder.notify = not reminder.notify
    db.commit()
    db.refresh(reminder)
    return reminder