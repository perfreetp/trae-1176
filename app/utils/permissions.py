from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.family import FamilyMember
from app.schemas.family import VALID_ROLES, ROLE_PERMISSIONS


def validate_role(role: str):
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"无效角色，可选值: {', '.join(VALID_ROLES)}")


def get_member_role(db: Session, family_space_id: int, user_id: int) -> str:
    member = db.query(FamilyMember).filter(
        FamilyMember.family_space_id == family_space_id,
        FamilyMember.user_id == user_id,
    ).first()
    return member.role if member else None


def require_permission(db: Session, family_space_id: int, user_id: int, permission: str):
    role = get_member_role(db, family_space_id, user_id)
    if not role:
        raise HTTPException(status_code=403, detail="您不是该家庭馆成员")
    perms = ROLE_PERMISSIONS.get(role, set())
    if permission not in perms:
        raise HTTPException(status_code=403, detail=f"当前角色({role})无此操作权限: {permission}")


def update_last_active(db: Session, family_space_id: int, user_id: int):
    from datetime import datetime
    member = db.query(FamilyMember).filter(
        FamilyMember.family_space_id == family_space_id,
        FamilyMember.user_id == user_id,
    ).first()
    if member:
        member.last_active_at = datetime.utcnow()
        db.commit()
