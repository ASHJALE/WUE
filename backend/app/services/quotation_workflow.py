"""Transactional status transitions for stored quotations."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.quotation import get
from app.models.quotation import Quotation


class QuotationActionNotFoundError(Exception):
    """Raised when a quotation action targets a missing record."""


class InvalidQuotationTransitionError(Exception):
    """Raised when the requested status transition is not allowed."""


def _transition(
    db: Session, quotation_id: int, expected_status: str, new_status: str
) -> Quotation:
    try:
        quotation = db.scalar(
            select(Quotation)
            .where(Quotation.id == quotation_id)
            .with_for_update()
        )
        if quotation is None:
            raise QuotationActionNotFoundError("Quotation not found.")
        if quotation.status != expected_status:
            raise InvalidQuotationTransitionError(
                f"Quotation status cannot change from {quotation.status} to {new_status}."
            )
        quotation.status = new_status
        db.commit()
    except (QuotationActionNotFoundError, InvalidQuotationTransitionError):
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise InvalidQuotationTransitionError(
            "The quotation status could not be updated."
        ) from error
    except Exception:
        db.rollback()
        raise
    return get(db, quotation_id)  # type: ignore[return-value]


def approve(db: Session, quotation_id: int) -> Quotation:
    return _transition(db, quotation_id, "draft", "approved")


def reject(db: Session, quotation_id: int) -> Quotation:
    return _transition(db, quotation_id, "draft", "rejected")


def complete(db: Session, quotation_id: int) -> Quotation:
    return _transition(db, quotation_id, "approved", "completed")
