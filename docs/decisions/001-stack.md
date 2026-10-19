# ADR 001 — Vue 3 + FastAPI + PostgreSQL como stack principal

- **Status:** aceita
- **Data:** 2026-10-19

## Contexto

O projeto precisa demonstrar frontend, backend, modelagem relacional, análise de dados e
entrega sem transformar o portfólio em uma colagem de tecnologias. Havia três caminhos:
Vue/Vite + FastAPI + PostgreSQL, React/Vite + FastAPI ou Spring Boot no backend.

## Decisão

Adotar **Vue 3 + TypeScript + Vite** no frontend, **FastAPI + Pydantic + SQLAlchemy** no backend,
**PostgreSQL** como banco e **Python** no pipeline.

## Justificativa

- Vue + Vite entrega uma SPA leve, com boa ergonomia para dashboards e build rápido.
- FastAPI gera OpenAPI, valida contratos com Pydantic e mantém o código de análise no mesmo
  ecossistema do pipeline (Python/pandas).
- PostgreSQL oferece tipos relacionais, constraints, índices e recursos analíticos suficientes
  para o MVP.
- Uma stack coesa permite profundidade: testes, migrações, CI e documentação de verdade.

