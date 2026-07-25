# Trilha — Painel admin

**Tema:** painel administrativo — CRUD, filtros, permissões por papel e trilha de auditoria.
**Feature sensível:** SIM quando expõe PII ou é multi-tenant — nesses casos, rode `/kairos-forge:analisar-ameacas`.

## Requisitos típicos (rascunho — renumere e adapte na SPEC)

| ID | Requisito | Prioridade | Critério de aceite |
|---|---|---|---|
| ADM-01 | Como admin, quero listar/buscar/filtrar os recursos principais, para operar o produto. | P1 | WHEN filtro aplicado THEN lista SHALL paginar no servidor (não carregar tudo). |
| ADM-02 | Como admin, quero criar/editar/desativar recursos, para manter os dados. | P1 | WHEN edição salva THEN validação SHALL rodar no servidor; desativar ≠ deletar (soft delete). |
| ADM-03 | Como sistema, quero permissões por papel (ex.: admin, operador, leitura), para limitar quem faz o quê. | P1 | WHEN papel sem permissão tenta ação THEN resposta SHALL ser 403 — coberto por teste por papel. |
| ADM-04 | Como auditoria, quero registro de quem mudou o quê e quando, para rastrear ações administrativas. | P2 | WHEN mutação executa THEN log de auditoria SHALL registrar autor, alvo, antes/depois. |
| ADM-05 | Como admin, quero exportar a listagem filtrada, para análise externa. | P3 | WHEN exportação pedida THEN arquivo SHALL respeitar os filtros e permissões ativos. |

## Tarefas e agentes sugeridos

| Tarefa | Agente | Gate sugerido |
|---|---|---|
| Modelo de papéis/permissões + auditoria | Fernanda (desenho) + Carlos | teste 403 por papel |
| Endpoints CRUD com validação e paginação | Lucas | integration por recurso |
| Telas de listagem, formulários e filtros | Marina + Pablo | teste de componente |
| Acessibilidade de tabelas e formulários | Ada | checagem ARIA/teclado |
| Testes de permissão e regressão | Ricardo | matriz papel × ação |
| Revisão de segurança pré-PR (se PII/multi-tenant) | Helena | `/kairos-forge:revisar` |

## Riscos e ameaças típicas (insumo pro /analisar-ameacas)

- Autorização só no front (botão escondido ≠ permissão): toda checagem repete no servidor.
- IDOR: admin de um tenant acessando recurso de outro por ID sequencial.
- Exportação vazando colunas além da tela (PII em CSV).
- Auditoria editável ou deletável pelo próprio admin (log é append-only).
- Mass assignment em edição (campos não previstos aceitos pelo endpoint).

## Perguntas que o arquiteto DEVE fazer antes de fechar a SPEC

1. Quais recursos entram no CRUD da primeira versão? (Corte agressivo — ADM cresce depois.)
2. Papéis fixos ou configuráveis? Quem atribui papel?
3. Multi-tenant? Se sim, admin global existe?
4. Soft delete vale para tudo? Há dado com retenção legal?
5. Auditoria precisa de "antes/depois" completo ou só o evento?

## Fora do escopo desta trilha

Dashboard de métricas/BI (é feature própria), gestão de billing (trilha-pagamentos), permissões a nível de campo.
