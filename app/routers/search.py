import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from collections import defaultdict

from app.database import get_db
from app.models.letter import Letter, LetterPage
from app.models.person import Person, PersonRelation
from app.models.attachment import Attachment
from app.models.exhibition import Exhibition, Comment
from app.models.family import FamilySpace
from app.schemas.search import SearchQuery, SearchResults, StatOverview, CommunicationGraphOut

router = APIRouter(prefix="/api/search", tags=["检索统计"])

SNIPPET_RADIUS = 30


def _make_snippet(text: str, keyword: str) -> str:
    if not text or not keyword:
        return ""
    idx = text.lower().find(keyword.lower())
    if idx < 0:
        return ""
    start = max(0, idx - SNIPPET_RADIUS)
    end = min(len(text), idx + len(keyword) + SNIPPET_RADIUS)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    snippet_text = text[start:end]
    highlight_pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    snippet_text = highlight_pattern.sub(lambda m: f"**{m.group(0)}**", snippet_text)
    return prefix + snippet_text + suffix


def _collect_hits(letter: Letter, keyword: str, db: Session) -> list:
    hits = []
    if not keyword:
        return hits
    field_checks = [
        ("title", letter.title),
        ("description", letter.description),
        ("tags", letter.tags),
        ("send_location", letter.send_location),
        ("receive_location", letter.receive_location),
    ]
    for field_name, field_val in field_checks:
        if field_val and keyword.lower() in field_val.lower():
            hits.append({
                "field": field_name,
                "snippet": _make_snippet(field_val, keyword),
            })
    pages = db.query(LetterPage).filter(LetterPage.letter_id == letter.id).all()
    for p in pages:
        for src_field, src_val in [("transcription", p.transcription), ("notes", p.notes)]:
            if src_val and keyword.lower() in src_val.lower():
                hits.append({
                    "field": f"page_{p.page_number}_{src_field}",
                    "snippet": _make_snippet(src_val, keyword),
                })
    return hits


def _build_aggregations(letters: list, db: Session) -> dict:
    by_era = defaultdict(int)
    by_person = defaultdict(int)
    by_tag = defaultdict(int)
    by_category = defaultdict(int)
    for l in letters:
        if l.era:
            by_era[l.era] += 1
        if l.category:
            by_category[l.category] += 1
        if l.sender_id:
            sender = db.query(Person).filter(Person.id == l.sender_id).first()
            if sender:
                by_person[sender.name] += 1
        if l.receiver_id:
            receiver = db.query(Person).filter(Person.id == l.receiver_id).first()
            if receiver:
                by_person[receiver.name] += 1
        if l.tags:
            for tag in l.tags.split(","):
                tag = tag.strip()
                if tag:
                    by_tag[tag] += 1
    return {
        "by_era": dict(sorted(by_era.items(), key=lambda x: -x[1])),
        "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
        "by_person": dict(sorted(by_person.items(), key=lambda x: -x[1])),
        "by_tag": dict(sorted(by_tag.items(), key=lambda x: -x[1])),
    }


@router.post("/letters", response_model=SearchResults, summary="检索信件（关键词+时间）")
def search_letters(data: SearchQuery, db: Session = Depends(get_db)):
    base_query = db.query(Letter)

    if data.family_space_id:
        base_query = base_query.filter(Letter.family_space_id == data.family_space_id)

    if data.keyword:
        keyword_filter = f"%{data.keyword}%"
        letter_ids_with_transcription = db.query(LetterPage.letter_id).filter(
            or_(
                LetterPage.transcription.ilike(keyword_filter),
                LetterPage.notes.ilike(keyword_filter),
            )
        ).subquery()
        base_query = base_query.filter(
            or_(
                Letter.title.ilike(keyword_filter),
                Letter.description.ilike(keyword_filter),
                Letter.tags.ilike(keyword_filter),
                Letter.send_location.ilike(keyword_filter),
                Letter.receive_location.ilike(keyword_filter),
                Letter.id.in_(letter_ids_with_transcription),
            )
        )

    if data.sender_id:
        base_query = base_query.filter(Letter.sender_id == data.sender_id)
    if data.receiver_id:
        base_query = base_query.filter(Letter.receiver_id == data.receiver_id)
    if data.era:
        base_query = base_query.filter(Letter.era == data.era)
    if data.date_from:
        base_query = base_query.filter(Letter.send_date >= data.date_from)
    if data.date_to:
        base_query = base_query.filter(Letter.send_date <= data.date_to)
    if data.category:
        base_query = base_query.filter(Letter.category == data.category)
    if data.tags:
        tags_filter = f"%{data.tags}%"
        base_query = base_query.filter(Letter.tags.ilike(tags_filter))
    if data.visibility:
        base_query = base_query.filter(Letter.visibility == data.visibility)
    if data.is_starred is not None:
        base_query = base_query.filter(Letter.is_starred == data.is_starred)
    if data.status:
        base_query = base_query.filter(Letter.status == data.status)
    elif not data.include_draft:
        base_query = base_query.filter(Letter.status == "published")

    total = base_query.count()
    page = max(1, data.page)
    page_size = min(100, max(1, data.page_size))
    items = base_query.order_by(Letter.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result_items = []
    for l in items:
        hits = _collect_hits(l, data.keyword, db) if data.keyword else []
        result_items.append({
            "id": l.id,
            "title": l.title,
            "sender_id": l.sender_id,
            "receiver_id": l.receiver_id,
            "send_date": l.send_date,
            "era": l.era,
            "category": l.category,
            "visibility": l.visibility,
            "is_starred": l.is_starred,
            "status": l.status,
            "created_at": l.created_at.isoformat() if l.created_at else "",
            "hits": hits,
        })

    all_matched = base_query.all()
    aggregations = _build_aggregations(all_matched, db) if data.family_space_id else None

    return SearchResults(total=total, page=page, page_size=page_size, items=result_items, aggregations=aggregations)


@router.post("/transcriptions", response_model=SearchResults, summary="检索释文内容")
def search_transcriptions(data: SearchQuery, db: Session = Depends(get_db)):
    if not data.keyword:
        return SearchResults(total=0, page=1, page_size=data.page_size, items=[])
    keyword_filter = f"%{data.keyword}%"

    pages_query = db.query(LetterPage).join(
        Letter, LetterPage.letter_id == Letter.id
    ).filter(
        or_(
            LetterPage.transcription.ilike(keyword_filter),
            LetterPage.notes.ilike(keyword_filter),
        )
    )

    if data.family_space_id:
        pages_query = pages_query.filter(Letter.family_space_id == data.family_space_id)

    total = pages_query.count()
    page = max(1, data.page)
    page_size = min(100, max(1, data.page_size))
    pages = pages_query.offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for p in pages:
        letter = db.query(Letter).filter(Letter.id == p.letter_id).first()
        hits = []
        if p.transcription and data.keyword.lower() in p.transcription.lower():
            hits.append({"field": f"page_{p.page_number}_transcription", "snippet": _make_snippet(p.transcription, data.keyword)})
        if p.notes and data.keyword.lower() in p.notes.lower():
            hits.append({"field": f"page_{p.page_number}_notes", "snippet": _make_snippet(p.notes, data.keyword)})
        items.append({
            "page_id": p.id,
            "letter_id": p.letter_id,
            "letter_title": letter.title if letter else "",
            "page_number": p.page_number,
            "transcription": p.transcription[:200] if p.transcription else "",
            "notes": p.notes[:200] if p.notes else "",
            "hits": hits,
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
