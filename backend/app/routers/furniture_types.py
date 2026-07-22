"""Furniture type CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import ConflictError
from app.crud import furniture_type as crud
from app.database import get_db
from app.schemas.furniture_type import (
    FurnitureTypeCreate,
    FurnitureTypeRead,
    FurnitureTypeUpdate,
)

router = APIRouter(prefix="/furniture-types", tags=["Furniture Types"])
DbSession = Annotated[Session, Depends(get_db)]


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Furniture type not found.")


@router.post("", response_model=FurnitureTypeRead, status_code=status.HTTP_201_CREATED)
def create_furniture_type(data: FurnitureTypeCreate, db: DbSession):
    try:
        return crud.create(db, data)
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[FurnitureTypeRead])
def list_furniture_types(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
):
    return crud.list_all(db, skip, limit)


@router.get("/{furniture_type_id}", response_model=FurnitureTypeRead)
def get_furniture_type(furniture_type_id: int, db: DbSession):
    record = crud.get(db, furniture_type_id)
    if record is None:
        raise _not_found()
    return record


@router.put("/{furniture_type_id}", response_model=FurnitureTypeRead)
def update_furniture_type(
    furniture_type_id: int, data: FurnitureTypeUpdate, db: DbSession
):
    record = crud.get(db, furniture_type_id)
    if record is None:
        raise _not_found()
    try:
        return crud.update(db, record, data)
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.delete("/{furniture_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_furniture_type(furniture_type_id: int, db: DbSession) -> Response:
    record = crud.get(db, furniture_type_id)
    if record is None:
        raise _not_found()
    try:
        crud.delete(db, record)
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
