# Trilhas por tema — índice

Blueprints de SPEC para temas que todo produto repete (ADR-0013). O `/kairos-forge:especificar` usa a trilha como **ponto de partida** quando a feature casa com um tema — requisitos típicos viram rascunho da tabela, perguntas da trilha entram na interrogação do arquiteto, riscos alimentam o `/analisar-ameacas`.

Modo guiado: o usuário pode pedir só o tema ("quero login", "preciso de checkout") — Laura reconhece a trilha e conduz. A trilha nunca substitui a interrogação: é rascunho a adaptar, não fôrma.

| Trilha | Tema | Sensível? (analisar-ameacas) |
|---|---|---|
| [trilha-auth.md](trilha-auth.md) | Login social + e-mail/senha, sessão, RLS | **Sim** — sempre |
| [trilha-pagamentos.md](trilha-pagamentos.md) | Checkout, webhooks, recibos, reconciliação | **Sim** — sempre |
| [trilha-painel-admin.md](trilha-painel-admin.md) | CRUD, filtros, permissões, auditoria | Sim se multi-tenant/PII |
| [trilha-api.md](trilha-api.md) | Endpoints tipados, validação, versionamento, docs | Sim se input externo/auth |
| [trilha-seed-dados.md](trilha-seed-dados.md) | Seeds, fixtures e dados de teste | Não (mas nunca em produção) |
| [trilha-pipeline-dados.md](trilha-pipeline-dados.md) | Ingestão, zonas com contrato, qualidade como gate, linhagem | Sim se dado pessoal/financeiro/saúde |

Regras: trilha é stack-agnóstica (o arquiteto traduz pro stack do projeto, lido de `contextos/stack.md`); IDs de requisito são renumerados na SPEC real; tarefas/gates são sugestão de partida — o plano final é da Laura.
