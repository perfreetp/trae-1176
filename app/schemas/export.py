from pydantic import BaseModel
from typing import Optional, List


class ExportRequest(BaseModel):
    family_space_id: int
    format: Optional[str] = "zip"
    include_attachments: Optional[bool] = True
    include_transcriptions: Optional[bool] = True
    include_metadata: Optional[bool] = True
    include_handover: Optional[bool] = True
    letter_ids: Optional[List[int]] = None
    date_from: Optional[str] = ""
    date_to: Optional[str] = ""


class PreservationItem(BaseModel):
    id: int
    title: str
    format: str
    size: int
    checksum: Optional[str] = ""
    status: str


class PreservationManifest(BaseModel):
    family_space_id: int
    family_name: str
    export_date: str
    total_items: int
    items: List[PreservationItem]


class HandoverLetterSummary(BaseModel):
    id: int
    title: str
    page_count: int
    attachment_count: int
    visibility: str
    share_link_count: int
    checksum: Optional[str] = ""


class HandoverSummary(BaseModel):
    family_space_id: int
    family_name: str
    export_date: str
    total_letters: int
    total_pages: int
    total_attachments: int
    active_share_links: int
    total_share_access: int
    letters: List[HandoverLetterSummary]


class ExportTaskOut(BaseModel):
    task_id: str
    status: str
    download_url: Optional[str] = ""
    created_at: str
    file_size: Optional[int] = 0
