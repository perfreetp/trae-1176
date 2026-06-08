from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class LetterCreate(BaseModel):
    family_space_id: int
    title: str
    description: Optional[str] = ""
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    send_location: Optional[str] = ""
    receive_location: Optional[str] = ""
    send_date: Optional[str] = ""
    receive_date: Optional[str] = ""
    era: Optional[str] = ""
    category: Optional[str] = ""
    tags: Optional[str] = ""
    visibility: Optional[str] = "family"
    status: Optional[str] = "draft"
    operator_id: int


class LetterUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    send_location: Optional[str] = None
    receive_location: Optional[str] = None
    send_date: Optional[str] = None
    receive_date: Optional[str] = None
    era: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    visibility: Optional[str] = None
    is_starred: Optional[bool] = None
    status: Optional[str] = None
    operator_id: int


class LetterPageCreate(BaseModel):
    page_number: int
    image_path: Optional[str] = ""
    transcription: Optional[str] = ""
    notes: Optional[str] = ""
    operator_id: int


class LetterPageUpdate(BaseModel):
    image_path: Optional[str] = None
    transcription: Optional[str] = None
    notes: Optional[str] = None
    operator_id: int


class VisibilityUpdate(BaseModel):
    visibility: str
    operator_id: int


class LetterActionRequest(BaseModel):
    operator_id: int


class PublishRequest(BaseModel):
    operator_id: int


class LetterPageOut(BaseModel):
    id: int
    letter_id: int
    page_number: int
    image_path: Optional[str] = ""
    transcription: Optional[str] = ""
    notes: Optional[str] = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LetterOut(BaseModel):
    id: int
    family_space_id: int
    title: str
    description: Optional[str] = ""
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    send_location: Optional[str] = ""
    receive_location: Optional[str] = ""
    send_date: Optional[str] = ""
    receive_date: Optional[str] = ""
    era: Optional[str] = ""
    category: Optional[str] = ""
    tags: Optional[str] = ""
    visibility: str
    is_starred: bool
    status: Optional[str] = "draft"
    created_by: int
    created_at: datetime
    updated_at: datetime
    pages: Optional[List[LetterPageOut]] = []

    model_config = {"from_attributes": True}


class LetterOutSimple(BaseModel):
    id: int
    family_space_id: int
    title: str
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    send_date: Optional[str] = ""
    era: Optional[str] = ""
    visibility: str
    is_starred: bool
    status: Optional[str] = "draft"
    created_at: datetime

    model_config = {"from_attributes": True}
