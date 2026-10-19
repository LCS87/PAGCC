"""Filtros de período e escopo compartilhados pelas consultas analíticas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ForbiddenError
from app.models.entities import AnalyticsDailyMetric, EtlRun, User
from app.models.enums import EtlStatus, UserRole


@dataclass(frozen=True)
class MetricFilters:
    start: date
    end: date
    unit_id: int | None = None
    specialty_id: int | None = None
    professional_id: int | None = None

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def previous_period(self) -> MetricFilters:
        previous_end = self.start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=self.days - 1)
        return MetricFilters(
            start=previous_start,
            end=previous_end,
            unit_id=self.unit_id,
            specialty_id=self.specialty_id,
            professional_id=self.professional_id,
        )


def clinic_zone() -> ZoneInfo:
    return ZoneInfo(settings.clinic_timezone)


def local_date(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=clinic_zone())
    return value.astimezone(clinic_zone()).date()


def get_demo_today(db: Session) -> date:
    """Data-âncora do último pipeline bem-sucedido.

    Mantém a demonstração coerente mesmo quando os dados foram gerados em outro dia.
    """
    anchor = db.scalar(
        select(EtlRun.anchor_date)
        .where(EtlRun.status.in_([EtlStatus.SUCCESS, EtlStatus.PARTIAL]))
        .order_by(EtlRun.started_at.desc())
        .limit(1)
    )
    return anchor or date.today()


def data_bounds(db: Session) -> tuple[date | None, date | None]:
    row = db.execute(
        select(func.min(AnalyticsDailyMetric.day), func.max(AnalyticsDailyMetric.day))
    ).one()
    return row[0], row[1]


def scoped_professional_id(user: User | None, requested: int | None) -> int | None:
    """Perfis PROFISSIONAL só enxergam os próprios dados."""
    if user is not None and user.role == UserRole.PROFISSIONAL:
        if user.professional_id is None:
            raise ForbiddenError(
                "Usuário PROFISSIONAL sem vínculo com profissional. Procure o administrador."
            )
        return user.professional_id
    return requested


def ensure_professional_access(user: User | None, professional_id: int | None) -> None:
    if (
        user is not None
        and user.role == UserRole.PROFISSIONAL
        and (professional_id is None or professional_id != user.professional_id)
    ):
        raise ForbiddenError("Você só pode acessar os próprios indicadores.")


def resolve_filters(
    db: Session,
    *,
    start: date | None = None,
    end: date | None = None,
    unit_id: int | None = None,
    specialty_id: int | None = None,
    professional_id: int | None = None,
    default_days: int = 30,
    current_user: User | None = None,
) -> MetricFilters:
    """Resolve o período padrão e aplica o escopo do perfil PROFISSIONAL."""
    today = get_demo_today(db)
    if end is None:
        end = today
    if start is None:
        start = end - timedelta(days=default_days - 1)
    if start > end:
        raise ValueError("A data inicial não pode ser posterior à data final.")
    professional_id = scoped_professional_id(current_user, professional_id)
    return MetricFilters(
        start=start,
        end=end,
        unit_id=unit_id,
        specialty_id=specialty_id,
        professional_id=professional_id,
    )


def describe_period(filters: MetricFilters) -> dict[str, date]:
    return {"start": filters.start, "end": filters.end}


__all__ = [
    "MetricFilters",
    "clinic_zone",
    "data_bounds",
    "describe_period",
    "ensure_professional_access",
    "get_demo_today",
    "local_date",
    "resolve_filters",
    "scoped_professional_id",
]
