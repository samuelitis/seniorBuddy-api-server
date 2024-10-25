from functools import wraps
from urllib import request
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from datetime import time, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db, handle_exceptions
from models import User, HospitalReminder, MedicationReminder, MedicationReminderCreate, HospitalReminderCreate
from utils import token_manager, get_current_user

import json

router = APIRouter()
@handle_exceptions
@router.post("/medication")
async def create_medication_reminder(remind: MedicationReminderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = user.user_id
    new_reminder = MedicationReminder(
        user_id = user_id,
        content = remind.content,
        start_date = remind.start_date,
        end_date = remind.start_date + timedelta(days=remind.repeat_day),
        dose_morning = "기상" in remind.frequency,
        dose_breakfast_before = "아침식전" in remind.frequency,
        dose_breakfast_after = "아침식후" in remind.frequency,
        dose_lunch_before = "점심식전" in remind.frequency,
        dose_lunch_after = "점심식후" in remind.frequency,
        dose_dinner_before = "저녁식전" in remind.frequency,
        dose_dinner_after = "저녁식후" in remind.frequency,
        dose_bedtime = "취침전" in remind.frequency,
        additional_info=remind.additional_info
    )
    db.add(new_reminder)
    db.commit()
    db.refresh(new_reminder)
    return new_reminder

@handle_exceptions
@router.post("/hospital")
async def create_hospital_reminder(remind: HospitalReminderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = user.user_id
    new_reminder = HospitalReminder(
        user_id=user_id,
        content=remind.content,
        start_date=remind.start_date_time.date(),
        reminder_time=remind.start_date_time.time(),
        additional_info=remind.additional_info
    )
    db.add(new_reminder)
    db.commit()
    db.refresh(new_reminder)
    return new_reminder
 
@handle_exceptions
@router.get("/medication")
async def get_medication_reminders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminders = db.query(MedicationReminder).filter(MedicationReminder.user_id == user.user_id).all()
    return reminders

@handle_exceptions
@router.get("/hospital")
async def get_hospital_reminders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminders = db.query(HospitalReminder).filter(HospitalReminder.user_id == user.user_id).all()
    return reminders
