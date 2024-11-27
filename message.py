## 임시코드

## DB를 바꿀필요가 있음

import json
import pytz
import firebase_admin
import schedule
import time

from firebase_admin import credentials, messaging
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, time
from collections import defaultdict


from models import ScheduledMessage, MedicationReminder, HospitalReminder, User, UserSchedule

local_tz = pytz.timezone('Asia/Seoul')
today = datetime.now(local_tz).date()

from utils.config import variables
DATABASE_URL = f"mysql+mysqlconnector://{variables.MYSQL_USER}:{variables.MYSQL_PASSWORD}@{variables.MYSQL_HOST}:{variables.MYSQL_PORT}/seniorbuddy_db"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def adjust_time(original_time, delta):
    return (datetime.combine(today, original_time) + delta).time()

def send_action_message(user_id, title, body, action):
    with get_db() as db:
        _token = db.query(User).filter(
            User.user_id == user_id
        ).first().fcm_token

        data = messaging.Message(
            data={
                'type': 'showOverlay',
                'title': title,
                'body': body,
                'action': action
            },
            android=messaging.AndroidConfig(
                direct_boot_ok=True,
            ),
            token = _token,
        )
        try:
            response = messaging.send(data)
            print('time:', datetime.now(), 'Successfully sent message:', response, 'Message:', body)
        except Exception as e:
            print('Error sending message:', e)

def send_message(status = 'pending'):
    with get_db() as db:
        _ = db.query(ScheduledMessage).filter(
            and_(
                ScheduledMessage.status == status,
                ScheduledMessage.scheduled_time <= datetime.now()
            )
        ).first()
        if _ is None:
            return
        _token = db.query(User).filter(
            User.user_id == _.user_id
        ).first().fcm_token

        data = messaging.Message(
            data={
                'type': 'showOverlay',
                'title': _.title,
                'body': _.content,
            },
            android=messaging.AndroidConfig(
                direct_boot_ok=True,
            ),
            token = _token,
        )
        try:
            response = messaging.send(data)
            print('time:', datetime.now(), 'Successfully sent message:', response, 'Message:', _.content)
            db.query(ScheduledMessage).filter(ScheduledMessage.id == _.id).update({"status": "sent"})
            db.commit()
        except Exception as e:
            print('Error sending message:', e)
            db.query(ScheduledMessage).filter(ScheduledMessage.id == _.id).update({"status": "failed"})
            db.commit()

