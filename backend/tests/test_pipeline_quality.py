"""Testes do gerador determinístico e das regras de qualidade."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.pipeline.generator import generate_dataset
from app.pipeline.quality import stage_dataset

ANCHOR = date(2026, 5, 20)
EXPECTED_REJECTIONS = {
    "invalid_status",
    "invalid_datetime",
    "end_before_start",
    "missing_required_field",
    "duplicate_external_id",
    "negative_amount",
    "orphan_attendance",
}


def _generate(tmp_path: Path, seed: int = 99):
    return generate_dataset(
        tmp_path / "raw",
        seed=seed,
        anchor=ANCHOR,
        history_months=1,
        future_days=2,
    )


def test_gerador_e_deterministico(tmp_path):
    first = _generate(tmp_path / "a", seed=7)
    second = _generate(tmp_path / "b", seed=7)
    assert first.checksums == second.checksums
    assert first.counts == second.counts


def test_gerador_muda_com_outra_semente(tmp_path):
    first = _generate(tmp_path / "a", seed=7)
    second = _generate(tmp_path / "b", seed=8)
    assert first.checksums["appointments.jsonl"] != second.checksums["appointments.jsonl"]


def test_qualidade_rejeita_exatamente_os_casos_injetados(tmp_path):
    result = _generate(tmp_path)
    staged = stage_dataset(result.raw_dir)
    rejected = {issue.issue_type for issue in staged.issues if issue.rejected}
    assert rejected == EXPECTED_REJECTIONS
    assert sum(1 for issue in staged.issues if issue.rejected) == 7
    assert all(issue.severity.value == "ERROR" for issue in staged.issues if issue.rejected)
    assert not any(issue.severity.value == "WARNING" for issue in staged.issues)


def test_qualidade_mantem_registros_validos(tmp_path):
    result = _generate(tmp_path)
    staged = stage_dataset(result.raw_dir)
    assert len(staged.appointments) > 100
    assert len(staged.attendances) > 50
    assert len(staged.payments) == len(staged.attendances)
    assert staged.history
    assert {row["status"] for row in staged.appointments} <= {
        "AGENDADA",
        "CONFIRMADA",
        "EM_ATENDIMENTO",
        "CONCLUIDA",
        "CANCELADA_PACIENTE",
        "CANCELADA_CLINICA",
        "FALTA",
        "REAGENDADA",
    }


def test_staging_materializado(tmp_path):
    from app.pipeline.loader import write_staging

    result = _generate(tmp_path)
    staged = stage_dataset(result.raw_dir)
    destination = write_staging(staged, tmp_path / "staging")
    assert (destination / "appointments.csv").exists()
    assert (destination / "payments.csv").exists()
    assert (destination / "quality_issues.csv").exists()
    header = (destination / "appointments.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "external_id" in header
