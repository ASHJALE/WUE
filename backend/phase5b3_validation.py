"""Disposable validation for the Phase 5B-3 dynamic BOM preview."""

from __future__ import annotations

import json
import time
from decimal import Decimal
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app.models  # noqa: F401 - register all ORM relationship targets
from sqlalchemy import delete, func, select

from app.database import get_session_factory
from app.models.estimate import Estimate
from app.models.furniture_material import FurnitureMaterial
from app.models.furniture_type import FurnitureType
from app.models.inventory import Inventory
from app.models.material import Material
from app.models.quotation import Quotation
from app.models.quotation_item import QuotationItem
from app.models.user import User

BASE_URL = "http://127.0.0.1:8765"
results: list[str] = []


def request(label: str, path: str, expected: int):
    req = Request(BASE_URL + path, method="GET")
    try:
        with urlopen(req) as response:
            status = response.status
            text = response.read().decode()
    except HTTPError as error:
        status = error.code
        text = error.read().decode()
    results.append(f"{label}|HTTP {status}|{text}")
    if status != expected:
        raise AssertionError(f"{label}: expected {expected}, received {status}")
    return json.loads(text)


def decimal(value) -> Decimal:
    return Decimal(str(value))


suffix = str(int(time.time() * 1000))
estimate_ids: list[int] = []
furniture_material_ids: list[int] = []
inventory_ids: list[int] = []
material_ids: list[int] = []
furniture_type_ids: list[int] = []
user_id = None
quotation_count_before = quotation_item_count_before = 0
inventory_before: dict[int, Decimal] = {}

