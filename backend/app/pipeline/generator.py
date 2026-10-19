"""Gerador de dados sintéticos determinístico.

Reprodutibilidade: a combinação (seed, âncora) gera exatamente o mesmo conjunto.
A âncora é o "hoje" da demonstração — o pipeline grava essa data em `etl_run`
e a API a utiliza como data de referência.

Nenhum dado pessoal real é utilizado: pacientes são referências fictícias
(`PAC-0001`) e profissionais têm nomes inventados com e-mails `.example`.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from app.core.config import settings
from app.models.enums import (
    AppointmentSource,
    AppointmentStatus,
    AttendanceStatus,
    CancellationActor,
    PaymentMethod,
    PaymentStatus,
)

TIMEZONE = ZoneInfo(settings.clinic_timezone)
SLOT_STEP_MINUTES = 15

WEEKDAY_NAMES = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


@dataclass(frozen=True)
class AvailabilityPattern:
    blocks: dict[int, list[tuple[time, time]]]

    def blocks_for(self, weekday: int) -> list[tuple[time, time]]:
        return self.blocks.get(weekday, [])


def _blocks(*, saturday: bool = False, morning: bool = True, afternoon: bool = True):
    blocks: dict[int, list[tuple[time, time]]] = {}
    for weekday in range(5):
        slots: list[tuple[time, time]] = []
        if morning:
            slots.append((time(8, 0), time(12, 0)))
        afternoon_start = time(14, 0) if morning else time(13, 0)
        afternoon_end = time(18, 0) if morning else time(19, 0)
        if afternoon:
            slots.append((afternoon_start, afternoon_end))
        blocks[weekday] = slots
    if saturday:
        blocks[5] = [(time(8, 0), time(12, 0))]
    return blocks


PATTERNS: dict[str, AvailabilityPattern] = {
    "integral": AvailabilityPattern(_blocks()),
    "integral_sabado": AvailabilityPattern(_blocks(saturday=True)),
    "manha": AvailabilityPattern(_blocks(afternoon=False)),
    "tarde": AvailabilityPattern(_blocks(morning=False, afternoon=True)),
    "alternado": AvailabilityPattern(
        {
            1: [(time(8, 0), time(12, 0))],
            2: [(time(14, 0), time(18, 0))],
            3: [(time(8, 0), time(12, 0))],
            4: [(time(14, 0), time(18, 0))],
        }
    ),
}


@dataclass(frozen=True)
class ClinicSpec:
    code: str = "CLINICA-VIDA"
    name: str = "Clínica Vida Integrada"
    city: str = "Fortaleza"


UNITS = [
    ("UN-ALDEOTA", "Unidade Aldeota", "Fortaleza"),
    ("UN-MEIRELES", "Unidade Meireles", "Fortaleza"),
    ("UN-EUSEBIO", "Unidade Eusébio", "Eusébio"),
]

SPECIALTIES = [
    ("CLM", "Clínica Médica"),
    ("CAR", "Cardiologia"),
    ("DER", "Dermatologia"),
    ("ORT", "Ortopedia"),
    ("PED", "Pediatria"),
    ("GIN", "Ginecologia"),
    ("PSI", "Psicologia"),
    ("NUT", "Nutrição"),
]

SERVICE_TYPES = [
    ("RET30", "Consulta de retorno", 30, Decimal("180.00")),
    ("CONS45", "Consulta eletiva", 45, Decimal("260.00")),
    ("CONS60", "Consulta inicial", 60, Decimal("350.00")),
    ("AVAL90", "Avaliação multiprofissional", 90, Decimal("480.00")),
]

SERVICES_BY_SPECIALTY: dict[str, list[str]] = {
    "CLM": ["RET30", "CONS45", "CONS60"],
    "CAR": ["RET30", "CONS45", "CONS60"],
    "DER": ["RET30", "CONS45", "CONS60"],
    "ORT": ["CONS45", "CONS60", "AVAL90"],
    "PED": ["RET30", "CONS45", "CONS60"],
    "GIN": ["RET30", "CONS45", "CONS60"],
    "PSI": ["CONS60", "AVAL90"],
    "NUT": ["RET30", "CONS45", "CONS60"],
}

PROFESSIONALS: list[dict] = [
    {
        "code": "PRO-001",
        "name": "Dra. Ana Beatriz Lima",
        "specialty": "CLM",
        "unit": "UN-ALDEOTA",
        "pattern": "integral",
        "demand": 1.05,
    },
    {
        "code": "PRO-002",
        "name": "Dr. Carlos Eduardo Souza",
        "specialty": "CAR",
        "unit": "UN-ALDEOTA",
        "pattern": "integral_sabado",
        "demand": 1.10,
    },
    {
        "code": "PRO-003",
        "name": "Dra. Mariana Alves",
        "specialty": "DER",
        "unit": "UN-ALDEOTA",
        "pattern": "manha",
        "demand": 1.12,
    },
    {
        "code": "PRO-004",
        "name": "Dr. Rafael Nogueira",
        "specialty": "ORT",
        "unit": "UN-MEIRELES",
        "pattern": "integral",
        "demand": 0.95,
    },
    {
        "code": "PRO-005",
        "name": "Dra. Juliana Castro",
        "specialty": "PED",
        "unit": "UN-MEIRELES",
        "pattern": "tarde",
        "demand": 1.00,
    },
    {
        "code": "PRO-006",
        "name": "Dra. Fernanda Ribeiro",
        "specialty": "GIN",
        "unit": "UN-MEIRELES",
        "pattern": "integral",
        "demand": 0.92,
    },
    {
        "code": "PRO-007",
        "name": "Dr. Paulo Henrique Matos",
        "specialty": "PSI",
        "unit": "UN-ALDEOTA",
        "pattern": "tarde",
        "demand": 0.85,
    },
    {
        "code": "PRO-008",
        "name": "Dra. Camila Freitas",
        "specialty": "NUT",
        "unit": "UN-EUSEBIO",
        "pattern": "manha",
        "demand": 0.80,
    },
    {
        "code": "PRO-009",
        "name": "Dr. Bruno Carvalho",
        "specialty": "CLM",
        "unit": "UN-EUSEBIO",
        "pattern": "tarde",
        "demand": 0.90,
    },
    {
        "code": "PRO-010",
        "name": "Dra. Larissa Mendes",
        "specialty": "DER",
        "unit": "UN-MEIRELES",
        "pattern": "integral_sabado",
        "demand": 1.08,
    },
    {
        "code": "PRO-011",
        "name": "Dr. Thiago Barbosa",
        "specialty": "CAR",
        "unit": "UN-EUSEBIO",
        "pattern": "manha",
        "demand": 1.00,
    },
    {
        "code": "PRO-012",
        "name": "Dra. Renata Lopes",
        "specialty": "PSI",
        "unit": "UN-EUSEBIO",
        "pattern": "integral",
        "demand": 0.78,
    },
]

PATIENT_POOL = 420
REGULAR_PATIENTS = 180

SOURCES = [
    (AppointmentSource.TELEFONE, 0.30),
    (AppointmentSource.WHATSAPP, 0.35),
    (AppointmentSource.BALCAO, 0.20),
    (AppointmentSource.PORTAL, 0.15),
]

PATIENT_CANCEL_REASONS = [
    "Problema pessoal",
    "Esqueceu o horário",
    "Sem transporte",
    "Conflito de trabalho",
    "Viagem",
]

CLINIC_CANCEL_REASONS = [
    "Profissional indisponível",
    "Manutenção da unidade",
    "Feriado interno",
    "Reorganização da agenda",
]

PAYMENT_METHODS = [
    (PaymentMethod.PIX, 0.36),
    (PaymentMethod.CARTAO_CREDITO, 0.30),
    (PaymentMethod.CARTAO_DEBITO, 0.16),
    (PaymentMethod.DINHEIRO, 0.10),
    (PaymentMethod.CONVENIO, 0.08),
]


@dataclass
class GenerationResult:
    raw_dir: Path
    anchor: date
    seed: int
    counts: dict[str, int]
    checksums: dict[str, str] = field(default_factory=dict)
    invalid_injected: dict[str, int] = field(default_factory=dict)


def resolve_anchor(anchor: date | None = None) -> date:
    if anchor is not None:
        return anchor
    if settings.etl_anchor_date:
        return date.fromisoformat(settings.etl_anchor_date)
    return datetime.now(TIMEZONE).date()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _weighted_choice(rng: random.Random, options: list[tuple[object, float]]):
    roll = rng.random()
    cumulative = 0.0
    for value, weight in options:
        cumulative += weight
        if roll <= cumulative:
            return value
    return options[-1][0]


def _pick_patient(rng: random.Random) -> str:
    if rng.random() < 0.55:
        number = rng.randint(1, REGULAR_PATIENTS)
    else:
        number = rng.randint(REGULAR_PATIENTS + 1, PATIENT_POOL)
    return f"PAC-{number:04d}"


def _pick_service(rng: random.Random, specialty: str) -> tuple[str, int, Decimal]:
    codes = SERVICES_BY_SPECIALTY[specialty]
    code = rng.choice(codes)
    spec = next(item for item in SERVICE_TYPES if item[0] == code)
    return spec[0], spec[2], spec[3]


def _status_for_historical(rng: random.Random, day: date, hour: int) -> AppointmentStatus:
    no_show = 0.07
    if day.weekday() == 0 and hour <= 9:
        no_show += 0.07
    if day.weekday() == 4 and hour >= 16:
        no_show += 0.05
    if day.weekday() == 5:
        no_show += 0.03
    cancel_patient = 0.055
    cancel_clinic = 0.02
    rescheduled = 0.025
    roll = rng.random()
    if roll < no_show:
        return AppointmentStatus.FALTA
    roll -= no_show
    if roll < cancel_patient:
        return AppointmentStatus.CANCELADA_PACIENTE
    roll -= cancel_patient
    if roll < cancel_clinic:
        return AppointmentStatus.CANCELADA_CLINICA
    roll -= cancel_clinic
    if roll < rescheduled:
        return AppointmentStatus.REAGENDADA
    return AppointmentStatus.CONCLUIDA


def _status_for_future(rng: random.Random, day: date, anchor: date) -> AppointmentStatus:
    roll = rng.random()
    if day == anchor:
        if roll < 0.55:
            return AppointmentStatus.CONFIRMADA
        if roll < 0.88:
            return AppointmentStatus.AGENDADA
        if roll < 0.95:
            return AppointmentStatus.CANCELADA_PACIENTE
        return AppointmentStatus.CANCELADA_CLINICA
    if roll < 0.60:
        return AppointmentStatus.CONFIRMADA
    if roll < 0.92:
        return AppointmentStatus.AGENDADA
    if roll < 0.97:
        return AppointmentStatus.CANCELADA_PACIENTE
    return AppointmentStatus.CANCELADA_CLINICA


def _fill_probability(rng: random.Random, day: date, demand: float) -> float:
    base = 0.76 * demand
    if day.weekday() == 0:
        base += 0.06
    elif day.weekday() == 4:
        base -= 0.10
    elif day.weekday() == 5:
        base -= 0.22
    month = day.month
    if month in (1, 7):
        base -= 0.06
    elif month in (3, 8):
        base += 0.04
    return max(0.30, min(0.96, base))


class _Builder:
    def __init__(self, rng: random.Random, anchor: date) -> None:
        self.rng = rng
        self.anchor = anchor
        self.appointments: list[dict] = []
        self.attendances: list[dict] = []
        self.payments: list[dict] = []
        self.history: list[dict] = []
        self.occupied: set[tuple[str, str]] = set()
        self._appointment_seq = 0
        self._attendance_seq = 0
        self._payment_seq = 0
        self._history_seq = 0

    # ------------------------------------------------------------------ ids
    def _prefix(self, kind: str) -> str:
        return f"{kind}-{self.anchor.strftime('%Y%m%d')}"

    def _next_appointment_id(self) -> str:
        self._appointment_seq += 1
        return f"{self._prefix('APT')}-{self._appointment_seq:06d}"

    def _next_attendance_id(self) -> str:
        self._attendance_seq += 1
        return f"{self._prefix('ATT')}-{self._attendance_seq:06d}"

    def _next_payment_id(self) -> str:
        self._payment_seq += 1
        return f"{self._prefix('PAY')}-{self._payment_seq:06d}"

    def _next_history_id(self) -> str:
        self._history_seq += 1
        return f"{self._prefix('HIS')}-{self._history_seq:06d}"

    # -------------------------------------------------------------- helpers
    def _slot_key(self, professional_code: str, moment: datetime) -> tuple[str, str]:
        return professional_code, moment.isoformat()

    def _is_free(self, professional_code: str, start: datetime, duration: int) -> bool:
        cursor = start
        end = start + timedelta(minutes=duration)
        while cursor < end:
            if self._slot_key(professional_code, cursor) in self.occupied:
                return False
            cursor += timedelta(minutes=SLOT_STEP_MINUTES)
        return True

    def _mark(self, professional_code: str, start: datetime, duration: int) -> None:
        cursor = start
        end = start + timedelta(minutes=duration)
        while cursor < end:
            self.occupied.add(self._slot_key(professional_code, cursor))
            cursor += timedelta(minutes=SLOT_STEP_MINUTES)

    # ------------------------------------------------------------ generation
    def add_appointment(
        self,
        *,
        professional: dict,
        start: datetime,
        duration: int,
        service_code: str,
        price: Decimal,
        status: AppointmentStatus,
        rescheduled_from: str | None = None,
        forced_patient: str | None = None,
    ) -> dict:
        rng = self.rng
        end = start + timedelta(minutes=duration)
        external_id = self._next_appointment_id()
        created_at = start - timedelta(days=rng.randint(2, 40), hours=rng.randint(0, 8))
        if created_at > start:
            created_at = start - timedelta(hours=2)
        if created_at.date() < self.anchor - relativedelta(months=20):
            created_at = start - timedelta(days=rng.randint(2, 10))

        confirmed_at = None
        if status in {
            AppointmentStatus.CONCLUIDA,
            AppointmentStatus.FALTA,
            AppointmentStatus.CONFIRMADA,
            AppointmentStatus.EM_ATENDIMENTO,
        }:
            if rng.random() < 0.85:
                confirmed_at = created_at + timedelta(
                    hours=rng.randint(2, 48), minutes=rng.randint(0, 59)
                )
                if confirmed_at >= start:
                    confirmed_at = start - timedelta(hours=rng.randint(1, 24))
        elif status == AppointmentStatus.CANCELADA_PACIENTE and rng.random() < 0.4:
            confirmed_at = created_at + timedelta(hours=rng.randint(1, 24))

        cancellation_actor = None
        cancellation_reason = None
        cancelled_at = None
        if status == AppointmentStatus.CANCELADA_PACIENTE:
            cancellation_actor = CancellationActor.PACIENTE
            cancellation_reason = rng.choice(PATIENT_CANCEL_REASONS)
            cancelled_at = start - timedelta(hours=rng.randint(1, 96))
        elif status == AppointmentStatus.CANCELADA_CLINICA:
            cancellation_actor = CancellationActor.CLINICA
            cancellation_reason = rng.choice(CLINIC_CANCEL_REASONS)
            cancelled_at = start - timedelta(hours=rng.randint(2, 120))

        source = _weighted_choice(rng, SOURCES)
        patient_ref = forced_patient or _pick_patient(rng)

        appointment = {
            "external_id": external_id,
            "clinic_code": ClinicSpec.code,
            "unit_code": professional["unit"],
            "specialty_code": professional["specialty"],
            "professional_code": professional["code"],
            "service_code": service_code,
            "patient_ref": patient_ref,
            "scheduled_start": _iso(start),
            "scheduled_end": _iso(end),
            "status": status.value,
            "source": source.value,
            "confirmed_at": _iso(confirmed_at),
            "cancellation_actor": cancellation_actor.value if cancellation_actor else None,
            "cancellation_reason": cancellation_reason,
            "rescheduled_from_external_id": rescheduled_from,
            "created_at": _iso(created_at),
            "updated_at": _iso(end),
        }
        self.appointments.append(appointment)
        self._mark(professional["code"], start, duration)

        attendance = None
        if status == AppointmentStatus.CONCLUIDA:
            attendance = self._add_attendance(appointment, start, duration, price)

        self._add_history(
            appointment,
            created_at,
            end,
            status,
            confirmed_at=confirmed_at,
            cancelled_at=cancelled_at,
            attendance=attendance,
        )
        return appointment

    def _add_attendance(
        self, appointment: dict, start: datetime, duration: int, price: Decimal
    ) -> dict:
        rng = self.rng
        arrived_at = None if rng.random() < 0.2 else start - timedelta(minutes=rng.randint(2, 30))
        started_at = start + timedelta(minutes=rng.randint(0, 34))
        ended_at = started_at + timedelta(
            minutes=duration + rng.randint(-5, 12)
        )
        attendance = {
            "external_id": self._next_attendance_id(),
            "appointment_external_id": appointment["external_id"],
            "arrived_at": _iso(arrived_at),
            "started_at": _iso(started_at),
            "ended_at": _iso(ended_at),
            "status": AttendanceStatus.CONCLUIDO.value,
        }
        self.attendances.append(attendance)

        discount = rng.choices([0, 0.1, 0.2], weights=[70, 22, 8])[0]
        charged = (price * (Decimal("1") - Decimal(str(discount)))).quantize(Decimal("0.01"))
        payment_status = rng.choices(
            [PaymentStatus.PAGO, PaymentStatus.PENDENTE, PaymentStatus.ESTORNADO],
            weights=[84, 12, 4],
        )[0]
        method = _weighted_choice(rng, PAYMENT_METHODS)
        if (
            method == PaymentMethod.CONVENIO
            and payment_status == PaymentStatus.PAGO
            and rng.random() < 0.5
        ):
            payment_status = PaymentStatus.PENDENTE

        if payment_status == PaymentStatus.PAGO:
            received = charged
            refund = Decimal("0.00")
        elif payment_status == PaymentStatus.ESTORNADO:
            # O valor foi recebido e depois estornado: receita líquida zero.
            received = charged
            refund = charged
        else:
            received = Decimal("0.00")
            refund = Decimal("0.00")

        payment = {
            "external_id": self._next_payment_id(),
            "attendance_external_id": attendance["external_id"],
            "amount_charged": f"{charged:.2f}",
            "amount_received": f"{received:.2f}",
            "refund_amount": f"{refund:.2f}",
            "method": method.value,
            "status": payment_status.value,
            "recorded_at": _iso(ended_at + timedelta(minutes=rng.randint(0, 45))),
        }
        self.payments.append(payment)
        return attendance

    def _add_history(
        self,
        appointment: dict,
        created_at: datetime,
        end: datetime,
        status: AppointmentStatus,
        *,
        confirmed_at: datetime | None,
        cancelled_at: datetime | None,
        attendance: dict | None,
    ) -> None:
        events: list[tuple[str | None, str, datetime, str | None]] = [
            (None, AppointmentStatus.AGENDADA.value, created_at, "Agendamento criado")
        ]
        if confirmed_at is not None:
            events.append(
                (
                    AppointmentStatus.AGENDADA.value,
                    AppointmentStatus.CONFIRMADA.value,
                    confirmed_at,
                    "Confirmação registrada",
                )
            )
        if status == AppointmentStatus.CONCLUIDA and attendance is not None:
            started = datetime.fromisoformat(attendance["started_at"])
            ended = datetime.fromisoformat(attendance["ended_at"])
            events.append(
                (
                    AppointmentStatus.CONFIRMADA.value,
                    AppointmentStatus.EM_ATENDIMENTO.value,
                    started,
                    "Check-in realizado",
                )
            )
            events.append(
                (
                    AppointmentStatus.EM_ATENDIMENTO.value,
                    AppointmentStatus.CONCLUIDA.value,
                    ended,
                    "Atendimento concluído",
                )
            )
        elif status in {
            AppointmentStatus.FALTA,
            AppointmentStatus.CANCELADA_PACIENTE,
            AppointmentStatus.CANCELADA_CLINICA,
            AppointmentStatus.REAGENDADA,
        }:
            when = cancelled_at or end
            events.append(
                (
                    AppointmentStatus.CONFIRMADA.value
                    if confirmed_at
                    else AppointmentStatus.AGENDADA.value,
                    status.value,
                    when,
                    appointment.get("cancellation_reason") or "Status atualizado",
                )
            )

        for from_status, to_status, moment, reason in events:
            self.history.append(
                {
                    "external_id": self._next_history_id(),
                    "appointment_external_id": appointment["external_id"],
                    "from_status": from_status,
                    "to_status": to_status,
                    "changed_at": _iso(moment),
                    "reason": reason,
                }
            )

    def try_add_replacement(
        self, original: dict, professional: dict, duration: int, start: datetime
    ):
        rng = self.rng
        for offset in range(1, 22):
            day = start.date() + timedelta(days=offset)
            if day.weekday() >= 6:
                continue
            blocks = PATTERNS[professional["pattern"]].blocks_for(day.weekday())
            for block_start, block_end in blocks:
                cursor = datetime.combine(day, block_start, tzinfo=TIMEZONE)
                limit = datetime.combine(day, block_end, tzinfo=TIMEZONE)
                while cursor + timedelta(minutes=duration) <= limit:
                    if self._is_free(professional["code"], cursor, duration):
                        status = (
                            _status_for_historical(rng, day, cursor.hour)
                            if day <= self.anchor
                            else _status_for_future(rng, day, self.anchor)
                        )
                        if status == AppointmentStatus.REAGENDADA:
                            status = AppointmentStatus.CONCLUIDA
                        service = next(
                            item for item in SERVICE_TYPES if item[0] == original["service_code"]
                        )
                        return self.add_appointment(
                            professional=professional,
                            start=cursor,
                            duration=duration,
                            service_code=original["service_code"],
                            price=service[3],
                            status=status,
                            rescheduled_from=original["external_id"],
                            forced_patient=original["patient_ref"],
                        )
                    cursor += timedelta(minutes=SLOT_STEP_MINUTES)
        return None


def _add_invalid_records(
    appointments: list[dict],
    attendances: list[dict],
    payments: list[dict],
    history: list[dict],
) -> dict[str, int]:
    """Injeta problemas controlados para demonstrar a rejeição na qualidade."""
    injected = {
        "invalid_status": 0,
        "invalid_datetime": 0,
        "end_before_start": 0,
        "missing_professional": 0,
        "duplicate_external_id": 0,
        "negative_amount": 0,
        "orphan_attendance": 0,
    }
    source = appointments[0]
    i = 1

    bad = dict(source)
    bad["external_id"] = f"APT-BAD{i:03d}"
    bad["status"] = "PENDENTE_CONFIRMACAO"
    appointments.append(bad)
    injected["invalid_status"] += 1
    i += 1

    bad = dict(appointments[0])
    bad["external_id"] = f"APT-BAD{i:03d}"
    bad["scheduled_start"] = "2026-13-45T10:00:00-03:00"
    appointments.append(bad)
    injected["invalid_datetime"] += 1
    i += 1

    bad = dict(appointments[0])
    bad["external_id"] = f"APT-BAD{i:03d}"
    bad["scheduled_end"] = bad["scheduled_start"]
    appointments.append(bad)
    injected["end_before_start"] += 1
    i += 1

    bad = dict(appointments[0])
    bad["external_id"] = f"APT-BAD{i:03d}"
    bad["professional_code"] = ""
    appointments.append(bad)
    injected["missing_professional"] += 1
    i += 1

    duplicate = dict(appointments[1])
    duplicate["scheduled_start"] = appointments[2]["scheduled_start"]
    duplicate["scheduled_end"] = appointments[2]["scheduled_end"]
    appointments.append(duplicate)
    injected["duplicate_external_id"] += 1

    if payments:
        bad_payment = dict(payments[0])
        bad_payment["external_id"] = f"PAY-BAD{i:03d}"
        bad_payment["amount_charged"] = "-50.00"
        payments.append(bad_payment)
        injected["negative_amount"] += 1

    orphan = dict(attendances[0])
    orphan["external_id"] = f"ATT-BAD{i:03d}"
    orphan["appointment_external_id"] = "APT-INEXISTENTE"
    attendances.append(orphan)
    injected["orphan_attendance"] += 1

    return injected


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_dataset(
    output_root: Path,
    *,
    seed: int = 42,
    anchor: date | None = None,
    history_months: int = 18,
    future_days: int = 14,
) -> GenerationResult:
    anchor = resolve_anchor(anchor)
    rng = random.Random(seed)
    builder = _Builder(rng, anchor)

    first_day = (anchor - relativedelta(months=history_months)).replace(day=1)
    last_day = anchor + timedelta(days=future_days)
    total_days = (last_day - first_day).days + 1

    {item["code"]: item for item in PROFESSIONALS}

    for day_offset in range(total_days):
        day = first_day + timedelta(days=day_offset)
        for professional in PROFESSIONALS:
            blocks = PATTERNS[professional["pattern"]].blocks_for(day.weekday())
            if not blocks:
                continue
            fill = _fill_probability(rng, day, professional["demand"])
            for block_start, block_end in blocks:
                cursor = datetime.combine(day, block_start, tzinfo=TIMEZONE)
                limit = datetime.combine(day, block_end, tzinfo=TIMEZONE)
                while cursor + timedelta(minutes=30) <= limit:
                    service_code, duration, price = _pick_service(
                        rng, professional["specialty"]
                    )
                    if cursor + timedelta(minutes=duration) > limit:
                        cursor += timedelta(minutes=SLOT_STEP_MINUTES)
                        continue
                    free = builder._is_free(professional["code"], cursor, duration)
                    if free and rng.random() < fill:
                        if day > anchor or day == anchor and cursor.hour >= 13:
                            status = _status_for_future(rng, day, anchor)
                        else:
                            status = _status_for_historical(rng, day, cursor.hour)
                        appointment = builder.add_appointment(
                            professional=professional,
                            start=cursor,
                            duration=duration,
                            service_code=service_code,
                            price=price,
                            status=status,
                        )
                        if status == AppointmentStatus.REAGENDADA and rng.random() < 0.75:
                            builder.try_add_replacement(
                                appointment, professional, duration, cursor
                            )
                        cursor += timedelta(minutes=duration + rng.randint(0, 15))
                    else:
                        cursor += timedelta(minutes=SLOT_STEP_MINUTES)

    builder.appointments.sort(key=lambda item: item["scheduled_start"] or "")
    builder.attendances.sort(key=lambda item: item["external_id"])
    builder.payments.sort(key=lambda item: item["external_id"])
    builder.history.sort(key=lambda item: item["external_id"])

    injected = _add_invalid_records(
        builder.appointments,
        builder.attendances,
        builder.payments,
        builder.history,
    )

    raw_dir = output_root / anchor.isoformat()
    raw_dir.mkdir(parents=True, exist_ok=True)

    clinic_payload = {
        "code": ClinicSpec.code,
        "name": ClinicSpec.name,
        "timezone": settings.clinic_timezone,
    }
    units = [
        {"code": code, "name": name, "city": city, "clinic_code": ClinicSpec.code}
        for code, name, city in UNITS
    ]
    specialties = [{"code": code, "name": name} for code, name in SPECIALTIES]
    services = [
        {
            "code": code,
            "name": name,
            "duration_minutes": duration,
            "base_price": f"{price:.2f}",
        }
        for code, name, duration, price in SERVICE_TYPES
    ]
    professionals = [
        {
            "code": item["code"],
            "full_name": item["name"],
            "email": f"{item['code'].lower()}@clinica-vida.example",
            "unit_code": item["unit"],
            "specialty_code": item["specialty"],
            "is_active": True,
        }
        for item in PROFESSIONALS
    ]
    availability = []
    for item in PROFESSIONALS:
        pattern = PATTERNS[item["pattern"]]
        for weekday, blocks in sorted(pattern.blocks.items()):
            for block_start, block_end in blocks:
                availability.append(
                    {
                        "professional_code": item["code"],
                        "weekday": weekday,
                        "start_time": block_start.strftime("%H:%M"),
                        "end_time": block_end.strftime("%H:%M"),
                    }
                )

    files: dict[str, list[dict] | dict] = {
        "clinic.json": clinic_payload,
        "units.json": units,
        "specialties.json": specialties,
        "service_types.json": services,
        "professionals.json": professionals,
        "availability.json": availability,
        "appointments.jsonl": builder.appointments,
        "attendances.jsonl": builder.attendances,
        "payments.jsonl": builder.payments,
        "status_history.jsonl": builder.history,
    }

    counts: dict[str, int] = {}
    checksums: dict[str, str] = {}
    for filename, payload in files.items():
        path = raw_dir / filename
        if filename.endswith(".jsonl"):
            _write_jsonl(path, payload)  # type: ignore[arg-type]
            counts[filename] = len(payload)  # type: ignore[arg-type]
        else:
            _write_json(path, payload)
            counts[filename] = 1 if isinstance(payload, dict) else len(payload)
        checksums[filename] = _sha256(path)

    manifest = {
        "seed": seed,
        "anchor_date": anchor.isoformat(),
        "history_months": history_months,
        "future_days": future_days,
        "timezone": settings.clinic_timezone,
        "generated_at": datetime.now(TIMEZONE).isoformat(),
        "first_day": first_day.isoformat(),
        "last_day": last_day.isoformat(),
        "counts": counts,
        "checksums": checksums,
        "invalid_injected": injected,
    }
    _write_json(raw_dir / "manifest.json", manifest)

    return GenerationResult(
        raw_dir=raw_dir,
        anchor=anchor,
        seed=seed,
        counts=counts,
        checksums=checksums,
        invalid_injected=injected,
    )


__all__ = [
    "GenerationResult",
    "PATTERNS",
    "PROFESSIONALS",
    "generate_dataset",
    "resolve_anchor",
    "WEEKDAY_NAMES",
    "professional_by_code",
]


def professional_by_code(code: str) -> dict | None:
    return next((item for item in PROFESSIONALS if item["code"] == code), None)
