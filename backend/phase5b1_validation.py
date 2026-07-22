"""Disposable HTTP validation for Phase 5B-1 BOM-template CRUD."""

from __future__ import annotations

import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

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
furniture_type_id = material_id = bom_id = None

try:
    expect("root", "GET", "/", 200)
    expect("docs", "GET", "/docs", 200)
    expect("health", "GET", "/health/database", 200)

    furniture = expect(
        "prerequisite.furniture.create",
        "POST",
        "/furniture-types",
        201,
        {"name": f"Phase5B1 Furniture {suffix}"},
    )
    furniture_type_id = furniture["id"]
    material = expect(
        "prerequisite.material.create",
        "POST",
        "/materials",
        201,
        {
            "name": f"Phase5B1 Material {suffix}",
            "unit": "piece",
            "current_unit_price": 25,
        },
    )
    material_id = material["id"]

    bom = expect(
        "bom.create",
        "POST",
        "/furniture-materials",
        201,
        {
            "furniture_type_id": furniture_type_id,
            "material_id": material_id,
            "quantity_required": 2.500,
            "wastage_percentage": 5.00,
            "notes": "temporary",
        },
    )
    bom_id = bom["id"]
    expect("bom.read", "GET", f"/furniture-materials/{bom_id}", 200)
    expect(
        "bom.update",
        "PUT",
        f"/furniture-materials/{bom_id}",
        200,
        {"quantity_required": 3.250, "wastage_percentage": 7.50},
    )
    expect(
        "bom.list",
        "GET",
        f"/furniture-materials?skip=0&limit=100&furniture_type_id={furniture_type_id}",
        200,
    )
    expect(
        "bom.duplicate",
        "POST",
        "/furniture-materials",
        409,
        {
            "furniture_type_id": furniture_type_id,
            "material_id": material_id,
            "quantity_required": 1,
        },
    )
    expect(
        "bom.missing_furniture_type",
        "POST",
        "/furniture-materials",
        409,
        {
            "furniture_type_id": 9223372036854775807,
            "material_id": material_id,
            "quantity_required": 1,
        },
    )
    expect(
        "bom.missing_material",
        "POST",
        "/furniture-materials",
        409,
        {
            "furniture_type_id": furniture_type_id,
            "material_id": 9223372036854775807,
            "quantity_required": 1,
        },
    )
    expect(
        "bom.invalid_quantity",
        "POST",
        "/furniture-materials",
        422,
        {
            "furniture_type_id": furniture_type_id,
            "material_id": material_id,
            "quantity_required": 0,
        },
    )
    expect(
        "bom.invalid_wastage_low",
        "PUT",
        f"/furniture-materials/{bom_id}",
        422,
        {"wastage_percentage": -1},
    )
    expect(
        "bom.invalid_wastage_high",
        "PUT",
        f"/furniture-materials/{bom_id}",
        422,
        {"wastage_percentage": 101},
    )
    expect(
        "bom.missing",
        "GET",
        "/furniture-materials/9223372036854775807",
        404,
    )

    expect("bom.delete", "DELETE", f"/furniture-materials/{bom_id}", 204)
    bom_id = None
    expect("prerequisite.material.delete", "DELETE", f"/materials/{material_id}", 204)
    material_id = None
    expect(
        "prerequisite.furniture.delete",
        "DELETE",
        f"/furniture-types/{furniture_type_id}",
        204,
    )
    furniture_type_id = None
    print("PHASE5B1_VALIDATION_OK=True")
finally:
    if bom_id is not None:
        request("cleanup.bom", "DELETE", f"/furniture-materials/{bom_id}")
    if material_id is not None:
        request("cleanup.material", "DELETE", f"/materials/{material_id}")
    if furniture_type_id is not None:
        request(
            "cleanup.furniture",
            "DELETE",
            f"/furniture-types/{furniture_type_id}",
        )
    print("--- PHASE 5B-1 RESULTS ---")
    print("\n".join(results))
