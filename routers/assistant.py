from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import AssistantThreadCreate, AssistantMessageCreate
from database import get_db
import models
import uuid, os
import openai
from datetime import datetime
from schemas import AssistantThreadCreate
from openai import AsyncAssistantEventHandler, AsyncOpenAI, AssistantEventHandler, OpenAI
from openai.types.beta.threads import Text, TextDelta
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import ToolCall, RunStep
from openai.types.beta import AssistantStreamEvent

router = APIRouter()
assistant_id = os.getenv("OPENAI_ASSISTANT_ID")

### 스레드 관리 API ###

# 스레드 생성
@router.post("/assistant/threads", response_model=AssistantThreadCreate)
def create_assistant_thread(user_id: int, db: Session = Depends(get_db)):
    # OpenAI API로 새로운 Assistant 쓰레드를 생성
    thread_id = str(uuid.uuid4())
    assistant_thread = models.AssistantThread(
        user_id=user_id,
        assistant_id=assistant_id,
        thread_id=thread_id,
        created_at=datetime.utcnow()
    )
    db.add(assistant_thread)
    db.commit()
    db.refresh(assistant_thread)
    return assistant_thread

# 특정 사용자의 스레드 조회
@router.get("/threads/{user_id}")
def get_thread(user_id: int, db: Session = Depends(get_db)):
    thread = models.get_thread_by_user(db, user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread

# 스레드 삭제
@router.delete("/assistant/threads/{thread_id}")
def delete_assistant_thread(thread_id: str, db: Session = Depends(get_db)):
    thread = models.delete_thread(db, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"message": "Thread deleted successfully"}

# 메세지 생성
# 구조 확인후 필요한 정보만 저장할것,
@router.post("/assistant/threads/{thread_id}/messages", response_model=AssistantMessageCreate)
def add_message_to_thread(thread_id: str, message: AssistantMessageCreate, db: Session = Depends(get_db)):
    # OpenAI API로 메시지 전송
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": message.content}],
        thread_id=thread_id,
        assistant_id=assistant_id
    )
    
    # 응답을 AssistantMessages 테이블에 저장
    assistant_message = models.AssistantMessage(
        thread_id=thread_id,
        sender="user",
        content=message.content,
        created_at=datetime.utcnow()
    )
    db.add(assistant_message)
    
    # Assistant 응답 메시지도 저장
    assistant_response = models.AssistantMessage(
        thread_id=thread_id,
        sender="assistant",
        content=response['choices'][0]['message']['content'],
        created_at=datetime.utcnow()
    )
    db.add(assistant_response)
    
    db.commit()

    db.refresh(assistant_message)
    return assistant_message

# 메세지 실행
# 스트리밍으로 할 시 프론트에서 처리할것이 많아집니다.
# 하지만 사용자경험이 향상하므로 채택할 필요성을 느낌
# 음.. 일단은 보류..
@router.post("/assistant/threads/{thread_id}/messages/{message_id}/run")
def run_assistant_message(thread_id: str, message_id: str, db: Session = Depends(get_db)):
    # # 특정 메시지에 대해 OpenAI의 ToolCall을 실행
    # message = db.query(models.AssistantMessage).filter(models.AssistantMessage.message_id == message_id).first()
    # if not message:
    #     raise HTTPException(status_code=404, detail="Message not found")
    
    # response = openai.ToolCall.create(
    #     assistant_id=assistant_id,
    #     thread_id=thread_id,
    #     message_id=message_id
    # )
    
    # # 실행 결과 저장
    # message.status = "executed"
    # db.commit()
    
    # return {"status": "Run executed", "result": response}
    return {"status": "Run executed", "result": "response"}

# 메세지 상태 조회
@router.get("/assistant/threads/{thread_id}/messages/{message_id}/status")
def get_message_status(thread_id: str, message_id: str, db: Session = Depends(get_db)):
    message = db.query(models.AssistantMessage).filter(models.AssistantMessage.message_id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"message_id": message_id, "status": message.status}

# 특정 스레드의 메시지 조회
@router.get("/threads/{thread_id}/messages/")
def get_messages(thread_id: str, db: Session = Depends(get_db)):
    messages = models.get_messages_by_thread(db, thread_id)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for this thread")
    return messages

# 메시지 삭제
@router.delete("/messages/{message_id}")
def delete_message(message_id: str, db: Session = Depends(get_db)):
    deleted_message = models.delete_message(db, message_id)
    if not deleted_message:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Message deleted"}