"""Public registration, OAuth2 login, and current-user endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.crud import ConflictError
from app.crud import user as user_crud
from app.database import get_db
from app.dependencies.auth import CurrentUser
from app.schemas.auth import PublicUser, Token, UserRegister
from app.services.auth import authenticate_user, create_access_token, hash_password

router = APIRouter(prefix="/auth", tags=["Authentication"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/register", response_model=PublicUser, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: DbSession):
    try:
        return user_crud.create(db, data, hash_password(data.password))
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    user = authenticate_user(db, form.username, form.password)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect identifier or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=PublicUser)
def current_user(user: CurrentUser):
    return user
