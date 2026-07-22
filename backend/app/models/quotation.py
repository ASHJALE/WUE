"""Quotation ORM model."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CHAR,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .estimate import Estimate
    from .quotation_item import QuotationItem


class Quotation(Base):
    """Stored quotation costs and totals for an estimate."""

    __tablename__ = "quotations"
    __table_args__ = (
        CheckConstraint("material_total >= 0", name="ck_quotations_material_total"),
        CheckConstraint("labor_cost >= 0", name="ck_quotations_labor_cost"),
        CheckConstraint("logistics_cost >= 0", name="ck_quotations_logistics_cost"),
        CheckConstraint(
            "subtotal_before_profit >= 0",
            name="ck_quotations_subtotal_before_profit",
        ),
        CheckConstraint(
            "profit_percentage BETWEEN 0 AND 100",
            name="ck_quotations_profit_percentage",
        ),
        CheckConstraint("profit_amount >= 0", name="ck_quotations_profit_amount"),
        CheckConstraint("grand_total >= 0", name="ck_quotations_grand_total"),
        CheckConstraint(
            "currency_code ~ '^[A-Z]{3}$'", name="ck_quotations_currency_code"
        ),
        CheckConstraint(
            "status IN ('draft', 'approved', 'rejected', 'completed')",
            name="ck_quotations_status",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= CAST(created_at AS DATE)",
            name="ck_quotations_valid_until",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    quotation_number: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True
    )
    estimate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("estimates.id"), nullable=False
    )
    material_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    labor_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    logistics_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    subtotal_before_profit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    profit_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    profit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    grand_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    currency_code: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, default="PHP", server_default="PHP"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    estimate: Mapped[Estimate] = relationship(back_populates="quotations")
    items: Mapped[list[QuotationItem]] = relationship(back_populates="quotation")
