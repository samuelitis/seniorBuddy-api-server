import os, json
from typing import Any, override
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import AssistantThreadCreate, AssistantMessageCreate
from database import get_db
from models import AssistantThread, AssistantMessage
from datetime import datetime
from schemas import AssistantThreadCreate
from openai import AsyncAssistantEventHandler, AsyncOpenAI, AssistantEventHandler, OpenAI
from openai.types.beta.threads import Text, TextDelta
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import ToolCall, RunStep
from openai.types.beta import AssistantStreamEvent
from functions import getUltraSrtFcst



router = APIRouter()
assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
client = OpenAI()

### 스레드 관리 API ###
#
#    ooooooooooooo oooo                                           .o8 
#    8'   888   `8 `888                                          "888 
#         888       888 .oo.   oooo d8b  .ooooo.   .oooo.    .oooo888 
#         888       888P"Y88b  `888""8P d88' `88b `P  )88b  d88' `888 
#         888       888   888   888     888ooo888  .oP"888  888   888 
#         888       888   888   888     888    .o d8(  888  888   888 
#        o888o     o888o o888o d888b    `Y8bod8P' `Y888""8o `Y8bod88P"

# 스레드 생성
@router.post("/assistant/threads", response_model=AssistantThreadCreate)
def create_assistant_thread(user_id: int, db: Session = Depends(get_db)):
    # OpenAI API를 통해 스레드 생성
    thread = client.beta.threads.create()
    
    assistant_thread = AssistantThread(
        user_id=user_id,
        thread_id=thread.id,
        created_at=datetime.utcnow(),
        run_state="created",  # 초기 상태
        run_id=thread.run_id
    )
    
    db.add(assistant_thread)
    db.commit()
    db.refresh(assistant_thread)
    
    return assistant_thread

# 특정 사용자의 스레드 조회
@router.get("/assistant/threads/{user_id}")
def get_threads_by_user(user_id: int, db: Session = Depends(get_db)):
    threads = db.query(AssistantThread).filter(AssistantThread.user_id == user_id).all()
    if not threads:
        raise HTTPException(status_code=404, detail="No threads found for this user")
    return threads

