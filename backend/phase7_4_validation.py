"""Isolated ASGI validation for Phase 7.4 material recommendations."""

import asyncio
import json
from types import SimpleNamespace

from app.dependencies.auth import get_current_user
from app.main import app
from app.services.material_recommender import RECOMMENDATION_CATALOG, recommend_materials

SUPPORTED_TYPES = ("chair", "bed", "sofa", "dining_table", "lamp_shade")
VALID_QUALITIES = {"Economy", "Standard", "Premium"}


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
        "method": "POST", "scheme": "http", "path": "/materials/recommend",
        "raw_path": b"/materials/recommend", "query_string": b"", "root_path": "",
        "headers": headers, "client": ("127.0.0.1", 12345), "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return start["status"], json.loads(response_body) if response_body else None


async def main():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=404, username="phase74")
    try:
        assert set(RECOMMENDATION_CATALOG) == set(SUPPORTED_TYPES)
        for furniture_type in SUPPORTED_TYPES:
            status_code, response = await request({"furniture_type": furniture_type})
            assert status_code == 200, (furniture_type, status_code, response)
            assert response["furniture_type"] == furniture_type
            assert response["display_name"] and response["status"] == "recommended"
            materials = response["materials"]
            primary = [item for item in materials if item["priority"] == "Primary"]
            alternatives = [item for item in materials if item["priority"] == "Alternative"]
            assert len(primary) >= 2 and len(alternatives) >= 2
            assert all(item["quality"] in VALID_QUALITIES for item in materials)
            assert all(item["reason"].strip() for item in materials)
            assert [item.model_dump() for item in recommend_materials(furniture_type)] == materials

        invalid_status, invalid = await request({"furniture_type": "desk"})
        assert invalid_status == 422 and invalid["detail"]

        app.dependency_overrides.clear()
        unauthorized_status, _ = await request({"furniture_type": "chair"}, authenticated=False)
        assert unauthorized_status == 401

        operation = app.openapi()["paths"]["/materials/recommend"]["post"]
        assert operation["security"] and "200" in operation["responses"]

        print("MATERIAL_ENDPOINT_OK=True")
        print("JWT_REQUIRED_OK=True")
        print("SUPPORTED_TYPES_OK=True")
        print("INVALID_TYPE_422_OK=True")
        print("RECOMMENDER_SERVICE_OK=True")
        print("PRIMARY_GROUP_OK=True")
        print("ALTERNATIVE_GROUP_OK=True")
        print("MINIMUM_RECOMMENDATIONS_OK=True")
        print("QUALITY_VALIDATION_OK=True")
        print("REASON_PRESENT_OK=True")
        print("BACKEND_TESTS_OK=True")
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    asyncio.run(main())
