import os
import json
import uuid
import zipfile
import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.letter import Letter, LetterPage
from app.models.person import Person, PersonRelation
from app.models.attachment import Attachment, ShareLink, ShareAccessLog
from app.models.family import FamilySpace
from app.schemas.export import (
    ExportRequest, ExportTaskOut, PreservationManifest, PreservationItem,
    HandoverSummary, HandoverLetterSummary,
)

router = APIRouter(prefix="/api/export", tags=["导出交接"])

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


def _file_checksum(file_path: str) -> str:
    h = hashlib.sha256()
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    return h.hexdigest()


def _build_handover(space_id: int, letters: list, db: Session) -> dict:
    space = db.query(FamilySpace).filter(FamilySpace.id == space_id).first()
    total_pages = 0
    total_attachments = 0
    active_shares = 0
    total_access = 0
    letter_summaries = []

    for letter in letters:
        pages = db.query(LetterPage).filter(LetterPage.letter_id == letter.id).all()
        total_pages += len(pages)

        attachments = db.query(Attachment).filter(Attachment.letter_id == letter.id).all()
        total_attachments += len(attachments)

        share_links = db.query(ShareLink).filter(ShareLink.letter_id == letter.id).all()
        active_count = sum(1 for s in share_links if s.is_active == "yes")
        active_shares += active_count

        access_count = 0
        for sl in share_links:
            access_count += db.query(ShareAccessLog).filter(ShareAccessLog.share_link_id == sl.id).count()
        total_access += access_count

        content_parts = [letter.title or "", letter.description or ""]
        for p in pages:
            content_parts.append(p.transcription or "")
        content_hash = hashlib.sha256("".join(content_parts).encode("utf-8")).hexdigest()[:16]

        letter_summaries.append(HandoverLetterSummary(
            id=letter.id,
            title=letter.title,
            page_count=len(pages),
            attachment_count=len(attachments),
            visibility=letter.visibility,
            share_link_count=len(share_links),
            checksum=content_hash,
        ).model_dump())

    return HandoverSummary(
        family_space_id=space_id,
        family_name=space.name if space else "",
        export_date=datetime.utcnow().isoformat(),
        total_letters=len(letters),
        total_pages=total_pages,
        total_attachments=total_attachments,
        active_share_links=active_shares,
        total_share_access=total_access,
        letters=letter_summaries,
    ).model_dump()


