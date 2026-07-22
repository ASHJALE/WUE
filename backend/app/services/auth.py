"""Password hashing, credential verification, and JWT handling."""

from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import (
    get_jwt_algorithm,
    get_jwt_expiration_minutes,
    get_jwt_secret_key,
)
from app.crud import user as user_crud
from app.models.user import User

password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("wue-dummy-credential-check")


class InvalidAccessTokenError(Exception):
    """Raised when a JWT cannot identify a valid user subject."""


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hash.verify(password, stored_hash)


def authenticate_user(db: Session, identifier: str, password: str) -> User | None:
    user = user_crud.get_by_identifier(db, identifier)
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(
    user_id: int, expires_delta: timedelta | None = None
) -> str:
    now = datetime.now(timezone.utc)
    expires = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=get_jwt_expiration_minutes())
    )
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": expires},
        get_jwt_secret_key(),
        algorithm=get_jwt_algorithm(),
    )


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret_key(),
            algorithms=[get_jwt_algorithm()],
        )
        subject = payload.get("sub")
        if not isinstance(subject, str):
            raise InvalidAccessTokenError("Token subject is missing.")
        user_id = int(subject)
        if user_id <= 0:
            raise ValueError
        return user_id
    except (InvalidTokenError, TypeError, ValueError) as error:
        raise InvalidAccessTokenError("Invalid access token.") from error
