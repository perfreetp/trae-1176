from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.exhibition import Exhibition, ExhibitionItem, Comment
from app.models.letter import Letter
from app.schemas.exhibition import (
    ExhibitionCreate, ExhibitionUpdate, ExhibitionOut,
    ExhibitionItemCreate, ExhibitionItemUpdate, ExhibitionItemOut,
    CommentCreate, CommentOut
)

router = APIRouter(prefix="/api/exhibitions", tags=["展陈专题"])


@router.post("", response_model=ExhibitionOut, summary="创建专题展览")
def create_exhibition(data: ExhibitionCreate, db: Session = Depends(get_db)):
    exhibition = Exhibition(
        family_space_id=data.family_space_id,
        title=data.title,
        description=data.description,
        cover_image=data.cover_image,
        curator_id=1,
    )
    db.add(exhibition)
    db.commit()
    db.refresh(exhibition)
    return exhibition


@router.get("", response_model=List[ExhibitionOut], summary="获取展览列表")
def list_exhibitions(
    family_space_id: Optional[int] = None,
    is_published: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(Exhibition)
    if family_space_id:
        query = query.filter(Exhibition.family_space_id == family_space_id)
    if is_published is not None:
        query = query.filter(Exhibition.is_published == is_published)
    return query.order_by(Exhibition.sort_order, Exhibition.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{exhibition_id}", response_model=ExhibitionOut, summary="获取展览详情")
def get_exhibition(exhibition_id: int, db: Session = Depends(get_db)):
    exhibition = db.query(Exhibition).filter(Exhibition.id == exhibition_id).first()
    if not exhibition:
        raise HTTPException(status_code=404, detail="展览不存在")
    return exhibition


@router.put("/{exhibition_id}", response_model=ExhibitionOut, summary="更新展览信息")
def update_exhibition(exhibition_id: int, data: ExhibitionUpdate, db: Session = Depends(get_db)):
    exhibition = db.query(Exhibition).filter(Exhibition.id == exhibition_id).first()
    if not exhibition:
        raise HTTPException(status_code=404, detail="展览不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(exhibition, key, value)
    from datetime import datetime
    exhibition.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(exhibition)
    return exhibition


@router.delete("/{exhibition_id}", summary="删除展览")
def delete_exhibition(exhibition_id: int, db: Session = Depends(get_db)):
    exhibition = db.query(Exhibition).filter(Exhibition.id == exhibition_id).first()
    if not exhibition:
        raise HTTPException(status_code=404, detail="展览不存在")
    db.delete(exhibition)
    db.commit()
    return {"detail": "已删除"}


@router.post("/{exhibition_id}/publish", response_model=ExhibitionOut, summary="发布/取消发布展览")
def toggle_publish(exhibition_id: int, db: Session = Depends(get_db)):
    exhibition = db.query(Exhibition).filter(Exhibition.id == exhibition_id).first()
    if not exhibition:
        raise HTTPException(status_code=404, detail="展览不存在")
    exhibition.is_published = "no" if exhibition.is_published == "yes" else "yes"
    from datetime import datetime
    exhibition.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(exhibition)
    return exhibition


@router.post("/{exhibition_id}/items", response_model=ExhibitionItemOut, summary="添加展览展品")
def add_exhibition_item(exhibition_id: int, data: ExhibitionItemCreate, db: Session = Depends(get_db)):
    exhibition = db.query(Exhibition).filter(Exhibition.id == exhibition_id).first()
    if not exhibition:
        raise HTTPException(status_code=404, detail="展览不存在")
    letter = db.query(Letter).filter(Letter.id == data.letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    if letter.family_space_id != exhibition.family_space_id:
        raise HTTPException(status_code=400, detail="信件不属于当前家庭馆，不可跨馆添加展品")
    item = ExhibitionItem(
        exhibition_id=exhibition_id,
        letter_id=data.letter_id,
        sort_order=data.sort_order,
        caption=data.caption,
        section_title=data.section_title,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{exhibition_id}/items", response_model=List[ExhibitionItemOut], summary="获取展览展品列表")
def list_exhibition_items(exhibition_id: int, db: Session = Depends(get_db)):
    return db.query(ExhibitionItem).filter(
        ExhibitionItem.exhibition_id == exhibition_id
    ).order_by(ExhibitionItem.sort_order).all()


@router.put("/{exhibition_id}/items/{item_id}", response_model=ExhibitionItemOut, summary="更新展品信息")
def update_exhibition_item(
    exhibition_id: int,
    item_id: int,
    data: ExhibitionItemUpdate,
    db: Session = Depends(get_db),
):
    item = db.query(ExhibitionItem).filter(
        ExhibitionItem.id == item_id,
        ExhibitionItem.exhibition_id == exhibition_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="展品不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{exhibition_id}/items/{item_id}", summary="移除展品")
def remove_exhibition_item(exhibition_id: int, item_id: int, db: Session = Depends(get_db)):
    item = db.query(ExhibitionItem).filter(
        ExhibitionItem.id == item_id,
        ExhibitionItem.exhibition_id == exhibition_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="展品不存在")
    db.delete(item)
    db.commit()
    return {"detail": "已移除"}


@router.post("/{exhibition_id}/items/reorder", summary="批量调整展品顺序")
def reorder_items(exhibition_id: int, item_orders: dict, db: Session = Depends(get_db)):
    items = db.query(ExhibitionItem).filter(ExhibitionItem.exhibition_id == exhibition_id).all()
    id_to_item = {item.id: item for item in items}
    for item_id, new_order in item_orders.items():
        item_id_int = int(item_id)
        if item_id_int in id_to_item:
            id_to_item[item_id_int].sort_order = new_order
    db.commit()
    return {"detail": "排序已更新"}


@router.post("/comments", response_model=CommentOut, summary="添加浏览留言")
def create_comment(data: CommentCreate, db: Session = Depends(get_db)):
    letter = db.query(Letter).filter(Letter.id == data.letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    comment = Comment(
        letter_id=data.letter_id,
        user_id=None,
        visitor_name=data.visitor_name,
        content=data.content,
        source=data.source,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/comments/{letter_id}", response_model=List[CommentOut], summary="获取信件留言列表")
def list_comments(letter_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Comment).filter(
        Comment.letter_id == letter_id
    ).order_by(Comment.created_at.desc()).offset(skip).limit(limit).all()


@router.delete("/comments/{comment_id}", summary="删除留言")
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="留言不存在")
    db.delete(comment)
    db.commit()
    return {"detail": "已删除"}
