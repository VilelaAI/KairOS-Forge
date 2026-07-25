# Trilha — API REST

**Tema:** endpoints tipados com validação, versionamento, erros consistentes e documentação.
**Feature sensível:** SIM quando recebe input externo ou exige auth — nesses casos, rode `/kairos-forge:analisar-ameacas`.

## Requisitos típicos (rascunho — renumere e adapte na SPEC)

| ID | Requisito | Prioridade | Critério de aceite |
|---|---|---|---|
| API-01 | Como consumidor, quero endpoints com contrato tipado e validação, para integrar com segurança. | P1 | WHEN payload inválido THEN resposta SHALL ser 400 com erros por campo; válido SHALL retornar o esquema documentado. |
| API-02 | Como consumidor, quero erros consistentes (formato único, códigos estáveis), para tratar falhas programaticamente. | P1 | WHEN erro ocorre THEN corpo SHALL seguir o formato padrão do projeto (código, mensagem, detalhes). |
| API-03 | Como consumidor, quero autenticação/autorização nos endpoints protegidos, para acessar só o que posso. | P1 | WHEN token ausente/inválido THEN 401; sem permissão THEN 403 — cobertos por teste. |
| API-04 | Como mantenedor, quero versionamento explícito, para evoluir sem quebrar clientes. | P2 | WHEN rota v1 existe THEN mudança incompatível SHALL nascer em v2, não mutar v1. |
| API-05 | Como consumidor, quero documentação viva (OpenAPI ou equivalente), para descobrir o contrato. | P2 | WHEN endpoint muda THEN doc SHALL refletir (gerada do código ou gate de CI que compara). |

## Tarefas e agentes sugeridos

| Tarefa | Agente | Gate sugerido |
|---|---|---|
| Desenho do contrato (recursos, verbos, erros, versionamento) | Thiago | revisão do contrato antes de codar |
| Implementação dos endpoints + validação | Lucas | integration por endpoint (feliz + 400/401/403) |
| Persistência/queries dos recursos | Carlos | EXPLAIN nas queries de listagem |
| Rate limit e proteção de borda (se API pública) | Nina + Lucas | teste de limite |
| Testes de contrato | Ricardo | suite de contrato verde |
| Documentação OpenAPI + exemplos | Felipe | doc gerada/validada no CI |

## Riscos e ameaças típicas (insumo pro /analisar-ameacas)

- Validação só no cliente; endpoint aceita campos extras (mass assignment).
- IDs sequenciais + falta de checagem de dono = IDOR.
- Mensagens de erro vazando stack trace/SQL.
- Falta de rate limit em endpoint público (abuso e custo).
- Paginação sem limite máximo (dump da tabela em uma chamada).

## Perguntas que o arquiteto DEVE fazer antes de fechar a SPEC

1. Quem consome? (front próprio, terceiros, mobile) — muda auth, versionamento e CORS.
2. Padrão de erro do projeto já existe ou nasce aqui?
3. Precisa de idempotência em mutações (retry de clientes)?
4. Paginação: offset ou cursor? Ordenação padrão?
5. SLA/latência esperada? (Aciona Vinícius se houver meta.)

## Fora do escopo desta trilha

GraphQL/gRPC (decisão de arquitetura à parte — ADR), webhooks de saída (trilha-pagamentos cobre o padrão), gateway/API management.
