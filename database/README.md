# Migrações

As migrações do banco ficam em **`backend/alembic/`**, junto da aplicação que define os modelos
SQLAlchemy. Esta pasta existe para manter a estrutura prevista no plano e apontar o caminho
correto.

```bash
cd backend

# aplicar
alembic upgrade head

# criar nova revisão após alterar modelos
alembic revision --autogenerate -m "descrição"

# reverter uma revisão
alembic downgrade -1

# histórico
alembic history
```

A URL é lida de `DATABASE_URL` (via `backend/alembic/env.py`), nunca do `alembic.ini`.

## Tabelas criadas

Dimensões: `clinic`, `unit`, `specialty`, `professional`, `professional_availability`,
`service_type`.

Fatos: `appointment`, `attendance`, `payment_record`, `appointment_status_history`.

Analytics: `analytics_daily_metric`.

Governança: `etl_run`, `data_quality_issue`, `app_user`.

O dicionário completo está em [`docs/data-dictionary.md`](../docs/data-dictionary.md).
