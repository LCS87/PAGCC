"""Enums de domínio compartilhados por modelos, schemas e pipeline."""

from __future__ import annotations

from enum import StrEnum


class AppointmentStatus(StrEnum):
    AGENDADA = "AGENDADA"
    CONFIRMADA = "CONFIRMADA"
    EM_ATENDIMENTO = "EM_ATENDIMENTO"
    CONCLUIDA = "CONCLUIDA"
    CANCELADA_PACIENTE = "CANCELADA_PACIENTE"
    CANCELADA_CLINICA = "CANCELADA_CLINICA"
    FALTA = "FALTA"
    REAGENDADA = "REAGENDADA"


APPOINTMENT_STATUSES: tuple[str, ...] = tuple(status.value for status in AppointmentStatus)
CANCELLED_STATUSES = {
    AppointmentStatus.CANCELADA_PACIENTE,
    AppointmentStatus.CANCELADA_CLINICA,
}
# Status que ocupam (ou ocuparam) a agenda. Faltas ocupam o horário reservado.
OCCUPYING_STATUSES = {
    AppointmentStatus.CONCLUIDA,
    AppointmentStatus.FALTA,
    AppointmentStatus.EM_ATENDIMENTO,
    AppointmentStatus.CONFIRMADA,
    AppointmentStatus.AGENDADA,
}


class AttendanceStatus(StrEnum):
    CONCLUIDO = "CONCLUIDO"
    EM_ANDAMENTO = "EM_ANDAMENTO"


class PaymentMethod(StrEnum):
    PIX = "PIX"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    DINHEIRO = "DINHEIRO"
    CONVENIO = "CONVENIO"


class PaymentStatus(StrEnum):
    PAGO = "PAGO"
    PENDENTE = "PENDENTE"
    ESTORNADO = "ESTORNADO"


class AppointmentSource(StrEnum):
    TELEFONE = "TELEFONE"
    WHATSAPP = "WHATSAPP"
    BALCAO = "BALCAO"
    PORTAL = "PORTAL"


class CancellationActor(StrEnum):
    PACIENTE = "PACIENTE"
    CLINICA = "CLINICA"


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    GESTOR = "GESTOR"
    COORDENADOR = "COORDENADOR"
    ANALISTA = "ANALISTA"
    RECEPCAO = "RECEPCAO"
    PROFISSIONAL = "PROFISSIONAL"


class EtlStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class QualitySeverity(StrEnum):
    WARNING = "WARNING"
    ERROR = "ERROR"


class Granularity(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class MetricKey(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"
    OCCUPANCY = "occupancy"
    REVENUE = "revenue"
    TICKET = "ticket"
    WAIT_TIME = "wait_time"
    ATTENDANCE_RATE = "attendance_rate"
    NO_SHOW_RATE = "no_show_rate"
    CANCELLATION_RATE = "cancellation_rate"
    RESCHEDULE_RATE = "reschedule_rate"
