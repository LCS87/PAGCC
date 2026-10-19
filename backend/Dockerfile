# Imagem do backend (FastAPI + pipeline)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY data/generator data/generator
COPY data/pipelines data/pipelines
COPY data/quality data/quality
COPY scripts/backend-entrypoint.sh /app/backend-entrypoint.sh
RUN chmod +x /app/backend-entrypoint.sh

WORKDIR /app/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=300s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["/app/backend-entrypoint.sh"]
