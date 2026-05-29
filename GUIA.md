# Guia de uso — embratur-skills

Manual operacional do dia a dia. Para o catálogo curto e instruções de instalação, veja o [`README.md`](README.md).

**Quem deveria ler:** desenvolvedores, tech leads e qualquer pessoa do time que vai trabalhar com Coding Agents (Lovable, Replit, Claude Code, Codex, Cursor).

**Como ler:** linearmente na primeira vez, como referência depois.

## Sumário

1. [Conceitos básicos](#1-conceitos-básicos)
2. [Como skills funcionam no Lovable e no Replit](#2-como-skills-funcionam-no-lovable-e-no-replit)
3. [Classificação — obrigatórias, essenciais, complementares, rituais](#3-classificação)
4. [Como conversar com Coding Agents](#4-como-conversar-com-coding-agents)
5. [Catálogo detalhado das 19 skills](#5-catálogo-detalhado-das-19-skills)
6. [Personas da fábrica](#6-personas-da-fábrica)
7. [Cenários reais passo a passo](#7-cenários-reais-passo-a-passo)
8. [Combinando skills](#8-combinando-skills)
9. [Cheat sheet de prompts](#9-cheat-sheet-de-prompts)
10. [Boas práticas](#10-boas-práticas)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Conceitos básicos

### O que é uma skill

Uma skill é uma **pasta** com um arquivo `SKILL.md` dentro. O arquivo tem 2 partes:

```markdown
---
name: nome-da-skill
description: Use when <gatilho>. <O que produz>.
---

# Conteúdo da skill em markdown
```

O agente lê automaticamente o frontmatter e **ativa a skill quando o contexto da conversa bate com a `description`**. Você raramente precisa invocar manualmente — basta descrever bem a tarefa.

### Skill temática vs skill de processo

| Tipo | Prefixo | Função | Exemplos |
|---|---|---|---|
| **Temática** | `squad-*` | Ativa um time de personas especializadas | `squad-backend`, `squad-qualidade` |
| **Processo** | substantivo descritivo | Conduz um ritual ou produz artefato | `spec-rastreavel`, `revisao-pre-pr` |

Skill temática responde **"quem faz?"**. Skill de processo responde **"como organizamos?"**.

### Personas embutidas

Skills temáticas embutem **personas com nome próprio** — Laura, Marina, Helena, etc. Quando você ativa `squad-backend`, o agente assume a persona de "Lucas" (Backend) ou "Carlos" (DBA) conforme a tarefa, e fala em primeira pessoa: "Lucas aqui, backend. Vou implementar o endpoint…".

A persona é uma **convenção de comportamento**, não uma entidade técnica diferente. O agente continua sendo o agente; ele apenas se identifica e age dentro do escopo daquele papel. Isso ajuda a equipe a saber **qual chapéu está sendo usado** em cada momento.

---

## 2. Como skills funcionam no Lovable e no Replit

### Lovable

- **Onde vivem:** workspace-scoped. Cada projeto Lovable tem seu próprio catálogo.
- **Como adicionar:** sidebar **Skills** → **Create skill** → cola o conteúdo do `SKILL.md`.
- **Descoberta:** Lovable indexa `name` e `description`. Quando você descreve uma tarefa, o sistema escolhe a skill cujo `description` mais combina.
- **Ativação:** automática e implícita.
- **Limite:** workspaces com muitas skills (> 50) podem ter conflito de descoberta.

### Replit Agent

- **Onde vivem:** `/.agents/skills/<nome>/SKILL.md` no projeto.
- **Como adicionar:** clonar ou copiar a pasta.
- **Descoberta:** automática.
- **Ativação:** Replit menciona explicitamente a skill ativada — útil pra debug.
- **Persistência:** skills ficam no repo. Fork carrega o catálogo junto.

### Recomendação prática para a Embratur

**Versione no Replit** quando o projeto for crítico — o catálogo viaja com o código. **Use Lovable** pra prototipagem rápida e UI. Ferramentas como Claude Code e Codex CLI também consomem a mesma pasta `skills/` — então o investimento em escrever skill boa é portátil.

---

## 3. Classificação

Nem toda skill tem o mesmo peso. Antes do catálogo, esta é a foto que mostra o que TEM que ser usado, o que deveria ser usado, e o que entra só quando o contexto pedir.

### 🔴 Obrigatórias (4) — não passa sem

Pular qualquer uma destas quebra o ciclo de qualidade. Trate como portão.

| Skill | Quando obrigatória | Risco de pular |
|---|---|---|
| `onboarding-de-projeto` | Primeira vez que o projeto adota o pacote | Próximas skills chutam comandos, convenções, gates |
| `spec-rastreavel` | Antes de toda feature não-trivial (3+ arquivos, schema novo, endpoint público) | Implementação sem critério de aceite → retrabalho |
| `aceite-contra-spec` | Depois de implementar SPEC | PR sem validação de que cumpriu o contrato |
| `revisao-pre-pr` | Antes de TODO pull request | Bug, regressão ou vulnerabilidade indo pra produção |

### 🟠 Essenciais (4) — usar sempre que cabe

Compõem a fábrica de software. Trabalho real passa por essas.

| Skill | Quando usar |
|---|---|
| `squad-arquitetura` | Antes de qualquer decisão arquitetural ou feature com 2+ componentes |
| `squad-backend` | Toda vez que mexer em código de servidor |
| `squad-frontend` | Toda vez que mexer em UI ou estado de cliente |
| `squad-qualidade` | Definir matriz de teste antes da implementação + auditoria de segurança proativa |

### 🟡 Complementares contextuais (7) — usar quando o sinal aparecer

Entram em situações específicas. Sem o sinal, são ruído.

| Skill | Sinal pra ativar |
|---|---|
| `modelo-de-ameacas` | Feature toca auth, PII, billing, upload, multi-tenant, IA com input externo |
| `mapa-arquitetural` | Projeto brownfield novo OU refactor que toca 3+ módulos |
| `squad-plataforma` | Pipeline novo, Dockerfile, deploy, observabilidade, cloud |
| `squad-produto` | Feature grande precisa virar MVP, backlog precisa ranking, vai lançar |
| `squad-documentacao` | API mudou, ADR precisa registrar decisão, demo pra stakeholder |
| `squad-conteudo-ux` | Microcopy dúbia, naming travado, taxonomia caótica |
| `squad-metricas` | Antes de lançar feature importante ("o que vamos medir?") |

### 🔵 Rituais semanais (2) — disciplina

Não obrigatórias por feature, mas obrigatórias **por semana**.

| Skill | Quando |
|---|---|
| `auditoria-do-setup` | Sexta-feira — pontuação do projeto em 5 dimensões |
| `evolucao-semanal` | Logo depois da auditoria — escolhe UMA capacidade nova pra construir |

### ⚪ Reflexão crítica (2) — quando precisar pensar diferente

Não fazem parte do fluxo padrão. Entram pra estressar uma ideia ou ouvir várias perspectivas.

| Skill | Quando |
|---|---|
| `squad-revisao-critica` | Antes de decisão irreversível ou cara |
| `mesa-de-personas` | Brainstorm livre com várias personas conversando |

### Foto resumida pra novato

Se você nunca usou skills antes, **comece usando só estas 4**:

1. `onboarding-de-projeto` (uma vez)
2. `spec-rastreavel` (antes de codar)
3. `aceite-contra-spec` (depois de codar)
4. `revisao-pre-pr` (antes do PR)

Depois de 1-2 semanas com isso fluindo, vá adicionando as essenciais (squad-*) e contextuais (modelo-de-ameacas, mapa-arquitetural, etc.) conforme o trabalho real pedir.

---

## 4. Como conversar com Coding Agents

Esta seção existe porque **a maior causa de skill que "não funciona" é prompt fraco**. Vou mostrar o padrão recomendado, anti-padrões e exemplos lado a lado.

### O padrão CARDO

Antes de mandar um prompt, garanta 5 elementos:

| Letra | O que é | Exemplo |
|---|---|---|
| **C — Contexto** | O quê e por quê. Estado atual e objetivo. | "Vou exportar relatórios CSV pros analistas porque hoje eles copiam manual do dashboard" |
| **A — Ação** | Verbo no infinitivo + objeto direto. | "implementar endpoint POST /relatorios" |
| **R — Restrições** | Tecnologia, prazo, dependências, limites. | "Node 20 + Postgres, sem mudar provedor cloud, deadline próxima sexta" |
| **D — Done-when** | Critério verificável de pronto. | "endpoint retorna 202 + job id, gera CSV em até 30s pra 10k linhas" |
| **O — Output** | Arquivo, formato, gate esperado. | "código + teste + SPEC atualizada + commit em PT-BR" |

Não é receita rígida. É checklist mental antes de digitar.

### Anti-padrões comuns

#### ❌ Prompt vago

> "ajuda no relatório"

**Por que falha:** o agente não sabe se é design, implementação, doc, bug. Vai chutar.

#### ❌ Prompt sem contexto

> "implementa POST /relatorios"

**Por que falha:** sem stack, sem schema, sem volume esperado, sem critério de aceite. O código gerado vai ser genérico — vai usar Express quando o projeto é Fastify, vai assumir Postgres quando é MongoDB.

#### ❌ Prompt enfileirado

> "faz a SPEC, implementa, testa, revisa e abre PR"

**Por que falha:** mistura múltiplas skills numa só rajada. O agente perde checkpoints, você perde controle. A SPEC pode estar errada e você só descobre no PR.

#### ❌ Prompt sem critério de aceite

> "implementa exportação de relatórios"

**Por que falha:** "pronto" pra você ≠ "pronto" pro agente. Sem WHEN/THEN/SHALL, o agente decide sozinho quando parar e geralmente para cedo demais.

#### ❌ Prompt "sem limite"

> "faz do jeito que achar melhor"

**Por que falha:** você abdicou da decisão. O agente faz a versão mais sofisticada, mais cara, ou mais errada — e você só descobre tarde.

### Receita boa lado a lado

#### Exemplo 1 — Implementar feature

❌ **Ruim:**
> "preciso de um sistema de exportação"

✅ **Bom:**
> "Vou implementar exportação de relatórios CSV pros analistas. Stack atual: Node 20 + Fastify + Postgres + Knex. Volume esperado: até 10k linhas por export, precisa rodar em background pra não bloquear a UI. Não quero adicionar serviço novo (sem fila externa nova; usa pg_cron ou job in-process). Antes de codar, ative `spec-rastreavel` pra Laura me ajudar a desenhar — quero SPEC com requisitos rastreáveis e plano de implementação por persona."

#### Exemplo 2 — Pedir revisão

❌ **Ruim:**
> "revisa esse código"

✅ **Bom:**
> "Branch `feature/exportar-relatorios`, base `main`. Diff tem ~280 linhas: 1 endpoint novo (`POST /relatorios`), 1 service, 1 migration, 2 testes. Ative `revisao-pre-pr`. Foco especial: (1) SQL injection na geração do CSV, (2) auth no endpoint, (3) idempotência (request duplicada não pode gerar 2 jobs). Critério de bloqueio: qualquer 🔴 ou 2+ 🟠 de Helena."

#### Exemplo 3 — Documentar

❌ **Ruim:**
> "documenta os endpoints"

✅ **Bom:**
> "Adicionei 5 endpoints novos em `api/relatorios.ts` (GET /, POST /, GET /:id, PATCH /:id/status, DELETE /:id). Stack: Fastify + zod pra validação. Ative `squad-documentacao` — quero o Felipe atualizando `openapi.yaml` no padrão atual do projeto (veja como `/usuarios` está documentado lá), com exemplos curl reais usando token de dev. Marca como `v0` no path. Error codes precisam aparecer com mensagem e ação sugerida."

#### Exemplo 4 — Pedir threat model

❌ **Ruim:**
> "isso tá seguro?"

✅ **Bom:**
> "Vou implementar login com Google OAuth no app público (sem MFA na v1). Usuários são turistas brasileiros — escala esperada 50k MAU. Antes de codar, ative `modelo-de-ameacas`. Helena, lista atacantes realistas pra esse contexto (não quero NSA na lista), abuse paths principais, e mitigações priorizadas por alavancagem. Output em `docs/seguranca/`."

#### Exemplo 5 — Discutir arquitetura

❌ **Ruim:**
> "monolito ou microserviços?"

✅ **Bom:**
> "Time atual: 6 devs. Produto: app de turismo MVP, lançou há 3 meses, 5k usuários ativos. Hoje monolito Node em um único repo. Pressão pra extrair o módulo de pagamentos (PCI compliance) e o módulo de busca (precisa de pgvector + workers pesados). Ative `squad-revisao-critica` com `squad-arquitetura`. Quero Álvaro e Lúcia questionando se extração agora faz sentido, e Rafael propondo as 2-3 alternativas com trade-offs. Output: ADR em `docs/adr/` com recomendação."

### Quando você não sabe qual skill usar

**Apenas descreva a tarefa.** O sistema escolhe a skill se o `description` foi escrito bem. Você só precisa nomear a skill se:

- O sistema escolheu errado (raramente acontece)
- Você quer forçar um ângulo específico ("quero Helena olhando isso", "ativa revisao-pre-pr")
- A skill é nova e a equipe ainda não internalizou os gatilhos

### Auto-checagem antes de mandar

Antes de enviar um prompt, faça 30 segundos de revisão:

- [ ] Tem **contexto** suficiente pra alguém de fora entender em 10 segundos?
- [ ] A **ação** é um verbo, não um substantivo solto?
- [ ] Listei **restrições** importantes (stack, prazo, limites)?
- [ ] Tem **critério de aceite** verificável?
- [ ] Sei qual **output** quero (arquivo, formato, gate)?

Se faltar 2 ou mais, reescreve.

---

## 5. Catálogo detalhado das 19 skills

Cada item tem: classificação, função, quando ativar, exemplo de prompt ruim/bom, output, próximo passo.

### 🔴 Obrigatórias

#### `onboarding-de-projeto`

**Faz:** entrevista de 7 perguntas, gera `CLAUDE.md`, cria estrutura de pastas (`contextos/`, `decisoes/`, `docs/specs/`, `docs/adr/`, `docs/seguranca/`).

**Quando ativar:** primeira vez em um projeto, depois de instalar o pacote.

**Tempo:** ~15 minutos.

❌ "configura aí"
✅ "Acabei de adicionar o pacote `embratur-skills` nesse projeto. Ative `onboarding-de-projeto` — me faz a entrevista das 7 perguntas e prepara a estrutura."

**Output:** projeto preparado pra rodar o ciclo das outras skills.

**Próximo passo:** primeira feature → `spec-rastreavel`.

---

#### `spec-rastreavel`

**Faz:** SPEC com requisitos rastreáveis (IDs estáveis tipo `EXP-01`, prioridade P1/P2/P3, critério WHEN/THEN/SHALL), plano de implementação por tarefa atômica, matriz de testes.

**Quando ativar:** antes de codar feature não-trivial.

**Quando NÃO ativar:** typo, rename, mudança em 1 arquivo < 20 linhas.

❌ "preciso da SPEC de exportação"
✅ "Vou implementar exportação de relatórios CSV pros analistas. Stack: Node + Fastify + Postgres + Knex. Volume até 10k linhas, async (background job). Não quero serviço novo. Ative `spec-rastreavel` — quero Laura fazendo triagem e Diego/Fernanda escrevendo a SPEC com requisitos rastreáveis."

**Output:** `docs/specs/SPEC-NNN-<slug>.md`.

**Próximo passo:** `squad-backend` ou `squad-frontend` pra implementar.

---

#### `aceite-contra-spec`

**Faz:** compara código implementado com requisitos da SPEC. Roda gates declarados. Devolve veredicto (aprovado / aprovado com ressalvas / bloqueado) e matriz de rastreabilidade.

**Quando ativar:** depois de implementar SPEC, antes de `revisao-pre-pr`.

**Não corrige** — recomenda quem corrige.

❌ "tá pronto?"
✅ "Terminei a implementação da SPEC-007 (exportar relatórios). Ative `aceite-contra-spec`. Base é `main`, branch é `feature/exportar-relatorios`. Rode os gates declarados na SPEC. Quero veredicto explícito por requisito."

**Output:** `docs/specs/validacoes/VALIDACAO-SPEC-NNN-YYYY-MM-DD.md`.

**Diferença vs `revisao-pre-pr`:** aceite valida **cumprimento de contrato**; revisão valida **qualidade de código**.

---

#### `revisao-pre-pr`

**Faz:** revisão multi-dimensão do diff. Helena (segurança) e Patrícia (QA) sempre rodam. Vinícius, Marcos, Carlos e Ada entram conforme o escopo. Cada uma produz parecer com severidade 🔴🟠🟡🔵.

**Quando ativar:** antes de abrir PR, antes de push pra branch protegida.

**Bloqueia automaticamente** se: 🔴 de qualquer revisora, ou 2+ 🟠.

**Limite:** diff > 500 linhas é devolvido com pedido pra fatiar.

❌ "revisa o PR"
✅ "Branch `feature/exportar-relatorios`, ~280 linhas de diff vs `main`. Já rodei `aceite-contra-spec` e ficou aprovado. Ative `revisao-pre-pr`. Foco extra em SQL injection no gerador de CSV e em idempotência do endpoint. Critério de bloqueio: padrão (qualquer 🔴, ou 2+ 🟠)."

**Output:** relatório consolidado com veredicto agregado.

**Próximo passo:** abrir PR (se aprovado) ou corrigir (se bloqueado).

---

### 🟠 Essenciais

#### `squad-arquitetura`

**Faz:** desenha solução técnica antes de codar. Triagem de tamanho, interrogação do problema, 2-3 abordagens com trade-offs explícitos.

**Personas:** Laura (Tech Lead), Rafael (Staff), Diego (Sistemas), Fernanda (Dados), Thiago (Integrações).

❌ "qual a melhor arquitetura?"
✅ "Preciso desenhar a feature de busca semântica no catálogo de destinos turísticos. Stack: Postgres + pgvector já decidido. Volume catálogo: ~50k destinos, queries esperadas ~100/min. Ative `squad-arquitetura`. Quero Diego coordenando com André (busca) e Fernanda (índice). 2-3 abordagens com trade-off custo/latência/manutenção. Recomendação ao final."

**Output:** ADR em `docs/adr/` ou SPEC em `docs/specs/`.

**Próximo passo:** `spec-rastreavel` (se virar feature) ou implementação direta (se for pequeno).

---

#### `squad-backend`

**Faz:** implementa endpoints, services, validação, transações, migrations, jobs, integrações de IA, busca.

**Personas:** Lucas (Backend), Carlos (DBA), Vinícius (Performance), Juliana (Data Eng), Gabriel (IA), André (Busca).

**File ownership:** cada persona tem áreas exclusivas. Se duas precisam do mesmo arquivo, serialize.

❌ "implementa o endpoint"
✅ "Implementa T2 da SPEC-007 (endpoint POST /relatorios). Stack: Fastify 4 + Knex. Validação com zod. Schema do payload já está na SPEC. Ative `squad-backend`. Quero Lucas implementando + Carlos validando a query nova. Done-when: endpoint retorna 202 + jobId, payload inválido retorna 400 estruturado, idempotente por jobId. Gate: `npm test -- relatorios`."

**Output:** código + teste mínimo (caminho feliz + 1 erro) + commit em PT-BR.

**Próximo passo:** `aceite-contra-spec` quando T2 marcar como completed.

---

#### `squad-frontend`

**Faz:** telas, componentes, hooks, estado, design tokens, acessibilidade.

**Personas:** Marina (Frontend), Pablo (UI), Isabela (UX), Ada (Acessibilidade).

❌ "cria a tela"
✅ "Implementa a tela `RelatoriosExport` (T3 da SPEC-007). Stack: React + Vite + TanStack Query. Já temos o `DateRangePicker` em `src/components/ui/`. Ative `squad-frontend`. Quero Marina criando a tela e o hook `useExportarRelatorio`, Pablo garantindo que usa os tokens do design system. Ada audita acessibilidade ao final. Estados obrigatórios: loading/vazio/erro/sucesso. Done-when: usuário consegue exportar, vê toast de sucesso e baixa o CSV."

**Output:** componente com 5 estados cobertos + teste de render + auditoria a11y.

**Próximo passo:** `aceite-contra-spec`.

---

#### `squad-qualidade`

**Faz:** estratégia de teste, escrita de testes, auditoria de segurança proativa (diferente de `revisao-pre-pr` que é pós-código).

**Personas:** Patrícia (QA Lead), Ricardo (Testes), Helena (Security).

❌ "tem teste?"
✅ "Acabei de implementar o endpoint POST /relatorios. Ative `squad-qualidade`. Patrícia define matriz de cobertura pra esses 3 requisitos (EXP-01, EXP-02, EXP-03), Ricardo escreve os testes que faltam, Helena audita SQL injection no gerador de CSV e auth no endpoint. Gate de cobertura: caminho feliz + 1 erro por requisito P1."

**Output:** matriz, testes implementados, parecer de segurança com severidade.

**Diferença vs `revisao-pre-pr`:** entra **durante** a implementação, não no fim.

---

### 🟡 Complementares contextuais

#### `modelo-de-ameacas`

**Faz:** threat model coordenado por Helena. Ativos, trust boundaries, entrypoints, atacante realista, abuse paths, mitigações priorizadas.

**Quando ativar:** auth, registro, MFA, PII, dados financeiros/saúde, upload, multi-tenant, IA com input externo.

**Read-only.** Salva em `docs/seguranca/AMEACAS-<feature>-YYYY-MM-DD.md`.

❌ "tem segurança nisso?"
✅ "Vou implementar SSO via Google OAuth no portal público (sem MFA na v1). Público: turistas brasileiros, escala esperada 50k MAU. Ative `modelo-de-ameacas`. Helena coordena. Quero atacantes realistas pra esse contexto (sem NSA), 3-5 abuse paths principais, e mitigações priorizadas por alavancagem com camada apropriada (não quero 'esconder botão' como mitigação)."

**Output:** threat model + mitigações priorizadas + sinais de detecção.

---

#### `mapa-arquitetural`

**Faz:** inventário estrutural de código existente — componentes, acoplamento, duplicação, bounded contexts, plano de decomposição incremental.

**Read-only.** Salva em `docs/arquitetura/MAPA-YYYY-MM-DD.md`.

❌ "olha esse repo"
✅ "Acabei de herdar esse repo (80k linhas, monolito Node). Quero entender o que tem antes de mexer em qualquer coisa. Escopo: `apps/api/` e `apps/web/`. Não auditar `legacy/`. Ative `mapa-arquitetural`. Diego coordena com Fernanda (banco) e Rafael (padrões). Foco em acoplamento entre módulos e duplicação de domínio. Plano incremental de decomposição."

**Próximo passo:** `spec-rastreavel` pra movimentos médios, ADR pra grandes.

---

#### `squad-plataforma`

**Faz:** infraestrutura, CI/CD, deploy, observabilidade, FinOps, secrets, SLOs.

**Personas:** Elisa (Cloud), Marcos (DevOps), Renata (Observabilidade).

❌ "configura o deploy"
✅ "Preciso configurar deploy automático na main pro backend (Node 20, Dockerfile já existe). Provedor é Fly.io. Ative `squad-plataforma`. Marcos coordena: workflow do GitHub Actions, health check obrigatório antes de subir tráfego, rollback automático se health check falhar 3x em 5 min, notificação no Slack. Renata adiciona correlation ID no logger. Sem mudar provedor."

---

#### `squad-produto`

**Faz:** escopo, fatiamento de MVP, priorização ICE, plano de lançamento em 3 fases, audit de ROI.

**Personas:** Camila (PM), Hugo (Priorização), Sofia (Lançamento), Rui (Audit).

❌ "como faço isso?"
✅ "Stakeholder pediu 'sistema completo de relatórios com BI, drill-down e share por email'. Ative `squad-produto`. Quero Camila fatiando em 3 incrementos (MVP, V2, V3), Hugo aplicando ICE nos itens, e Rui questionando ROI de cada bloco. Output em `docs/specs/`. Importante: MVP precisa ter critério de aceite verificável e métrica de sucesso."

---

#### `squad-documentacao`

**Faz:** README, runbook, OpenAPI, ADR, apresentação executiva.

**Personas:** Beatriz (Technical Writer), Felipe (API Docs), Marcos [Specs] (ADR), Renato (doc de usuário), Helena [Apresentação] (demos).

❌ "documenta a API"
✅ "Adicionei 5 endpoints novos em `api/relatorios.ts`. Ative `squad-documentacao`. Felipe atualiza `openapi.yaml` no padrão atual (veja como `/usuarios` está lá), com exemplos curl reais e error codes. Beatriz atualiza o README na seção 'Endpoints'. Marca como `v0`. Done-when: cada endpoint tem método, path, payload, exemplos de sucesso e erro."

---

#### `squad-conteudo-ux`

**Faz:** microcopy, voz, naming, taxonomia, revisão textual.

**Personas:** Celina, Cora, Elisa [Naming], Bruno, Letícia.

❌ "texto da tela"
✅ "Empty state da tela `RelatoriosExport` está vazio e o botão tá escrito 'OK'. Tom do produto: formalidade 5, entusiasmo 4 (definimos isso na semana passada). Ative `squad-conteudo-ux`. Celina escreve empty state seguindo a fórmula (por que vazio + o que pode fazer + ação primária) e revisa o botão (verbo + objeto). Letícia confere consistência com outras telas."

---

#### `squad-metricas`

**Faz:** tracking plan, KPIs, AARRR, A/B testing, feature flags, DORA, DX.

**Personas:** Lia, Otávio, Vera, Tomás, Clara, Enzo.

❌ "como meço sucesso?"
✅ "Vou lançar a feature de exportação semana que vem. Hoje 0% dos analistas usam o dashboard pra extrair dado. Hipótese: 60% vão migrar pra exportação em 4 semanas. Ative `squad-metricas`. Otávio define a métrica primária e guardrails, Lia escreve o tracking plan (eventos `relatorio_export_solicitado`, `relatorio_export_concluido`, etc.), Vera propõe rollout progressivo com feature flag (10% → 50% → 100%)."

---

### 🔵 Rituais semanais

#### `auditoria-do-setup`

**Faz:** pontua o projeto de 0-100 em 5 dimensões (Fundação, Pipeline, Guardrails, Conhecimento, Estrutura). Devolve top 3 lacunas ranqueadas por alavancagem.

**Read-only.** Salva em `decisoes/auditorias/AUDIT-YYYY-MM-DD.md`.

❌ "auditoria"
✅ "Sexta. Ative `auditoria-do-setup` nesse projeto. Quero pontuação por dimensão, top 3 lacunas ranqueadas por alavancagem (não por score baixo), e comparação com a auditoria anterior se houver. Salva o relatório."

**Próximo passo:** `evolucao-semanal`.

---

#### `evolucao-semanal`

**Faz:** entrevista de 5 perguntas (repetição, atrito, teste do estagiário, restrição, alavanca). Identifica **UMA** capacidade nova pra construir na próxima semana.

❌ "o que vamos fazer essa semana?"
✅ "Auditei agora. Top 3 lacunas: sem CODEOWNERS, sem tracking plan, sem runbook do deploy. Ative `evolucao-semanal`. Quero as 5 perguntas e escolha de UMA capacidade pra construir até a próxima sexta, baseada no que doeu essa semana (não no que falta em geral)."

**Output:** `decisoes/evolucoes/EVOL-YYYY-MM-DD.md` com 1 item escolhido + descartados.

---

### ⚪ Reflexão crítica

#### `squad-revisao-critica`

**Faz:** pre-mortem, red team, debate estruturado, inversão de Munger, princípios fundamentais.

**Personas:** Álvaro (Inversão), Lúcia (Princípios), Félix (Red Team), Dante (Desbloqueio).

❌ "o que você acha?"
✅ "Tô decidindo entre migrar pro Postgres 16 agora (próximo sprint) ou esperar 6 meses até quando a major version atualizar de novo. Migração é irreversível em horas mas requer dia inteiro de janela. Ative `squad-revisao-critica`. Álvaro faz pre-mortem das duas opções, Lúcia confronta com princípio da reversibilidade, Félix questiona se decidir agora é mesmo necessário. Veredicto recomendado ao final."

**Output:** parecer adversarial em `docs/decisoes/REVISAO-*.md`.

---

#### `mesa-de-personas`

**Faz:** modo conversacional onde várias personas falam em primeira pessoa.

**Quando ativar:** brainstorm livre, code review conversacional, debate de arquitetura sem estrutura formal.

❌ "discussão sobre arquitetura"
✅ "Quero ouvir Diego, Fernanda e Vinícius discutindo se a feature de busca semântica deveria rodar como worker separado ou inline no endpoint. Não quero SPEC ainda, é discussão. Ative `mesa-de-personas`. Cada um se apresenta, fala da própria dimensão e referencia os outros pelo nome."

---

## 6. Personas da fábrica

São 45 personas. Lista por squad:

### `squad-arquitetura`

| Persona | Papel | Especialidade |
|---|---|---|
| Laura | Tech Lead | Coordenação, triagem, Definition of Done |
| Rafael | Staff Engineer | Decisões irreversíveis, padrões |
| Diego | Arquiteto de Sistemas | Fluxos, contratos, eventos |
| Fernanda | Arquiteta de Dados | Schemas, índices, RLS |
| Thiago | Arquiteto de Integrações | APIs, OAuth, idempotência |

### `squad-backend`

| Persona | Papel | Especialidade |
|---|---|---|
| Lucas | Backend Engineer | Endpoints, services, transações |
| Carlos | DBA | Migrations, queries, RLS |
| Vinícius | Performance Engineer | Profiling, bundle, load test |
| Juliana | Data Engineer | ETLs, jobs, qualidade de dados |
| Gabriel | AI Engineer | LLM, RAG, prompt, evals |
| André | Search Engineer | Full-text, vetorial, hybrid |

### `squad-frontend`

| Persona | Papel | Especialidade |
|---|---|---|
| Marina | Frontend Engineer | Telas, componentes, hooks |
| Pablo | UI Engineer | Visual, tokens, dashboards |
| Isabela | UX Researcher | Jornadas, heurísticas |
| Ada | Accessibility Engineer | ARIA, contraste, axe-core |

### `squad-plataforma`

| Persona | Papel | Especialidade |
|---|---|---|
| Elisa | Cloud Architect | Provedor, FinOps, residência |
| Marcos | DevOps / SRE | CI/CD, Docker, rollback |
| Renata | Observability Engineer | Logs, métricas, traces |

### `squad-qualidade`

| Persona | Papel | Especialidade |
|---|---|---|
| Patrícia | QA Lead | Estratégia, triagem, regressão |
| Ricardo | Test Automation Engineer | Unit, integration, e2e |
| Helena | Security Engineer | OWASP, RLS, PII |

### `squad-produto`

| Persona | Papel | Especialidade |
|---|---|---|
| Camila | PM Técnico | User stories, MVP slice |
| Hugo | Priorização | ICE, Value Equation |
| Sofia | Lançamento | Checklist em 3 fases |
| Rui | Audit | TCO, ROI, desperdício |

### `squad-documentacao`

| Persona | Papel | Especialidade |
|---|---|---|
| Beatriz | Technical Writer | README, runbook, changelog |
| Felipe | API Documentation Engineer | OpenAPI, curl, error codes |
| Marcos [Specs] | Narrativa estruturada | ADR em 6 blocos |
| Renato | Doc de usuário | DITA simplificado |
| Helena [Apresentação] | Demos para stakeholder | Framework Sparkline |

### `squad-conteudo-ux`

| Persona | Papel | Especialidade |
|---|---|---|
| Celina | Microcopy | Botão, erro, empty state |
| Cora | Voz | Tom em 4 dimensões |
| Elisa [Naming] | Naming | Scoring em 5 dimensões |
| Bruno | Taxonomia | MECE em 3 níveis |
| Letícia | Revisão textual | 4 lentes |

### `squad-metricas`

| Persona | Papel | Especialidade |
|---|---|---|
| Lia | Instrumentação | Tracking plan |
| Otávio | KPIs | Norte-métrica, AARRR |
| Vera | Growth / A-B | Feature flags, experimentos |
| Tomás | DORA | Deployment frequency, MTTR |
| Clara | Comunidade / DX | Contributor ladder |
| Enzo | Developer Experience | Developer journey |

### `squad-revisao-critica`

| Persona | Papel | Especialidade |
|---|---|---|
| Álvaro | Inversão | Munger, pre-mortem |
| Lúcia | Princípios | SOLID, YAGNI, Conway |
| Félix | Red Team | Failure modes |
| Dante | Desbloqueio | Timeboxing, desacoplamento |

### Colisões de nome

| Nome curto | Como desambiguar |
|---|---|
| **Marcos** | Marcos (DevOps, `squad-plataforma`) vs Marcos [Specs] (ADR, `squad-documentacao`) |
| **Helena** | Helena (Security, `squad-qualidade`) vs Helena [Apresentação] (demos, `squad-documentacao`) |
| **Elisa** | Elisa (Cloud, `squad-plataforma`) vs Elisa [Naming] (naming, `squad-conteudo-ux`) |

Sempre desambigue com o sufixo do papel.

---

## 7. Cenários reais passo a passo

Cinco jornadas narradas. Cada uma com o prompt **literal** que você manda em cada etapa.

### Cenário 1 — Sua primeira feature usando o pacote

**Situação:** projeto novo, equipe acabou de adicionar `embratur-skills`. Quer implementar "exportação de relatórios CSV pros analistas".

**Passo 1 — Configurar o projeto** (uma única vez)

> "Acabei de adicionar `embratur-skills`. Ative `onboarding-de-projeto` — me faz a entrevista das 7 perguntas."

Responde com paragrafos (não frases curtas), em PT-BR, sendo explícito sobre stack e convenções. Resultado: `CLAUDE.md` + `contextos/` + `decisoes/` criados.

**Passo 2 — Desenhar a feature**

> "Vou implementar exportação de relatórios CSV pros analistas. Stack: Node 20 + Fastify + Postgres + Knex. Volume até 10k linhas, precisa rodar em background pra não bloquear UI. Não quero serviço novo (sem fila externa). Ative `spec-rastreavel`."

Resposta: Laura entra, classifica como "médio", chama Diego e Fernanda. Eles fazem perguntas (formato? destino dos arquivos? quem dispara?). Após 5-10 trocas, SPEC sai em `docs/specs/SPEC-001-exportar-relatorios.md` com requisitos `EXP-01`, `EXP-02`, `EXP-03`.

**Passo 3 — Implementar backend**

> "Implementa T1 (migration) e T2 (endpoint POST /relatorios) da SPEC-001. Ative `squad-backend`."

Carlos faz a migration. Lucas implementa o endpoint. Ricardo (vem do `squad-qualidade` se a SPEC pedir) escreve os testes. Cada um marca a task como completed e Laura cobra Definition of Done.

**Passo 4 — Implementar frontend** (em paralelo ao passo 3 se file ownership permite)

> "Implementa T3 (tela RelatoriosExport) da SPEC-001. Estado loading/vazio/erro/sucesso obrigatórios. Ative `squad-frontend`."

Marina implementa, Pablo cuida do visual, Ada audita acessibilidade.

**Passo 5 — Validar contra SPEC**

> "Tudo da SPEC-001 implementado. Ative `aceite-contra-spec` na branch atual contra `main`."

Roda gates declarados na SPEC. Veredicto: aprovado, aprovado com ressalvas ou bloqueado. Se bloqueado, volta pro passo 3 ou 4.

**Passo 6 — Revisão pré-PR**

> "Aprovado contra SPEC. Ative `revisao-pre-pr`."

Helena audita segurança, Patrícia audita cobertura, Vinícius olha performance. Veredicto agregado. Se passar, abre PR.

**Tempo total típico:** 1-2 dias úteis pra feature média.

---

### Cenário 2 — Bug crítico em produção

**Situação:** alerta dispara — endpoint `POST /relatorios` retornando 500 em 30% das requisições desde 14h.

**Passo 1 — Reproduzir e triar**

> "Alerta: POST /relatorios com 30% de 500 desde 14h. Logs mostram erro 'connection terminated unexpectedly' do pool. Ative `squad-qualidade`. Patrícia faz triagem (severidade, frequência, workaround), Ricardo escreve repro mínima."

**Passo 2 — Investigar (se a causa não for óbvia)**

> "Repro confirmou: pool esgotando depois de 200 requests/min. Suspeita: conexões não devolvidas em job background. Ative `squad-backend`. Lucas investiga o ciclo de vida do connection no service `exportarRelatorio`."

**Passo 3 — Correção mínima**

> "Causa confirmada: `knex.transaction` não está fechando em caminho de erro. Lucas corrige + Ricardo adiciona teste de regressão pra esse caso."

**Passo 4 — Revisão acelerada**

> "Correção em 1 arquivo, 12 linhas, 1 teste novo. Ative `revisao-pre-pr` — foco em correção + teste de regressão. Não precisa de revisão completa."

**Passo 5 — Deploy monitorado**

> "Aprovado. Ative `squad-plataforma`. Marcos faz deploy com rollback automático se taxa de 500 não cair pra <1% em 10 min."

**Tempo típico:** 1-3 horas se a causa for clara.

---

### Cenário 3 — Refactor de módulo brownfield

**Situação:** módulo `pagamentos/` tem 8 hotspots de bug nos últimos 3 meses, acoplamento alto com `usuarios/` e `auditoria/`. Time quer extrair.

**Passo 1 — Mapear antes de tocar**

> "Quero entender o módulo `pagamentos/` antes de extrair. Escopo: só esse diretório. Ative `mapa-arquitetural`. Diego coordena com Fernanda (banco) e Rafael (padrões)."

Saída: `docs/arquitetura/MAPA-2026-05-29.md` com componentes, acoplamento, duplicação, plano incremental.

**Passo 2 — Questionar a decisão**

> "Mapa mostra que `pagamentos/` está acoplado com `usuarios/` em 14 pontos. Mover agora vai exigir alterar `usuarios/` também. Ative `squad-revisao-critica`. Álvaro: pre-mortem da extração. Lúcia: confronta com Conway. Félix: red team. Recomendação ao final."

**Passo 3 — ADR**

> "Time decidiu extrair em 2 fases (primeiro desacoplar do `usuarios/`, depois extrair). Ative `squad-documentacao`. Marcos [Specs] escreve ADR-005 com contexto, decisão, alternativas, consequências e plano de reversão."

**Passo 4 — Movimentos pequenos primeiro**

> "Ative `spec-rastreavel` para Fase 1: desacoplar `pagamentos/` de `usuarios/`. Lista de imports cruzados está no mapa. Tarefa por arquivo, reversível em horas."

A partir daqui o fluxo segue como feature normal.

---

### Cenário 4 — Sexta-feira (ritual semanal)

**Situação:** sexta de manhã. Sprint terminou ontem.

**Passo 1 — Auditar**

> "Sexta. Ative `auditoria-do-setup`. Quero pontuação por dimensão e top 3 lacunas ranqueadas por alavancagem."

Saída: pontuação tipo "Fundação 18/20, Pipeline 14/20, Guardrails 8/20, Conhecimento 12/20, Estrutura 9/20 = 61/100" + top 3 lacunas.

**Passo 2 — Evoluir**

> "Auditei. Ative `evolucao-semanal`. Quero as 5 perguntas e escolha de UMA capacidade pra construir até a próxima sexta."

Você responde 5 perguntas sobre a semana. Sai 1 candidato escolhido (ex.: "hook de pre-commit pra rodar lint em arquivos modificados").

**Passo 3 — Especificar o item escolhido**

> "Item da semana: pre-commit hook de lint. Ative `spec-rastreavel` pra essa mudança pequena (SPEC curta ou plano inline)."

Implementa durante a semana. Próxima sexta: ciclo recomeça.

---

### Cenário 5 — Antes de lançar feature importante

**Situação:** exportação de relatórios pronta. Lançamento é segunda.

**Passo 1 — Plano de lançamento**

> "Vou lançar exportação de relatórios na segunda. ~200 analistas vão ver isso. Hoje 0% usa exportação. Ative `squad-produto`. Sofia faz checklist de pré-lançamento + plano de rollout progressivo (1% → 10% → 50% → 100% em 5 dias)."

**Passo 2 — Métricas**

> "Ative `squad-metricas`. Otávio define métrica primária (% de analistas que exportam pelo menos 1 relatório em 7 dias) e guardrails (taxa de erro do endpoint, latência p95, NPS dos analistas). Lia escreve tracking plan."

**Passo 3 — Infra do lançamento**

> "Ative `squad-plataforma`. Marcos cria feature flag `exportar_relatorios_v1`, configura rollback automático se taxa de erro > 5%. Renata adiciona dashboard de saúde no Grafana."

**Passo 4 — Comunicação**

> "Ative `squad-conteudo-ux`. Celina escreve a mensagem do empty state, o tooltip do botão, e o toast de sucesso. Cora confere que o tom bate com o produto. Letícia revisa consistência com outras telas."

**Passo 5 — Lançar**

Segunda, manhã. Marcos abre o feature flag pra 1%. Equipe monitora dashboard. Se 4h sem incidente, sobe pra 10%. Cinco dias depois: 100%.

**Passo 6 — Retro (2 semanas depois)**

> "Lançamos há 2 semanas. Hoje 38% dos analistas usaram pelo menos 1 vez. Ative `evolucao-semanal` em contexto de retro: o que aprendemos? O que mudou no setup?"

---

## 8. Combinando skills

### Encadeamento natural

A maioria dos fluxos é uma cadeia. O output de uma skill aponta pra próxima — os SKILL.md fazem referência cruzada.

Cadeia padrão pra feature: `spec-rastreavel` → `modelo-de-ameacas`? → `squad-arquitetura`? → `squad-backend`/`squad-frontend` → `aceite-contra-spec` → `revisao-pre-pr` → PR.

### Paralelismo prudente

`squad-backend` e `squad-frontend` podem rodar "em paralelo" se o file ownership for disjunto. No Lovable/Replit, "paralelo" significa: personas se intercalam na mesma conversa, sem esperar a outra acabar.

Se duas personas precisam do mesmo arquivo, **serialize**. Uma termina, marca como completed, outra entra.

### Substituição contextual

| Em vez de... | Use... | Quando |
|---|---|---|
| `squad-backend` | `mesa-de-personas` | Brainstorm antes de implementar |
| `revisao-pre-pr` | `squad-qualidade` | Durante implementação, não no fim |
| `spec-rastreavel` | implementação direta | Bug pequeno, < 20 linhas em 1 arquivo |
| `auditoria-do-setup` | `mapa-arquitetural` | Foco é estrutura do código, não setup do projeto |

### Skills que NUNCA devem rodar juntas

- `aceite-contra-spec` antes de implementar — não há código pra validar.
- `revisao-pre-pr` em diff > 500 linhas — devolve com pedido pra fatiar.
- `modelo-de-ameacas` em mudança trivial — vira ruído.
- `evolucao-semanal` sem `auditoria-do-setup` antes — falta o input.

---

## 9. Cheat sheet de prompts

Prompts prontos pra copiar. Substitua os `<placeholders>`.

### Onboarding (uma vez por projeto)

```
Acabei de adicionar `embratur-skills`. Ative `onboarding-de-projeto` — me faz a entrevista das 7 perguntas e prepara a estrutura.
```

### Especificar feature

```
Vou implementar <feature em 1 frase>. Stack: <linguagens, frameworks, banco>. Volume esperado: <números>. Restrições: <o que evitar>. Ative `spec-rastreavel`.
```

### Threat model

```
Vou implementar <feature sensível>. Público: <quem usa>. Dados envolvidos: <PII, financeiro, etc>. Ative `modelo-de-ameacas`. Atacantes realistas pra esse contexto.
```

### Decisão arquitetural

```
Preciso desenhar <o quê>. Stack atual: <stack>. Contexto: <restrições, volume, deadline>. Ative `squad-arquitetura`. 2-3 abordagens com trade-off custo/latência/manutenção. Recomendação ao final.
```

### Implementar backend

```
Implementa <tarefa T-X da SPEC-NNN | feature em 1 frase>. Stack: <stack>. Done-when: <critério verificável>. Gate: <comando de teste>. Ative `squad-backend`.
```

### Implementar frontend

```
Implementa <tela ou componente>. Stack: <React/Vue/etc + libs>. Estados obrigatórios: loading/vazio/erro/sucesso. Done-when: <critério>. Ative `squad-frontend`.
```

### Definir testes

```
Acabei de implementar <o quê>. Requisitos rastreáveis: <IDs>. Ative `squad-qualidade`. Patrícia faz matriz, Ricardo escreve testes que faltam, Helena audita segurança.
```

### Documentar API

```
Adicionei <N> endpoints novos em <arquivo>. Padrão atual do projeto: ver como <endpoint exemplo> está em <openapi.yaml ou docs/api/>. Ative `squad-documentacao`. Felipe coordena.
```

### Lançamento

```
Vou lançar <feature> em <data>. Público alvo: <quem>. Hipótese de impacto: <métrica esperada>. Ative `squad-produto` + `squad-metricas` + `squad-plataforma`. Sofia: checklist e rollout. Otávio: métricas. Marcos: feature flag e rollback.
```

### Validar contra SPEC

```
Terminei a SPEC-NNN. Branch <nome>, base <main>. Ative `aceite-contra-spec`. Rode os gates declarados na SPEC. Veredicto explícito por requisito.
```

### Revisão pré-PR

```
Branch <nome>, ~<N> linhas de diff vs <base>. Ative `revisao-pre-pr`. Foco extra em <preocupações específicas>. Critério de bloqueio: padrão.
```

### Auditoria semanal

```
Sexta. Ative `auditoria-do-setup`. Pontuação por dimensão e top 3 lacunas ranqueadas por alavancagem.
```

### Evolução semanal

```
Auditei. Top 3 lacunas: <copia da auditoria>. Ative `evolucao-semanal`.
```

### Pre-mortem antes de decisão grande

```
Tô decidindo entre <A> e <B>. Reversibilidade: <horas/dias/semanas>. Custo se errar: <descrição>. Ative `squad-revisao-critica`. Álvaro pre-mortem, Lúcia princípios, Félix red team. Veredicto recomendado.
```

### Brainstorm livre

```
Quero ouvir <persona 1>, <persona 2> e <persona 3> discutindo <o quê>. Não quero SPEC ainda, é discussão. Ative `mesa-de-personas`.
```

---

## 10. Boas práticas

### Use PT-BR em tudo

Código (nomes), comentários, commits, mensagens de erro de UI, descrições de tarefa. Termos técnicos consagrados (PR, CI, RLS, JWT, payload, endpoint) ficam em inglês.

### Faça triagem antes de cerimônia

Bug de 1 linha não precisa de SPEC, threat model, code review formal. As próprias skills fazem auto-sizing — confie. Se `spec-rastreavel` disser "isso é trivial, pula", pula.

### Não suavize achados de severidade

`revisao-pre-pr` retornou 🔴? Não negocie. 🔴 é 🔴 mesmo com prazo apertado.

### Toda métrica tem decisão

Se você não sabe o que vai fazer quando a métrica subir ou cair, não meça.

### Rastreabilidade > volume de doc

SPEC com 5 requisitos rastreáveis (`EXP-01`, `EXP-02`...) vale mais do que SPEC de 20 páginas sem IDs.

### Persona é convenção

Se "Carlos" respondeu numa tarefa de frontend, o roteamento está errado. Diga: "isso é trabalho da Marina, não do Carlos."

### File ownership existe pra evitar conflito de merge

Quando ativar squad com várias personas, cada uma cuida dos seus arquivos. Conflito = serializar.

### Defina os gates do projeto cedo

`contextos/testes.md` mapeia comando real de lint, unit, integration, e2e, build. Sem isso, validação e revisão chutam comandos genéricos.

### Sexta-feira é dia de ritual

`auditoria-do-setup` + `evolucao-semanal` toda sexta. Disciplina importa mais do que sofisticação.

### Não confunda "agent decidiu" com "decisão tomada"

Se o agente propôs uma solução, você ainda é responsável por aprovar. Coding Agent é acelerador, não substituto de decisão técnica.

---

## 11. Troubleshooting

### A skill não disparou automaticamente

99% das vezes é prompt fraco ou `description` ruim. Soluções:

1. Aplica a receita CARDO (Contexto, Ação, Restrições, Done-when, Output).
2. Se ainda não disparar, **invoque manualmente**: "Ative `nome-da-skill`".
3. Se for problema recorrente, abre issue no repo central pra ajustar o `description`.

### Disparou a skill errada

Cancela e renomeia:

> "Não, eu queria `squad-qualidade`, não `revisao-pre-pr`. Estou no meio da implementação, não no fim."

### A persona errada respondeu

Diga explicitamente:

> "Helena, não Marcos — quero security review, não infraestrutura."

### A skill quer implementar antes de decidir

Pare e ative `squad-arquitetura` ou `spec-rastreavel`:

> "Espera. Antes de implementar, ative `spec-rastreavel` — preciso da SPEC primeiro."

### A skill quer rodar comando que não existe no projeto

Cria `contextos/testes.md` com os comandos reais. Veja exemplo na `onboarding-de-projeto`.

### Diff grande demais pra `revisao-pre-pr`

Fatie. `squad-produto` pode ajudar Camila a quebrar em PRs menores.

### Não sei se uso `squad-qualidade` ou `revisao-pre-pr`

| Sinal | Skill |
|---|---|
| Meio da implementação, "o que testar?" | `squad-qualidade` |
| Já terminei, "tá pronto pro PR?" | `revisao-pre-pr` |
| Auditoria de feature inteira | `squad-qualidade` (Helena) |
| Auditoria do **diff específico** | `revisao-pre-pr` |

### Skill funcionou em Lovable mas não em Replit (ou vice-versa)

Cheque o caminho:
- **Lovable:** skill colada via UI no workspace
- **Replit:** `/.agents/skills/<nome>/SKILL.md` no projeto

`mesa-de-personas` substitui o caso de uso da `mobilizar` (Claude Code Agent Teams). Paralelismo real ainda exige Claude Code.

### Skill não existe pra meu caso

3 opções:

1. **Combina skills existentes** — geralmente o caso novo é uma sequência de skills antigas.
2. **Cria localmente** — adiciona em `skills/<nome>/SKILL.md` no seu projeto.
3. **Propõe pro catálogo central** — abre PR seguindo `CONTRIBUTING.md`.

### Equipe não está usando as skills

Sintoma comum no começo. Causas mais frequentes:

- Equipe não sabe o que está disponível → distribui esse guia + faz workshop de 1h.
- Skills "atrapalham" o ritmo → provavelmente estão sendo invocadas em casos triviais. Reforce a triagem.
- Prompts ruins → as skills dependem de input bom. Faça revisão de prompts no review da PR ("você descreveu bem a tarefa?").
- Pulando passos pra "ir mais rápido" → curto prazo parece, longo prazo retrabalho. Cobra o ritual.
