from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import secrets
from datetime import datetime, timedelta

from app.database import get_db
from app.models.family import FamilySpace, FamilyMember, FamilyInvitation, User
from app.schemas.family import (
    FamilySpaceCreate, FamilySpaceUpdate, FamilySpaceOut,
    FamilyMemberAdd, FamilyMemberOut,
    InvitationCreate, InvitationOut, InvitationAccept,
    UserCreate, UserOut
)

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


@router.post("/spaces", response_model=FamilySpaceOut, summary="创建家庭馆")
def create_family_space(data: FamilySpaceCreate, db: Session = Depends(get_db)):
    space = FamilySpace(
        name=data.name,
        description=data.description,
        cover_image=data.cover_image,
        creator_id=1,
        is_public=data.is_public,
    )
    db.add(space)
    db.flush()
    member = FamilyMember(
        family_space_id=space.id,
        user_id=1,
        role="owner",
        nickname="创建者",
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
    space = db.query(FamilySpace).filter(FamilySpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="家庭馆不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(space, key, value)
    space.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(space)
    return space


@router.delete("/spaces/{space_id}", summary="删除家庭馆")
def delete_family_space(space_id: int, db: Session = Depends(get_db)):
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
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.put("/spaces/{space_id}/members/{member_id}", response_model=FamilyMemberOut, summary="更新成员角色")
def update_member(space_id: int, member_id: int, data: FamilyMemberAdd, db: Session = Depends(get_db)):
    member = db.query(FamilyMember).filter(
        FamilyMember.id == member_id,
        FamilyMember.family_space_id == space_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    member.role = data.role
    member.nickname = data.nickname
    db.commit()
    db.refresh(member)
    return member


@router.delete("/spaces/{space_id}/members/{member_id}", summary="移除家庭成员")
def remove_member(space_id: int, member_id: int, db: Session = Depends(get_db)):
    member = db.query(FamilyMember).filter(
        FamilyMember.id == member_id,
        FamilyMember.family_space_id == space_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    if member.role == "owner":
        raise HTTPException(status_code=400, detail="不能移除馆主")
    db.delete(member)
    db.commit()
    return {"detail": "已移除"}


@router.post("/spaces/{space_id}/invitations", response_model=InvitationOut, summary="创建邀请")
def create_invitation(space_id: int, data: InvitationCreate, db: Session = Depends(get_db)):
    space = db.query(FamilySpace).filter(FamilySpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="家庭馆不存在")
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
        inviter_id=1,
        invitee_user_id=data.invitee_user_id,
        invitee_phone=data.invitee_phone,
        invitee_email=data.invitee_email,
        code=code,
        status="pending",
        message=data.message,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.get("/spaces/{space_id}/invitations", response_model=List[InvitationOut], summary="获取邀请列表")
def list_invitations(space_id: int, db: Session = Depends(get_db)):
    return db.query(FamilyInvitation).filter(FamilyInvitation.family_space_id == space_id).all()


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
    if invitation.invitee_user_id and invitation.invitee_user_id != data.user_id:
        raise HTTPException(status_code=403, detail="此邀请不适用于当前用户")
    if invitation.invitee_phone and invitation.invitee_phone != acceptor.phone:
        if invitation.invitee_email and invitation.invitee_email != acceptor.email:
            if invitation.invitee_user_id is None:
                raise HTTPException(status_code=403, detail="手机号或邮箱与邀请不匹配")
    existing = db.query(FamilyMember).filter(
        FamilyMember.family_space_id == invitation.family_space_id,
        FamilyMember.user_id == data.user_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已是该家庭馆成员，无需重复加入")
    invitation.status = "accepted"
    member = FamilyMember(
        family_space_id=invitation.family_space_id,
        user_id=data.user_id,
        role="member",
        nickname=acceptor.display_name or acceptor.username,
    )
    db.add(member)
    db.commit()
    db.refresh(invitation)
    return invitation
