"""Pendências operacionais e priorização de tarefas com regra explícita."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    AnalyticsDailyMetric,
    Appointment,
    DataQualityIssue,
    EtlRun,
    Professional,
)
from app.models.enums import AppointmentStatus, QualitySeverity
from app.schemas.dashboard import OperationalSummary, OperationalTask
from app.services.filters import clinic_zone, get_demo_today
from app.services.metrics_formulas import percentage


def _now_for_demo(demo_today: date) -> datetime:
    zone = clinic_zone()
    real_now = datetime.now(zone)
    if real_now.date() == demo_today:
        return real_now
    reference_hour = 18 if real_now.date() > demo_today else 8
    return datetime.combine(demo_today, time(reference_hour, 0), tzinfo=zone)


def _count(db: Session, *conditions) -> int:
    return int(db.scalar(select(func.count(Appointment.id)).where(*conditions)) or 0)


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    zone = clinic_zone()
    start = datetime.combine(day, time.min, tzinfo=zone)
    return start, start + timedelta(days=1)


def build_operational_summary(db: Session) -> OperationalSummary:
    demo_today = get_demo_today(db)
    now = _now_for_demo(demo_today)
    zone = clinic_zone()
    today_start, today_end = _day_bounds(demo_today)
    next_7_end = today_start + timedelta(days=8)
    next_48h = now + timedelta(hours=48)
    last_7_start = today_start - timedelta(days=7)

    tasks: list[OperationalTask] = []

    # 1. Atrasados hoje: ainda não iniciados depois do horário previsto.
    late_stmt = select(func.count(Appointment.id), func.min(Appointment.scheduled_start)).where(
        Appointment.scheduled_start >= today_start,
        Appointment.scheduled_start < today_end,
        Appointment.scheduled_start < now,
        Appointment.status.in_([AppointmentStatus.AGENDADA, AppointmentStatus.CONFIRMADA]),
    )
    late_count, late_first = db.execute(late_stmt).one()
    late_count = int(late_count or 0)
    if late_count:
        tasks.append(
            OperationalTask(
                id="late-today",
                severity="critical",
                title=f"{late_count} consulta(s) atrasada(s) hoje",
                detail="Agendamentos do dia que já passaram do horário previsto e seguem "
                "como agendados ou confirmados.",
                rule="scheduled_start < agora E status em (AGENDADA, CONFIRMADA) E data = hoje.",
                count=late_count,
                due_at=late_first,
                link="/agenda",
            )
        )

    # 2. Confirmações pendentes nas próximas 48h.
    unconfirmed_stmt = select(
        func.count(Appointment.id), func.min(Appointment.scheduled_start)
    ).where(
        Appointment.scheduled_start >= now,
        Appointment.scheduled_start < next_48h,
        Appointment.status == AppointmentStatus.AGENDADA,
    )
    unconfirmed_count, unconfirmed_first = db.execute(unconfirmed_stmt).one()
    unconfirmed_count = int(unconfirmed_count or 0)
    if unconfirmed_count:
        tasks.append(
            OperationalTask(
                id="pending-confirmation",
                severity="warning",
                title=f"{unconfirmed_count} consulta(s) sem confirmação em 48h",
                detail=(
                    "Pacientes ainda não confirmaram presença. Priorize contato "
                    "para reduzir faltas."
                ),
                rule="status = AGENDADA E scheduled_start entre agora e agora + 48h.",
                count=unconfirmed_count,
                due_at=unconfirmed_first,
                link="/agenda",
            )
        )

    # 3. Faltas nos últimos 7 dias.
    no_show_count = _count(
        db,
        Appointment.scheduled_start >= last_7_start,
        Appointment.scheduled_start < today_end,
        Appointment.status == AppointmentStatus.FALTA,
    )
    if no_show_count:
        rate_row = db.execute(
            select(
                func.count(Appointment.id),
                func.sum(case((Appointment.status == AppointmentStatus.FALTA, 1), else_=0)),
            ).where(
                Appointment.scheduled_start >= last_7_start,
                Appointment.scheduled_start < today_end,
                Appointment.status != AppointmentStatus.REAGENDADA,
            )
        ).one()
        rate = percentage(int(rate_row[1] or 0), int(rate_row[0] or 0))
        tasks.append(
            OperationalTask(
                id="recent-no-show",
                severity="warning",
                title=f"{no_show_count} falta(s) nos últimos 7 dias",
                detail=f"Taxa de faltas no período: {rate if rate is not None else '—'}%.",
                rule="status = FALTA E scheduled_start nos últimos 7 dias.",
                count=no_show_count,
                due_at=now,
                link="/analytics?dimension=weekday",
            )
        )

    # 4. Cancelamentos pela clínica nos últimos 7 dias (horários liberados).
    clinic_cancel_count = _count(
        db,
        Appointment.scheduled_start >= last_7_start,
        Appointment.scheduled_start < today_end,
        Appointment.status == AppointmentStatus.CANCELADA_CLINICA,
    )
    if clinic_cancel_count:
        tasks.append(
            OperationalTask(
                id="clinic-cancellations",
                severity="info",
                title=f"{clinic_cancel_count} cancelamento(s) pela clínica em 7 dias",
                detail=(
                    "Horários liberados pela clínica podem ser reofertados a "
                    "pacientes em espera."
                ),
                rule="status = CANCELADA_CLINICA E scheduled_start nos últimos 7 dias.",
                count=clinic_cancel_count,
                due_at=now,
                link="/agenda",
            )
        )

    # 5. Profissionais com ocupação baixa nos últimos 30 dias.
    window_start = demo_today - timedelta(days=29)
    rows = db.execute(
        select(
            Professional.full_name,
            func.sum(AnalyticsDailyMetric.booked_minutes),
            func.sum(AnalyticsDailyMetric.available_minutes),
        )
        .join(AnalyticsDailyMetric, AnalyticsDailyMetric.professional_id == Professional.id)
        .where(
            AnalyticsDailyMetric.day >= window_start,
            AnalyticsDailyMetric.day <= demo_today,
        )
        .group_by(Professional.id, Professional.full_name)
        .having(func.sum(AnalyticsDailyMetric.available_minutes) > 0)
    ).all()
    low = []
    for name, booked, available in rows:
        occupancy = percentage(booked or 0, available or 0)
        if occupancy is not None and occupancy < 40:
            low.append((name, occupancy))
    if low:
        low.sort(key=lambda item: item[1])
        names = ", ".join(f"{name} ({value}%)" for name, value in low[:3])
        tasks.append(
            OperationalTask(
                id="low-occupancy",
                severity="info",
                title=f"{len(low)} profissional(is) com ocupação abaixo de 40%",
                detail=f"Ocupação nos últimos 30 dias: {names}.",
                rule="booked_minutes ÷ available_minutes < 40% nos últimos 30 dias.",
                count=len(low),
                due_at=now + timedelta(days=7),
                link="/profissionais",
            )
        )

    # 6. Faixa horária com taxa de faltas acima da média (últimos 30 dias).
    appt_rows = db.execute(
        select(Appointment.scheduled_start, Appointment.status)
        .where(
            Appointment.scheduled_start >= datetime.combine(
                window_start, time.min, tzinfo=zone
            ),
            Appointment.scheduled_start < today_end,
            Appointment.status != AppointmentStatus.REAGENDADA,
        )
    ).all()
    hour_stats: dict[int, list[int]] = {}
    total_eligible = 0
    total_no_show = 0
    for scheduled_start, status in appt_rows:
        hour = scheduled_start.astimezone(zone).hour
        bucket = hour_stats.setdefault(hour, [0, 0])
        bucket[0] += 1
        total_eligible += 1
        if status == AppointmentStatus.FALTA:
            bucket[1] += 1
            total_no_show += 1
    overall_rate = percentage(total_no_show, total_eligible) or 0
    worst = None
    for hour, (eligible, no_shows) in hour_stats.items():
        if eligible < 15:
            continue
        rate = percentage(no_shows, eligible) or 0
        if rate >= overall_rate + 10 and rate >= 20 and (worst is None or rate > worst[1]):
            worst = (hour, rate, eligible)
    if worst:
        hour, rate, eligible = worst
        tasks.append(
            OperationalTask(
                id="peak-no-show",
                severity="warning",
                title=f"Faltas concentradas às {hour:02d}h ({rate}%)",
                detail=f"{eligible} agendamentos na faixa, taxa {rate}% contra média de "
                f"{overall_rate}% nos últimos 30 dias. Não implica causalidade.",
                rule="Faixa com ≥ 15 agendamentos e taxa de faltas ≥ média + 10 p.p. e ≥ 20%.",
                count=eligible,
                due_at=now + timedelta(days=3),
                link="/analytics?dimension=hour",
            )
        )

    # 7. Confirmação registrada sem timestamp (pendência de cadastro).
    missing_confirmation = _count(
        db,
        Appointment.status == AppointmentStatus.CONFIRMADA,
        Appointment.confirmed_at.is_(None),
        Appointment.scheduled_start >= today_start,
        Appointment.scheduled_start < next_7_end,
    )
    if missing_confirmation:
        tasks.append(
            OperationalTask(
                id="missing-confirmation-timestamp",
                severity="info",
                title=f"{missing_confirmation} confirmação(ões) sem data de registro",
                detail=(
                    "Status confirmado, mas sem confirmed_at. Indica "
                    "inconsistência de cadastro."
                ),
                rule="status = CONFIRMADA E confirmed_at IS NULL nos próximos 7 dias.",
                count=missing_confirmation,
                due_at=now + timedelta(days=1),
                link="/qualidade",
            )
        )

    # 8. Erros de qualidade da última execução do pipeline.
    last_run = db.scalar(select(EtlRun).order_by(EtlRun.started_at.desc()).limit(1))
    quality_errors = 0
    if last_run is not None:
        quality_errors = int(
            db.scalar(
                select(func.count(DataQualityIssue.id)).where(
                    DataQualityIssue.etl_run_id == last_run.id,
                    DataQualityIssue.severity == QualitySeverity.ERROR,
                )
            )
            or 0
        )
    if quality_errors:
        tasks.append(
            OperationalTask(
                id="pipeline-quality-errors",
                severity="critical",
                title=f"{quality_errors} registro(s) rejeitado(s) na última carga",
                detail=f"Execução {last_run.run_id} · semente {last_run.source_seed}. "
                "Veja os detalhes na tela de qualidade dos dados.",
                rule="data_quality_issue.severity = ERROR na execução mais recente.",
                count=quality_errors,
                due_at=last_run.finished_at,
                link="/qualidade",
            )
        )

    # 9. Tempo de espera médio elevado nos últimos 7 dias.
    wait_row = db.execute(
        select(
            func.coalesce(func.sum(AnalyticsDailyMetric.wait_seconds_sum), 0),
            func.coalesce(func.sum(AnalyticsDailyMetric.wait_samples), 0),
        ).where(
            AnalyticsDailyMetric.day >= demo_today - timedelta(days=6),
            AnalyticsDailyMetric.day <= demo_today,
        )
    ).one()
    wait_avg_seconds = (
        float(wait_row[0]) / int(wait_row[1]) if int(wait_row[1] or 0) > 0 else None
    )
    if wait_avg_seconds is not None and wait_avg_seconds > 20 * 60:
        tasks.append(
            OperationalTask(
                id="high-wait-time",
                severity="warning",
                title=f"Espera média de {round(wait_avg_seconds / 60)} min nos últimos 7 dias",
                detail="Acima do limite operacional de 20 minutos definido para a demonstração.",
                rule="média(started_at − arrived_at) > 20 min nos últimos 7 dias.",
                count=int(wait_row[1]),
                due_at=now + timedelta(days=2),
                link="/analytics?metric=wait_time",
            )
        )

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    tasks.sort(key=lambda task: (severity_order.get(task.severity, 3), -task.count))

    counts = {
        "today_scheduled": _count(
            db,
            Appointment.scheduled_start >= today_start,
            Appointment.scheduled_start < today_end,
            Appointment.status != AppointmentStatus.REAGENDADA,
        ),
        "today_confirmed": _count(
            db,
            Appointment.scheduled_start >= today_start,
            Appointment.scheduled_start < today_end,
            Appointment.status.in_(
                [
                    AppointmentStatus.CONFIRMADA,
                    AppointmentStatus.CONCLUIDA,
                    AppointmentStatus.EM_ATENDIMENTO,
                ]
            ),
        ),
        "today_completed": _count(
            db,
            Appointment.scheduled_start >= today_start,
            Appointment.scheduled_start < today_end,
            Appointment.status == AppointmentStatus.CONCLUIDA,
        ),
        "pending_confirmation_48h": unconfirmed_count,
        "late_today": late_count,
        "last7_no_show": no_show_count,
        "last7_cancelled_clinic": clinic_cancel_count,
    }

    return OperationalSummary(
        generated_at=datetime.now(zone),
        tasks=tasks,
        counts=counts,
        next_days=[demo_today + timedelta(days=offset) for offset in range(7)],
    )


__all__ = ["build_operational_summary"]
