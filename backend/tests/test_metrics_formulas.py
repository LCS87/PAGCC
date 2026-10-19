"""Casos conhecidos para as fórmulas das métricas (docs/metrics.md)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.services.metrics_formulas import (
    MetricTotals,
    average,
    derive_metrics,
    minutes_between,
    percent_change,
    percentage,
    safe_div,
)


def test_safe_div_e_percentage():
    assert safe_div(10, 4) == 2.5
    assert safe_div(10, 0) is None
    assert safe_div(10, None) is None
    assert percentage(1, 3) == 33.33
    assert percentage(0, 0) is None


def test_percent_change():
    assert percent_change(120, 100) == 20.0
    assert percent_change(80, 100) == -20.0
    assert percent_change(10, 0) is None
    assert percent_change(None, 10) is None
    assert percent_change(10, None) is None


def test_average_e_minutes_between():
    assert average(3000, 100) == 30.0
    assert average(10, 0) is None
    start = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    assert minutes_between(start, start + timedelta(minutes=30)) == 30
    assert minutes_between(start, start - timedelta(minutes=5)) is None
    assert minutes_between(None, start) is None


def test_metric_totals_eligible_exclui_reagendamentos():
    totals = MetricTotals(scheduled=100, rescheduled=5)
    assert totals.eligible == 95
    assert MetricTotals(scheduled=3, rescheduled=5).eligible == 0


def test_derive_metrics_com_caso_conhecido():
    totals = MetricTotals(
        scheduled=100,
        completed=70,
        no_show=10,
        cancelled_patient=8,
        cancelled_clinic=2,
        rescheduled=5,
        booked_minutes=2000,
        available_minutes=3000,
        revenue_charged=7000.0,
        revenue_received=6500.0,
        wait_seconds_sum=3000,
        wait_samples=100,
    )
    metrics = derive_metrics(totals)

    assert totals.eligible == 95
    assert metrics.attendance_rate == pytest.approx(73.68)
    assert metrics.no_show_rate == pytest.approx(10.53)
    assert metrics.cancellation_rate == pytest.approx(10.53)
    assert metrics.reschedule_rate == pytest.approx(5.0)
    assert metrics.occupancy_pct == pytest.approx(66.67)
    assert metrics.ticket == pytest.approx(100.0)
    assert metrics.wait_seconds_avg == pytest.approx(30.0)


def test_derive_metrics_sem_denominador():
    metrics = derive_metrics(MetricTotals())
    assert metrics.attendance_rate is None
    assert metrics.no_show_rate is None
    assert metrics.occupancy_pct is None
    assert metrics.ticket is None
    assert metrics.wait_seconds_avg is None