@router.post("/memorial-book", response_model=ExportTaskOut, summary="生成纪念册素材包")
def export_memorial_book(data: ExportRequest, db: Session = Depends(get_db)):
    space = db.query(FamilySpace).filter(FamilySpace.id == data.family_space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="家庭馆不存在")

    query = db.query(Letter).filter(Letter.family_space_id == data.family_space_id)
    if data.letter_ids:
        query = query.filter(Letter.id.in_(data.letter_ids))
    if data.date_from:
        query = query.filter(Letter.send_date >= data.date_from)
    if data.date_to:
        query = query.filter(Letter.send_date <= data.date_to)
    letters = query.all()

    if data.letter_ids:
        requested_ids = set(data.letter_ids)
        found_ids = {l.id for l in letters}
        mismatch = requested_ids - found_ids
        if mismatch:
            raise HTTPException(
                status_code=400,
                detail=f"信件 {','.join(str(i) for i in mismatch)} 不属于当前家庭馆或不存在",
            )

    task_id = uuid.uuid4().hex[:12]
    zip_filename = f"memorial_{space.name}_{task_id}.zip"
    zip_path = os.path.join(EXPORT_DIR, zip_filename)

    persons = db.query(Person).filter(Person.family_space_id == data.family_space_id).all()
    person_map = {p.id: p for p in persons}

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        metadata = {
            "family_name": space.name,
            "export_date": datetime.utcnow().isoformat(),
            "total_letters": len(letters),
            "total_persons": len(persons),
            "letters": [],
        }

        for letter in letters:
            letter_data = {
                "id": letter.id,
                "title": letter.title,
                "description": letter.description,
                "sender": person_map[letter.sender_id].name if letter.sender_id and letter.sender_id in person_map else "",
                "receiver": person_map[letter.receiver_id].name if letter.receiver_id and letter.receiver_id in person_map else "",
                "send_location": letter.send_location,
                "receive_location": letter.receive_location,
                "send_date": letter.send_date,
                "receive_date": letter.receive_date,
                "era": letter.era,
                "category": letter.category,
                "tags": letter.tags,
            }

            if data.include_transcriptions:
                pages = db.query(LetterPage).filter(LetterPage.letter_id == letter.id).order_by(LetterPage.page_number).all()
                letter_data["pages"] = [
                    {
                        "page_number": p.page_number,
                        "transcription": p.transcription,
                        "notes": p.notes,
                    }
                    for p in pages
                ]

            if data.include_attachments:
                attachments = db.query(Attachment).filter(Attachment.letter_id == letter.id).all()
                letter_data["attachments"] = [
                    {
                        "file_name": a.file_name,
                        "file_type": a.file_type,
                        "media_type": a.media_type,
                        "file_size": a.file_size,
                    }
                    for a in attachments
                ]
                for att in attachments:
                    att_full_path = os.path.join(UPLOAD_DIR, att.file_path)
                    if os.path.exists(att_full_path):
                        arcname = f"attachments/{letter.id}_{att.file_name}"
                        zf.write(att_full_path, arcname)

            metadata["letters"].append(letter_data)

        if data.include_metadata:
            persons_data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "alias": p.alias,
                    "gender": p.gender,
                    "birth_year": p.birth_year,
                    "death_year": p.death_year,
                    "bio": p.bio,
                }
                for p in persons
            ]
            relations = db.query(PersonRelation).filter(
                PersonRelation.from_person_id.in_([p.id for p in persons]),
                PersonRelation.to_person_id.in_([p.id for p in persons]),
            ).all()
            relations_data = [
                {
                    "from": person_map[r.from_person_id].name if r.from_person_id in person_map else "",
                    "to": person_map[r.to_person_id].name if r.to_person_id in person_map else "",
                    "relation_type": r.relation_type,
                    "description": r.description,
                }
                for r in relations
            ]
            metadata["persons"] = persons_data
            metadata["relations"] = relations_data

        zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))

        if data.include_handover:
            handover = _build_handover(data.family_space_id, letters, db)
            zf.writestr("handover.json", json.dumps(handover, ensure_ascii=False, indent=2))

    file_size = os.path.getsize(zip_path)
    return ExportTaskOut(
        task_id=task_id,
        status="completed",
        download_url=f"/api/export/download/{zip_filename}",
        created_at=datetime.utcnow().isoformat(),
        file_size=file_size,
    )


@router.get("/handover/{family_space_id}", response_model=HandoverSummary, summary="生成交接清单")
def get_handover_summary(family_space_id: int, db: Session = Depends(get_db)):
    space = db.query(FamilySpace).filter(FamilySpace.id == family_space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="家庭馆不存在")
    letters = db.query(Letter).filter(Letter.family_space_id == family_space_id).all()
    return _build_handover(family_space_id, letters, db)


@router.get("/download/{filename}", summary="下载导出文件")
def download_export(filename: str):
    file_path = os.path.join(EXPORT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/zip",
    )


@router.get("/preservation/{family_space_id}", response_model=PreservationManifest, summary="生成长期保存清单")
def get_preservation_manifest(family_space_id: int, db: Session = Depends(get_db)):
    space = db.query(FamilySpace).filter(FamilySpace.id == family_space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="家庭馆不存在")

    letters = db.query(Letter).filter(Letter.family_space_id == family_space_id).all()
    items = []

    for letter in letters:
        pages = db.query(LetterPage).filter(LetterPage.letter_id == letter.id).all()
        for page in pages:
            if page.image_path:
                full_path = os.path.join(UPLOAD_DIR, page.image_path)
                size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
                items.append(PreservationItem(
                    id=page.id,
                    title=f"{letter.title}-第{page.page_number}页",
                    format="image",
                    size=size,
                    checksum=_file_checksum(full_path),
                    status="ok" if os.path.exists(full_path) else "missing",
                ))

        attachments = db.query(Attachment).filter(Attachment.letter_id == letter.id).all()
        for att in attachments:
            full_path = os.path.join(UPLOAD_DIR, att.file_path)
            size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
            items.append(PreservationItem(
                id=att.id,
                title=f"{letter.title}-{att.file_name}",
                format=att.media_type,
                size=size,
                checksum=_file_checksum(full_path),
                status="ok" if os.path.exists(full_path) else "missing",
            ))

    return PreservationManifest(
        family_space_id=family_space_id,
        family_name=space.name,
        export_date=datetime.utcnow().isoformat(),
        total_items=len(items),
        items=items,
    )
