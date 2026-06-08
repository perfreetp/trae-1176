from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import secrets
from datetime import datetime, timedelta

from app.database import get_db
from app.models.family import FamilySpace, FamilyMember, FamilyInvitation, User
from app.schemas.family import (
    FamilySpaceCreate, FamilySpaceUpdate, FamilySpaceOut,
    FamilyMemberAdd, FamilyMemberOut, MemberRoleUpdate,
    InvitationCreate, InvitationOut, InvitationAccept,
    UserCreate, UserOut, VALID_ROLES, ROLE_PERMISSIONS,
    SpaceActionRequest, BatchInviteRequest, BatchInviteResultItem, BatchInviteResponse,
)
from app.utils.permissions import validate_role, require_permission, update_last_active
from app.utils.audit import audit_create, audit_update, audit_delete, audit_action

router = APIRouter(prefix="/api/family", tags=["家庭空间"])


@router.post("/users", response_model=UserOut, summary="注册用户")
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    import bcrypt
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    hashed = bcrypt.hashpw(data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(
        username=data.username,
        hashed_password=hashed,
        phone=data.phone,
        email=data.email,
        display_name=data.display_name or data.username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserOut, summary="获取用户信息")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.get("/roles", summary="获取角色定义和权限矩阵")
def get_role_definitions():
    return {
        "roles": VALID_ROLES,
        "permissions": {role: sorted(perms) for role, perms in ROLE_PERMISSIONS.items()},
    }


@router.post("/spaces", response_model=FamilySpaceOut, summary="创建家庭馆")
def create_family_space(data: FamilySpaceCreate, db: Session = Depends(get_db)):
    space = FamilySpace(
        name=data.name,
        description=data.description,
        cover_image=data.cover_image,
        creator_id=data.creator_id,
        is_public=data.is_public,
    )
    db.add(space)
    db.flush()
    member = FamilyMember(
        family_space_id=space.id,
        user_id=data.creator_id,
        role="owner",
        nickname="创建者",
        join_source="creator",
        last_active_at=datetime.utcnow(),
    )
    db.add(member)
    db.commit()
    db.refresh(space)
    return space


@router.get("/spaces", response_model=List[FamilySpaceOut], summary="获取家庭馆列表")
def list_family_spaces(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(FamilySpace).offset(skip).limit(limit).all()


@router.get("/spaces/{space_id}", response_model=FamilySpaceOut, summary="获取家庭馆详情")
def get_family_space(space_id: int, db: Session = Depends(get_db)):
    space = db.query(FamilySpace).filter(FamilySpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="家庭馆不存在")
    return space


@router.put("/spaces/{space_id}", response_model=FamilySpaceOut, summary="更新家庭馆信息")
def update_family_space(space_id: int, data: FamilySpaceUpdate, db: Session = Depends(get_db)):
    require_permission(db, space_id, data.operator_id, "manage_space")
    space = db.query(FamilySpace).filter(FamilySpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="家庭馆不存在")
    update_data = data.model_dump(exclude_unset=True, exclude={"operator_id"})
    for key, value in update_data.items():
        setattr(space, key, value)
    space.updated_at = datetime.utcnow()
    update_last_active(db, space_id, data.operator_id)
    db.commit()
    db.refresh(space)
    return space


@router.delete("/spaces/{space_id}", summary="删除家庭馆")
def delete_family_space(space_id: int, data: SpaceActionRequest, db: Session = Depends(get_db)):
    require_permission(db, space_id, data.operator_id, "manage_space")
    space = db.query(FamilySpace).filter(FamilySpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="家庭馆不存在")
    db.delete(space)
    db.commit()
    return {"detail": "已删除"}


@router.get("/spaces/{space_id}/members", response_model=List[FamilyMemberOut], summary="获取家庭成员列表")
def list_members(space_id: int, db: Session = Depends(get_db)):
    return db.query(FamilyMember).filter(FamilyMember.family_space_id == space_id).all()


@router.post("/spaces/{space_id}/members", response_model=FamilyMemberOut, summary="添加家庭成员")
def add_member(space_id: int, data: FamilyMemberAdd, db: Session = Depends(get_db)):
    require_permission(db, space_id, data.operator_id, "manage_members")
    validate_role(data.role)
    space = db.query(FamilySpace).filter(FamilySpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="家庭馆不存在")
    existing = db.query(FamilyMember).filter(
        FamilyMember.family_space_id == space_id,
        FamilyMember.user_id == data.user_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该用户已是成员")
    member = FamilyMember(
        family_space_id=space_id,
        user_id=data.user_id,
        role=data.role,
        nickname=data.nickname,
        join_source="direct",
        last_active_at=datetime.utcnow(),
    )
    db.add(member)
    update_last_active(db, space_id, data.operator_id)
    audit_create(db, space_id, data.operator_id, "member", member.id, after={"user_id": data.user_id, "role": data.role, "join_source": "direct"})
    db.commit()
    db.refresh(member)
    return member


@router.put("/spaces/{space_id}/members/{member_id}", response_model=FamilyMemberOut, summary="更新成员角色")
def update_member(space_id: int, member_id: int, data: MemberRoleUpdate, db: Session = Depends(get_db)):
    require_permission(db, space_id, data.operator_id, "manage_members")
    validate_role(data.role)
    member = db.query(FamilyMember).filter(
        FamilyMember.id == member_id,
        FamilyMember.family_space_id == space_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    if member.role == "owner" and data.role != "owner":
        owner_count = db.query(FamilyMember).filter(
            FamilyMember.family_space_id == space_id,
            FamilyMember.role == "owner",
        ).count()
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="家庭馆必须至少保留一位馆主，请先转让馆主")
    old_role = member.role
    member.role = data.role
    if data.nickname is not None:
        member.nickname = data.nickname
    update_last_active(db, space_id, data.operator_id)
    audit_update(db, space_id, data.operator_id, "member_role", member.id, before={"role": old_role}, after={"role": data.role}, detail=f"角色从{old_role}改为{data.role}")
    db.commit()
    db.refresh(member)
    return member


@router.delete("/spaces/{space_id}/members/{member_id}", summary="移除家庭成员")
def remove_member(space_id: int, member_id: int, data: SpaceActionRequest, db: Session = Depends(get_db)):
    require_permission(db, space_id, data.operator_id, "manage_members")
    member = db.query(FamilyMember).filter(
        FamilyMember.id == member_id,
        FamilyMember.family_space_id == space_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    if member.role == "owner":
        raise HTTPException(status_code=400, detail="不能移除馆主，请先转让馆主角色")
    audit_delete(db, space_id, data.operator_id, "member", member.id, detail=f"移除用户{member.user_id}角色{member.role}")
    db.delete(member)
    update_last_active(db, space_id, data.operator_id)
    db.commit()
    return {"detail": "已移除"}


@router.post("/spaces/{space_id}/invitations", response_model=InvitationOut, summary="创建邀请")
def create_invitation(space_id: int, data: InvitationCreate, db: Session = Depends(get_db)):
    require_permission(db, space_id, data.operator_id, "invite_members")
    validate_role(data.role)
    space = db.query(FamilySpace).filter(FamilySpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="家庭馆不存在")
    if not data.invitee_user_id and not data.invitee_phone and not data.invitee_email:
        raise HTTPException(status_code=400, detail="请至少指定一种邀请方式（用户ID/手机号/邮箱）")
    if data.invitee_user_id:
        invitee = db.query(User).filter(User.id == data.invitee_user_id).first()
        if not invitee:
            raise HTTPException(status_code=404, detail="被邀请用户不存在")
        already = db.query(FamilyMember).filter(
            FamilyMember.family_space_id == space_id,
            FamilyMember.user_id == data.invitee_user_id,
        ).first()
        if already:
            raise HTTPException(status_code=400, detail="该用户已是本馆成员")
    code = secrets.token_urlsafe(16)
    invitation = FamilyInvitation(
        family_space_id=space_id,
        inviter_id=data.operator_id,
        invitee_user_id=data.invitee_user_id,
        invitee_phone=data.invitee_phone,
        invitee_email=data.invitee_email,
        role=data.role,
        code=code,
        status="pending",
        message=data.message,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invitation)
    update_last_active(db, space_id, data.operator_id)
    audit_action(db, space_id, data.operator_id, "create_invitation", "invitation", invitation.id, detail=f"邀请方式: user={data.invitee_user_id} phone={data.invitee_phone} email={data.invitee_email} role={data.role}")
    db.commit()
    db.refresh(invitation)
    return invitation


@router.get("/spaces/{space_id}/invitations", response_model=List[InvitationOut], summary="获取邀请列表(支持状态筛选)")
def list_invitations(space_id: int, status: str = "", db: Session = Depends(get_db)):
    query = db.query(FamilyInvitation).filter(FamilyInvitation.family_space_id == space_id)
    if status:
        query = query.filter(FamilyInvitation.status == status)
    return query.order_by(FamilyInvitation.created_at.desc()).all()


@router.post("/invitations/accept", response_model=InvitationOut, summary="接受邀请")
def accept_invitation(data: InvitationAccept, db: Session = Depends(get_db)):
    acceptor = db.query(User).filter(User.id == data.user_id).first()
    if not acceptor:
        raise HTTPException(status_code=404, detail="用户不存在")
    invitation = db.query(FamilyInvitation).filter(FamilyInvitation.code == data.code).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="邀请不存在")
    if invitation.status != "pending":
        raise HTTPException(status_code=400, detail="邀请已处理，不可重复接受")
    if invitation.expires_at and invitation.expires_at < datetime.utcnow():
        invitation.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="邀请已过期")
    existing = db.query(FamilyMember).filter(
        FamilyMember.family_space_id == invitation.family_space_id,
        FamilyMember.user_id == data.user_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已是该家庭馆成员，无需重复加入")

    matched = False
    if invitation.invitee_user_id:
        if invitation.invitee_user_id == data.user_id:
            matched = True
        else:
            raise HTTPException(status_code=403, detail="此邀请不适用于当前用户")
    elif invitation.invitee_phone:
        if invitation.invitee_phone == acceptor.phone:
            matched = True
        else:
            raise HTTPException(status_code=403, detail="手机号与邀请不匹配，只有被邀请手机号对应的账号可接受")
    elif invitation.invitee_email:
        if invitation.invitee_email == acceptor.email:
            matched = True
        else:
            raise HTTPException(status_code=403, detail="邮箱与邀请不匹配，只有被邀请邮箱对应的账号可接受")

    if not matched:
        raise HTTPException(status_code=403, detail="无法验证您是被邀请人")

    invitation.status = "accepted"
    member = FamilyMember(
        family_space_id=invitation.family_space_id,
        user_id=data.user_id,
        role=invitation.role,
        nickname=acceptor.display_name or acceptor.username,
        join_source="invitation",
        last_active_at=datetime.utcnow(),
    )
    db.add(member)
    audit_action(db, invitation.family_space_id, data.user_id, "accept_invitation", "invitation", invitation.id, detail=f"接受邀请成为{invitation.role}")
    db.commit()
    db.refresh(invitation)
    return invitation


import re

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/spaces/{space_id}/invitations/batch", response_model=BatchInviteResponse, summary="批量邀请")
def batch_invite(space_id: int, data: BatchInviteRequest, db: Session = Depends(get_db)):
    require_permission(db, space_id, data.operator_id, "invite_members")
    validate_role(data.role)
    space = db.query(FamilySpace).filter(FamilySpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="家庭馆不存在")

    results = []
    for item in data.items:
        phone = (item.phone or "").strip()
        email = (item.email or "").strip()

        if not phone and not email:
            results.append(BatchInviteResultItem(phone=phone, email=email, status="invalid", detail="手机号和邮箱都为空"))
            continue

        if phone and not PHONE_RE.match(phone):
            results.append(BatchInviteResultItem(phone=phone, email=email, status="invalid", detail=f"手机号格式不正确: {phone}"))
            continue

        if email and not EMAIL_RE.match(email):
            results.append(BatchInviteResultItem(phone=phone, email=email, status="invalid", detail=f"邮箱格式不正确: {email}"))
            continue

        if phone:
            existing_user = db.query(User).filter(User.phone == phone).first()
            if existing_user:
                already = db.query(FamilyMember).filter(
                    FamilyMember.family_space_id == space_id,
                    FamilyMember.user_id == existing_user.id,
                ).first()
                if already:
                    results.append(BatchInviteResultItem(phone=phone, email=email, status="already_member", detail=f"手机号{phone}对应用户已是成员"))
                    continue

        if email:
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                already = db.query(FamilyMember).filter(
                    FamilyMember.family_space_id == space_id,
                    FamilyMember.user_id == existing_user.id,
                ).first()
                if already:
                    results.append(BatchInviteResultItem(phone=phone, email=email, status="already_member", detail=f"邮箱{email}对应用户已是成员"))
                    continue

        code = secrets.token_urlsafe(16)
        invitation = FamilyInvitation(
            family_space_id=space_id,
            inviter_id=data.operator_id,
            invitee_phone=phone,
            invitee_email=email,
            role=data.role,
            code=code,
            status="pending",
            message=data.message,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db.add(invitation)
        db.flush()
        results.append(BatchInviteResultItem(
            phone=phone, email=email, status="success",
            detail="邀请已创建", invitation_id=invitation.id,
        ))
        audit_action(db, space_id, data.operator_id, "batch_invite", "invitation", invitation.id, detail=f"批量邀请: phone={phone} email={email}")

    update_last_active(db, space_id, data.operator_id)
    db.commit()
    return BatchInviteResponse(results=results)
