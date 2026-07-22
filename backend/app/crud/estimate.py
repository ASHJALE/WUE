"""Estimate database operations and status workflow."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.crud import ConflictError
from app.models.estimate import Estimate
from app.models.furniture_type import FurnitureType
from app.models.user import User
from app.schemas.estimate import EstimateCreate, EstimateUpdate

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"draft", "processing", "processed"},
    "processing": {"processing", "processed"},
    "processed": {"processed", "quoted"},
    "quoted": {"quoted"},
}


def _validate_references(
    db: Session,
    user_id: int,
    selected_furniture_type_id: int | None,
    recognized_furniture_type_id: int | None,
) -> None:
    if db.get(User, user_id) is None:
        raise ConflictError("The referenced user does not exist.")
    if (
        selected_furniture_type_id is not None
        and db.get(FurnitureType, selected_furniture_type_id) is None
    ):
        raise ConflictError("The selected furniture type does not exist.")
    if (
        recognized_furniture_type_id is not None
        and db.get(FurnitureType, recognized_furniture_type_id) is None
    ):
        raise ConflictError("The recognized furniture type does not exist.")


def _validate_effective_state(
    *,
    selected_furniture_type_id: int | None,
    recognized_furniture_type_id: int | None,
    recognition_confidence,
    image_path: str | None,
    input_method: str,
    status: str,
) -> None:
    if (recognized_furniture_type_id is None) != (recognition_confidence is None):
        raise ConflictError(
            "Recognized furniture type and confidence must be supplied together."
        )
    if input_method == "image_upload" and not (image_path and image_path.strip()):
        raise ConflictError("Image upload requires a nonblank image path.")
    if status in {"processed", "quoted"} and selected_furniture_type_id is None:
        raise ConflictError(
            "Processed or quoted estimates require a selected furniture type."
        )


def _query():
    return select(Estimate).options(
        joinedload(Estimate.user),
        joinedload(Estimate.selected_furniture_type),
        joinedload(Estimate.recognized_furniture_type),
    )


def create(db: Session, data: EstimateCreate) -> Estimate:
    _validate_references(
        db,
        data.user_id,
        data.selected_furniture_type_id,
        data.recognized_furniture_type_id,
    )
    record = Estimate(**data.model_dump(), status="draft")
    db.add(record)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("The estimate conflicts with existing data.") from error
    db.refresh(record)
    return get(db, record.id)  # type: ignore[return-value]


def list_all(
    db: Session,
    skip: int,
    limit: int,
    user_id: int | None = None,
    status: str | None = None,
) -> list[Estimate]:
    statement = _query().order_by(Estimate.id)
    if user_id is not None:
        statement = statement.where(Estimate.user_id == user_id)
    if status is not None:
        statement = statement.where(Estimate.status == status)
    return list(db.scalars(statement.offset(skip).limit(limit)))


def get(db: Session, estimate_id: int) -> Estimate | None:
    return db.scalar(_query().where(Estimate.id == estimate_id))


def update(db: Session, record: Estimate, data: EstimateUpdate) -> Estimate:
    changes = data.model_dump(exclude_unset=True)
    effective = {
        "user_id": changes.get("user_id", record.user_id),
        "selected_furniture_type_id": changes.get(
            "selected_furniture_type_id", record.selected_furniture_type_id
        ),
        "recognized_furniture_type_id": changes.get(
            "recognized_furniture_type_id", record.recognized_furniture_type_id
        ),
        "recognition_confidence": changes.get(
            "recognition_confidence", record.recognition_confidence
        ),
        "image_path": changes.get("image_path", record.image_path),
        "input_method": changes.get("input_method", record.input_method),
        "status": changes.get("status", record.status),
    }
    if effective["image_path"] is not None:
        effective["image_path"] = effective["image_path"].strip() or None
        if "image_path" in changes:
            changes["image_path"] = effective["image_path"]

    _validate_references(
        db,
        effective["user_id"],
        effective["selected_furniture_type_id"],
        effective["recognized_furniture_type_id"],
    )
    _validate_effective_state(
        selected_furniture_type_id=effective["selected_furniture_type_id"],
        recognized_furniture_type_id=effective["recognized_furniture_type_id"],
        recognition_confidence=effective["recognition_confidence"],
        image_path=effective["image_path"],
        input_method=effective["input_method"],
        status=effective["status"],
    )
    if effective["status"] not in ALLOWED_STATUS_TRANSITIONS[record.status]:
        raise ConflictError(
            f"Estimate status cannot change from {record.status} to {effective['status']}."
        )

    for field, value in changes.items():
        setattr(record, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("The estimate conflicts with existing data.") from error
    db.refresh(record)
    return get(db, record.id)  # type: ignore[return-value]
