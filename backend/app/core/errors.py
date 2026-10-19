"""Erros de aplicação e handlers padronizados."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Erro esperado de negócio/API, serializado como `{"error": {...}}`."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: object) -> None:
        super().__init__(
            "not_found",
            f"{resource} não encontrado(a).",
            status_code=404,
            details={"resource": resource, "id": str(identifier)},
        )


class ForbiddenError(AppError):
    def __init__(self, message: str = "Acesso não autorizado para este perfil.") -> None:
        super().__init__("forbidden", message, status_code=403)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Credenciais inválidas ou sessão expirada.") -> None:
        super().__init__("unauthorized", message, status_code=401)


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("conflict", message, status_code=409)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        logger.warning("app_error", extra={"event": exc.code})
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error.get("loc", []) if part != "body"),
                "message": error.get("msg"),
                "type": error.get("type"),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Parâmetros inválidos na requisição.",
                    "details": details,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found"}.get(
            exc.status_code, "http_error"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": str(exc.detail)}},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Erro interno inesperado. Consulte os logs do servidor.",
                }
            },
        )
