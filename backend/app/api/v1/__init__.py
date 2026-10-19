"""Agregador dos routers da API v1."""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    analytics,
    appointments,
    attendances,
    auth,
    kpis,
    meta,
    professionals,
    quality,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(meta.router)
api_router.include_router(kpis.router)
api_router.include_router(analytics.router)
api_router.include_router(appointments.router)
api_router.include_router(attendances.router)
api_router.include_router(professionals.router)
api_router.include_router(quality.router)
api_router.include_router(admin.router)

__all__ = ["api_router"]
