"""Endpoints de autenticação."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services.auth import authenticate, issue_token

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse, summary="Autentica e emite token JWT")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate(db, payload.email, payload.password)
    return issue_token(user)


@router.get("/me", response_model=UserOut, summary="Dados do usuário autenticado")
def me(user: User = Depends(get_current_user)) -> User:
    return user
