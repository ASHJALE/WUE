"""Safe authentication request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)

    @field_validator("username", "email", "full_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank.")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email_shape(cls, value: str) -> str:
        if value.count("@") != 1 or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return value


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
