"""Autenticação e gestão de usuários (RBAC)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import User
from app.models.enums import UserRole
from app.schemas.auth import TokenResponse, UserCreate, UserOut, UserUpdate

# Hash de referência para manter tempo de resposta constante em e-mails inexistentes.
_DUMMY_HASH = (
    "pbkdf2_sha256$260000$MDAwMDAwMDAwMDAwMDAwMA==$"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
)


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    if user is None:
        verify_password(password, _DUMMY_HASH)
        raise UnauthorizedError()
    if not verify_password(password, user.password_hash):
        raise UnauthorizedError()
    if not user.is_active:
        raise UnauthorizedError("Usuário inativo. Procure o administrador.")
    user.last_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user


def issue_token(user: User) -> TokenResponse:
    token = create_access_token(
        user.email, role=getattr(user.role, "value", str(user.role))
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.full_name)).all())


def create_user(db: Session, payload: UserCreate) -> User:
    email = payload.email.lower().strip()
    if db.scalar(select(User.id).where(User.email == email)):
        raise ConflictError("Já existe um usuário com este e-mail.")
    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        professional_id=payload.professional_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, payload: UserUpdate) -> User:
    user = db.get(User, user_id)
    if user is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Usuário", user_id)

    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    if "email" in data:
        data.pop("email")
    for field, value in data.items():
        setattr(user, field, value)
    if password:
        user.password_hash = hash_password(password)
    db.commit()
    db.refresh(user)
    return user


__all__ = ["authenticate", "create_user", "issue_token", "list_users", "update_user", "UserRole"]
