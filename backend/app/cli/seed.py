"""Criação idempotente dos usuários de demonstração."""

from __future__ import annotations

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.entities import Professional, User
from app.models.enums import UserRole

configure_logging(settings.log_level)
logger = get_logger("clinic_analytics.seed")

DEMO_USERS = [
    ("admin@clinicavida.example", "Administrador Demo", UserRole.ADMIN, None),
    ("gestor@clinicavida.example", "Marina Gouveia", UserRole.GESTOR, None),
    ("coordenador@clinicavida.example", "Rafael Torres", UserRole.COORDENADOR, None),
    ("analista@clinicavida.example", "Helena Prado", UserRole.ANALISTA, None),
    ("recepcao@clinicavida.example", "Sofia Martins", UserRole.RECEPCAO, None),
    ("profissional@clinicavida.example", "Dra. Ana Beatriz Lima", UserRole.PROFISSIONAL, "PRO-001"),
]


def seed_users() -> int:
    created = 0
    with SessionLocal() as db:
        professional_id = db.scalar(
            select(Professional.id).where(Professional.code == "PRO-001")
        )
        for email, full_name, role, professional_code in DEMO_USERS:
            existing = db.scalar(select(User).where(User.email == email))
            if existing is not None:
                continue
            linked_id = professional_id if professional_code == "PRO-001" else None
            db.add(
                User(
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password(settings.demo_password),
                    role=role,
                    professional_id=linked_id,
                    is_active=True,
                )
            )
            created += 1
        db.commit()
    logger.info("seed_completed", extra={"event": "seed", "users_created": created})
    return created


def main() -> None:
    created = seed_users()
    print(
        f"Seed concluído: {created} usuário(s) criado(s). "
        f"Senha padrão definida por DEMO_PASSWORD."
    )


if __name__ == "__main__":
    main()
