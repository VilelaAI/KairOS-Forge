# Trilha — Seed e dados de teste

**Tema:** seeds reproduzíveis, fixtures e massa de dados para desenvolvimento e testes.
**Feature sensível:** não — mas com a regra de ouro: **seed nunca roda em produção, e dado real nunca vira fixture**.

## Requisitos típicos (rascunho — renumere e adapte na SPEC)

| ID | Requisito | Prioridade | Critério de aceite |
|---|---|---|---|
| SEED-01 | Como dev, quero um comando único de seed, para subir ambiente local com dados coerentes. | P1 | WHEN seed roda em banco vazio THEN aplicação SHALL funcionar logada com usuário de teste. |
| SEED-02 | Como dev, quero seeds idempotentes, para rodar de novo sem duplicar. | P1 | WHEN seed roda duas vezes THEN estado final SHALL ser o mesmo. |
| SEED-03 | Como QA, quero fixtures por cenário (vazio, típico, extremo), para testar estados diferentes. | P2 | WHEN fixture X carrega THEN cenário SHALL corresponder ao descrito (contagens conferidas). |
| SEED-04 | Como sistema, quero bloqueio de seed em produção, para nunca poluir dado real. | P1 | WHEN ambiente é produção THEN comando SHALL abortar com erro claro. |
| SEED-05 | Como dev, quero dados fake realistas (nomes, e-mails, datas), para o preview parecer real sem usar PII. | P2 | WHEN seed gera registros THEN nenhum dado SHALL vir de base real. |

## Tarefas e agentes sugeridos

| Tarefa | Agente | Gate sugerido |
|---|---|---|
| Estratégia de seed (ordem, volumes, cenários) | Fernanda (desenho) + Juliana | doc curto da estratégia |
| Implementação dos seeds + guarda de ambiente | Carlos | rodar 2x e comparar (SEED-02) + teste do bloqueio (SEED-04) |
| Fixtures por cenário para a suite | Ricardo | suite usando as fixtures |
| Integração no fluxo de dev (comando, README) | Beatriz | doc de setup atualizada |

## Riscos típicos

- Seed com dado real copiado de produção (vazamento de PII em todo ambiente de dev).
- Seed acoplado a IDs fixos que colidem com migrations futuras.
- Fixture gigante que deixa a suite lenta (fixtures mínimas por cenário).
- Seed que só funciona em banco recém-criado (quebra o SEED-02).

## Perguntas que o arquiteto DEVE fazer antes de fechar a SPEC

1. Quais cenários a suite precisa? (vazio, típico, volume, borda)
2. Volume de dados: dezenas (dev) ou milhares (teste de performance — aciona Vinícius)?
3. Como o ambiente é detectado (env var, config)? O bloqueio de produção usa o quê?
4. Multi-tenant precisa de seed por tenant?

## Fora do escopo desta trilha

Migração de dados reais entre ambientes (ETL — Juliana, com SPEC própria), anonimização de base de produção, geração de massa para load test.
