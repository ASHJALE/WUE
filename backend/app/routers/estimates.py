"""Estimate CRUD and status-workflow endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.crud import ConflictError
from app.crud import estimate as crud
from app.database import get_db
from app.dependencies.auth import CurrentUser
from app.models.estimate import Estimate
from app.schemas.estimate import EstimateCreate, EstimateRead, EstimateStatus, EstimateUpdate
from app.schemas.calculation import BOMPreviewRead
from app.services.bom import (
    BOMPreviewConflictError,
    BOMPreviewNotFoundError,
    calculate_bom_preview,
)
from app.schemas.phase7_integration import Phase7IntegrationRead, Phase7IntegrationRequest
from app.services.phase7_integration_service import (
    Phase7IntegrationForbiddenError,
    Phase7IntegrationNotFoundError,
    Phase7IntegrationPersistenceError,
    Phase7IntegrationValidationError,
    integrate_phase7_workflow,
)

router = APIRouter(prefix="/estimates", tags=["Estimates"])
DbSession = Annotated[Session, Depends(get_db)]


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Estimate not found.")


def _response(record: Estimate) -> EstimateRead:
    snapshot = record.phase7_snapshot
    preliminary_quotation = snapshot.preliminary_quotation_json if snapshot else None
    return EstimateRead(
        id=record.id,
        user_id=record.user_id,
        username=record.user.username,
        selected_furniture_type_id=record.selected_furniture_type_id,
        selected_furniture_type_name=(
            record.selected_furniture_type.name
            if record.selected_furniture_type is not None
            else None
        ),
        recognized_furniture_type_id=record.recognized_furniture_type_id,
        recognized_furniture_type_name=(
            record.recognized_furniture_type.name
            if record.recognized_furniture_type is not None
            else None
        ),
        image_path=record.image_path,
        input_method=record.input_method,
        recognition_confidence=record.recognition_confidence,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        integration_status="integrated" if snapshot else "not_integrated",
        phase7_snapshot_saved=snapshot is not None,
        phase7_upload_id=snapshot.upload_id if snapshot else None,
        saved_cost_summary=snapshot.cost_summary_json if snapshot else None,
        preliminary_quotation_id=(
            preliminary_quotation.get("quotation_id") if preliminary_quotation else None
        ),
    )


@router.post("/{estimate_id}/integrate-phase7", response_model=Phase7IntegrationRead)
def integrate_phase7_estimate(
    estimate_id: int,
    data: Phase7IntegrationRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    try:
        return integrate_phase7_workflow(db, estimate_id, data, current_user)
    except Phase7IntegrationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Phase7IntegrationForbiddenError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except Phase7IntegrationValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Phase7IntegrationPersistenceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("", response_model=EstimateRead, status_code=status.HTTP_201_CREATED)
def create_estimate(data: EstimateCreate, db: DbSession):
    try:
        return _response(crud.create(db, data))
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[EstimateRead])
def list_estimates(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    user_id: int | None = None,
    estimate_status: Annotated[EstimateStatus | None, Query(alias="status")] = None,
):
    return [
        _response(record)
        for record in crud.list_all(db, skip, limit, user_id, estimate_status)
    ]


@router.get("/{estimate_id}", response_model=EstimateRead)
def get_estimate(estimate_id: int, db: DbSession):
    record = crud.get(db, estimate_id)
    if record is None:
        raise _not_found()
    return _response(record)


@router.get("/{estimate_id}/bom-preview", response_model=BOMPreviewRead)
def get_estimate_bom_preview(estimate_id: int, db: DbSession):
    try:
        return calculate_bom_preview(db, estimate_id)
    except BOMPreviewNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except BOMPreviewConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="The BOM preview could not be calculated due to a database error.",
        ) from error


@router.put("/{estimate_id}", response_model=EstimateRead)
def update_estimate(estimate_id: int, data: EstimateUpdate, db: DbSession):
    record = crud.get(db, estimate_id)
    if record is None:
        raise _not_found()
    try:
        return _response(crud.update(db, record, data))
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
