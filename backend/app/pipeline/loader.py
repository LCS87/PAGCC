"""Pipeline ETL/ELT: raw → staging → curado → analytics, com rastreabilidade.

Cada execução grava um `etl_run` com contagens de lidas, inseridas, atualizadas e
rejeitadas, além dos problemas em `data_quality_issue`. As cargas são idempotentes
por chave natural (código ou `external_id`).
"""

from __future__ import annotations

import csv
import time
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, joinedload

from app.models.entities import (
    AnalyticsDailyMetric,
    Appointment,
    AppointmentStatusHistory,
    Attendance,
    Clinic,
    DataQualityIssue,
    EtlRun,
    PaymentRecord,
    Professional,
    ProfessionalAvailability,
    ServiceType,
    Specialty,
    Unit,
)
from app.models.enums import (
    AppointmentSource,
    AppointmentStatus,
    AttendanceStatus,
    CancellationActor,
    EtlStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.pipeline.quality import StagedDataset, stage_dataset
from app.services.filters import clinic_zone

OCCUPYING_STATUSES = {
    AppointmentStatus.CONCLUIDA,
    AppointmentStatus.FALTA,
    AppointmentStatus.EM_ATENDIMENTO,
    AppointmentStatus.CONFIRMADA,
    AppointmentStatus.AGENDADA,
}


def _insert_statement(db: Session, model):
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        return pg_insert(model)
    if dialect == "sqlite":
        return sqlite_insert(model)
    raise RuntimeError(f"Dialeto não suportado pelo pipeline: {dialect}")


def _upsert(
    db: Session,
    model,
    rows: list[dict],
    key: str = "external_id",
    chunk_size: int = 1000,
) -> tuple[int, int]:
    """Insere/atualiza por chave natural em lotes e devolve (inseridos, atualizados)."""
    if not rows:
        return 0, 0
    key_column = getattr(model, key)
    inserted = 0
    updated = 0

    for start in range(0, len(rows), chunk_size):
        batch = rows[start : start + chunk_size]
        keys = [row[key] for row in batch]
        existing = set(db.scalars(select(key_column).where(key_column.in_(keys))).all())
        inserted += sum(1 for item in keys if item not in existing)
        updated += sum(1 for item in keys if item in existing)

        statement = _insert_statement(db, model)
        update_columns = {
            column: getattr(statement.excluded, column)
            for column in batch[0]
            if column not in {key, "id"}
        }
        statement = statement.values(batch).on_conflict_do_update(
            index_elements=[key], set_=update_columns
        )
        db.execute(statement)
    return inserted, updated


def _upsert_availability(db: Session, rows: list[dict]) -> tuple[int, int]:
    """Upsert pela chave (profissional, dia da semana, início do turno)."""
    if not rows:
        return 0, 0
    existing = {
        (professional_id, weekday, start_time)
        for professional_id, weekday, start_time in db.execute(
            select(
                ProfessionalAvailability.professional_id,
                ProfessionalAvailability.weekday,
                ProfessionalAvailability.start_time,
            )
        ).all()
    }
    inserted = sum(
        1
        for row in rows
        if (row["professional_id"], row["weekday"], row["start_time"]) not in existing
    )
    updated = len(rows) - inserted

    statement = _insert_statement(db, ProfessionalAvailability)
    statement = statement.values(rows).on_conflict_do_update(
        index_elements=["professional_id", "weekday", "start_time"],
        set_={"end_time": statement.excluded.end_time},
    )
    db.execute(statement)
    return inserted, updated


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_staging(staged: StagedDataset, staging_root: Path) -> Path:
    """Materializa a camada staging normalizada em CSV."""
    destination = staging_root
    destination.mkdir(parents=True, exist_ok=True)

    _write_csv(
        destination / "appointments.csv",
        [
            {
                "external_id": row["external_id"],
                "scheduled_start": row["scheduled_start"].isoformat(),
                "scheduled_end": row["scheduled_end"].isoformat(),
                "unit_code": row["unit_code"],
                "specialty_code": row["specialty_code"],
                "professional_code": row["professional_code"],
                "service_code": row["service_code"],
                "patient_ref": row["patient_ref"],
                "status": row["status"],
                "source": row["source"],
                "confirmed_at": row["confirmed_at"].isoformat() if row["confirmed_at"] else "",
                "rescheduled_from_external_id": row["rescheduled_from_external_id"] or "",
            }
            for row in staged.appointments
        ],
        [
            "external_id",
            "scheduled_start",
            "scheduled_end",
            "unit_code",
            "specialty_code",
            "professional_code",
            "service_code",
            "patient_ref",
            "status",
            "source",
            "confirmed_at",
            "rescheduled_from_external_id",
        ],
    )
    _write_csv(
        destination / "attendances.csv",
        [
            {
                "external_id": row["external_id"],
                "appointment_external_id": row["appointment_external_id"],
                "arrived_at": row["arrived_at"].isoformat() if row["arrived_at"] else "",
                "started_at": row["started_at"].isoformat(),
                "ended_at": row["ended_at"].isoformat() if row["ended_at"] else "",
                "status": row["status"],
            }
            for row in staged.attendances
        ],
        [
            "external_id",
            "appointment_external_id",
            "arrived_at",
            "started_at",
            "ended_at",
            "status",
        ],
    )
    _write_csv(
        destination / "payments.csv",
        [
            {
                "external_id": row["external_id"],
                "attendance_external_id": row["attendance_external_id"],
                "amount_charged": f"{row['amount_charged']:.2f}",
                "amount_received": f"{row['amount_received']:.2f}",
                "refund_amount": f"{row['refund_amount']:.2f}",
                "method": row["method"],
                "status": row["status"],
                "recorded_at": row["recorded_at"].isoformat(),
            }
            for row in staged.payments
        ],
        [
            "external_id",
            "attendance_external_id",
            "amount_charged",
            "amount_received",
            "refund_amount",
            "method",
            "status",
            "recorded_at",
        ],
    )
    _write_csv(
        destination / "quality_issues.csv",
        [
            {
                "entity": issue.entity,
                "issue_type": issue.issue_type,
                "severity": issue.severity.value,
                "record_ref": issue.record_ref or "",
                "rejected": issue.rejected,
                "detail": issue.detail,
            }
            for issue in staged.issues
        ],
        ["entity", "issue_type", "severity", "record_ref", "rejected", "detail"],
    )
    _write_csv(
        destination / "availability.csv",
        [
            {
                "professional_code": row["professional_code"],
                "weekday": row["weekday"],
                "start_time": row["start_time"].strftime("%H:%M"),
                "end_time": row["end_time"].strftime("%H:%M"),
            }
            for row in staged.availability
        ],
        ["professional_code", "weekday", "start_time", "end_time"],
    )
    return destination


def _resolve_period(db: Session) -> tuple[date, date]:
    row = db.execute(
        select(func.min(Appointment.scheduled_start), func.max(Appointment.scheduled_start))
    ).one()
    zone = clinic_zone()
    if row[0] is None:
        today = date.today()
        return today, today
    return row[0].astimezone(zone).date(), row[1].astimezone(zone).date()


def rebuild_analytics(db: Session) -> int:
    """Reconstrói a tabela agregada diária a partir da camada curada."""
    db.execute(delete(AnalyticsDailyMetric))
    zone = clinic_zone()

    professionals = db.execute(
        select(Professional)
        .options(joinedload(Professional.availabilities))
        .where(Professional.is_active.is_(True))
    ).scalars().unique().all()

    availability_minutes: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for professional in professionals:
        for window in professional.availabilities:
            start = window.start_time.hour * 60 + window.start_time.minute
            end = window.end_time.hour * 60 + window.end_time.minute
            availability_minutes[professional.id][window.weekday] += max(end - start, 0)

    appointment_rows = db.execute(
        select(
            Appointment.scheduled_start,
            Appointment.status,
            Appointment.unit_id,
            Appointment.specialty_id,
            Appointment.professional_id,
            ServiceType.duration_minutes,
            Attendance.arrived_at,
            Attendance.started_at,
            func.coalesce(func.sum(PaymentRecord.amount_charged), 0),
            func.coalesce(func.sum(PaymentRecord.amount_received), 0),
            func.coalesce(func.sum(PaymentRecord.refund_amount), 0),
        )
        .join(ServiceType, ServiceType.id == Appointment.service_type_id)
        .outerjoin(Attendance, Attendance.appointment_id == Appointment.id)
        .outerjoin(PaymentRecord, PaymentRecord.attendance_id == Attendance.id)
        .group_by(
            Appointment.id,
            Appointment.scheduled_start,
            Appointment.status,
            Appointment.unit_id,
            Appointment.specialty_id,
            Appointment.professional_id,
            ServiceType.duration_minutes,
            Attendance.arrived_at,
            Attendance.started_at,
        )
    ).all()

    aggregates: dict[tuple, dict[str, float]] = {}

    def bucket(day: date, unit_id: int, specialty_id: int, professional_id: int):
        key = (day, unit_id, specialty_id, professional_id)
        return aggregates.setdefault(
            key,
            {
                "scheduled": 0,
                "completed": 0,
                "no_show": 0,
                "cancelled_patient": 0,
                "cancelled_clinic": 0,
                "rescheduled": 0,
                "booked": 0,
                "available": 0,
                "revenue_charged": 0.0,
                "revenue_received": 0.0,
                "wait_sum": 0,
                "wait_samples": 0,
            },
        )

    for row in appointment_rows:
        local_day = row[0].astimezone(zone).date()
        target = bucket(local_day, row[2], row[3], row[4])
        status = row[1]
        target["scheduled"] += 1
        if status == AppointmentStatus.CONCLUIDA:
            target["completed"] += 1
            target["revenue_charged"] += float(row[8])
            target["revenue_received"] += float(row[9]) - float(row[10])
        elif status == AppointmentStatus.FALTA:
            target["no_show"] += 1
        elif status == AppointmentStatus.CANCELADA_PACIENTE:
            target["cancelled_patient"] += 1
        elif status == AppointmentStatus.CANCELADA_CLINICA:
            target["cancelled_clinic"] += 1
        elif status == AppointmentStatus.REAGENDADA:
            target["rescheduled"] += 1
        if status in OCCUPYING_STATUSES:
            target["booked"] += int(row[5])
        if row[6] is not None and row[7] is not None:
            delta = (row[7] - row[6]).total_seconds()
            if delta >= 0:
                target["wait_sum"] += int(delta)
                target["wait_samples"] += 1

    start_day, end_day = _resolve_period(db)
    total_days = (end_day - start_day).days + 1
    for offset in range(total_days):
        current = start_day + timedelta(days=offset)
        for professional in professionals:
            target = bucket(
                current, professional.unit_id, professional.specialty_id, professional.id
            )
            target["available"] += availability_minutes[professional.id].get(
                current.weekday(), 0
            )

    payload = []
    for (day, unit_id, specialty_id, professional_id), values in aggregates.items():
        payload.append(
            {
                "day": day,
                "unit_id": unit_id,
                "specialty_id": specialty_id,
                "professional_id": professional_id,
                "scheduled_count": int(values["scheduled"]),
                "completed_count": int(values["completed"]),
                "no_show_count": int(values["no_show"]),
                "cancelled_patient_count": int(values["cancelled_patient"]),
                "cancelled_clinic_count": int(values["cancelled_clinic"]),
                "rescheduled_count": int(values["rescheduled"]),
                "booked_minutes": int(values["booked"]),
                "available_minutes": int(values["available"]),
                "revenue_charged": Decimal(str(round(values["revenue_charged"], 2))),
                "revenue_received": Decimal(str(round(values["revenue_received"], 2))),
                "wait_seconds_sum": int(values["wait_sum"]),
                "wait_samples": int(values["wait_samples"]),
            }
        )

    if payload:
        statement = _insert_statement(db, AnalyticsDailyMetric)
        update_columns = {
            column: getattr(statement.excluded, column)
            for column in payload[0]
            if column not in {"id"}
        }
        statement = statement.on_conflict_do_update(
            index_elements=["day", "unit_id", "specialty_id", "professional_id"],
            set_=update_columns,
        )
        db.execute(statement, payload)
    return len(payload)


def run_pipeline(
    db: Session,
    *,
    raw_dir: Path,
    staging_root: Path,
    seed: int | None = None,
    anchor: date | None = None,
) -> dict:
    started_at = datetime.now(UTC)
    run = EtlRun(
        run_id=f"etl-{started_at.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}",
        started_at=started_at,
        status=EtlStatus.RUNNING,
        source_seed=seed or 0,
        anchor_date=anchor or date.today(),
        raw_path=str(raw_dir),
        rows_read=0,
        rows_inserted=0,
        rows_updated=0,
        rows_rejected=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        timings: dict[str, float] = {}
        started_clock = time.perf_counter()

        def mark(phase: str) -> None:
            timings[phase] = round(time.perf_counter() - started_clock, 2)

        staged = stage_dataset(raw_dir)
        mark("stage")
        manifest = staged.manifest or {}
        if seed is None:
            seed = int(manifest.get("seed", 0))
        if anchor is None:
            manifest_anchor = manifest.get("anchor_date")
            anchor = date.fromisoformat(manifest_anchor) if manifest_anchor else date.today()
        run.source_seed = seed
        run.anchor_date = anchor
        db.commit()

        write_staging(staged, staging_root / anchor.isoformat())
        mark("staging_files")

        clinic_payload = staged.clinic or {
            "code": "CLINICA-VIDA",
            "name": "Clínica Vida Integrada",
            "timezone": "America/Fortaleza",
        }
        _upsert(
            db,
            Clinic,
            [
                {
                    "code": clinic_payload["code"],
                    "name": clinic_payload["name"],
                    "timezone": clinic_payload.get("timezone", "America/Fortaleza"),
                }
            ],
            key="code",
        )
        clinic = db.scalar(select(Clinic).where(Clinic.code == clinic_payload["code"]))
        assert clinic is not None
        clinic_id = clinic.id

        unit_inserted, unit_updated = _upsert(
            db,
            Unit,
            [
                {
                    "clinic_id": clinic_id,
                    "code": row["code"],
                    "name": row["name"],
                    "city": row["city"],
                    "is_active": True,
                }
                for row in staged.units
            ],
            key="code",
        )
        specialty_inserted, specialty_updated = _upsert(
            db,
            Specialty,
            [{"code": row["code"], "name": row["name"]} for row in staged.specialties],
            key="code",
        )
        service_inserted, service_updated = _upsert(
            db,
            ServiceType,
            [
                {
                    "code": row["code"],
                    "name": row["name"],
                    "duration_minutes": int(row["duration_minutes"]),
                    "base_price": Decimal(str(row["base_price"])),
                }
                for row in staged.service_types
            ],
            key="code",
        )

        unit_ids = dict(db.execute(select(Unit.code, Unit.id)).all())
        specialty_ids = dict(db.execute(select(Specialty.code, Specialty.id)).all())
        service_type_ids = dict(db.execute(select(ServiceType.code, ServiceType.id)).all())

        professional_inserted, professional_updated = _upsert(
            db,
            Professional,
            [
                {
                    "clinic_id": clinic_id,
                    "unit_id": unit_ids[row["unit_code"]],
                    "specialty_id": specialty_ids[row["specialty_code"]],
                    "code": row["code"],
                    "full_name": row["full_name"],
                    "email": row.get("email") or f"{row['code'].lower()}@clinica-vida.example",
                    "is_active": bool(row.get("is_active", True)),
                }
                for row in staged.professionals
            ],
            key="code",
        )
        professional_ids = dict(db.execute(select(Professional.code, Professional.id)).all())
        mark("dimensions")

        availability_rows = [
            {
                "professional_id": professional_ids[row["professional_code"]],
                "weekday": row["weekday"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
            }
            for row in staged.availability
        ]
        availability_inserted, availability_updated = _upsert_availability(
            db, availability_rows
        )

        appointment_rows = [
            {
                "external_id": row["external_id"],
                "clinic_id": clinic_id,
                "unit_id": unit_ids[row["unit_code"]],
                "specialty_id": specialty_ids[row["specialty_code"]],
                "professional_id": professional_ids[row["professional_code"]],
                "service_type_id": service_type_ids[row["service_code"]],
                "patient_ref": row["patient_ref"],
                "scheduled_start": row["scheduled_start"],
                "scheduled_end": row["scheduled_end"],
                "status": AppointmentStatus(row["status"]),
                "source": AppointmentSource(row["source"]),
                "confirmed_at": row["confirmed_at"],
                "cancellation_actor": (
                    CancellationActor(row["cancellation_actor"])
                    if row["cancellation_actor"]
                    else None
                ),
                "cancellation_reason": row["cancellation_reason"],
                "rescheduled_from_id": None,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in staged.appointments
        ]
        appointment_inserted, appointment_updated = _upsert(
            db, Appointment, appointment_rows, key="external_id"
        )
        mark("appointments")

        # Snapshot: remove agendamentos de cargas anteriores (outra âncora).
        # As tabelas filhas têm ON DELETE CASCADE.
        snapshot_prefix = f"APT-{anchor.strftime('%Y%m%d')}-%"
        db.execute(
            delete(Appointment).where(Appointment.external_id.not_like(snapshot_prefix))
        )

        appointment_ids = dict(
            db.execute(select(Appointment.external_id, Appointment.id)).all()
        )
        for row in staged.appointments:
            reference = row.get("rescheduled_from_external_id")
            if reference and reference in appointment_ids:
                db.execute(
                    update(Appointment)
                    .where(Appointment.external_id == row["external_id"])
                    .values(rescheduled_from_id=appointment_ids[reference])
                )

        attendance_rows = [
            {
                "external_id": row["external_id"],
                "appointment_id": appointment_ids[row["appointment_external_id"]],
                "arrived_at": row["arrived_at"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "status": AttendanceStatus(row["status"]),
            }
            for row in staged.attendances
        ]
        attendance_inserted, attendance_updated = _upsert(
            db, Attendance, attendance_rows, key="external_id"
        )
        mark("attendances")

        attendance_ids = dict(
            db.execute(select(Attendance.external_id, Attendance.id)).all()
        )
        payment_rows = [
            {
                "external_id": row["external_id"],
                "attendance_id": attendance_ids[row["attendance_external_id"]],
                "amount_charged": row["amount_charged"],
                "amount_received": row["amount_received"],
                "refund_amount": row["refund_amount"],
                "method": PaymentMethod(row["method"]),
                "status": PaymentStatus(row["status"]),
                "recorded_at": row["recorded_at"],
            }
            for row in staged.payments
        ]
        payment_inserted, payment_updated = _upsert(
            db, PaymentRecord, payment_rows, key="external_id"
        )
        mark("payments")

        history_rows = [
            {
                "external_id": row["external_id"],
                "appointment_id": appointment_ids[row["appointment_external_id"]],
                "from_status": (
                    AppointmentStatus(row["from_status"]) if row["from_status"] else None
                ),
                "to_status": AppointmentStatus(row["to_status"]),
                "changed_at": row["changed_at"],
                "reason": row["reason"],
            }
            for row in staged.history
        ]
        history_inserted, history_updated = _upsert(
            db, AppointmentStatusHistory, history_rows, key="external_id"
        )
        mark("history")

        analytics_rows = rebuild_analytics(db)
        mark("analytics")

        for issue in staged.issues:
            db.add(
                DataQualityIssue(
                    etl_run_id=run.id,
                    entity=issue.entity,
                    issue_type=issue.issue_type,
                    severity=issue.severity,
                    record_ref=issue.record_ref,
                    detail=issue.detail[:500],
                )
            )

        inserted = (
            unit_inserted
            + specialty_inserted
            + service_inserted
            + professional_inserted
            + availability_inserted
            + appointment_inserted
            + attendance_inserted
            + payment_inserted
            + history_inserted
        )
        updated = (
            unit_updated
            + specialty_updated
            + service_updated
            + professional_updated
            + availability_updated
            + appointment_updated
            + attendance_updated
            + payment_updated
            + history_updated
        )
        rejected = sum(1 for issue in staged.issues if issue.rejected)

        run.rows_read = staged.rows_read
        run.rows_inserted = inserted
        run.rows_updated = updated
        run.rows_rejected = rejected
        run.finished_at = datetime.now(UTC)
        run.status = EtlStatus.SUCCESS if rejected == 0 else EtlStatus.PARTIAL
        run.message = (
            f"Pipeline concluído: {staged.rows_read} registros lidos, {inserted} inseridos, "
            f"{updated} atualizados, {rejected} rejeitados. "
            f"Analytics reconstruído com {analytics_rows} linhas agregadas."
        )
        db.commit()
        mark("commit")

        return {
            "run_id": run.run_id,
            "status": run.status.value,
            "anchor_date": anchor.isoformat(),
            "seed": run.source_seed,
            "rows_read": run.rows_read,
            "rows_inserted": inserted,
            "rows_updated": updated,
            "rows_rejected": rejected,
            "analytics_rows": analytics_rows,
            "issues": len(staged.issues),
            "message": run.message,
            "timings_seconds": timings,
        }
    except Exception as exc:
        db.rollback()
        failed = db.get(EtlRun, run.id)
        if failed is not None:
            failed.status = EtlStatus.FAILED
            failed.finished_at = datetime.now(UTC)
            failed.message = f"Falha no pipeline: {exc}"[:2000]
            db.commit()
        raise


__all__ = ["rebuild_analytics", "run_pipeline", "write_staging", "OCCUPYING_STATUSES"]
