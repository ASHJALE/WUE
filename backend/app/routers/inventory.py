"""Inventory CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import ConflictError
from app.crud import inventory as crud
from app.database import get_db
from app.models.inventory import Inventory
from app.schemas.inventory import InventoryCreate, InventoryRead, InventoryUpdate

router = APIRouter(prefix="/inventory", tags=["Inventory"])
DbSession = Annotated[Session, Depends(get_db)]


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Inventory record not found.")


def _response(record: Inventory) -> InventoryRead:
    return InventoryRead(
        id=record.id,
        material_id=record.material_id,
        material_name=record.material.name,
        quantity_available=record.quantity_available,
        reorder_level=record.reorder_level,
        updated_at=record.updated_at,
    )


@router.post("", response_model=InventoryRead, status_code=status.HTTP_201_CREATED)
def create_inventory(data: InventoryCreate, db: DbSession):
    try:
        return _response(crud.create(db, data))
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[InventoryRead])
def list_inventory(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
):
    return [_response(record) for record in crud.list_all(db, skip, limit)]


@router.get("/{inventory_id}", response_model=InventoryRead)
def get_inventory(inventory_id: int, db: DbSession):
    record = crud.get(db, inventory_id)
    if record is None:
        raise _not_found()
    return _response(record)


@router.put("/{inventory_id}", response_model=InventoryRead)
def update_inventory(inventory_id: int, data: InventoryUpdate, db: DbSession):
    record = crud.get(db, inventory_id)
    if record is None:
        raise _not_found()
    try:
        return _response(crud.update(db, record, data))
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.delete("/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory(inventory_id: int, db: DbSession) -> Response:
    record = crud.get(db, inventory_id)
    if record is None:
        raise _not_found()
    try:
        crud.delete(db, record)
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
