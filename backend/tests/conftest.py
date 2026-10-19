"""Fixtures de teste: banco PostgreSQL isolado + carga sintética pequena."""

from __future__ import annotations

import os
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.entities import Professional, User
from app.models.enums import UserRole
from app.pipeline.generator import generate_dataset
from app.pipeline.loader import run_pipeline

TEST_ANCHOR = date(2026, 10, 19)
TEST_SEED = 1234


def _test_database_url() -> str:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit
    url = make_url(settings.database_url)
    if url.get_backend_name() != "postgresql":
        return "sqlite+pysqlite:///:memory:"
    return str(url.set(database=f"{url.database}_test"))


def _ensure_database(url) -> None:
    if url.get_backend_name() != "postgresql":
        return
    admin_url = url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def database_url() -> str:
    url_string = _test_database_url()
    _ensure_database(make_url(url_string))
    return url_string


@pytest.fixture(scope="session")
def engine(database_url):
    engine = create_engine(database_url, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def dataset(tmp_path_factory) -> dict:
    base = tmp_path_factory.mktemp("clinic-data")
    result = generate_dataset(
        base / "raw",
        seed=TEST_SEED,
        anchor=TEST_ANCHOR,
        history_months=2,
        future_days=4,
    )
    return {
        "raw_dir": result.raw_dir,
        "staging_root": base / "staging",
        "seed": TEST_SEED,
        "anchor": TEST_ANCHOR,
    }


@pytest.fixture(scope="session")
def seeded_engine(engine, dataset):
    with Session(engine) as db:
        run_pipeline(
            db,
            raw_dir=dataset["raw_dir"],
            staging_root=dataset["staging_root"],
            seed=dataset["seed"],
            anchor=dataset["anchor"],
        )
        professional_id = db.scalar(
            select(Professional.id).where(Professional.code == "PRO-001")
        )
        users = [
            ("admin@clinicavida.example", "Administrador Teste", UserRole.ADMIN, None),
            ("gestor@clinicavida.example", "Gestora Teste", UserRole.GESTOR, None),
            (
                "profissional@clinicavida.example",
                "Profissional Teste",
                UserRole.PROFISSIONAL,
                professional_id,
            ),
        ]
        for email, name, role, linked in users:
            db.add(
                User(
                    email=email,
                    full_name=name,
                    password_hash=hash_password("Clinic@2026"),
                    role=role,
                    professional_id=linked,
                    is_active=True,
                )
            )
        db.commit()
    return engine


@pytest.fixture(scope="session")
def client(seeded_engine):
    testing_session = sessionmaker(
        bind=seeded_engine, autoflush=False, expire_on_commit=False
    )

    def override_get_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _login(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Clinic@2026"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def admin_headers(client) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client, 'admin@clinicavida.example')}"}


@pytest.fixture(scope="session")
def gestor_headers(client) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client, 'gestor@clinicavida.example')}"}


@pytest.fixture(scope="session")
def profissional_headers(client) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_login(client, 'profissional@clinicavida.example')}"
    }
