"""Furniture type database operations."""

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud import ConflictError
from app.models.estimate import Estimate
from app.models.furniture_material import FurnitureMaterial
from app.models.furniture_type import FurnitureType
from app.schemas.furniture_type import FurnitureTypeCreate, FurnitureTypeUpdate


def _name_exists(db: Session, name: str, exclude_id: int | None = None) -> bool:
    statement = select(FurnitureType.id).where(
        func.lower(FurnitureType.name) == name.lower()
    )
    if exclude_id is not None:
        statement = statement.where(FurnitureType.id != exclude_id)
    return db.scalar(statement) is not None


def create(db: Session, data: FurnitureTypeCreate) -> FurnitureType:
    if _name_exists(db, data.name):
        raise ConflictError("A furniture type with this name already exists.")

    record = FurnitureType(**data.model_dump())
    db.add(record)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("The furniture type conflicts with existing data.") from error
    db.refresh(record)
    return record


def list_all(db: Session, skip: int, limit: int) -> list[FurnitureType]:
    return list(
        db.scalars(select(FurnitureType).order_by(FurnitureType.id).offset(skip).limit(limit))
    )


def get(db: Session, furniture_type_id: int) -> FurnitureType | None:
    return db.get(FurnitureType, furniture_type_id)


def update(
    db: Session, record: FurnitureType, data: FurnitureTypeUpdate
) -> FurnitureType:
    changes = data.model_dump(exclude_unset=True)
    new_name = changes.get("name")
    if new_name is not None and _name_exists(db, new_name, record.id):
        raise ConflictError("A furniture type with this name already exists.")

    for field, value in changes.items():
        setattr(record, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("The furniture type conflicts with existing data.") from error
    db.refresh(record)
    return record


def delete(db: Session, record: FurnitureType) -> None:
    has_dependents = db.scalar(
        select(FurnitureType.id).where(
            FurnitureType.id == record.id,
            or_(
                select(FurnitureMaterial.id)
                .where(FurnitureMaterial.furniture_type_id == record.id)
                .exists(),
                select(Estimate.id)
                .where(
                    or_(
                        Estimate.selected_furniture_type_id == record.id,
                        Estimate.recognized_furniture_type_id == record.id,
                    )
                )
                .exists(),
            ),
        )
    )
    if has_dependents is not None:
        raise ConflictError(
            "The furniture type cannot be deleted because it is referenced by other records."
        )

    db.delete(record)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError(
            "The furniture type cannot be deleted because it is referenced by other records."
        ) from error
