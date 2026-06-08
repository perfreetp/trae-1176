from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    family_space_id = Column(Integer, ForeignKey("family_spaces.id"), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), default="")
    target_id = Column(Integer, default=0)
    before_value = Column(Text, default="")
    after_value = Column(Text, default="")
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
