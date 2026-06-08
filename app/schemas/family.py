from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    password: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    display_name: Optional[str] = ""


class UserOut(BaseModel):
    id: int
    username: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    display_name: Optional[str] = ""
    avatar: Optional[str] = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class FamilySpaceCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    cover_image: Optional[str] = ""
    is_public: Optional[bool] = False


class FamilySpaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    is_public: Optional[bool] = None


class FamilySpaceOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = ""
    cover_image: Optional[str] = ""
    creator_id: int
    is_public: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FamilyMemberOut(BaseModel):
    id: int
    family_space_id: int
    user_id: int
    role: str
    nickname: Optional[str] = ""
    joined_at: datetime

    model_config = {"from_attributes": True}


class FamilyMemberAdd(BaseModel):
    user_id: int
    role: Optional[str] = "member"
    nickname: Optional[str] = ""


class InvitationCreate(BaseModel):
    invitee_user_id: Optional[int] = None
    invitee_phone: Optional[str] = ""
    invitee_email: Optional[str] = ""
    message: Optional[str] = ""


class InvitationOut(BaseModel):
    id: int
    family_space_id: int
    inviter_id: int
    invitee_user_id: Optional[int] = None
    invitee_phone: Optional[str] = ""
    invitee_email: Optional[str] = ""
    code: str
    status: str
    message: Optional[str] = ""
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class InvitationAccept(BaseModel):
    code: str
    user_id: int
