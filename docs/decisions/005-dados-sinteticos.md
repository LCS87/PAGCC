# ADR 005 — Dados sintéticos determinísticos e snapshot por âncora

- **Status:** aceita
- **Data:** 2026-10-19

## Contexto

O projeto precisa ser demonstrável e reproduzível, mas não pode usar dados reais de pacientes.
Ao mesmo tempo, o dashboard “de hoje” deve continuar coerente quando a demonstração ocorre dias
depois da geração.

## Decisão

- Gerar dados com `random.Random(seed)` e uma **data-âncora** explícita (`ETL_ANCHOR_DATE`).
- Registrar seed, âncora, contagens e checksums no `manifest.json` e em `etl_run`.
- Usar a âncora da última execução como `demo_today` na API e no frontend.
- Tratar cada carga como **snapshot**: agendamentos de outra âncora são removidos, mantendo um
  único conjunto coerente.
- Injetar sete casos inválidos controlados para demonstrar as regras de qualidade.

## Justificativa

- Mesma seed + mesma âncora ⇒ mesmos arquivos e mesmos agregados.
- A âncora elimina o problema de dashboards vazios quando o conjunto envelhece.
- O snapshot evita duplicação ao trocar a data de referência.
- Os casos inválidos tornam a tela de qualidade demonstrável, em vez de decorativa.

## Consequências

- Trocar a âncora substitui o conjunto anterior (não é histórico incremental).
- A âncora fica visível nos dashboards; é uma decisão explícita de demonstração.
- Dados reais, se algum dia forem usados, exigiriam outra estratégia de ingestão e governança.
