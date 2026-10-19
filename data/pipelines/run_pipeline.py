"""CLI do pipeline ETL/ELT.

Uso:
    python data/pipelines/run_pipeline.py --generate
    python data/pipelines/run_pipeline.py --anchor 2026-10-19 --no-generate
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.pipeline.generator import generate_dataset, resolve_anchor  # noqa: E402
from app.pipeline.loader import run_pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa o pipeline raw → curado → analytics.")
    parser.add_argument("--seed", type=int, default=settings.etl_seed)
    parser.add_argument("--anchor", type=str, default=None)
    parser.add_argument("--history-months", type=int, default=settings.etl_history_months)
    parser.add_argument("--future-days", type=int, default=settings.etl_future_days)
    parser.add_argument("--raw-dir", type=str, default=str(settings.raw_path))
    parser.add_argument(
        "--generate",
        dest="generate",
        action="store_true",
        default=True,
        help="Gera os dados sintéticos antes de carregar (padrão).",
    )
    parser.add_argument(
        "--no-generate",
        dest="generate",
        action="store_false",
        help="Usa um conjunto raw já existente para a âncora.",
    )
    args = parser.parse_args()

    anchor = date.fromisoformat(args.anchor) if args.anchor else resolve_anchor()
    raw_root = Path(args.raw_dir)
    raw_dir = raw_root / anchor.isoformat()

    if args.generate or not (raw_dir / "manifest.json").exists():
        print(f"[1/3] Gerando dados sintéticos em {raw_dir} (seed={args.seed})...")
        generate_dataset(
            raw_root,
            seed=args.seed,
            anchor=anchor,
            history_months=args.history_months,
            future_days=args.future_days,
        )
    else:
        print(f"[1/3] Reutilizando dados raw existentes em {raw_dir}.")

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - diagnóstico de ambiente
        raise SystemExit(
            "Não foi possível conectar ao banco. Verifique DATABASE_URL e se o PostgreSQL "
            f"está em execução.\nDetalhe: {exc}"
        ) from exc

    print("[2/3] Validando, carregando e reconstruindo a camada analytics...")
    with SessionLocal() as db:
        result = run_pipeline(
            db,
            raw_dir=raw_dir,
            staging_root=settings.staging_path / anchor.isoformat(),
            seed=args.seed,
            anchor=anchor,
        )

    print("[3/3] Pipeline concluído.")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
