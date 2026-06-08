from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AttachmentOut(BaseModel):
    id: int
    letter_id: int
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    media_type: str
    description: Optional[str] = ""
    duration: Optional[int] = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthorizationCreate(BaseModel):
    letter_id: int
    reason: Optional[str] = ""


class AuthorizationReview(BaseModel):
    status: str
    response: Optional[str] = ""


class AuthorizationOut(BaseModel):
    id: int
    letter_id: int
    applicant_id: int
    authorizer_id: Optional[int] = None
    status: str
    reason: Optional[str] = ""
    response: Optional[str] = ""
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ShareLinkCreate(BaseModel):
    letter_id: int
    access_level: Optional[str] = "view"
    max_views: Optional[int] = 0
    password: Optional[str] = ""
    expires_hours: Optional[int] = None
    preview_fields: Optional[str] = "title,send_date,era"


class ShareLinkOut(BaseModel):
    id: int
    letter_id: int
    creator_id: int
    token: str
    access_level: str
    max_views: int
    current_views: int
    is_active: str
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ShareAccessVerify(BaseModel):
    token: str
    password: Optional[str] = ""
    user_id: Optional[int] = None


class ShareAccessLogOut(BaseModel):
    id: int
    share_link_id: int
    visitor_ip: Optional[str] = ""
    visitor_user_id: Optional[int] = None
    access_method: str
    access_sequence: int = 0
    password_attempt: Optional[str] = ""
    success: str
    fail_reason: Optional[str] = ""
    created_at: datetime

    model_config = {"from_attributes": True}
