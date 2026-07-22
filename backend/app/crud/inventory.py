"""Inventory database operations."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.crud import ConflictError
from app.models.inventory import Inventory
from app.models.material import Material
from app.schemas.inventory import InventoryCreate, InventoryUpdate


def _validate_material(db: Session, material_id: int) -> None:
    if db.get(Material, material_id) is None:
        raise ConflictError("The referenced material does not exist.")


def _material_has_inventory(
    db: Session, material_id: int, exclude_id: int | None = None
) -> bool:
    statement = select(Inventory.id).where(Inventory.material_id == material_id)
    if exclude_id is not None:
        statement = statement.where(Inventory.id != exclude_id)
    return db.scalar(statement) is not None


def create(db: Session, data: InventoryCreate) -> Inventory:
    _validate_material(db, data.material_id)
    if _material_has_inventory(db, data.material_id):
        raise ConflictError("An inventory record already exists for this material.")

    record = Inventory(**data.model_dump())
    db.add(record)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("The inventory record conflicts with existing data.") from error
    db.refresh(record)
    return get(db, record.id)  # type: ignore[return-value]


def list_all(db: Session, skip: int, limit: int) -> list[Inventory]:
    statement = (
        select(Inventory)
        .options(joinedload(Inventory.material))
        .order_by(Inventory.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement))


def get(db: Session, inventory_id: int) -> Inventory | None:
    return db.scalar(
        select(Inventory)
        .options(joinedload(Inventory.material))
        .where(Inventory.id == inventory_id)
    )


def update(db: Session, record: Inventory, data: InventoryUpdate) -> Inventory:
    changes = data.model_dump(exclude_unset=True)
    new_material_id = changes.get("material_id")
    if new_material_id is not None:
        _validate_material(db, new_material_id)
        if _material_has_inventory(db, new_material_id, record.id):
            raise ConflictError("An inventory record already exists for this material.")

    for field, value in changes.items():
        setattr(record, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("The inventory record conflicts with existing data.") from error
    db.refresh(record)
    return get(db, record.id)  # type: ignore[return-value]


def delete(db: Session, record: Inventory) -> None:
    db.delete(record)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("The inventory record could not be deleted.") from error
