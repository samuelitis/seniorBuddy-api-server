from firebase_admin import credentials, messaging, initialize_app
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import User, AssistantThread

cred = credentials.Certificate("fcm_key.json")
initialize_app(cred)

def increase_font_size(db: Session, thread_id):
    try:
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()

        if user.fcm_token is None:
            return {"status": "failed", "message": "User has no FCM token"}
        
        data = messaging.Message(
            data={
                'type': 'increaseFontSize',
                'title': 'none',
                'body': 'none',
            },
            android=messaging.AndroidConfig(
                direct_boot_ok=True,
            ),
            token = user.fcm_token,
        )
        response = messaging.send(data)

        print('Successfully sent message:', response)
        return {"status": "success", "message": response}
    
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}

def decrease_font_size(db: Session, thread_id):
    try:
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()

        if user.fcm_token is None:
            return {"status": "failed", "message": "User has no FCM token"}
        
        data = messaging.Message(
            data={
                'type': 'decreaseFontSize',
                'title': 'none',
                'body': 'none',
            },
            android=messaging.AndroidConfig(
                direct_boot_ok=True,
            ),
            token = user.fcm_token,
        )
        response = messaging.send(data)

        print('Successfully sent message:', response)
        return {"status": "success", "message": response}
    
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}

def send_message(db: Session, thread_id, contact_name: str, content: str):
    try:
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()

        if user.fcm_token is None:
            return {"status": "failed", "message": "User has no FCM token"}
        
        data = messaging.Message(
            data={
                'type': 'sendMessage',
                'title': contact_name,
                'body': content,
            },
            android=messaging.AndroidConfig(
                direct_boot_ok=True,
            ),
            token = user.fcm_token,
        )
        response = messaging.send(data)

        print('Successfully sent message:', response)
        return {"status": "success", "message": response}

    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}


def call_contact(db: Session, thread_id, contact_name: str):
    try:
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()

        if user.fcm_token is None:
            return {"status": "failed", "message": "User has no FCM token"}
        
        data = messaging.Message(
            data={
                'type': 'callContact',
                'title': contact_name,
                'body': 'none',
            },
            android=messaging.AndroidConfig(
                direct_boot_ok=True,
            ),
            token = user.fcm_token,
        )
        response = messaging.send(data)

        print('Successfully sent message:', response)
        return {"status": "success", "message": response}
    
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}
    
    

def launch_specific_app(db: Session, thread_id, app_name: str, activity_name: str):
    try:
        user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()

        if user.fcm_token is None:
            return {"status": "error", "message": "User has no FCM token"}

        if app_name not in app_name_mapping:
            return {"status": "error", "message": "App not found"}

        app_name_mapping = {
            "카카오톡": "com.kakao.talk",
            "카메라": "com.sec.android.app.camera",
            "문자": "com.samsung.android.messaging",
            "전화": "com.samsung.android.dialer",
            "사진첩": "com.sec.android.gallery3d",
            "갤러리": "com.sec.android.gallery3d",
            "네이버밴드": "com.nhn.android.band"
        }

        data = messaging.Message(
            data={
                'type': 'launchSpecificApp',
                'title': app_name_mapping[app_name],
                'body': activity_name if activity_name else 'none',
            },
            android=messaging.AndroidConfig(
                direct_boot_ok=True,
            ),
            token = user.fcm_token,
        )
        response = messaging.send(data)

        print('Successfully sent message:', response)
        return {"status": "success", "message": response}
    
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "failed", "message": f"데이터베이스 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"status": "failed", "message": f"예상치 못한 오류가 발생했습니다: {str(e)}"}