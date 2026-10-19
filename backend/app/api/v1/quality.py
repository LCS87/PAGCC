"""Qualidade dos dados e execuções do pipeline."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import QualitySeverity
from app.schemas.dashboard import QualityIssuePage, QualitySummary
from app.schemas.domain import EtlRunOut
from app.services.quality import list_issues, list_runs, quality_summary

router = APIRouter(prefix="/quality", tags=["Qualidade dos dados"])


@router.get("/summary", response_model=QualitySummary, summary="Resumo da última execução")
def summary(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> QualitySummary:
    return quality_summary(db)


@router.get(
    "/issues",
    response_model=QualityIssuePage,
    summary="Registros rejeitados e avisos de qualidade",
)
def issues(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    run_id: int | None = Query(default=None, ge=1),
    severity: QualitySeverity | None = Query(default=None),
    entity: str | None = Query(default=None, max_length=40),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QualityIssuePage:
    return list_issues(
        db,
        page=page,
        page_size=page_size,
        run_id=run_id,
        severity=severity,
        entity=entity,
    )


@router.get(
    "/runs",
    response_model=list[EtlRunOut],
    summary="Histórico de execuções do pipeline",
)
def runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[EtlRunOut]:
    return list_runs(db, limit=limit)
