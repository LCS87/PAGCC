# Dados sintéticos

Este diretório contém o gerador, o pipeline e os artefatos das camadas de dados.

## Camadas

| Caminho | Conteúdo | Versionado? |
| --- | --- | --- |
| `raw/<âncora>/` | JSON/JSONL exatamente como gerados + `manifest.json` | não |
| `staging/<âncora>/` | CSVs normalizados + problemas de qualidade | não |
| `exports/` | CSV exportados pela API (quando usados localmente) | não |
| `generator/` | CLI do gerador | sim |
| `pipelines/` | CLI do pipeline | sim |
| `quality/` | relatório de qualidade | sim |

A lógica reutilizável fica em `backend/app/pipeline/` para ser testada e importada pela API.

## Comandos

```bash
# 1. Gerar dados para uma âncora (padrão: hoje no fuso da clínica)
python data/generator/generate.py --seed 42 --anchor 2026-10-19

# 2. Carregar (gera automaticamente se necessário)
python data/pipelines/run_pipeline.py --generate

# 3. Reprocessar sem gerar novamente
python data/pipelines/run_pipeline.py --no-generate

# 4. Relatório da última execução
python data/quality/report.py
```

Variáveis relevantes: `ETL_SEED`, `ETL_ANCHOR_DATE`, `ETL_HISTORY_MONTHS`,
`ETL_FUTURE_DAYS`, `DATABASE_URL`.

## O que é gerado

- 1 clínica, 3 unidades, 8 especialidades, 4 tipos de serviço, 12 profissionais e 92 janelas
  semanais de disponibilidade.
- ~18 meses de histórico + 14 dias de agenda futura.
- Agendamentos com distribuição de status que varia por dia da semana, horário e demanda do
  profissional.
- Atendimentos e pagamentos apenas para consultas concluídas.
- Linha do tempo de status por agendamento.
- 7 registros inválidos controlados para demonstrar rejeição.

## Reprodutibilidade

`manifest.json` registra seed, âncora, contagens, checksums SHA-256 e os casos inválidos
injetados. A mesma seed + âncora produz exatamente os mesmos arquivos de dados.

O pipeline trata cada execução como um snapshot: agendamentos de outra âncora são removidos,
evitando misturar conjuntos. Reexecutar a mesma âncora não duplica registros
(`rows_inserted = 0`).

## Qualidade

As regras estão em `backend/app/pipeline/quality.py` e documentadas em
[`docs/data-dictionary.md`](../docs/data-dictionary.md). Rejeições e avisos são gravados em
`data_quality_issue` e exibidos na tela **Qualidade dos dados**.

## Privacidade

Nenhum dado real é usado. Pacientes são referências `PAC-0001`; profissionais têm nomes
inventados e e-mails no domínio reservado `.example`. Não há CPF, telefone, endereço ou
informação clínica.