# 스레드 삭제
@router.delete("/assistant/threads/{user_id}")
def delete_assistant_thread(user_id: int, db: Session = Depends(get_db)):
    # user_id로 해당 유저의 스레드를 찾음
    thread = db.query(AssistantThread).filter(AssistantThread.user_id == user_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    db.delete(thread)
    db.commit()
    return {"message": "Thread deleted successfully"}

#    ooo        ooooo                                                           
#    `88.       .888'                                                           
#     888b     d'888   .ooooo.   .oooo.o  .oooo.o  .oooo.    .oooooooo  .ooooo. 
#     8 Y88. .P  888  d88' `88b d88(  "8 d88(  "8 `P  )88b  888' `88b  d88' `88b
#     8  `888'   888  888ooo888 `"Y88b.  `"Y88b.   .oP"888  888   888  888ooo888
#     8    Y     888  888    .o o.  )88b o.  )88b d8(  888  `88bod8P'  888    .o
#    o8o        o888o `Y8bod8P' 8""888P' 8""888P' `Y888""8o `8oooooo.  `Y8bod8P'
#                                                           d"     YD           
#                                                           "Y88888P'           

# 메시지 생성 및 전송
@router.post("/assistant/threads/{user_id}/messages", response_model=AssistantMessageCreate)
def add_message_to_thread(user_id: int, message: AssistantMessageCreate, db: Session = Depends(get_db)):
    thread = db.query(AssistantThread).filter(AssistantThread.user_id == user_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # OpenAI API로 메시지 전송
    response = client.beta.threads.messages.create(
        thread_id=thread.thread_id,
        role="user",
        content=message.content
    )

    # 데이터베이스에 메시지 저장
    new_message = AssistantMessage(
        thread_id=thread.thread_id,
        sender_type="user",
        status_type="sent",
        content=message.content,
        created_at=datetime.utcnow()
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    return new_message

# 메시지 실행
@router.post("/assistant/threads/{user_id}/messages/{message_id}/run")
async def run_assistant_message(user_id: int, message_id: str, db: Session = Depends(get_db)):
    thread = db.query(AssistantThread).filter(AssistantThread.user_id == user_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # 해당 스레드의 메시지 찾기
    message = db.query(AssistantMessage).filter(AssistantMessage.message_id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # 스트리밍 방식으로 메시지 실행
    async with client.beta.threads.runs.stream(
        thread_id=thread.thread_id,
        instructions="",  # system 및 개인화된 instruction 추가
        event_handler=EventHandler(db, thread.thread_id, message_id),
    ) as stream:
        stream.until_done()

    return {"status": "Run executed", "message": message.content}

# 특정 스레드의 메시지 조회
@router.get("/assistant/threads/{user_id}/messages")
def get_messages_by_thread(user_id: int, db: Session = Depends(get_db)):
    thread = db.query(AssistantThread).filter(AssistantThread.user_id == user_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    messages = db.query(AssistantMessage).filter(AssistantMessage.thread_id == thread.thread_id).all()
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for this thread")
    return messages

# 메시지 삭제
@router.delete("/assistant/messages/{user_id}/{message_id}")
def delete_message(user_id: int, message_id: str, db: Session = Depends(get_db)):
    thread = db.query(AssistantThread).filter(AssistantThread.user_id == user_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # 해당 스레드의 메시지 찾기
    message = db.query(AssistantMessage).filter(AssistantMessage.message_id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    db.delete(message)
    db.commit()
    return {"message": "Message deleted successfully"}
class EventHandler(AssistantEventHandler):
    def __init__(self, db: Session, thread_id: str, message_id: str):
        self.db = db
        self.thread_id = thread_id
        self.message_id = message_id
        self.current_run = None

    def update_message_status(self, status: str):
        message = self.db.query(AssistantMessage).filter(AssistantMessage.message_id == self.message_id).first()
        if message:
            message.status = status
            self.db.commit()
            print(f"Message {self.message_id} status updated to {status}")

    def on_event(self, event: Any) -> None:
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id
            self.handle_requires_action(event.data, run_id)

    @override
    def on_thread_created(self, thread):
        print(f"Thread Created: {thread.id}")
        self.update_message_status("Thread Created")

    @override
    def on_run_created(self, run):
        print(f"Run Created: {run.id}")
        self.current_run = run
        self.update_message_status("Run Created")

    @override
    def on_error(self, error: Any) -> None:
        print(f"Error 발생: {error}")
        self.update_message_status(f"Error: {error}")
        # 에러 보고 혹은 raise?
        # raise HTTPException(status_code=404, detail="Error 발생")

    @override
    def on_tool_call_created(self, tool_call):
        print(f"Tool Call Created: {tool_call.function}")
        self.update_message_status(f"Tool Call Created: {tool_call.function.name}")
        self.function_name = tool_call.function.name
        self.tool_id = tool_call.id
        # print({self.current_run.status})
        # print(f"\nassistant > {tool_call.type} {self.function_name}\n", flush=True)

    @override
    def handle_requires_action(self, data, run_id):
        tool_outputs = []
        self.update_message_status("Action Required")

        for tool in data.required_action.submit_tool_outputs.tool_calls:
            if tool.function.name == "getUltraSrtFcst":
                result = getUltraSrtFcst()
            if isinstance(result, dict):
                result = json.dumps(result, ensure_ascii=False)
            elif not isinstance(result, str):
                result = str(result)    
            tool_outputs.append({"tool_call_id" : tool.id, "output": result})
        self.submit_tool_outputs(tool_outputs)

    @override
    def submit_tool_outputs(self, tool_outputs):
      with client.beta.threads.runs.submit_tool_outputs_stream(
        thread_id=self.current_run.thread_id,
        run_id=self.current_run.id,
        tool_outputs=tool_outputs,
        event_handler=EventHandler(),
      ) as stream:
        for text in stream.text_deltas:
          print(text, end="", flush=True)
        print()

    @override
    def on_message_done(self, message: Message) -> None:
        print(message.content[0].text.value)
        # db에 업데이트 할것