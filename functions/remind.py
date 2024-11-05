from datetime import time, datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import User, HospitalReminder, MedicationReminder, AssistantThread

def register_medication_remind(db: Session, thread_id, content: str, start_date: int, repeat_day: str, frequency: str, additional_info: str):
    try:
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()
        user_id = user.user_id
        
        if user_id is None:
            return {"status": "failed", "message": "사용자 정보가 없습니다."}
        try:
            start_date = datetime.now() - timedelta(days=start_date)
        except ValueError:
            return {"status": "failed", "message": "날짜 형식이 잘못되었습니다. 오늘날짜로 등록할 것인지 다시 물어봐주세요"}
        new_reminder = MedicationReminder(
            user_id = user_id,
            content = content,
            start_date = start_date,
            end_date = start_date + timedelta(days=repeat_day),
            dose_morning = "기상" in frequency,
            dose_breakfast_before = "아침식전" in frequency,
            dose_breakfast_after = "아침식후" in frequency,
            dose_lunch_before = "점심식전" in frequency,
            dose_lunch_after = "점심식후" in frequency,
            dose_dinner_before = "저녁식전" in frequency,
            dose_dinner_after = "저녁식후" in frequency,
            dose_bedtime = "취침전" in frequency,
            additional_info = additional_info
        )
        db.add(new_reminder)
        db.commit()
        db.refresh(new_reminder)
        return new_reminder
    
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}
    
def register_hospital_remind(db: Session, thread_id, content: str, year: int=datetime.now().year, month: int=datetime.now().month, day: int=datetime.now().day, day_num: int=0, hour: int=9, minute: int=0, additional_info: str=None):
    try:
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()
        user_id = user.user_id
        
        if user_id is None:
            return {"status": "failed", "message": "사용자 정보가 없습니다."}
        try:
            reminder_time = time(hour, minute)
            date = f"{year}-{month}-{day}"
            start_date = datetime.strptime(date, "%Y-%m-%d") - timedelta(days=day_num)

        except ValueError:
            return {"status": "failed", "message": "시간 형식이 잘못되었습니다. 다시 시간을 입력해주세요"}
        
        new_reminder = HospitalReminder(
            user_id = user_id,
            content = content,
            start_date = start_date,
            reminder_time = reminder_time,
            additional_info = additional_info
        )
        db.add(new_reminder)
        db.commit()
        db.refresh(new_reminder)
        return new_reminder
    
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}