"""Integração do pipeline com o banco: carga, idempotência e analytics."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    AnalyticsDailyMetric,
    Appointment,
    AppointmentStatusHistory,
    Attendance,
    DataQualityIssue,
    EtlRun,
    PaymentRecord,
)
from app.pipeline.loader import run_pipeline


def _count(db: Session, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def test_carga_inicial_grava_contagens(seeded_engine, dataset):
    with Session(seeded_engine) as db:
        run = db.scalar(select(EtlRun).order_by(EtlRun.id.desc()).limit(1))
        assert run is not None
        assert run.rows_rejected == 7
        assert run.rows_inserted > 0
        assert run.status.value == "PARTIAL"

        assert _count(db, Appointment) > 100
        assert _count(db, Attendance) > 50
        assert _count(db, PaymentRecord) == _count(db, Attendance)
        assert _count(db, AppointmentStatusHistory) > 0
        assert _count(db, AnalyticsDailyMetric) > 0
        assert _count(db, DataQualityIssue) == 7


def test_analytics_bate_com_agendamentos(seeded_engine):
    with Session(seeded_engine) as db:
        scheduled = db.scalar(select(func.sum(AnalyticsDailyMetric.scheduled_count)))
        appointments = db.scalar(select(func.count(Appointment.id)))
        assert int(scheduled or 0) == int(appointments or 0)

        completed = db.scalar(select(func.sum(AnalyticsDailyMetric.completed_count)))
        concluded = db.scalar(
            select(func.count(Appointment.id)).where(Appointment.status == "CONCLUIDA")
        )
        assert int(completed or 0) == int(concluded or 0)


def test_reprocessamento_nao_duplica(seeded_engine, dataset):
    with Session(seeded_engine) as db:
        before_appointments = _count(db, Appointment)
        before_analytics = _count(db, AnalyticsDailyMetric)

        result = run_pipeline(
            db,
            raw_dir=dataset["raw_dir"],
            staging_root=dataset["staging_root"],
            seed=dataset["seed"],
            anchor=dataset["anchor"],
        )

        assert result["rows_inserted"] == 0
        assert result["rows_updated"] > 0
        assert result["rows_rejected"] == 7
        assert _count(db, Appointment) == before_appointments
        assert _count(db, AnalyticsDailyMetric) == before_analytics
