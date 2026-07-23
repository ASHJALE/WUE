"""Non-persistent Phase 7 preliminary quotation assembly."""

from datetime import datetime, timezone
from itertools import count
from threading import Lock

from app.schemas.quotation import (
    PreliminaryCustomerRead,
    PreliminaryFurnitureRead,
    PreliminaryProjectRead,
    PreliminaryQuotationAssemble,
    PreliminaryQuotationRead,
)

ASSUMPTIONS = [
    "Preliminary AI-generated estimate",
    "Prices are configurable",
    "Labor estimate may vary",
    "No overhead included",
    "Final quotation subject to review",
]
DISCLAIMER = "This quotation preview is generated for estimation purposes only."
_temporary_sequence = count(1)
_sequence_lock = Lock()


def _temporary_quotation_id(generated_at: datetime) -> str:
    with _sequence_lock:
        sequence = next(_temporary_sequence)
    return f"TMP-{generated_at:%Y%m%d}-{sequence % 10000:04d}"


def assemble_preliminary_quotation(
    data: PreliminaryQuotationAssemble,
) -> PreliminaryQuotationRead:
    generated_at = datetime.now(timezone.utc)
    classification = data.classification
    return PreliminaryQuotationRead(
        quotation_id=_temporary_quotation_id(generated_at),
        generated_at=generated_at,
        customer=PreliminaryCustomerRead(
            name=data.customer.name,
            location=data.customer.location,
        ),
        project=PreliminaryProjectRead(name=data.customer.project_name),
        furniture=PreliminaryFurnitureRead(
            furniture_type=classification.predicted_class,
            display_name=classification.display_name,
            confidence=classification.confidence,
            model_name=classification.model_name,
            model_version=classification.model_version,
            is_placeholder=classification.is_placeholder,
        ),
        recommendations=data.recommendations,
        bom=data.bom,
        quantity_estimates=data.quantity_estimates,
        cost_summary=data.cost_summary,
        assumptions=list(ASSUMPTIONS),
        disclaimer=DISCLAIMER,
    )
