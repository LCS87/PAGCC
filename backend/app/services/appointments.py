"""Consultas de agenda, listagem e detalhe de atendimentos."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import NotFoundError
from app.models.entities import (
    Appointment,
    AppointmentStatusHistory,
    Attendance,
    Professional,
    Specialty,
    Unit,
)
from app.models.enums import AppointmentStatus
from app.schemas.domain import (
    AppointmentDetail,
    AppointmentOut,
    AttendanceOut,
    PaymentOut,
    TimelineEvent,
)
from app.services.filters import clinic_zone

SORT_FIELDS = {
    "scheduled_start": Appointment.scheduled_start,
    "status": Appointment.status,
    "patient_ref": Appointment.patient_ref,
    "created_at": Appointment.created_at,
}


def local_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    zone = clinic_zone()
    return (
        datetime.combine(start, time.min, tzinfo=zone),
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=zone),
    )


def _status_value(status) -> str:
    return getattr(status, "value", status)


def appointment_to_out(appointment: Appointment) -> AppointmentOut:
    attendance = appointment.attendance
    charged = (
        sum(float(payment.amount_charged) for payment in attendance.payments)
        if attendance
        else 0.0
    )
    wait_seconds = None
    if attendance and attendance.arrived_at:
        delta = (attendance.started_at - attendance.arrived_at).total_seconds()
        if delta >= 0:
            wait_seconds = int(delta)
    return AppointmentOut(
        id=appointment.id,
        external_id=appointment.external_id,
        patient_ref=appointment.patient_ref,
        scheduled_start=appointment.scheduled_start,
        scheduled_end=appointment.scheduled_end,
        status=appointment.status,
        source=appointment.source,
        confirmed_at=appointment.confirmed_at,
        cancellation_actor=appointment.cancellation_actor,
        cancellation_reason=appointment.cancellation_reason,
        professional=appointment.professional,
        unit=appointment.unit,
        specialty=appointment.specialty,
        service_type=appointment.service_type,
        priced_amount=round(charged, 2) if charged else float(appointment.service_type.base_price),
        wait_seconds=wait_seconds,
    )


def _base_query():
    return select(Appointment).options(
        joinedload(Appointment.professional).joinedload(Professional.unit),
        joinedload(Appointment.professional).joinedload(Professional.specialty),
        joinedload(Appointment.unit),
        joinedload(Appointment.specialty),
        joinedload(Appointment.service_type),
        selectinload(Appointment.attendance).selectinload(Attendance.payments),
    )


def _filters(
    start: date | None,
    end: date | None,
    status: list[AppointmentStatus] | None,
    unit_id: int | None,
    specialty_id: int | None,
    professional_id: int | None,
    search: str | None,
) -> list:
    conditions: list = []
    if start is not None or end is not None:
        if start is None:
            start = end
        if end is None:
            end = start
        start_dt, _ = local_bounds(start, end)
        _, end_dt = local_bounds(start, end)
        conditions.extend(
            [Appointment.scheduled_start >= start_dt, Appointment.scheduled_start < end_dt]
        )
    if status:
        conditions.append(Appointment.status.in_(status))
    if unit_id is not None:
        conditions.append(Appointment.unit_id == unit_id)
    if specialty_id is not None:
        conditions.append(Appointment.specialty_id == specialty_id)
    if professional_id is not None:
        conditions.append(Appointment.professional_id == professional_id)
    if search:
        term = f"%{search.strip()}%"
        conditions.append(
            or_(
                Appointment.patient_ref.ilike(term),
                Appointment.external_id.ilike(term),
                Appointment.professional.has(Professional.full_name.ilike(term)),
            )
        )
    return conditions


def list_appointments(
    db: Session,
    *,
    start: date | None = None,
    end: date | None = None,
    status: list[AppointmentStatus] | None = None,
    unit_id: int | None = None,
    specialty_id: int | None = None,
    professional_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
    sort: str = "scheduled_start",
    direction: str = "desc",
) -> tuple[list[AppointmentOut], int]:
    conditions = _filters(
        start, end, status, unit_id, specialty_id, professional_id, search
    )
    total = db.scalar(select(func.count(Appointment.id)).where(*conditions)) or 0

    column = SORT_FIELDS.get(sort, Appointment.scheduled_start)
    ordering = column.desc() if direction.lower() == "desc" else column.asc()

    appointments = (
        db.execute(
            _base_query()
            .where(*conditions)
            .order_by(ordering)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .unique()
        .all()
    )
    return [appointment_to_out(appointment) for appointment in appointments], total


def agenda(
    db: Session,
    *,
    start: date,
    end: date,
    unit_id: int | None = None,
    specialty_id: int | None = None,
    professional_id: int | None = None,
    status: list[AppointmentStatus] | None = None,
) -> list[AppointmentOut]:
    conditions = _filters(
        start, end, status, unit_id, specialty_id, professional_id, None
    )
    appointments = (
        db.execute(
            _base_query()
            .where(*conditions)
            .order_by(Appointment.scheduled_start.asc())
            .limit(3000)
        )
        .scalars()
        .unique()
        .all()
    )
    return [appointment_to_out(appointment) for appointment in appointments]


def get_appointment(db: Session, appointment_id: int) -> AppointmentDetail:
    appointment = db.scalar(
        _base_query()
        .where(Appointment.id == appointment_id)
        .options(selectinload(Appointment.status_history))
    )
    if appointment is None:
        raise NotFoundError("Agendamento", appointment_id)

    attendance = None
    if appointment.attendance:
        payments = [
            PaymentOut(
                id=payment.id,
                amount_charged=float(payment.amount_charged),
                amount_received=float(payment.amount_received),
                refund_amount=float(payment.refund_amount),
                method=payment.method,
                status=payment.status,
                recorded_at=payment.recorded_at,
            )
            for payment in appointment.attendance.payments
        ]
        attendance = AttendanceOut(
            id=appointment.attendance.id,
            external_id=appointment.attendance.external_id,
            arrived_at=appointment.attendance.arrived_at,
            started_at=appointment.attendance.started_at,
            ended_at=appointment.attendance.ended_at,
            status=appointment.attendance.status,
            payments=payments,
        )

    base = appointment_to_out(appointment)
    return AppointmentDetail(
        **base.model_dump(),
        attendance=attendance,
        timeline=[
            TimelineEvent(
                from_status=event.from_status,
                to_status=event.to_status,
                changed_at=event.changed_at,
                reason=event.reason,
            )
            for event in sorted(
                appointment.status_history, key=lambda item: item.changed_at
            )
        ],
        rescheduled_from_id=appointment.rescheduled_from_id,
    )


def find_appointments(
    db: Session, *, start: date, end: date, status: list[AppointmentStatus] | None = None
) -> list[Appointment]:
    start_dt, end_dt = local_bounds(start, end)
    stmt = select(Appointment).where(
        Appointment.scheduled_start >= start_dt, Appointment.scheduled_start < end_dt
    )
    if status:
        stmt = stmt.where(Appointment.status.in_(status))
    return list(db.scalars(stmt))


__all__ = [
    "agenda",
    "appointment_to_out",
    "find_appointments",
    "get_appointment",
    "list_appointments",
    "local_bounds",
    "_status_value",
    "AppointmentStatusHistory",
    "AppointmentStatus",
    "Unit",
    "Specialty",
]
