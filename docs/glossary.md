# Glossário de domínio

## Termos

| Termo | Definição |
| --- | --- |
| **Agendamento** (`appointment`) | Reserva de horário para um paciente com profissional, unidade e tipo de serviço. Pode terminar em atendimento, falta, cancelamento ou reagendamento. |
| **Atendimento** (`attendance`) | Registro administrativo do comparecimento e da realização. Existe somente para agendamentos concluídos. |
| **Paciente (referência)** | Identificador fictício `PAC-0001`. Não há nome, CPF, telefone ou endereço. |
| **Profissional** | Pessoa que atende, vinculada a uma unidade e especialidade e a janelas semanais de disponibilidade. |
| **Unidade** | Local físico fictício da clínica (Aldeota, Meireles, Eusébio). |
| **Especialidade** | Área do profissional (Clínica Médica, Cardiologia etc.). |
| **Tipo de serviço** | Procedimento administrativo com duração prevista e preço-base fictício. |
| **Disponibilidade** (`professional_availability`) | Turno semanal em que o profissional atende (ex.: segunda 08:00–12:00). Base do denominador de ocupação. |
| **Agendamento elegível** | Agendamento que deveria acontecer: total menos reagendamentos. É o denominador das taxas. |
| **Minutos reservados** | Duração dos agendamentos que ocupam a agenda: concluído, falta, em atendimento, confirmado ou agendado. |
| **Minutos disponíveis** | Soma das janelas de disponibilidade no período, incluindo dias sem agendamentos. |
| **Receita bruta simulada** | Soma dos valores cobrados nos atendimentos concluídos. Não representa caixa. |
| **Receita recebida simulada** | Valores recebidos menos estornos nos atendimentos concluídos. |
| **Ticket médio** | Receita bruta dividida pelas consultas realizadas. |
| **Espera** | Diferença entre chegada (`arrived_at`) e início do atendimento (`started_at`). |
| **Falta** (`FALTA`) | Paciente não compareceu e não cancelou. O horário é contabilizado como ocupado. |
| **Reagendamento** (`REAGENDADA`) | Horário original liberado; o novo horário, quando existe, é um agendamento próprio. |
| **Camada raw** | Dados sintéticos como gerados, preservados em JSON/JSONL. |
| **Camada staging** | Normalização e validação, materializada em CSV. |
| **Camada curada** | Tabelas relacionais validadas no PostgreSQL. |
| **Camada analytics** | Agregado diário `analytics_daily_metric`, consumido pelos dashboards. |
| **Execução do pipeline** (`etl_run`) | Registro com seed, âncora, contagens, status e mensagem. |
| **Problema de qualidade** (`data_quality_issue`) | Registro rejeitado (ERROR) ou mantido com ressalva (WARNING). |
| **Âncora / `demo_today`** | Data de referência do conjunto sintético; usada como “hoje” nos dashboards. |
| **Seed** | Semente do gerador aleatório; junto da âncora, garante reprodutibilidade. |

## Status do agendamento

| Status | Significado | Conta como realizada? | Ocupa a agenda? | Entra em “elegíveis”? |
| --- | --- | --- | --- | --- |
| AGENDADA | Marcada, ainda sem confirmação | não | sim | sim |
| CONFIRMADA | Presença confirmada | não | sim | sim |
| EM_ATENDIMENTO | Paciente em atendimento | não | sim | sim |
| CONCLUIDA | Atendimento realizado | sim | sim | sim |
| CANCELADA_PACIENTE | Cancelada pelo paciente | não | não | sim |
| CANCELADA_CLINICA | Cancelada pela clínica | não | não | sim |
| FALTA | Não compareceu | não | sim | sim |
| REAGENDADA | Horário remarcado | não | não | não |

## Papéis

| Papel | Escopo |
| --- | --- |
| ADMIN | Todos os recursos; gerencia usuários |
| GESTOR | Dashboards, exportação e status do sistema |
| COORDENADOR | Dashboards e exportação |
| ANALISTA | Analytics e exportação |
| RECEPCAO | Agenda e atendimentos |
| PROFISSIONAL | Apenas os próprios indicadores, agenda e atendimentos |

## Camadas e siglas

- **ETL/ELT:** extração, transformação e carga; aqui o pipeline também reconstrói agregações.
- **KPI:** indicador-chave de desempenho com fórmula documentada.
- **RBAC:** controle de acesso baseado em papéis.
- **SLA operacional da demo:** meta ilustrativa de 85% para comparecimento/ocupação; não é
  compromisso contratual.
