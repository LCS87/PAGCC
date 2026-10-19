"""KPIs executivos e operacionais."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_metric_filters
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import Granularity
from app.schemas.dashboard import (
    OperationalSummary,
    OverviewResponse,
    ProfessionalIndicator,
    TimeseriesResponse,
)
from app.services.analytics import timeseries as build_timeseries
from app.services.filters import MetricFilters
from app.services.metrics import build_overview
from app.services.operations import build_operational_summary
from app.services.professionals import professional_indicators

router = APIRouter(prefix="/kpis", tags=["KPIs"])


@router.get(
    "/overview",
    response_model=OverviewResponse,
    summary="KPIs do período com comparação ao período anterior",
)
def overview(
    filters: MetricFilters = Depends(get_metric_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OverviewResponse:
    return build_overview(db, filters)


@router.get(
    "/operational",
    response_model=OperationalSummary,
    summary="Pendências, atrasos e tarefas priorizadas",
)
def operational(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> OperationalSummary:
    return build_operational_summary(db)


@router.get(
    "/professionals",
    response_model=list[ProfessionalIndicator],
    summary="Indicadores agregados por profissional",
)
def professionals(
    filters: MetricFilters = Depends(get_metric_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProfessionalIndicator]:
    return professional_indicators(db, filters)


@router.get(
    "/timeseries",
    response_model=TimeseriesResponse,
    summary="Série temporal de agendamentos, realizados, faltas, ocupação e receita",
)
def series(
    granularity: Granularity = Query(default=Granularity.DAY),
    filters: MetricFilters = Depends(get_metric_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TimeseriesResponse:
    return build_timeseries(db, filters, granularity)