def scheduling_messages():
    scheduled_messages = []
    grouped_messages = defaultdict(list)
    with get_db() as db:
        try:
            db.query(ScheduledMessage).delete()
            db.commit()
            users = db.query(User).all()
            for user in users:
                if user.fcm_token is not None:
                    user_schedule = db.query(UserSchedule).filter(UserSchedule.user_id == user.user_id).first()
                    if user_schedule is None:
                        new_schedule = UserSchedule(
                            user_id=user.user_id,
                            morning_time=time(7, 30),
                            breakfast_time=time(8, 30),
                            lunch_time=time(12, 0),
                            dinner_time=time(18, 0),
                            bedtime_time=time(22, 0)
                        )
                        db.add(new_schedule)
                        db.commit()
                        db.refresh(new_schedule)
                        user_schedule = db.query(UserSchedule).filter(UserSchedule.user_id == user.user_id).first()

                    medication_reminders = db.query(MedicationReminder).filter(
                        and_(
                            MedicationReminder.user_id == user.user_id,
                            MedicationReminder.start_date <= today,
                            MedicationReminder.end_date >= today
                        )
                    ).all()

                    _reminders = {
                        "dose_morning": [user_schedule.morning_time, []],
                        "dose_breakfast_after": [adjust_time(user_schedule.breakfast_time, -timedelta(minutes=40)), []],
                        "dose_breakfast_before": [adjust_time(user_schedule.breakfast_time, timedelta(minutes=20)), []],
                        "dose_lunch_after": [adjust_time(user_schedule.lunch_time, -timedelta(minutes=40)), []],
                        "dose_lunch_before": [adjust_time(user_schedule.lunch_time, timedelta(minutes=20)), []],
                        "dose_dinner_after": [adjust_time(user_schedule.dinner_time, -timedelta(minutes=40)), []],
                        "dose_dinner_before": [adjust_time(user_schedule.dinner_time, timedelta(minutes=20)), []],
                        "dose_bedtime": [adjust_time(user_schedule.bedtime_time, -timedelta(minutes=30)), []]
                    }

                    for reminder in medication_reminders:
                        for attribute, (scheduled_time, contents) in _reminders.items():
                            if getattr(reminder, attribute):
                                contents.append(reminder.content)

                    # 약물 알림 메시지 생성
                    for attribute, (scheduled_time, contents) in _reminders.items():
                        if contents:
                            # 중복 제거를 위해 set 사용
                            unique_contents = set(contents)
                            combined_content = f"{', '.join(unique_contents)}"
                            
                            if "morning" in attribute:
                                combined_content = f"좋은 아침입니다. {combined_content} 드셔야해요"
                            elif "bedtime" in attribute:
                                combined_content = f"주무시기 전에 {combined_content} 드셔야해요"
                            elif "breakfast_after" in attribute:
                                combined_content = f"아침 식사 30분 전에 {combined_content} 드셔야해요"
                            elif "lunch_after" in attribute:
                                combined_content = f"점심 식사 30분 전에 {combined_content} 드셔야해요"
                            elif "dinner_after" in attribute:
                                combined_content = f"저녁 식사 30분 전에 {combined_content} 드셔야해요"
                            elif "breakfast_before" in attribute:
                                combined_content = f"아침 식사 30분이 지난거같네요. {combined_content} 드셔야해요"
                            elif "lunch_before" in attribute:
                                combined_content = f"점심 식사 30분이 지난거같네요. {combined_content} 드셔야해요"
                            elif "dinner_before" in attribute:
                                combined_content = f"저녁 식사 30분이 지난거같네요. {combined_content} 드셔야해요"

                            scheduled_messages.append({
                                "user_id": user.user_id,
                                "title": "약드세요!",
                                "content": combined_content,
                                "scheduled_time": datetime.combine(today, scheduled_time)
                            })
                    hospital_reminders = db.query(HospitalReminder).filter(
                        and_(HospitalReminder.user_id == user.user_id,
                            HospitalReminder.start_date == today)
                    ).all()

                    for reminder in hospital_reminders:
                        hour = reminder.reminder_time.hour
                        minute = reminder.reminder_time.minute

                        if hour < 12:
                            period = "오전"
                            display_hour = hour if hour != 0 else 12
                        else:
                            period = "오후"
                            display_hour = hour - 12 if hour > 12 else hour 
                        _title = f"병원 예약"
                        _body = (f"{period} {display_hour}시 {minute}분에 {reminder.content} 방문일정이 있습니다." + (f", {reminder.additional_info}" if reminder.additional_info else "")).replace(" 0분", "").replace(" 30분", "반")
                        scheduled_messages.append({
                            "user_id": user.user_id,
                            "title": _title,
                            "content": _body,
                            "scheduled_time": datetime.combine(today, reminder.reminder_time) - timedelta(minutes=60)
                        })
                        
                for message in scheduled_messages:
                    key = message["scheduled_time"]
                    grouped_messages[key].append(message)

                scheduled_messages = []
                for time, contents in grouped_messages.items():
                    unique_contents = set(msg["content"] for msg in contents)
                    combined_content = ", ".join(unique_contents)
            
                    scheduled_messages.append({
                        "user_id": contents[0]["user_id"],
                        "title": contents[0]["title"],
                        "content": combined_content,
                        "scheduled_time": time
                    })
                for message in scheduled_messages:
                    new_message = ScheduledMessage(
                        user_id=message["user_id"],
                        title=message["title"],
                        content=message["content"],
                        scheduled_time=message["scheduled_time"],
                        status="pending"
                    )
                    db.add(new_message)

        except Exception as e:
            print(f"오류 발생: {e}")
            db.rollback()
        finally:
            db.commit()


cred = credentials.Certificate("fcm_key.json")
firebase_admin.initialize_app(cred)

if __name__ == '__main__':
    schedule.every().day.at("00:01").do(scheduling_messages)
    while True:
        schedule.run_pending()
        if datetime.now().time() > time(0, 30):
            send_message()