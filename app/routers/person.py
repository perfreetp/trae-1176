from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.person import Person, PersonRelation
from app.models.letter import Letter
from app.schemas.person import (
    PersonCreate, PersonUpdate, PersonOut,
    PersonRelationCreate, PersonRelationOut,
    PersonWithRelations, FamilyGraphEdge, FamilyGraphOut
)

router = APIRouter(prefix="/api/persons", tags=["人物关系"])


@router.post("", response_model=PersonOut, summary="创建人物")
def create_person(data: PersonCreate, db: Session = Depends(get_db)):
    person = Person(
        family_space_id=data.family_space_id,
        name=data.name,
        alias=data.alias,
        gender=data.gender,
        birth_year=data.birth_year,
        death_year=data.death_year,
        bio=data.bio,
        avatar=data.avatar,
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.get("", response_model=List[PersonOut], summary="获取人物列表")
def list_persons(
    family_space_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Person)
    if family_space_id:
        query = query.filter(Person.family_space_id == family_space_id)
    return query.offset(skip).limit(limit).all()


@router.get("/{person_id}", response_model=PersonWithRelations, summary="获取人物详情（含关系）")
def get_person(person_id: int, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="人物不存在")
    return person


@router.put("/{person_id}", response_model=PersonOut, summary="更新人物信息")
def update_person(person_id: int, data: PersonUpdate, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="人物不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(person, key, value)
    from datetime import datetime
    person.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(person)
    return person


@router.delete("/{person_id}", summary="删除人物")
def delete_person(person_id: int, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="人物不存在")
    db.delete(person)
    db.commit()
    return {"detail": "已删除"}


@router.post("/relations", response_model=PersonRelationOut, summary="创建人物关系")
def create_relation(data: PersonRelationCreate, db: Session = Depends(get_db)):
    if data.from_person_id == data.to_person_id:
        raise HTTPException(status_code=400, detail="不能创建自引用关系")
    from_person = db.query(Person).filter(Person.id == data.from_person_id).first()
    to_person = db.query(Person).filter(Person.id == data.to_person_id).first()
    if not from_person or not to_person:
        raise HTTPException(status_code=404, detail="人物不存在")
    relation = PersonRelation(
        from_person_id=data.from_person_id,
        to_person_id=data.to_person_id,
        relation_type=data.relation_type,
        description=data.description,
    )
    db.add(relation)
    db.commit()
    db.refresh(relation)
    return relation


@router.get("/{person_id}/relations", response_model=List[PersonRelationOut], summary="获取人物关系列表")
def list_relations(person_id: int, db: Session = Depends(get_db)):
    return db.query(PersonRelation).filter(
        (PersonRelation.from_person_id == person_id) | (PersonRelation.to_person_id == person_id)
    ).all()


@router.delete("/relations/{relation_id}", summary="删除人物关系")
def delete_relation(relation_id: int, db: Session = Depends(get_db)):
    relation = db.query(PersonRelation).filter(PersonRelation.id == relation_id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="关系不存在")
    db.delete(relation)
    db.commit()
    return {"detail": "已删除"}


@router.get("/graph/{family_space_id}", response_model=FamilyGraphOut, summary="生成家族通信图谱")
def get_family_graph(family_space_id: int, db: Session = Depends(get_db)):
    persons = db.query(Person).filter(Person.family_space_id == family_space_id).all()
    if not persons:
        return FamilyGraphOut(nodes=[], edges=[])

    nodes = []
    for p in persons:
        letter_count = db.query(Letter).filter(
            (Letter.sender_id == p.id) | (Letter.receiver_id == p.id),
            Letter.family_space_id == family_space_id,
        ).count()
        nodes.append({
            "id": p.id,
            "name": p.name,
            "alias": p.alias,
            "gender": p.gender,
            "birth_year": p.birth_year,
            "death_year": p.death_year,
            "letter_count": letter_count,
        })

    edges = []
    seen_pairs = set()
    for p in persons:
        sent_letters = db.query(Letter).filter(
            Letter.sender_id == p.id,
            Letter.family_space_id == family_space_id,
        ).all()
        for letter in sent_letters:
            if letter.receiver_id:
                pair = (min(p.id, letter.receiver_id), max(p.id, letter.receiver_id))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    count = db.query(Letter).filter(
                        Letter.sender_id == p.id,
                        Letter.receiver_id == letter.receiver_id,
                        Letter.family_space_id == family_space_id,
                    ).count() + db.query(Letter).filter(
                        Letter.sender_id == letter.receiver_id,
                        Letter.receiver_id == p.id,
                        Letter.family_space_id == family_space_id,
                    ).count()
                    receiver = next((n for n in nodes if n["id"] == letter.receiver_id), None)
                    if receiver:
                        edges.append({
                            "source": p.name,
                            "target": receiver["name"],
                            "letter_count": count,
                            "type": "correspondence",
                        })

    relations = db.query(PersonRelation).filter(
        PersonRelation.from_person_id.in_([p.id for p in persons]),
        PersonRelation.to_person_id.in_([p.id for p in persons]),
    ).all()
    for rel in relations:
        from_p = next((n for n in nodes if n["id"] == rel.from_person_id), None)
        to_p = next((n for n in nodes if n["id"] == rel.to_person_id), None)
        if from_p and to_p:
            edges.append({
                "source": from_p["name"],
                "target": to_p["name"],
                "relation": rel.relation_type,
                "description": rel.description,
                "type": "kinship",
            })

    return FamilyGraphOut(nodes=nodes, edges=edges)
