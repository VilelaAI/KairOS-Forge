# Posse de arquivo — tabela default por agente

Default da fábrica, usado no `--posse` do `quadro.py adicionar` (Passo 4 da skill).
**Adapte ao stack real do projeto** — esta tabela assume a stack default da VilelaAI, e
posse errada é pior que posse ausente: ela serializa quem podia correr junto e libera
quem devia esperar.

| Agente | File ownership |
|---|---|
| Carlos (DBA) | `migrations/`, `**/*.sql`, `db/seed*` |
| Fernanda (Arq Dados) | (não modifica — só desenha; produz docs) |
| Lucas (Backend) | `api/`, `server/`, `services/`, `src/lib/api/` |
| Gabriel (IA) | `prompts/`, `src/lib/ai/`, `src/lib/llm/` |
| Juliana (ETL) | `pipelines/`, `etl/`, `jobs/` |
| Marina (Frontend) | `src/components/`, `src/pages/`, `src/hooks/`, `src/stores/` |
| Pablo (UI) | `src/components/ui/`, `src/styles/`, `tailwind.config.*` |
| Ada (Acessib) | qualquer JSX/TSX para adicionar ARIA, mas só esses arquivos |
| Ricardo (Testes) | `**/*.test.*`, `**/*.spec.*`, `tests/`, `e2e/`, `playwright/` |
| Marcos (DevOps) | `.github/`, `Dockerfile*`, `docker-compose*`, `scripts/deploy*` |
| Renata (Observ) | `src/lib/logger.*`, `src/lib/metrics.*`, instrumentação |
| Davi (Ciência de Dados) | `notebooks/`, `analysis/`, `analises/` |
| Milena (ML) | `ml/`, `models/`, `features/` |
| Heitor (MLOps) | `ml/pipelines/`, `ml/serving/`, monitoramento de modelo |
| Yasmin (Mobile) | `app/`, `mobile/`, `src-mobile/` |
| Théo (Distribuição) | `fastlane/`, `android/app/build.gradle*`, `ios/*.plist` |
| Alice (Evals IA) | `evals/`, `**/*.eval.*`, gold sets |
| Bento (Analytics) | `dbt/`, `marts/`, `analytics/` |
| Murilo (Eventos) | `events/`, contratos de evento, config de mensageria |
| Ivan (Modernização) | (definido por SPEC — refactor atravessa módulos, sempre serializado) |
| Beatriz (Docs) | `README.md`, `docs/`, `CHANGELOG.md` |
| Felipe (API Docs) | `openapi.*`, `docs/api/`, `postman/` |
| Helena (Security) | (não modifica — audita; produz relatório) |
| Patrícia (QA) | (não modifica — planeja; produz checklist) |

## Como o quadro resolve sobreposição

Duas regras, as mesmas que CODEOWNERS e gitignore já usam:

1. **O caminho mais fundo manda.** Pablo em `src/components/ui/**` manda ali dentro,
   mesmo com Marina em `src/components/**`.
2. **O nome mais específico manda.** Ricardo em `**/*.test.*` manda nos testes dentro da
   pasta da Marina.

O que sobra depois dessas duas é colisão de verdade, e colisão de verdade serializa —
as duas tarefas nunca saem na mesma onda. Para fixar a ordem,
`quadro.py depender <task> --de <outra>`; para soltar as duas, refine os padrões.

A heurística erra de propósito para o lado conservador: **falso positivo custa
paralelismo, falso negativo custa o arquivo.**

## O que o quadro NÃO vê

Recurso compartilhado que não é arquivo — API com rate limit, ambiente de teste único,
uma migration que só pode rodar uma vez. Essa aresta continua sendo julgamento da Laura,
declarada com `--depende` ou `depender`. O quadro cobre a classe que dá para cobrir e não
finge cobrir a outra.
