from fastapi import APIRouter, Depends, HTTPException
from datetime import timedelta

from sqlalchemy.orm import Session
from database import get_db, handle_exceptions
from models import User, HospitalReminder, MedicationReminder, MedicationReminderCreate, HospitalReminderCreate, MedicationReminderResponse, HospitalReminderResponse, UserSchedule
from utils import get_current_user

import json

router = APIRouter()


#    ooo        ooooo                 .o8   o8o                          .    o8o                       
#    `88.       .888'                "888   `"'                        .o8    `"'                       
#     888b     d'888   .ooooo.   .oooo888  oooo   .ooooo.   .oooo.   .o888oo oooo   .ooooo.  ooo. .oo.  
#     8 Y88. .P  888  d88' `88b d88' `888  `888  d88' `"Y8 `P  )88b    888   `888  d88' `88b `888P"Y88b 
#     8  `888'   888  888ooo888 888   888   888  888        .oP"888    888    888  888   888  888   888 
#     8    Y     888  888    .o 888   888   888  888   .o8 d8(  888    888 .  888  888   888  888   888 
#    o8o        o888o `Y8bod8P' `Y8bod88P" o888o `Y8bod8P' `Y888""8o   "888" o888o `Y8bod8P' o888o o888o
day_switch = {
    "3일": 3,
    "7일": 7,
    "2주": 14,
    "1개월": 30,
    "2개월": 60,
    "3개월": 90,
    "1년": 365,
    "1년 이상": 365
}
@handle_exceptions
@router.post("/medication")
async def create_medication_reminder(remind: MedicationReminderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = user.user_id
    new_reminder = MedicationReminder(
        user_id = user_id,
        content = remind.content,
        start_date = remind.start_date,
        end_date = remind.start_date + timedelta(days=day_switch.get(remind.day, 0)),
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
@router.get("/medication")
async def get_medication_reminders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminders = db.query(MedicationReminder).filter(MedicationReminder.user_id == user.user_id).all()
    return reminders

@handle_exceptions
@router.put("/medication/{reminder_id}")
async def update_medication_reminder(reminder_id: int, remind: MedicationReminderResponse, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminder = db.query(MedicationReminder).filter(MedicationReminder.reminder_id == reminder_id, MedicationReminder.user_id == user.user_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    # nullable 필드 업데이트 로직
    if remind.content is not None:
        reminder.content = remind.content
    if remind.start_date is not None:
        reminder.start_date = remind.start_date
    if remind.day is not None:
        reminder.end_date = remind.start_date + timedelta(days=day_switch.get(remind.day, 0))
    if remind.frequency is not None:
        reminder.dose_morning = "기상" in remind.frequency
        reminder.dose_breakfast_before = "아침식전" in remind.frequency
        reminder.dose_breakfast_after = "아침식후" in remind.frequency
        reminder.dose_lunch_before = "점심식전" in remind.frequency
        reminder.dose_lunch_after = "점심식후" in remind.frequency
        reminder.dose_dinner_before = "저녁식전" in remind.frequency
        reminder.dose_dinner_after = "저녁식후" in remind.frequency
        reminder.dose_bedtime = "취침전" in remind.frequency
    if remind.additional_info is not None:
        reminder.additional_info = remind.additional_info

    db.commit()
    return reminder

@handle_exceptions
@router.delete("/medication/{reminder_id}")
async def delete_medication_reminder(reminder_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminder = db.query(MedicationReminder).filter(MedicationReminder.reminder_id == reminder_id, MedicationReminder.user_id == user.user_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    db.delete(reminder)
    db.commit()
    return {"detail": "Reminder deleted successfully"}

    
#    ooooo   ooooo                                o8o      .             oooo 
#    `888'   `888'                                `"'    .o8             `888 
#     888     888   .ooooo.   .oooo.o oo.ooooo.  oooo  .o888oo  .oooo.    888 
#     888ooooo888  d88' `88b d88(  "8  888' `88b `888    888   `P  )88b   888 
#     888     888  888   888 `"Y88b.   888   888  888    888    .oP"888   888 
#     888     888  888   888 o.  )88b  888   888  888    888 . d8(  888   888 
#    o888o   o888o `Y8bod8P' 8""888P'  888bod8P' o888o   "888" `Y888""8o o888o
#                                      888                                    
#                                     o888o                                   

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
@router.get("/hospital")
async def get_hospital_reminders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminders = db.query(HospitalReminder).filter(HospitalReminder.user_id == user.user_id).all()
    return reminders

@handle_exceptions
@router.put("/hospital/{reminder_id}")
async def update_hospital_reminder(reminder_id: int, remind: HospitalReminderResponse, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminder = db.query(HospitalReminder).filter(HospitalReminder.reminder_id == reminder_id, HospitalReminder.user_id == user.user_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    # nullable 필드 업데이트 로직
    if remind.content is not None:
        reminder.content = remind.content
    if remind.start_date_time is not None:
        reminder.start_date = remind.start_date_time.date()
        reminder.reminder_time = remind.start_date_time.time()
    if remind.additional_info is not None:
        reminder.additional_info = remind.additional_info

    db.commit()
    return reminder

@handle_exceptions
@router.delete("/hospital/{reminder_id}")
async def delete_hospital_reminder(reminder_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminder = db.query(HospitalReminder).filter(HospitalReminder.reminder_id == reminder_id, HospitalReminder.user_id == user.user_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    db.delete(reminder)
    db.commit()
    return {"detail": "Reminder deleted successfully"}

@handle_exceptions
@router.get("/")
def get_user_schedules(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 복약 시간, 병원 예약 등 알림 시간순으로 반환
    result = []
    user_id = user.user_id
    user_schedules = db.query(UserSchedule).filter(UserSchedule.user_id == user_id).all()
    hospital_reminders = db.query(HospitalReminder).filter(HospitalReminder.user_id == user_id).all()
    medicine_reminders = db.query(MedicationReminder).filter(MedicationReminder.user_id == user_id).all()