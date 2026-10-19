"""Monitoramento da qualidade dos dados e das execuções do pipeline."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import DataQualityIssue, EtlRun
from app.models.enums import QualitySeverity
from app.schemas.dashboard import (
    QualityBreakdownItem,
    QualityIssuePage,
    QualitySummary,
)
from app.schemas.domain import EtlRunOut, QualityIssueOut


def last_run(db: Session) -> EtlRun | None:
    return db.scalar(select(EtlRun).order_by(EtlRun.started_at.desc()).limit(1))


def quality_summary(db: Session) -> QualitySummary:
    run = last_run(db)
    total_runs = int(db.scalar(select(func.count(EtlRun.id))) or 0)
    recent = list(
        db.scalars(select(EtlRun).order_by(EtlRun.started_at.desc()).limit(5)).all()
    )

    severity_counts: dict[str, int] = {}
    by_type: list[QualityBreakdownItem] = []
    if run is not None:
        rows = db.execute(
            select(DataQualityIssue.severity, func.count(DataQualityIssue.id))
            .where(DataQualityIssue.etl_run_id == run.id)
            .group_by(DataQualityIssue.severity)
        ).all()
        severity_counts = {
            getattr(severity, "value", str(severity)): int(count) for severity, count in rows
        }
        type_rows = db.execute(
            select(DataQualityIssue.issue_type, func.count(DataQualityIssue.id))
            .where(DataQualityIssue.etl_run_id == run.id)
            .group_by(DataQualityIssue.issue_type)
            .order_by(func.count(DataQualityIssue.id).desc())
            .limit(12)
        ).all()
        by_type = [
            QualityBreakdownItem(key=issue_type, count=int(count))
            for issue_type, count in type_rows
        ]

    rows_read = int(run.rows_read) if run else 0
    rows_rejected = int(run.rows_rejected) if run else 0
    return QualitySummary(
        last_run=EtlRunOut.model_validate(run) if run else None,
        total_runs=total_runs,
        issues_by_severity={
            QualitySeverity.ERROR.value: severity_counts.get(
                QualitySeverity.ERROR.value, 0
            ),
            QualitySeverity.WARNING.value: severity_counts.get(
                QualitySeverity.WARNING.value, 0
            ),
        },
        issues_by_type=by_type,
        total_rows_read=rows_read,
        total_rows_rejected=rows_rejected,
        rejected_pct=round(rows_rejected / rows_read * 100, 4) if rows_read else 0.0,
        recent_runs=[EtlRunOut.model_validate(item) for item in recent],
    )


def list_issues(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    run_id: int | None = None,
    severity: QualitySeverity | None = None,
    entity: str | None = None,
) -> QualityIssuePage:
    conditions = []
    if run_id is not None:
        conditions.append(DataQualityIssue.etl_run_id == run_id)
    if severity is not None:
        conditions.append(DataQualityIssue.severity == severity)
    if entity:
        conditions.append(DataQualityIssue.entity == entity)

    total = int(
        db.scalar(select(func.count(DataQualityIssue.id)).where(*conditions)) or 0
    )
    issues = (
        db.execute(
            select(DataQualityIssue)
            .where(*conditions)
            .order_by(DataQualityIssue.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    pages = (total + page_size - 1) // page_size if total else 0
    return QualityIssuePage(
        items=[QualityIssueOut.model_validate(issue) for issue in issues],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


def list_runs(db: Session, limit: int = 20) -> list[EtlRunOut]:
    runs = db.scalars(
        select(EtlRun).order_by(EtlRun.started_at.desc()).limit(min(limit, 100))
    ).all()
    return [EtlRunOut.model_validate(run) for run in runs]


__all__ = ["last_run", "list_issues", "list_runs", "quality_summary"]
