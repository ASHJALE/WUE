"""One-time validation for the Phase 5B-5A quotation-status migration."""

from __future__ import annotations

import subprocess
import sys
import time
from decimal import Decimal

import app.models  # noqa: F401 - register all mapper targets
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import configure_mappers

from app.database import get_engine, get_session_factory
from app.main import app
from app.models.estimate import Estimate
from app.models.furniture_type import FurnitureType
from app.models.material import Material
from app.models.quotation import Quotation
from app.models.quotation_item import QuotationItem
from app.models.user import User

OLD_REVISION = "b8f4d1daabca"
NEW_REVISION = "c3e5f7a9b1d2"
ALLOWED = ("draft", "approved", "rejected", "completed")
REJECTED = ("issued", "accepted", "expired", "not-a-valid-status")


def run_alembic(*arguments: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + result.stderr).strip()
    print(f"ALEMBIC_{arguments[0].upper()}={output}")
    return output


def structure_fingerprint() -> dict:
    """Capture public structure, excluding only the changing status check."""
    inspector = inspect(get_engine())
    result = {}
    for table in sorted(inspector.get_table_names(schema="public")):
        checks = [
            value
            for value in inspector.get_check_constraints(table, schema="public")
            if not (table == "quotations" and value.get("name") == "ck_quotations_status")
        ]
        result[table] = {
            "columns": inspector.get_columns(table, schema="public"),
            "foreign_keys": inspector.get_foreign_keys(table, schema="public"),
            "indexes": inspector.get_indexes(table, schema="public"),
            "unique_constraints": inspector.get_unique_constraints(table, schema="public"),
            "primary_key": inspector.get_pk_constraint(table, schema="public"),
            "checks": checks,
        }
    return repr(result)


suffix = str(int(time.time() * 1000))
captured: dict[str, list[int]] = {
    "users": [], "furniture_types": [], "materials": [], "estimates": [],
    "quotations": [], "quotation_items": [],
}
pre_quotation_count = pre_item_count = 0
post_quotation_count = post_item_count = 0
converted_count = 0
success = False

