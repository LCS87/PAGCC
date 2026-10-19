"""Metadados e opções de filtro."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import User
from app.schemas.dashboard import FilterOptions
from app.services.admin import filter_options

router = APIRouter(prefix="/meta", tags=["Metadados"])


@router.get(
    "/options",
    response_model=FilterOptions,
    summary="Unidades, especialidades, profissionais, status e datas de referência",
)
def options(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> FilterOptions:
    return filter_options(db)
