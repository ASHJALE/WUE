"""Atomic quotation generation based on the Phase 5B-3 BOM preview."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.quotation import get
from app.models.estimate import Estimate
from app.models.quotation import Quotation
from app.models.quotation_item import QuotationItem
from app.schemas.quotation import QuotationGenerate
from app.services.bom import (
    BOMPreviewConflictError,
    MONEY_QUANTUM,
    ONE_HUNDRED,
    calculate_bom_preview,
)


class QuotationNotFoundError(Exception):
    """Raised when the requested estimate does not exist."""


class QuotationConflictError(Exception):
    """Raised when estimate, BOM, or inventory state prevents generation."""


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _quotation_number() -> str:
    return f"WUE-{datetime.now():%Y%m%d}-{uuid4().hex[:12].upper()}"


def generate(db: Session, estimate_id: int, data: QuotationGenerate) -> Quotation:
    """Create a quotation, its snapshots, and status update in one transaction."""
    try:
        estimate = db.scalar(
            select(Estimate).where(Estimate.id == estimate_id).with_for_update()
        )
        if estimate is None:
            raise QuotationNotFoundError("Estimate not found.")
        if estimate.selected_furniture_type_id is None:
            raise QuotationConflictError(
                "The estimate must have a selected furniture type."
            )
        if db.scalar(select(Quotation.id).where(Quotation.estimate_id == estimate_id)):
            raise QuotationConflictError(
                "A quotation already exists for this estimate."
            )
        if estimate.status != "processed":
            raise QuotationConflictError(
                f"Only processed estimates can be quoted; current status is {estimate.status}."
            )

        try:
            preview = calculate_bom_preview(db, estimate_id)
        except BOMPreviewConflictError as error:
            raise QuotationConflictError(str(error)) from error
        if preview.has_inventory_shortage:
            raise QuotationConflictError(
                "Quotation cannot be generated because primary BOM inventory is missing or insufficient."
            )

        material_total = _money(preview.material_total)
        labor_cost = _money(data.labor_cost)
        logistics_cost = _money(data.logistics_cost)
        profit_percentage = _money(data.profit_margin_percentage)
        subtotal = _money(material_total + labor_cost + logistics_cost)
        profit_amount = _money(subtotal * profit_percentage / ONE_HUNDRED)
        grand_total = _money(subtotal + profit_amount)

        quotation = Quotation(
            quotation_number=_quotation_number(),
            estimate_id=estimate_id,
            material_total=material_total,
            labor_cost=labor_cost,
            logistics_cost=logistics_cost,
            subtotal_before_profit=subtotal,
            profit_percentage=profit_percentage,
            profit_amount=profit_amount,
            grand_total=grand_total,
            currency_code="PHP",
            status="draft",
        )
        db.add(quotation)
        db.flush()
        for item in preview.items:
            db.add(
                QuotationItem(
                    quotation_id=quotation.id,
                    material_id=item.material_id,
                    furniture_material_id=item.furniture_material_id,
                    material_name_snapshot=item.material_name,
                    unit_snapshot=item.unit,
                    quantity=item.required_quantity,
                    unit_price_snapshot=item.current_unit_price,
                    line_total=item.line_total,
                    is_alternative=False,
                )
            )
        estimate.status = "quoted"
        db.commit()
    except (QuotationNotFoundError, QuotationConflictError):
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise QuotationConflictError(
            "Quotation generation conflicts with existing data."
        ) from error
    except Exception:
        db.rollback()
        raise

    return get(db, quotation.id)  # type: ignore[return-value]
