"""Isolated ASGI validation for Phase 7.6 preliminary quantity estimation."""

import asyncio
import json
from types import SimpleNamespace

from app.dependencies.auth import get_current_user
from app.main import app
from app.schemas.quantity import FurnitureDimensions
from app.services.bom_generator import generate_bom
from app.services.material_recommender import recommend_materials
from app.services.quantity_estimator import QUANTITY_RULE_CATALOG, estimate_quantities

SUPPORTED_TYPES = ("chair", "bed", "sofa", "dining_table", "lamp_shade")
VALID_UNITS = {"board_foot", "square_meter", "meter", "piece", "set", "application"}
DIMENSIONS = {
    "chair": {"width": 450, "depth": 500, "height": 900},
    "bed": {"width": 1600, "depth": 2000, "height": 1000},
    "sofa": {"width": 2100, "depth": 900, "height": 850},
    "dining_table": {"width": 1800, "depth": 900, "height": 750},
    "lamp_shade": {"width": 350, "depth": 350, "height": 600},
}


async def request(payload: dict, authenticated: bool = True):
    body = json.dumps(payload).encode()
    headers = [(b"content-type", b"application/json")]
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
        "method": "POST", "scheme": "http", "path": "/bom/estimate-quantities",
        "raw_path": b"/bom/estimate-quantities", "query_string": b"", "root_path": "",
        "headers": headers, "client": ("127.0.0.1", 12345), "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return start["status"], json.loads(response_body) if response_body else None


def payload_for(furniture_type: str):
    materials = recommend_materials(furniture_type)
    components = generate_bom(furniture_type, materials)
    return {
        "furniture_type": furniture_type,
        "dimensions": DIMENSIONS[furniture_type],
        "components": [item.model_dump() for item in components],
    }, components


async def main():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=606, username="phase76")
    try:
        assert set(QUANTITY_RULE_CATALOG) == set(SUPPORTED_TYPES)
        for furniture_type in SUPPORTED_TYPES:
            payload, components = payload_for(furniture_type)
            status_code, response = await request(payload)
            assert status_code == 200, (furniture_type, status_code, response)
            assert response["furniture_type"] == furniture_type and response["status"] == "estimated"
            assert len(response["components"]) == len(components)
            assert all(item["estimated_quantity"] > 0 for item in response["components"])
            assert all(item["unit"] in VALID_UNITS for item in response["components"])
            assert all(item["calculation_basis"] == "Template Estimate" for item in response["components"])
            assert all(item["confidence"] == "Preliminary" for item in response["components"])
            direct = estimate_quantities(
                furniture_type,
                FurnitureDimensions(**DIMENSIONS[furniture_type]),
                components,
            )
            assert [item.model_dump() for item in direct] == response["components"]

        chair_payload, _ = payload_for("chair")
        invalid_furniture = {**chair_payload, "furniture_type": "desk"}
        invalid_furniture_status, _ = await request(invalid_furniture)
        assert invalid_furniture_status == 422

        for invalid_dimensions in (
            {"width": 0, "depth": 500, "height": 900},
            {"width": -1, "depth": 500, "height": 900},
            {"width": "wide", "depth": 500, "height": 900},
        ):
            invalid_status, _ = await request({**chair_payload, "dimensions": invalid_dimensions})
            assert invalid_status == 422

        invalid_component = json.loads(json.dumps(chair_payload))
        invalid_component["components"][0]["component"] = "Unknown Part"
        invalid_component_status, _ = await request(invalid_component)
        assert invalid_component_status == 422

        malformed_component = json.loads(json.dumps(chair_payload))
        del malformed_component["components"][0]["category"]
        malformed_status, _ = await request(malformed_component)
        assert malformed_status == 422

        app.dependency_overrides.clear()
        unauthorized_status, _ = await request(chair_payload, authenticated=False)
        assert unauthorized_status == 401

        operation = app.openapi()["paths"]["/bom/estimate-quantities"]["post"]
        assert operation["security"] and "200" in operation["responses"]

        print("QUANTITY_ENDPOINT_OK=True")
        print("JWT_REQUIRED_OK=True")
        print("INVALID_FURNITURE_422_OK=True")
        print("INVALID_DIMENSIONS_422_OK=True")
        print("NEGATIVE_DIMENSIONS_REJECTED_OK=True")
        print("QUANTITY_SERVICE_OK=True")
        print("POSITIVE_QUANTITIES_OK=True")
        print("UNIT_VALIDATION_OK=True")
        print("BACKEND_TESTS_OK=True")
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    asyncio.run(main())
