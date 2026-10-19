"""Profissionais, especialidades e indicadores individuais."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import NotFoundError
from app.models.entities import AnalyticsDailyMetric, Professional
from app.schemas.dashboard import ProfessionalIndicator
from app.schemas.domain import ProfessionalDetail
from app.services.filters import MetricFilters
from app.services.metrics_formulas import percentage


def _professional_query():
    return select(Professional).options(
        joinedload(Professional.unit),
        joinedload(Professional.specialty),
        selectinload(Professional.availabilities),
    )


def list_professionals(
    db: Session,
    *,
    unit_id: int | None = None,
    specialty_id: int | None = None,
    active_only: bool = True,
) -> list[ProfessionalDetail]:
    stmt = _professional_query().order_by(Professional.full_name)
    if unit_id is not None:
        stmt = stmt.where(Professional.unit_id == unit_id)
    if specialty_id is not None:
        stmt = stmt.where(Professional.specialty_id == specialty_id)
    if active_only:
        stmt = stmt.where(Professional.is_active.is_(True))
    professionals = db.execute(stmt).scalars().unique().all()
    return [
        ProfessionalDetail.model_validate(professional) for professional in professionals
    ]


def get_professional(db: Session, professional_id: int) -> Professional:
    professional = db.scalar(_professional_query().where(Professional.id == professional_id))
    if professional is None:
        raise NotFoundError("Profissional", professional_id)
    return professional


def professional_indicators(
    db: Session, filters: MetricFilters
) -> list[ProfessionalIndicator]:
    conditions = [
        AnalyticsDailyMetric.day >= filters.start,
        AnalyticsDailyMetric.day <= filters.end,
    ]
    if filters.unit_id is not None:
        conditions.append(AnalyticsDailyMetric.unit_id == filters.unit_id)
    if filters.specialty_id is not None:
        conditions.append(AnalyticsDailyMetric.specialty_id == filters.specialty_id)
    if filters.professional_id is not None:
        conditions.append(AnalyticsDailyMetric.professional_id == filters.professional_id)

    rows = db.execute(
        select(
            AnalyticsDailyMetric.professional_id,
            func.coalesce(func.sum(AnalyticsDailyMetric.scheduled_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.completed_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.no_show_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.cancelled_patient_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.cancelled_clinic_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.booked_minutes), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.available_minutes), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.revenue_charged), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.wait_seconds_sum), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.wait_samples), 0),
        )
        .where(*conditions)
        .group_by(AnalyticsDailyMetric.professional_id)
    ).all()

    professionals = {
        professional.id: professional
        for professional in db.execute(_professional_query()).scalars().unique().all()
    }

    indicators = []
    for row in rows:
        professional = professionals.get(int(row[0]))
        if professional is None:
            continue
        scheduled = int(row[1])
        completed = int(row[2])
        no_show = int(row[3])
        cancelled = int(row[4]) + int(row[5])
        booked = int(row[6])
        available = int(row[7])
        wait_samples = int(row[10])
        indicators.append(
            ProfessionalIndicator(
                professional=professional,
                scheduled=scheduled,
                completed=completed,
                no_show=no_show,
                cancelled=cancelled,
                attendance_rate=percentage(completed, scheduled - cancelled),
                no_show_rate=percentage(no_show, scheduled - cancelled),
                occupancy_pct=percentage(booked, available),
                revenue=round(float(row[8]), 2),
                wait_seconds_avg=(
                    round(int(row[9]) / wait_samples, 1) if wait_samples else None
                ),
            )
        )

    indicators.sort(key=lambda item: item.occupancy_pct or 0, reverse=True)
    return indicators


__all__ = ["get_professional", "list_professionals", "professional_indicators"]
