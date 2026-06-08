from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional
from collections import defaultdict

from app.database import get_db
from app.models.letter import Letter, LetterPage
from app.models.person import Person, PersonRelation
from app.models.attachment import Attachment
from app.models.exhibition import Exhibition, Comment
from app.models.family import FamilySpace
from app.schemas.search import SearchQuery, SearchResults, StatOverview, CommunicationRecord, CommunicationGraphOut

router = APIRouter(prefix="/api/search", tags=["检索统计"])


@router.post("/letters", response_model=SearchResults, summary="检索信件（关键词+时间）")
def search_letters(data: SearchQuery, db: Session = Depends(get_db)):
    query = db.query(Letter)

    if data.family_space_id:
        query = query.filter(Letter.family_space_id == data.family_space_id)
    if data.keyword:
        keyword_filter = f"%{data.keyword}%"
        query = query.filter(
            or_(
                Letter.title.ilike(keyword_filter),
                Letter.description.ilike(keyword_filter),
                Letter.tags.ilike(keyword_filter),
                Letter.send_location.ilike(keyword_filter),
                Letter.receive_location.ilike(keyword_filter),
            )
        )
    if data.sender_id:
        query = query.filter(Letter.sender_id == data.sender_id)
    if data.receiver_id:
        query = query.filter(Letter.receiver_id == data.receiver_id)
    if data.era:
        query = query.filter(Letter.era == data.era)
    if data.date_from:
        query = query.filter(Letter.send_date >= data.date_from)
    if data.date_to:
        query = query.filter(Letter.send_date <= data.date_to)
    if data.category:
        query = query.filter(Letter.category == data.category)
    if data.tags:
        tags_filter = f"%{data.tags}%"
        query = query.filter(Letter.tags.ilike(tags_filter))
    if data.visibility:
        query = query.filter(Letter.visibility == data.visibility)
    if data.is_starred is not None:
        query = query.filter(Letter.is_starred == data.is_starred)

    total = query.count()
    page = max(1, data.page)
    page_size = min(100, max(1, data.page_size))
    items = query.order_by(Letter.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return SearchResults(total=total, page=page, page_size=page_size, items=[
        {
            "id": l.id,
            "title": l.title,
            "sender_id": l.sender_id,
            "receiver_id": l.receiver_id,
            "send_date": l.send_date,
            "era": l.era,
            "category": l.category,
            "visibility": l.visibility,
            "is_starred": l.is_starred,
            "created_at": l.created_at.isoformat() if l.created_at else "",
        }
        for l in items
    ])


@router.post("/transcriptions", response_model=SearchResults, summary="检索释文内容")
def search_transcriptions(data: SearchQuery, db: Session = Depends(get_db)):
    if not data.keyword:
        return SearchResults(total=0, page=1, page_size=data.page_size, items=[])
    keyword_filter = f"%{data.keyword}%"
    pages_query = db.query(LetterPage).filter(
        or_(
            LetterPage.transcription.ilike(keyword_filter),
            LetterPage.notes.ilike(keyword_filter),
        )
    )
    total = pages_query.count()
    page = max(1, data.page)
    page_size = min(100, max(1, data.page_size))
    pages = pages_query.offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for p in pages:
        letter = db.query(Letter).filter(Letter.id == p.letter_id).first()
        items.append({
            "page_id": p.id,
            "letter_id": p.letter_id,
            "letter_title": letter.title if letter else "",
            "page_number": p.page_number,
            "transcription": p.transcription[:200] if p.transcription else "",
            "notes": p.notes[:200] if p.notes else "",
        })
    return SearchResults(total=total, page=page, page_size=page_size, items=items)


@router.get("/stats/{family_space_id}", response_model=StatOverview, summary="获取统计数据")
def get_statistics(family_space_id: int, db: Session = Depends(get_db)):
    total_letters = db.query(Letter).filter(Letter.family_space_id == family_space_id).count()
    total_persons = db.query(Person).filter(Person.family_space_id == family_space_id).count()
    total_attachments = db.query(Attachment).join(Letter).filter(Letter.family_space_id == family_space_id).count()
    total_exhibitions = db.query(Exhibition).filter(Exhibition.family_space_id == family_space_id).count()
    total_comments = db.query(Comment).join(Letter).filter(Letter.family_space_id == family_space_id).count()

    letters_by_era = defaultdict(int)
    letters_by_category = defaultdict(int)
    letters_by_month = defaultdict(int)

    letters = db.query(Letter).filter(Letter.family_space_id == family_space_id).all()
    for l in letters:
        if l.era:
            letters_by_era[l.era] += 1
        if l.category:
            letters_by_category[l.category] += 1
        if l.send_date:
            month_key = l.send_date[:7] if len(l.send_date) >= 7 else l.send_date
            letters_by_month[month_key] += 1
        elif l.created_at:
            month_key = l.created_at.strftime("%Y-%m")
            letters_by_month[month_key] += 1

    return StatOverview(
        total_letters=total_letters,
        total_persons=total_persons,
        total_attachments=total_attachments,
        total_exhibitions=total_exhibitions,
        total_comments=total_comments,
        letters_by_era=dict(letters_by_era),
        letters_by_category=dict(letters_by_category),
        letters_by_month=dict(sorted(letters_by_month.items())),
    )


@router.get("/communication/{family_space_id}", response_model=CommunicationGraphOut, summary="生成家族通信图谱数据")
def get_communication_graph(family_space_id: int, db: Session = Depends(get_db)):
    persons = db.query(Person).filter(Person.family_space_id == family_space_id).all()
    nodes = [{"id": p.id, "name": p.name, "alias": p.alias, "gender": p.gender} for p in persons]

    letters = db.query(Letter).filter(
        Letter.family_space_id == family_space_id,
        Letter.sender_id.isnot(None),
        Letter.receiver_id.isnot(None),
    ).all()

    pair_stats = defaultdict(lambda: {"count": 0, "earliest": "", "latest": ""})
    for l in letters:
        key = (l.sender_id, l.receiver_id)
        pair_stats[key]["count"] += 1
        if l.send_date:
            if not pair_stats[key]["earliest"] or l.send_date < pair_stats[key]["earliest"]:
                pair_stats[key]["earliest"] = l.send_date
            if not pair_stats[key]["latest"] or l.send_date > pair_stats[key]["latest"]:
                pair_stats[key]["latest"] = l.send_date

    person_map = {p.id: p.name for p in persons}
    edges = []
    for (sender_id, receiver_id), stats in pair_stats.items():
        edges.append({
            "source": person_map.get(sender_id, f"人物{sender_id}"),
            "target": person_map.get(receiver_id, f"人物{receiver_id}"),
            "letter_count": stats["count"],
            "earliest_date": stats["earliest"],
            "latest_date": stats["latest"],
            "type": "correspondence",
        })

    relations = db.query(PersonRelation).filter(
        PersonRelation.from_person_id.in_([p.id for p in persons]),
        PersonRelation.to_person_id.in_([p.id for p in persons]),
    ).all()
    for rel in relations:
        edges.append({
            "source": person_map.get(rel.from_person_id, ""),
            "target": person_map.get(rel.to_person_id, ""),
            "relation": rel.relation_type,
            "description": rel.description,
            "type": "kinship",
        })

    return CommunicationGraphOut(nodes=nodes, edges=edges)
