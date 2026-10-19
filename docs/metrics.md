# Catálogo de métricas

Todas as métricas são calculadas a partir de `analytics_daily_metric`, no fuso
`America/Fortaleza` (configurável por `CLINIC_TIMEZONE`). O dia de referência é a data local do
início do agendamento (`scheduled_start`).

## Conceitos-base

| Conceito | Definição |
| --- | --- |
| Agendamento | Registro em `appointment`, independentemente de ter gerado atendimento. |
| Atendimento | Registro administrativo em `attendance`, criado somente para agendamentos concluídos. |
| Agendamentos elegíveis | `scheduled_count − rescheduled_count` (exclui reagendamentos). |
| Minutos reservados | Soma da duração dos agendamentos cujo status está em CONCLUIDA, FALTA, EM_ATENDIMENTO, CONFIRMADA ou AGENDADA. Cancelamentos e reagendamentos não ocupam. |
| Minutos disponíveis | Soma das janelas semanais de `professional_availability` para os dias do período, inclusive dias sem agenda. |
| Receita bruta | Soma de `amount_charged` dos atendimentos concluídos. |
| Receita recebida | Soma de `amount_received − refund_amount` dos atendimentos concluídos. |
| Período anterior | Janela imediatamente anterior, com a mesma quantidade de dias. |

> **Status incluídos em “agendadas”:** todos, inclusive cancelamentos, faltas e reagendamentos.
> **Status incluídos em “elegíveis”:** todos, exceto REAGENDADA.
> Um agendamento futuro dentro do período ainda não realizado reduz as taxas; por isso a janela
> padrão do dashboard termina em `demo_today`.

## KPIs do MVP

### 1. Consultas agendadas — `scheduled`

- **Fórmula:** `COUNT(appointment)` no período.
- **Unidade:** contagem.
- **Inclusões:** todos os status.
- **Granularidade:** dia local do `scheduled_start`.
- **Uso:** volume de demanda e base para taxas.

### 2. Consultas realizadas — `completed`

- **Fórmula:** `COUNT(status = CONCLUIDA)`.
- **Inclusões:** apenas atendimentos concluídos; cancelamentos e faltas ficam fora.
- **Observação:** todo concluído possui `attendance` correspondente.

### 3. Taxa de comparecimento — `attendance_rate`

- **Fórmula:** `realizadas ÷ elegíveis × 100`.
- **Denominador:** `scheduled − rescheduled`.
- **Ausência de base:** retorna `null` (exibido como “—”), nunca zero enganoso.

### 4. Taxa de faltas — `no_show_rate`

- **Fórmula:** `faltas ÷ elegíveis × 100`.
- **Falta:** status `FALTA` (paciente não compareceu e não cancelou).
- **Cautela:** taxas altas por faixa horária não provam causalidade.

### 5. Taxa de cancelamento — `cancellation_rate`

- **Fórmula:** `(cancelamentos do paciente + cancelamentos da clínica) ÷ elegíveis × 100`.
- **Separação:** `cancelled_patient_count` e `cancelled_clinic_count` ficam disponíveis na camada
  analítica para análises futuras.
- **Fora do denominador:** reagendamentos.

### 6. Ocupação da agenda — `occupancy`

- **Fórmula:** `minutos reservados ÷ minutos disponíveis × 100`.
- **Reservados:** status CONCLUIDA, FALTA, EM_ATENDIMENTO, CONFIRMADA e AGENDADA.
- **Disponíveis:** janelas semanais cadastradas, somadas para todos os dias do período.
- **Limitação:** não considera feriados, bloqueios pontuais ou salas; a agenda é simplificada.

### 7. Receita bruta simulada — `revenue`

- **Fórmula:** `SUM(amount_charged)` dos atendimentos concluídos.
- **Natureza:** valor cobrado fictício, não é caixa nem faturamento real.
- **Fora:** cancelamentos, faltas e estornos.

### 8. Receita recebida simulada — `revenue_received`

- **Fórmula:** `SUM(amount_received − refund_amount)` dos atendimentos concluídos.
- **Observação:** um estorno registra valor recebido e refundido; a receita líquida é zero.

### 9. Ticket médio — `ticket`

- **Fórmula:** `receita bruta ÷ consultas realizadas`.
- **Denominador explícito:** apenas atendimentos concluídos no período.
- **Ausência de base:** `null`.

### 10. Tempo médio de espera — `wait_time`

- **Fórmula:** `média(started_at − arrived_at)` para atendimentos com ambos os horários e
  diferença não negativa.
- **Unidade:** segundos na API; a interface converte para minutos.
- **Fora:** registros sem `arrived_at` ou com chegada posterior ao início (tratados como aviso).

### 11. Taxa de reagendamento — `reschedule_rate`

- **Fórmula:** `reagendamentos ÷ total de agendamentos × 100`.
- **Definição:** agendamentos marcados como `REAGENDADA` representam o horário original liberado.
- **Observação:** o novo horário, quando existe, é um agendamento próprio.

## Variação entre períodos

- **Fórmula:** `(valor atual − valor anterior) ÷ valor anterior × 100`.
- **Base zero:** retorna `null` (interface mostra “sem base”).
- **Indicadores favoráveis:** o backend envia `favorable = up | down | neutral`; a interface usa
  isso para colorir a seta (não apenas o sinal numérico).

## Segmentações disponíveis

| Dimensão | Descrição |
| --- | --- |
| `specialty` | Especialidade do profissional no agendamento |
| `professional` | Profissional |
| `unit` | Unidade |
| `weekday` | Dia da semana local (0 = segunda) |
| `hour` | Hora local de início |
| `status` | Status do agendamento |
| `source` | Origem da marcação (telefone, WhatsApp, balcão, portal) |

## Dados ausentes e qualidade

- Registros rejeitados não entram em nenhuma métrica.
- Avisos permanecem nos dados, mas podem ser excluídos de cálculos específicos (ex.: espera).
- Percentuais sem denominador retornam `null`.
- Valores são arredondados a duas casas na API; a interface formata em pt-BR.
- Filtros de data inválidos retornam `422` com código `invalid_period`.

## Ética e comunicação

- Receita e custos são simulados; nunca apresentar como resultado real.
- Não inferir causalidade a partir de correlações.
- Alertas exibem a regra que os gerou e o período considerado.
- O produto não emite recomendação clínica.

## Validação automatizada

Os testes `backend/tests/test_metrics_formulas.py` verificam um caso conhecido:

```text
scheduled=100, completed=70, no_show=10, cancelled=10, rescheduled=5,
booked=2000, available=3000, revenue=7000, wait=3000s/100 amostras
→ elegíveis=95, comparecimento=73,68%, faltas=10,53%, cancelamento=10,53%,
  ocupação=66,67%, ticket=100,00, espera=30s
```
