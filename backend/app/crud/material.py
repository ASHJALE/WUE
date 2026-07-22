"""Material database operations."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud import ConflictError
from app.models.furniture_material import FurnitureMaterial
from app.models.inventory import Inventory
from app.models.material import Material
from app.models.quotation_item import QuotationItem
from app.schemas.material import MaterialCreate, MaterialUpdate


def _name_exists(db: Session, name: str, exclude_id: int | None = None) -> bool:
    statement = select(Material.id).where(func.lower(Material.name) == name.lower())
    if exclude_id is not None:
        statement = statement.where(Material.id != exclude_id)
    return db.scalar(statement) is not None


def _validate_alternative(
    db: Session, alternative_material_id: int | None, material_id: int | None = None
) -> None:
    if alternative_material_id is None:
        return
    if material_id is not None and alternative_material_id == material_id:
        raise ConflictError("A material cannot be its own alternative.")
    if db.get(Material, alternative_material_id) is None:
        raise ConflictError("The alternative material does not exist.")


def create(db: Session, data: MaterialCreate) -> Material:
    if _name_exists(db, data.name):
        raise ConflictError("A material with this name already exists.")
    _validate_alternative(db, data.alternative_material_id)

    record = Material(**data.model_dump())
    db.add(record)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("The material conflicts with existing data.") from error
    db.refresh(record)
    return record


def list_all(db: Session, skip: int, limit: int) -> list[Material]:
    return list(db.scalars(select(Material).order_by(Material.id).offset(skip).limit(limit)))


def get(db: Session, material_id: int) -> Material | None:
    return db.get(Material, material_id)


def update(db: Session, record: Material, data: MaterialUpdate) -> Material:
    changes = data.model_dump(exclude_unset=True)
    new_name = changes.get("name")
    if new_name is not None and _name_exists(db, new_name, record.id):
        raise ConflictError("A material with this name already exists.")
    if "alternative_material_id" in changes:
        _validate_alternative(db, changes["alternative_material_id"], record.id)

    for field, value in changes.items():
        setattr(record, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("The material conflicts with existing data.") from error
    db.refresh(record)
    return record


def delete(db: Session, record: Material) -> None:
    dependent_checks = (
        select(Inventory.id).where(Inventory.material_id == record.id),
        select(FurnitureMaterial.id).where(FurnitureMaterial.material_id == record.id),
        select(QuotationItem.id).where(QuotationItem.material_id == record.id),
        select(Material.id).where(Material.alternative_material_id == record.id),
    )
    if any(db.scalar(statement) is not None for statement in dependent_checks):
        raise ConflictError(
            "The material cannot be deleted because it is referenced by other records."
        )

    db.delete(record)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError(
            "The material cannot be deleted because it is referenced by other records."
        ) from error
