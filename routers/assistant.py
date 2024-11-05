import json
from typing import Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from openai import AssistantEventHandler, OpenAI
from openai.types.beta.threads import Message
from openai import OpenAIError

from models import  AssistantMessageCreate, AssistantThread, AssistantMessage, User
from database import get_db, handle_exceptions
from functions import getUltraSrtFcst, register_medication_remind, register_hospital_remind, getHospBasisList
from utils.config import variables
from utils import get_current_user

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

### 스레드 관리 API ###
#
#    ooooooooooooo oooo                                           .o8 
#    8'   888   `8 `888                                          "888 
#         888       888 .oo.   oooo d8b  .ooooo.   .oooo.    .oooo888 
#         888       888P"Y88b  `888""8P d88' `88b `P  )88b  d88' `888 
#         888       888   888   888     888ooo888  .oP"888  888   888 
#         888       888   888   888     888    .o d8(  888  888   888 
#        o888o     o888o o888o d888b    `Y8bod8P' `Y888""8o `Y8bod88P"
# run state : creating, created, run, interrupt, done

# 스레드 생성
async def create_assistant_thread(user_id: int, db: Session = Depends(get_db)):
    thread = client.beta.threads.create()
    
    assistant_thread = AssistantThread(
        user_id=user_id,
        thread_id=thread.id
    )
    
    db.add(assistant_thread)
    db.commit()
    db.refresh(assistant_thread)
    
    return assistant_thread
    

