"""Agenda e atendimentos (somente leitura no MVP)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, pagination
from app.core.errors import AppError
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import AppointmentStatus
from app.schemas.common import Page
from app.schemas.domain import AppointmentDetail, AppointmentOut
from app.services.appointments import agenda as agenda_service
from app.services.appointments import get_appointment, list_appointments
from app.services.filters import (
    ensure_professional_access,
    get_demo_today,
    scoped_professional_id,
)

router = APIRouter(prefix="/appointments", tags=["Agenda"])


@router.get("", response_model=Page[AppointmentOut], summary="Lista paginada de agendamentos")
def appointments(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    status: list[AppointmentStatus] | None = Query(default=None),
    unit_id: int | None = Query(default=None, ge=1),
    specialty_id: int | None = Query(default=None, ge=1),
    professional_id: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None, max_length=80),
    sort: Literal["scheduled_start", "status", "patient_ref", "created_at"] = "scheduled_start",
    direction: Literal["asc", "desc"] = "desc",
    page_params: tuple[int, int] = Depends(pagination),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[AppointmentOut]:
    page, page_size = page_params
    professional_id = scoped_professional_id(user, professional_id)
    if start and end and start > end:
        raise AppError("invalid_period", "A data inicial não pode ser posterior à final.", 422)

    items, total = list_appointments(
        db,
        start=start,
        end=end,
        status=status,
        unit_id=unit_id,
        specialty_id=specialty_id,
        professional_id=professional_id,
        search=search,
        page=page,
        page_size=page_size,
        sort=sort,
        direction=direction,
    )
    pages = (total + page_size - 1) // page_size if total else 0
    return Page(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get(
    "/agenda",
    response_model=list[AppointmentOut],
    summary="Agenda por intervalo de datas (máximo de 62 dias)",
)
def agenda(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    unit_id: int | None = Query(default=None, ge=1),
    specialty_id: int | None = Query(default=None, ge=1),
    professional_id: int | None = Query(default=None, ge=1),
    status: list[AppointmentStatus] | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AppointmentOut]:
    today = get_demo_today(db)
    start = start or today
    end = end or start + timedelta(days=6)
    if start > end:
        raise AppError("invalid_period", "A data inicial não pode ser posterior à final.", 422)
    if (end - start).days > 62:
        raise AppError("range_too_large", "Intervalo máximo para a agenda é de 62 dias.", 422)
    professional_id = scoped_professional_id(user, professional_id)
    return agenda_service(
        db,
        start=start,
        end=end,
        unit_id=unit_id,
        specialty_id=specialty_id,
        professional_id=professional_id,
        status=status,
    )


@router.get(
    "/{appointment_id}",
    response_model=AppointmentDetail,
    summary="Detalhe administrativo do agendamento com linha do tempo",
)
def appointment_detail(
    appointment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AppointmentDetail:
    detail = get_appointment(db, appointment_id)
    ensure_professional_access(user, detail.professional.id)
    return detail
