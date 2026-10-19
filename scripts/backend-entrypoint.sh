#!/bin/sh
set -eu

echo "[entrypoint] Aguardando o PostgreSQL..."
python - <<'PY'
import os
import time

from sqlalchemy import create_engine, text

url = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://clinic:clinic@pagcc-db:5432/clinic_analytics",
)
engine = create_engine(url, pool_pre_ping=True)
for attempt in range(60):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("[entrypoint] Banco disponível.")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"[entrypoint] tentativa {attempt + 1}/60: {exc}")
        time.sleep(2)
else:
    raise SystemExit("[entrypoint] banco não respondeu a tempo.")
PY

echo "[entrypoint] Aplicando migrações..."
alembic upgrade head

echo "[entrypoint] Criando usuários de demonstração..."
python -m app.cli.seed

if [ "${RUN_PIPELINE:-1}" = "1" ]; then
  echo "[entrypoint] Executando pipeline de dados sintéticos..."
  python /app/data/pipelines/run_pipeline.py --generate
else
  echo "[entrypoint] RUN_PIPELINE=0: pulando carga de dados."
fi

echo "[entrypoint] Iniciando API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
