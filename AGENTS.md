# AGENTS.md

> This file mirrors `CLAUDE.md` for Codex CLI and OpenCode compatibility.
> See `CLAUDE.md` for the canonical (Portuguese) version.

## Project Overview

**kairos-forge** is a Claude Code / Codex CLI / OpenCode / Cursor plugin that delivers a 71-agent software factory in Brazilian Portuguese. The factory consists of **40 core agents** organized in 11 teams (leadership, product, architecture, frontend, mobile, backend, data, data science, quality, platform, docs) and **31 support agents** in 10 squads (microcopy, narrative, naming, value, observability, DX, architectural review, requirements engineering, project & delivery management, governance).

The factory is coordinated by **Laura (Tech Lead)** who analyzes task complexity and only mobilizes the relevant agents. Agents respond in the first person with consistent personas.

## Positioning vs kairos-ai

`kairos-forge` is the **MIT generic** version of the KairOS factory. For projects in **Brazilian regulated domains** (LGPD, IT Security, NRs, OAB, MEC-LDB, ANVISA, BACEN), use [kairos-ai](https://github.com/VilelaAI/kairos-ai), which adds business squads, legal guardrails, binary assertions, Ralph Loop, and a regulatory advisor.

The two plugins are independent — one does not import from the other. The core agents are intentionally duplicated and may diverge over time.

## Plugin Structure

- `.claude-plugin/plugin.json` — Plugin manifest (Claude Code)
- `agents/` — 71 subagents as `<id>.md` files (Claude Code format)
- `skills/<name>/SKILL.md` — 15 skills, invoked as `/kairos-forge:<name>` (Claude Code format)
- `hooks/hooks.json` — Claude Code hooks (SessionStart banner, PostToolUse pedagogical reminder, and the deterministic execution recorder wired at four lifecycle points — ADR-0021)
- `.agents/` — Same content as `agents/` and `skills/`, in Codex CLI format (`<id>/AGENT.md` for agents, `skills/<name>/SKILL.md` for skills)
- `.cursor/` — Generated Cursor distribution (ADR-0011): adapted subagents in `agents/` (`tools:`/`model:` stripped; `readonly: true` when the original allow-list has no write-capable tool), mirrored skills (open Agent Skills format), an `alwaysApply` rule replacing the SessionStart banner, plus `scripts/grafo.py` and `templates/` so `${CLAUDE_PLUGIN_ROOT}` references resolve
- `.codex/hooks.json` — Codex-specific hooks (no `Write|Edit` matcher; only Bash supported)
- `templates/` — `CLAUDE.md.template`, `squad-fabrica.yaml`, `anti-drift.md`, `trilhas/` (theme-based SPEC blueprints — guided mode, ADR-0013)
- `docs/adr/` — Architecture Decision Records
- `scripts/sync-multi-cli.py` — Regenerates `.agents/` (Codex) and `.cursor/` (Cursor) from `agents/` + `skills/` whenever the canonical Claude Code sources change
- `scripts/grafo.py` — Deterministic side of the knowledge graph (validate, diagnose, k-hop subgraph, human sample, Mermaid export for SPEC/RFC/ADR); the graph itself lives in the user project at `.agents/grafo/`
- `scripts/execucao.py` — Deterministic execution recorder called by hooks; appends one event per lifecycle point to `.agents/execucoes/*.jsonl` in the user project. Never blocks, never writes to stdout, never records secrets (ADR-0021)
- `scripts/telemetria.py` — Aggregates that record: `resumo` (the numbers behind the `/auditar` Autonomy dimension), `sessoes`, and `corroborar` (used by `/validar` to check a `verificado:` claim against what actually ran)
- `scripts/release.py` — Version bump with counts computed from the filesystem, plus a `check` mode run by CI (consistency of counts/version, root↔plugin parity, JSON validity, mirrors)
- `evals/roteamento-laura/` — Gold set for Laura's routing regression eval, run by Alice (repo-root only, not distributed in `plugin/`)
- `.github/workflows/ci.yml` — CI: sync with no pending diff, `release.py check`, agent security audit (repo-root only)
- `hermes/` — Hermes Agent bridge (ADR-0019): routing/cycle skills + workflow + install.sh that plug the factory into a 24/7 Hermes bot as its engineering engine (Hermes operates — kanban, cron, approvals; the factory specs, builds, validates and reviews inside Claude Code)

## Cross-platform compatibility

| Component | Claude Code | Codex CLI | OpenCode | Cursor |
|---|---|---|---|---|
| Plugin manifest | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` | n/a | n/a |
| Marketplace catalog | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` | n/a | n/a |
| Install command | `/plugin marketplace add` (TUI) | `codex plugin marketplace add` + TUI selection | `cp -R skills/ .opencode/skills/` | `cp -R plugin/.cursor <project>/.cursor` (or `~/.cursor/`) |
| Skills | `skills/<name>/SKILL.md` | same `skills/` folder (shared) | `.opencode/skills/` or `.claude/skills/` | `.cursor/skills/` (generated mirror, Agent Skills standard) |
| Subagents | `agents/<id>.md` | `.agents/<id>/AGENT.md` | via copy of `agents/` | `.cursor/agents/<id>.md` (generated, adapted frontmatter) |
| SessionStart hook | `hooks/hooks.json` | `.codex/hooks.json` | via `oh-my-opencode` | `.cursor/rules/kairos-forge.mdc` (`alwaysApply`) |
| PostToolUse hook | `hooks/hooks.json` | ❌ (only Bash matcher) | via `oh-my-opencode` | ❌ |
| Execution telemetry (ADR-0021) | ✅ full (4 lifecycle points) | ⚠️ SessionStart only — no usable trajectory | ❌ | ❌ |
| Agent Teams (`/mobilizar`) | ✅ native (`TeamCreate`) | ❌ no equivalent | ❌ no equivalent | ❌ (parallel subagents exist, but no Teams protocol) |
| Project instructions | `CLAUDE.md` | `AGENTS.md` | `CLAUDE.md` (fallback) or `AGENTS.md` | `AGENTS.md` |

**Skills are shared, not duplicated** between Claude Code and Codex — both discover skills at `skills/<name>/SKILL.md` when packaged as plugin. Cursor has no plugin/marketplace concept, so it receives a **generated** mirror under `.cursor/skills/` (same SKILL.md files, open Agent Skills standard — regenerated by the sync script, never edited by hand).

### Skill availability per CLI

All 15 skills live in `skills/` and are accessible to both Claude Code and Codex.

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
| `revisar` | ✅ | ✅ | ✅ | ✅ |
| `otimizar` | ✅ | ✅ | ✅ | ✅ |
| `migrar` | ✅ | ✅ | ✅ | ✅ |
| `desenhar` | ✅ | ✅ | ✅ | ✅ |
| `lancar` | ✅ | ✅ | ✅ | ✅ |
| `auditar` | ✅ | ✅ | ✅ | ✅ |
| `evoluir` | ✅ | ✅ | ✅ | ✅ |

Natural flow ordering: `onboardar` → `mapear-arquitetura` (brownfield) → `especificar` → `analisar-ameacas` (sensitive features) → `desenhar` (UI features — ADR-0020) → `mobilizar`/`rodar` → `validar` → `revisar` → `lancar` (gated deploy — ADR-0020) → `mapear-conhecimento` (as docs accumulate; feeds later `mobilizar`/`validar` runs) → `auditar` (weekly) → `evoluir`. On demand, outside the flow: `otimizar` — a metric-driven ratchet loop (one change per round, measure, keep-or-revert via git, full lineage recorded; sentinels guard against Goodhart; explicit budget and exhaustion criteria — ADR-0012) — and `migrar` — strangler-fig legacy modernization owned by Ivan: characterization tests before touching anything, one slice at a time with a cut-over route and per-slice keep-or-revert (ADR-0018).

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

This delivers the 71 subagents (`.cursor/agents/`), the 15 skills in the `/` menu (`.cursor/skills/`), an `alwaysApply` rule with the factory banner and `${CLAUDE_PLUGIN_ROOT}` path resolution, plus `scripts/grafo.py` and `templates/`. Project instructions: Cursor reads `AGENTS.md` — `/kairos-forge:onboardar` offers to generate it alongside `CLAUDE.md`. `mobilizar` detects Cursor and redirects to `rodar`.

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

Always run `/reload-plugins` (Claude Code) or restart the CLI (Codex/OpenCode) after sync.

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

## Critical design constraints

- **All output in PT-BR**: agents communicate in Portuguese, even when invoked from English-language projects. The plugin itself is multilingual (English AGENTS.md, Portuguese CLAUDE.md), but agent personas are Portuguese-native.
- **Squad agents speak in first person**: When running a squad (`/kairos-forge:rodar`), each agent introduces itself by name/role and stays in character.
- **Agent naming**: Format `Name [Role]` with emoji icon (e.g., 👩‍💼 Laura [Tech Lead], 🔐 Helena [Security]).
- **Support squads are non-coding**: Squads with `tipo: apoio` NEVER implement code — they produce textual artifacts only.
- **Name collisions are explicit**: Three pairs share first names across core/support (Marcos, Helena, Elisa). Laura disambiguates before invoking when the user mentions only the first name.
- **`.agents/` and `.cursor/` are generated, not edited**: The Claude Code paths (`agents/`, `skills/`) are canonical. Edits to `.agents/` or `.cursor/` will be lost on next sync.
- **mobilizar is Claude Code-exclusive**: Agent Teams require `TeamCreate`/`TaskCreate` which only exist in Claude Code. The skill informs the user and redirects to `rodar` when invoked under Codex/OpenCode/Cursor.
