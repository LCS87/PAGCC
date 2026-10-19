"""Schemas das entidades de domínio."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AppointmentSource,
    AppointmentStatus,
    AttendanceStatus,
    CancellationActor,
    EtlStatus,
    PaymentMethod,
    PaymentStatus,
    QualitySeverity,
    UserRole,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UnitOut(ORMModel):
    id: int
    code: str
    name: str
    city: str
    is_active: bool


class SpecialtyOut(ORMModel):
    id: int
    code: str
    name: str


class AvailabilityOut(ORMModel):
    weekday: int
    start_time: time
    end_time: time


class ProfessionalOut(ORMModel):
    id: int
    code: str
    full_name: str
    email: str
    is_active: bool
    unit: UnitOut
    specialty: SpecialtyOut


class ProfessionalDetail(ProfessionalOut):
    availabilities: list[AvailabilityOut] = Field(default_factory=list)


class ServiceTypeOut(ORMModel):
    id: int
    code: str
    name: str
    duration_minutes: int
    base_price: float


class PaymentOut(ORMModel):
    id: int
    amount_charged: float
    amount_received: float
    refund_amount: float
    method: PaymentMethod
    status: PaymentStatus
    recorded_at: datetime


class AttendanceOut(ORMModel):
    id: int
    external_id: str
    arrived_at: datetime | None
    started_at: datetime
    ended_at: datetime | None
    status: AttendanceStatus
    payments: list[PaymentOut] = Field(default_factory=list)


class TimelineEvent(ORMModel):
    from_status: AppointmentStatus | None
    to_status: AppointmentStatus
    changed_at: datetime
    reason: str | None


class AppointmentOut(ORMModel):
    id: int
    external_id: str
    patient_ref: str
    scheduled_start: datetime
    scheduled_end: datetime
    status: AppointmentStatus
    source: AppointmentSource
    confirmed_at: datetime | None
    cancellation_actor: CancellationActor | None
    cancellation_reason: str | None
    professional: ProfessionalOut
    unit: UnitOut
    specialty: SpecialtyOut
    service_type: ServiceTypeOut
    priced_amount: float | None = None
    wait_seconds: int | None = None


class AppointmentDetail(AppointmentOut):
    attendance: AttendanceOut | None = None
    timeline: list[TimelineEvent] = Field(default_factory=list)
    rescheduled_from_id: int | None = None


class AttendanceListItem(ORMModel):
    id: int
    external_id: str
    appointment_id: int
    arrived_at: datetime | None
    started_at: datetime
    ended_at: datetime | None
    status: AttendanceStatus
    patient_ref: str
    professional_name: str
    specialty_name: str
    unit_name: str
    scheduled_start: datetime
    wait_seconds: int | None = None
    amount_charged: float = 0.0


class AttendanceDetail(BaseModel):
    attendance: AttendanceOut
    appointment: AppointmentOut | None = None


class AppointmentUpdateStatus(BaseModel):
    status: AppointmentStatus
    reason: str | None = Field(default=None, max_length=160)


class EtlRunOut(ORMModel):
    id: int
    run_id: str
    started_at: datetime
    finished_at: datetime | None
    status: EtlStatus
    source_seed: int
    anchor_date: date
    raw_path: str
    rows_read: int
    rows_inserted: int
    rows_updated: int
    rows_rejected: int
    message: str | None


class QualityIssueOut(ORMModel):
    id: int
    etl_run_id: int
    entity: str
    issue_type: str
    severity: QualitySeverity
    record_ref: str | None
    detail: str
    created_at: datetime


class UserOutAdmin(ORMModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    professional_id: int | None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class ClinicOut(ORMModel):
    id: int
    code: str
    name: str
    timezone: str


def money(value: Decimal | float | None) -> float:
    return float(value or 0)
