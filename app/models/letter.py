from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Letter(Base):
    __tablename__ = "letters"

    id = Column(Integer, primary_key=True, index=True)
    family_space_id = Column(Integer, ForeignKey("family_spaces.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, default="")
    sender_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    receiver_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    send_location = Column(String(200), default="")
    receive_location = Column(String(200), default="")
    send_date = Column(String(50), default="")
    receive_date = Column(String(50), default="")
    era = Column(String(50), default="")
    category = Column(String(50), default="")
    tags = Column(String(500), default="")
    visibility = Column(String(20), default="family")
    is_starred = Column(Boolean, default=False)
    status = Column(String(20), default="draft")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    family_space = relationship("FamilySpace", back_populates="letters")
    sender_person = relationship("Person", foreign_keys=[sender_id], back_populates="sent_letters")
    receiver_person = relationship("Person", foreign_keys=[receiver_id], back_populates="received_letters")
    pages = relationship("LetterPage", back_populates="letter", cascade="all, delete-orphan", order_by="LetterPage.page_number")
    attachments = relationship("Attachment", back_populates="letter", cascade="all, delete-orphan")
    authorizations = relationship("LetterAuthorization", back_populates="letter", cascade="all, delete-orphan")
    exhibition_items = relationship("ExhibitionItem", back_populates="letter")
    comments = relationship("Comment", back_populates="letter", cascade="all, delete-orphan")


class LetterPage(Base):
    __tablename__ = "letter_pages"

    id = Column(Integer, primary_key=True, index=True)
    letter_id = Column(Integer, ForeignKey("letters.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_path = Column(String(500), default="")
    transcription = Column(Text, default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    letter = relationship("Letter", back_populates="pages")
