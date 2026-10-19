"""Configuração central da aplicação, carregada por variáveis de ambiente."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Configurações tipadas. Lê `.env` da raiz e de `backend/.env`."""

    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Aplicação
    app_name: str = "Clinic Analytics API"
    app_version: str = "1.0.0"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Banco
    database_url: str = (
        "postgresql+psycopg://clinic:clinic@localhost:5432/clinic_analytics"
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Autenticação
    jwt_secret: str = "troque-este-segredo-em-producao"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    demo_password: str = "Clinic@2026"

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Domínio
    clinic_timezone: str = "America/Fortaleza"

    # Pipeline / dados sintéticos
    etl_seed: int = 42
    etl_anchor_date: str | None = None
    etl_history_months: int = 18
    etl_future_days: int = 14
    raw_dir: str = str(REPO_ROOT / "data" / "raw")
    staging_dir: str = str(REPO_ROOT / "data" / "staging")
    export_dir: str = str(REPO_ROOT / "data" / "exports")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def raw_path(self) -> Path:
        return Path(self.raw_dir)

    @property
    def staging_path(self) -> Path:
        return Path(self.staging_dir)

    @property
    def export_path(self) -> Path:
        return Path(self.export_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
