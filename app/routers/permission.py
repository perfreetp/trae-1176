import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.attachment import LetterAuthorization, ShareLink, ShareAccessLog, Attachment
from app.models.letter import Letter, LetterPage
from app.schemas.attachment import (
    AuthorizationCreate, AuthorizationReview, AuthorizationOut,
    ShareLinkCreate, ShareLinkOut, ShareAccessVerify, ShareAccessLogOut,
)

router = APIRouter(prefix="/api/permissions", tags=["权限分享"])


@router.post("/authorizations", response_model=AuthorizationOut, summary="申请亲属授权")
def create_authorization(data: AuthorizationCreate, db: Session = Depends(get_db)):
    letter = db.query(Letter).filter(Letter.id == data.letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    auth = LetterAuthorization(
        letter_id=data.letter_id,
        applicant_id=1,
        status="pending",
        reason=data.reason,
    )
    db.add(auth)
    db.commit()
    db.refresh(auth)
    return auth


@router.get("/authorizations", response_model=List[AuthorizationOut], summary="获取授权申请列表")
def list_authorizations(
    status: str = "",
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(LetterAuthorization)
    if status:
        query = query.filter(LetterAuthorization.status == status)
    return query.order_by(LetterAuthorization.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/authorizations/{auth_id}", response_model=AuthorizationOut, summary="获取授权详情")
def get_authorization(auth_id: int, db: Session = Depends(get_db)):
    auth = db.query(LetterAuthorization).filter(LetterAuthorization.id == auth_id).first()
    if not auth:
        raise HTTPException(status_code=404, detail="授权申请不存在")
    return auth


@router.put("/authorizations/{auth_id}/review", response_model=AuthorizationOut, summary="审核授权申请")
def review_authorization(auth_id: int, data: AuthorizationReview, db: Session = Depends(get_db)):
    auth = db.query(LetterAuthorization).filter(LetterAuthorization.id == auth_id).first()
    if not auth:
        raise HTTPException(status_code=404, detail="授权申请不存在")
    if auth.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已处理")
    if data.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="无效的审核状态")
    auth.status = data.status
    auth.response = data.response
    auth.authorizer_id = 1
    auth.reviewed_at = datetime.utcnow()
    if data.status == "approved":
        letter = db.query(Letter).filter(Letter.id == auth.letter_id).first()
        if letter:
            letter.visibility = "family"
    db.commit()
    db.refresh(auth)
    return auth


@router.post("/share-links", response_model=ShareLinkOut, summary="创建分享链接")
def create_share_link(data: ShareLinkCreate, db: Session = Depends(get_db)):
    letter = db.query(Letter).filter(Letter.id == data.letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    token = secrets.token_urlsafe(24)
    expires_at = None
    if data.expires_hours is not None:
        try:
            hours = int(data.expires_hours)
            if hours != 0:
                expires_at = datetime.utcnow() + timedelta(hours=hours)
        except (ValueError, TypeError):
            pass
    preview_fields = data.preview_fields or "title,send_date,era"
    link = ShareLink(
        letter_id=data.letter_id,
        creator_id=1,
        token=token,
        access_level=data.access_level,
        max_views=data.max_views if data.max_views and data.max_views > 0 else 0,
        current_views=0,
        is_active="yes",
        password=data.password or "",
        preview_fields=preview_fields,
        expires_at=expires_at,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.get("/share-links", response_model=List[ShareLinkOut], summary="获取分享链接列表")
def list_share_links(letter_id: int = 0, db: Session = Depends(get_db)):
    query = db.query(ShareLink)
    if letter_id:
        query = query.filter(ShareLink.letter_id == letter_id)
    return query.order_by(ShareLink.created_at.desc()).all()


@router.post("/share-links/verify", summary="验证分享链接")
def verify_share_link(data: ShareAccessVerify, db: Session = Depends(get_db)):
    link = db.query(ShareLink).filter(ShareLink.token == data.token).first()
    if not link:
        raise HTTPException(status_code=404, detail="分享链接不存在")

    current_seq = db.query(ShareAccessLog).filter(
        ShareAccessLog.share_link_id == link.id
    ).count() + 1

    def _log(success: str, fail_reason: str = "", password_attempt: str = ""):
        db.add(ShareAccessLog(
            share_link_id=link.id,
            visitor_user_id=data.user_id,
            access_method="token",
            access_sequence=current_seq,
            password_attempt=password_attempt,
            success=success,
            fail_reason=fail_reason,
        ))
        db.commit()

    if link.max_views > 0 and link.current_views >= link.max_views:
        if link.is_active == "yes":
            link.is_active = "no"
            db.commit()
        _log("no", "max_views_reached")
        raise HTTPException(status_code=403, detail="分享链接已达到最大访问次数")
    if link.is_active != "yes":
        _log("no", "link_deactivated")
        raise HTTPException(status_code=403, detail="分享链接已停用")
    if link.expires_at and link.expires_at < datetime.utcnow():
        link.is_active = "no"
        db.commit()
        _log("no", "link_expired")
        raise HTTPException(status_code=403, detail="分享链接已过期")
    if link.password and link.password != data.password:
        _log("no", "wrong_password", "wrong")
        raise HTTPException(status_code=403, detail="访问密码错误")

    link.current_views += 1
    if link.max_views > 0 and link.current_views >= link.max_views:
        link.is_active = "no"
    db.commit()
    _log("yes", "", "ok" if link.password else "")

    letter = db.query(Letter).filter(Letter.id == link.letter_id).first()
    if not letter:
        return {"access_level": link.access_level, "letter": None}

    allowed_fields = set()
    if link.preview_fields:
        allowed_fields = {f.strip() for f in link.preview_fields.split(",") if f.strip()}

    field_map = {
        "title": ("title", letter.title),
        "description": ("description", letter.description),
        "send_date": ("send_date", letter.send_date),
        "send_location": ("send_location", letter.send_location),
        "receive_location": ("receive_location", letter.receive_location),
        "era": ("era", letter.era),
        "category": ("category", letter.category),
        "tags": ("tags", letter.tags),
    }

    if link.access_level == "view" and allowed_fields:
        letter_data = {"id": letter.id}
        for field_key, (field_name, field_val) in field_map.items():
            if field_key in allowed_fields:
                letter_data[field_name] = field_val
    else:
        letter_data = {
            "id": letter.id,
            "title": letter.title,
            "description": letter.description,
            "send_date": letter.send_date,
            "send_location": letter.send_location,
            "receive_location": letter.receive_location,
            "era": letter.era,
            "category": letter.category,
            "tags": letter.tags,
        }

    pages = db.query(LetterPage).filter(
        LetterPage.letter_id == letter.id
    ).order_by(LetterPage.page_number).all()
    letter_data["pages"] = [
        {"page_number": p.page_number, "transcription": p.transcription}
        for p in pages
    ]

    attachments = db.query(Attachment).filter(
        Attachment.letter_id == letter.id
    ).all()
    letter_data["attachments"] = [
        {"id": a.id, "file_name": a.file_name, "media_type": a.media_type, "file_size": a.file_size}
        for a in attachments
    ]

    return {
        "access_level": link.access_level,
        "preview_fields": link.preview_fields,
        "current_views": link.current_views,
        "max_views": link.max_views,
        "letter": letter_data,
    }


@router.put("/share-links/{link_id}/revoke", response_model=ShareLinkOut, summary="撤销分享链接")
def revoke_share_link(link_id: int, db: Session = Depends(get_db)):
    link = db.query(ShareLink).filter(ShareLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="分享链接不存在")
    if link.is_active != "yes":
        raise HTTPException(status_code=400, detail="分享链接已处于停用状态")
    link.is_active = "no"
    db.commit()
    db.refresh(link)
    return link


@router.put("/share-links/{link_id}/restore", response_model=ShareLinkOut, summary="恢复分享链接")
def restore_share_link(link_id: int, db: Session = Depends(get_db)):
    link = db.query(ShareLink).filter(ShareLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="分享链接不存在")
    if link.is_active == "yes":
        raise HTTPException(status_code=400, detail="分享链接已是活跃状态")
    if link.expires_at and link.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="分享链接已过期，无法恢复")
    if link.max_views > 0 and link.current_views >= link.max_views:
        raise HTTPException(status_code=400, detail="分享链接已达访问上限，无法恢复")
    link.is_active = "yes"
    db.commit()
    db.refresh(link)
    return link


@router.get("/share-links/{link_id}/logs", response_model=List[ShareAccessLogOut], summary="获取分享链接访问记录")
def list_share_access_logs(link_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    link = db.query(ShareLink).filter(ShareLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="分享链接不存在")
    return db.query(ShareAccessLog).filter(
        ShareAccessLog.share_link_id == link_id
    ).order_by(ShareAccessLog.created_at.desc()).offset(skip).limit(limit).all()


@router.delete("/share-links/{link_id}", summary="删除分享链接")
def delete_share_link(link_id: int, db: Session = Depends(get_db)):
    link = db.query(ShareLink).filter(ShareLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="分享链接不存在")
    db.query(ShareAccessLog).filter(ShareAccessLog.share_link_id == link_id).delete()
    db.delete(link)
    db.commit()
    return {"detail": "已删除"}
