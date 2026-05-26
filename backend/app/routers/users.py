"""User administration endpoints. Admin-only (require_admin) on every route.

Guards:
- Can't delete yourself
- Can't deactivate yourself
- Can't demote yourself (admin → operator)
- Can't remove the last active admin (would lock out the system)
- Username uniqueness enforced (409 on collision)
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import User
from app.schemas import PasswordSet, UserAdminCreate, UserAdminUpdate, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

VALID_ROLES = ("admin", "operator")


def _hash(password: str) -> str:
    return pwd_ctx.hash(password)


def _count_active_admins(db: Session, exclude_id: int | None = None) -> int:
    q = db.query(User).filter(User.role == "admin", User.is_active == True)
    if exclude_id is not None:
        q = q.filter(User.id != exclude_id)
    return q.count()


@router.get("", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(User).order_by(User.username).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserAdminCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if payload.role not in VALID_ROLES:
        raise HTTPException(400, f"role must be one of {VALID_ROLES}")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(409, "Користувач з таким логіном уже існує")
    if not payload.password or len(payload.password) < 4:
        raise HTTPException(400, "Пароль не може бути коротшим за 4 символи")

    user = User(
        username=payload.username,
        hashed_password=_hash(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    if payload.username is not None and payload.username != user.username:
        if db.query(User).filter(User.username == payload.username, User.id != user_id).first():
            raise HTTPException(409, "Користувач з таким логіном уже існує")
        user.username = payload.username

    if payload.role is not None and payload.role != user.role:
        if payload.role not in VALID_ROLES:
            raise HTTPException(400, f"role must be one of {VALID_ROLES}")
        if user.id == current.id and payload.role != "admin":
            raise HTTPException(400, "Не можна понизити власну роль")
        # If demoting an admin → check at least one admin remains
        if user.role == "admin" and payload.role != "admin":
            if _count_active_admins(db, exclude_id=user.id) == 0:
                raise HTTPException(400, "У системі має лишитися щонайменше один admin")
        user.role = payload.role

    if payload.is_active is not None and payload.is_active != user.is_active:
        if user.id == current.id and not payload.is_active:
            raise HTTPException(400, "Не можна деактивувати власний обліковий запис")
        if user.role == "admin" and not payload.is_active:
            if _count_active_admins(db, exclude_id=user.id) == 0:
                raise HTTPException(400, "У системі має лишитися щонайменше один активний admin")
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def set_password(
    user_id: int,
    payload: PasswordSet,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if not payload.password or len(payload.password) < 4:
        raise HTTPException(400, "Пароль не може бути коротшим за 4 символи")
    user.hashed_password = _hash(payload.password)
    db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == current.id:
        raise HTTPException(400, "Не можна видалити власний обліковий запис")
    if user.role == "admin" and _count_active_admins(db, exclude_id=user.id) == 0:
        raise HTTPException(400, "У системі має лишитися щонайменше один admin")
    db.delete(user)
    db.commit()
