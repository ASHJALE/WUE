"""Disposable end-to-end validation for Phase 5B-4 quotation generation."""

from __future__ import annotations

import json
import time
from decimal import Decimal
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app.models  # noqa: F401
from sqlalchemy import delete, func, select, update

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


def request(label: str, method: str, path: str, expected: int, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urlopen(req) as response:
            code, text = response.status, response.read().decode()
    except HTTPError as error:
        code, text = error.code, error.read().decode()
    results.append(f"{label}|{method} {path}|HTTP {code}")
    if code != expected:
        raise AssertionError(f"{label}: expected {expected}, received {code}: {text}")
    return json.loads(text)


def dec(value) -> Decimal:
    return Decimal(str(value))


suffix = str(int(time.time() * 1000))
ids: dict[str, list[int]] = {name: [] for name in (
    "quotations", "quotation_items", "estimates", "furniture_materials",
    "inventory", "materials", "furniture_types", "users",
)}
inventory_before: dict[int, Decimal] = {}
success = False

try:
    with get_session_factory()() as db:
        user = User(
            username=f"phase5b4_{suffix}", email=f"phase5b4_{suffix}@example.test",
            password_hash="temporary-validation-hash", full_name="Phase 5B-4 Validation",
        )
        normal = FurnitureType(name=f"Phase5B4 Normal {suffix}")
        empty = FurnitureType(name=f"Phase5B4 Empty {suffix}")
        shortage_type = FurnitureType(name=f"Phase5B4 Shortage {suffix}")
        missing_type = FurnitureType(name=f"Phase5B4 Missing {suffix}")
        db.add_all([user, normal, empty, shortage_type, missing_type]); db.flush()
        ids["users"].append(user.id)
        ids["furniture_types"].extend([normal.id, empty.id, shortage_type.id, missing_type.id])

        alternative = Material(name=f"Phase5B4 Alternative {suffix}", unit="piece", current_unit_price=Decimal("0.10"))
        first = Material(name=f"Phase5B4 First {suffix}", unit="piece", current_unit_price=Decimal("1.00"), alternative_material=alternative)
        second = Material(name=f"Phase5B4 Second {suffix}", unit="meter", current_unit_price=Decimal("3.33"))
        short = Material(name=f"Phase5B4 Short Material {suffix}", unit="sheet", current_unit_price=Decimal("4.00"))
        missing = Material(name=f"Phase5B4 Missing Material {suffix}", unit="sheet", current_unit_price=Decimal("5.00"))
        db.add_all([alternative, first, second, short, missing]); db.flush()
        ids["materials"].extend([alternative.id, first.id, second.id, short.id, missing.id])
        first_id, second_id = first.id, second.id

        inventories = [
            Inventory(material_id=alternative.id, quantity_available=Decimal("100.000"), reorder_level=Decimal("0.000")),
            Inventory(material_id=first.id, quantity_available=Decimal("5.000"), reorder_level=Decimal("1.000")),
            Inventory(material_id=second.id, quantity_available=Decimal("5.000"), reorder_level=Decimal("1.000")),
            Inventory(material_id=short.id, quantity_available=Decimal("0.500"), reorder_level=Decimal("0.000")),
        ]
        db.add_all(inventories); db.flush()
        ids["inventory"].extend(row.id for row in inventories)
        inventory_before = {row.id: row.quantity_available for row in inventories}

        boms = [
            FurnitureMaterial(furniture_type_id=normal.id, material_id=first.id, quantity_required=Decimal("1.000"), wastage_percentage=Decimal("0.50")),
            FurnitureMaterial(furniture_type_id=normal.id, material_id=second.id, quantity_required=Decimal("2.000"), wastage_percentage=Decimal("10.00")),
            FurnitureMaterial(furniture_type_id=shortage_type.id, material_id=short.id, quantity_required=Decimal("1.000"), wastage_percentage=Decimal("0.00")),
            FurnitureMaterial(furniture_type_id=missing_type.id, material_id=missing.id, quantity_required=Decimal("1.000"), wastage_percentage=Decimal("0.00")),
        ]
        db.add_all(boms); db.flush(); ids["furniture_materials"].extend(row.id for row in boms)

        estimates = {
            "success": Estimate(user_id=user.id, selected_furniture_type_id=normal.id, input_method="predefined", status="processed"),
            "draft": Estimate(user_id=user.id, selected_furniture_type_id=normal.id, input_method="predefined", status="draft"),
            "processing": Estimate(user_id=user.id, selected_furniture_type_id=normal.id, input_method="predefined", status="processing"),
            "quoted": Estimate(user_id=user.id, selected_furniture_type_id=normal.id, input_method="predefined", status="quoted"),
            "no_selection": Estimate(user_id=user.id, input_method="predefined", status="draft"),
            "empty": Estimate(user_id=user.id, selected_furniture_type_id=empty.id, input_method="predefined", status="processed"),
            "shortage": Estimate(user_id=user.id, selected_furniture_type_id=shortage_type.id, input_method="predefined", status="processed"),
            "missing": Estimate(user_id=user.id, selected_furniture_type_id=missing_type.id, input_method="predefined", status="processed"),
        }
        db.add_all(estimates.values()); db.commit()
        ids["estimates"].extend(row.id for row in estimates.values())
        estimate_ids = {key: row.id for key, row in estimates.items()}
        user_id = user.id

    payload = {"labor_cost": "2.005", "logistics_cost": "1.005", "profit_margin_percentage": "12.50"}
    quote = request("quotation.create", "POST", f"/estimates/{estimate_ids['success']}/quotation", 201, payload)
    if tuple(map(dec, (quote["material_total"], quote["labor_cost"], quote["logistics_cost"], quote["subtotal_before_profit"], quote["profit_amount"], quote["grand_total"]))) != (
        Decimal("8.34"), Decimal("2.01"), Decimal("1.01"), Decimal("11.36"), Decimal("1.42"), Decimal("12.78")
    ):
        raise AssertionError("Quotation totals or ROUND_HALF_UP behavior are incorrect.")
    if len(quote["items"]) != 2:
        raise AssertionError("Expected one quotation item for each primary BOM row.")
    expected_items = [(first_id, Decimal("1.005"), Decimal("1.00"), Decimal("1.01")), (second_id, Decimal("2.200"), Decimal("3.33"), Decimal("7.33"))]
    actual_items = [(item["material_id"], dec(item["quantity"]), dec(item["unit_price_snapshot"]), dec(item["line_total"])) for item in quote["items"]]
    if actual_items != expected_items or any(item["is_alternative"] for item in quote["items"]):
        raise AssertionError("Primary quotation snapshots or alternative behavior are incorrect.")
    ids["quotations"].append(quote["id"]); ids["quotation_items"].extend(item["id"] for item in quote["items"])

    request("quotation.duplicate", "POST", f"/estimates/{estimate_ids['success']}/quotation", 409, payload)
    request("quotation.missing_estimate", "POST", "/estimates/9223372036854775807/quotation", 404, payload)
    for key in ("draft", "processing", "quoted", "no_selection", "empty", "shortage", "missing"):
        request(f"quotation.reject_{key}", "POST", f"/estimates/{estimate_ids[key]}/quotation", 409, payload)
    for label, bad in (
        ("negative_labor", {**payload, "labor_cost": "-0.01"}),
        ("negative_logistics", {**payload, "logistics_cost": "-0.01"}),
        ("profit_below_zero", {**payload, "profit_margin_percentage": "-0.01"}),
        ("profit_above_hundred", {**payload, "profit_margin_percentage": "100.01"}),
    ):
        request(f"quotation.{label}", "POST", f"/estimates/{estimate_ids['draft']}/quotation", 422, bad)

    listing = request("quotation.list", "GET", f"/quotations?estimate_id={estimate_ids['success']}&user_id={user_id}", 200)
    if len(listing) != 1 or listing[0]["id"] != quote["id"]:
        raise AssertionError("Quotation list filters returned unexpected data.")
    detail = request("quotation.detail", "GET", f"/quotations/{quote['id']}", 200)
    if [item["id"] for item in detail["items"]] != sorted(ids["quotation_items"]):
        raise AssertionError("Quotation detail item ordering is not predictable.")
    request("quotation.missing", "GET", "/quotations/9223372036854775807", 404)

    with get_session_factory()() as db:
        statuses = dict(db.execute(select(Estimate.id, Estimate.status).where(Estimate.id.in_(ids["estimates"]))).all())
        if statuses[estimate_ids["success"]] != "quoted" or any(statuses[estimate_ids[key]] != ("quoted" if key == "quoted" else "draft" if key in {"draft", "no_selection"} else "processing" if key == "processing" else "processed") for key in ("draft", "processing", "quoted", "no_selection", "empty", "shortage", "missing")):
            raise AssertionError("A failed request changed an estimate status.")
        inventory_after = dict(db.execute(select(Inventory.id, Inventory.quantity_available).where(Inventory.id.in_(ids["inventory"]))).all())
        if inventory_after != inventory_before:
            raise AssertionError("Quotation generation changed inventory quantities.")
        failed_quote_count = db.scalar(select(func.count(Quotation.id)).where(Quotation.estimate_id.in_([estimate_ids[key] for key in ("draft", "processing", "quoted", "no_selection", "empty", "shortage", "missing")]))) or 0
        if failed_quote_count:
            raise AssertionError("A failed generation left quotation data.")
    success = True
    print("PHASE5B4_VALIDATION_OK=True")
    print("NO_INVENTORY_QUANTITIES_CHANGED=True")
    print("NO_AUTOMATIC_ALTERNATIVE_SUBSTITUTION=True")
    print("ATOMIC_QUOTATION_CREATION_VERIFIED=True")
finally:
    with get_session_factory()() as db:
        if ids["quotation_items"]: db.execute(delete(QuotationItem).where(QuotationItem.id.in_(ids["quotation_items"])))
        if ids["quotations"]: db.execute(delete(Quotation).where(Quotation.id.in_(ids["quotations"])))
        if ids["estimates"]: db.execute(delete(Estimate).where(Estimate.id.in_(ids["estimates"])))
        if ids["furniture_materials"]: db.execute(delete(FurnitureMaterial).where(FurnitureMaterial.id.in_(ids["furniture_materials"])))
        if ids["inventory"]: db.execute(delete(Inventory).where(Inventory.id.in_(ids["inventory"])))
        if ids["materials"]:
            db.execute(update(Material).where(Material.id.in_(ids["materials"])).values(alternative_material_id=None))
            db.execute(delete(Material).where(Material.id.in_(ids["materials"])))
        if ids["furniture_types"]: db.execute(delete(FurnitureType).where(FurnitureType.id.in_(ids["furniture_types"])))
        if ids["users"]: db.execute(delete(User).where(User.id.in_(ids["users"])))
        db.commit()
        for label, model in (("QUOTATIONS", Quotation), ("QUOTATION_ITEMS", QuotationItem), ("ESTIMATES", Estimate), ("FURNITURE_MATERIALS", FurnitureMaterial), ("INVENTORY", Inventory), ("MATERIALS", Material), ("FURNITURE_TYPES", FurnitureType), ("USERS", User)):
            remaining = db.scalar(select(func.count(model.id)).where(model.id.in_(ids[label.lower()]))) if ids[label.lower()] else 0
            print(f"PHASE5B4_{label}={remaining or 0}")
    print("--- PHASE 5B-4 HTTP RESULTS ---")
    print("\n".join(results))
    if not success:
        print("PHASE5B4_VALIDATION_OK=False")
