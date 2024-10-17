import os, json
from typing import Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Request, BackgroundTasks
from sqlalchemy.orm import Session
from asyncio import TimeoutError, wait_for
from openai import AsyncAssistantEventHandler, AsyncOpenAI, AssistantEventHandler, OpenAI
from openai.types.beta.threads import Text, TextDelta
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import ToolCall, RunStep
from openai.types.beta import AssistantStreamEvent

from models import AssistantThreadCreate, AssistantMessageCreate, AssistantThread, AssistantMessage, User
from database import get_db
from functions import getUltraSrtFcst
from utils.config import variables
from utils import token_manager, get_current_user

__INSTRUCTIONS__ = """
당신은 어르신을 돕는 시니어 도우미입니다. 
당신의 이름은 '애비'입니다. 
답변은 짧게 구성을 하며, 어르신을 대할 때는 친근하고 따뜻한 말투를 사용해야합니다.
복잡한 정보는 간단하게 풀어 설명하고, 쉬운 단어를 사용하여 어르신이 편하게 이해할 수 있도록 돕습니다.
어르신이 이전 대화를 기억하지 못할 때, 다시한번 말하기도 해야합니다.
사용자는 대화 모드를 수행중입니다. 특수문자를 사용하지말고 대화형식으로 답변하세요
"""

router = APIRouter()
assistant_id = variables.OPENAI_ASSISTANT_ID
openai_api_key = variables.OPENAI_API_KEY
client = OpenAI(api_key=openai_api_key)

def override(method: Any) -> Any:
    return method

def process_message_in_background(thread_id: str, message_id: str, db: Session):
    try:
        # 비동기 스트리밍 작업 처리
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            instructions=__INSTRUCTIONS__,
            event_handler=EventHandler(db, thread_id, message_id),
        ) as stream:
            stream.until_done()  # 비동기 작업 처리
    except Exception as e:
        print(f"Error in background task: {str(e)}")

### 스레드 관리 API ###
#
#    ooooooooooooo oooo                                           .o8 
#    8'   888   `8 `888                                          "888 
#         888       888 .oo.   oooo d8b  .ooooo.   .oooo.    .oooo888 
#         888       888P"Y88b  `888""8P d88' `88b `P  )88b  d88' `888 
#         888       888   888   888     888ooo888  .oP"888  888   888 
#         888       888   888   888     888    .o d8(  888  888   888 
#        o888o     o888o o888o d888b    `Y8bod8P' `Y888""8o `Y8bod88P"
# run state : created, running, processing, waiting, done

# 스레드 생성
async def create_assistant_thread(user_id: int, db: Session = Depends(get_db)):
    thread = client.beta.threads.create()
    
    assistant_thread = AssistantThread(
        user_id=user_id,
        thread_id=thread.id,
        run_state="created"
    )
    
    db.add(assistant_thread)
    db.commit()
    db.refresh(assistant_thread)
    
    return assistant_thread

