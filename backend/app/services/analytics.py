"""Séries temporais, segmentações e exportação CSV (camada analytics)."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    AnalyticsDailyMetric,
    Appointment,
    Attendance,
    PaymentRecord,
    Professional,
    Specialty,
    Unit,
)
from app.models.enums import APPOINTMENT_STATUSES, AppointmentStatus, Granularity
from app.schemas.dashboard import BreakdownItem, BreakdownResponse, SeriesPoint, TimeseriesResponse
from app.services.filters import MetricFilters, clinic_zone, local_date
from app.services.metrics_formulas import percentage

MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
WEEKDAYS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


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


def _appointment_conditions(filters: MetricFilters) -> list:
    zone = clinic_zone()
    start_dt = datetime.combine(filters.start, datetime.min.time(), tzinfo=zone)
    end_dt = datetime.combine(
        filters.end + timedelta(days=1), datetime.min.time(), tzinfo=zone
    )
    conditions = [
        Appointment.scheduled_start >= start_dt,
        Appointment.scheduled_start < end_dt,
    ]
    if filters.unit_id is not None:
        conditions.append(Appointment.unit_id == filters.unit_id)
    if filters.specialty_id is not None:
        conditions.append(Appointment.specialty_id == filters.specialty_id)
    if filters.professional_id is not None:
        conditions.append(Appointment.professional_id == filters.professional_id)
    return conditions


def _bucket(day: date, granularity: Granularity) -> date:
    if granularity == Granularity.WEEK:
        return day - timedelta(days=day.weekday())
    if granularity == Granularity.MONTH:
        return day.replace(day=1)
    return day


def _bucket_label(bucket: date, granularity: Granularity) -> str:
    if granularity == Granularity.MONTH:
        return f"{MONTHS_PT[bucket.month - 1]}/{str(bucket.year)[2:]}"
    if granularity == Granularity.WEEK:
        return f"Sem. {bucket.day:02d}/{bucket.month:02d}"
    return f"{bucket.day:02d}/{bucket.month:02d}"


def timeseries(
    db: Session, filters: MetricFilters, granularity: Granularity = Granularity.DAY
) -> TimeseriesResponse:
    rows = db.execute(
        select(
            AnalyticsDailyMetric.day,
            func.coalesce(func.sum(AnalyticsDailyMetric.scheduled_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.completed_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.no_show_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.cancelled_patient_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.cancelled_clinic_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.rescheduled_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.booked_minutes), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.available_minutes), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.revenue_charged), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.wait_seconds_sum), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.wait_samples), 0),
        )
        .where(*_conditions(filters))
        .group_by(AnalyticsDailyMetric.day)
        .order_by(AnalyticsDailyMetric.day)
    ).all()

    buckets: dict[date, dict[str, float]] = defaultdict(
        lambda: {
            "scheduled": 0,
            "completed": 0,
            "no_show": 0,
            "cancelled": 0,
            "rescheduled": 0,
            "booked": 0,
            "available": 0,
            "revenue": 0.0,
            "wait_sum": 0,
            "wait_samples": 0,
        }
    )
    for row in rows:
        target = buckets[_bucket(row[0], granularity)]
        target["scheduled"] += int(row[1])
        target["completed"] += int(row[2])
        target["no_show"] += int(row[3])
        target["cancelled"] += int(row[4]) + int(row[5])
        target["rescheduled"] += int(row[6])
        target["booked"] += int(row[7])
        target["available"] += int(row[8])
        target["revenue"] += float(row[9])
        target["wait_sum"] += int(row[10])
        target["wait_samples"] += int(row[11])

    points = []
    for bucket_day in sorted(buckets):
        values = buckets[bucket_day]
        occupancy = percentage(values["booked"], values["available"])
        wait_avg = (
            round(values["wait_sum"] / values["wait_samples"], 1)
            if values["wait_samples"]
            else None
        )
        points.append(
            SeriesPoint(
                bucket=bucket_day.isoformat(),
                label=_bucket_label(bucket_day, granularity),
                scheduled=int(values["scheduled"]),
                completed=int(values["completed"]),
                no_show=int(values["no_show"]),
                cancelled=int(values["cancelled"]),
                rescheduled=int(values["rescheduled"]),
                occupancy_pct=occupancy,
                revenue=round(values["revenue"], 2),
                wait_seconds_avg=wait_avg,
            )
        )
    return TimeseriesResponse(granularity=granularity, points=points)


def _daily_breakdown(
    db: Session, filters: MetricFilters, column
) -> dict[int, dict[str, float]]:
    rows = db.execute(
        select(
            column,
            func.coalesce(func.sum(AnalyticsDailyMetric.scheduled_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.completed_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.no_show_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.cancelled_patient_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.cancelled_clinic_count), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.booked_minutes), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.available_minutes), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.revenue_charged), 0),
        )
        .where(*_conditions(filters))
        .group_by(column)
    ).all()

    result: dict[int, dict[str, float]] = {}
    for row in rows:
        result[int(row[0])] = {
            "scheduled": int(row[1]),
            "completed": int(row[2]),
            "no_show": int(row[3]),
            "cancelled": int(row[4]) + int(row[5]),
            "booked": int(row[6]),
            "available": int(row[7]),
            "revenue": float(row[8]),
        }
    return result


def _item(
    key: str,
    label: str,
    values: dict[str, float] | None,
    total_scheduled: int,
    extra: dict | None = None,
) -> BreakdownItem:
    values = values or {
        "scheduled": 0,
        "completed": 0,
        "no_show": 0,
        "cancelled": 0,
        "booked": 0,
        "available": 0,
        "revenue": 0.0,
    }
    scheduled = int(values["scheduled"])
    completed = int(values["completed"])
    return BreakdownItem(
        key=key,
        label=label,
        scheduled=scheduled,
        completed=completed,
        no_show=int(values["no_show"]),
        cancelled=int(values["cancelled"]),
        occupancy_pct=percentage(values["booked"], values["available"]),
        no_show_rate=percentage(values["no_show"], scheduled),
        revenue=round(values["revenue"], 2),
        ticket=round(values["revenue"] / completed, 2) if completed else None,
        share_pct=percentage(scheduled, total_scheduled),
        extra=extra,
    )


def breakdown(
    db: Session, filters: MetricFilters, dimension: str
) -> BreakdownResponse:
    dimension = dimension.lower()
    items: list[BreakdownItem] = []

    if dimension in {"specialty", "professional", "unit"}:
        if dimension == "specialty":
            column = AnalyticsDailyMetric.specialty_id
            names = dict(db.execute(select(Specialty.id, Specialty.name)).all())
        elif dimension == "professional":
            column = AnalyticsDailyMetric.professional_id
            names = dict(db.execute(select(Professional.id, Professional.full_name)).all())
        else:
            column = AnalyticsDailyMetric.unit_id
            names = dict(db.execute(select(Unit.id, Unit.name)).all())

        grouped = _daily_breakdown(db, filters, column)
        total = sum(int(values["scheduled"]) for values in grouped.values())
        for key in sorted(grouped, key=lambda item: str(names.get(item, ""))):
            items.append(_item(str(key), names.get(key, f"#{key}"), grouped[key], total))
        return BreakdownResponse(dimension=dimension, items=items)

    if dimension == "weekday":
        rows = db.execute(
            select(
                AnalyticsDailyMetric.day,
                func.coalesce(func.sum(AnalyticsDailyMetric.scheduled_count), 0),
                func.coalesce(func.sum(AnalyticsDailyMetric.completed_count), 0),
                func.coalesce(func.sum(AnalyticsDailyMetric.no_show_count), 0),
                func.coalesce(func.sum(AnalyticsDailyMetric.cancelled_patient_count), 0),
                func.coalesce(func.sum(AnalyticsDailyMetric.cancelled_clinic_count), 0),
                func.coalesce(func.sum(AnalyticsDailyMetric.booked_minutes), 0),
                func.coalesce(func.sum(AnalyticsDailyMetric.available_minutes), 0),
                func.coalesce(func.sum(AnalyticsDailyMetric.revenue_charged), 0),
            )
            .where(*_conditions(filters))
            .group_by(AnalyticsDailyMetric.day)
        ).all()
        grouped: dict[int, dict[str, float]] = defaultdict(
            lambda: {
                "scheduled": 0,
                "completed": 0,
                "no_show": 0,
                "cancelled": 0,
                "booked": 0,
                "available": 0,
                "revenue": 0.0,
            }
        )
        for row in rows:
            target = grouped[row[0].weekday()]
            target["scheduled"] += int(row[1])
            target["completed"] += int(row[2])
            target["no_show"] += int(row[3])
            target["cancelled"] += int(row[4]) + int(row[5])
            target["booked"] += int(row[6])
            target["available"] += int(row[7])
            target["revenue"] += float(row[8])
        total = sum(int(values["scheduled"]) for values in grouped.values())
        for weekday in range(7):
            items.append(
                _item(str(weekday), WEEKDAYS_PT[weekday], grouped.get(weekday), total)
            )
        return BreakdownResponse(dimension=dimension, items=items)

    if dimension == "hour":
        rows = db.execute(
            select(
                Appointment.id,
                Appointment.scheduled_start,
                Appointment.status,
                func.coalesce(func.sum(PaymentRecord.amount_charged), 0),
            )
            .select_from(Appointment)
            .outerjoin(Attendance, Attendance.appointment_id == Appointment.id)
            .outerjoin(PaymentRecord, PaymentRecord.attendance_id == Attendance.id)
            .where(*_appointment_conditions(filters))
            .group_by(Appointment.id, Appointment.scheduled_start, Appointment.status)
        ).all()

        zone = ZoneInfo(str(clinic_zone()))
        grouped_hours: dict[int, dict[str, float]] = defaultdict(
            lambda: {"scheduled": 0, "completed": 0, "no_show": 0, "cancelled": 0, "revenue": 0.0}
        )
        for row in rows:
            local_hour = row[1].astimezone(zone).hour
            target = grouped_hours[local_hour]
            target["scheduled"] += 1
            status = row[2]
            if status == AppointmentStatus.CONCLUIDA:
                target["completed"] += 1
                target["revenue"] += float(row[3])
            elif status == AppointmentStatus.FALTA:
                target["no_show"] += 1
            elif status in {
                AppointmentStatus.CANCELADA_PACIENTE,
                AppointmentStatus.CANCELADA_CLINICA,
            }:
                target["cancelled"] += 1
        total = sum(int(values["scheduled"]) for values in grouped_hours.values())
        for hour in range(24):
            values = grouped_hours.get(hour)
            if not values:
                continue
            items.append(
                _item(
                    f"{hour:02d}h",
                    f"{hour:02d}h",
                    {
                        **values,
                        "booked": 0,
                        "available": 0,
                    },
                    total,
                )
            )
        return BreakdownResponse(dimension=dimension, items=items)

    if dimension in {"status", "source"}:
        column = Appointment.status if dimension == "status" else Appointment.source
        rows = db.execute(
            select(column, func.count(Appointment.id))
            .where(*_appointment_conditions(filters))
            .group_by(column)
        ).all()
        total = sum(int(row[1]) for row in rows)
        for key, count in sorted(rows, key=lambda row: str(row[0])):
            items.append(
                BreakdownItem(
                    key=str(getattr(key, "value", key)),
                    label=str(getattr(key, "value", key)).replace("_", " ").title(),
                    scheduled=int(count),
                    completed=0,
                    no_show=0,
                    cancelled=0,
                    share_pct=percentage(count, total),
                )
            )
        return BreakdownResponse(dimension=dimension, items=items)

    raise ValueError(
        "Dimensão inválida. Use specialty, professional, unit, weekday, hour, status ou source."
    )


def export_appointments_csv(
    db: Session, filters: MetricFilters, limit: int = 50_000
) -> str:
    rows = db.execute(
        select(
            Appointment.external_id,
            Appointment.scheduled_start,
            Unit.name,
            Specialty.name,
            Professional.full_name,
            Appointment.patient_ref,
            Appointment.status,
            Appointment.source,
            Appointment.scheduled_end,
            func.coalesce(func.sum(PaymentRecord.amount_charged), 0),
            func.coalesce(func.sum(PaymentRecord.amount_received), 0),
        )
        .select_from(Appointment)
        .join(Unit, Unit.id == Appointment.unit_id)
        .join(Specialty, Specialty.id == Appointment.specialty_id)
        .join(Professional, Professional.id == Appointment.professional_id)
        .outerjoin(Attendance, Attendance.appointment_id == Appointment.id)
        .outerjoin(PaymentRecord, PaymentRecord.attendance_id == Attendance.id)
        .where(*_appointment_conditions(filters))
        .group_by(
            Appointment.id,
            Appointment.external_id,
            Appointment.scheduled_start,
            Unit.name,
            Specialty.name,
            Professional.full_name,
            Appointment.patient_ref,
            Appointment.status,
            Appointment.source,
            Appointment.scheduled_end,
        )
        .order_by(Appointment.scheduled_start)
        .limit(limit)
    ).all()

    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(
        [
            "agendamento_id",
            "data_hora_local",
            "unidade",
            "especialidade",
            "profissional",
            "paciente_ref",
            "status",
            "origem",
            "duracao_minutos",
            "valor_cobrado_simulado",
            "valor_recebido_simulado",
        ]
    )
    zone = clinic_zone()
    for row in rows:
        local_start = row[1].astimezone(zone)
        local_end = row[8].astimezone(zone)
        writer.writerow(
            [
                row[0],
                local_start.strftime("%d/%m/%Y %H:%M"),
                row[2],
                row[3],
                row[4],
                row[5],
                getattr(row[6], "value", row[6]),
                getattr(row[7], "value", row[7]),
                int((local_end - local_start).total_seconds() // 60),
                f"{float(row[9]):.2f}".replace(".", ","),
                f"{float(row[10]):.2f}".replace(".", ","),
            ]
        )
    return buffer.getvalue()


__all__ = [
    "APPOINTMENT_STATUSES",
    "breakdown",
    "export_appointments_csv",
    "local_date",
    "timeseries",
]
