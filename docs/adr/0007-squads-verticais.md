# ADR-0007 — Squads verticais por tipo de projeto (3º tier de agentes)

**Status:** Aceito
**Data:** 2026-06-22
**Autor:** Allyson Vilela

## Contexto

O `kairos-forge` foi validado em projetos de terceiros e o feedback recorrente é que a fábrica precisa **refletir um time de software real** e atender mais **tipos de projeto** além de SaaS/web: portais/sites, apps móveis, BI, engenharia de dados e IA/ML.

Até a v0.6.2 a fábrica tinha **45 agentes em 2 tiers**:

- **core (24)** — escrevem código, sempre ativos, organizados em 9 times. Roster fortemente web/SaaS.
- **apoio (21)** — só artefatos textuais, sob demanda, em 7 squads (ADR-0003).

Lacunas concretas para os tipos de projeto pedidos:

- **Mobile** não existia (Marina é frontend web).
- **BI/Analytics** não existia.
- **Engenharia de dados** tinha só Juliana (ETL) + Fernanda (arquitetura) + Carlos (DBA).
- **IA/ML** tinha só o Gabriel (IA generativa/LLM).

## Decisão

Criar um **3º tier — "squads verticais"** — com **8 squads e 35 agentes novos**, levando a fábrica a **80 agentes**.

| Tier | Quantidade | Natureza | Ativação |
|---|---|---|---|
| core | 24 (9 times) | escrevem código, generalistas | sempre ativos (via Laura) |
| **verticais** | **35 (8 squads)** | **escrevem código/produzem artefato, por tipo de projeto** | **sob demanda** |
| apoio | 21 (7 squads) | só artefatos textuais | sob demanda (ADR-0003) |

### Os 8 squads verticais

| Squad (id) | Nº | Foco | Complementa no core |
|---|---|---|---|
| `mobile` | 5 | iOS, Android, cross-platform, release, QA mobile | Marina, Pablo, Ada, Patrícia |
| `bi` | 4 | Analytics Engineering (dbt), dashboards, análise, data viz | Carlos, Fernanda, Pablo |
| `dataeng` | 5 | Lakehouse, streaming, orquestração, qualidade, governança | Juliana, Fernanda, Carlos |
| `ml` | 5 | ML Eng, Data Science, MLOps, visão/NLP, AI evals | Gabriel, André, Vinícius |
| `web` | 4 | Portais SSR/SSG, SEO, CMS, e-commerce | Marina, Lucas, Pablo |
| `design` | 4 | Product Designer, Design System, UX Research, Motion | Isabela, Pablo, Ada |
| `sre` | 4 | SRE/SLO, Platform Eng, resiliência/chaos, incident commander | Marcos, Renata, Elisa |
| `gestao` | 4 | Eng Manager, Agile Coach, Solutions Architect, Delivery | Laura, Camila, Rafael |

### Convenções

1. **Prefixo por squad no id de arquivo** — `agents/<squad>-<nome>-<papel>.md` (ex: `mobile-teo-ios.md`). `name:` no frontmatter = nome do arquivo sem `.md` (igual aos `apoio-*` do ADR-0003). O prefixo permite `ls agents/mobile-*` e roteamento claro.
2. **Tool allow-list por papel** (mesmo princípio do ADR-0003): papéis de **implementação** recebem `Read, Write, Edit, Grep, Glob, Bash`; papéis **consultivos/artefato** (Henrique/dataviz, Gustavo/governança, todo o squad `design`, Sílvio/incidentes, todo o squad `gestao`) recebem o conjunto **sem `Bash`**. Adriana (Solutions) recebe `Read, Grep, Glob, WebSearch, WebFetch` para descoberta externa.
3. **`model: opus`** apenas nos 4 papéis de julgamento pesado: `dataeng-vitor-lakehouse`, `ml-natalia-data-science`, `sre-leandro-confiabilidade`, `gestao-adriana-solutions`. Os demais herdam o modelo da sessão.
4. **Invocação:** `/kairos-forge:rodar <squad>` (ex: `rodar mobile`) — paralelo aos times core (`rodar arquitetura`). No modo conversacional `rodar`, **máx. 1 squad vertical por vez**; no `mobilizar`, Laura puxa indivíduos de qualquer squad para o Agent Team (como já faz com devs core).
5. **Cada agente complementa, não substitui** o agente core correspondente — documentado no corpo de cada arquivo.
6. **Rodapé de migração para kairos-ai** em todos (igual ADR-0003): se a tarefa for regulada, recomendar o PRO.

