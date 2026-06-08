from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AuditLogOut(BaseModel):
    id: int
    family_space_id: int
    operator_id: int
    action: str
    target_type: Optional[str] = ""
    target_id: Optional[int] = 0
    before_value: Optional[str] = ""
    after_value: Optional[str] = ""
    detail: Optional[str] = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogQuery(BaseModel):
    family_space_id: int
    operator_id: Optional[int] = None
    action: Optional[str] = ""
    action_prefix: Optional[str] = ""
    time_from: Optional[str] = ""
    time_to: Optional[str] = ""
    page: Optional[int] = 1
    page_size: Optional[int] = 20
