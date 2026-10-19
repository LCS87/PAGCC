# ADR 004 — Autenticação JWT e autorização por papéis

- **Status:** aceita
- **Data:** 2026-10-19

## Contexto

O projeto acadêmico pode ou não incluir autenticação. Demonstrar autorização real no backend
agrega valor ao portfólio, mas aumenta o escopo do frontend e dos testes.

## Decisão

Incluir autenticação **JWT HS256** com senha em **PBKDF2-HMAC-SHA256** e autorização por papéis:

| Papel | Acesso |
| --- | --- |
| ADMIN | tudo, incluindo usuários |
| GESTOR | dashboards, exportação, status do sistema |
| COORDENADOR | dashboards, exportação |
| ANALISTA | analytics, exportação |
| RECEPCAO | agenda e atendimentos |
| PROFISSIONAL | somente os próprios indicadores e agenda |

O escopo do profissional é aplicado no backend: filtros são substituídos pelo `professional_id`
do usuário e detalhes de terceiros retornam `403`.

## Justificativa

- Autorização no servidor é o comportamento correto; esconder botões não protege dados.
- JWT é simples de demonstrar e testar, sem infraestrutura de sessão.
- PBKDF2 usa apenas a biblioteca padrão, reduzindo dependências binárias no Windows/Docker.

## Consequências

- Não há refresh token, revogação, MFA ou recuperação de senha — limitações documentadas.
- A senha de demonstração é configurável por `DEMO_PASSWORD` e deve ser trocada fora do ambiente
  local.
- O segredo JWT precisa ser forte e mantido fora do Git.
