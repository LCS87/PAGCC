"""Status do sistema, opções de filtro e administração."""

from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import (
    Appointment,
    Attendance,
    Clinic,
    DataQualityIssue,
    EtlRun,
    PaymentRecord,
    Professional,
    Specialty,
    Unit,
    User,
)
from app.models.enums import APPOINTMENT_STATUSES
from app.schemas.dashboard import FilterOptions, SystemStatus
from app.schemas.domain import ClinicOut, EtlRunOut
from app.services.filters import data_bounds, get_demo_today
from app.services.professionals import list_professionals
from app.services.quality import last_run


def filter_options(db: Session) -> FilterOptions:
    units = [
        {"id": unit.id, "code": unit.code, "name": unit.name, "city": unit.city}
        for unit in db.scalars(select(Unit).order_by(Unit.name)).all()
    ]
    specialties = [
        {"id": specialty.id, "code": specialty.code, "name": specialty.name}
        for specialty in db.scalars(select(Specialty).order_by(Specialty.name)).all()
    ]
    clinic = db.scalar(select(Clinic).limit(1))
    min_day, max_day = data_bounds(db)
    return FilterOptions(
        units=units,
        specialties=specialties,
        professionals=list_professionals(db),
        statuses=list(APPOINTMENT_STATUSES),
        demo_today=get_demo_today(db),
        min_date=min_day,
        max_date=max_day,
        timezone=settings.clinic_timezone,
        clinic=ClinicOut.model_validate(clinic).model_dump() if clinic else None,
    )


def system_status(db: Session) -> SystemStatus:
    database = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - apenas diagnóstico
        database = "indisponível"

    counts = {
        "appointments": int(db.scalar(select(func.count(Appointment.id))) or 0),
        "attendances": int(db.scalar(select(func.count(Attendance.id))) or 0),
        "payments": int(db.scalar(select(func.count(PaymentRecord.id))) or 0),
        "professionals": int(db.scalar(select(func.count(Professional.id))) or 0),
        "units": int(db.scalar(select(func.count(Unit.id))) or 0),
        "specialties": int(db.scalar(select(func.count(Specialty.id))) or 0),
        "users": int(db.scalar(select(func.count(User.id))) or 0),
        "quality_issues": int(db.scalar(select(func.count(DataQualityIssue.id))) or 0),
    }
    run = last_run(db)
    return SystemStatus(
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timezone=settings.clinic_timezone,
        database=database,
        demo_mode=True,
        demo_today=get_demo_today(db),
        pipeline_last_run=EtlRunOut.model_validate(run) if run else None,
        counts=counts,
    )


__all__ = ["filter_options", "system_status", "EtlRun", "EtlRunOut"]
