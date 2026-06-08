import json
from sqlalchemy.orm import Session
from app.models.audit import AuditLog


def write_audit(
    db: Session,
    family_space_id: int,
    operator_id: int,
    action: str,
    target_type: str = "",
    target_id: int = 0,
    before_value: str = "",
    after_value: str = "",
    detail: str = "",
):
    log = AuditLog(
        family_space_id=family_space_id,
        operator_id=operator_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before_value=before_value,
        after_value=after_value,
        detail=detail,
    )
    db.add(log)


def _val(v):
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def audit_create(db, family_space_id, operator_id, target_type, target_id, after=None):
    write_audit(db, family_space_id, operator_id, f"create_{target_type}", target_type, target_id, after_value=_val(after))


def audit_update(db, family_space_id, operator_id, target_type, target_id, before=None, after=None, detail=""):
    write_audit(db, family_space_id, operator_id, f"update_{target_type}", target_type, target_id, before_value=_val(before), after_value=_val(after), detail=detail)


def audit_delete(db, family_space_id, operator_id, target_type, target_id, detail=""):
    write_audit(db, family_space_id, operator_id, f"delete_{target_type}", target_type, target_id, detail=detail)


def audit_action(db, family_space_id, operator_id, action, target_type="", target_id=0, detail=""):
    write_audit(db, family_space_id, operator_id, action, target_type, target_id, detail=detail)
