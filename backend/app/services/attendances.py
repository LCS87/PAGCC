"""Listagem e detalhe de atendimentos administrativos."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.entities import (
    Appointment,
    Attendance,
    PaymentRecord,
    Professional,
    Specialty,
    Unit,
)
from app.schemas.domain import (
    AppointmentOut,
    AttendanceListItem,
    AttendanceOut,
    PaymentOut,
)
from app.services.appointments import _base_query
from app.services.filters import clinic_zone

SORT_FIELDS = {
    "started_at": Attendance.started_at,
    "arrived_at": Attendance.arrived_at,
    "created_at": Attendance.created_at,
}


def _local_bounds(start: date | None, end: date | None):
    if start is None and end is None:
        return None, None
    start = start or end
    end = end or start
    zone = clinic_zone()
    from datetime import datetime, time

    return (
        datetime.combine(start, time.min, tzinfo=zone),
        datetime.combine(end, time.max, tzinfo=zone),
    )


def list_attendances(
    db: Session,
    *,
    start: date | None = None,
    end: date | None = None,
    professional_id: int | None = None,
    unit_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
    sort: str = "started_at",
    direction: str = "desc",
) -> tuple[list[AttendanceListItem], int]:
    start_dt, end_dt = _local_bounds(start, end)
    conditions = []
    if start_dt is not None:
        conditions.extend(
            [Appointment.scheduled_start >= start_dt, Appointment.scheduled_start <= end_dt]
        )
    if professional_id is not None:
        conditions.append(Appointment.professional_id == professional_id)
    if unit_id is not None:
        conditions.append(Appointment.unit_id == unit_id)
    if search:
        term = f"%{search.strip()}%"
        conditions.append(
            Appointment.patient_ref.ilike(term) | Attendance.external_id.ilike(term)
        )

    statement = (
        select(
            Attendance,
            Appointment.patient_ref,
            Appointment.scheduled_start,
            Professional.full_name,
            Specialty.name,
            Unit.name,
            func.coalesce(func.sum(PaymentRecord.amount_charged), 0),
        )
        .select_from(Attendance)
        .join(Appointment, Appointment.id == Attendance.appointment_id)
        .join(Professional, Professional.id == Appointment.professional_id)
        .join(Specialty, Specialty.id == Appointment.specialty_id)
        .join(Unit, Unit.id == Appointment.unit_id)
        .outerjoin(PaymentRecord, PaymentRecord.attendance_id == Attendance.id)
        .where(*conditions)
        .group_by(
            Attendance.id,
            Appointment.patient_ref,
            Appointment.scheduled_start,
            Professional.full_name,
            Specialty.name,
            Unit.name,
        )
    )

    total = db.scalar(
        select(func.count())
        .select_from(Attendance)
        .join(Appointment, Appointment.id == Attendance.appointment_id)
        .where(*conditions)
    ) or 0

    column = SORT_FIELDS.get(sort, Attendance.started_at)
    ordering = column.desc() if direction.lower() == "desc" else column.asc()
    rows = db.execute(
        statement.order_by(ordering).offset((page - 1) * page_size).limit(page_size)
    ).all()

    items = []
    for (
        attendance,
        patient_ref,
        scheduled_start,
        professional_name,
        specialty_name,
        unit_name,
        charged,
    ) in rows:
        wait_seconds = None
        if attendance.arrived_at:
            delta = (attendance.started_at - attendance.arrived_at).total_seconds()
            if delta >= 0:
                wait_seconds = int(delta)
        items.append(
            AttendanceListItem(
                id=attendance.id,
                external_id=attendance.external_id,
                appointment_id=attendance.appointment_id,
                arrived_at=attendance.arrived_at,
                started_at=attendance.started_at,
                ended_at=attendance.ended_at,
                status=attendance.status,
                patient_ref=patient_ref,
                professional_name=professional_name,
                specialty_name=specialty_name,
                unit_name=unit_name,
                scheduled_start=scheduled_start,
                wait_seconds=wait_seconds,
                amount_charged=round(float(charged), 2),
            )
        )
    return items, total


def get_attendance(db: Session, attendance_id: int) -> dict:
    attendance = db.get(Attendance, attendance_id)
    if attendance is None:
        raise NotFoundError("Atendimento", attendance_id)

    appointment = db.scalar(
        _base_query().where(Appointment.id == attendance.appointment_id)
    )
    appointment_out = None
    if appointment is not None:
        from app.services.appointments import appointment_to_out

        appointment_out = appointment_to_out(appointment)

    return {
        "attendance": AttendanceOut(
            id=attendance.id,
            external_id=attendance.external_id,
            arrived_at=attendance.arrived_at,
            started_at=attendance.started_at,
            ended_at=attendance.ended_at,
            status=attendance.status,
            payments=[
                PaymentOut(
                    id=payment.id,
                    amount_charged=float(payment.amount_charged),
                    amount_received=float(payment.amount_received),
                    refund_amount=float(payment.refund_amount),
                    method=payment.method,
                    status=payment.status,
                    recorded_at=payment.recorded_at,
                )
                for payment in attendance.payments
            ],
        ),
        "appointment": appointment_out,
    }


__all__ = ["get_attendance", "list_attendances", "AppointmentOut", "AttendanceOut"]
