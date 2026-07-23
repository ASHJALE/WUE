"""Atomic and idempotent persistence of a completed Phase 7 workflow."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.estimate import Estimate
from app.models.furniture_material import FurnitureMaterial
from app.models.furniture_type import FurnitureType
from app.models.phase7_estimate_snapshot import Phase7EstimateSnapshot
from app.models.user import User
from app.schemas.phase7_integration import (
    IntegratedFurnitureTypeRead,
    Phase7IntegrationRead,
    Phase7IntegrationRequest,
)
from app.services.images import get_owned_upload

FURNITURE_NAMES = {
    "chair": "Chair",
    "bed": "Bed",
    "sofa": "Sofa",
    "dining_table": "Dining Table",
    "lamp_shade": "Lamp Shade",
}


class Phase7IntegrationNotFoundError(Exception):
    pass


class Phase7IntegrationForbiddenError(Exception):
    pass


class Phase7IntegrationValidationError(Exception):
    pass


class Phase7IntegrationPersistenceError(Exception):
    pass


def _resolve_furniture_type(db: Session, furniture_key: str) -> FurnitureType:
    expected_name = FURNITURE_NAMES[furniture_key]
    record = db.scalar(
        select(FurnitureType).where(func.lower(FurnitureType.name) == expected_name.lower())
    )
    if record is None or not record.is_active:
        raise Phase7IntegrationValidationError(
            f"Furniture type '{expected_name}' is not configured as active."
        )
    return record


def integrate_phase7_workflow(
    db: Session,
    estimate_id: int,
    data: Phase7IntegrationRequest,
    current_user: User,
) -> Phase7IntegrationRead:
    try:
        estimate = db.scalar(
            select(Estimate)
            .where(Estimate.id == estimate_id)
            .with_for_update()
        )
        if estimate is None:
            raise Phase7IntegrationNotFoundError("Estimate not found.")
        if estimate.user_id != current_user.id and current_user.role != "admin":
            raise Phase7IntegrationForbiddenError("You cannot integrate another user's estimate.")

        upload = get_owned_upload(data.upload.upload_id, estimate.user_id)
        if upload is None:
            raise Phase7IntegrationValidationError("The uploaded image was not found for this estimate owner.")
        expected_image_path = f"uploads/furniture/{upload.stored_filename}"
        if data.upload.image_path.replace("\\", "/").lstrip("/") != expected_image_path:
            raise Phase7IntegrationValidationError("The image reference does not match the owned upload.")

        selected_type = _resolve_furniture_type(db, data.classification.confirmed_furniture_type)
        recognized_type = _resolve_furniture_type(db, data.classification.recognized_furniture_type)

        estimate.selected_furniture_type_id = selected_type.id
        estimate.recognized_furniture_type_id = recognized_type.id
        estimate.image_path = expected_image_path
        estimate.input_method = "image_upload"
        estimate.recognition_confidence = data.classification.confidence
        if estimate.status != "quoted":
            estimate.status = "processed"

        snapshot = estimate.phase7_snapshot
        if snapshot is None:
            snapshot = Phase7EstimateSnapshot(estimate_id=estimate.id, upload_id=data.upload.upload_id)
            db.add(snapshot)
        snapshot.upload_id = data.upload.upload_id
        snapshot.dimensions_json = data.dimensions.model_dump(mode="json")
        snapshot.recommendations_json = [item.model_dump(mode="json") for item in data.recommendations]
        snapshot.bom_json = [item.model_dump(mode="json") for item in data.bom]
        snapshot.quantities_json = [item.model_dump(mode="json") for item in data.quantity_estimates]
        snapshot.cost_summary_json = data.cost_summary.model_dump(mode="json")
        snapshot.preliminary_quotation_json = data.preliminary_quotation.model_dump(mode="json")

        db.commit()
        db.refresh(estimate)
        bom_available = bool(
            db.scalar(
                select(FurnitureMaterial.id)
                .where(FurnitureMaterial.furniture_type_id == selected_type.id)
                .limit(1)
            )
        )
        return Phase7IntegrationRead(
            estimate_id=estimate.id,
            selected_furniture_type=IntegratedFurnitureTypeRead(id=selected_type.id, name=selected_type.name),
            recognized_furniture_type=IntegratedFurnitureTypeRead(id=recognized_type.id, name=recognized_type.name),
            recognition_confidence=estimate.recognition_confidence,
            image_path=estimate.image_path,
            phase7_snapshot_saved=True,
            bom_preview_available=bom_available,
            updated_at=estimate.updated_at,
        )
    except (
        Phase7IntegrationNotFoundError,
        Phase7IntegrationForbiddenError,
        Phase7IntegrationValidationError,
    ):
        db.rollback()
        raise
    except (IntegrityError, SQLAlchemyError) as error:
        db.rollback()
        raise Phase7IntegrationPersistenceError("Phase 7 integration could not be saved atomically.") from error
