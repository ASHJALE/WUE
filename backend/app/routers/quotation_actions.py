"""Quotation approval workflow and PDF export endpoints."""

from typing import Annotated, Callable

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.crud import quotation as crud
from app.database import get_db
from app.models.quotation import Quotation
from app.routers.quotations import _detail_response
from app.schemas.quotation import QuotationRead
from app.services.pdf import build_quotation_pdf
from app.services.quotation_workflow import (
    InvalidQuotationTransitionError,
    QuotationActionNotFoundError,
    approve,
    complete,
    reject,
)

router = APIRouter(prefix="/quotations", tags=["Quotation actions"])
DbSession = Annotated[Session, Depends(get_db)]


def _run_action(
    action: Callable[[Session, int], Quotation], db: Session, quotation_id: int
) -> QuotationRead:
    try:
        return _detail_response(action(db, quotation_id))
    except QuotationActionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except InvalidQuotationTransitionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="The quotation status could not be updated due to a database error.",
        ) from error


@router.post("/{quotation_id}/approve", response_model=QuotationRead)
def approve_quotation(quotation_id: int, db: DbSession):
    return _run_action(approve, db, quotation_id)


@router.post("/{quotation_id}/reject", response_model=QuotationRead)
def reject_quotation(quotation_id: int, db: DbSession):
    return _run_action(reject, db, quotation_id)


@router.post("/{quotation_id}/complete", response_model=QuotationRead)
def complete_quotation(quotation_id: int, db: DbSession):
    return _run_action(complete, db, quotation_id)


@router.get("/{quotation_id}/pdf", response_class=Response)
def quotation_pdf(quotation_id: int, db: DbSession):
    quotation = crud.get(db, quotation_id)
    if quotation is None:
        raise HTTPException(status_code=404, detail="Quotation not found.")
    try:
        content = build_quotation_pdf(quotation)
    except Exception as error:
        raise HTTPException(status_code=500, detail="The quotation PDF could not be generated.") from error
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{quotation.quotation_number}.pdf"'
        },
    )
