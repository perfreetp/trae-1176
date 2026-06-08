import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.attachment import Attachment
from app.models.letter import Letter
from app.schemas.attachment import AttachmentOut

router = APIRouter(prefix="/api/attachments", tags=["影像附件"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/x-m4a"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_AUDIO_TYPES


def _save_file(file: UploadFile, sub_dir: str) -> str:
    dir_path = os.path.join(UPLOAD_DIR, sub_dir)
    os.makedirs(dir_path, exist_ok=True)
    ext = os.path.splitext(file.filename or "file")[1] or ".bin"
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(dir_path, filename)
    with open(file_path, "wb") as f:
        content = file.file.read()
        f.write(content)
    return os.path.join(sub_dir, filename)


@router.post("/{letter_id}/upload", response_model=AttachmentOut, summary="上传信件附件（图片/录音）")
async def upload_attachment(
    letter_id: int,
    file: UploadFile = File(...),
    media_type: str = "image",
    description: str = "",
    db: Session = Depends(get_db),
):
    letter = db.query(Letter).filter(Letter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.content_type}")
    content = await file.read()
    file_size = len(content)
    await file.seek(0)
    sub_dir = "images" if media_type == "image" else "audio"
    relative_path = _save_file(file, sub_dir)
    attachment = Attachment(
        letter_id=letter_id,
        file_name=file.filename or "unnamed",
        file_path=relative_path,
        file_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        media_type=media_type,
        description=description,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.post("/{letter_id}/upload-page-image", response_model=AttachmentOut, summary="上传信件页面图片")
async def upload_page_image(
    letter_id: int,
    file: UploadFile = File(...),
    page_number: int = 1,
    db: Session = Depends(get_db),
):
    from app.models.letter import LetterPage
    letter = db.query(Letter).filter(Letter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    content = await file.read()
    file_size = len(content)
    await file.seek(0)
    relative_path = _save_file(file, "pages")
    page = db.query(LetterPage).filter(
        LetterPage.letter_id == letter_id,
        LetterPage.page_number == page_number,
    ).first()
    if page:
        page.image_path = relative_path
        from datetime import datetime
        page.updated_at = datetime.utcnow()
    else:
        page = LetterPage(
            letter_id=letter_id,
            page_number=page_number,
            image_path=relative_path,
        )
        db.add(page)
    attachment = Attachment(
        letter_id=letter_id,
        file_name=file.filename or "page_image",
        file_path=relative_path,
        file_type=file.content_type or "image/jpeg",
        file_size=file_size,
        media_type="image",
        description=f"第{page_number}页原图",
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/{letter_id}", response_model=List[AttachmentOut], summary="获取信件附件列表")
def list_attachments(letter_id: int, db: Session = Depends(get_db)):
    return db.query(Attachment).filter(Attachment.letter_id == letter_id).all()


@router.delete("/{attachment_id}", summary="删除附件")
def delete_attachment(attachment_id: int, db: Session = Depends(get_db)):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")
    full_path = os.path.join(UPLOAD_DIR, attachment.file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
    db.delete(attachment)
    db.commit()
    return {"detail": "已删除"}
