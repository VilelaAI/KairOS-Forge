# kairos-forge — guia para o Claude

Plugin Claude Code / Codex CLI / OpenCode / Cursor que entrega uma fábrica de software de 71 agentes em PT-BR. Você está editando o próprio plugin.

## O que este projeto é

Plugin multi-CLI (não runtime, não SDK). 71 agentes (40 core + 31 apoio em 10 squads), 18 skills, hooks por CLI, coordenação por Laura (Tech Lead).

Ordem natural das skills no fluxo: `onboardar` → `mapear-arquitetura` (brownfield) → `diagnosticar` (sistema existente — ADR-0028) → `especificar` → `analisar-ameacas` (features sensíveis) → `desenhar` (features com UI — ADR-0020) → `mobilizar`/`rodar` → `validar` → `revisar` → `lancar` (deploy com gates — ADR-0020) → `mapear-conhecimento` (quando docs acumulam; alimenta mobilizar/validar seguintes) → `auditar` (semanal) → `evoluir`. A skill `entregar` (ADR-0023) **percorre esse trecho central sozinha** — especificar → construir → validar ⇄ corrigir → revisar ⇄ corrigir → PR, roteando cada falha de volta ao agente responsável dentro de um orçamento declarado, em vez de o usuário encadear os comandos à mão. Fora do fluxo, sob demanda: `otimizar` (ciclo de catraca contra métrica mensurável — ADR-0012) e `migrar` (modernização de legado por estrangulamento, dono Ivan — ADR-0018).

