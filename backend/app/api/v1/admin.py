"""Administração: status do sistema e usuários/papéis."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import UserRole
from app.schemas.auth import UserCreate, UserUpdate
from app.schemas.dashboard import SystemStatus
from app.schemas.domain import UserOutAdmin
from app.services.admin import system_status
from app.services.auth import create_user, list_users, update_user

router = APIRouter(prefix="/admin", tags=["Administração"])

ADMIN_ONLY = require_roles(UserRole.ADMIN)
MANAGERS = require_roles(UserRole.ADMIN, UserRole.GESTOR)


@router.get(
    "/status",
    response_model=SystemStatus,
    summary="Versão, banco, pipeline e contagens do ambiente",
)
def status(
    db: Session = Depends(get_db), user: User = Depends(MANAGERS)
) -> SystemStatus:
    return system_status(db)


@router.get(
    "/users",
    response_model=list[UserOutAdmin],
    summary="Lista usuários e papéis (somente ADMIN)",
)
def users(db: Session = Depends(get_db), user: User = Depends(ADMIN_ONLY)) -> list[User]:
    return list_users(db)


@router.post(
    "/users",
    response_model=UserOutAdmin,
    status_code=201,
    summary="Cria um usuário (somente ADMIN)",
)
def create(
    payload: UserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(ADMIN_ONLY),
) -> User:
    return create_user(db, payload)


@router.patch(
    "/users/{user_id}",
    response_model=UserOutAdmin,
    summary="Atualiza papel, status ou senha de um usuário (somente ADMIN)",
)
def patch(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(ADMIN_ONLY),
) -> User:
    return update_user(db, user_id, payload)
