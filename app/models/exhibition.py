from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Exhibition(Base):
    __tablename__ = "exhibitions"

    id = Column(Integer, primary_key=True, index=True)
    family_space_id = Column(Integer, ForeignKey("family_spaces.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, default="")
    cover_image = Column(String(500), default="")
    curator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_published = Column(String(10), default="no")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    family_space = relationship("FamilySpace", back_populates="exhibitions")
    items = relationship("ExhibitionItem", back_populates="exhibition", cascade="all, delete-orphan", order_by="ExhibitionItem.sort_order")


class ExhibitionItem(Base):
    __tablename__ = "exhibition_items"

    id = Column(Integer, primary_key=True, index=True)
    exhibition_id = Column(Integer, ForeignKey("exhibitions.id"), nullable=False)
    letter_id = Column(Integer, ForeignKey("letters.id"), nullable=False)
    sort_order = Column(Integer, default=0)
    caption = Column(Text, default="")
    section_title = Column(String(200), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    exhibition = relationship("Exhibition", back_populates="items")
    letter = relationship("Letter", back_populates="exhibition_items")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    letter_id = Column(Integer, ForeignKey("letters.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    visitor_name = Column(String(100), default="")
    content = Column(Text, nullable=False)
    source = Column(String(50), default="web")
    created_at = Column(DateTime, default=datetime.utcnow)

    letter = relationship("Letter", back_populates="comments")
