from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class FamilySpace(Base):
    __tablename__ = "family_spaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    cover_image = Column(String(500), default="")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_spaces")
    members = relationship("FamilyMember", back_populates="family_space", cascade="all, delete-orphan")
    letters = relationship("Letter", back_populates="family_space", cascade="all, delete-orphan")
    persons = relationship("Person", back_populates="family_space", cascade="all, delete-orphan")
    exhibitions = relationship("Exhibition", back_populates="family_space", cascade="all, delete-orphan")
    invitations = relationship("FamilyInvitation", back_populates="family_space", cascade="all, delete-orphan")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    family_space_id = Column(Integer, ForeignKey("family_spaces.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(50), default="visitor")
    nickname = Column(String(100), default="")
    join_source = Column(String(50), default="direct")
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)

    family_space = relationship("FamilySpace", back_populates="members")
    user = relationship("User", back_populates="family_memberships")


class FamilyInvitation(Base):
    __tablename__ = "family_invitations"

    id = Column(Integer, primary_key=True, index=True)
    family_space_id = Column(Integer, ForeignKey("family_spaces.id"), nullable=False)
    inviter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invitee_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    invitee_phone = Column(String(20), default="")
    invitee_email = Column(String(200), default="")
    role = Column(String(50), default="visitor")
    code = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), default="pending")
    message = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    family_space = relationship("FamilySpace", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[inviter_id])
    invitee_user = relationship("User", foreign_keys=[invitee_user_id])


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20), unique=True, default="")
    email = Column(String(200), unique=True, default="")
    hashed_password = Column(String(200), nullable=False)
    display_name = Column(String(100), default="")
    avatar = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    created_spaces = relationship("FamilySpace", foreign_keys="FamilySpace.creator_id", back_populates="creator")
    family_memberships = relationship("FamilyMember", back_populates="user")
