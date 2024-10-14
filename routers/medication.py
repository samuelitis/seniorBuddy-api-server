from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from datetime import time
from models import MedicationTimeCreate, MedicationTimeUpdate

router = APIRouter()

# 1. 복약 시간 설정
@router.post("/medication_times", response_model=int)
async def create_medication_time(medication_time: MedicationTimeCreate):
    """
    복약 시간을 설정하는 API.
    medication_name: 복약 이름
    dosage: 복약 용량
    medication_time: 복약 시간 (HH:MM:SS)
    
    이 API는 새로운 복약 시간을 데이터베이스에 추가합니다.
    """
    pass

# 2. 복약 시간 조회 (모든 복약 시간 조회)
@router.get("/medication_times", response_model=List[MedicationTimeCreate])
async def get_medication_times(user_id: int):
    """
    복약 시간을 조회하는 API.
    user_id: 사용자의 ID

    이 API는 특정 사용자의 모든 복약 시간을 반환합니다.
    """
    pass

# 2-1. 복약 시간 단일 조회 (특정 복약 시간 조회)
@router.get("/medication_times/{medication_id}", response_model=MedicationTimeCreate)
async def get_medication_time(medication_id: int):
    """
    특정 복약 시간을 조회하는 API.
    medication_id: 복약 시간의 ID

    이 API는 특정 복약 시간 데이터를 반환합니다.
    """
    pass

# 3. 복약 시간 수정
@router.put("/medication_times/{medication_id}")
async def update_medication_time(medication_id: int, medication_time: MedicationTimeUpdate):
    """
    복약 시간을 수정하는 API.
    medication_id: 수정할 복약 시간의 ID
    medication_time: 수정할 복약 정보 (복약 이름, 용량, 시간 중 하나 이상)

    이 API는 복약 시간을 수정하고 데이터베이스에 업데이트합니다.
    """
    pass

# 4. 복약 시간 삭제
@router.delete("/medication_times/{medication_id}")
async def delete_medication_time(medication_id: int):
    """
    복약 시간을 삭제하는 API.
    medication_id: 삭제할 복약 시간의 ID

    이 API는 복약 시간을 데이터베이스에서 삭제합니다.
    """
    pass

# 5. 복약 시간 알림 설정
@router.post("/medication_times/{medication_id}/notify")
async def set_medication_reminder(medication_id: int):
    """
    복약 알림 설정 API.
    medication_id: 알림을 설정할 복약 시간의 ID

    이 API는 복약 시간에 맞춰 알림을 설정합니다. 
    실제 알림 시스템은 외부 서비스나 cron 작업으로 구현될 수 있습니다.
    """
    pass