# 특정 사용자의 스레드 조회
# id 말고 엑세스토큰으로 찾아야하지 않을까?
# 
@router.get("/threads")
async def get_threads_by_user(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    threads = db.query(AssistantThread).filter(AssistantThread.user_id == user.user_id).all()
    if not threads:
        threads = await create_assistant_thread(user.user_id, db)

    return threads
# 스레드 삭제
@router.delete("/threads")
async def delete_assistant_thread(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = db.query(AssistantThread).filter(AssistantThread.user_id == user.user_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found", headers={"X-Error": "Thread not found"})
    
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
@router.post("/message", response_model=AssistantMessageCreate)
async def add_and_run_message(request: Request, message: AssistantMessageCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = db.query(AssistantThread).filter(AssistantThread.user_id == user.user_id).first()
    if not thread:
        thread = create_assistant_thread(user.user_id, db)

    running_states = ["run"]
    latest_message = db.query(AssistantMessage).filter(AssistantMessage.thread_id == thread.thread_id).order_by(AssistantMessage.created_at.desc()).first()

    if latest_message and latest_message.status_type in running_states:
        raise HTTPException(status_code=400, detail="A message is already in progress", headers={"X-Error": "A message is already in progress"})

    response = client.beta.threads.messages.create(
        thread_id=thread.thread_id,
        role="user",
        content=message.content
    )

    new_message = AssistantMessage(
        thread_id=thread.thread_id,
        sender_type="user",
        status_type="init",
        content=message.content,
        created_at=datetime.utcnow()
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    try:
        await wait_for(
            client.beta.threads.runs.stream(
                thread_id=thread.thread_id,
                instructions=__INSTRUCTIONS__,
                event_handler=EventHandler(db, thread.thread_id, new_message.message_id),
            ).until_done(),
            timeout=60.0  # 60초 이내에 응답을 받아야 함
        )
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Stream processing timeout", headers={"X-Error": "Stream processing timeout"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream execution failed: {str(e)}", headers={"X-Error": f"Stream execution failed: {str(e)}"})

    return {"status": "Message created and executed", "message": new_message.content}

# 특정 스레드의 메시지 조회
@router.get("/messages")
async def get_messages_by_thread(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = db.query(AssistantThread).filter(AssistantThread.user_id == user.user_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found", headers={"X-Error": "Thread not found"})

    messages = db.query(AssistantMessage).filter(AssistantMessage.thread_id == thread.thread_id).all()
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for this thread", headers={"X-Error": "No messages found for this thread"})
    
    return messages


#       .oooooo.                                               .o.       ooooo
#      d8P'  `Y8b                                             .888.      `888'
#     888      888 oo.ooooo.   .ooooo.  ooo. .oo.            .8"888.      888 
#     888      888  888' `88b d88' `88b `888P"Y88b          .8' `888.     888 
#     888      888  888   888 888ooo888  888   888         .88ooo8888.    888 
#     `88b    d88'  888   888 888    .o  888   888        .8'     `888.   888 
#      `Y8bood8P'   888bod8P' `Y8bod8P' o888o o888o      o88o     o8888o o888o
#                   888                                                       
#                  o888o                                                 

class EventHandler(AssistantEventHandler):
    def __init__(self, db: Session, thread_id: str, message_id: str):
        self.db = db
        self.thread_id = thread_id
        self.message_id = message_id
        self.current_run = None
        self.status = "initializing"

    def update_message_status(self, status: str):
        message = self.db.query(AssistantMessage).filter(AssistantMessage.message_id == self.message_id).first()
        if message:
            self.db.query(AssistantThread).filter(AssistantThread.thread_id == self.thread_id).update({"run_state": status})
            self.db.commit()
            print(f"Thread {self.thread_id} status updated to {status}")

    def on_event(self, event: Any) -> None:
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id
            self.update_message_status("requires_action")
            self.handle_requires_action(event.data, run_id)

    @override
    def on_run_created(self, run):
        self.current_run = run

    @override
    def on_error(self, error: Any) -> None:
        print(f'Error: {error}')

    @override
    def on_tool_call_created(self, tool_call):
        self.function_name = tool_call.function.name
        self.tool_id = tool_call.id


    @override
    def handle_requires_action(self, data, run_id):
        tool_outputs = []

        for tool in data.required_action.submit_tool_outputs.tool_calls:
            if tool.function.name == "getUltraSrtFcst":
                result = getUltraSrtFcst()
            if isinstance(result, dict):
                result = json.dumps(result, ensure_ascii=False)
            elif not isinstance(result, str):
                result = str(result)    
            tool_outputs.append({"tool_call_id" : tool.id, "output": result})
        self.submit_tool_outputs(tool_outputs, run_id)

    @override
    def submit_tool_outputs(self, tool_outputs, run_id):
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
        self.db.query(AssistantThread).filter(AssistantThread.thread_id == self.thread_id).update({"run_state": "done"})
        self.db.query(AssistantThread).filter(AssistantThread.thread_id == self.thread_id).update({"content": message})
        self.db.commit()
        print(f"Message {self.message_id} processing done")
        print(f"Thread {self.thread_id} status updated to done")
