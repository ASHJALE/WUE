"""Isolated ASGI validation for Phase 7.5 structured BOM generation."""

import asyncio
import json
from types import SimpleNamespace

from app.dependencies.auth import get_current_user
from app.main import app
from app.schemas.material import MaterialRecommendation
from app.services.bom_generator import BOM_TEMPLATE_CATALOG, generate_bom
from app.services.material_recommender import recommend_materials

SUPPORTED_TYPES = ("chair", "bed", "sofa", "dining_table", "lamp_shade")


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
        "method": "POST", "scheme": "http", "path": "/bom/generate",
        "raw_path": b"/bom/generate", "query_string": b"", "root_path": "",
        "headers": headers, "client": ("127.0.0.1", 12345), "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return start["status"], json.loads(response_body) if response_body else None


async def main():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=505, username="phase75")
    try:
        assert set(BOM_TEMPLATE_CATALOG) == set(SUPPORTED_TYPES)
        for furniture_type in SUPPORTED_TYPES:
            recommendations = recommend_materials(furniture_type)
            payload = {
                "furniture_type": furniture_type,
                "materials": [item.model_dump() for item in recommendations],
            }
            status_code, response = await request(payload)
            assert status_code == 200, (furniture_type, status_code, response)
            assert response["furniture_type"] == furniture_type and response["status"] == "generated"
            assert len(response["components"]) == len(BOM_TEMPLATE_CATALOG[furniture_type])
            assert all(item["component"].strip() for item in response["components"])
            assert all(item["recommended_material"].strip() for item in response["components"])
            assert all(item["category"].strip() for item in response["components"])
            assert all(item["quantity"] is None for item in response["components"])
            assert all(item["notes"] == "Quantity calculated in Phase 7.6" for item in response["components"])
            service_result = generate_bom(furniture_type, recommendations)
            assert [item.model_dump() for item in service_result] == response["components"]

        valid_materials = [item.model_dump() for item in recommend_materials("chair")]
        invalid_furniture_status, _ = await request({"furniture_type": "desk", "materials": valid_materials})
        assert invalid_furniture_status == 422

        empty_status, _ = await request({"furniture_type": "chair", "materials": []})
        assert empty_status == 422
        malformed_status, _ = await request({"furniture_type": "chair", "materials": [{"name": "Wood"}]})
        assert malformed_status == 422
        alternatives_only = [
            MaterialRecommendation(
                name="MDF", category="Engineered Wood", priority="Alternative",
                quality="Economy", reason="Validation alternative.",
            ).model_dump()
        ]
        no_primary_status, _ = await request({"furniture_type": "chair", "materials": alternatives_only})
        assert no_primary_status == 422

        app.dependency_overrides.clear()
        unauthorized_status, _ = await request(
            {"furniture_type": "chair", "materials": valid_materials}, authenticated=False
        )
        assert unauthorized_status == 401

        operation = app.openapi()["paths"]["/bom/generate"]["post"]
        assert operation["security"] and "200" in operation["responses"]

        print("BOM_ENDPOINT_OK=True")
        print("JWT_REQUIRED_OK=True")
        print("INVALID_FURNITURE_422_OK=True")
        print("INVALID_MATERIALS_422_OK=True")
        print("BOM_SERVICE_OK=True")
        print("COMPONENT_GENERATION_OK=True")
        print("NULL_QUANTITY_OK=True")
        print("CATEGORY_VALIDATION_OK=True")
        print("BACKEND_TESTS_OK=True")
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    asyncio.run(main())
