from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogOut, AuditLogQuery

router = APIRouter(prefix="/api/audit", tags=["审计追踪"])


@router.post("/logs", response_model=dict, summary="查询操作流水")
def query_audit_logs(data: AuditLogQuery, db: Session = Depends(get_db)):
    query = db.query(AuditLog).filter(AuditLog.family_space_id == data.family_space_id)
    if data.operator_id:
        query = query.filter(AuditLog.operator_id == data.operator_id)
    if data.action:
        query = query.filter(AuditLog.action == data.action)
    if data.action_prefix:
        query = query.filter(AuditLog.action.like(f"{data.action_prefix}%"))
    if data.time_from:
        try:
            query = query.filter(AuditLog.created_at >= datetime.fromisoformat(data.time_from))
        except ValueError:
            pass
    if data.time_to:
        try:
            query = query.filter(AuditLog.created_at <= datetime.fromisoformat(data.time_to))
        except ValueError:
            pass
    total = query.count()
    page = max(1, data.page)
    page_size = min(100, max(1, data.page_size))
    items = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "items": [AuditLogOut.model_validate(i).model_dump() for i in items]}


@router.get("/logs/{family_space_id}", response_model=List[AuditLogOut], summary="获取操作流水(简易)")
def list_audit_logs(
    family_space_id: int,
    operator_id: Optional[int] = None,
    action: Optional[str] = "",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog).filter(AuditLog.family_space_id == family_space_id)
    if operator_id:
        query = query.filter(AuditLog.operator_id == operator_id)
    if action:
        query = query.filter(AuditLog.action == action)
    return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
