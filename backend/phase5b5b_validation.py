"""Disposable end-to-end validation for Phase 5B-5B."""

from __future__ import annotations

import json
import time
from decimal import Decimal
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app.models  # noqa: F401
from sqlalchemy import delete, func, select

from app.database import get_session_factory
from app.models.estimate import Estimate
from app.models.furniture_type import FurnitureType
from app.models.inventory import Inventory
from app.models.material import Material
from app.models.quotation import Quotation
from app.models.quotation_item import QuotationItem
from app.models.user import User

BASE_URL = "http://127.0.0.1:8765"
results: list[str] = []


def request(label: str, method: str, path: str, expected: int):
    req = Request(BASE_URL + path, method=method)
    try:
        with urlopen(req) as response:
            code = response.status
            content_type = response.headers.get_content_type()
            length = response.headers.get("Content-Length")
            content = response.read()
    except HTTPError as error:
        code = error.code
        content_type = error.headers.get_content_type()
        length = error.headers.get("Content-Length")
        content = error.read()
    results.append(f"{label}|{method} {path}|HTTP {code}")
    if code != expected:
        raise AssertionError(
            f"{label}: expected {expected}, received {code}: {content.decode(errors='replace')}"
        )
    if content_type == "application/json":
        return json.loads(content), content_type, length
    return content, content_type, length


suffix = str(int(time.time() * 1000))
ids: dict[str, list[int]] = {
    "users": [], "furniture_types": [], "materials": [], "estimates": [],
    "quotations": [], "quotation_items": [],
}
inventory_before: list[tuple[int, Decimal]] = []
totals_before: dict[int, tuple] = {}
items_before: list[tuple] = []
estimate_statuses_before: dict[int, str] = {}
success = False

