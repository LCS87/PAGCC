"""Relatório de qualidade da última execução do pipeline.

Uso:
    python data/quality/report.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.services.quality import list_issues, quality_summary  # noqa: E402


def main() -> None:
    with SessionLocal() as db:
        summary = quality_summary(db)
        run = summary.last_run
        print("=== Qualidade dos dados ===")
        if run is None:
            print("Nenhuma execução encontrada. Rode o pipeline primeiro.")
            return
        print(f"Execução: {run.run_id} ({run.status.value})")
        print(f"Âncora: {run.anchor_date} · semente: {run.source_seed}")
        print(
            f"Lidos: {summary.total_rows_read} · rejeitados: {summary.total_rows_rejected} "
            f"({summary.rejected_pct}%)"
        )
        print(f"Erros: {summary.issues_by_severity.get('ERROR', 0)}")
        print(f"Avisos: {summary.issues_by_severity.get('WARNING', 0)}")
        if summary.issues_by_type:
            print("\nPor tipo:")
            for item in summary.issues_by_type:
                print(f"  - {item.key}: {item.count}")

        issues = list_issues(db, page=1, page_size=50, run_id=run.id)
        if issues.items:
            print("\nPrimeiros registros:")
            for issue in issues.items[:20]:
                print(
                    f"  [{issue.severity.value}] {issue.entity}/{issue.issue_type} "
                    f"({issue.record_ref}): {issue.detail}"
                )


if __name__ == "__main__":
    main()
