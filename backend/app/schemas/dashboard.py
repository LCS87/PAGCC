"""Schemas dos dashboards, analytics e monitoramento."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import Granularity
from app.schemas.domain import (
    AppointmentOut,
    EtlRunOut,
    ProfessionalDetail,
    ProfessionalOut,
    QualityIssueOut,
)


class PeriodOut(BaseModel):
    start: date
    end: date


class KpiValue(BaseModel):
    key: str
    label: str
    value: float | None
    previous: float | None = None
    delta_pct: float | None = None
    unit: str = Field(description="count | percent | currency | seconds")
    favorable: str = Field(default="neutral", description="up | down | neutral")
    formula: str
    denominator: int | None = None
    sample_size: int | None = None


class OverviewResponse(BaseModel):
    period: PeriodOut
    previous_period: PeriodOut
    kpis: list[KpiValue]
    generated_at: datetime
    demo_mode: bool = True


class SeriesPoint(BaseModel):
    bucket: str
    label: str
    scheduled: int
    completed: int
    no_show: int
    cancelled: int
    rescheduled: int = 0
    occupancy_pct: float | None = None
    revenue: float = 0.0
    wait_seconds_avg: float | None = None


class TimeseriesResponse(BaseModel):
    granularity: Granularity
    points: list[SeriesPoint]


class BreakdownItem(BaseModel):
    key: str
    label: str
    scheduled: int
    completed: int
    no_show: int
    cancelled: int
    occupancy_pct: float | None = None
    no_show_rate: float | None = None
    revenue: float = 0.0
    ticket: float | None = None
    share_pct: float | None = None
    extra: dict[str, float | int | str | None] | None = None


class BreakdownResponse(BaseModel):
    dimension: str
    items: list[BreakdownItem]


class OperationalTask(BaseModel):
    id: str
    severity: str
    title: str
    detail: str
    rule: str
    count: int
    due_at: datetime | None = None
    link: str | None = None


class OperationalSummary(BaseModel):
    generated_at: datetime
    tasks: list[OperationalTask]
    counts: dict[str, int]
    next_days: list[date]


class ProfessionalIndicator(BaseModel):
    professional: ProfessionalOut
    scheduled: int
    completed: int
    no_show: int
    cancelled: int
    attendance_rate: float | None
    no_show_rate: float | None
    occupancy_pct: float | None
    revenue: float
    wait_seconds_avg: float | None


class ProfessionalProfile(BaseModel):
    professional: ProfessionalDetail
    indicator: ProfessionalIndicator | None = None
    recent_appointments: list[AppointmentOut] = Field(default_factory=list)


class QualityBreakdownItem(BaseModel):
    key: str
    count: int


class QualitySummary(BaseModel):
    last_run: EtlRunOut | None
    total_runs: int
    issues_by_severity: dict[str, int]
    issues_by_type: list[QualityBreakdownItem]
    total_rows_read: int
    total_rows_rejected: int
    rejected_pct: float
    recent_runs: list[EtlRunOut]


class QualityIssuePage(BaseModel):
    items: list[QualityIssueOut]
    total: int
    page: int
    page_size: int
    pages: int


class SystemStatus(BaseModel):
    app_name: str
    version: str
    environment: str
    timezone: str
    database: str
    demo_mode: bool
    demo_today: date
    pipeline_last_run: EtlRunOut | None
    counts: dict[str, int]


class FilterOptions(BaseModel):
    units: list[dict] = Field(default_factory=list)
    specialties: list[dict] = Field(default_factory=list)
    professionals: list[ProfessionalOut] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    demo_today: date
    min_date: date | None = None
    max_date: date | None = None
    timezone: str
    clinic: dict | None = None
