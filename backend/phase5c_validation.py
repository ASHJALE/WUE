"""Disposable end-to-end validation for Phase 5C authentication."""

from __future__ import annotations

import json
import time
from datetime import timedelta
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import app.models  # noqa: F401
from sqlalchemy import delete, func, select

from app.database import get_session_factory
from app.models.estimate import Estimate
from app.models.furniture_material import FurnitureMaterial
from app.models.furniture_type import FurnitureType
from app.models.inventory import Inventory
from app.models.material import Material
from app.models.quotation import Quotation
from app.models.quotation_item import QuotationItem
from app.models.user import User
from app.services.auth import create_access_token, verify_password

BASE_URL = "http://127.0.0.1:8765"
results: list[str] = []


def request(
    label: str,
    method: str,
    path: str,
    expected: int,
    *,
    json_body=None,
    form_body=None,
    token: str | None = None,
):
    headers = {}
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    elif form_body is not None:
        data = urlencode(form_body).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req) as response:
            code, body = response.status, response.read().decode()
    except HTTPError as error:
        code, body = error.code, error.read().decode()
    results.append(f"{label}|{method} {path}|HTTP {code}")
    if code != expected:
        raise AssertionError(f"{label}: expected {expected}, received {code}: {body}")
    return json.loads(body)


def user_snapshot(db):
    return list(
        db.execute(
            select(
                User.id, User.username, User.email, User.password_hash,
                User.full_name, User.role, User.is_active,
                User.created_at, User.updated_at,
            ).order_by(User.id)
        ).all()
    )


def unrelated_counts(db):
    return {
        model.__tablename__: db.scalar(select(func.count(model.id))) or 0
        for model in (
            FurnitureType, Material, FurnitureMaterial, Inventory,
            Estimate, Quotation, QuotationItem,
        )
    }


suffix = str(int(time.time() * 1000))
username = f"phase5c_{suffix}"
email = f"phase5c_{suffix}@example.test"
password = "Phase5C-Strong-Password!"
created_user_id: int | None = None
success = False

with get_session_factory()() as db:
    users_before = user_snapshot(db)
    unrelated_before = unrelated_counts(db)

try:
    registered = request(
        "auth.register", "POST", "/auth/register", 201,
        json_body={
            "username": username,
            "email": email,
            "password": password,
            "full_name": "Phase 5C Validation User",
        },
    )
    created_user_id = registered["id"]
    if "password" in registered or "password_hash" in registered:
        raise AssertionError("Registration exposed password material.")
    if registered["role"] != "user" or registered["is_active"] is not True:
        raise AssertionError("Registration did not use safe user defaults.")

    with get_session_factory()() as db:
        stored = db.get(User, created_user_id)
        if stored is None or stored.password_hash == password:
            raise AssertionError("Plaintext password was stored.")
        if not stored.password_hash.startswith("$argon2"):
            raise AssertionError("Stored password is not an Argon2 hash.")
        if not verify_password(password, stored.password_hash):
            raise AssertionError("Stored hash does not verify the original password.")

    request(
        "auth.duplicate_register", "POST", "/auth/register", 409,
        json_body={
            "username": username.upper(),
            "email": f"other_{suffix}@example.test",
            "password": password,
            "full_name": "Duplicate Validation User",
        },
    )
    login = request(
        "auth.login", "POST", "/auth/login", 200,
        form_body={"username": username, "password": password},
    )
    access_token = login.get("access_token")
    if not access_token or login.get("token_type") != "bearer":
        raise AssertionError("Login did not return the required Bearer token response.")

    email_login = request(
        "auth.login_email", "POST", "/auth/login", 200,
        form_body={"username": email.upper(), "password": password},
    )
    if not email_login.get("access_token"):
        raise AssertionError("Case-insensitive email login failed.")
    request(
        "auth.incorrect_password", "POST", "/auth/login", 401,
        form_body={"username": username, "password": "incorrect-password"},
    )
    request(
        "auth.unknown_user", "POST", "/auth/login", 401,
        form_body={"username": f"missing_{suffix}", "password": password},
    )

    current = request("auth.me", "GET", "/auth/me", 200, token=access_token)
    if current["id"] != created_user_id or current["username"] != username:
        raise AssertionError("Current-user response did not match the token subject.")
    if "password" in current or "password_hash" in current:
        raise AssertionError("Current-user response exposed password material.")
    request("auth.me_missing_token", "GET", "/auth/me", 401)
    request("auth.me_malformed_token", "GET", "/auth/me", 401, token="not-a-jwt")
    expired = create_access_token(created_user_id, timedelta(seconds=-1))
    request("auth.me_expired_token", "GET", "/auth/me", 401, token=expired)
    missing_user_token = create_access_token(9223372036854775807)
    request(
        "auth.me_missing_user", "GET", "/auth/me", 401,
        token=missing_user_token,
    )

    with get_session_factory()() as db:
        if unrelated_counts(db) != unrelated_before:
            raise AssertionError("Authentication validation changed an unrelated table.")

    print("REGISTER_VALIDATION_OK=True")
    print("PASSWORD_HASHING_OK=True")
    print("DUPLICATE_REGISTRATION_OK=True")
    print("LOGIN_VALIDATION_OK=True")
    print("INVALID_CREDENTIALS_OK=True")
    print("CURRENT_USER_OK=True")
    print("MISSING_TOKEN_OK=True")
    print("MALFORMED_TOKEN_OK=True")
    print("EXPIRED_TOKEN_OK=True")
    print("MISSING_USER_TOKEN_OK=True")
    print("PASSWORD_HASH_NOT_EXPOSED=True")
    success = True
finally:
    with get_session_factory()() as db:
        if created_user_id is not None:
            db.execute(delete(User).where(User.id == created_user_id))
        db.commit()
        remaining = (
            db.scalar(select(func.count(User.id)).where(User.id == created_user_id))
            if created_user_id is not None else 0
        ) or 0
        if user_snapshot(db) != users_before:
            raise AssertionError("A pre-existing user changed during validation.")
        if unrelated_counts(db) != unrelated_before:
            raise AssertionError("An unrelated table changed during validation.")
        print(f"PHASE5C_TEMP_USERS={remaining}")
        print("TEMP_FIXTURE_CLEANUP_OK=True")
    print("--- PHASE 5C HTTP RESULTS ---")
    print("\n".join(results))
    print(f"PHASE5C_VALIDATION_OK={success}")
