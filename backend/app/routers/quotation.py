"""Authenticated non-persistent Phase 7 quotation preview endpoint."""

from fastapi import APIRouter

from app.dependencies.auth import CurrentUser
from app.schemas.quotation import PreliminaryQuotationAssemble, PreliminaryQuotationRead
from app.services.quotation_builder import assemble_preliminary_quotation

router = APIRouter(prefix="/quotation", tags=["Preliminary Quotation"])


@router.post("/assemble", response_model=PreliminaryQuotationRead)
def assemble_quotation_preview(
    data: PreliminaryQuotationAssemble,
    _current_user: CurrentUser,
) -> PreliminaryQuotationRead:
    return assemble_preliminary_quotation(data)
