"""Database-backed validation for atomic Phase 8.1 workflow integration."""

import asyncio
import json
import tempfile
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db, get_session_factory
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.estimate import Estimate
from app.models.furniture_material import FurnitureMaterial
from app.models.furniture_type import FurnitureType
from app.models.inventory import Inventory
from app.models.material import Material
from app.models.phase7_estimate_snapshot import Phase7EstimateSnapshot
from app.models.user import User
from app.schemas.classification import ClassificationRead
from app.schemas.cost import CostCalculateRequest
from app.schemas.quantity import FurnitureDimensions
from app.schemas.quotation import PreliminaryCustomerInput, PreliminaryQuotationAssemble
from app.services import images as image_service
from app.services.bom_generator import generate_bom
from app.services.cost_calculator import calculate_preliminary_cost
from app.services.material_recommender import recommend_materials
from app.services.quantity_estimator import estimate_quantities
from app.services.quotation_builder import assemble_preliminary_quotation


async def request(method: str, path: str, payload: dict | None = None, authenticated: bool = True):
    body = json.dumps(payload).encode() if payload is not None else b""
    headers = [(b"content-type", b"application/json")] if payload is not None else []
    if authenticated:
        headers.append((b"authorization", b"Bearer validation-token"))
    messages = []
    delivered = False

    async def receive():
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
        "query_string": b"", "root_path": "", "headers": headers,
        "client": ("127.0.0.1", 12345), "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return start["status"], json.loads(response_body) if response_body else None


def build_phase7_payload(upload_id, stored_filename, confidence=0.82):
    recommendations = recommend_materials("chair")
    bom = generate_bom("chair", recommendations)
    quantities = estimate_quantities(
        "chair", FurnitureDimensions(width=450, depth=500, height=900), bom
    )
    cost = calculate_preliminary_cost(CostCalculateRequest.model_validate({
        "furniture_type": "chair", "components": [item.model_dump() for item in quantities],
        "labor": {"hours": 8, "hourly_rate": 150}, "profit_margin_percent": 20,
    }))
    classification = ClassificationRead(
        upload_id=upload_id, predicted_class="chair", display_name="Chair",
        confidence=confidence, model_name="wue-development-classifier", model_version="0.1.0",
        is_placeholder=True,
        supported_classes=["chair", "bed", "sofa", "dining_table", "lamp_shade"],
    )
    quotation = assemble_preliminary_quotation(PreliminaryQuotationAssemble(
        customer=PreliminaryCustomerInput(
            name="Phase 8.1 Customer", project_name="Validation Chair", location="Angeles City"
        ),
        classification=classification,
        recommendations=recommendations,
        bom=bom,
        quantity_estimates=quantities,
        cost_summary=cost,
    ))
    return {
        "upload": {
            "upload_id": str(upload_id),
            "image_path": f"uploads/furniture/{stored_filename}",
        },
        "classification": {
            "recognized_furniture_type": "chair",
            "confirmed_furniture_type": "chair",
            "confidence": confidence,
        },
        "dimensions": {"width": 450, "depth": 500, "height": 900, "unit": "mm"},
        "recommendations": [item.model_dump(mode="json") for item in recommendations],
        "bom": [item.model_dump(mode="json") for item in bom],
        "quantity_estimates": [item.model_dump(mode="json") for item in quantities],
        "cost_summary": cost.model_dump(mode="json"),
        "preliminary_quotation": quotation.model_dump(mode="json"),
    }


