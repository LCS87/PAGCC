"""Profissionais, unidades e especialidades."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import User
from app.schemas.dashboard import ProfessionalIndicator, ProfessionalProfile
from app.schemas.domain import ProfessionalDetail
from app.services.appointments import list_appointments
from app.services.filters import ensure_professional_access, resolve_filters
from app.services.professionals import (
    get_professional,
    list_professionals,
    professional_indicators,
)

router = APIRouter(prefix="/professionals", tags=["Profissionais"])


@router.get("", response_model=list[ProfessionalDetail], summary="Lista de profissionais")
def professionals(
    unit_id: int | None = None,
    specialty_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProfessionalDetail]:
    return list_professionals(db, unit_id=unit_id, specialty_id=specialty_id)


@router.get(
    "/indicators",
    response_model=list[ProfessionalIndicator],
    summary="Indicadores por profissional no período",
)
def indicators(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ProfessionalIndicator]:
    filters = resolve_filters(db, current_user=user)
    return professional_indicators(db, filters)


@router.get(
    "/{professional_id}",
    response_model=ProfessionalProfile,
    summary="Perfil do profissional com indicadores e consultas recentes",
)
def professional_detail(
    professional_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfessionalProfile:
    professional = get_professional(db, professional_id)
    ensure_professional_access(user, professional_id)
    filters = resolve_filters(db, professional_id=professional_id, current_user=user)
    indicators = professional_indicators(db, filters)
    indicator = next(
        (item for item in indicators if item.professional.id == professional_id), None
    )
    recent, _ = list_appointments(
        db, professional_id=professional_id, page=1, page_size=10, sort="scheduled_start"
    )
    return ProfessionalProfile(
        professional=ProfessionalDetail.model_validate(professional),
        indicator=indicator,
        recent_appointments=recent,
    )