try:
    current_before = run_alembic("current")
    if OLD_REVISION not in current_before or NEW_REVISION in current_before:
        raise AssertionError(
            "This one-time validator requires the database at the pre-migration revision."
        )

    with get_session_factory()() as db:
        user = User(
            username=f"phase5b5a_{suffix}",
            email=f"phase5b5a_{suffix}@example.test",
            password_hash="temporary-validation-hash",
            full_name="Phase 5B-5A Validation",
        )
        furniture = FurnitureType(name=f"Phase5B5A Furniture {suffix}")
        material = Material(
            name=f"Phase5B5A Material {suffix}", unit="piece",
            current_unit_price=Decimal("10.00"),
        )
        db.add_all([user, furniture, material]); db.flush()
        captured["users"].append(user.id)
        captured["furniture_types"].append(furniture.id)
        captured["materials"].append(material.id)

        estimate = Estimate(
            user_id=user.id, selected_furniture_type_id=furniture.id,
            input_method="predefined", status="quoted",
        )
        db.add(estimate); db.flush(); captured["estimates"].append(estimate.id)
        quotation = Quotation(
            quotation_number=f"5B5A-{suffix[-12:]}", estimate_id=estimate.id,
            material_total=Decimal("10.00"), subtotal_before_profit=Decimal("10.00"),
            grand_total=Decimal("10.00"), status="accepted",
        )
        db.add(quotation); db.flush(); captured["quotations"].append(quotation.id)
        item = QuotationItem(
            quotation_id=quotation.id, material_id=material.id,
            material_name_snapshot=material.name, unit_snapshot=material.unit,
            quantity=Decimal("1.000"), unit_price_snapshot=Decimal("10.00"),
            line_total=Decimal("10.00"), is_alternative=False,
        )
        db.add(item); db.commit(); captured["quotation_items"].append(item.id)

        pre_quotation_count = db.scalar(select(func.count(Quotation.id))) or 0
        pre_item_count = db.scalar(select(func.count(QuotationItem.id))) or 0
        accepted_before = db.scalar(
            select(func.count(Quotation.id)).where(Quotation.status == "accepted")
        ) or 0

    structure_before = structure_fingerprint()
    run_alembic("upgrade", "head")
    current_after = run_alembic("current")
    if NEW_REVISION not in current_after:
        raise AssertionError("Alembic did not reach the Phase 5B-5A revision.")

    structure_after = structure_fingerprint()
    if structure_after != structure_before:
        raise AssertionError("A public table structure changed outside the status check.")

    with get_session_factory()() as db:
        converted_count = db.scalar(
            select(func.count(Quotation.id)).where(
                Quotation.id.in_(captured["quotations"]), Quotation.status == "approved"
            )
        ) or 0
        if converted_count != 1 or accepted_before < 1:
            raise AssertionError("The captured accepted quotation was not converted.")

        quotation_id = captured["quotations"][0]
        for value in ALLOWED:
            db.execute(
                text("UPDATE quotations SET status = :status WHERE id = :id"),
                {"status": value, "id": quotation_id},
            )
            db.commit()
            stored = db.scalar(select(Quotation.status).where(Quotation.id == quotation_id))
            if stored != value:
                raise AssertionError(f"New constraint did not accept {value}.")
            print(f"STATUS_ACCEPTED_{value.upper()}=True")

        for value in REJECTED:
            try:
                db.execute(
                    text("UPDATE quotations SET status = :status WHERE id = :id"),
                    {"status": value, "id": quotation_id},
                )
                db.commit()
            except IntegrityError:
                db.rollback()
                print(f"STATUS_REJECTED_{value.upper().replace('-', '_')}=True")
            else:
                raise AssertionError(f"New constraint unexpectedly accepted {value}.")

        post_quotation_count = db.scalar(select(func.count(Quotation.id))) or 0
        post_item_count = db.scalar(select(func.count(QuotationItem.id))) or 0
        if post_quotation_count != pre_quotation_count:
            raise AssertionError("Quotation row count changed during migration.")
        if post_item_count != pre_item_count:
            raise AssertionError("Quotation-item row count changed during migration.")

    configure_mappers()
    openapi = app.openapi()
    if not openapi.get("paths"):
        raise AssertionError("Application OpenAPI generation failed.")
    run_alembic("check")
    print("MODEL_IMPORTS_OK=True")
    print("CONFIGURE_MAPPERS_OK=True")
    print("APPLICATION_STARTUP_IMPORT_OK=True")
    print(f"OPENAPI_PATH_COUNT={len(openapi['paths'])}")
    print(f"QUOTATION_ROWS_BEFORE={pre_quotation_count}")
    print(f"QUOTATION_ROWS_AFTER={post_quotation_count}")
    print(f"QUOTATION_ITEM_ROWS_BEFORE={pre_item_count}")
    print(f"QUOTATION_ITEM_ROWS_AFTER={post_item_count}")
    print(f"ACCEPTED_ROWS_CONVERTED={converted_count}")
    success = True
finally:
    with get_session_factory()() as db:
        if captured["quotation_items"]:
            db.execute(delete(QuotationItem).where(QuotationItem.id.in_(captured["quotation_items"])))
        if captured["quotations"]:
            db.execute(delete(Quotation).where(Quotation.id.in_(captured["quotations"])))
        if captured["estimates"]:
            db.execute(delete(Estimate).where(Estimate.id.in_(captured["estimates"])))
        if captured["materials"]:
            db.execute(delete(Material).where(Material.id.in_(captured["materials"])))
        if captured["furniture_types"]:
            db.execute(delete(FurnitureType).where(FurnitureType.id.in_(captured["furniture_types"])))
        if captured["users"]:
            db.execute(delete(User).where(User.id.in_(captured["users"])))
        db.commit()
        for label, model in (
            ("USERS", User), ("ESTIMATES", Estimate), ("QUOTATIONS", Quotation),
            ("QUOTATION_ITEMS", QuotationItem),
        ):
            values = captured[label.lower()]
            count = db.scalar(select(func.count(model.id)).where(model.id.in_(values))) if values else 0
            print(f"PHASE5B5A_{label}={count or 0}")
    print(f"PHASE5B5A_VALIDATION_OK={success}")
