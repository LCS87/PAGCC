# ADR 003 — Camadas de dados e tabela agregada diária

- **Status:** aceita
- **Data:** 2026-10-19

## Contexto

O dashboard precisa de KPIs rápidos, séries temporais e segmentações. Consultar agendamentos,
atendimentos e pagamentos a cada requisição seria caro e espalharia regras de negócio pelas
rotas. Também era necessário demonstrar separação entre dados brutos, tratados e agregados.

## Decisão

Implementar quatro camadas:

1. **Raw** — JSON/JSONL gerados, com `manifest.json` e checksums.
2. **Staging** — CSVs normalizados, produzidos após validação.
3. **Curado** — tabelas relacionais com chaves, constraints e índices.
4. **Analytics** — `analytics_daily_metric`, uma linha por dia × unidade × especialidade ×
   profissional, com contagens, minutos, receita e espera.

A API lê apenas a camada analytics para KPIs e séries. Detalhes operacionais (agenda,
atendimentos, linha do tempo) leem as tabelas curadas.

## Justificativa

- Consultas de KPI viram `SUM`/`GROUP BY` simples e previsíveis.
- Regras de cálculo ficam em `services/metrics_formulas.py` e nos testes, não nas rotas.
- A ocupação exige dias sem agendamento; por isso o rebuild inclui a disponibilidade semanal de
  todos os profissionais no intervalo.
- O pipeline pode ser reexecutado sem duplicar dados (upsert + reconstrução dos agregados).

## Consequências

- A camada analytics é reconstruída integralmente a cada execução (~7 mil linhas para 18 meses).
- Mudanças de status exigem nova execução do pipeline para refletir nos agregados.
- Para volumes muito maiores, será necessário particionar ou materializar visões incrementais.