try:
    with get_session_factory()() as db:
        inventory_before = list(
            db.execute(select(Inventory.id, Inventory.quantity_available).order_by(Inventory.id)).all()
        )
        user = User(
            username=f"phase5b5b_{suffix}", email=f"phase5b5b_{suffix}@example.test",
            password_hash="temporary-validation-hash", full_name="Phase 5B-5B Customer",
        )
        furniture = FurnitureType(name=f"Phase5B5B Furniture {suffix}")
        material = Material(
            name=f"Phase5B5B Material {suffix}", unit="piece",
            current_unit_price=Decimal("25.00"),
        )
        db.add_all([user, furniture, material]); db.flush()
        ids["users"].append(user.id); ids["furniture_types"].append(furniture.id)
        ids["materials"].append(material.id)

        estimates = [
            Estimate(user_id=user.id, selected_furniture_type_id=furniture.id, input_method="predefined", status="quoted")
            for _ in range(2)
        ]
        db.add_all(estimates); db.flush(); ids["estimates"].extend(row.id for row in estimates)
        quotations = [
            Quotation(
                quotation_number=f"5B5B-{index}-{suffix[-10:]}", estimate_id=estimate.id,
                material_total=Decimal("50.00"), labor_cost=Decimal("10.00"),
                logistics_cost=Decimal("5.00"), subtotal_before_profit=Decimal("65.00"),
                profit_percentage=Decimal("10.00"), profit_amount=Decimal("6.50"),
                grand_total=Decimal("71.50"), status="draft",
            )
            for index, estimate in enumerate(estimates, start=1)
        ]
        db.add_all(quotations); db.flush(); ids["quotations"].extend(row.id for row in quotations)
        items = [
            QuotationItem(
                quotation_id=quotation.id, material_id=material.id,
                material_name_snapshot=material.name, unit_snapshot=material.unit,
                quantity=Decimal("2.000"), unit_price_snapshot=Decimal("25.00"),
                line_total=Decimal("50.00"), is_alternative=False,
            )
            for quotation in quotations
        ]
        db.add_all(items); db.commit(); ids["quotation_items"].extend(row.id for row in items)
        flow_id, reject_id = (row.id for row in quotations)
        totals_before = {
            row.id: (
                row.material_total, row.labor_cost, row.logistics_cost,
                row.subtotal_before_profit, row.profit_percentage,
                row.profit_amount, row.grand_total,
            )
            for row in quotations
        }
        items_before = list(
            db.execute(
                select(
                    QuotationItem.id, QuotationItem.quotation_id,
                    QuotationItem.material_id, QuotationItem.quantity,
                    QuotationItem.unit_price_snapshot, QuotationItem.line_total,
                    QuotationItem.is_alternative,
                ).where(QuotationItem.id.in_(ids["quotation_items"])).order_by(QuotationItem.id)
            ).all()
        )
        estimate_statuses_before = dict(
            db.execute(select(Estimate.id, Estimate.status).where(Estimate.id.in_(ids["estimates"]))).all()
        )

    approved, _, _ = request("workflow.approve", "POST", f"/quotations/{flow_id}/approve", 200)
    if approved["status"] != "approved": raise AssertionError("Approval did not return approved status.")
    request("workflow.approved_reject", "POST", f"/quotations/{flow_id}/reject", 400)
    request("workflow.duplicate_approve", "POST", f"/quotations/{flow_id}/approve", 400)
    completed, _, _ = request("workflow.complete", "POST", f"/quotations/{flow_id}/complete", 200)
    if completed["status"] != "completed": raise AssertionError("Completion did not return completed status.")
    request("workflow.duplicate_complete", "POST", f"/quotations/{flow_id}/complete", 400)
    request("workflow.completed_approve", "POST", f"/quotations/{flow_id}/approve", 400)
    request("workflow.completed_reject", "POST", f"/quotations/{flow_id}/reject", 400)

    rejected, _, _ = request("workflow.reject", "POST", f"/quotations/{reject_id}/reject", 200)
    if rejected["status"] != "rejected": raise AssertionError("Rejection did not return rejected status.")
    request("workflow.rejected_approve", "POST", f"/quotations/{reject_id}/approve", 400)
    request("workflow.rejected_complete", "POST", f"/quotations/{reject_id}/complete", 400)
    request("workflow.duplicate_reject", "POST", f"/quotations/{reject_id}/reject", 400)
    request("workflow.missing_approve", "POST", "/quotations/9223372036854775807/approve", 404)
    request("workflow.missing_reject", "POST", "/quotations/9223372036854775807/reject", 404)
    request("workflow.missing_complete", "POST", "/quotations/9223372036854775807/complete", 404)

    pdf, content_type, content_length = request("pdf.export", "GET", f"/quotations/{flow_id}/pdf", 200)
    if content_type != "application/pdf": raise AssertionError("PDF content type is incorrect.")
    if not pdf.startswith(b"%PDF") or len(pdf) == 0:
        raise AssertionError("PDF signature or body is invalid.")
    if content_length is not None and int(content_length) <= 0:
        raise AssertionError("PDF Content-Length is not positive.")
    request("pdf.missing", "GET", "/quotations/9223372036854775807/pdf", 404)

    with get_session_factory()() as db:
        inventory_after = list(
            db.execute(select(Inventory.id, Inventory.quantity_available).order_by(Inventory.id)).all()
        )
        statuses_after = dict(
            db.execute(select(Estimate.id, Estimate.status).where(Estimate.id.in_(ids["estimates"]))).all()
        )
        totals_after = {
            row.id: (
                row.material_total, row.labor_cost, row.logistics_cost,
                row.subtotal_before_profit, row.profit_percentage,
                row.profit_amount, row.grand_total,
            )
            for row in db.scalars(select(Quotation).where(Quotation.id.in_(ids["quotations"])))
        }
        items_after = list(
            db.execute(
                select(
                    QuotationItem.id, QuotationItem.quotation_id,
                    QuotationItem.material_id, QuotationItem.quantity,
                    QuotationItem.unit_price_snapshot, QuotationItem.line_total,
                    QuotationItem.is_alternative,
                ).where(QuotationItem.id.in_(ids["quotation_items"])).order_by(QuotationItem.id)
            ).all()
        )
    if inventory_after != inventory_before: raise AssertionError("Inventory changed.")
    if statuses_after != estimate_statuses_before: raise AssertionError("Estimate status changed.")
    if totals_after != totals_before: raise AssertionError("Quotation totals changed.")
    if items_after != items_before: raise AssertionError("Quotation items changed.")
    success = True
    print("PDF_SIGNATURE_OK=True")
    print("WORKFLOW_VALIDATION_OK=True")
    print("PDF_VALIDATION_OK=True")
    print("NO_INVENTORY_CHANGES=True")
    print("NO_ESTIMATE_STATUS_CHANGES=True")
finally:
    with get_session_factory()() as db:
        if ids["quotation_items"]: db.execute(delete(QuotationItem).where(QuotationItem.id.in_(ids["quotation_items"])))
        if ids["quotations"]: db.execute(delete(Quotation).where(Quotation.id.in_(ids["quotations"])))
        if ids["estimates"]: db.execute(delete(Estimate).where(Estimate.id.in_(ids["estimates"])))
        if ids["materials"]: db.execute(delete(Material).where(Material.id.in_(ids["materials"])))
        if ids["furniture_types"]: db.execute(delete(FurnitureType).where(FurnitureType.id.in_(ids["furniture_types"])))
        if ids["users"]: db.execute(delete(User).where(User.id.in_(ids["users"])))
        db.commit()
        for label, model in (("USERS", User), ("ESTIMATES", Estimate), ("QUOTATIONS", Quotation), ("QUOTATION_ITEMS", QuotationItem)):
            values = ids[label.lower()]
            count = db.scalar(select(func.count(model.id)).where(model.id.in_(values))) if values else 0
            print(f"PHASE5B5B_{label}={count or 0}")
    print("--- PHASE 5B-5B HTTP RESULTS ---")
    print("\n".join(results))
    print(f"PHASE5B5B_VALIDATION_OK={success}")
