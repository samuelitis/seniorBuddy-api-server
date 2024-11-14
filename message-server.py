from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import get_db
from models import ScheduledMessage, MedicationReminder, HospitalReminder, User

def schedule_messages(db: Session):
    now = datetime.utcnow()
    db.query(ScheduledMessage).delete()  # 기존 메시지 삭제

    users = db.query(User).all()

    for user in users:
        medication_reminders = db.query(MedicationReminder).filter(MedicationReminder.user_id == user.user_id).all()
        for reminder in medication_reminders:
            scheduled_message = ScheduledMessage(
                user_id=user.user_id,
                title="약 복용 알림",
                content=reminder.content,
                scheduled_time=now + timedelta(minutes=1),
                status="pending"
            )
            db.add(scheduled_message)

        hospital_reminders = db.query(HospitalReminder).filter(HospitalReminder.user_id == user.user_id).all()
        for reminder in hospital_reminders:
            scheduled_message = ScheduledMessage(
                user_id=user.user_id,
                title="병원 예약 알림",
                content=reminder.content,
                scheduled_time=now + timedelta(minutes=1),
                status="pending"
            )
            db.add(scheduled_message)

    db.commit()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(schedule_messages, 'cron', hour=0, minute=0)  # 매일 자정에 호출
    scheduler.start()

if __name__ == "__main__":
    start_scheduler()