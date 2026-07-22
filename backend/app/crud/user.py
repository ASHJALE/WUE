"""User persistence helpers for authentication."""

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud import ConflictError
from app.models.user import User
from app.schemas.auth import UserRegister


def get_by_identifier(db: Session, identifier: str) -> User | None:
    normalized = identifier.strip().lower()
    return db.scalar(
        select(User).where(
            or_(
                func.lower(User.username) == normalized,
                func.lower(User.email) == normalized,
            )
        )
    )


def create(db: Session, data: UserRegister, password_hash: str) -> User:
    user = User(
        username=data.username,
        email=data.email,
        password_hash=password_hash,
        full_name=data.full_name,
        role="user",
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("A user with that username or email already exists.") from error
    db.refresh(user)
    return user
