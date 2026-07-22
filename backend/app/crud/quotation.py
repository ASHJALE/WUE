"""Read operations for quotations."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.estimate import Estimate
from app.models.quotation import Quotation


def _query():
    return select(Quotation).options(
        joinedload(Quotation.estimate).joinedload(Estimate.user),
        joinedload(Quotation.estimate).joinedload(Estimate.selected_furniture_type),
        selectinload(Quotation.items),
    )


def get(db: Session, quotation_id: int) -> Quotation | None:
    return db.scalar(_query().where(Quotation.id == quotation_id))


def list_all(
    db: Session,
    skip: int,
    limit: int,
    estimate_id: int | None = None,
    user_id: int | None = None,
) -> list[Quotation]:
    statement = _query().order_by(Quotation.id)
    if estimate_id is not None:
        statement = statement.where(Quotation.estimate_id == estimate_id)
    if user_id is not None:
        statement = statement.join(Quotation.estimate).where(Estimate.user_id == user_id)
    return list(db.scalars(statement.offset(skip).limit(limit)))