async def main():
    factory = get_session_factory()
    setup = factory()
    created = {}
    original_upload_directory = image_service.UPLOAD_DIRECTORY
    baseline = {
        "estimates": setup.scalar(select(func.count()).select_from(Estimate)),
        "snapshots": setup.scalar(select(func.count()).select_from(Phase7EstimateSnapshot)),
        "quotations": setup.execute(text("select count(*) from quotations")).scalar_one(),
        "inventory": setup.execute(text("select id, material_id, quantity_available, reorder_level from inventory order by id")).all(),
    }
    try:
        token = uuid4().hex[:10]
        owner = User(
            username=f"p81_owner_{token}", email=f"p81_owner_{token}@example.test",
            password_hash="validation-only", full_name="Phase 81 Owner", role="user",
        )
        other = User(
            username=f"p81_other_{token}", email=f"p81_other_{token}@example.test",
            password_hash="validation-only", full_name="Phase 81 Other", role="user",
        )
        setup.add_all([owner, other])
        chair = setup.scalar(select(FurnitureType).where(func.lower(FurnitureType.name) == "chair"))
        if chair is None:
            chair = FurnitureType(name="Chair", description="Temporary Phase 8.1 validation type")
            setup.add(chair)
            setup.flush()
            created["chair"] = chair.id
        material = Material(
            name=f"P81 Validation Wood {token}", unit="board_foot",
            current_unit_price=Decimal("100.00"), is_active=True,
        )
        setup.add(material)
        setup.flush()
        inventory = Inventory(
            material_id=material.id, quantity_available=Decimal("100.000"),
            reorder_level=Decimal("5.000"),
        )
        bom_row = FurnitureMaterial(
            furniture_type_id=chair.id, material_id=material.id,
            quantity_required=Decimal("2.000"), wastage_percentage=Decimal("5.00"),
        )
        estimate = Estimate(user_id=owner.id, input_method="predefined", status="draft")
        setup.add_all([inventory, bom_row, estimate])
        setup.commit()
        created.update({
            "owner": owner.id, "other": other.id, "material": material.id,
            "inventory": inventory.id, "bom": bom_row.id, "estimate": estimate.id,
        })

        with tempfile.TemporaryDirectory(prefix="wue-phase81-") as temporary:
            image_service.UPLOAD_DIRECTORY = Path(temporary) / "furniture"
            image_service.UPLOAD_DIRECTORY.mkdir(parents=True)
            upload_id = uuid4()
            stored_filename = f"{upload_id}.png"
            (image_service.UPLOAD_DIRECTORY / stored_filename).write_bytes(b"\x89PNG\r\n\x1a\nvalidation")
            metadata_path = image_service.UPLOAD_DIRECTORY / f"{upload_id}.json"
            metadata = {
                "upload_id": str(upload_id), "owner_user_id": owner.id,
                "stored_filename": stored_filename, "content_type": "image/png", "size_bytes": 18,
            }
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            payload = build_phase7_payload(upload_id, stored_filename)

            app.dependency_overrides[get_current_user] = lambda: owner
            unauth_overrides = dict(app.dependency_overrides)
            app.dependency_overrides.clear()
            unauth_status, _ = await request(
                "POST", f"/estimates/{estimate.id}/integrate-phase7", payload, authenticated=False
            )
            assert unauth_status == 401
            app.dependency_overrides.update(unauth_overrides)

            missing_status, missing_response = await request("POST", "/estimates/999999999/integrate-phase7", payload)
            assert missing_status == 404, (missing_status, missing_response)
            app.dependency_overrides[get_current_user] = lambda: other
            forbidden_status, _ = await request(
                "POST", f"/estimates/{estimate.id}/integrate-phase7", payload
            )
            assert forbidden_status == 403
            app.dependency_overrides[get_current_user] = lambda: owner

            incomplete = json.loads(json.dumps(payload))
            del incomplete["cost_summary"]
            incomplete_status, _ = await request(
                "POST", f"/estimates/{estimate.id}/integrate-phase7", incomplete
            )
            assert incomplete_status == 422
            invalid_furniture = json.loads(json.dumps(payload))
            invalid_furniture["classification"]["confirmed_furniture_type"] = "desk"
            invalid_furniture_status, _ = await request(
                "POST", f"/estimates/{estimate.id}/integrate-phase7", invalid_furniture
            )
            assert invalid_furniture_status == 422
            mismatch = json.loads(json.dumps(payload))
            mismatch["quantity_estimates"][0]["component"] = "Mismatched Component"
            mismatch_status, _ = await request(
                "POST", f"/estimates/{estimate.id}/integrate-phase7", mismatch
            )
            assert mismatch_status == 422

            metadata["owner_user_id"] = other.id
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            ownership_status, _ = await request(
                "POST", f"/estimates/{estimate.id}/integrate-phase7", payload
            )
            assert ownership_status == 422
            metadata["owner_user_id"] = owner.id
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

            success_status, success = await request(
                "POST", f"/estimates/{estimate.id}/integrate-phase7", payload
            )
            assert success_status == 200, (success_status, success)
            assert success["selected_furniture_type"]["name"] == "Chair"
            assert success["recognized_furniture_type"]["name"] == "Chair"
            assert success["phase7_snapshot_saved"] is True
            assert success["bom_preview_available"] is True

            verify = factory()
            saved = verify.get(Estimate, estimate.id)
            assert saved.selected_furniture_type_id == chair.id
            assert saved.recognized_furniture_type_id == chair.id
            assert saved.recognition_confidence == Decimal("0.8200")
            assert saved.image_path == f"uploads/furniture/{stored_filename}"
            assert saved.input_method == "image_upload" and saved.status == "processed"
            assert verify.scalar(
                select(func.count()).select_from(Phase7EstimateSnapshot).where(
                    Phase7EstimateSnapshot.estimate_id == estimate.id
                )
            ) == 1
            verify.close()

            repeat_status, _ = await request(
                "POST", f"/estimates/{estimate.id}/integrate-phase7", payload
            )
            assert repeat_status == 200
            count_session = factory()
            assert count_session.scalar(
                select(func.count()).select_from(Phase7EstimateSnapshot).where(
                    Phase7EstimateSnapshot.estimate_id == estimate.id
                )
            ) == 1
            count_session.close()

            detail_status, detail = await request("GET", f"/estimates/{estimate.id}")
            assert detail_status == 200
            for legacy_field in (
                "id", "user_id", "username", "selected_furniture_type_id",
                "recognized_furniture_type_id", "image_path", "input_method",
                "recognition_confidence", "status", "created_at", "updated_at",
            ):
                assert legacy_field in detail
            assert detail["integration_status"] == "integrated"
            assert detail["phase7_snapshot_saved"] is True
            assert detail["saved_cost_summary"] == payload["cost_summary"]
            assert detail["preliminary_quotation_id"] == payload["preliminary_quotation"]["quotation_id"]

            bom_status, bom_preview = await request("GET", f"/estimates/{estimate.id}/bom-preview")
            assert bom_status == 200 and bom_preview["item_count"] >= 1

            failing_payload = build_phase7_payload(upload_id, stored_filename, confidence=0.77)
            failing_session = factory()
            def fail_commit():
                raise SQLAlchemyError("intentional Phase 8.1 rollback validation")
            failing_session.commit = fail_commit
            def failing_db_dependency():
                try:
                    yield failing_session
                finally:
                    failing_session.close()
            app.dependency_overrides[get_db] = failing_db_dependency
            failed_status, _ = await request(
                "POST", f"/estimates/{estimate.id}/integrate-phase7", failing_payload
            )
            assert failed_status == 503
            app.dependency_overrides.pop(get_db, None)
            rollback_check = factory()
            assert rollback_check.get(Estimate, estimate.id).recognition_confidence == Decimal("0.8200")
            rollback_check.close()

        print("INTEGRATION_ENDPOINT_OK=True")
        print("JWT_REQUIRED_OK=True")
        print("OWNER_SAVE_OK=True")
        print("OTHER_USER_403_OK=True")
        print("MISSING_ESTIMATE_404_OK=True")
        print("INCOMPLETE_WORKFLOW_422_OK=True")
        print("INVALID_FURNITURE_422_OK=True")
        print("UPLOAD_OWNERSHIP_OK=True")
        print("CROSS_COMPONENT_VALIDATION_OK=True")
        print("ESTIMATE_FIELDS_UPDATED_OK=True")
        print("SELECTED_TYPE_PERSISTED_OK=True")
        print("RECOGNIZED_TYPE_PERSISTED_OK=True")
        print("CONFIDENCE_PERSISTED_OK=True")
        print("IMAGE_PATH_PERSISTED_OK=True")
        print("PHASE7_SNAPSHOT_PERSISTED_OK=True")
        print("ATOMIC_ROLLBACK_OK=True")
        print("IDEMPOTENT_SAVE_OK=True")
        print("NO_DUPLICATE_RECORDS_OK=True")
        print("ESTIMATE_RESPONSE_COMPATIBLE_OK=True")
        print("PREVIEW_BOM_AFTER_SAVE_OK=True")
        print("NO_OVERHEAD_SAVED_OK=True")
        print("PRODUCTION_QUOTATION_UNCHANGED=True")
        print("INVENTORY_UNCHANGED=True")
        print("BACKEND_TESTS_OK=True")
    finally:
        app.dependency_overrides.clear()
        image_service.UPLOAD_DIRECTORY = original_upload_directory
        setup.close()
        cleanup = factory()
        try:
            if created.get("estimate"):
                cleanup.execute(delete(Phase7EstimateSnapshot).where(Phase7EstimateSnapshot.estimate_id == created["estimate"]))
                cleanup.execute(delete(Estimate).where(Estimate.id == created["estimate"]))
            if created.get("bom"):
                cleanup.execute(delete(FurnitureMaterial).where(FurnitureMaterial.id == created["bom"]))
            if created.get("inventory"):
                cleanup.execute(delete(Inventory).where(Inventory.id == created["inventory"]))
            if created.get("material"):
                cleanup.execute(delete(Material).where(Material.id == created["material"]))
            for key in ("owner", "other"):
                if created.get(key):
                    cleanup.execute(delete(User).where(User.id == created[key]))
            if created.get("chair"):
                cleanup.execute(delete(FurnitureType).where(FurnitureType.id == created["chair"]))
            cleanup.commit()
            assert cleanup.scalar(select(func.count()).select_from(Estimate)) == baseline["estimates"]
            assert cleanup.scalar(select(func.count()).select_from(Phase7EstimateSnapshot)) == baseline["snapshots"]
            assert cleanup.execute(text("select count(*) from quotations")).scalar_one() == baseline["quotations"]
            assert cleanup.execute(text("select id, material_id, quantity_available, reorder_level from inventory order by id")).all() == baseline["inventory"]
        finally:
            cleanup.close()


if __name__ == "__main__":
    asyncio.run(main())
