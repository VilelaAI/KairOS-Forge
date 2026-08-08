# AGENTS.md

> This file mirrors `CLAUDE.md` for Codex CLI and OpenCode compatibility.
> See `CLAUDE.md` for the canonical (Portuguese) version.

## Project Overview

**kairos-forge** is a Claude Code / Codex CLI / OpenCode / Cursor / Kiro CLI plugin that delivers a 71-agent software factory in Brazilian Portuguese. The factory consists of **40 core agents** organized in 11 teams (leadership, product, architecture, frontend, mobile, backend, data, data science, quality, platform, docs) and **31 support agents** in 10 squads (microcopy, narrative, naming, value, observability, DX, architectural review, requirements engineering, project & delivery management, governance).

The factory is coordinated by **Laura (Tech Lead)** who analyzes task complexity and only mobilizes the relevant agents. Agents respond in the first person with consistent personas.

## Positioning vs kairos-ai

`kairos-forge` is the **MIT generic** version of the KairOS factory. For projects in **Brazilian regulated domains** (LGPD, IT Security, NRs, OAB, MEC-LDB, ANVISA, BACEN), use [kairos-ai](https://github.com/VilelaAI/kairos-ai), which adds business squads, legal guardrails, binary assertions, Ralph Loop, and a regulatory advisor.

The two plugins are independent — one does not import from the other. The core agents are intentionally duplicated and may diverge over time.

## Plugin Structure

- `.claude-plugin/plugin.json` — Plugin manifest (Claude Code)
- `agents/` — 71 subagents as `<id>.md` files (Claude Code format)
- `skills/<name>/SKILL.md` — 18 skills, invoked as `/kairos-forge:<name>` (Claude Code format)
- `hooks/hooks.json` — Claude Code hooks (SessionStart banner, PostToolUse pedagogical reminder, and the deterministic execution recorder wired at four lifecycle points — ADR-0021)
- `.agents/` — Same content as `agents/` and `skills/`, in Codex CLI format (`<id>/AGENT.md` for agents, `skills/<name>/SKILL.md` for skills)
- `.cursor/` — Generated Cursor distribution (ADR-0011): adapted subagents in `agents/` (`tools:`/`model:` stripped; `readonly: true` when the original allow-list has no write-capable tool), mirrored skills (open Agent Skills format), an `alwaysApply` rule replacing the SessionStart banner, plus `scripts/grafo.py` and `templates/` so `${CLAUDE_PLUGIN_ROOT}` references resolve
- `.kiro/` — Generated Kiro CLI distribution (ADR-0035): agent configs in `agents/<id>.json` (persona as `prompt`, allow-list translated to Kiro tool names, telemetry and guardrail hooks embedded — Kiro keeps hooks in the agent config, not in a global file), mirrored skills, an always-loaded `steering/` file replacing the SessionStart banner, plus support scripts and `templates/`
- `.codex/hooks.json` — Codex-specific hooks (no `Write|Edit` matcher; only Bash supported)
- `templates/` — `CLAUDE.md.template`, `squad-fabrica.yaml`, `anti-drift.md`, `trilhas/` (theme-based SPEC blueprints — guided mode, ADR-0013)
- `docs/adr/` — Architecture Decision Records
- `scripts/sync-multi-cli.py` — Regenerates `.agents/` (Codex), `.cursor/` (Cursor) and `.kiro/` (Kiro CLI) from `agents/` + `skills/` whenever the canonical Claude Code sources change
- `scripts/kiro.py` — Kiro boundary (ADR-0035): the single tool-name table used by BOTH the translated allow-list and the hook matchers, plus a hook-payload adapter that preserves the guardrail's exit 2
- `scripts/grafo.py` — Deterministic side of the knowledge graph (validate, diagnose, k-hop subgraph, human sample, Mermaid export for SPEC/RFC/ADR); the graph itself lives in the user project at `.agents/grafo/`
- `scripts/diagnostico.py` — Deterministic level-1 evidence for `/diagnosticar`: churn and code hotspots, authorship concentration on those hotspots, test-to-source ratio, dependency inventory, declared-debt density, file-size distribution. Measures only; scoring and causal inference are the skill's judgment (ADR-0028)
- `scripts/execucao.py` — Deterministic execution recorder called by hooks; appends one event per lifecycle point to `.agents/execucoes/*.jsonl` in the user project. Never blocks, never writes to stdout, never records secrets (ADR-0021)
- `scripts/telemetria.py` — Aggregates that record: `resumo` (the numbers behind the `/auditar` Autonomy dimension), `sessoes`, and `corroborar` (used by `/validar` to check a `verificado:` claim against what actually ran)
- `scripts/release.py` — Version bump with counts computed from the filesystem, plus a `check` mode run by CI (consistency of counts/version, root↔plugin parity, JSON validity, mirrors)
- `evals/roteamento-laura/` — Gold set plus `rodar.py`, a headless runner for Laura's routing regression eval (repo-root only, not distributed in `plugin/`). Skips cleanly with exit 0 when no API key is present — a false red trains the team to ignore red
- `evals/comportamento-fabrica/` — Gold set for the five behaviors that separate a harness from a prompt folder (ADR-0031), each tied to a promise the factory already makes in writing. 8 of the 13 cases are decided by reading `.agents/execucoes/` — no model in the loop. Running the cases needs an agent; CI keeps the set well-formed via `release.py check`
- `templates/ci/` — Event-driven workflow recipes for the **user's** project (ADR-0026): review-on-PR, fix-on-red-CI, audit-on-cron
- `scripts/ciclo.py` — Deterministic state machine for the `entregar` arc (ADR-0029/0033), planning phases included. The skill executes a step and registers the outcome; the script decides the transition. Budget is enforced, not promised; `corrigindo_revisao` has exactly one outgoing edge — back to `validando`; and `registrar aprovado` is read from the validation report on disk, not taken on the agent's word
- `scripts/guardrail.py` — Deterministic guardrails: destructive commands, protected paths, SPEC integrity, report contracts. Hook mode (exit 2 blocks) and CLI mode for CLIs without `PreToolUse` and for CI (ADR-0022/0032)
- `scripts/contrato.py` — Pure module for the report boundary contracts (ADR-0032): one fence per report type (` ```kairos-critica ` / ` ```kairos-validacao ` / ` ```kairos-revisao `, never shared — both reports carry the same `**Veredicto:**` line, so a shared fence would let one be read as the other), coherence checks, and proof of coverage: a clean verdict must list what was actually checked. No I/O, never throws — byte-testable and safe to call from a hook
- `scripts/painel.py` — The living board (ADR-0013/0032): renders SPEC requirement status, arc state, both gate verdicts and trajectory into one view — terminal by default, self-contained HTML with `--html` (no CDN, no remote font, no script: it has to open on a machine with no network, which is exactly where someone is debugging a stuck cycle), `--json` for other tooling. **Rendering, never state** — it writes nothing but the output file you asked for and keeps nothing between runs; a persisted board is the parallel spreadsheet ADR-0013 rejected. It also applies the doctrine to its own number: a requirement marked `Concluído` without `verificado:` does not count as done — it drops to "in progress" and is listed in the warning, because a board that counted the word would show progress `/validar` itself would refuse
- `contratos/ASSINATURA.json` + `docs/contrato-de-integracao.md` — The integration contract (ADR-0034): `ciclo.py estado --json` and the three report fences are a **public, versioned surface** for outside drivers (kairos-symphony). Signed with a sha256 of the declaration and verified by `release.py check` — change the shape without re-signing and CI goes red, because a contract nobody verifies is a promise
- `.github/workflows/ci.yml` — CI: sync with no pending diff, `release.py check`, agent security audit (repo-root only)
- `hermes/` — Hermes Agent bridge (ADR-0019): routing/cycle skills + workflow + install.sh that plug the factory into a 24/7 Hermes bot as its engineering engine (Hermes operates — kanban, cron, approvals; the factory specs, builds, validates and reviews inside Claude Code)

## Cross-platform compatibility

| Component | Claude Code | Codex CLI | OpenCode | Cursor | Kiro CLI |
|---|---|---|---|---|---|
| Plugin manifest | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` | n/a | n/a | n/a |
| Marketplace catalog | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` | n/a | n/a | n/a |
| Install command | `/plugin marketplace add` (TUI) | `codex plugin marketplace add` + TUI selection | `cp -R skills/ .opencode/skills/` | `cp -R plugin/.cursor <project>/.cursor` (or `~/.cursor/`) | `cp -R plugin/.kiro <project>/.kiro` (or `~/.kiro/`) |
| Skills | `skills/<name>/SKILL.md` | same `skills/` folder (shared) | `.opencode/skills/` or `.claude/skills/` | `.cursor/skills/` (generated mirror, Agent Skills standard) | `.kiro/skills/<name>/SKILL.md` (generated mirror, same format) |
| Subagents | `agents/<id>.md` | `.agents/<id>/AGENT.md` | via copy of `agents/` | `.cursor/agents/<id>.md` (generated, adapted frontmatter) | `.kiro/agents/<id>.json` (generated, allow-list translated) |
| SessionStart hook | `hooks/hooks.json` | `.codex/hooks.json` | via `oh-my-opencode` | `.cursor/rules/kairos-forge.mdc` (`alwaysApply`) | `agentSpawn` hook + `.kiro/steering/` |
| PostToolUse hook | `hooks/hooks.json` | ❌ (only Bash matcher) | via `oh-my-opencode` | ❌ | ✅ `postToolUse` (per-agent config) |
| Blocking guardrail (ADR-0022) | ✅ `PreToolUse` exit 2 | ❌ CI-only (`guardrail.py verificar`) | ❌ | ❌ | ✅ `preToolUse` exit 2 (⚠️ unverified under ACP) |
| Execution telemetry (ADR-0021) | ✅ full (4 lifecycle points) | ⚠️ SessionStart only — no usable trajectory | ❌ | ❌ | ✅ full (⚠️ unverified under ACP) |
| Agent Teams (`/mobilizar`) | ✅ native (`TeamCreate`) | ❌ no equivalent | ❌ no equivalent | ❌ (parallel subagents exist, but no Teams protocol) | ❌ (subagents + `spawn_run` exist, but no Teams protocol) |
| Project instructions | `CLAUDE.md` | `AGENTS.md` | `CLAUDE.md` (fallback) or `AGENTS.md` | `AGENTS.md` | `.kiro/steering/` |

Kiro is the **second CLI where the whole harness runs** — not just the prompt folder. Hooks block with exit 2 and the per-tool allow-list survives translation (Cursor degrades it to `readonly`). The caveat: it was not confirmed in execution whether kiro-cli hooks fire in **ACP** sessions, which is how Kiro Crew drives the CLI. If they don't, it degrades like Codex/Cursor — and under Kiro Crew the mounting point is the Gateway's own PreToolUse gate (ADR-0035).

**Skills are shared, not duplicated** between Claude Code and Codex — both discover skills at `skills/<name>/SKILL.md` when packaged as plugin. Cursor has no plugin/marketplace concept, so it receives a **generated** mirror under `.cursor/skills/` (same SKILL.md files, open Agent Skills standard — regenerated by the sync script, never edited by hand).

### Skill availability per CLI

All 18 skills live in `skills/` and are accessible to both Claude Code and Codex.

| Skill | Claude Code | Codex CLI | OpenCode | Cursor |
|---|---|---|---|---|
| `onboardar` | ✅ | ✅ | ✅ | ✅ |
| `especificar` | ✅ | ✅ | ✅ | ✅ |
| `mapear-arquitetura` | ✅ | ✅ | ✅ | ✅ |
| `mapear-conhecimento` | ✅ | ✅ | ✅ | ✅ |
| `analisar-ameacas` | ✅ | ✅ | ✅ | ✅ |
| `validar` | ✅ | ✅ | ✅ | ✅ |
| `rodar` | ✅ | ✅ | ✅ | ✅ |
| `mobilizar` | ✅ | ⚠️ skill loads but detects environment and redirects to `rodar` | ⚠️ same as Codex | ⚠️ same as Codex |
| `entregar` | ✅ | ✅ (builds via `rodar`) | ✅ (builds via `rodar`) | ✅ (builds via `rodar`) |
| `diagnosticar` | ✅ | ✅ | ✅ | ✅ |
| `avaliar` | ✅ | ✅ | ✅ | ✅ |
| `revisar` | ✅ | ✅ | ✅ | ✅ |
| `otimizar` | ✅ | ✅ | ✅ | ✅ |
| `migrar` | ✅ | ✅ | ✅ | ✅ |
| `desenhar` | ✅ | ✅ | ✅ | ✅ |
| `lancar` | ✅ | ✅ | ✅ | ✅ |
| `auditar` | ✅ | ✅ | ✅ | ✅ |
| `evoluir` | ✅ | ✅ | ✅ | ✅ |

Natural flow ordering: `onboardar` → `mapear-arquitetura` (brownfield) → `especificar` → `analisar-ameacas` (sensitive features) → `desenhar` (UI features — ADR-0020) → `mobilizar`/`rodar` → `validar` → `revisar` → `lancar` (gated deploy — ADR-0020) → `mapear-conhecimento` (as docs accumulate; feeds later `mobilizar`/`validar` runs) → `auditar` (weekly) → `evoluir`. The `entregar` skill (ADR-0023) walks that central stretch on its own — specify → build → validate ⇄ fix → review ⇄ fix → PR — routing each failure back to the responsible agent inside a declared budget instead of the user chaining commands by hand. On demand, outside the flow: `otimizar` — a metric-driven ratchet loop (one change per round, measure, keep-or-revert via git, full lineage recorded; sentinels guard against Goodhart; explicit budget and exhaustion criteria — ADR-0012) — and `migrar` — strangler-fig legacy modernization owned by Ivan: characterization tests before touching anything, one slice at a time with a cut-over route and per-slice keep-or-revert (ADR-0018).

**Knowledge graph (Graph Engineering, ADR-0009).** The factory maintains a per-project knowledge graph at `.agents/grafo/` (JSONL entities/relations/aliases with provenance, versioned schema, hub profiles). It acts as shared memory for `mobilizar` teammates, as the grounding layer for `validar` (claims checked against edges; claims absent from the graph escalate to the human), and as the persistent world model that survives context-window flushes. 🕸️ Olívia (`olivia-grafos`, Dados team) owns it via the `mapear-conhecimento` skill; `scripts/grafo.py` handles the deterministic parts.

**Layered persistent memory (ADR-0010).** Three layers: **episodic** (session capture + cross-CLI handoffs via the optional external [ai-memory](https://github.com/akitaonrails/ai-memory) companion, detected through its `memory_*` MCP tools — never bundled, graceful degradation when absent), **curated** (`decisoes/`, `.agents/memory/`, `contextos/` in the repo), and **structural** (the knowledge graph above). Durable facts flow upward (session → curated file → graph edge); the repo stays the source of truth, and skills never double-write. See `docs/memoria-persistente.md`.

For Codex/OpenCode users, `/kairos-forge:rodar` is the recommended fallback when `mobilizar` is unavailable — the conversational/sequential mode works on all three CLIs.

## Installation per CLI

### Claude Code (recommended)

```
/plugin marketplace add VilelaAI/kairos-forge
/plugin install kairos-forge
/reload-plugins
```

For parallel Agent Teams via `mobilizar`:

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

### Codex CLI

The Codex CLI uses `plugin marketplace add` to register marketplaces. **There is no `--plugin-dir` flag, and `codex plugin install` is not a CLI subcommand** — installation happens inside the TUI after registering the marketplace.

#### Local development

On **Linux**:

```bash
git clone https://github.com/VilelaAI/kairos-forge.git
cd kairos-forge

# Register this directory as a local marketplace
codex plugin marketplace add .

# Open the Codex TUI
codex
```

On **macOS** (use absolute path to avoid relative-path edge cases):

```bash
git clone https://github.com/VilelaAI/kairos-forge.git
cd kairos-forge

codex plugin marketplace add "$(pwd)"
codex
```

Inside the TUI, open the plugin menu (`/plugin` or interactive navigation) and install `kairos-forge` from the `kairos-forge` marketplace.

#### After publishing to GitHub

```bash
codex plugin marketplace add VilelaAI/kairos-forge
codex
# Inside TUI: /plugin → choose kairos-forge → install
```

#### Codex layout

- `.codex-plugin/plugin.json` — plugin manifest
- `.agents/plugins/marketplace.json` — marketplace catalog (Codex path)
- `skills/<name>/SKILL.md` — skills (same path as Claude Code, **shared** between both CLIs)
- `.agents/<id>/AGENT.md` — subagents in Codex format (generated from `agents/`)
- `.codex/hooks.json` — Codex hooks (SessionStart only — Codex doesn't support `Write|Edit` matcher)

To enable the SessionStart hook, add to `~/.codex/config.toml`:

```toml
[features]
codex_hooks = true
```

### Cursor

Cursor has no plugin marketplace — install is a single copy of the generated `.cursor/` distribution (requires Cursor 2.4+ for subagents; skills need 2.1+):

```bash
git clone https://github.com/VilelaAI/kairos-forge.git

# Per project:
cp -R kairos-forge/plugin/.cursor /path/to/project/.cursor

# Or globally, for all projects:
cp -R kairos-forge/plugin/.cursor/* ~/.cursor/
```

This delivers the 71 subagents (`.cursor/agents/`), the 18 skills in the `/` menu (`.cursor/skills/`), an `alwaysApply` rule with the factory banner and `${CLAUDE_PLUGIN_ROOT}` path resolution, plus `scripts/grafo.py` and `templates/`. Project instructions: Cursor reads `AGENTS.md` — `/kairos-forge:onboardar` offers to generate it alongside `CLAUDE.md`. `mobilizar` detects Cursor and redirects to `rodar`.

### Kiro CLI

Kiro has no plugin marketplace either — install is a copy of the generated `.kiro/` distribution (ADR-0035):

```bash
git clone https://github.com/VilelaAI/kairos-forge.git

# Per project:
cp -R kairos-forge/plugin/.kiro /path/to/project/.kiro

# Or globally, for all projects:
cp -R kairos-forge/plugin/.kiro/* ~/.kiro/
```

This delivers the 71 agent configs (`.kiro/agents/<id>.json` — persona as `prompt`, allow-list translated to Kiro tool names, telemetry and guardrail hooks embedded), the 18 skills (`.kiro/skills/`), an always-loaded steering file, plus the support scripts and templates. Start from Laura: `kiro-cli chat --agent laura-tech-lead`.

Under **Kiro Crew**, each agent runs as `kiro-cli acp --agent <id>` and the Gateway supplies what the factory deliberately doesn't — persistence between sessions, scheduling, webhooks, Slack/Telegram, interactive approvals, OS sandbox. The Gateway is the *when/where*; the factory is the *how*. It drives the arc through the ADR-0034 contract (`ciclo.py estado --json`) rather than reimplementing it. See `docs/kirocrew.md`.

### OpenCode

```bash
git clone https://github.com/VilelaAI/kairos-forge.git
# Option A: copy skills to OpenCode's discovery path
cp -r kairos-forge/skills/* .opencode/skills/
# Option B: use Claude Code compatibility path
cp -r kairos-forge/skills/* .claude/skills/
```

OpenCode reads `CLAUDE.md` as a fallback for `AGENTS.md`, so project instructions load automatically. For hooks, install [oh-my-opencode](https://github.com/fractalmind-ai/oh-my-opencode) which provides a Claude Code hooks compatibility layer.

## Mandatory conventions

1. **PT-BR everywhere.** Skills, agents, commands, comments, commit messages — Portuguese. AGENTS.md and code identifiers may be English when the technology demands.
2. **Infinitive verbs in skill names.** `especificar`, not `spec`.
3. **Skills ≤ 500 lines** in SKILL.md. Heavy reference material lives in skill `references/`.
4. **Agents have explicit tool allow-lists.** Never give universal access.
5. **Personas are fixed.** The 40 core agents and 31 support agents have stable names and personalities. Do not invent new ones — use existing or open an ADR for a new persona.
6. **Support agents never code.** They produce textual artifacts (Markdown, lists, tables, plans).

## Workflow for changes

- Modify a skill or agent → run `python3 scripts/sync-multi-cli.py` → bump patch version
- Add new agent or skill → run sync → bump minor version + new ADR
- Change fundamental contract (e.g., file ownership protocol, SPEC format) → bump major + new ADR
- Version bumps go through `python3 scripts/release.py bump X.Y.Z` — it computes agent/team/squad/skill counts from the filesystem, injects version+counts everywhere, runs both syncs and mirrors `plugin/`; `python3 scripts/release.py check` is what CI runs on every PR
- Changed Laura's prompt, an agent `description` or routing → run the routing eval (`evals/roteamento-laura/`) with Alice before committing

Always run `/reload-plugins` (Claude Code) or restart the CLI (Codex/OpenCode/Kiro) after sync.

## Decisions made

- **ADR-0001**: plugin instead of standalone runtime (independent of Claude Code internals)
- **ADR-0002**: relationship with kairos-ai — Forge is lite/MIT, kairos-ai is regulated/PRO
- **ADR-0003**: porting of the 21 support agents from kairos-ai
- **ADR-0004**: multi-CLI compatibility — Claude Code canonical, Codex via `.agents/` mirror, OpenCode via fallback paths
- **ADR-0005**: traceable SPEC and validation-against-contract step (v0.5.0)
- **ADR-0006**: modular architecture, threat model, and the Estrutura dimension in `/auditar` (v0.6.0)
- **ADR-0007**: infrastructure specialists in the Plataforma squad — Igor (IaC), Kaique (Kubernetes), Gael (GitOps), Nina (Networking) (v0.7.0)
- **ADR-0008**: SRE/Incident Commander (Sérgio) and AIOps Engineer (Aline) in the Plataforma squad (v0.7.0)
- **ADR-0009**: Graph Engineering — knowledge graph as the factory's shared memory; `mapear-conhecimento` skill and Olívia (Knowledge) in the Dados team (v0.8.0)
- **ADR-0010**: layered persistent memory — optional ai-memory integration via MCP (episodic/curated/structural) and dependency-graph discipline in `/mobilizar` (v0.8.1)
- **ADR-0011**: Cursor support — generated `.cursor/` distribution with adapted subagents, mirrored skills (Agent Skills standard), `alwaysApply` rule, and skill-support files (v0.9.0)
- **ADR-0012**: ratchet loop — `otimizar` skill (metric-driven keep-or-revert improvement), complexity budget in `/mobilizar`, structured reflection in the anti-drift DoD, and traceability bar in `/validar` (v0.10.0)
- **ADR-0013**: KodeOne-inspired features — consumption ledger and model-tier routing in `/mobilizar`, live board rendering at checkpoints, theme trails in `templates/trilhas/` (guided mode in `/especificar` and `/rodar`) (v0.10.2)
- **ADR-0014**: support squads for Requirements Engineering (Joana, Caio, Norma) and Project & Delivery Management (Iara, Breno, Talita) (v0.11.0)
- **ADR-0015**: Stop-and-Ask conditions against content invention (especificar, Joana, anti-drift), appetite-vs-scope and Working Backwards in `/especificar` (v0.11.1)
- **ADR-0016**: core Data Science team (Davi, Milena, Heitor) and Governance support squad (Vitor, Regina, Paula) (v0.12.0)
- **ADR-0017**: seven specialized profiles — Mobile team (Yasmin, Théo), Ivan (Legacy Modernization), Alice (AI Evals), Bento (Analytics), Murilo (Events & Streaming), Ingrid (Localization, in apoio-microcopy) (v0.13.0)
- **ADR-0018**: `migrar` skill (strangler fig with Ivan), RFC mode in `/especificar`, `mermaid` subcommand in grafo.py and debate mode in `/rodar` (v0.14.0)
- **ADR-0019**: Hermes bridge — the factory as the engineering engine of Hermes Agent (24/7 via Telegram); recommended-default questions in `/especificar` (v0.15.0)
- **ADR-0020**: `desenhar` (design handoff + visual verification, Isabela) and `lancar` (gated deploy with layered health check, Marcos) — the oh-my-hermes product cycle, plugin-compatible parts only (v0.16.0)
- **ADR-0021**: Harness observability — deterministic per-hook execution record, `telemetria.py`, trajectory corroboration in `/validar`, and a sixth **Autonomy** dimension in `/auditar`. Autonomy without an instrument is a guess; this is what makes L4 a verifiable target (v0.17.0)
- **ADR-0022**: Deterministic guardrails — `guardrail.py` on `PreToolUse`/`PostToolUse` (destructive commands, protected files, SPEC integrity). `.agents/execucoes/` and `.agents/guardrails.json` are non-negotiable: the agent never writes its own measuring instrument. CLI fallback (`guardrail.py verificar`) for CLIs without `PreToolUse` (v0.18.0)
- **ADR-0023**: `entregar` skill — the closed arc (specify → build → validate ⇄ fix → review ⇄ fix → PR), promoted from the Hermes bridge into the plugin. Failures route back to the responsible agent within a declared round budget; the human approval frontier stays intact (v0.18.0)
- **ADR-0024**: Blast-radius containment — git worktree per teammate when human review leaves the loop, and declared reversibility as the admission test for autonomy: a task whose revert you cannot write is not autonomous (v0.18.0)
- **ADR-0025**: `avaliar` skill — evals with a versioned gold set and an explicit rubric across the paper's five axes (task success, tool use quality, trajectory compliance, hallucination, response quality) as a CI gate, owned by Alice. The plugin's own routing eval becomes headless-runnable, so the factory stops preaching what it measured by hand (v0.19.0)
- **ADR-0026**: Event-driven triggers — `templates/ci/` ships review-on-PR, fix-on-red-CI (opens a PR, never writes to the base branch) and audit-on-cron for the user's project. Install only after telemetry and guardrails are in place (v0.19.0)
- **ADR-0027**: Static/dynamic context boundary declared and budgeted, enforced by `release.py check` — including the 500-line-per-skill rule that was convention until now (v0.19.0)
- **ADR-0028**: `diagnosticar` skill — the front door for an existing system, owned by Rafael. Declared evidence ladder (repo only / + runnable environment / + production telemetry), six dimensions scored against a rubric published inside the report, and projected gains only as a range with its basis stated — no basis, no number. `diagnostico.py` supplies the measured layer (v0.20.0)
- **ADR-0029**: Deterministic state machine for the `entregar` arc — inspired by the Inverted Agentic Orchestration pattern (cooperacode/IAO), but importing the property, not the runtime: transitions live in code. The guardrail blocks `gh pr create` outside `pronto_para_pr`, and `.agents/ciclo/` joins the sacred paths the agent may not write (v0.21.0)
- **ADR-0030**: Three families of hardening. (a) *Artifact fitted to its own test*: a sealed hold-out half of the gold set that alone grants approval, plus a certification digest that voids the eval when the artifact changes; and SPEC-churn detection — a commit touching both the SPEC and production code is the spec being rewritten to match what was built. (b) *Guardrail ergonomics*: denials now enter the trajectory (a run that passes while reaching for tools it lacks is not passing), and rules can start in `aviso` mode and be promoted to `bloqueio` once the warn rate drops — sacred paths never degrade. (c) *In-flight detection*: repetition, alternation and no-progress, all requiring failure, firing once when the pattern closes. Plus three-point/PERT estimation for Breno and RICE/WSJF for Hugo (v0.22.0)
- **ADR-0031**: Judge hygiene in `/avaliar` — different family from the generator (inside Claude Code the lazy default is Claude judging Claude, exactly the case to avoid; measured bias is large: 93.3% vs 39.5% on the same outputs), a panel when being wrong is expensive, objectively checkable things go to code, pinned judge version, and never reward *shape* (length, keywords, citation count, tool-call count, similarity) — optimize against a judge long enough and the agent learns to look right instead of be right. Suite sizing reconciled with a time ceiling: ~30 cases for signal, ~500 to trust the aggregate, under 5 minutes or it stops being run. Plus `evals/comportamento-fabrica/`; blast-radius lanes in `/revisar` and `/entregar` — the gate asks *how much does it cost to undo*, not *how confident am I*, because confidence is the weak variable and the one the model controls — and revert rate in `diagnostico.py` as the actuarial signal the model cannot influence. Auto-merge explicitly declined: integration stays the repo owner's call (ADR-0023) (v0.23.0)
- **ADR-0032**: Relationship with [LionCode](https://github.com/LionLabsCommunity/LionCodeLabs) (Electron IDE for agent orchestration — 216k lines of TS to our 6.8k; 31 agents to our 71) and three mechanisms adopted from it. The strategic call: **we don't become an app, we become something that fits inside one** — their seed catalog is a data structure, which makes it a fifth sync target (ADR-0004), not a new product. The three: (a) *real progress refunds the token* — the flat budget punished convergence, treating 5→3→1 blockers the same as 5→5→5; the cycle now compares against the best mark reached and only burns a round when nothing improved, with an absolute ceiling on top; (b) *proof of coverage* — a clean report must list what was examined, enforced by the parser, not the prompt ("found nothing" without saying where you looked is absence of search, not absence of defect); (c) *one fence per report type*, because a wrong field can be ignored but a wrong fence simply doesn't open. Consequence: `/revisar` now saves a report to disk, so both halves of the arc are artifact-fed instead of taken on the agent's word (v0.24.0)
- **ADR-0033**: Phased planning and adversarial SPEC critique. The `/especificar` checkpoints — mirror the understanding, pick the approach, approve the SPEC — already existed as prose; they become **states**, because prose stops a human who is reading and stops nothing in a script-driven arc. Then the gap inventory: the SPEC was the *only* stage of the arc with no adversary (validation has Ricardo and Patrícia, review has Helena and Patrícia, evals have a judge panel — the SPEC had its author). New `criticando` gate: at least two critics who did not write it attack premise, requirement, plan and testability, with independence enforced by the parser (two distinct names in `criticado_por` — one pair of eyes is review, not critique). Runs *before* the human gate, so the user isn't spending attention on what two agents would find for free. Plus a numeric wave cap of 6 teammates in `/mobilizar` (judgment only works while someone is watching), and a symmetry fix: `registrar limpo` on review now requires the artifact too (v0.26.0)
- **ADR-0034**: A public, versioned integration contract. Analysing [kairos-symphony](https://github.com/VilelaAI/kairos-symphony) after proposing to build a runtime that already existed: 8.5k lines of TS, 161 tests, daemon spawning CLIs via `child_process` — the exact shape proposed, already built. The two state machines *nest* (its 6 work-item states around our 17 arc states; its `in_progress` is where the whole arc lives), but the seam had a defect that was ours: its autonomous loop stops on a `checkpoint.md` **written by the agent**, which is precisely what v0.21–v0.26 removed here. It reimplemented because on our side there was no contract to depend on. So `ciclo.py estado --json` and the three fences become a stable surface — with derived fields (`terminal`, `aguardando_humano`, `gate`, `resultados_validos`) whose only job is to stop consumers comparing state-name strings, and a sha256 signature verified by `release.py check`: change the shape without re-signing and CI goes red (v0.27.0)
- **ADR-0035**: Kiro CLI support and the Kiro Crew boundary. Two different questions behind one name: **kiro-cli** is a *CLI* (its skills use the same `SKILL.md` format, its agents take a per-tool allow-list, and its hooks block with exit 2 like Claude Code's) so it becomes a first-class sync target — `.kiro/` generated, the second CLI where the whole harness runs. **Kiro Crew** is a *Gateway*, the same category as Hermes and LionCode: it is the *when/where* (persistence, scheduling, Slack, approvals, sandbox) to the factory's *how*, and it drives the arc through the ADR-0034 contract rather than reimplementing it. One tool-name table in `scripts/kiro.py` feeds both the allow-list and the hook matchers, because a guardrail on a matcher that never fires guards nothing. Explicitly **not** adopted: the Gateway's memory and automatic skill synthesis — the repo stays the source of truth, and skills enter through an ADR (v0.28.0)

## Critical design constraints

- **All output in PT-BR**: agents communicate in Portuguese, even when invoked from English-language projects. The plugin itself is multilingual (English AGENTS.md, Portuguese CLAUDE.md), but agent personas are Portuguese-native.
- **Squad agents speak in first person**: When running a squad (`/kairos-forge:rodar`), each agent introduces itself by name/role and stays in character.
- **Agent naming**: Format `Name [Role]` with emoji icon (e.g., 👩‍💼 Laura [Tech Lead], 🔐 Helena [Security]).
- **Support squads are non-coding**: Squads with `tipo: apoio` NEVER implement code — they produce textual artifacts only.
- **Name collisions are explicit**: Three pairs share first names across core/support (Marcos, Helena, Elisa). Laura disambiguates before invoking when the user mentions only the first name.
- **`.agents/` and `.cursor/` are generated, not edited**: The Claude Code paths (`agents/`, `skills/`) are canonical. Edits to `.agents/` or `.cursor/` will be lost on next sync.
- **mobilizar is Claude Code-exclusive**: Agent Teams require `TeamCreate`/`TaskCreate` which only exist in Claude Code. The skill informs the user and redirects to `rodar` when invoked under Codex/OpenCode/Cursor.
