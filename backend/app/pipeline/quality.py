"""Validação e normalização da camada raw para staging.

Cada regra registra uma `StagedIssue`. Problemas que impedem o carregamento
marcam `rejected=True` e o registro não segue para a camada curada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.models.enums import (
    APPOINTMENT_STATUSES,
    AppointmentSource,
    AttendanceStatus,
    CancellationActor,
    PaymentMethod,
    PaymentStatus,
    QualitySeverity,
)

REQUIRED_DIMENSION_FIELDS = {
    "units.json": ("code", "name", "city"),
    "specialties.json": ("code", "name"),
    "service_types.json": ("code", "name", "duration_minutes", "base_price"),
    "professionals.json": ("code", "full_name", "unit_code", "specialty_code"),
}

SOURCE_VALUES = {item.value for item in AppointmentSource}
CANCELLATION_ACTORS = {item.value for item in CancellationActor}
ATTENDANCE_STATUSES = {item.value for item in AttendanceStatus}
PAYMENT_METHODS = {item.value for item in PaymentMethod}
PAYMENT_STATUSES = {item.value for item in PaymentStatus}


@dataclass
class StagedIssue:
    entity: str
    issue_type: str
    severity: QualitySeverity
    record_ref: str | None
    detail: str
    rejected: bool = True


@dataclass
class StagedDataset:
    clinic: dict | None = None
    units: list[dict] = field(default_factory=list)
    specialties: list[dict] = field(default_factory=list)
    service_types: list[dict] = field(default_factory=list)
    professionals: list[dict] = field(default_factory=list)
    availability: list[dict] = field(default_factory=list)
    appointments: list[dict] = field(default_factory=list)
    attendances: list[dict] = field(default_factory=list)
    payments: list[dict] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    issues: list[StagedIssue] = field(default_factory=list)
    rows_read: int = 0
    raw_counts: dict[str, int] = field(default_factory=dict)
    manifest: dict = field(default_factory=dict)


def _issue(
    dataset: StagedDataset,
    entity: str,
    issue_type: str,
    detail: str,
    record_ref: str | None,
    severity: QualitySeverity = QualitySeverity.ERROR,
    rejected: bool = True,
) -> None:
    dataset.issues.append(
        StagedIssue(
            entity=entity,
            issue_type=issue_type,
            severity=severity,
            record_ref=record_ref,
            detail=detail,
            rejected=rejected,
        )
    )


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({"_invalid_json_line": line_number, "_raw": line[:200]})
    return rows


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed


def _parse_time(value: object) -> time | None:
    if not isinstance(value, str) or ":" not in value:
        return None
    try:
        hour, minute = value.split(":")[:2]
        return time(int(hour), int(minute))
    except (ValueError, TypeError):
        return None


def _parse_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def stage_dataset(raw_dir: Path) -> StagedDataset:
    dataset = StagedDataset()
    manifest_path = raw_dir / "manifest.json"
    if manifest_path.exists():
        try:
            dataset.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            dataset.manifest = {}

    clinic_path = raw_dir / "clinic.json"
    if clinic_path.exists():
        try:
            dataset.clinic = json.loads(clinic_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            _issue(dataset, "clinic", "invalid_json", "Arquivo de clínica inválido.", "clinic.json")

    # ---------------------------------------------------------------- dimensões
    for filename, required in REQUIRED_DIMENSION_FIELDS.items():
        rows = _load_jsonl(raw_dir / filename) if filename.endswith(".jsonl") else None
        if rows is None:
            path = raw_dir / filename
            try:
                rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
            except json.JSONDecodeError:
                rows = []
                _issue(dataset, filename, "invalid_json", "JSON inválido.", filename)
        dataset.rows_read += len(rows)
        dataset.raw_counts[filename] = len(rows)
        seen: set[str] = set()
        entity = filename.replace(".json", "")
        for row in rows:
            if not isinstance(row, dict):
                continue
            missing = [field_name for field_name in required if not row.get(field_name)]
            if missing:
                _issue(
                    dataset,
                    entity,
                    "missing_required_field",
                    f"Campos obrigatórios ausentes: {', '.join(missing)}.",
                    str(row.get("code") or row.get("external_id") or "?"),
                )
                continue
            code = str(row["code"])
            if code in seen:
                _issue(
                    dataset,
                    entity,
                    "duplicate_code",
                    f"Código duplicado: {code}.",
                    code,
                )
                continue
            seen.add(code)
            if entity == "service_types":
                try:
                    duration = int(row["duration_minutes"])
                    price = _parse_decimal(row["base_price"])
                except (TypeError, ValueError):
                    duration, price = 0, None
                if duration <= 0 or price is None or price < 0:
                    _issue(
                        dataset,
                        entity,
                        "invalid_service_values",
                        "Duração deve ser positiva e preço não negativo.",
                        code,
                    )
                    continue
                row = {**row, "duration_minutes": duration, "base_price": price}
            if entity == "clinic":
                continue
            destination = {
                "units": dataset.units,
                "specialties": dataset.specialties,
                "service_types": dataset.service_types,
                "professionals": dataset.professionals,
            }[entity]
            destination.append(row)

    unit_codes = {row["code"] for row in dataset.units}
    specialty_codes = {row["code"] for row in dataset.specialties}
    service_codes = {row["code"] for row in dataset.service_types}
    clinic_code = (dataset.clinic or {}).get("code")

    valid_professionals = []
    for row in dataset.professionals:
        if row.get("unit_code") not in unit_codes:
            _issue(
                dataset,
                "professionals",
                "unknown_unit",
                f"Unidade inexistente: {row.get('unit_code')}.",
                row["code"],
            )
            continue
        if row.get("specialty_code") not in specialty_codes:
            _issue(
                dataset,
                "professionals",
                "unknown_specialty",
                f"Especialidade inexistente: {row.get('specialty_code')}.",
                row["code"],
            )
            continue
        valid_professionals.append(row)
    dataset.professionals = valid_professionals
    professional_map = {row["code"]: row for row in dataset.professionals}
    professional_codes = set(professional_map)

    # ------------------------------------------------------------ disponibilidade
    availability_path = raw_dir / "availability.json"
    if availability_path.exists():
        try:
            availability_rows = json.loads(availability_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            availability_rows = []
        dataset.rows_read += len(availability_rows)
        dataset.raw_counts["availability.json"] = len(availability_rows)
        for row in availability_rows:
            code = row.get("professional_code")
            if code not in professional_codes:
                _issue(
                    dataset,
                    "availability",
                    "unknown_professional",
                    f"Profissional inexistente: {code}.",
                    str(code),
                )
                continue
            try:
                weekday = int(row.get("weekday"))
            except (TypeError, ValueError):
                weekday = -1
            start = _parse_time(row.get("start_time"))
            end = _parse_time(row.get("end_time"))
            if weekday < 0 or weekday > 6 or start is None or end is None or end <= start:
                _issue(
                    dataset,
                    "availability",
                    "invalid_availability",
                    "Dia da semana ou intervalo de horário inválido.",
                    f"{code}:{row.get('weekday')}",
                )
                continue
            dataset.availability.append(
                {
                    "professional_code": code,
                    "weekday": weekday,
                    "start_time": start,
                    "end_time": end,
                }
            )

    # --------------------------------------------------------------- agendamentos
    raw_appointments = _load_jsonl(raw_dir / "appointments.jsonl")
    dataset.rows_read += len(raw_appointments)
    dataset.raw_counts["appointments.jsonl"] = len(raw_appointments)
    seen_appointments: set[str] = set()
    valid_ids: set[str] = set()

    for row in raw_appointments:
        external_id = str(row.get("external_id") or "")
        if "_invalid_json_line" in row:
            _issue(
                dataset,
                "appointments",
                "invalid_json",
                f"Linha JSON inválida: {row['_invalid_json_line']}.",
                external_id or "?",
            )
            continue

        if not external_id:
            _issue(dataset, "appointments", "missing_external_id", "external_id ausente.", "?")
            continue
        if external_id in seen_appointments:
            _issue(
                dataset,
                "appointments",
                "duplicate_external_id",
                f"external_id duplicado: {external_id}.",
                external_id,
            )
            continue

        missing = [
            field_name
            for field_name in (
                "unit_code",
                "specialty_code",
                "professional_code",
                "service_code",
                "patient_ref",
                "scheduled_start",
                "scheduled_end",
                "status",
                "source",
            )
            if not row.get(field_name)
        ]
        if missing:
            _issue(
                dataset,
                "appointments",
                "missing_required_field",
                f"Campos obrigatórios ausentes: {', '.join(missing)}.",
                external_id,
            )
            seen_appointments.add(external_id)
            continue

        status_value = str(row["status"])
        if status_value not in APPOINTMENT_STATUSES:
            _issue(
                dataset,
                "appointments",
                "invalid_status",
                f"Status não permitido: {status_value}.",
                external_id,
            )
            seen_appointments.add(external_id)
            continue
        if str(row["source"]) not in SOURCE_VALUES:
            _issue(
                dataset,
                "appointments",
                "invalid_source",
                f"Origem não permitida: {row['source']}.",
                external_id,
            )
            seen_appointments.add(external_id)
            continue

        scheduled_start = _parse_datetime(row.get("scheduled_start"))
        scheduled_end = _parse_datetime(row.get("scheduled_end"))
        if scheduled_start is None or scheduled_end is None:
            _issue(
                dataset,
                "appointments",
                "invalid_datetime",
                "Data/hora inválida em scheduled_start ou scheduled_end.",
                external_id,
            )
            seen_appointments.add(external_id)
            continue
        if scheduled_end <= scheduled_start:
            _issue(
                dataset,
                "appointments",
                "end_before_start",
                f"Fim ({scheduled_end.isoformat()}) não é posterior ao início.",
                external_id,
            )
            seen_appointments.add(external_id)
            continue

        professional = professional_map.get(str(row["professional_code"]))
        if professional is None:
            _issue(
                dataset,
                "appointments",
                "unknown_professional",
                f"Profissional inexistente: {row['professional_code']}.",
                external_id,
            )
            seen_appointments.add(external_id)
            continue
        if row["unit_code"] not in unit_codes:
            _issue(
                dataset,
                "appointments",
                "unknown_unit",
                f"Unidade inexistente: {row['unit_code']}.",
                external_id,
            )
            seen_appointments.add(external_id)
            continue
        if row["specialty_code"] not in specialty_codes:
            _issue(
                dataset,
                "appointments",
                "unknown_specialty",
                f"Especialidade inexistente: {row['specialty_code']}.",
                external_id,
            )
            seen_appointments.add(external_id)
            continue
        if row["service_code"] not in service_codes:
            _issue(
                dataset,
                "appointments",
                "unknown_service",
                f"Tipo de serviço inexistente: {row['service_code']}.",
                external_id,
            )
            seen_appointments.add(external_id)
            continue
        if (
            professional["unit_code"] != row["unit_code"]
            or professional["specialty_code"] != row["specialty_code"]
        ):
            _issue(
                dataset,
                "appointments",
                "dimension_mismatch",
                "Unidade/especialidade do agendamento divergem do profissional.",
                external_id,
            )
            seen_appointments.add(external_id)
            continue
        if clinic_code and row.get("clinic_code") and row["clinic_code"] != clinic_code:
            _issue(
                dataset,
                "appointments",
                "unknown_clinic",
                f"Clínica inexistente: {row['clinic_code']}.",
                external_id,
            )
            seen_appointments.add(external_id)
            continue

        confirmed_at = None
        if row.get("confirmed_at"):
            confirmed_at = _parse_datetime(row["confirmed_at"])
            if confirmed_at is None:
                _issue(
                    dataset,
                    "appointments",
                    "invalid_confirmation_datetime",
                    "confirmed_at inválido; campo será ignorado.",
                    external_id,
                    severity=QualitySeverity.WARNING,
                    rejected=False,
                )
        cancellation_actor = row.get("cancellation_actor")
        if cancellation_actor and cancellation_actor not in CANCELLATION_ACTORS:
            _issue(
                dataset,
                "appointments",
                "invalid_cancellation_actor",
                f"cancellation_actor inválido: {cancellation_actor}.",
                external_id,
                severity=QualitySeverity.WARNING,
                rejected=False,
            )
            cancellation_actor = None

        seen_appointments.add(external_id)
        valid_ids.add(external_id)
        dataset.appointments.append(
            {
                "external_id": external_id,
                "clinic_code": row.get("clinic_code") or clinic_code,
                "unit_code": row["unit_code"],
                "specialty_code": row["specialty_code"],
                "professional_code": row["professional_code"],
                "service_code": row["service_code"],
                "patient_ref": str(row["patient_ref"]).strip(),
                "scheduled_start": scheduled_start,
                "scheduled_end": scheduled_end,
                "status": status_value,
                "source": str(row["source"]),
                "confirmed_at": confirmed_at,
                "cancellation_actor": cancellation_actor,
                "cancellation_reason": row.get("cancellation_reason"),
                "rescheduled_from_external_id": row.get("rescheduled_from_external_id"),
                "created_at": _parse_datetime(row.get("created_at")) or scheduled_start,
                "updated_at": _parse_datetime(row.get("updated_at")) or scheduled_end,
            }
        )

    # Referências de reagendamento só podem ser resolvidas após todos os IDs válidos.
    valid_ids_set = {row["external_id"] for row in dataset.appointments}
    for row in dataset.appointments:
        reference = row.get("rescheduled_from_external_id")
        if reference and reference not in valid_ids_set:
            _issue(
                dataset,
                "appointments",
                "unknown_reschedule_reference",
                f"Agendamento de origem inexistente: {reference}.",
                row["external_id"],
                severity=QualitySeverity.WARNING,
                rejected=False,
            )
            row["rescheduled_from_external_id"] = None

    # --------------------------------------------------------------- atendimentos
    raw_attendances = _load_jsonl(raw_dir / "attendances.jsonl")
    dataset.rows_read += len(raw_attendances)
    dataset.raw_counts["attendances.jsonl"] = len(raw_attendances)
    seen_attendances: set[str] = set()
    valid_attendance_ids: set[str] = set()
    for row in raw_attendances:
        external_id = str(row.get("external_id") or "")
        if not external_id:
            _issue(dataset, "attendances", "missing_external_id", "external_id ausente.", "?")
            continue
        if external_id in seen_attendances:
            _issue(
                dataset,
                "attendances",
                "duplicate_external_id",
                f"external_id duplicado: {external_id}.",
                external_id,
            )
            continue
        seen_attendances.add(external_id)
        appointment_ref = row.get("appointment_external_id")
        if appointment_ref not in valid_ids:
            _issue(
                dataset,
                "attendances",
                "orphan_attendance",
                f"Agendamento inexistente: {appointment_ref}.",
                external_id,
            )
            continue
        started_at = _parse_datetime(row.get("started_at"))
        arrived_at = _parse_datetime(row.get("arrived_at")) if row.get("arrived_at") else None
        ended_at = _parse_datetime(row.get("ended_at")) if row.get("ended_at") else None
        if started_at is None:
            _issue(
                dataset,
                "attendances",
                "invalid_datetime",
                "started_at inválido.",
                external_id,
            )
            continue
        if ended_at is not None and ended_at < started_at:
            _issue(
                dataset,
                "attendances",
                "end_before_start",
                "ended_at anterior a started_at.",
                external_id,
            )
            continue
        if arrived_at is not None and arrived_at > started_at:
            _issue(
                dataset,
                "attendances",
                "arrived_after_start",
                "Chegada posterior ao início; espera não será calculada.",
                external_id,
                severity=QualitySeverity.WARNING,
                rejected=False,
            )
            arrived_at = None
        status_value = str(row.get("status") or "")
        if status_value not in ATTENDANCE_STATUSES:
            _issue(
                dataset,
                "attendances",
                "invalid_status",
                f"Status de atendimento inválido: {status_value}.",
                external_id,
            )
            continue
        valid_attendance_ids.add(external_id)
        dataset.attendances.append(
            {
                "external_id": external_id,
                "appointment_external_id": appointment_ref,
                "arrived_at": arrived_at,
                "started_at": started_at,
                "ended_at": ended_at,
                "status": status_value,
            }
        )

    # ------------------------------------------------------------------ pagamentos
    raw_payments = _load_jsonl(raw_dir / "payments.jsonl")
    dataset.rows_read += len(raw_payments)
    dataset.raw_counts["payments.jsonl"] = len(raw_payments)
    seen_payments: set[str] = set()
    for row in raw_payments:
        external_id = str(row.get("external_id") or "")
        if not external_id:
            _issue(dataset, "payments", "missing_external_id", "external_id ausente.", "?")
            continue
        if external_id in seen_payments:
            _issue(
                dataset,
                "payments",
                "duplicate_external_id",
                f"external_id duplicado: {external_id}.",
                external_id,
            )
            continue
        seen_payments.add(external_id)
        attendance_ref = row.get("attendance_external_id")
        if attendance_ref not in valid_attendance_ids:
            _issue(
                dataset,
                "payments",
                "orphan_payment",
                f"Atendimento inexistente: {attendance_ref}.",
                external_id,
            )
            continue
        charged = _parse_decimal(row.get("amount_charged"))
        received = _parse_decimal(row.get("amount_received"))
        refund = _parse_decimal(row.get("refund_amount"))
        if charged is None or received is None or refund is None:
            _issue(
                dataset,
                "payments",
                "invalid_amount",
                "Valores financeiros inválidos.",
                external_id,
            )
            continue
        if charged < 0 or received < 0 or refund < 0:
            _issue(
                dataset,
                "payments",
                "negative_amount",
                f"Valor negativo: cobrado={charged}, recebido={received}, estorno={refund}.",
                external_id,
            )
            continue
        if received > charged:
            _issue(
                dataset,
                "payments",
                "received_above_charged",
                "Valor recebido maior que o cobrado.",
                external_id,
                severity=QualitySeverity.WARNING,
                rejected=False,
            )
        method = str(row.get("method") or "")
        status_value = str(row.get("status") or "")
        if method not in PAYMENT_METHODS:
            _issue(
                dataset,
                "payments",
                "invalid_payment_method",
                f"Forma de pagamento inválida: {method}.",
                external_id,
            )
            continue
        if status_value not in PAYMENT_STATUSES:
            _issue(
                dataset,
                "payments",
                "invalid_payment_status",
                f"Status de pagamento inválido: {status_value}.",
                external_id,
            )
            continue
        recorded_at = _parse_datetime(row.get("recorded_at"))
        if recorded_at is None:
            _issue(
                dataset,
                "payments",
                "invalid_datetime",
                "recorded_at inválido.",
                external_id,
            )
            continue
        dataset.payments.append(
            {
                "external_id": external_id,
                "attendance_external_id": attendance_ref,
                "amount_charged": charged,
                "amount_received": received,
                "refund_amount": refund,
                "method": method,
                "status": status_value,
                "recorded_at": recorded_at,
            }
        )

    # ------------------------------------------------------------------ histórico
    raw_history = _load_jsonl(raw_dir / "status_history.jsonl")
    dataset.rows_read += len(raw_history)
    dataset.raw_counts["status_history.jsonl"] = len(raw_history)
    seen_history: set[str] = set()
    for row in raw_history:
        external_id = str(row.get("external_id") or "")
        if not external_id:
            _issue(dataset, "status_history", "missing_external_id", "external_id ausente.", "?")
            continue
        if external_id in seen_history:
            _issue(
                dataset,
                "status_history",
                "duplicate_external_id",
                f"external_id duplicado: {external_id}.",
                external_id,
            )
            continue
        seen_history.add(external_id)
        appointment_ref = row.get("appointment_external_id")
        if appointment_ref not in valid_ids:
            _issue(
                dataset,
                "status_history",
                "orphan_history",
                f"Agendamento inexistente: {appointment_ref}.",
                external_id,
            )
            continue
        to_status = str(row.get("to_status") or "")
        from_status = row.get("from_status")
        if to_status not in APPOINTMENT_STATUSES or (
            from_status and from_status not in APPOINTMENT_STATUSES
        ):
            _issue(
                dataset,
                "status_history",
                "invalid_status",
                f"Status inválido no histórico: {to_status}.",
                external_id,
            )
            continue
        changed_at = _parse_datetime(row.get("changed_at"))
        if changed_at is None:
            _issue(
                dataset,
                "status_history",
                "invalid_datetime",
                "changed_at inválido.",
                external_id,
            )
            continue
        dataset.history.append(
            {
                "external_id": external_id,
                "appointment_external_id": appointment_ref,
                "from_status": from_status,
                "to_status": to_status,
                "changed_at": changed_at,
                "reason": row.get("reason"),
            }
        )

    return dataset


__all__ = ["StagedDataset", "StagedIssue", "stage_dataset"]
