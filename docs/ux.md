# Decisões de produto e UX

## Princípios

1. **Cada cartão responde a uma pergunta gerencial.** Nada de gráficos decorativos.
2. **Fórmula visível.** Todo KPI tem ícone de informação com a fórmula e a base de cálculo.
3. **Cor não é o único sinal.** Status sempre combina texto, ponto colorido e posição; alertas
   exibem a regra que os gerou.
4. **Densidade controlada.** Tabelas compactas, tipografia legível e hierarquia clara entre
   título, contexto e ação.
5. **Estado explícito.** Carregando, vazio, erro e “sem resultado” têm componentes próprios.
6. **Acessibilidade básica.** Foco visível, rótulos, navegação por teclado e contraste.

## Identidade visual

| Token | Claro | Escuro |
| --- | --- | --- |
| Fundo | `#f3f6fb` | `#070f1c` |
| Superfície | `#ffffff` | `#0f1c2e` |
| Texto | `#0f172a` | `#e8eef8` |
| Primária | `#0f766e` | `#2dd4bf` |
| Informação | `#0369a1` | `#38bdf8` |
| Sucesso | `#15803d` | `#4ade80` |
| Atenção | `#b45309` | `#fbbf24` |
| Perigo | `#b91c1c` | `#f87171` |

- Tipografia de sistema (Inter/Segoe UI) para bom desempenho e legibilidade.
- Raio de 9–14 px, sombras suaves e bordas de 1 px.
- Sidebar escura fixa em desktop; gaveta sobreposta em telas menores.
- Tema persistido em `localStorage`; padrão segue `prefers-color-scheme`.

## Estrutura das telas

| Tela | Pergunta central |
| --- | --- |
| Login | Quem está acessando e com qual papel? |
| Dashboard | Como está o período e o que precisa de atenção agora? |
| Agenda | O que acontece hoje/próximos dias e o que está atrasado? |
| Profissionais | Quem está ocioso, sobrecarregado ou com muitas faltas? |
| Detalhe do profissional | Como é a disponibilidade e a evolução desse profissional? |
| Atendimentos | Quais atendimentos ocorreram, com que espera e valor? |
| Detalhe do atendimento | Quais são os dados administrativos e financeiros do registro? |
| Analytics | Qual a tendência, a composição e a comparação com o período anterior? |
| Qualidade | O pipeline executou? O que foi rejeitado e por quê? |
| Administração | Qual a versão, o estado do banco, do pipeline e dos usuários? |

## Estados

- **Carregando:** skeletons com a mesma geometria do conteúdo final.
- **Erro:** mensagem da API + botão “Tentar novamente”; erros de rede não quebram a tela.
- **Vazio:** explicação do que fazer (ajustar filtros, rodar pipeline).
- **Sem permissão:** `403` do backend; o frontend redireciona ou exibe aviso.
- **Sessão expirada:** evento global limpa o token e leva ao login com aviso.

## Filtros

- Período com atalhos 7/30/90/180 dias ancorados em `demo_today`.
- Unidade, especialidade e profissional combináveis; a lista de profissionais é reduzida pelos
  demais filtros.
- No mobile, filtros avançados ficam atrás do botão **Filtros**.
- O perfil PROFISSIONAL vê o filtro travado no próprio vínculo.

## Gráficos

- ECharts com paleta derivada das variáveis CSS; ao alternar o tema, as opções são recalculadas.
- Série temporal com seleção de métricas e granularidade dia/semana/mês.
- Barras horizontais para rankings; rosca para distribuição de status.
- Tooltip com valores formatados em pt-BR e legenda textual fora do canvas.
- Cada gráfico tem `role="img"` e `aria-label`.

## Responsividade

- 1440 px: sidebar fixa, grids de 3–4 colunas.
- 768–1023 px: sidebar em gaveta, grids de 2 colunas.
- < 640 px: uma coluna, filtros recolhidos, tabelas com rolagem horizontal, ações empilhadas.

## Acessibilidade — checklist

- [x] Link “Pular para o conteúdo”.
- [x] Foco visível em todos os controles.
- [x] `label` associado a inputs e selects.
- [x] Botões de ícone com `aria-label`.
- [x] Status com texto além da cor.
- [x] `aria-current` na paginação e `aria-pressed` nos filtros de métrica.
- [x] Contraste mínimo nas duas temas (texto principal sobre superfície).
- [x] Tabelas com cabeçalhos semânticos.
- [ ] Auditoria formal com leitor de tela (fora do escopo acadêmico).

## Limitações conhecidas

- Não há testes end-to-end automatizados no CI; a captura de telas via Playwright é um passo
  manual documentado.
- A paginação de atendimentos reinicia ao mudar filtros; não há persistência em URL.
- A agenda é uma lista agrupada por dia, não um calendário com grade horária.
- Sem i18n; interface em português do Brasil.
