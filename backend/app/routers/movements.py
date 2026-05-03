from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Movement, User
from app.schemas import MovementCreate, MovementListRead, MovementRead, MovementUpdate

router = APIRouter(prefix="/api/movements", tags=["movements"])


def _get_or_404(db: Session, movement_id: int) -> Movement:
    m = db.get(Movement, movement_id)
    if not m:
        raise HTTPException(status_code=404, detail="Movement not found")
    return m


@router.get("", response_model=List[MovementListRead])
def list_movements(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    movements = (
        db.query(Movement)
        .order_by(Movement.entry_date.desc().nullslast(), Movement.id.desc())
        .all()
    )
    return [MovementListRead.from_movement(m) for m in movements]


@router.get("/{movement_id}", response_model=MovementRead)
def get_movement(
    movement_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return _get_or_404(db, movement_id)


@router.post("", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
def create_movement(
    payload: MovementCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = Movement(**payload.model_dump(), created_by=user.id)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.put("/{movement_id}", response_model=MovementRead)
def update_movement(
    movement_id: int,
    payload: MovementUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    m = _get_or_404(db, movement_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(m, field, value)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movement(
    movement_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    m = _get_or_404(db, movement_id)
    db.delete(m)
    db.commit()
