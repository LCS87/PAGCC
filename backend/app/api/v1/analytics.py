"""Analytics: séries, segmentações e exportação CSV."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_metric_filters, require_roles
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import Granularity, UserRole
from app.schemas.dashboard import BreakdownResponse, TimeseriesResponse
from app.services.analytics import breakdown as build_breakdown
from app.services.analytics import export_appointments_csv
from app.services.analytics import timeseries as build_timeseries
from app.services.filters import MetricFilters

router = APIRouter(prefix="/analytics", tags=["Analytics"])

EXPORT_ROLES = (
    UserRole.ADMIN,
    UserRole.GESTOR,
    UserRole.COORDENADOR,
    UserRole.ANALISTA,
)


@router.get(
    "/timeseries",
    response_model=TimeseriesResponse,
    summary="Série temporal para os gráficos de evolução",
)
def series(
    granularity: Granularity = Query(default=Granularity.DAY),
    filters: MetricFilters = Depends(get_metric_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TimeseriesResponse:
    return build_timeseries(db, filters, granularity)


@router.get(
    "/breakdown",
    response_model=BreakdownResponse,
    summary=(
        "Segmentação por especialidade, profissional, unidade, dia da semana, "
        "hora, status ou origem"
    ),
)
def breakdown(
    dimension: str = Query(
        default="specialty",
        pattern="^(specialty|professional|unit|weekday|hour|status|source)$",
    ),
    filters: MetricFilters = Depends(get_metric_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BreakdownResponse:
    return build_breakdown(db, filters, dimension)


@router.get(
    "/export.csv",
    summary="Exporta os agendamentos do período em CSV (dados sintéticos)",
    response_class=Response,
)
def export_csv(
    filters: MetricFilters = Depends(get_metric_filters),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*EXPORT_ROLES)),
) -> Response:
    content = export_appointments_csv(db, filters)
    filename = f"agendamentos_{filters.start.isoformat()}_{filters.end.isoformat()}.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
