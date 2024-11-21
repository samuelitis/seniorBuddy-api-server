from datetime import time, datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import User, HospitalReminder, MedicationReminder, AssistantThread, UserSchedule, UserScheduleResponse

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
    
def remove_medication_remind(db: Session, thread_id, reminder_id: int):
    try:
        print(f"remove_medication_remind({thread_id}, {reminder_id})")
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()
        user_id = user.user_id
        
        if user_id is None:
            return {"status": "failed", "message": "사용자 정보가 없습니다."}

        # db에서 조회
        reminder = db.query(MedicationReminder).filter(MedicationReminder.reminder_id == reminder_id, 
                                                       MedicationReminder.user_id == user.user_id).first()
        if reminder is None:
            return {"status": "failed", "message": f"리마인더를 찾지 못했습니다."}
        #db에서 삭제
        db.delete(reminder)
        db.commit()

        return {"status": "success", "message": "약 복용 알림이 삭제되었습니다."}
    
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}

# 약 복용 알림 정보 조회
def get_medication_remind(db: Session, thread_id):
    try:
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()
        user_id = user.user_id
        
        if user_id is None:
            return {"status": "failed", "message": "사용자 정보가 없습니다."}
        
        reminders = db.query(MedicationReminder).filter(MedicationReminder.user_id == user_id).all()
        result = []
        for reminder in reminders:
            result.append({
                'reminder_id': reminder.reminder_id,
                'content': reminder.content,
                'start_date': reminder.start_date,
                'end_date': reminder.end_date,
                'dose_morning': reminder.dose_morning,
                'dose_breakfast_before': reminder.dose_breakfast_before,
                'dose_breakfast_after': reminder.dose_breakfast_after,
                'dose_lunch_before': reminder.dose_lunch_before,
                'dose_lunch_after': reminder.dose_lunch_after,
                'dose_dinner_before': reminder.dose_dinner_before,
                'dose_dinner_after': reminder.dose_dinner_after,
                'dose_bedtime': reminder.dose_bedtime,
                'additional_info': reminder.additional_info
            })
        return result
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

# 병원 예약 알림 삭제
def remove_hospital_remind(db: Session, thread_id, reminder_id: int):
    try:
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()
        user_id = user.user_id
        
        if user_id is None:
            return {"status": "failed", "message": "사용자 정보가 없습니다."}

        # db에서 조회
        reminder = db.query(HospitalReminder).filter(HospitalReminder.user_id == user_id, HospitalReminder.reminder_id == reminder_id).first()

        #db에서 삭제
        db.delete(reminder)
        db.commit()

        return {"status": "success", "message": "병원 예약 알림이 삭제되었습니다."}
    
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}

# 병원 예약 정보 조회
def get_hospital_remind(db: Session, thread_id):
    try:
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()
        user_id = user.user_id
        
        if user_id is None:
            return {"status": "failed", "message": "사용자 정보가 없습니다."}
        
        reminders = db.query(HospitalReminder).filter(HospitalReminder.user_id == user_id).all()
        return reminders
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}

# 식사시간 등록
def set_default_meal_time(db: Session, thread_id):
    try:
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()
        user_id = user.user_id
        
        if user_id is None:
            return {"status": "failed", "message": "사용자 정보가 없습니다."}
        
        if db.query(UserSchedule).filter(UserSchedule.user_id == user_id).first():
            return {"status": "failed", "message": "이미 식사시간이 등록되어 있습니다."}
        
        new_schedule = UserSchedule(
            user_id = user_id,
            morning_time = time(7, 0),
            breakfast_time = time(8, 0),
            lunch_time = time(12, 0),
            dinner_time = time(18, 0),
            bedtime_time = time(22, 0)
        )
        db.add(new_schedule)
        db.commit()
        db.refresh(new_schedule)
        return new_schedule
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}

# 현재 함수가 assistant api를 통해서만 사용가능하도록 되어있음
# 아닌 경우에도 사용가능하지만 조금 수정할 필요가 있어보임
# 아니면 식사기록, 취침 및 기상 시간을 기록하는 api를 따로 만들어서 사용하는 것도 좋을 것 같음
# 나중에 수정할 필요가 있음
# RNN 모델을 사용해서 식사시간을 추정하는 것도 좋을 것 같음
# 이에 대해서 적용하지말고 일단 의논해보도록
# 이번 주는 해당 기능 연결 X
def update_meal_time(db: Session, thread_id, eaten: bool, meal_type: str, minutes: int = 10):
    try:
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()
        user_id = user.user_id
        
        if user_id is None:
            return {"status": "failed", "message": "사용자 정보가 없습니다."}
        
        schedule = db.query(UserSchedule).filter(UserSchedule.user_id == user_id).first()
        if schedule is None:
            set_default_meal_time(db, thread_id)
            return {"status": "failed", "message": "식사시간이 등록되어 있지 않아 기본값으로 설정되었습니다."}
        
        # 식사 여부에 따라 meal_time 조정
        if eaten:
            # 10분 낮추기
            if meal_type == "morning":
                schedule.morning_time = (schedule.morning_time.replace(hour=0, minute=0) - timedelta(minutes=minutes)).time()
            elif meal_type == "breakfast":
                schedule.breakfast_time = (schedule.breakfast_time.replace(hour=0, minute=0) - timedelta(minutes=minutes)).time()
            elif meal_type == "lunch":
                schedule.lunch_time = (schedule.lunch_time.replace(hour=0, minute=0) - timedelta(minutes=minutes)).time()
            elif meal_type == "dinner":
                schedule.dinner_time = (schedule.dinner_time.replace(hour=0, minute=0) - timedelta(minutes=minutes)).time()
            elif meal_type == "bedtime":
                schedule.bedtime_time = (schedule.bedtime_time.replace(hour=0, minute=0) - timedelta(minutes=minutes)).time()
        else:
            # 10분 추가하기
            if meal_type == "morning":
                schedule.morning_time = (schedule.morning_time.replace(hour=0, minute=0) + timedelta(minutes=minutes)).time()
            elif meal_type == "breakfast":
                schedule.breakfast_time = (schedule.breakfast_time.replace(hour=0, minute=0) + timedelta(minutes=minutes)).time()
            elif meal_type == "lunch":
                schedule.lunch_time = (schedule.lunch_time.replace(hour=0, minute=0) + timedelta(minutes=minutes)).time()
            elif meal_type == "dinner":
                schedule.dinner_time = (schedule.dinner_time.replace(hour=0, minute=0) + timedelta(minutes=minutes)).time()
            elif meal_type == "bedtime":
                schedule.bedtime_time = (schedule.bedtime_time.replace(hour=0, minute=0) + timedelta(minutes=minutes)).time()

        schedule.updated_at = datetime.now()
        db.commit()
        db.refresh(schedule)
        return schedule
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}