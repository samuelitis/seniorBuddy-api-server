from sqlalchemy.orm import Session
from models import AssistantThread, AssistantMessage

# 특정 사용자의 스레드 조회
def get_thread_by_user(db: Session, user_id: int):
    return db.query(AssistantThread).filter(AssistantThread.user_id == user_id).first()

# 스레드 삭제
def delete_thread(db: Session, thread_id: str):
    thread = db.query(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()
    if thread:
        db.delete(thread)
        db.commit()
        return thread
    return None

# 특정 스레드의 메시지 조회
def get_messages_by_thread(db: Session, thread_id: str):
    return db.query(AssistantMessage).filter(AssistantMessage.thread_id == thread_id).all()

# 메시지 삭제
def delete_message(db: Session, message_id: str):
    message = db.query(AssistantMessage).filter(AssistantMessage.message_id == message_id).first()
    if message:
        db.delete(message)
        db.commit()
        return message
    return None