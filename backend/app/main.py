"""Ponto de entrada da API do Clinic Analytics."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger, request_id_ctx
from app.db.session import engine

configure_logging(settings.log_level)
logger = get_logger("clinic_analytics.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "startup",
        extra={
            "event": "startup",
            "environment": settings.environment,
            "database": settings.database_url.split("@")[-1],
        },
    )
    if settings.is_production and "troque-este-segredo" in settings.jwt_secret:
        logger.warning(
            "jwt_secret_default",
            extra={"event": "insecure_default_secret"},
        )
    yield
    engine.dispose()
    logger.info("shutdown", extra={"event": "shutdown"})


app = FastAPI(
    title="Clinic Analytics API",
    description=(
        "API da plataforma analítica para clínicas ambulatoriais. Todos os dados são "
        "sintéticos e destinados a demonstração acadêmica."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)

register_exception_handlers(app)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    token = request_id_ctx.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - started) * 1000
        logger.exception(
            "request_failed",
            extra={
                "event": "request",
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": round(elapsed, 2),
            },
        )
        request_id_ctx.reset(token)
        raise
    elapsed = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request",
        extra={
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(elapsed, 2),
            "user_id": (
                getattr(request.state.user, "id", None)
                if hasattr(request.state, "user")
                else None
            ),
        },
    )
    request_id_ctx.reset(token)
    return response


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["Infra"], summary="Health check da API e do banco")
def health() -> JSONResponse:
    from sqlalchemy import text

    database = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - ambiente degradado
        database = "error"
    status_code = 200 if database == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if database == "ok" else "degraded",
            "version": settings.app_version,
            "database": database,
            "environment": settings.environment,
        },
    )


@app.get("/", tags=["Infra"], summary="Identificação da API")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/health",
        "api": settings.api_v1_prefix,
    }
