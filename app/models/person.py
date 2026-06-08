from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Person(Base):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    family_space_id = Column(Integer, ForeignKey("family_spaces.id"), nullable=False)
    name = Column(String(100), nullable=False)
    alias = Column(String(100), default="")
    gender = Column(String(10), default="")
    birth_year = Column(String(20), default="")
    death_year = Column(String(20), default="")
    bio = Column(Text, default="")
    avatar = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    family_space = relationship("FamilySpace", back_populates="persons")
    sent_letters = relationship("Letter", foreign_keys="Letter.sender_id", back_populates="sender_person")
    received_letters = relationship("Letter", foreign_keys="Letter.receiver_id", back_populates="receiver_person")
    relations_from = relationship("PersonRelation", foreign_keys="PersonRelation.from_person_id", back_populates="from_person", cascade="all, delete-orphan")
    relations_to = relationship("PersonRelation", foreign_keys="PersonRelation.to_person_id", back_populates="to_person", cascade="all, delete-orphan")


class PersonRelation(Base):
    __tablename__ = "person_relations"

    id = Column(Integer, primary_key=True, index=True)
    from_person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    to_person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    relation_type = Column(String(50), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    from_person = relationship("Person", foreign_keys=[from_person_id], back_populates="relations_from")
    to_person = relationship("Person", foreign_keys=[to_person_id], back_populates="relations_to")
