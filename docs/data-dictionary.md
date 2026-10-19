# Dicionário de dados

Banco: PostgreSQL. Timestamps são `timestamptz` (UTC no armazenamento; exibição no fuso da
clínica). Chaves primárias são inteiras e internas; nunca há CPF, telefone ou endereço.

## Camadas

| Camada | Local | Conteúdo |
| --- | --- | --- |
| Raw | `data/raw/<âncora>/*.json/jsonl` | Dados gerados, preservados como vieram |
| Staging | `data/staging/<âncora>/*.csv` | Tipos normalizados, sem rejeições |
| Curado | Tabelas `clinic` … `app_user` | Dimensões e fatos validados |
| Analytics | `analytics_daily_metric` | Agregado diário por dimensão |
| Governança | `etl_run`, `data_quality_issue` | Execuções e problemas |

## Dimensões

### `clinic`

| Coluna | Tipo | Notas |
| --- | --- | --- |
| id | int PK | |
| code | varchar(32) UQ | `CLINICA-VIDA` |
| name | varchar(160) | Nome fictício |
| timezone | varchar(64) | `America/Fortaleza` |
| created_at / updated_at | timestamptz | |

### `unit`

| Coluna | Tipo | Notas |
| --- | --- | --- |
| id | int PK | |
| clinic_id | FK clinic | CASCADE |
| code | varchar(32) UQ | `UN-ALDEOTA`, `UN-MEIRELES`, `UN-EUSEBIO` |
| name | varchar(120) | |
| city | varchar(80) | |
| is_active | bool | |

### `specialty`

| Coluna | Tipo | Notas |
| --- | --- | --- |
| id | int PK | |
| code | varchar(32) UQ | `CLM`, `CAR`, `DER`, `ORT`, `PED`, `GIN`, `PSI`, `NUT` |
| name | varchar(80) | |

### `professional`

| Coluna | Tipo | Notas |
| --- | --- | --- |
| id | int PK | |
| clinic_id / unit_id / specialty_id | FK | |
| code | varchar(32) UQ | `PRO-001`… |
| full_name | varchar(120) | Nome fictício |
| email | varchar(160) | Domínio `.example` |
| is_active | bool | |
| created_at / updated_at | timestamptz | |

### `professional_availability`

Janela semanal de atendimento. Cada linha é um turno (ex.: segunda 08:00–12:00).

| Coluna | Tipo | Notas |
| --- | --- | --- |
| id | int PK | |
| professional_id | FK professional | CASCADE |
| weekday | smallint | 0 = segunda … 6 = domingo |
| start_time / end_time | time | `end_time > start_time` |
| UQ | (professional_id, weekday, start_time) | evita turno duplicado |

### `service_type`

| Coluna | Tipo | Notas |
| --- | --- | --- |
| id | int PK | |
| code | varchar(32) UQ | `RET30`, `CONS45`, `CONS60`, `AVAL90` |
| name | varchar(120) | |
| duration_minutes | smallint | usado na ocupação |
| base_price | numeric(10,2) | valor fictício |

## Fatos

### `appointment`

| Coluna | Tipo | Notas |
| --- | --- | --- |
| id | int PK | |
| external_id | varchar(40) UQ | prefixo `APT-AAAAMMDD-` |
| clinic_id / unit_id / specialty_id / professional_id / service_type_id | FK | |
| patient_ref | varchar(24) | `PAC-0001`; não é identificador real |
| scheduled_start / scheduled_end | timestamptz | `end > start` |
| status | enum varchar | AGENDADA, CONFIRMADA, EM_ATENDIMENTO, CONCLUIDA, CANCELADA_PACIENTE, CANCELADA_CLINICA, FALTA, REAGENDADA |
| source | enum varchar | TELEFONE, WHATSAPP, BALCAO, PORTAL |
| confirmed_at | timestamptz null | |
| cancellation_actor | enum null | PACIENTE, CLINICA |
| cancellation_reason | varchar(120) null | |
| rescheduled_from_id | FK appointment null | auto-relacionamento |
| created_at / updated_at | timestamptz | |

Índices: `scheduled_start`, `(status, scheduled_start)`,
`(unit_id, specialty_id, professional_id, scheduled_start)`.

### `attendance`

| Coluna | Tipo | Notas |
| --- | --- | --- |
| id | int PK | |
| external_id | varchar(40) UQ | `ATT-…` |
| appointment_id | FK UQ | um atendimento por agendamento |
| arrived_at | timestamptz null | base do tempo de espera |
| started_at | timestamptz | |
| ended_at | timestamptz null | `>= started_at` |
| status | enum | CONCLUIDO, EM_ANDAMENTO |
| created_at / updated_at | timestamptz | |

### `payment_record`

