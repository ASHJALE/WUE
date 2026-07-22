"""Disposable HTTP validation for Phase 5B-2 Estimate CRUD and workflow."""

from __future__ import annotations

import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app.models  # noqa: F401 - register every relationship target
from sqlalchemy import delete

from app.database import get_session_factory
from app.models.estimate import Estimate
from app.models.furniture_type import FurnitureType
from app.models.user import User

BASE_URL = "http://127.0.0.1:8765"
results: list[str] = []


def request(label: str, method: str, path: str, body: dict | None = None):
    payload = json.dumps(body).encode() if body is not None else None
    req = Request(
        BASE_URL + path,
        data=payload,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req) as response:
            status = response.status
            text = response.read().decode()
    except HTTPError as error:
        status = error.code
        text = error.read().decode()
    shown = "<Swagger UI HTML>" if label == "docs" else text
    results.append(f"{label}|HTTP {status}|{shown}")
    parsed = json.loads(text) if text.lstrip().startswith(("{", "[")) else None
    return status, parsed


def expect(label: str, method: str, path: str, expected: int, body=None):
    status, parsed = request(label, method, path, body)
    if status != expected:
        raise AssertionError(f"{label}: expected {expected}, received {status}")
    return parsed


suffix = str(int(time.time() * 1000))
estimate_ids: list[int] = []
user_id = furniture_type_id = None

try:
    with get_session_factory()() as db:
        user = User(
            username=f"phase5b2_user_{suffix}",
            email=f"phase5b2_{suffix}@example.test",
            password_hash="temporary-validation-hash",
            full_name="Phase 5B-2 Validation User",
        )
        furniture_type = FurnitureType(name=f"Phase5B2 Furniture {suffix}")
        db.add_all([user, furniture_type])
        db.commit()
        db.refresh(user)
        db.refresh(furniture_type)
        user_id = user.id
        furniture_type_id = furniture_type.id

    expect("root", "GET", "/", 200)
    expect("docs", "GET", "/docs", 200)
    expect("health", "GET", "/health/database", 200)

    estimate = expect(
        "estimate.create",
        "POST",
        "/estimates",
        201,
        {
            "user_id": user_id,
            "selected_furniture_type_id": furniture_type_id,
            "recognized_furniture_type_id": furniture_type_id,
            "recognition_confidence": 0.8750,
            "input_method": "predefined",
        },
    )
    estimate_ids.append(estimate["id"])
    if estimate["username"] != f"phase5b2_user_{suffix}":
        raise AssertionError("Estimate response did not include the expected username.")
    if estimate["selected_furniture_type_name"] != f"Phase5B2 Furniture {suffix}":
        raise AssertionError("Estimate response did not include the selected type name.")

    expect("estimate.read", "GET", f"/estimates/{estimate['id']}", 200)
    expect(
        "estimate.list",
        "GET",
        f"/estimates?skip=0&limit=100&user_id={user_id}&status=draft",
        200,
    )
    expect(
        "estimate.status.processing",
        "PUT",
        f"/estimates/{estimate['id']}",
        200,
        {"status": "processing"},
    )
    expect(
        "estimate.status.processed",
        "PUT",
        f"/estimates/{estimate['id']}",
        200,
        {"status": "processed"},
    )
    expect(
        "estimate.status.backward_rejected",
        "PUT",
        f"/estimates/{estimate['id']}",
        409,
        {"status": "draft"},
    )
    expect(
        "estimate.status.quoted",
        "PUT",
        f"/estimates/{estimate['id']}",
        200,
        {"status": "quoted"},
    )
    expect(
        "estimate.status.quoted_terminal",
        "PUT",
        f"/estimates/{estimate['id']}",
        409,
        {"status": "processing"},
    )
    expect(
        "estimate.status.invalid",
        "PUT",
        f"/estimates/{estimate['id']}",
        422,
        {"status": "invalid"},
    )

    image_estimate = expect(
        "estimate.image_upload_valid",
        "POST",
        "/estimates",
        201,
        {
            "user_id": user_id,
            "input_method": "image_upload",
            "image_path": "uploads/phase5b2-test.jpg",
        },
    )
    estimate_ids.append(image_estimate["id"])
    draft = expect(
        "estimate.draft_without_selected",
        "POST",
        "/estimates",
        201,
        {"user_id": user_id, "input_method": "predefined"},
    )
    estimate_ids.append(draft["id"])
    expect(
        "estimate.processed_requires_selected",
        "PUT",
        f"/estimates/{draft['id']}",
        409,
        {"status": "processed"},
    )

    expect(
        "estimate.missing_user",
        "POST",
        "/estimates",
        409,
        {"user_id": 9223372036854775807, "input_method": "predefined"},
    )
    expect(
        "estimate.missing_selected_type",
        "POST",
        "/estimates",
        409,
        {
            "user_id": user_id,
            "selected_furniture_type_id": 9223372036854775807,
            "input_method": "predefined",
        },
    )
    expect(
        "estimate.missing_recognized_type",
        "POST",
        "/estimates",
        409,
        {
            "user_id": user_id,
            "recognized_furniture_type_id": 9223372036854775807,
            "recognition_confidence": 0.5,
            "input_method": "predefined",
        },
    )
    expect(
        "estimate.confidence_high",
        "POST",
        "/estimates",
        422,
        {
            "user_id": user_id,
            "recognized_furniture_type_id": furniture_type_id,
            "recognition_confidence": 1.1,
            "input_method": "predefined",
        },
    )
    expect(
        "estimate.recognition_pair_required",
        "POST",
        "/estimates",
        422,
        {
            "user_id": user_id,
            "recognized_furniture_type_id": furniture_type_id,
            "input_method": "predefined",
        },
    )
    expect(
        "estimate.image_path_required",
        "POST",
        "/estimates",
        422,
        {"user_id": user_id, "input_method": "image_upload"},
    )
    expect(
        "estimate.missing",
        "GET",
        "/estimates/9223372036854775807",
        404,
    )
    expect(
        "estimate.list_invalid_status",
        "GET",
        "/estimates?status=invalid",
        422,
    )
    print("PHASE5B2_VALIDATION_OK=True")
finally:
    with get_session_factory()() as db:
        if estimate_ids:
            db.execute(delete(Estimate).where(Estimate.id.in_(estimate_ids)))
        if furniture_type_id is not None:
            db.execute(
                delete(FurnitureType).where(FurnitureType.id == furniture_type_id)
            )
        if user_id is not None:
            db.execute(delete(User).where(User.id == user_id))
        db.commit()
    print("--- PHASE 5B-2 RESULTS ---")
    print("\n".join(results))
