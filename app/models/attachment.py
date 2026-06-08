from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    letter_id = Column(Integer, ForeignKey("letters.id"), nullable=False)
    file_name = Column(String(300), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, default=0)
    media_type = Column(String(20), default="image")
    description = Column(Text, default="")
    duration = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    letter = relationship("Letter", back_populates="attachments")


class LetterAuthorization(Base):
    __tablename__ = "letter_authorizations"

    id = Column(Integer, primary_key=True, index=True)
    letter_id = Column(Integer, ForeignKey("letters.id"), nullable=False)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    authorizer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="pending")
    reason = Column(Text, default="")
    response = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)

    letter = relationship("Letter", back_populates="authorizations")
    applicant = relationship("User", foreign_keys=[applicant_id])
    authorizer = relationship("User", foreign_keys=[authorizer_id])


class ShareLink(Base):
    __tablename__ = "share_links"

    id = Column(Integer, primary_key=True, index=True)
    letter_id = Column(Integer, ForeignKey("letters.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(100), unique=True, nullable=False)
    access_level = Column(String(20), default="view")
    max_views = Column(Integer, default=0)
    current_views = Column(Integer, default=0)
    is_active = Column(String(10), default="yes")
    password = Column(String(200), default="")
    preview_fields = Column(String(500), default="title,send_date,era")
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class ShareAccessLog(Base):
    __tablename__ = "share_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    share_link_id = Column(Integer, ForeignKey("share_links.id"), nullable=False)
    visitor_ip = Column(String(50), default="")
    visitor_user_id = Column(Integer, nullable=True)
    access_method = Column(String(20), default="token")
    access_sequence = Column(Integer, default=0)
    password_attempt = Column(String(10), default="")
    success = Column(String(10), default="yes")
    fail_reason = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
