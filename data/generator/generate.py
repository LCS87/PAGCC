"""CLI do gerador de dados sintéticos.

Uso:
    python data/generator/generate.py --seed 42 --anchor 2026-10-19
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.pipeline.generator import generate_dataset, resolve_anchor  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o conjunto sintético determinístico.")
    parser.add_argument("--seed", type=int, default=settings.etl_seed)
    parser.add_argument(
        "--anchor",
        type=str,
        default=None,
        help="Data-âncora AAAA-MM-DD (padrão: ETL_ANCHOR_DATE ou hoje).",
    )
    parser.add_argument("--history-months", type=int, default=settings.etl_history_months)
    parser.add_argument("--future-days", type=int, default=settings.etl_future_days)
    parser.add_argument("--output", type=str, default=str(settings.raw_path))
    args = parser.parse_args()

    anchor = date.fromisoformat(args.anchor) if args.anchor else resolve_anchor()
    result = generate_dataset(
        Path(args.output),
        seed=args.seed,
        anchor=anchor,
        history_months=args.history_months,
        future_days=args.future_days,
    )
    print(
        json.dumps(
            {
                "raw_dir": str(result.raw_dir),
                "anchor_date": result.anchor.isoformat(),
                "seed": result.seed,
                "counts": result.counts,
                "invalid_injected": result.invalid_injected,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
