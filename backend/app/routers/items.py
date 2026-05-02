from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import AssetDocument, Item, ItemDocument, User
from app.schemas import ItemCreate, ItemListRead, ItemRead, ItemUpdate

router = APIRouter(prefix="/api/items", tags=["items"])


def _sync_documents(db: Session, item_id: int, docs: list) -> None:
    links = db.query(ItemDocument).filter(ItemDocument.item_id == item_id).all()
    doc_ids = [lnk.doc_id for lnk in links]
    for lnk in links:
        db.delete(lnk)
    db.flush()
    for doc_id in doc_ids:
        doc = db.get(AssetDocument, doc_id)
        if doc:
            db.delete(doc)
    db.flush()
    for d in docs:
        if not any([d.doc_type, d.doc_number, d.doc_date]):
            continue
        doc = AssetDocument(doc_type=d.doc_type, doc_number=d.doc_number, doc_date=d.doc_date)
        db.add(doc)
        db.flush()
        db.add(ItemDocument(item_id=item_id, doc_id=doc.id))


def _get_or_404(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get("", response_model=List[ItemListRead])
def list_items(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Item).order_by(Item.number).all()


@router.get("/{item_id}", response_model=ItemRead)
def get_item(item_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _get_or_404(db, item_id)


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = db.query(Item).filter(Item.number == payload.number).first()
    if existing:
        raise HTTPException(status_code=409, detail="Item number already exists")

    item = Item(
        number=payload.number,
        name=payload.name,
        category=payload.category,
        nomenclature_code=payload.nomenclature_code,
        serial_number=payload.serial_number,
        unit_of_measure=payload.unit_of_measure,
        price=payload.price,
        quantity=payload.quantity,
        item_type=payload.item_type,
        batch_id=payload.batch_id,
        notes=payload.notes,
        is_official=payload.is_official,
        created_by=user.id,
    )
    db.add(item)
    db.flush()
    _sync_documents(db, item.id, payload.documents)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int,
    payload: ItemUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = _get_or_404(db, item_id)

    if payload.number and payload.number != item.number:
        conflict = db.query(Item).filter(Item.number == payload.number).first()
        if conflict:
            raise HTTPException(status_code=409, detail="Item number already exists")

    for field, value in payload.model_dump(exclude_unset=True, exclude={"documents"}).items():
        setattr(item, field, value)

    if payload.documents is not None:
        _sync_documents(db, item_id, payload.documents)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = _get_or_404(db, item_id)
    _sync_documents(db, item_id, [])
    db.delete(item)
    db.commit()
