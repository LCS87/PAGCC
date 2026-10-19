# Roteiro de demonstração (≈ 10 minutos)

## Antes de começar

```bash
docker compose up --build -d
docker compose logs -f backend   # aguarde "Iniciando API" e o pipeline concluir
```

- Frontend: http://localhost:8080
- API docs: http://localhost:8000/docs
- Login: `gestor@clinicavida.example` / `Clinic@2026`

Deixe dois terminais prontos: um para `docker compose logs -f backend` e outro para
`docker compose exec backend python /app/data/quality/report.py`.

## 1. Contexto (40 s)

> “Este é um dashboard analítico para clínicas ambulatoriais. O objetivo é transformar dados
> operacionais em indicadores e ações priorizadas. Não é prontuário e não recomenda conduta
> clínica. Todos os dados são sintéticos.”

Mostre a barra lateral, o selo **Dados sintéticos** e a data de referência da demonstração.

## 2. Dashboard executivo (2 min)

1. Destaque os 11 KPIs, com comparação ao período anterior e base de cálculo.
2. Passe o mouse no ícone de informação de “Taxa de comparecimento” para mostrar a fórmula.
3. Troque o período de 30 para 90 dias e comente que os cards e gráficos se atualizam.
4. Filtre por unidade e especialidade; observe a mudança de volume.
5. Mostre o gráfico de evolução, alterne dia/semana/mês e ligue/desligue séries.
6. No painel “Operação de hoje”, leia o progresso e as duas prioridades.
7. Abra “Ver agenda”.

## 3. Agenda e operação (1 min 30 s)

1. Alterne dia/semana e navegue com as setas.
2. Filtre por status “FALTA” e depois “AGENDADA”.
3. Aponte o painel de pendências com regra explícita.
4. Abra um agendamento → mostre a linha do tempo de status e os dados administrativos.
5. Reforce: não há diagnóstico, prescrição ou dado clínico.

## 4. Profissionais (1 min)

1. Volte a “Profissionais”.
2. Mostre ocupação, comparecimento, faltas, espera e receita simulada.
3. Abra o perfil de um profissional: disponibilidade semanal, evolução e consultas recentes.
4. Comente que a ocupação usa minutos reservados ÷ disponíveis.

## 5. Analytics (2 min)

1. Abra “Analytics”.
2. Alterne a métrica da série entre agendadas, realizadas e ocupação.
3. Troque a segmentação para dia da semana e depois hora.
4. Mostre a tabela de comparação com o período anterior.
5. Abra uma definição de métrica em “Definições das métricas”.
6. Clique em **Exportar CSV** e abra o arquivo no Excel (separador `;`).

## 6. Qualidade dos dados (1 min 30 s)

1. Abra “Qualidade dos dados”.
2. Mostre a última execução (`etl_run`), contagens e status **Parcial**.
3. Explique: 7 registros inválidos são injetados de propósito para demonstrar validação.
4. Filtre por severidade **Erro** e mostre os tipos: status inválido, data impossível, valor
   negativo, duplicidade, órfão etc.
5. Rode no terminal:

```bash
docker compose exec backend python /app/data/quality/report.py
```

## 7. Perfis e autorização (1 min)

1. Saia e entre como `profissional@clinicavida.example`.
2. Mostre que só aparecem os próprios indicadores e consultas.
3. Tente acessar `/admin` → redirecionado; a API retornaria `403`.
4. Volte como `admin@clinicavida.example` e abra “Administração”: usuários, papéis, status do
   sistema e da última carga.

## 8. Engenharia (1 min)

1. Abra `docker-compose.yml`: containers `pagcc-db`, `pagcc-backend`, `pagcc-frontend`.
2. Mostre o `README` (arquitetura, execução, decisões, limitações).
3. Cite os testes: `pytest` (35 testes) e `vitest` (12 testes), lint e build no CI.
4. Encerre com as limitações: dados sintéticos, sem TLS, sem refresh token, não é software
   clínico.

## Perguntas frequentes

**Por que não React/Next?** O dashboard é autenticado e orientado a dados; Vue/Vite atende com
menos complexidade. A decisão está em `docs/decisions/001-stack.md`.

**Os números são reais?** Não. Valores, pacientes e profissionais são fictícios. Receita é
simulada e não representa caixa.

**Como os dados são reproduzíveis?** Semente fixa + âncora. A mesma combinação gera os mesmos
arquivos; o `manifest.json` guarda checksums e contagens.

**O que acontece ao reexecutar o pipeline?** Upsert por chave natural e reconstrução do
agregado; nenhum registro é duplicado.

**Por que a ocupação pode passar de 100%?** Não deveria: a disponibilidade é a soma das janelas
semanais e a agenda é gerada dentro delas. Se dados externos forem carregados, valide a
disponibilidade antes de interpretar a métrica.
