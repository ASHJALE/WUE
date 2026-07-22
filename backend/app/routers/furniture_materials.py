"""Furniture Bill of Materials CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import ConflictError
from app.crud import furniture_material as crud
from app.database import get_db
from app.models.furniture_material import FurnitureMaterial
from app.schemas.furniture_material import (
    FurnitureMaterialCreate,
    FurnitureMaterialRead,
    FurnitureMaterialUpdate,
)

router = APIRouter(prefix="/furniture-materials", tags=["Furniture Materials"])
DbSession = Annotated[Session, Depends(get_db)]


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="BOM entry not found.")


def _response(record: FurnitureMaterial) -> FurnitureMaterialRead:
    return FurnitureMaterialRead(
        id=record.id,
        furniture_type_id=record.furniture_type_id,
        furniture_type_name=record.furniture_type.name,
        material_id=record.material_id,
        material_name=record.material.name,
        quantity_required=record.quantity_required,
        wastage_percentage=record.wastage_percentage,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("", response_model=FurnitureMaterialRead, status_code=status.HTTP_201_CREATED)
def create_furniture_material(data: FurnitureMaterialCreate, db: DbSession):
    try:
        return _response(crud.create(db, data))
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[FurnitureMaterialRead])
def list_furniture_materials(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    furniture_type_id: int | None = None,
):
    return [
        _response(record)
        for record in crud.list_all(db, skip, limit, furniture_type_id)
    ]


@router.get("/{furniture_material_id}", response_model=FurnitureMaterialRead)
def get_furniture_material(furniture_material_id: int, db: DbSession):
    record = crud.get(db, furniture_material_id)
    if record is None:
        raise _not_found()
    return _response(record)


@router.put("/{furniture_material_id}", response_model=FurnitureMaterialRead)
def update_furniture_material(
    furniture_material_id: int,
    data: FurnitureMaterialUpdate,
    db: DbSession,
):
    record = crud.get(db, furniture_material_id)
    if record is None:
        raise _not_found()
    try:
        return _response(crud.update(db, record, data))
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.delete("/{furniture_material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_furniture_material(
    furniture_material_id: int, db: DbSession
) -> Response:
    record = crud.get(db, furniture_material_id)
    if record is None:
        raise _not_found()
    try:
        crud.delete(db, record)
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
