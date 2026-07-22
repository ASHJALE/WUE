"""Quotation generation and read endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.crud import quotation as crud
from app.database import get_db
from app.models.quotation import Quotation
from app.schemas.quotation import (
    QuotationGenerate,
    QuotationItemRead,
    QuotationListRead,
    QuotationRead,
)
from app.services.quotation import (
    QuotationConflictError,
    QuotationNotFoundError,
    generate,
)

router = APIRouter(tags=["Quotations"])
DbSession = Annotated[Session, Depends(get_db)]


def _list_response(record: Quotation) -> QuotationListRead:
    estimate = record.estimate
    furniture_type = estimate.selected_furniture_type
    return QuotationListRead(
        id=record.id,
        quotation_number=record.quotation_number,
        estimate_id=record.estimate_id,
        user_id=estimate.user_id,
        username=estimate.user.username,
        furniture_type_id=estimate.selected_furniture_type_id,
        furniture_type_name=furniture_type.name,
        material_total=record.material_total,
        labor_cost=record.labor_cost,
        logistics_cost=record.logistics_cost,
        subtotal_before_profit=record.subtotal_before_profit,
        profit_percentage=record.profit_percentage,
        profit_amount=record.profit_amount,
        grand_total=record.grand_total,
        currency_code=record.currency_code,
        status=record.status,
        valid_until=record.valid_until,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _detail_response(record: Quotation) -> QuotationRead:
    return QuotationRead(
        **_list_response(record).model_dump(),
        items=[QuotationItemRead.model_validate(item) for item in sorted(record.items, key=lambda item: item.id)],
    )


@router.post(
    "/estimates/{estimate_id}/quotation",
    response_model=QuotationRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_quotation(estimate_id: int, data: QuotationGenerate, db: DbSession):
    try:
        return _detail_response(generate(db, estimate_id, data))
    except QuotationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except QuotationConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="The quotation could not be generated due to a database error.",
        ) from error


@router.get("/quotations", response_model=list[QuotationListRead])
def list_quotations(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    estimate_id: int | None = None,
    user_id: int | None = None,
):
    return [
        _list_response(record)
        for record in crud.list_all(db, skip, limit, estimate_id, user_id)
    ]


@router.get("/quotations/{quotation_id}", response_model=QuotationRead)
def get_quotation(quotation_id: int, db: DbSession):
    record = crud.get(db, quotation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Quotation not found.")
    return _detail_response(record)
