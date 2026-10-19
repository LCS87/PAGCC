# Arquitetura

## Visão de contexto

O Clinic Analytics é uma aplicação de demonstração para gestão de clínicas ambulatoriais.
Ela consome um conjunto sintético, transforma em indicadores e apresenta dashboards para
diferentes papéis. Não há integração com sistemas externos, convênios, bancos ou prontuários.

```text
Usuário ──▶ SPA Vue 3 ──/api──▶ FastAPI ──SQLAlchemy──▶ PostgreSQL
                                     ▲                        │
                                     └──── analytics_daily ◀──┘
                                                ▲
                                   Pipeline ETL (Python)
                                     raw → staging → curado
```

## Componentes

### Frontend (`frontend/`)

- SPA Vue 3 + TypeScript + Vite.
- Roteamento por módulos; *guards* verificam autenticação e papéis.
- Pinia para sessão, tema e metadados (unidades, especialidades, profissionais, data de
  referência).
- Cliente HTTP próprio sobre `fetch`, com JWT, tratamento de 401 e erros padronizados.
- ECharts renderiza séries, barras e rosca; o tema é recalculado a partir das variáveis CSS
  quando o usuário alterna claro/escuro.
- Nginx serve o build e faz proxy de `/api`, `/docs` e `/openapi.json` para o backend.

### Backend (`backend/app/`)

- **API v1** organizada por domínio: autenticação, metadados, KPIs, analytics, agenda,
  atendimentos, profissionais, qualidade e administração.
- **Serviços** concentram regras e consultas; routers apenas validam e orquestram.
- **Schemas Pydantic** definem contratos e documentação OpenAPI.
- **SQLAlchemy 2** com modelos tipados, *naming convention* de constraints e enums persistidos
  como `VARCHAR + CHECK`.
- **Erros** seguem `{ "error": { "code", "message", "details" } }`, com handlers para validação,
  HTTP, erros de aplicação e exceções inesperadas.
- **Logs** em JSON, com `request_id`, tempo de resposta, método, rota, status e usuário.

### Banco (`PostgreSQL`)

- Entidades dimensionais: `clinic`, `unit`, `specialty`, `professional`, `service_type`,
  `professional_availability`.
- Fatos: `appointment`, `attendance`, `payment_record`, `appointment_status_history`.
- Camada analítica: `analytics_daily_metric` (dia × unidade × especialidade × profissional).
- Governança: `etl_run`, `data_quality_issue`, `app_user`.
- Migrações versionadas em `backend/alembic/versions`.

### Pipeline (`backend/app/pipeline/` + CLIs em `data/`)

1. **Gerar raw**: `generator.py` cria JSONL/JSON determinístico por `(seed, âncora)`.
2. **Validar/normalizar**: `quality.py` produz um `StagedDataset` e uma lista de problemas.
3. **Materializar staging**: CSVs normalizados em `data/staging/<âncora>/`.
4. **Carregar curado**: `loader.py` faz upsert por chave natural, em lotes, e remove
   agendamentos de outras âncoras (semântica de *snapshot*).
5. **Reconstruir analytics**: agrega a camada curada, incluindo dias sem agendamento para
   calcular ocupação corretamente; grava em `analytics_daily_metric`.
6. **Registrar execução**: contagens, status, seed, âncora e problemas.

O pipeline é idempotente: executar duas vezes a mesma âncora não duplica registros
(`rows_inserted = 0`, `rows_updated > 0`).

## Fluxo de uma requisição

```text
GET /api/v1/kpis/overview?start=...&end=...&unit_id=...
  ├─ HTTPBearer → JWT → usuário (e escopo PROFISSIONAL)
  ├─ resolve_filters → período padrão = últimos 30 dias até demo_today
  ├─ scoped_professional_id → força profissional do usuário, se aplicável
  ├─ totals_for → SUM(analytics_daily_metric) com filtros
  ├─ derive_metrics → fórmulas documentadas
  └─ build_overview → KPIs + período anterior + variação
```

## Modelo analítico

`analytics_daily_metric` evita agregações caras em tempo de requisição e mantém a API simples.
Cada linha contém contagens por status, minutos reservados/disponíveis, receita e soma de
espera. As consultas de KPI, série temporal e segmentação são `SUM`/`GROUP BY` sobre essa tabela.

A ocupação usa a disponibilidade semanal (`professional_availability`) para calcular o
denominador, inclusive em dias sem agendamentos. Por isso a reconstrução percorre todos os dias
entre o primeiro e o último agendamento.

## Segurança

- Senhas com PBKDF2-HMAC-SHA256 (salt por usuário, 260 mil iterações).
- JWT HS256 com emissor e expiração; segredo por variável de ambiente.
- RBAC: ADMIN, GESTOR, COORDENADOR, ANALISTA, RECEPCAO, PROFISSIONAL.
- Exportação restrita a papéis analíticos.
- PROFISSIONAL só acessa os próprios indicadores, agenda e atendimentos (filtro e verificação
  de propriedade no backend).
- Logs não registram tokens nem dados pessoais.
- CORS configurável; nenhum segredo versionado.

## Escalabilidade e evolução

- O agregado diário suporta dashboards com rapidez; para volumes maiores, particionar por mês
  ou materializar visões adicionais.
- Exportações grandes devem migrar para jobs assíncronos.
- A camada curada permite trocar o gerador por uma fonte real sem alterar a API.
- Uma nova vertical (veterinária) deve criar entidades próprias (`animal`, `tutor`) e indicadores
  separados, sem reutilizar o modelo humano.

## Decisões e trade-offs

Consulte `docs/decisions/`. Em resumo: priorizou-se profundidade de uma stack coerente,
fórmulas explícitas, dados reproduzíveis e entrega local simples (Docker Compose), em vez de
microsserviços ou múltiplas linguagens sem necessidade.