try:
    with get_session_factory()() as db:
        quotation_count_before = db.scalar(select(func.count(Quotation.id))) or 0
        quotation_item_count_before = (
            db.scalar(select(func.count(QuotationItem.id))) or 0
        )

        user = User(
            username=f"phase5b3_user_{suffix}",
            email=f"phase5b3_{suffix}@example.test",
            password_hash="temporary-validation-hash",
            full_name="Phase 5B-3 Validation User",
        )
        furniture = FurnitureType(name=f"Phase5B3 Furniture {suffix}")
        empty_furniture = FurnitureType(name=f"Phase5B3 Empty Furniture {suffix}")
        db.add_all([user, furniture, empty_furniture])
        db.flush()
        user_id = user.id
        furniture_type_ids.extend([furniture.id, empty_furniture.id])

        enough = Material(
            name=f"Phase5B3 Enough {suffix}",
            unit="piece",
            current_unit_price=Decimal("1.00"),
        )
        shortage = Material(
            name=f"Phase5B3 Shortage {suffix}",
            unit="meter",
            current_unit_price=Decimal("3.33"),
        )
        alternative = Material(
            name=f"Phase5B3 Alternative {suffix}",
            unit="sheet",
            current_unit_price=Decimal("2.50"),
        )
        missing_inventory = Material(
            name=f"Phase5B3 Missing Inventory {suffix}",
            unit="sheet",
            current_unit_price=Decimal("4.00"),
            alternative_material=alternative,
        )
        db.add_all([enough, shortage, alternative, missing_inventory])
        db.flush()
        material_ids.extend(
            [enough.id, shortage.id, alternative.id, missing_inventory.id]
        )

        enough_inventory = Inventory(
            material_id=enough.id,
            quantity_available=Decimal("5.000"),
            reorder_level=Decimal("1.000"),
        )
        shortage_inventory = Inventory(
            material_id=shortage.id,
            quantity_available=Decimal("1.000"),
            reorder_level=Decimal("0.500"),
        )
        alternative_inventory = Inventory(
            material_id=alternative.id,
            quantity_available=Decimal("0.250"),
            reorder_level=Decimal("0.100"),
        )
        db.add_all(
            [enough_inventory, shortage_inventory, alternative_inventory]
        )
        db.flush()
        inventory_ids.extend(
            [
                enough_inventory.id,
                shortage_inventory.id,
                alternative_inventory.id,
            ]
        )
        inventory_before = {
            enough_inventory.id: enough_inventory.quantity_available,
            shortage_inventory.id: shortage_inventory.quantity_available,
            alternative_inventory.id: alternative_inventory.quantity_available,
        }

        bom_rows = [
            FurnitureMaterial(
                furniture_type_id=furniture.id,
                material_id=enough.id,
                quantity_required=Decimal("1.000"),
                wastage_percentage=Decimal("0.50"),
            ),
            FurnitureMaterial(
                furniture_type_id=furniture.id,
                material_id=shortage.id,
                quantity_required=Decimal("2.000"),
                wastage_percentage=Decimal("10.00"),
            ),
            FurnitureMaterial(
                furniture_type_id=furniture.id,
                material_id=missing_inventory.id,
                quantity_required=Decimal("0.500"),
                wastage_percentage=Decimal("0.00"),
            ),
        ]
        db.add_all(bom_rows)
        db.flush()
        furniture_material_ids.extend(row.id for row in bom_rows)

        main_estimate = Estimate(
            user_id=user.id,
            selected_furniture_type_id=furniture.id,
            input_method="predefined",
            status="processed",
        )
        no_selection = Estimate(
            user_id=user.id,
            input_method="predefined",
            status="draft",
        )
        no_bom = Estimate(
            user_id=user.id,
            selected_furniture_type_id=empty_furniture.id,
            input_method="predefined",
            status="draft",
        )
        db.add_all([main_estimate, no_selection, no_bom])
        db.commit()
        estimate_ids.extend([main_estimate.id, no_selection.id, no_bom.id])
        main_estimate_id = main_estimate.id
        no_selection_id = no_selection.id
        no_bom_id = no_bom.id

    preview = request(
        "bom_preview.normal", f"/estimates/{main_estimate_id}/bom-preview", 200
    )
    if preview["item_count"] != 3:
        raise AssertionError("Expected exactly three BOM preview items.")
    if decimal(preview["material_total"]) != Decimal("10.34"):
        raise AssertionError("Material total did not use expected line rounding.")
    if preview["has_inventory_shortage"] is not True:
        raise AssertionError("Expected the preview to report an inventory shortage.")

    by_name = {item["material_name"]: item for item in preview["items"]}
    enough_item = by_name[f"Phase5B3 Enough {suffix}"]
    if decimal(enough_item["wastage_quantity"]) != Decimal("0.005"):
        raise AssertionError("Wastage quantity calculation is incorrect.")
    if decimal(enough_item["required_quantity"]) != Decimal("1.005"):
        raise AssertionError("Required quantity calculation is incorrect.")
    if decimal(enough_item["line_total"]) != Decimal("1.01"):
        raise AssertionError("ROUND_HALF_UP monetary rounding is incorrect.")
    if enough_item["inventory"]["is_available"] is not True:
        raise AssertionError("Enough inventory was not reported as available.")

    shortage_item = by_name[f"Phase5B3 Shortage {suffix}"]
    if decimal(shortage_item["required_quantity"]) != Decimal("2.200"):
        raise AssertionError("Ten-percent wastage calculation is incorrect.")
    if decimal(shortage_item["inventory"]["shortage_quantity"]) != Decimal(
        "1.200"
    ):
        raise AssertionError("Inventory shortage calculation is incorrect.")

    missing_item = by_name[f"Phase5B3 Missing Inventory {suffix}"]
    if missing_item["inventory"]["inventory_id"] is not None:
        raise AssertionError("Missing inventory should return a null inventory ID.")
    if decimal(missing_item["inventory"]["quantity_on_hand"]) != Decimal("0.000"):
        raise AssertionError("Missing inventory should report zero on hand.")
    if decimal(missing_item["inventory"]["shortage_quantity"]) != Decimal("0.500"):
        raise AssertionError("Missing inventory shortage is incorrect.")
    alternative_result = missing_item["direct_alternative"]
    if alternative_result is None:
        raise AssertionError("Expected one direct alternative in the response.")
    if decimal(alternative_result["alternative_shortage_quantity"]) != Decimal(
        "0.250"
    ):
        raise AssertionError("Alternative shortage calculation is incorrect.")
    if decimal(alternative_result["estimated_alternative_line_total"]) != Decimal(
        "1.25"
    ):
        raise AssertionError("Alternative line total is incorrect.")

    request("bom_preview.missing_estimate", "/estimates/9223372036854775807/bom-preview", 404)
    request(
        "bom_preview.no_selected_type",
        f"/estimates/{no_selection_id}/bom-preview",
        409,
    )
    request("bom_preview.no_template", f"/estimates/{no_bom_id}/bom-preview", 409)

    with get_session_factory()() as db:
        quotation_count_after = db.scalar(select(func.count(Quotation.id))) or 0
        quotation_item_count_after = (
            db.scalar(select(func.count(QuotationItem.id))) or 0
        )
        inventory_after = dict(
            db.execute(
                select(Inventory.id, Inventory.quantity_available).where(
                    Inventory.id.in_(inventory_ids)
                )
            ).all()
        )
        status_after = db.scalar(
            select(Estimate.status).where(Estimate.id == main_estimate_id)
        )

    if quotation_count_after != quotation_count_before:
        raise AssertionError("BOM preview changed the quotation count.")
    if quotation_item_count_after != quotation_item_count_before:
        raise AssertionError("BOM preview changed the quotation-item count.")
    if inventory_after != inventory_before:
        raise AssertionError("BOM preview changed inventory quantities.")
    if status_after != "processed":
        raise AssertionError("BOM preview changed the estimate status.")

    print("NO_QUOTATION_RECORDS_CREATED=True")
    print("NO_INVENTORY_QUANTITIES_CHANGED=True")
    print("PHASE5B3_VALIDATION_OK=True")
finally:
    with get_session_factory()() as db:
        if estimate_ids:
            db.execute(delete(Estimate).where(Estimate.id.in_(estimate_ids)))
        if furniture_material_ids:
            db.execute(
                delete(FurnitureMaterial).where(
                    FurnitureMaterial.id.in_(furniture_material_ids)
                )
            )
        if inventory_ids:
            db.execute(delete(Inventory).where(Inventory.id.in_(inventory_ids)))
        if material_ids:
            db.execute(delete(Material).where(Material.id.in_(material_ids)))
        if furniture_type_ids:
            db.execute(
                delete(FurnitureType).where(
                    FurnitureType.id.in_(furniture_type_ids)
                )
            )
        if user_id is not None:
            db.execute(delete(User).where(User.id == user_id))
        db.commit()
    print("--- PHASE 5B-3 RESULTS ---")
    print("\n".join(results))
