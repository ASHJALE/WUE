"""Material CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import ConflictError
from app.crud import material as crud
from app.database import get_db
from app.schemas.material import MaterialCreate, MaterialRead, MaterialUpdate

router = APIRouter(prefix="/materials", tags=["Materials"])
DbSession = Annotated[Session, Depends(get_db)]


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Material not found.")


@router.post("", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
def create_material(data: MaterialCreate, db: DbSession):
    try:
        return crud.create(db, data)
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[MaterialRead])
def list_materials(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
):
    return crud.list_all(db, skip, limit)


@router.get("/{material_id}", response_model=MaterialRead)
def get_material(material_id: int, db: DbSession):
    record = crud.get(db, material_id)
    if record is None:
        raise _not_found()
    return record


@router.put("/{material_id}", response_model=MaterialRead)
def update_material(material_id: int, data: MaterialUpdate, db: DbSession):
    record = crud.get(db, material_id)
    if record is None:
        raise _not_found()
    try:
        return crud.update(db, record, data)
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(material_id: int, db: DbSession) -> Response:
    record = crud.get(db, material_id)
    if record is None:
        raise _not_found()
    try:
        crud.delete(db, record)
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