A memória da fábrica tem **três camadas** (ADR-0009/ADR-0010): **episódica** — sessões capturadas pelo [ai-memory](https://github.com/akitaonrails/ai-memory), companion externo opcional detectado pelas tools MCP `memory_*` (handoff entre CLIs, briefing, busca); **curada** — `decisoes/`, `.agents/memory/`, `contextos/` no repo; **estrutural** — `.agents/grafo/` com entidades e relações com proveniência, dona Olívia (`olivia-grafos`). `/mobilizar` usa o grafo como memória compartilhada entre teammates e `/validar` como base de fatos. O durável sobe de camada (sessão → arquivo → grafo); o repo é a fonte da verdade. Guia: `docs/memoria-persistente.md`.

## Posicionamento vs kairos-ai

`kairos-forge` é a **versão MIT genérica** (qualquer projeto). O [`kairos-ai`](https://github.com/VilelaAI/kairos-ai) é a **versão regulada** (LGPD, NRs, OAB, etc.) com squads negociais, guardrails legais, assertions binárias, Ralph Loop e Advisor Opus.

Não duplique funcionalidade entre os dois. Se algo é **regulatório**, vai pro kairos-ai. Se é **técnico genérico**, pode ir pros dois (mas o forge nunca importa do kairos-ai — independência total).

## Convenções obrigatórias

1. **PT-BR em tudo.** Skills, agentes, comandos, comentários, mensagens de commit, ADRs. Exceção única: `AGENTS.md` na raiz é em inglês (formato padrão Codex/OpenCode).
2. **Verbos no infinitivo nos nomes de skills.** `especificar`, não `spec`.
3. **Skills ≤ 500 linhas no SKILL.md.** Material pesado vai em `references/` da skill.
4. **Agentes têm allow-list explícita de ferramentas.** Nunca dar acesso total a todos.
5. **Acentuação PT-BR correta.** `solução`, não `solucao`. Verifique antes de commitar.
6. **Personas consistentes.** Os 71 agentes têm nomes e personalidades fixas. Não invente novos — use existentes ou peça via ADR.

## Workflow para mudanças (CRÍTICO)

Os arquivos canônicos são **`agents/`** e **`skills/`** (formato Claude Code). Os diretórios **`.agents/`** (Codex) e **`.cursor/`** (Cursor) são GERADOS automaticamente.

**Sempre que alterar agents/ ou skills/, rode antes de commitar:**

```bash
python3 scripts/sync-multi-cli.py
git add agents/ skills/ .agents/ .cursor/
```

Sem o sync, usuários de Codex CLI e Cursor pegam versão desatualizada.

**Para bump de versão, use o script de release** — ele calcula as contagens
(agentes/times/squads/skills) do filesystem, injeta versão+contagens em todos os
manifests/banners/docs, roda os dois syncs e espelha em `plugin/`:

```bash
python3 scripts/release.py bump 0.14.0   # tudo de uma vez
python3 scripts/release.py check         # o que o CI roda em todo PR
```

- Mudar prompt de agente ou skill → bump patch (0.4.x) + rodar sync
- Adicionar agente ou skill → bump minor (0.x.0) + ADR + rodar sync
- Mudar contrato fundamental → bump major (x.0.0) + ADR + rodar sync
- Mudou prompt da Laura, `description` de agente ou roteamento → rodar o eval de
  roteamento (`evals/roteamento-laura/`) com a Alice antes do commit

## Estrutura

| Path | O que tem | Mantido por |
|---|---|---|
| `.claude-plugin/plugin.json` | Manifest Claude Code | manual |
| `.claude-plugin/marketplace.json` | Catalog do marketplace Claude Code | manual |
| `.codex-plugin/plugin.json` | Manifest Codex CLI | manual |
| `.agents/plugins/marketplace.json` | Catalog do marketplace Codex (mesmo conteúdo do Claude Code mas em path próprio) | manual |
| `agents/<id>.md` | 71 subagentes (canônico Claude Code) | manual |
| `.agents/<id>/AGENT.md` | Mirror Codex dos subagents | **gerado** por `scripts/sync-multi-cli.py` |
| `.cursor/` | Distribuição Cursor completa: agents adaptados (readonly quando consultivo), skills espelhadas, rule `alwaysApply` (lista de skills derivada), scripts de suporte, templates (ADR-0011) | **gerado** por `scripts/sync-multi-cli.py` |
| `skills/<verbo>/SKILL.md` | 18 skills (compartilhadas — Claude Code e Codex leem da mesma pasta) | manual |
| `hooks/hooks.json` | Hooks Claude Code: banner, telemetria em 4 pontos do ciclo (ADR-0021), guardrails que bloqueiam em `PreToolUse`/`PostToolUse` (ADR-0022) e alerta de patinação em voo (ADR-0030) | manual |
| `.codex/hooks.json` | Hooks Codex (apenas SessionStart — Codex não suporta `Write\|Edit` matcher) | manual |
| `AGENTS.md` | Espelho em inglês do CLAUDE.md raiz, para Codex/OpenCode | manual |
| `templates/` | `CLAUDE.md.template`, `squad-fabrica.yaml`, `anti-drift.md`, `trilhas/` (blueprints de SPEC por tema — ADR-0013), `ci/` (gatilhos por evento pro projeto do usuário — ADR-0026) | manual |
| `docs/adr/` | ADRs | manual |
| `scripts/sync-multi-cli.py` | Regenera `.agents/` (Codex) e `.cursor/` (Cursor) a partir de `agents/` + `skills/` | manual |
| `scripts/grafo.py` | Parte determinística do grafo de conhecimento (validar, diagnosticar, subgrafo, amostrar, mermaid) | manual |
| `scripts/diagnostico.py` | Evidência determinística de nível 1 pro `/diagnosticar`: churn, autoria, teste, deps, dívida marcada, tamanho (ADR-0028) | manual |
| `scripts/execucao.py` | Registro determinístico de execução, chamado pelos hooks — escreve `.agents/execucoes/*.jsonl` (ADR-0021) | manual |
| `scripts/telemetria.py` | Agrega o registro: `resumo` (números do `/auditar`), `sessoes`, `corroborar` (usado pelo `/validar`) | manual |
| `scripts/ciclo.py` | Máquina de estados determinística do arco `/entregar`: planejamento em fases, transição, orçamento dos três gates e escalação decididos por código (ADR-0029/0033) | manual |
| `scripts/guardrail.py` | Guardrails determinísticos: comando destrutivo, arquivo protegido, integridade da SPEC, PR fora de estado, contrato de relatório. Modo hook (exit 2 bloqueia), modo CLI para os demais CLIs e o CI, e `autoteste` que prova que morde no projeto do usuário sem sujar a trajetória (ADR-0022/0032) | manual |
| `scripts/contrato.py` | Módulo puro dos contratos de fronteira dos relatórios: fences `kairos-critica`/`kairos-validacao`/`kairos-revisao`, coerência, prova de cobertura e independência dos críticos. Nunca lança, sem I/O (ADR-0032/0033) | manual |
| `scripts/painel.py` | Quadro vivo: renderiza SPEC + ciclo + relatórios + trajetória no terminal, em HTML autocontido ou JSON. Renderização, nunca estado — não escreve nada (ADR-0013/0032) | manual |
| `scripts/release.py` | Bump de versão com contagens calculadas do filesystem, `check` de consistência (CI) e `assinar-contratos` (ADR-0034) | manual |
| `contratos/ASSINATURA.json` | Versão + sha256 dos contratos de integração; o `check` recusa mudança de forma sem reassinar (ADR-0034) | manual |
| `exemplos/criar-projeto-demo.sh` | Scaffold de um projeto real (pytest de verdade) para testar a fábrica na máquina; roteiro em `docs/testar-localmente.md` (só na raiz, não distribui) | manual |
| `evals/roteamento-laura/` | Gold set + `rodar.py` headless do eval de roteamento da Laura (dogfooding — só na raiz, não distribui) | manual |
| `evals/comportamento-fabrica/` | Gold set dos cinco comportamentos que separam harness de pasta de prompts; 8 dos 13 casos são decididos lendo `.agents/execucoes/`, e em 3 deles a metade mecânica já é decidida pelo `guardrail.py autoteste` — o campo `mecanismo` liga um ao outro e o `release.py check` cobra as duas pontas (ADR-0031) | manual |
| `hermes/` | Ponte Hermes Agent: skills de roteamento/ciclo + workflow + install.sh — a fábrica como motor de engenharia de um agente 24/7 (ADR-0019) | manual |
| `.github/workflows/ci.yml` | CI: sync sem diff pendente, `release.py check`, segurança dos agentes (só na raiz) | manual |

> **Importante: skills/ é compartilhada.** Tanto Claude Code quanto Codex CLI descobrem skills em `skills/<nome>/SKILL.md` quando empacotados como plugin. Não há duplicação. Apenas os subagents (`agents/<id>.md` no Claude Code, `.agents/<id>/AGENT.md` no Codex) é que precisam de mirror.

> **Importante: dois marketplace.json.** Claude Code procura em `.claude-plugin/marketplace.json` (com versão e descrição — o `release.py` atualiza) e Codex em `.agents/plugins/marketplace.json` (só aponta pra `./plugin`, sem versão — raramente muda).

## Decisões já tomadas

- **ADR-0001**: plugin em vez de runtime standalone
- **ADR-0002**: relação com kairos-ai — forge é lite/MIT, kairos-ai é regulado/PRO
- **ADR-0003**: portagem dos 21 agentes de apoio
- **ADR-0004**: compatibilidade multi-CLI (Claude Code + Codex + OpenCode)
- **ADR-0005**: SPEC rastreável e validação contra contrato (v0.5.0)
- **ADR-0006**: arquitetura modular, threat model e dimensão Estrutura na auditoria (v0.6.0)
- **ADR-0007**: especialistas de infraestrutura no squad Plataforma — Igor (IaC), Kaique (Kubernetes), Gael (GitOps), Nina (Redes) (v0.7.0)
- **ADR-0008**: SRE/Incident Commander (Sérgio) e Engenheiro AIOps (Aline) no squad Plataforma (v0.7.0)
- **ADR-0009**: Graph Engineering — grafo de conhecimento como memória compartilhada da fábrica; skill `mapear-conhecimento` e Olívia (Conhecimento) no time Dados (v0.8.0)
- **ADR-0010**: memória persistente em camadas — integração opcional com ai-memory via MCP (episódica/curada/estrutural) e disciplina de grafo de dependências no `/mobilizar` (v0.8.1)
- **ADR-0011**: suporte ao Cursor — `.cursor/` gerado com subagents adaptados, skills (Agent Skills padrão), rule `alwaysApply` e suporte às skills (v0.9.0)
- **ADR-0012**: ciclo de catraca — skill `otimizar` (melhoria guiada por métrica com manter-ou-reverter), orçamento de complexidade no `/mobilizar`, reflexão estruturada no anti-drift e régua de rastreabilidade no `/validar` (v0.10.0)
- **ADR-0013**: inspirações KodeOne — ledger de consumo e roteamento de modelo por tier no `/mobilizar`, quadro vivo nos checkpoints, trilhas por tema em `templates/trilhas/` (modo guiado no `/especificar` e `/rodar`) (v0.10.2)
- **ADR-0014**: squads de apoio Requisitos (Joana, Caio, Norma) e Gestão de Projetos & Entregas (Iara, Breno, Talita) (v0.11.0)
- **ADR-0015**: Pare e Pergunte — condições de parada contra invenção de conteúdo (especificar, Joana, anti-drift), apetite vs escopo e Working Backwards no `/especificar` (v0.11.1)
- **ADR-0016**: time core Ciência de Dados (Davi, Milena, Heitor) e squad de apoio Governança (Vitor, Regina, Paula) (v0.12.0)
- **ADR-0017**: sete perfis especializados — time Mobile (Yasmin, Théo), Ivan (Modernização), Alice (Evals de IA), Bento (Analytics), Murilo (Eventos) e Ingrid (Localização, no apoio-microcopy) (v0.13.0)
- **ADR-0018**: skill `migrar` (estrangulamento com Ivan), modo RFC no `/especificar`, subcomando `mermaid` no grafo.py e modo debate no `/rodar` (v0.14.0)
- **ADR-0019**: ponte Hermes — a fábrica como motor de engenharia do Hermes Agent (24/7 via Telegram); pergunta com default recomendado no `/especificar` (v0.15.0)
- **ADR-0020**: skills `desenhar` (handoff de design + verificação visual, Isabela) e `lancar` (deploy com gates e health check em camadas, Marcos) — o ciclo de produto do oh-my-hermes nas partes compatíveis com plugin (v0.16.0)
- **ADR-0021**: observabilidade do harness — registro determinístico de execução por hook, `telemetria.py`, corroboração de trajetória no `/validar` e 6ª dimensão **Autonomia** no `/auditar` (v0.17.0)
- **ADR-0022**: guardrails determinísticos — `guardrail.py` em `PreToolUse`/`PostToolUse` (comando destrutivo, arquivo protegido, integridade da SPEC), com `.agents/execucoes/` e `.agents/guardrails.json` inegociáveis (o agente não escreve o próprio medidor) e fallback CLI para os demais CLIs (v0.18.0)
- **ADR-0023**: skill `entregar` — o arco fechado (especificar → construir → validar ⇄ corrigir → revisar ⇄ corrigir → PR) promovido da ponte Hermes para dentro do plugin, com orçamento declarado e fronteira de aprovação preservada (v0.18.0)
- **ADR-0024**: contenção de raio — worktree por teammate quando a supervisão humana sai do caminho, e reversibilidade declarada como critério de admissão da autonomia (v0.18.0)
- **ADR-0025**: skill `avaliar` — evals com gold set versionado e rubrica nos cinco eixos como gate, dona Alice; e o eval de roteamento do próprio plugin passa a rodar headless no CI (v0.19.0)
- **ADR-0026**: gatilhos por evento — `templates/ci/` com revisar no PR, corrigir em CI vermelho (abre PR, nunca escreve na base) e auditar por cron. Instalar só depois de telemetria e guardrails (v0.19.0)
- **ADR-0027**: fronteira estático/dinâmico declarada e orçamento de contexto verificado no `release.py check`, incluindo o limite de 500 linhas por skill (v0.19.0)
- **ADR-0028**: skill `diagnosticar` — porta de entrada de sistema existente, dono Rafael: escada de evidência declarada, seis dimensões com rubrica publicada, ganho só com faixa e base, e `diagnostico.py` como camada medida (v0.20.0)
- **ADR-0029**: máquina de estados do arco — `ciclo.py` decide transição, orçamento e escalação por código; `corrigindo_revisao` só sai para `validando`; veredicto lido do relatório; `gh pr create` bloqueado fora de estado (v0.21.0)
- **ADR-0030**: artefato ajustado ao resultado (conjunto selado + digest no `/avaliar`, churn de SPEC no `diagnostico.py`), ergonomia de guardrail (recusa na trajetória, modo `aviso` por classe) e detecção de patinação em voo; mais estimativa probabilística no Breno e RICE/WSJF no Hugo (v0.22.0)
- **ADR-0031**: higiene do juiz no `/avaliar` (família diferente, painel, versão pinada, nunca recompensar forma) com tamanho reconciliado a teto de tempo; `evals/comportamento-fabrica/` com os cinco comportamentos; faixa de raio de explosão no `/revisar`+`/entregar` e taxa de reversão no `diagnostico.py`; auto-merge explicitamente fora (v0.23.0)
- **ADR-0032**: relação com o LionCode (IDE desktop de orquestração — 32× o código, 0,4× os agentes): não viramos app, passamos a caber dentro de um; e três mecanismos adotados dele — progresso real devolve a ficha no `ciclo.py`, prova de cobertura no `contrato.py` (relatório limpo exige lista do que foi olhado) e fence própria por tipo de relatório, com a revisão passando a ser lida do disco (v0.24.0)
- **ADR-0033**: planejamento em fases — os checkpoints do `/especificar` viram estado porque prosa não para um runner headless; crítica adversarial da SPEC com dois críticos independentes cobrados pelo parser (a única etapa do arco que não tinha contraditório); teto de 6 teammates por onda no `/mobilizar`; e `limpo` da revisão passa a exigir artefato como os outros dois gates (v0.26.0)

- **ADR-0034**: contrato de integração público e versionado — `ciclo.py estado --json` e as três fences viram superfície estável com campos derivados (`terminal`, `aguardando_humano`, `gate`, `resultados_validos`) para o consumidor não comparar nome de estado; assinatura com digest verificada no CI, porque contrato que ninguém verifica é promessa. Abre a porta para o [kairos-symphony](https://github.com/VilelaAI/kairos-symphony) dirigir o arco em vez de reimplementá-lo (v0.27.0)

## Limitações conhecidas por CLI

| Item | Claude Code | Codex CLI | OpenCode | Cursor |
|---|---|---|---|---|
| `/kairos-forge:mobilizar` (Agent Teams) | ✅ | ❌ skill avisa e sugere `rodar` | ❌ skill avisa e sugere `rodar` | ❌ skill avisa e sugere `rodar` |
| Hook PostToolUse pedagógico | ✅ | ❌ | ❌ (sem `oh-my-opencode`) | ❌ |
| SessionStart banner | ✅ | ✅ | ❌ (sem `oh-my-opencode`) | ✅ via rule `alwaysApply` |
| Subagents com persona | ✅ nativo | ✅ mirror `.agents/` | ⚠️ via cópia de `agents/` | ✅ `.cursor/agents/` (allow-list degrada pra `readonly`) |
| Telemetria de execução (ADR-0021) | ✅ completa (4 pontos do ciclo) | ⚠️ só SessionStart — sem trajetória útil | ❌ | ❌ |

Nos CLIs sem hooks completos, a dimensão **Autonomia** do `/auditar` pontua 0 e o `/validar` pula a corroboração de trajetória — comportamento honesto, não bug: sem hook não há trajetória. O caminho nesses CLIs é rodar os checks equivalentes no CI do projeto (`templates/ci/`).

A skill `mobilizar` tem detecção embutida — quando rodada em CLI sem suporte, ela orienta o usuário a usar `rodar` em vez disso.

## O que NÃO portar do kairos-ai

Estes itens existem no kairos-ai e **não devem** vir pro forge:

- Squads negociais (DPO, Mapeamento, etc.)
- Domínios regulados (`dominios/lgpd/`, `dominios/seguranca-ti/`)
- Guardrails com referência legal
- Ralph Loop (auto-correção de assertions)
- Advisor (Opus para decisões regulatórias)
- Modo `--workflow debate` (planejado pra v0.7 do forge, em formato simplificado)
- Subagents nativos especializados em domínio (assertion-validator, compliance-auditor, etc.)
- Worker headless 24/7 e dashboard Next.js
