# ADR 006 — Observabilidade: logs JSON, request id e erros padronizados

- **Status:** aceita
- **Data:** 2026-10-19

## Contexto

Um dashboard depende de várias consultas e de um pipeline que pode falhar. Sem rastreabilidade,
erros de API e rejeições do ETL ficam difíceis de diagnosticar.

## Decisão

- Logs estruturados em JSON no stdout, com `timestamp`, nível, logger, mensagem e `request_id`.
- Middleware HTTP gera/propaga `X-Request-ID`, mede duração e registra método, rota, status e
  usuário autenticado (sem token nem dados pessoais).
- Erros de aplicação são serializados como `{ "error": { "code", "message", "details" } }`.
- Cada execução do pipeline grava `etl_run` e cada problema grava `data_quality_issue`.
- A tela de qualidade expõe a última execução, contagens e registros rejeitados.

## Justificativa

- Facilita correlacionar uma resposta 500 com a requisição e o usuário.
- Permite demonstrar operação e diagnóstico, não apenas telas.
- Evita formatos inconsistentes entre endpoints.

## Consequências

- Logs exigem disciplina para não incluir dados sensíveis; o projeto não registra tokens.
- Em produção, seria necessário agregar logs (ex.: Loki/ELK) e métricas (Prometheus).
- O `request_id` também é devolvido ao cliente para suporte.
