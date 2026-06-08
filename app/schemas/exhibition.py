from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ExhibitionCreate(BaseModel):
    family_space_id: int
    title: str
    description: Optional[str] = ""
    cover_image: Optional[str] = ""


class ExhibitionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    is_published: Optional[str] = None
    sort_order: Optional[int] = None


class ExhibitionItemCreate(BaseModel):
    letter_id: int
    sort_order: Optional[int] = 0
    caption: Optional[str] = ""
    section_title: Optional[str] = ""


class ExhibitionItemUpdate(BaseModel):
    sort_order: Optional[int] = None
    caption: Optional[str] = None
    section_title: Optional[str] = None


class ExhibitionItemOut(BaseModel):
    id: int
    exhibition_id: int
    letter_id: int
    sort_order: int
    caption: Optional[str] = ""
    section_title: Optional[str] = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class ExhibitionOut(BaseModel):
    id: int
    family_space_id: int
    title: str
    description: Optional[str] = ""
    cover_image: Optional[str] = ""
    curator_id: int
    is_published: str
    sort_order: int
    created_at: datetime
    updated_at: datetime
    items: Optional[List[ExhibitionItemOut]] = []

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    letter_id: int
    content: str
    visitor_name: Optional[str] = ""
    source: Optional[str] = "web"


class CommentOut(BaseModel):
    id: int
    letter_id: int
    user_id: Optional[int] = None
    visitor_name: Optional[str] = ""
    content: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}