# 특정 사용자의 스레드 조회
# id 말고 엑세스토큰으로 찾아야하지 않을까?
# 
@handle_exceptions
@router.get("/threads")
async def get_threads_by_user(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    threads = db.query(AssistantThread).filter(AssistantThread.user_id == user.user_id).all()
    if not threads:
        threads = await create_assistant_thread(user.user_id, db)

    return threads
# 스레드 삭제
@handle_exceptions
@router.delete("/threads")
async def delete_assistant_thread(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = db.query(AssistantThread).filter(AssistantThread.user_id == user.user_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="쓰레드를 찾을 수 없습니다.")
    client.beta.threads.delete(thread.thread_id)
    db.delete(thread)
    db.commit()
    return {"message": "쓰레드를 삭제했습니다."}
#    ooo        ooooo                                                           
#    `88.       .888'                                                           
#     888b     d'888   .ooooo.   .oooo.o  .oooo.o  .oooo.    .oooooooo  .ooooo. 
#     8 Y88. .P  888  d88' `88b d88(  "8 d88(  "8 `P  )88b  888' `88b  d88' `88b
#     8  `888'   888  888ooo888 `"Y88b.  `"Y88b.   .oP"888  888   888  888ooo888
#     8    Y     888  888    .o o.  )88b o.  )88b d8(  888  `88bod8P'  888    .o
#    o8o        o888o `Y8bod8P' 8""888P' 8""888P' `Y888""8o `8oooooo.  `Y8bod8P'
#                                                           d"     YD           
#                                                           "Y88888P'           

@handle_exceptions
@router.post("/message")
async def add_and_run_message(request: Request, message: AssistantMessageCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = db.query(AssistantThread).filter(AssistantThread.user_id == user.user_id).first()
    if not thread:
        thread = await create_assistant_thread(user.user_id, db)
    try:
        if thread.run_state != "None" or thread.run_state in ["thread.run.completed", "thread.run.cancelled"]: # completed, cancelled 상태를 분리해야할 필요가 있는지 확인해봐야함.
            response = client.beta.threads.messages.create(
                thread_id=thread.thread_id,
                role="user",
                content=message.content
            )
        elif thread.run_state in ["thread.run.failed"]: # 쓰레드 run 실패 후 메세지 요청 시 쓰레드 재생성?
            delete_assistant_thread(request, user, db)
            response = client.beta.threads.messages.create(
                thread_id=thread.thread_id,
                role="user",
                content=message.content
            )
            # raise HTTPException(status_code=400, detail=f"Thread run failed: {thread.run_state}")
        else:
            raise HTTPException(status_code=400, detail=f"메세지가 실행중입니다: {thread.run_state}")

    except OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"OpenAIError : 메세지 생성 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메세지 생성 실패: {str(e)}")

    new_message = AssistantMessage(
        thread_id=thread.thread_id,
        sender_type="user",
        content=message.content,
        created_at=datetime.utcnow()
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    with client.beta.threads.runs.stream(
        thread_id=thread.thread_id,
        assistant_id=variables.OPENAI_ASSISTANT_ID,
        instructions=__INSTRUCTIONS__,
        event_handler=EventHandler(db, thread.thread_id),
    ) as stream:
        stream.until_done()
    return {"status": "Message created and executed", "content": new_message.content}

# 특정 스레드의 메세지 조회
@handle_exceptions
@router.get("/messages")
async def get_messages_by_thread(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = db.query(AssistantThread).filter(AssistantThread.user_id == user.user_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="쓰레드를 찾을 수 없습니다.")

    messages = db.query(AssistantMessage).filter(AssistantMessage.thread_id == thread.thread_id).all()
    if not messages:
        raise HTTPException(status_code=404, detail="메세지를 찾을 수 없습니다.")
    
    return messages

@handle_exceptions
@router.get("/messages/latest")
async def get_latest_message(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = db.query(AssistantThread).filter(AssistantThread.user_id == user.user_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="쓰레드를 찾을 수 없습니다.")

    latest_message = db.query(AssistantMessage).filter(AssistantMessage.thread_id == thread.thread_id).order_by(desc(AssistantMessage.created_at)).first()
    if not latest_message:
        raise HTTPException(status_code=404, detail="최신 메세지를 찾을 수 없습니다.")
    
    return latest_message

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
    def __init__(self, db: Session, thread_id: str):
        super().__init__()
        self.db = db
        self.thread_id = thread_id

    def update_message_status(self, status: str):
        try:
            message = self.db.query(AssistantMessage).filter(AssistantMessage.thread_id == self.thread_id).order_by(desc(AssistantMessage.created_at)).first()
            if message:
                try:
                    self.db.query(AssistantThread).filter(AssistantThread.thread_id == self.thread_id).update({"run_state": status})
                    self.db.commit()
                    print(f"Thread status updated: {status}")
                except SQLAlchemyError as e:
                    self.db.rollback()
                    raise HTTPException(status_code=500, detail=f"메세지 상태 업데이트 실패: {str(e)}")
            else:
                raise HTTPException(status_code=404, detail="메세지가 존재하지 않습니다.")
        except SQLAlchemyError as e:
            raise HTTPException(status_code=500, detail=f"메세지 상태 업데이트 실패: {str(e)}")
    def on_event(self, event: Any) -> None:
        self.update_message_status(event.event)
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id
            self.handle_requires_action(event.data, run_id)
        if event.event == 'thread.run.cancelled':
            raise HTTPException(status_code=400, detail="쓰레드가 취소되었습니다.")
            # 어떤 상태에서 cancle이 발생하는지 확인해야함.
            # 내부적으로 어떻게 처리해야하는지
    @override
    def on_tool_call_created(self, tool_call):
        self.function_name = tool_call.function.name
        self.tool_id = tool_call.id

    @override
    def handle_requires_action(self, data, run_id):
        tool_outputs = []

        for tool in data.required_action.submit_tool_outputs.tool_calls:
            tool_arguments = json.loads(tool.function.arguments) if tool.function.arguments else {}
            if tool.function.name == "getUltraSrtFcst":
                result = getUltraSrtFcst(self.current_run.thread_id)
            if tool.function.name == "register_medication_remind":
                result = register_medication_remind(db=self.db, thread_id=self.current_run.thread_id, **tool_arguments)
            if tool.function.name == "register_hospital_remind":
                result = register_hospital_remind(db=self.db, thread_id=self.current_run.thread_id, **tool_arguments)
            if tool.function.name == "getHospBasisList":
                result = getHospBasisList(db=self.db, thread_id=self.current_run.thread_id, **tool_arguments)


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
            event_handler=EventHandler(self.db, self.thread_id),
        ) as stream:
            try:
                for text in stream.text_deltas:
                    self.db.commit()
            except Exception as e:
                self.db.rollback()
                raise HTTPException(status_code=500, detail=f"툴 아웃풋 제출 실패: {str(e)}")
    @override
    def on_text_delta(self, delta, snapshot):
        try:
            message = self.db.query(AssistantMessage).filter(AssistantMessage.thread_id == self.thread_id).order_by(desc(AssistantMessage.created_at)).first()
            if message:
                new_content = message.content + delta.value
                message.content = new_content
                self.db.commit()
            else:
                raise HTTPException(status_code=404, detail="메세지가 존재하지 않습니다.")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"메세지 델타 처리 실패: {str(e)}")
        
    @override
    def on_message_done(self, content: Message) -> None:
        try:
            message = self.db.query(AssistantMessage).filter(AssistantMessage.thread_id == self.thread_id).order_by(desc(AssistantMessage.created_at)).first()
            if message:
                message.content = content.content[0].text.value
                self.db.commit()
        except SQLAlchemyError as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"메세지 종료 처리 실패: {str(e)}")
