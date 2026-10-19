"""Dependências de autenticação, autorização, filtros e paginação."""

from __future__ import annotations

from datetime import date

import jwt
from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import UserRole
from app.services.filters import MetricFilters, resolve_filters

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Token de acesso ausente.")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Sessão expirada. Faça login novamente.") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Token inválido.") from exc

    email = payload.get("sub")
    if not email:
        raise UnauthorizedError("Token sem identificação de usuário.")
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active:
        raise UnauthorizedError("Usuário não encontrado ou inativo.")
    request.state.user = user
    return user


def require_roles(*roles: UserRole):
    allowed = set(roles)

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise ForbiddenError(
                "Seu perfil não tem permissão para acessar este recurso."
            )
        return user

    return dependency


def get_metric_filters(
    start: date | None = Query(default=None, description="Data inicial (AAAA-MM-DD)"),
    end: date | None = Query(default=None, description="Data final (AAAA-MM-DD)"),
    unit_id: int | None = Query(default=None, ge=1),
    specialty_id: int | None = Query(default=None, ge=1),
    professional_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MetricFilters:
    try:
        return resolve_filters(
            db,
            start=start,
            end=end,
            unit_id=unit_id,
            specialty_id=specialty_id,
            professional_id=professional_id,
            current_user=user,
        )
    except ValueError as exc:
        raise AppError("invalid_period", str(exc), status_code=422) from exc


def pagination(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> tuple[int, int]:
    return page, page_size


__all__ = [
    "get_current_user",
    "get_metric_filters",
    "pagination",
    "require_roles",
]
