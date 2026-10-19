"""Cálculo dos KPIs do dashboard executivo a partir da camada analítica."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import AnalyticsDailyMetric
from app.schemas.dashboard import KpiValue, OverviewResponse, PeriodOut
from app.services.filters import MetricFilters
from app.services.metrics_formulas import (
    MetricTotals,
    derive_metrics,
    percent_change,
)


def _conditions(filters: MetricFilters) -> list:
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
    return conditions


def totals_for(db: Session, filters: MetricFilters) -> MetricTotals:
    columns = (
        func.coalesce(func.sum(AnalyticsDailyMetric.scheduled_count), 0).label("scheduled"),
        func.coalesce(func.sum(AnalyticsDailyMetric.completed_count), 0).label("completed"),
        func.coalesce(func.sum(AnalyticsDailyMetric.no_show_count), 0).label("no_show"),
        func.coalesce(func.sum(AnalyticsDailyMetric.cancelled_patient_count), 0).label(
            "cancelled_patient"
        ),
        func.coalesce(func.sum(AnalyticsDailyMetric.cancelled_clinic_count), 0).label(
            "cancelled_clinic"
        ),
        func.coalesce(func.sum(AnalyticsDailyMetric.rescheduled_count), 0).label("rescheduled"),
        func.coalesce(func.sum(AnalyticsDailyMetric.booked_minutes), 0).label("booked_minutes"),
        func.coalesce(func.sum(AnalyticsDailyMetric.available_minutes), 0).label(
            "available_minutes"
        ),
        func.coalesce(func.sum(AnalyticsDailyMetric.revenue_charged), 0).label(
            "revenue_charged"
        ),
        func.coalesce(func.sum(AnalyticsDailyMetric.revenue_received), 0).label(
            "revenue_received"
        ),
        func.coalesce(func.sum(AnalyticsDailyMetric.wait_seconds_sum), 0).label(
            "wait_seconds_sum"
        ),
        func.coalesce(func.sum(AnalyticsDailyMetric.wait_samples), 0).label("wait_samples"),
    )
    row = db.execute(select(*columns).where(*_conditions(filters))).one()
    return MetricTotals.from_row(row._mapping)


def _kpi(
    key: str,
    label: str,
    value: float | None,
    previous: float | None,
    *,
    unit: str,
    favorable: str,
    formula: str,
    denominator: int | None = None,
    sample_size: int | None = None,
) -> KpiValue:
    return KpiValue(
        key=key,
        label=label,
        value=None if value is None else round(value, 2),
        previous=None if previous is None else round(previous, 2),
        delta_pct=percent_change(value, previous),
        unit=unit,
        favorable=favorable,
        formula=formula,
        denominator=denominator,
        sample_size=sample_size,
    )


def build_overview(db: Session, filters: MetricFilters) -> OverviewResponse:
    current = totals_for(db, filters)
    previous = totals_for(db, filters.previous_period())
    current_metrics = derive_metrics(current)
    previous_metrics = derive_metrics(previous)

    kpis = [
        _kpi(
            "scheduled",
            "Consultas agendadas",
            current.scheduled,
            previous.scheduled,
            unit="count",
            favorable="neutral",
            formula="Contagem de agendamentos com início no período (todos os status, "
            "inclusive cancelados e faltas).",
            sample_size=current.scheduled,
        ),
        _kpi(
            "completed",
            "Consultas realizadas",
            current.completed,
            previous.completed,
            unit="count",
            favorable="up",
            formula="Agendamentos com status CONCLUIDA e atendimento registrado.",
            sample_size=current.completed,
        ),
        _kpi(
            "attendance_rate",
            "Taxa de comparecimento",
            current_metrics.attendance_rate,
            previous_metrics.attendance_rate,
            unit="percent",
            favorable="up",
            formula="Consultas realizadas ÷ agendamentos elegíveis × 100. "
            "Elegíveis = agendamentos − reagendamentos.",
            denominator=current.eligible,
        ),
        _kpi(
            "no_show_rate",
            "Taxa de faltas",
            current_metrics.no_show_rate,
            previous_metrics.no_show_rate,
            unit="percent",
            favorable="down",
            formula="Faltas ÷ agendamentos elegíveis × 100.",
            denominator=current.eligible,
        ),
        _kpi(
            "cancellation_rate",
            "Taxa de cancelamento",
            current_metrics.cancellation_rate,
            previous_metrics.cancellation_rate,
            unit="percent",
            favorable="down",
            formula="(Cancelamentos do paciente + da clínica) ÷ agendamentos elegíveis × 100.",
            denominator=current.eligible,
        ),
        _kpi(
            "occupancy",
            "Ocupação da agenda",
            current_metrics.occupancy_pct,
            previous_metrics.occupancy_pct,
            unit="percent",
            favorable="up",
            formula="Minutos reservados ÷ minutos disponíveis × 100. Reservados = "
            "agendamentos não cancelados nem reagendados.",
            denominator=current.available_minutes,
        ),
        _kpi(
            "revenue",
            "Receita bruta simulada",
            current.revenue_charged,
            previous.revenue_charged,
            unit="currency",
            favorable="up",
            formula="Soma de amount_charged dos atendimentos concluídos no período.",
        ),
        _kpi(
            "revenue_received",
            "Receita recebida simulada",
            current.revenue_received,
            previous.revenue_received,
            unit="currency",
            favorable="up",
            formula="Soma de amount_received − refund_amount dos atendimentos concluídos.",
        ),
        _kpi(
            "ticket",
            "Ticket médio",
            current_metrics.ticket,
            previous_metrics.ticket,
            unit="currency",
            favorable="up",
            formula="Receita bruta ÷ consultas realizadas.",
            denominator=current.completed,
        ),
        _kpi(
            "wait_time",
            "Tempo médio de espera",
            current_metrics.wait_seconds_avg,
            previous_metrics.wait_seconds_avg,
            unit="seconds",
            favorable="down",
            formula="Média de (started_at − arrived_at) dos atendimentos com ambos os horários.",
            sample_size=current.wait_samples,
        ),
        _kpi(
            "reschedule_rate",
            "Taxa de reagendamento",
            current_metrics.reschedule_rate,
            previous_metrics.reschedule_rate,
            unit="percent",
            favorable="down",
            formula="Reagendamentos ÷ total de agendamentos × 100.",
            denominator=current.scheduled,
        ),
    ]

    return OverviewResponse(
        period=PeriodOut(start=filters.start, end=filters.end),
        previous_period=PeriodOut(
            start=filters.previous_period().start, end=filters.previous_period().end
        ),
        kpis=kpis,
        generated_at=datetime.now(UTC),
        demo_mode=True,
    )


__all__ = ["build_overview", "totals_for"]