| Coluna | Tipo | Notas |
| --- | --- | --- |
| id | int PK | |
| external_id | varchar(40) UQ | `PAY-…` |
| attendance_id | FK attendance | CASCADE |
| amount_charged / amount_received / refund_amount | numeric(10,2) | não negativos |
| method | enum | PIX, CARTAO_CREDITO, CARTAO_DEBITO, DINHEIRO, CONVENIO |
| status | enum | PAGO, PENDENTE, ESTORNADO |
| recorded_at | timestamptz | |
| created_at / updated_at | timestamptz | |

### `appointment_status_history`

| Coluna | Tipo | Notas |
| --- | --- | --- |
| id | int PK | |
| external_id | varchar(40) UQ | `HIS-…` |
| appointment_id | FK | CASCADE |
| from_status | enum null | primeiro evento não tem origem |
| to_status | enum | |
| changed_at | timestamptz | |
| reason | varchar(160) null | |

## Analytics

### `analytics_daily_metric`

Chave única: `(day, unit_id, specialty_id, professional_id)`.

| Coluna | Tipo | Notas |
| --- | --- | --- |
| day | date | data local do agendamento |
| scheduled_count | int | todos os status |
| completed_count | int | CONCLUIDA |
| no_show_count | int | FALTA |
| cancelled_patient_count / cancelled_clinic_count | int | cancelamentos |
| rescheduled_count | int | REAGENDADA |
| booked_minutes | int | status que ocupam a agenda |
| available_minutes | int | disponibilidade do dia |
| revenue_charged / revenue_received | numeric(12,2) | apenas concluídos |
| wait_seconds_sum / wait_samples | int | espera agregada |

## Governança

### `etl_run`

| Coluna | Notas |
| --- | --- |
| run_id | identificador legível `etl-AAAAMMDDTHHMMSS-xxxxxx` |
| started_at / finished_at | timestamptz |
| status | RUNNING, SUCCESS, PARTIAL, FAILED |
| source_seed / anchor_date | reprodutibilidade |
| raw_path | diretório dos arquivos de origem |
| rows_read / rows_inserted / rows_updated / rows_rejected | contagens |
| message | resumo ou erro |

### `data_quality_issue`

| Coluna | Notas |
| --- | --- |
| etl_run_id | FK etl_run |
| entity | appointments, attendances, payments… |
| issue_type | `duplicate_external_id`, `invalid_status`, etc. |
| severity | ERROR (rejeitado) ou WARNING (mantido com ressalva) |
| record_ref | `external_id` ou código |
| detail | descrição legível |

### `app_user`

| Coluna | Notas |
| --- | --- |
| email | UQ, usado no login |
| full_name | |
| password_hash | PBKDF2-SHA256 versionado (`pbkdf2_sha256$iterações$salt$hash`) |
| role | ADMIN, GESTOR, COORDENADOR, ANALISTA, RECEPCAO, PROFISSIONAL |
| professional_id | vínculo opcional para escopo de dados |
| is_active / last_login_at | |

## Enums

- **AppointmentStatus:** AGENDADA, CONFIRMADA, EM_ATENDIMENTO, CONCLUIDA,
  CANCELADA_PACIENTE, CANCELADA_CLINICA, FALTA, REAGENDADA.
- **PaymentStatus:** PAGO, PENDENTE, ESTORNADO.
- **QualitySeverity:** ERROR, WARNING.
- **EtlStatus:** RUNNING, SUCCESS, PARTIAL, FAILED.

## Regras de qualidade aplicadas

| Regra | Severidade | Ação |
| --- | --- | --- |
| Campos obrigatórios | ERROR | rejeita |
| JSON inválido | ERROR | rejeita |
| `external_id`/`code` duplicado | ERROR | mantém o primeiro, rejeita os demais |
| Data/hora inválida | ERROR | rejeita |
| `scheduled_end <= scheduled_start` | ERROR | rejeita |
| Status/origem fora do enum | ERROR | rejeita |
| FK inexistente (unidade, especialidade, profissional, serviço) | ERROR | rejeita |
| Dimensões divergentes do profissional | ERROR | rejeita |
| Atendimento/pagamento/histórico órfão | ERROR | rejeita |
| Valor financeiro negativo | ERROR | rejeita |
| Recebido maior que cobrado | WARNING | mantém |
| Chegada após o início | WARNING | mantém sem calcular espera |
| `confirmed_at` inválido | WARNING | mantém sem o campo |
| Referência de reagendamento inexistente | WARNING | mantém sem vínculo |

## Reprodutibilidade

```bash
python data/generator/generate.py --seed 42 --anchor 2026-10-19
python data/pipelines/run_pipeline.py --no-generate
```

Mesma seed + mesma âncora ⇒ mesmos arquivos raw (checksums no `manifest.json`) e mesmos
agregados. A âncora é gravada em `etl_run` e usada como `demo_today`.
