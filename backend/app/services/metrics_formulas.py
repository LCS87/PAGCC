"""Funções puras de cálculo das métricas.

Mantidas fora das rotas para serem testáveis com casos conhecidos e reutilizadas
pelo backend e por scripts de validação.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

Number = float | int | Decimal


def safe_div(numerator: Number, denominator: Number | None) -> float | None:
    """Divisão que devolve None quando o denominador é zero/ausente."""
    if denominator is None:
        return None
    try:
        denominator_f = float(denominator)
    except (TypeError, ValueError):
        return None
    if denominator_f == 0:
        return None
    return float(numerator) / denominator_f


def percentage(numerator: Number, denominator: Number | None) -> float | None:
    """Percentual arredondado a duas casas; None se denominador inválido."""
    value = safe_div(numerator, denominator)
    return None if value is None else round(value * 100, 2)


def percent_change(current: Number | None, previous: Number | None) -> float | None:
    """Variação relativa percentual. None se não houver base de comparação."""
    if current is None or previous is None:
        return None
    previous_f = float(previous)
    if previous_f == 0:
        return None
    return round((float(current) - previous_f) / previous_f * 100, 2)


def average(total: Number, samples: Number) -> float | None:
    value = safe_div(total, samples)
    return None if value is None else round(value, 1)


def minutes_between(start, end) -> int | None:
    """Minutos inteiros entre dois instantes; None se a ordem for inválida."""
    if start is None or end is None:
        return None
    delta = (end - start).total_seconds()
    if delta < 0:
        return None
    return int(round(delta / 60))


@dataclass(frozen=True)
class MetricTotals:
    """Totais brutos da camada analítica, sem métricas derivadas."""

    scheduled: int = 0
    completed: int = 0
    no_show: int = 0
    cancelled_patient: int = 0
    cancelled_clinic: int = 0
    rescheduled: int = 0
    booked_minutes: int = 0
    available_minutes: int = 0
    revenue_charged: float = 0.0
    revenue_received: float = 0.0
    wait_seconds_sum: int = 0
    wait_samples: int = 0

    @classmethod
    def from_row(cls, row: Mapping[str, object]) -> MetricTotals:
        def as_int(key: str) -> int:
            value = row.get(key) or 0
            return int(value)

        def as_float(key: str) -> float:
            value = row.get(key) or 0
            return float(value)

        return cls(
            scheduled=as_int("scheduled"),
            completed=as_int("completed"),
            no_show=as_int("no_show"),
            cancelled_patient=as_int("cancelled_patient"),
            cancelled_clinic=as_int("cancelled_clinic"),
            rescheduled=as_int("rescheduled"),
            booked_minutes=as_int("booked_minutes"),
            available_minutes=as_int("available_minutes"),
            revenue_charged=as_float("revenue_charged"),
            revenue_received=as_float("revenue_received"),
            wait_seconds_sum=as_int("wait_seconds_sum"),
            wait_samples=as_int("wait_samples"),
        )

    @property
    def cancelled(self) -> int:
        return self.cancelled_patient + self.cancelled_clinic

    @property
    def eligible(self) -> int:
        """Agendamentos que deveriam acontecer: exclui reagendamentos."""
        return max(self.scheduled - self.rescheduled, 0)


@dataclass(frozen=True)
class DerivedMetrics:
    attendance_rate: float | None
    no_show_rate: float | None
    cancellation_rate: float | None
    reschedule_rate: float | None
    occupancy_pct: float | None
    ticket: float | None
    wait_seconds_avg: float | None


def derive_metrics(totals: MetricTotals) -> DerivedMetrics:
    """Aplica as fórmulas documentadas em docs/metrics.md."""
    eligible = totals.eligible
    return DerivedMetrics(
        attendance_rate=percentage(totals.completed, eligible),
        no_show_rate=percentage(totals.no_show, eligible),
        cancellation_rate=percentage(totals.cancelled, eligible),
        reschedule_rate=percentage(totals.rescheduled, totals.scheduled),
        occupancy_pct=percentage(totals.booked_minutes, totals.available_minutes),
        ticket=(
            round(totals.revenue_charged / totals.completed, 2)
            if totals.completed
            else None
        ),
        wait_seconds_avg=average(totals.wait_seconds_sum, totals.wait_samples),
    )
