"""Modelos relacionais do domínio de clínica ambulatorial.

Convenções:
- Chaves internas inteiras; nenhum dado pessoal real (apenas `patient_ref` fictício).
- Todos os instantes são armazenados com timezone (UTC no banco).
- Agendamento (`appointment`) é separado do atendimento (`attendance`).
- Valores financeiros ficam em `payment_record`, separados do atendimento.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
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


def _enum(enum_cls, name: str, length: int = 32):
    """Enum armazenado como VARCHAR + CHECK (portável e legível)."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda cls: [member.value for member in cls],
        validate_strings=True,
    )


class Clinic(Base, TimestampMixin):
    __tablename__ = "clinic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Fortaleza")

    units: Mapped[list[Unit]] = relationship(back_populates="clinic")


class Unit(Base, TimestampMixin):
    __tablename__ = "unit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinic.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    clinic: Mapped[Clinic] = relationship(back_populates="units")


class Specialty(Base):
    __tablename__ = "specialty"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)


class Professional(Base, TimestampMixin):
    __tablename__ = "professional"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinic.id", ondelete="CASCADE"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id", ondelete="RESTRICT"))
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialty.id", ondelete="RESTRICT"))
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    unit: Mapped[Unit] = relationship()
    specialty: Mapped[Specialty] = relationship()
    availabilities: Mapped[list[ProfessionalAvailability]] = relationship(
        back_populates="professional", cascade="all, delete-orphan"
    )


class ProfessionalAvailability(Base):
    """Janela semanal de disponibilidade; cada linha é um turno."""

    __tablename__ = "professional_availability"
    __table_args__ = (
        UniqueConstraint(
            "professional_id", "weekday", "start_time", name="uq_availability_slot"
        ),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint("end_time > start_time", name="end_after_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professional.id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0=segunda
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    professional: Mapped[Professional] = relationship(back_populates="availabilities")


class ServiceType(Base):
    __tablename__ = "service_type"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)


class Appointment(Base, TimestampMixin):
    __tablename__ = "appointment"
    __table_args__ = (
        CheckConstraint("scheduled_end > scheduled_start", name="end_after_start"),
        Index("ix_appointment_scheduled_start", "scheduled_start"),
        Index("ix_appointment_status_start", "status", "scheduled_start"),
        Index(
            "ix_appointment_filters",
            "unit_id",
            "specialty_id",
            "professional_id",
            "scheduled_start",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinic.id", ondelete="CASCADE"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id", ondelete="RESTRICT"))
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialty.id", ondelete="RESTRICT"))
    professional_id: Mapped[int] = mapped_column(ForeignKey("professional.id", ondelete="RESTRICT"))
    service_type_id: Mapped[int] = mapped_column(
        ForeignKey("service_type.id", ondelete="RESTRICT")
    )
    patient_ref: Mapped[str] = mapped_column(String(24), nullable=False)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        _enum(AppointmentStatus, "appointment_status"), nullable=False, index=True
    )
    source: Mapped[AppointmentSource] = mapped_column(
        _enum(AppointmentSource, "appointment_source"), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_actor: Mapped[CancellationActor | None] = mapped_column(
        _enum(CancellationActor, "cancellation_actor")
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(120))
    rescheduled_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointment.id", ondelete="SET NULL")
    )

    professional: Mapped[Professional] = relationship()
    unit: Mapped[Unit] = relationship()
    specialty: Mapped[Specialty] = relationship()
    service_type: Mapped[ServiceType] = relationship()
    attendance: Mapped[Attendance | None] = relationship(
        back_populates="appointment", uselist=False
    )
    status_history: Mapped[list[AppointmentStatusHistory]] = relationship(
        back_populates="appointment",
        cascade="all, delete-orphan",
        order_by="AppointmentStatusHistory.changed_at",
    )


class AppointmentStatusHistory(Base):
    __tablename__ = "appointment_status_history"
    __table_args__ = (Index("ix_history_appointment_changed", "appointment_id", "changed_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointment.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[AppointmentStatus | None] = mapped_column(
        _enum(AppointmentStatus, "history_from_status")
    )
    to_status: Mapped[AppointmentStatus] = mapped_column(
        _enum(AppointmentStatus, "history_to_status"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(160))

    appointment: Mapped[Appointment] = relationship(back_populates="status_history")


class Attendance(Base, TimestampMixin):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("appointment_id", name="uq_attendance_appointment"),
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="end_after_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointment.id", ondelete="CASCADE"), nullable=False
    )
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[AttendanceStatus] = mapped_column(
        _enum(AttendanceStatus, "attendance_status"), nullable=False
    )

    appointment: Mapped[Appointment] = relationship(back_populates="attendance")
    payments: Mapped[list[PaymentRecord]] = relationship(back_populates="attendance")


class PaymentRecord(Base, TimestampMixin):
    __tablename__ = "payment_record"
    __table_args__ = (
        CheckConstraint("amount_charged >= 0", name="charged_non_negative"),
        CheckConstraint("amount_received >= 0", name="received_non_negative"),
        CheckConstraint("refund_amount >= 0", name="refund_non_negative"),
        Index("ix_payment_recorded_at", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    attendance_id: Mapped[int] = mapped_column(
        ForeignKey("attendance.id", ondelete="CASCADE"), nullable=False
    )
    amount_charged: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amount_received: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    method: Mapped[PaymentMethod] = mapped_column(
        _enum(PaymentMethod, "payment_method"), nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        _enum(PaymentStatus, "payment_status"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    attendance: Mapped[Attendance] = relationship(back_populates="payments")


class User(Base, TimestampMixin):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(_enum(UserRole, "user_role"), nullable=False)
    professional_id: Mapped[int | None] = mapped_column(
        ForeignKey("professional.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    professional: Mapped[Professional | None] = relationship()


class EtlRun(Base):
    __tablename__ = "etl_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[EtlStatus] = mapped_column(_enum(EtlStatus, "etl_status"), nullable=False)
    source_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    anchor_date: Mapped[date] = mapped_column(Date, nullable=False)
    raw_path: Mapped[str] = mapped_column(String(255), nullable=False)
    rows_read: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str | None] = mapped_column(Text)


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issue"
    __table_args__ = (Index("ix_quality_run_severity", "etl_run_id", "severity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    etl_run_id: Mapped[int] = mapped_column(
        ForeignKey("etl_run.id", ondelete="CASCADE"), nullable=False
    )
    entity: Mapped[str] = mapped_column(String(40), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(60), nullable=False)
    severity: Mapped[QualitySeverity] = mapped_column(
        _enum(QualitySeverity, "quality_severity"), nullable=False
    )
    record_ref: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnalyticsDailyMetric(Base):
    """Camada analytics: uma linha por dia × unidade × especialidade × profissional."""

    __tablename__ = "analytics_daily_metric"
    __table_args__ = (
        UniqueConstraint(
            "day", "unit_id", "specialty_id", "professional_id", name="uq_analytics_daily_key"
        ),
        Index("ix_analytics_daily_day", "day"),
        Index(
            "ix_analytics_daily_filters", "day", "unit_id", "specialty_id", "professional_id"
        ),
        CheckConstraint("available_minutes >= 0", name="available_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id", ondelete="CASCADE"), nullable=False)
    specialty_id: Mapped[int] = mapped_column(
        ForeignKey("specialty.id", ondelete="CASCADE"), nullable=False
    )
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professional.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    no_show_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled_patient_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled_clinic_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rescheduled_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    booked_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue_charged: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    revenue_received: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    wait_seconds_sum: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wait_samples: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
