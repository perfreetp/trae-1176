from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class SearchQuery(BaseModel):
    keyword: Optional[str] = ""
    family_space_id: Optional[int] = None
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    era: Optional[str] = ""
    date_from: Optional[str] = ""
    date_to: Optional[str] = ""
    category: Optional[str] = ""
    tags: Optional[str] = ""
    visibility: Optional[str] = ""
    is_starred: Optional[bool] = None
    page: Optional[int] = 1
    page_size: Optional[int] = 20


class SearchResults(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Any]


class StatOverview(BaseModel):
    total_letters: int
    total_persons: int
    total_attachments: int
    total_exhibitions: int
    total_comments: int
    letters_by_era: Optional[dict] = None
    letters_by_category: Optional[dict] = None
    letters_by_month: Optional[dict] = None


class CommunicationRecord(BaseModel):
    sender_name: str
    receiver_name: str
    letter_count: int
    earliest_date: Optional[str] = ""
    latest_date: Optional[str] = ""


class CommunicationGraphOut(BaseModel):
    nodes: List[dict]
    edges: List[dict]
