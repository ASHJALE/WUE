"""Furniture Bill of Materials database operations."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.crud import ConflictError
from app.models.furniture_material import FurnitureMaterial
from app.models.furniture_type import FurnitureType
from app.models.material import Material
from app.models.quotation_item import QuotationItem
from app.schemas.furniture_material import (
    FurnitureMaterialCreate,
    FurnitureMaterialUpdate,
)


def _validate_references(
    db: Session, furniture_type_id: int, material_id: int
) -> None:
    if db.get(FurnitureType, furniture_type_id) is None:
        raise ConflictError("The referenced furniture type does not exist.")
    if db.get(Material, material_id) is None:
        raise ConflictError("The referenced material does not exist.")


def _combination_exists(
    db: Session,
    furniture_type_id: int,
    material_id: int,
    exclude_id: int | None = None,
) -> bool:
    statement = select(FurnitureMaterial.id).where(
        FurnitureMaterial.furniture_type_id == furniture_type_id,
        FurnitureMaterial.material_id == material_id,
    )
    if exclude_id is not None:
        statement = statement.where(FurnitureMaterial.id != exclude_id)
    return db.scalar(statement) is not None


def create(db: Session, data: FurnitureMaterialCreate) -> FurnitureMaterial:
    _validate_references(db, data.furniture_type_id, data.material_id)
    if _combination_exists(db, data.furniture_type_id, data.material_id):
        raise ConflictError(
            "This material already exists in the selected furniture type's BOM."
        )

    record = FurnitureMaterial(**data.model_dump())
    db.add(record)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("The BOM entry conflicts with existing data.") from error
    db.refresh(record)
    return get(db, record.id)  # type: ignore[return-value]


def list_all(
    db: Session, skip: int, limit: int, furniture_type_id: int | None = None
) -> list[FurnitureMaterial]:
    statement = (
        select(FurnitureMaterial)
        .options(
            joinedload(FurnitureMaterial.furniture_type),
            joinedload(FurnitureMaterial.material),
        )
        .order_by(FurnitureMaterial.id)
    )
    if furniture_type_id is not None:
        statement = statement.where(
            FurnitureMaterial.furniture_type_id == furniture_type_id
        )
    return list(db.scalars(statement.offset(skip).limit(limit)))


def get(db: Session, furniture_material_id: int) -> FurnitureMaterial | None:
    return db.scalar(
        select(FurnitureMaterial)
        .options(
            joinedload(FurnitureMaterial.furniture_type),
            joinedload(FurnitureMaterial.material),
        )
        .where(FurnitureMaterial.id == furniture_material_id)
    )


def update(
    db: Session, record: FurnitureMaterial, data: FurnitureMaterialUpdate
) -> FurnitureMaterial:
    changes = data.model_dump(exclude_unset=True)
    furniture_type_id = changes.get(
        "furniture_type_id", record.furniture_type_id
    )
    material_id = changes.get("material_id", record.material_id)
    _validate_references(db, furniture_type_id, material_id)
    if _combination_exists(db, furniture_type_id, material_id, record.id):
        raise ConflictError(
            "This material already exists in the selected furniture type's BOM."
        )

    for field, value in changes.items():
        setattr(record, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("The BOM entry conflicts with existing data.") from error
    db.refresh(record)
    return get(db, record.id)  # type: ignore[return-value]


def delete(db: Session, record: FurnitureMaterial) -> None:
    is_referenced = db.scalar(
        select(QuotationItem.id).where(
            QuotationItem.furniture_material_id == record.id
        )
    )
    if is_referenced is not None:
        raise ConflictError(
            "The BOM entry cannot be deleted because quotation items reference it."
        )

    db.delete(record)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError(
            "The BOM entry cannot be deleted because other records reference it."
        ) from error
