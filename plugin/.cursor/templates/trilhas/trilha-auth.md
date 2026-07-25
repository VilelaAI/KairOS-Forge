# Trilha — Auth completo

**Tema:** autenticação e sessão — login social + e-mail/senha, recuperação, RLS/isolamento por usuário.
**Feature sensível:** SIM. `/kairos-forge:analisar-ameacas` é obrigatório antes de implementar.

## Requisitos típicos (rascunho — renumere e adapte na SPEC)

| ID | Requisito | Prioridade | Critério de aceite |
|---|---|---|---|
| AUTH-01 | Como visitante, quero criar conta com e-mail/senha, para acessar o produto. | P1 | WHEN cadastro válido THEN sessão criada SHALL redirecionar autenticado; senha nunca em texto puro. |
| AUTH-02 | Como visitante, quero login social (provedor do projeto), para entrar sem senha. | P1 | WHEN OAuth aprovado THEN conta criada/vinculada SHALL evitar duplicar usuário por e-mail. |
| AUTH-03 | Como usuário, quero recuperar senha por e-mail, para voltar a acessar. | P1 | WHEN token válido e não expirado THEN redefinição SHALL invalidar tokens anteriores. |
| AUTH-04 | Como sistema, quero isolamento por usuário (RLS ou equivalente), para que ninguém leia dados alheios. | P1 | WHEN usuário A consulta recurso de B THEN resposta SHALL ser 403/vazio — coberto por teste. |
| AUTH-05 | Como usuário, quero sair (logout) em todos os dispositivos, para proteger minha conta. | P2 | WHEN logout global THEN sessões/refresh tokens SHALL ser revogados. |

## Tarefas e agentes sugeridos

| Tarefa | Agente | Gate sugerido |
|---|---|---|
| Schema de usuários/sessões + RLS | Carlos (com desenho da Fernanda) | teste de isolamento (AUTH-04) |
| Fluxos de auth no backend (cadastro, login, recuperação) | Lucas | unit + integration dos fluxos |
| Telas de login/cadastro/recuperação | Marina (+ Pablo se houver design system) | teste de componente + caminho feliz e erro |
| Acessibilidade dos formulários | Ada | checagem ARIA/foco |
| Testes E2E do fluxo crítico | Ricardo | E2E verde |
| Revisão de segurança pré-PR | Helena | `/kairos-forge:revisar` |

## Riscos e ameaças típicas (insumo pro /analisar-ameacas)

- Enumeração de usuários em mensagens de erro (login e recuperação devem responder igual para conta existente/inexistente).
- Tokens de recuperação: expiração curta, uso único, invalidação em troca de senha.
- Fixação/roubo de sessão: rotação de sessão no login, cookies `HttpOnly`/`Secure`/`SameSite`.
- Força bruta: rate limit por conta e por IP; bloqueio progressivo.
- Vinculação de conta social a e-mail já existente (account takeover via provedor).

## Perguntas que o arquiteto DEVE fazer antes de fechar a SPEC

1. Quais provedores sociais? Há requisito de e-mail verificado?
2. Sessão: JWT ou sessão de servidor? Duração? Refresh?
3. Já existe tabela de usuários (brownfield) ou nasce agora? Migração de senhas?
4. Multi-tenant? (Se sim, o isolamento é por usuário E por tenant — muda AUTH-04.)
5. Requisito de MFA agora ou em follow-up (P2/P3)?

## Fora do escopo desta trilha

SSO corporativo (SAML/OIDC empresarial), RBAC fino (é da trilha-painel-admin), auditoria de acesso (idem).
