from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.letter import Letter, LetterPage
from app.models.person import Person
from app.schemas.letter import (
    LetterCreate, LetterUpdate, LetterOut, LetterOutSimple,
    LetterPageCreate, LetterPageUpdate, LetterPageOut,
    VisibilityUpdate, LetterActionRequest,
)
from app.utils.permissions import require_permission, update_last_active

router = APIRouter(prefix="/api/letters", tags=["信件档案"])


@router.post("", response_model=LetterOut, summary="创建信件")
def create_letter(data: LetterCreate, db: Session = Depends(get_db)):
    require_permission(db, data.family_space_id, data.operator_id, "manage_letters")
    if data.sender_id:
        sender = db.query(Person).filter(Person.id == data.sender_id).first()
        if not sender:
            raise HTTPException(status_code=400, detail="寄件人不存在")
        if sender.family_space_id != data.family_space_id:
            raise HTTPException(status_code=400, detail="寄件人不属于当前家庭馆")
    if data.receiver_id:
        receiver = db.query(Person).filter(Person.id == data.receiver_id).first()
        if not receiver:
            raise HTTPException(status_code=400, detail="收件人不存在")
        if receiver.family_space_id != data.family_space_id:
            raise HTTPException(status_code=400, detail="收件人不属于当前家庭馆")
    letter = Letter(
        family_space_id=data.family_space_id,
        title=data.title,
        description=data.description,
        sender_id=data.sender_id,
        receiver_id=data.receiver_id,
        send_location=data.send_location,
        receive_location=data.receive_location,
        send_date=data.send_date,
        receive_date=data.receive_date,
        era=data.era,
        category=data.category,
        tags=data.tags,
        visibility=data.visibility,
        created_by=data.operator_id,
    )
    db.add(letter)
    update_last_active(db, data.family_space_id, data.operator_id)
    db.commit()
    db.refresh(letter)
    return letter


@router.get("", response_model=List[LetterOutSimple], summary="获取信件列表")
def list_letters(
    family_space_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(Letter)
    if family_space_id:
        query = query.filter(Letter.family_space_id == family_space_id)
    return query.order_by(Letter.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{letter_id}", response_model=LetterOut, summary="获取信件详情")
def get_letter(letter_id: int, db: Session = Depends(get_db)):
    letter = db.query(Letter).filter(Letter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    return letter


@router.put("/{letter_id}", response_model=LetterOut, summary="更新信件")
def update_letter(letter_id: int, data: LetterUpdate, db: Session = Depends(get_db)):
    letter = db.query(Letter).filter(Letter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    require_permission(db, letter.family_space_id, data.operator_id, "manage_letters")
    if data.sender_id is not None:
        sender = db.query(Person).filter(Person.id == data.sender_id).first()
        if not sender:
            raise HTTPException(status_code=400, detail="寄件人不存在")
        if sender.family_space_id != letter.family_space_id:
            raise HTTPException(status_code=400, detail="寄件人不属于当前家庭馆")
    if data.receiver_id is not None:
        receiver = db.query(Person).filter(Person.id == data.receiver_id).first()
        if not receiver:
            raise HTTPException(status_code=400, detail="收件人不存在")
        if receiver.family_space_id != letter.family_space_id:
            raise HTTPException(status_code=400, detail="收件人不属于当前家庭馆")
    update_data = data.model_dump(exclude_unset=True, exclude={"operator_id"})
    for key, value in update_data.items():
        setattr(letter, key, value)
    from datetime import datetime
    letter.updated_at = datetime.utcnow()
    update_last_active(db, letter.family_space_id, data.operator_id)
    db.commit()
    db.refresh(letter)
    return letter


@router.delete("/{letter_id}", summary="删除信件")
def delete_letter(letter_id: int, data: LetterActionRequest, db: Session = Depends(get_db)):
    letter = db.query(Letter).filter(Letter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    require_permission(db, letter.family_space_id, data.operator_id, "manage_letters")
    update_last_active(db, letter.family_space_id, data.operator_id)
    db.delete(letter)
    db.commit()
    return {"detail": "已删除"}


@router.post("/{letter_id}/pages", response_model=LetterPageOut, summary="添加信件页面")
def add_page(letter_id: int, data: LetterPageCreate, db: Session = Depends(get_db)):
    letter = db.query(Letter).filter(Letter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    require_permission(db, letter.family_space_id, data.operator_id, "manage_letters")
    page = LetterPage(
        letter_id=letter_id,
        page_number=data.page_number,
        image_path=data.image_path,
        transcription=data.transcription,
        notes=data.notes,
    )
    update_last_active(db, letter.family_space_id, data.operator_id)
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


@router.get("/{letter_id}/pages", response_model=List[LetterPageOut], summary="获取信件页面列表")
def list_pages(letter_id: int, db: Session = Depends(get_db)):
    return db.query(LetterPage).filter(LetterPage.letter_id == letter_id).order_by(LetterPage.page_number).all()


@router.put("/{letter_id}/pages/{page_id}", response_model=LetterPageOut, summary="更新信件页面释文")
def update_page(letter_id: int, page_id: int, data: LetterPageUpdate, db: Session = Depends(get_db)):
    page = db.query(LetterPage).filter(
        LetterPage.id == page_id,
        LetterPage.letter_id == letter_id,
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")
    letter = db.query(Letter).filter(Letter.id == letter_id).first()
    if letter:
        require_permission(db, letter.family_space_id, data.operator_id, "manage_letters")
    update_data = data.model_dump(exclude_unset=True, exclude={"operator_id"})
    for key, value in update_data.items():
        setattr(page, key, value)
    from datetime import datetime
    page.updated_at = datetime.utcnow()
    if letter:
        update_last_active(db, letter.family_space_id, data.operator_id)
    db.commit()
    db.refresh(page)
    return page


@router.delete("/{letter_id}/pages/{page_id}", summary="删除信件页面")
def delete_page(letter_id: int, page_id: int, data: LetterActionRequest, db: Session = Depends(get_db)):
    page = db.query(LetterPage).filter(
        LetterPage.id == page_id,
        LetterPage.letter_id == letter_id,
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")
    letter = db.query(Letter).filter(Letter.id == letter_id).first()
    if letter:
        require_permission(db, letter.family_space_id, data.operator_id, "manage_letters")
        update_last_active(db, letter.family_space_id, data.operator_id)
    db.delete(page)
    db.commit()
    return {"detail": "已删除"}


@router.put("/{letter_id}/visibility", response_model=LetterOut, summary="设置信件公开范围")
def set_visibility(letter_id: int, data: VisibilityUpdate, db: Session = Depends(get_db)):
    letter = db.query(Letter).filter(Letter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    require_permission(db, letter.family_space_id, data.operator_id, "manage_letters")
    if data.visibility not in ("private", "family", "public"):
        raise HTTPException(status_code=400, detail="无效的可见性设置")
    letter.visibility = data.visibility
    from datetime import datetime
    letter.updated_at = datetime.utcnow()
    update_last_active(db, letter.family_space_id, data.operator_id)
    db.commit()
    db.refresh(letter)
    return letter


@router.put("/{letter_id}/star", response_model=LetterOut, summary="收藏/取消收藏信件")
def toggle_star(letter_id: int, data: LetterActionRequest, db: Session = Depends(get_db)):
    letter = db.query(Letter).filter(Letter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    require_permission(db, letter.family_space_id, data.operator_id, "view_content")
    letter.is_starred = not letter.is_starred
    from datetime import datetime
    letter.updated_at = datetime.utcnow()
    update_last_active(db, letter.family_space_id, data.operator_id)
    db.commit()
    db.refresh(letter)
    return letter
