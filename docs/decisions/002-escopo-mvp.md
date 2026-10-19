# ADR 002 — Escopo do MVP: clínica médica ambulatorial

- **Status:** aceita
- **Data:** 2026-10-19

## Contexto

O plano original listava clínicas médicas, odontológicas, veterinárias, fisioterapia,
laboratórios e gestão hospitalar. Cobrir todos os segmentos diluiria as métricas e exigiria
modelos de domínio incompatíveis entre si.

## Decisão

O MVP atende **clínicas médicas ambulatoriais multiprofissionais**. Ficam fora do escopo:
prontuário clínico, prescrições, diagnósticos, faturamento de convênios, emissão fiscal,
internação hospitalar e a vertical veterinária.

## Justificativa

- Agenda, profissionais, unidades, atendimentos e receita simulada são suficientes para
  demonstrar engenharia de dados e análise operacional.
- Evita responsabilidades regulatórias e clínicas que não podem ser demonstradas com segurança.
- Permite métricas coerentes (comparecimento, faltas, ocupação, ticket) e dados sintéticos
  realistas.

## Consequências

- O produto é apresentado como **gestão operacional e financeira simulada**, não apoio clínico.
- Novas verticais exigirão modelo e indicadores próprios; não se reutiliza `patient_ref` para
  animal/tutor.
- Os dashboards não armazenam nenhum dado clínico sensível.

## Critérios de aceite associados

- Fórmulas documentadas e testadas.
- Filtros por período, unidade, especialidade e profissional.
- Aviso explícito de dados sintéticos em todas as telas analíticas.