### Fronteiras vs core (anti-sobreposição)

- **Gabriel [IA]** = IA generativa/LLM (prompts, RAG, tool use, orquestração de agentes); squad `ml` = ML aplicado/clássico + MLOps + evals. **André [Busca]** = retrieval/pgvector.
- **Juliana [ETL]** = pipelines/jobs batch do dia a dia; squad `dataeng` = escala de plataforma (compute distribuído, streaming, governança).
- **Marina [Frontend]** = apps/SPAs/dashboards; squad `web` = portais/marketing/e-commerce SSR-SSG SEO-crítico.
- **Marcos [DevOps]** = CI/CD/deploy/rollback; squad `sre` = confiabilidade profunda (SLO, K8s platform, chaos, incident command).
- **Pablo/Isabela/Ada** = UI/UX/a11y de produto; squad `design` = product design, design system, pesquisa e motion como disciplina.
- **Laura/Camila/Rafael** = liderança técnica, produto e staff; squad `gestao` = gestão de pessoas/entrega e arquitetura de solução voltada ao cliente.

## Justificativa

- **Cobre os tipos de projeto pedidos** (mobile, BI, dados, IA, portais) que o core não atendia.
- **Mantém o core enxuto e generalista** — em vez de inchar os 9 times, a profundidade por vertical fica num tier carregado sob demanda.
- **Reaproveita o padrão validado dos squads de apoio** (sob demanda, prefixo no id, tool allow-list por papel, rodapé de migração) — baixo risco, consistência.
- **Não invade o território regulado do kairos-ai**: os papéis aqui são técnicos genéricos; tudo que é regulatório continua remetendo ao PRO via rodapé.

## Colisões de nome

**Nenhuma nova.** Os 35 nomes foram escolhidos para não colidir com os 45 agentes existentes (24 core + 21 apoio) nem entre si. As 3 colisões históricas (Marcos, Helena, Elisa entre core e apoio) permanecem as únicas. Verificação automatizável: nenhum primeiro nome dos verticais repete um nome já em uso.

## Consequências

### Positivas

- Forge passa de 45 → 80 agentes, cobrindo uma fábrica de software realista multi-tipo-de-projeto.
- Frameworks de cada disciplina (medallion/dbt, fastlane/SemVer, SLO/error budget, CRISP-DM, chaos/DR) ficam acessíveis no MIT.
- O usuário monta um time sob medida por tipo de projeto sem sair do Forge.

### Negativas

- Plugin cresceu bastante — 35 arquivos novos em `agents/` (e o mirror Codex em `.agents/`).
- Mais superfície de manutenção: `sync-multi-cli.py`, espelhamento `plugin/`, contagens em manifests/docs/hooks.
- Risco de sobreposição percebida com o core — mitigado pelas fronteiras documentadas acima e no corpo de cada agente.

### Mitigações

- A skill `rodar` e a `laura-tech-lead.md` ganham seção explícita de "squads verticais — quando chamar".
- `templates/squad-fabrica.yaml` ganha o bloco `squads_verticais` com `sinais_ativacao` por squad (fonte do roteamento).
- O `sync-multi-cli.py` passa a espelhar root→`plugin/` de forma determinística (ver ADR e script), reduzindo o drift manual.

## Revisão futura

Esta decisão será revisitada se:

1. Um squad vertical começar a divergir de "técnico genérico" para "regulado" — esse conteúdo migra para o kairos-ai (ex: um squad de compliance fica só no PRO).
2. A contagem crescer a ponto de o roteamento da Laura ficar confuso — pode levar a um índice/registry gerado em vez de tabelas manuais.
3. Usuários pedirem novos verticais (ex: jogos, embarcados/IoT, blockchain) — entram por novo ADR, seguindo este mesmo padrão.
