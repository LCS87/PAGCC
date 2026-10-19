"""Atendimentos administrativos (sem dados clínicos)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, pagination
from app.db.session import get_db
from app.models.entities import User
from app.schemas.common import Page
from app.schemas.domain import AttendanceDetail, AttendanceListItem
from app.services.attendances import get_attendance, list_attendances
from app.services.filters import ensure_professional_access, scoped_professional_id

router = APIRouter(prefix="/attendances", tags=["Atendimentos"])


@router.get("", response_model=Page[AttendanceListItem], summary="Lista de atendimentos")
def attendances(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    unit_id: int | None = Query(default=None, ge=1),
    professional_id: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None, max_length=80),
    sort: Literal["started_at", "arrived_at", "created_at"] = "started_at",
    direction: Literal["asc", "desc"] = "desc",
    page_params: tuple[int, int] = Depends(pagination),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[AttendanceListItem]:
    page, page_size = page_params
    professional_id = scoped_professional_id(user, professional_id)
    items, total = list_attendances(
        db,
        start=start,
        end=end,
        unit_id=unit_id,
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
    "/{attendance_id}",
    response_model=AttendanceDetail,
    summary="Detalhe do atendimento e do agendamento relacionado",
)
def attendance_detail(
    attendance_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttendanceDetail:
    payload = get_attendance(db, attendance_id)
    appointment = payload["appointment"]
    ensure_professional_access(
        user, appointment.professional.id if appointment is not None else None
    )
    return AttendanceDetail(**payload)
