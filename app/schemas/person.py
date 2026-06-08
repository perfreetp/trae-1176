from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PersonCreate(BaseModel):
    family_space_id: int
    name: str
    alias: Optional[str] = ""
    gender: Optional[str] = ""
    birth_year: Optional[str] = ""
    death_year: Optional[str] = ""
    bio: Optional[str] = ""
    avatar: Optional[str] = ""


class PersonUpdate(BaseModel):
    name: Optional[str] = None
    alias: Optional[str] = None
    gender: Optional[str] = None
    birth_year: Optional[str] = None
    death_year: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None


class PersonOut(BaseModel):
    id: int
    family_space_id: int
    name: str
    alias: Optional[str] = ""
    gender: Optional[str] = ""
    birth_year: Optional[str] = ""
    death_year: Optional[str] = ""
    bio: Optional[str] = ""
    avatar: Optional[str] = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonRelationCreate(BaseModel):
    from_person_id: int
    to_person_id: int
    relation_type: str
    description: Optional[str] = ""


class PersonRelationOut(BaseModel):
    id: int
    from_person_id: int
    to_person_id: int
    relation_type: str
    description: Optional[str] = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class PersonWithRelations(PersonOut):
    relations_from: Optional[List[PersonRelationOut]] = []
    relations_to: Optional[List[PersonRelationOut]] = []

    model_config = {"from_attributes": True}


class FamilyGraphEdge(BaseModel):
    source: str
    target: str
    relation: Optional[str] = ""
    description: Optional[str] = ""


class FamilyGraphOut(BaseModel):
    nodes: List[dict]
    edges: List[dict]
