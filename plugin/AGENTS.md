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
- `.claude-plugin/ativos.manifest.json` — **Generated** consolidated AI-asset manifest: identity (`chave`, `versao`, `origem`) plus the declared tool allow-list of every agent/skill, derived from the canonical sources by the sync script. Feeds the KairOS ecosystem asset-catalog seed (SPEC-E006) — the direction adopted in ADR-0032. Never edited by hand
- `agents/` — 71 subagents as `<id>.md` files (Claude Code format)
- `skills/<name>/SKILL.md` — 18 skills, invoked as `/kairos-forge:<name>` (Claude Code format)
- `hooks/hooks.json` — Claude Code hooks: SessionStart banner; the deterministic execution recorder at four lifecycle points (ADR-0021); guardrails that block on `PreToolUse`/`PostToolUse` (ADR-0022); secret reads through the `Read` tool and the **stop gate** on `Stop` (ADR-0042); the in-flight spinning alert (ADR-0030); and a once-per-session Definition-of-Done reminder on the first production file edited (ADR-0038)
- `.agents/<id>/AGENT.md` — **Generated** Codex mirror of the subagents (skills are not mirrored: Codex reads the shared `skills/` folder)
- `.codex/agents/<id>.toml` — **Generated** Codex subagent roles: what makes `spawn_agent(agent_type: "<id>")` resolve the persona (ADR-0035)
- `.opencode/agent/<id>.md` — **Generated** OpenCode subagents with `mode: subagent` and the allow-list translated into `permission`, which OpenCode enforces (ADR-0035)
- `.cursor/` — **Generated** Cursor distribution (ADR-0011): adapted subagents in `agents/` (`tools:`/`model:` stripped; `readonly: true` when the original allow-list has no write-capable tool), mirrored skills (open Agent Skills format), an `alwaysApply` rule replacing the SessionStart banner, the support scripts the skills call (`scripts/` — grafo, telemetria, execucao, guardrail, diagnostico, ciclo, contrato, painel, quadro, prova, qualidade) and `templates/` so `${CLAUDE_PLUGIN_ROOT}` references resolve, plus `hooks.json` wiring telemetry and guardrails to Cursor's lifecycle events (ADR-0042)
- `.codex/hooks.json` — Codex-specific hooks (SessionStart only — Codex has no `Write|Edit` matcher)
- `templates/` — `CLAUDE.md.template`, `squad-fabrica.yaml`, `anti-drift.md`, `trilhas/` (theme-based SPEC blueprints, data pipeline included — guided mode, ADR-0013/0037), `ci/` (see below)
- `docs/adr/` — Architecture Decision Records
- `scripts/sync-multi-cli.py` — Regenerates every per-CLI mirror (`.agents/`, `.codex/agents/`, `.opencode/agent/`, `.cursor/`) and the asset manifest from `agents/` + `skills/` whenever the canonical Claude Code sources change; `instalar --cli <codex|opencode|cursor|todos>` copies the personas into the CLI's config dir, preserving the user's own agents (ADR-0035)
- `scripts/grafo.py` — Deterministic side of the knowledge graph (validate, diagnose, k-hop subgraph, human sample, Mermaid export for SPEC/RFC/ADR) plus the **code layer** (ADR-0041): `codigo` extracts `importa`/`herda`/`instancia` edges by AST/regex into `codigo.jsonl` (regenerable, the script's only write) and `contexto <file>` returns the 1-hop architectural neighbourhood and the knowledge entities citing that file; the graph itself lives in the user project at `.agents/grafo/`
- `scripts/diagnostico.py` — Deterministic level-1 evidence for `/diagnosticar`: churn and code hotspots, authorship concentration on those hotspots, test-to-source ratio, dependency inventory, declared-debt density, file-size distribution. Measures only; scoring and causal inference are the skill's judgment (ADR-0028)
- `scripts/execucao.py` — Deterministic execution recorder called by hooks; appends one event per lifecycle point to `.agents/execucoes/*.jsonl` in the user project. Never blocks, never writes to stdout, never records secrets (ADR-0021)
- `scripts/telemetria.py` — Aggregates that record: `resumo` (the numbers behind the `/auditar` Autonomy dimension), `sessoes`, `corroborar` (used by `/validar` to check a `verificado:` claim against what actually ran), `ruido` (review findings the human marked `descartado:`, per reviewer — ADR-0039), and `prs` (PR autonomy from git history: the factory's merged PRs with no human commit at all, via `gh` with a fallback to git merges — it works without hooks, ADR-0044)
- `scripts/prova.py` — Negative proof of a diff's tests (ADR-0039): `pre-patch` runs each new test against the base in a throwaway worktree, without the patch — it has to fail (`passou_na_base` means the test proves nothing about the change); `testes-alterados` lists pre-existing tests modified or deleted in the diff with loosening signals (assertion removed, case skipped, file deleted); `selado` flags any case of `evals/*/selado.jsonl` copied into instruction text or repeated in the visible set (ADR-0043); `colher` turns every merged factory PR with tests in its diff into a candidate benchmark case (task = the linked issue, base = the commit before the delivery, oracle = those tests; `--validar` keeps only cases whose tests fail on the base and pass on the delivery — ADR-0044). Used by `/validar`, by Patrícia in `/revisar`, by `/avaliar` and by `release.py check`
- `scripts/qualidade.py` — The "make it right" gates over the functions the diff touched (ADR-0045, from ub-mode): `crap` (CC² × (1 − coverage)³ + CC, below 10, coverage read from the suite's own report), `duplicacao` (Jaccard of structural fingerprints, below 0.8) and `mutacao` (operators and `return` swapped one at a time in a throwaway worktree; a survivor is a test that does not notice the change). Python via `ast`, JS/TS and Go via a declared text scan; a legacy ratchet: a function already above the limit on the base that did not get worse is `legado_acima`, not a failure; `linguist-generated` files are skipped. Used by `/validar` (step 4.1) and by Ricardo
- `.gitattributes` — Marks the generated mirrors (`plugin/`, `.cursor/`, `.codex/agents/`, `.opencode/agent/`, `.agents/*/AGENT.md`, the asset manifest) as `linguist-generated`: GitHub collapses them in PR diffs and `qualidade.py` leaves them out (ADR-0045)
- `scripts/release.py` — Version bump with counts computed from the filesystem, a `check` mode run by CI (counts/version, root↔plugin parity, JSON validity, mirrors, static context budget, gold-set integrity, the sealed-set alarm, scripts cited by skills present under `.cursor/scripts/`, signed contracts) and `assinar-contratos` (ADR-0034)
- `scripts/check-agent-security.py` — Security audit of the factory's own setup: explicit allow-list on every agent, dangerous patterns in hook commands, committed secrets. CI runs it on the root and on `plugin/`; `/auditar` points it at the project's config
- `scripts/quadro.py` — Deterministic task board for `/mobilizar` (ADR-0035/0036): dependencies, wave ceiling (6), file-ownership collisions, per-task deadline (`varrer`), compensation in reverse order (`compensar`, Saga), and refusal to close with a hidden gap
- `evals/roteamento-laura/` — Gold set plus `rodar.py`, a headless runner for Laura's routing regression eval (repo-root only, not distributed in `plugin/`). Skips cleanly with exit 0 when no API key is present — a false red trains the team to ignore red
- `evals/comportamento-fabrica/` — Gold set for the five behaviors that separate a harness from a prompt folder (ADR-0031), each tied to a promise the factory already makes in writing. 9 of the 14 cases are decided by reading `.agents/execucoes/` or running `prova.py` — no model in the loop. Running the cases needs an agent; CI keeps the set well-formed via `release.py check`
- `templates/ci/` — Event-driven workflow recipes for the **user's** project (ADR-0026/0040): review-on-PR, fix-on-red-CI, audit-on-cron, triage-on-issue (one label — `forge:pronto` / `forge:precisa-spec` / `forge:falta-informacao` / `forge:aguardar` — as queue, lock and human pause point; `forge:construir` is never applied by the factory)
- `scripts/ciclo.py` — Deterministic state machine for the `entregar` arc (ADR-0029/0033), planning phases included. The skill executes a step and registers the outcome; the script decides the transition. Budget is enforced, not promised; `corrigindo_revisao` has exactly one outgoing edge — back to `validando`; and `registrar aprovado` is read from the validation report on disk, not taken on the agent's word. On approval it seals a digest of the SPEC's contract (Status/Verification cells excluded) and refuses a green gate result if the contract moved until a human runs `reaprovar` — `spec_alterada` in the public view, contract 1.1. On the third consecutive failure of the same gate with no progress (two fixes that did not work) it routes through `atacando_premissa_*` and only moves on once the shared premise is written down and not already attacked in that streak (ADR-0045, contract 1.2)
- `scripts/guardrail.py` — Deterministic guardrails: destructive commands, protected paths, generated artifacts, SPEC integrity, report contracts, **pre-existing test edits** (ADR-0039, born in `aviso`), and the ADR-0042 **floor** (no `modos`, no `liberados`): secret reads via shell and the `Read` tool (`grep` allowed), hook wiring (`.cursor/hooks.json`, `.codex/hooks.json`, and only the `hooks` block of `.claude/settings*.json`), unprovable or out-of-project destruction, machine control; plus a **stop gate** on `Stop` (production written with no green gate afterwards does not end silently; born in `aviso`, never fires twice). Hook mode (exit 2 blocks; on Cursor, JSON in its dialect) and CLI mode for CLIs without `PreToolUse` and for CI (ADR-0022/0032/0037/0039/0042)
- `scripts/tests/` — stdlib `unittest` suites: the `ciclo.py` contracts an external runner depends on (ADR-0034: `registrar` idempotence, SPEC digest, `reaprovar` only after approval), the `guardrail.py` floor (each rule, what it denies and what it lets through; stop gate; Cursor adapter), the `prova.py` sealed-set alarm (ADR-0043), PR autonomy in `telemetria.py`, `prova.py colher` against a real git repository, the `painel.py` inbox (ADR-0044), the three `qualidade.py` gates (with real mutation of a real suite) and the premise attack in `ciclo.py` (ADR-0045). CI runs `python3 -m unittest discover -s scripts/tests -t scripts`
- `scripts/contrato.py` — Pure module for the report boundary contracts (ADR-0032): one fence per report type (` ```kairos-critica ` / ` ```kairos-validacao ` / ` ```kairos-revisao `, never shared — both reports carry the same `**Veredicto:**` line, so a shared fence would let one be read as the other), coherence checks, and proof of coverage: a clean verdict must list what was actually checked. No I/O, never throws — byte-testable and safe to call from a hook
- `scripts/painel.py` — The living board (ADR-0013/0032): renders SPEC requirement status, arc state, both gate verdicts and trajectory into one view — terminal by default, self-contained HTML with `--html` (no CDN, no remote font, no script: it has to open on a machine with no network, which is exactly where someone is debugging a stuck cycle), `--json` for other tooling; `--caixa [--github]` is the inbox — human gates, a SPEC changed after approval, escalated cycles, blocked or overdue board tasks and, with `--github`, `forge:falta-informacao` issues and open factory PRs (ADR-0044). **Rendering, never state** — it writes nothing but the output file you asked for and keeps nothing between runs; a persisted board is the parallel spreadsheet ADR-0013 rejected. It also applies the doctrine to its own number: a requirement marked `Concluído` without `verificado:` does not count as done — it drops to "in progress" and is listed in the warning, because a board that counted the word would show progress `/validar` itself would refuse
- `contratos/ASSINATURA.json` + `docs/contrato-de-integracao.md` — The integration contract (ADR-0034): `ciclo.py estado --json` and the three report fences are a **public, versioned surface** for outside drivers (kairos-symphony). Signed with a sha256 of the declaration and verified by `release.py check` — change the shape without re-signing and CI goes red, because a contract nobody verifies is a promise
- `plugin/` — The distributed copy (the Codex marketplace points to `./plugin`): canonical sources mirrored plus every per-CLI generated mirror, written by `release.py bump`. `evals/` is not shipped; `plugin/README.md` is its own hand-maintained file (`release.py` only rewrites its counts)
- `.github/workflows/ci.yml` — CI on every PR: sync with no pending diff (root and `plugin/`), `release.py check`, `check-agent-security.py`, graph validity (when one exists), `guardrail.py verificar` and the `scripts/tests/` suites. Laura's routing eval runs separately, manually or on merge to `main`, because it costs tokens
- `.github/workflows/pages.yml` — Publishes the landing page to GitHub Pages on every push to `main` that touches `site/` or `marca/`: assembles `site/` with the SVGs from `marca/` and deploys. Deploy only, no gate
- `site/` — The project landing page: a self-contained `index.html` on the design-system tokens, plus `og.png` for link previews. Every number it cites carries a `data-n` attribute that `release.py` rewrites on `bump` and verifies on `check`
- `marca/` — Logo SVGs (horizontal, signature, symbol, app icon and one-color versions) with the text outlined. Kept outside `docs/` so it is not mirrored into `plugin/`
- `hermes/` — Hermes Agent bridge (ADR-0019): routing/cycle skills + workflow + install.sh that plug the factory into a 24/7 Hermes bot as its engineering engine (Hermes operates — kanban, cron, approvals; the factory specs, builds, validates and reviews inside Claude Code)

## Cross-platform compatibility

| Component | Claude Code | Codex CLI | OpenCode | Cursor |
|---|---|---|---|---|
| Plugin manifest | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` | n/a | n/a |
| Marketplace catalog | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` | n/a | n/a |
| Install command | `/plugin marketplace add` (TUI) | `codex plugin marketplace add` + TUI selection, then `sync-multi-cli.py instalar --cli codex` | copy `skills/` + `sync-multi-cli.py instalar --cli opencode` | `cp -R plugin/.cursor/. <project>/.cursor/` (global: see below) |
| Skills | `skills/<name>/SKILL.md` | same `skills/` folder (shared) | `.opencode/skills/` or `.claude/skills/` | `.cursor/skills/` (generated mirror, Agent Skills standard) |
| Subagents | `agents/<id>.md` | `.agents/<id>/AGENT.md` + roles in `.codex/agents/<id>.toml` (generated, ADR-0035) | `.opencode/agent/<id>.md` (generated, `mode: subagent`, ADR-0035) | `.cursor/agents/<id>.md` (generated, adapted frontmatter) |
| SessionStart hook | `hooks/hooks.json` | `.codex/hooks.json` | via `oh-my-opencode` | `.cursor/rules/kairos-forge.mdc` (`alwaysApply`) |
| PostToolUse hook | `hooks/hooks.json` | ❌ (no `Write\|Edit` matcher) | via `oh-my-opencode` | ✅ `afterFileEdit` in the generated `.cursor/hooks.json` (ADR-0042) |
| Execution telemetry (ADR-0021) | ✅ full (4 lifecycle points) | ⚠️ SessionStart only — no usable trajectory | ❌ | ✅ via the generated `.cursor/hooks.json` (ADR-0042) |
| Guardrails in a hook (ADR-0022/0042) | ✅ every class | ❌ CLI mode only | ❌ CLI mode only | ✅ command, read, SPEC, contract and stop; write classes CLI mode only (no pre-edit hook) |
| Parallel team (`/mobilizar`) | ✅ Agent Teams | ✅ `spawn_agent` | ✅ `task` (ADR-0035) | ✅ orchestrated subagents |
| Message a running worker | ✅ `SendMessage` | ✅ `send_message` | ✅ resume via `task_id` | ❌ — relaunch with full context |
| Agent tool allow-list | ✅ enforced | ⚠️ instruction (`apply_patch` survives) | ✅ enforced (`permission`) | ⚠️ degrades to `readonly` |
| Project instructions | `CLAUDE.md` | `AGENTS.md` | `CLAUDE.md` (fallback) or `AGENTS.md` | `AGENTS.md` |

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
| `mobilizar` | ✅ Agent Teams | ✅ `spawn_agent` | ✅ `task` | ✅ orchestrated subagents |
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

Natural flow ordering: `onboardar` → `mapear-arquitetura` (brownfield) → `diagnosticar` (existing system — ADR-0028) → `especificar` → `analisar-ameacas` (sensitive features) → `desenhar` (UI features — ADR-0020) → `mobilizar`/`rodar` → `validar` → `revisar` → `lancar` (gated deploy — ADR-0020) → `mapear-conhecimento` (as docs accumulate; feeds later `mobilizar`/`validar` runs) → `auditar` (weekly) → `evoluir`. The `entregar` skill (ADR-0023) walks that central stretch on its own — specify → build → validate ⇄ fix → review ⇄ fix → PR — routing each failure back to the responsible agent inside a declared budget instead of the user chaining commands by hand. On demand, outside the flow: `otimizar` — a metric-driven ratchet loop (one change per round, measure, keep-or-revert via git, full lineage recorded; sentinels guard against Goodhart; explicit budget and exhaustion criteria — ADR-0012) — and `migrar` — strangler-fig legacy modernization owned by Ivan: characterization tests before touching anything, one slice at a time with a cut-over route and per-slice keep-or-revert (ADR-0018).

**Knowledge graph (Graph Engineering, ADR-0009).** The factory maintains a per-project knowledge graph at `.agents/grafo/` (JSONL entities/relations/aliases with provenance, versioned schema, hub profiles). It acts as shared memory for `mobilizar` teammates, as the grounding layer for `validar` (claims checked against edges; claims absent from the graph escalate to the human), and as the persistent world model that survives context-window flushes. 🕸️ Olívia (`olivia-grafos`, Dados team) owns it via the `mapear-conhecimento` skill; `scripts/grafo.py` handles the deterministic parts, including the **code layer** (`codigo.jsonl`, import/inheritance/instantiation edges extracted by AST, regenerable — ADR-0041).

**Layered persistent memory (ADR-0010).** Three layers: **episodic** (session capture + cross-CLI handoffs via the optional external [ai-memory](https://github.com/akitaonrails/ai-memory) companion, detected through its `memory_*` MCP tools — never bundled, graceful degradation when absent), **curated** (`decisoes/`, `.agents/memory/`, `contextos/` in the repo — a lesson from a change to the factory itself enters `.agents/memory/` only with an observed contrast, ADR-0043), and **structural** (the knowledge graph above). Durable facts flow upward (session → curated file → graph edge); the repo stays the source of truth, and skills never double-write. See `docs/memoria-persistente.md`.

Codex, OpenCode and Cursor all run `mobilizar` (ADR-0035) — see `skills/mobilizar/references/`. `/kairos-forge:rodar` remains the right call for plain sequential conversation.

## Installation per CLI

### Claude Code (recommended)

```
/plugin marketplace add VilelaAI/kairos-forge
/plugin install kairos-forge
/reload-plugins
```

For a parallel team via `mobilizar` on Claude Code:

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
- `.codex/agents/<id>.toml` — subagent roles (generated, ADR-0035). Codex resolves roles from its config dir, not the plugin's: run `python3 scripts/sync-multi-cli.py instalar --cli codex [--escopo global]` once, or `spawn_agent` falls back to the generic agent
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

# Per project (the trailing /. copies the contents — no nested .cursor/.cursor when the folder exists):
mkdir -p /path/to/project/.cursor && cp -R kairos-forge/plugin/.cursor/. /path/to/project/.cursor/

# Or globally, for all projects — personas, skills, rule, scripts and templates:
mkdir -p ~/.cursor && cp -R kairos-forge/plugin/.cursor/{agents,skills,rules,scripts,templates} ~/.cursor/
```

This delivers the 71 subagents (`.cursor/agents/`), the 18 skills in the `/` menu (`.cursor/skills/`), an `alwaysApply` rule with the factory banner and `${CLAUDE_PLUGIN_ROOT}` path resolution, the support scripts and `templates/`, and `hooks.json`, which wires telemetry and guardrails to Cursor's lifecycle events (ADR-0042). The global copy leaves `hooks.json` out on purpose: it calls `.cursor/scripts/` relative to the project root, so telemetry and guardrails need the per-project install. To refresh only the personas later: `python3 kairos-forge/scripts/sync-multi-cli.py instalar --cli cursor [--escopo global]`. Project instructions: Cursor reads `AGENTS.md` — `/kairos-forge:onboardar` offers to generate it alongside `CLAUDE.md`. `mobilizar` runs on Cursor too: the main agent orchestrates the subagents in parallel while `quadro.py` holds the dependency graph, ownership and counts.

### OpenCode

```bash
git clone https://github.com/VilelaAI/kairos-forge.git
# Option A: copy skills to OpenCode's discovery path
cp -r kairos-forge/skills/* .opencode/skills/
# Option B: use Claude Code compatibility path
cp -r kairos-forge/skills/* .claude/skills/

# Personas as delegable subagents (mode: subagent, allow-list enforced as permission)
python3 kairos-forge/scripts/sync-multi-cli.py instalar --cli opencode   # --escopo global for $XDG_CONFIG_HOME/opencode/agent
```

OpenCode reads `CLAUDE.md` as a fallback for `AGENTS.md`, so project instructions load automatically. For hooks, install [oh-my-opencode](https://github.com/fractalmind-ai/oh-my-opencode) which provides a Claude Code hooks compatibility layer.

## Mandatory conventions

1. **PT-BR everywhere.** Skills, agents, commands, comments, commit messages — Portuguese. AGENTS.md and code identifiers may be English when the technology demands.
2. **Infinitive verbs in skill names.** `especificar`, not `spec`.
3. **Skills ≤ 500 lines** in SKILL.md, with the root acting as a router. Heavy reference material lives in skill `references/`. Skill `description` ≤ 300 chars, agent `description` ≤ 260: what it does, when to use it, one routing negative — owner, artifacts and flow summary belong in the body (ADR-0038). `release.py check` enforces both caps and the sum.
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
- **ADR-0035**: `/mobilizar` is no longer Claude Code-only. Auditing the four native tools the skill required against the Codex source: five of six primitives map directly (`spawn_agent`, `wait_agent`, `send_message`/`followup_task`, `close_agent`, `list_agents`) — only the **shared task board with dependencies** had no equivalent. So the board leaves the session and becomes a repo file (`quadro.py`, `.agents/quadro/`), the same move `ciclo.py` made for the arc and for the same reason: wave ceiling, file-ownership collisions and "is this actually done?" stop being the model's judgment. Extending the audit to the other CLIs killed the premise entirely: **all four can spawn parallel workers** — only the launch adapter differed — so the skill now runs on Claude Code, Codex, OpenCode and Cursor, with the 71 personas generated in each one's native format (`.codex/agents/*.toml`, `.opencode/agent/*.md`, `.cursor/agents/*.md`) (v0.28.0)
- **ADR-0036**: deadlines and compensation — the three things `/mobilizar` lacked for failures *after* work starts. A worker that dies silently used to hold its wave slot forever with **no error ever surfacing**; `varrer` now blocks on deadline and frees the slot. Late invalidation was all-or-nothing (declare a gap or redo everything); `compensar` now undoes the invalid task and only what was built on top of it, in reverse order — ADR-0024's `--reverter` was already the compensating action Saga asks for, only the orchestration was missing. Semantic/prompt caching, RAG and model serving from the same source stay out by ADR-0001: the forge is a plugin, not a runtime (v0.29.0)
- **ADR-0037**: reviewing ADOP (AWS) — a direct peer of this repo: a Claude Code plugin with hooks, commands and specialized agents, applied to data. Two gaps, neither about data. The **300+ generated files** (per-CLI mirrors, asset manifest) were guarded only by an in-file comment saying "don't edit here" — editing one raised no error, just silence: the change survived until the next sync, vanished, and CI reported a "pending diff" that points nowhere near the cause. And `/evoluir` never read the trajectory ADR-0021 has collected since v0.17 — the instrument fed only the skill that *reports*, not the one that *improves*. Plus a data-pipeline trilha. ADOP's prompt auto-graft stays out: it is the agent rewriting its own rule (ADR-0022) (v0.30.0)
- **ADR-0038**: lean instructions — the plugin audited against the skills-and-prompts guidance for newer models (Provencher, Codex, Sep 2026). Skill and agent `description`s cut to what + when + one routing negative (agents: 19k → 8.8k chars; skills: 8.8k → 3.3k) and their sum joins the static context budget in `release.py check`, which ADR-0027 had left out; the five largest skills become router + `references/`; the PostToolUse reminder fires once per session instead of on every edit; the boilerplate repeated across the 71 personas becomes one paragraph; anti-drift checkpoints happen per wave (the 3-task count predates the board), and in-session Pequeno-sized features proceed on the recommended default through the first two planning checkpoints — `ciclo.py` and its v1.0 contract are unchanged (v0.31.0)
- **ADR-0039**: verification is the bottleneck — audit against the *TLC AI Dev Flow* (Tech Leads Club, Sep 2026): the agent verifying its own work is not proof. `prova.py` runs each new test against the base without the patch (`passou_na_base` = requirement without evidence) and lists pre-existing tests loosened in the diff; a `teste` class in `guardrail.py`, the first born in `aviso`, traces every edit to a pre-existing test; `/validar` climbs the gates cheap-to-expensive and stops at the first red; `/revisar` re-reads each finding before posting and measures its own noise (`descartado:` on the finding line + `telemetria.py ruido`); the SPEC's T1 is a vertical slice and acceptance criteria carry values, not adjectives. The `tlc-*` skills are not installed — they would duplicate the arc without orchestration (v0.32.0)
- **ADR-0040**: the factory's entry point — what the TLC workshop shows about where work comes in. `templates/ci/kairos-forge-triar.yml`: an issue is triaged by Laura and Joana into `forge:pronto` / `forge:precisa-spec` / `forge:falta-informacao` / `forge:aguardar`, the label being queue, lock and human pause (`forge:construir` belongs to the human, never the factory); `rodar explorar <mission>` — a throwaway POC in a worktree with a time box, notes in `docs/pocs/`, `gh pr create` blocked on `poc/*` branches; a root `DESIGN.md` is the design system (getdesign.md format, owned by Pablo) and `desenhar verificar` checks against it; an appetite ceiling (a cycle becomes chained SPECs); an Origem field on the SPEC, issue-as-input and querying the project's data MCPs before asking the human; a Porta de entrada section in `CLAUDE.md.template` (v0.33.0)
- **ADR-0041**: code graph by AST, legacy readiness ladder and shadow cutover — the two structure boards of the TLC workshop. `grafo.py codigo` writes the graph's code layer (Python via `ast`, JS/TS via regex with `tsconfig` paths, Go via `go.mod`; regenerable, the script's only write) and `contexto <file>` is the *Navigation Paradox*'s `get_architectural_context` (+23 points where text search is blind), used by mobilizar, validar (callers outside the diff), revisar (5+ importers = band 2), mapear-arquitetura, diagnosticar and migrar; a five-rung ladder (reproducible build → standardisation → agent context → characterisation tests → harness) as a `/migrar` precondition and a `/diagnosticar` section; shadow cutover with a comparator and zero divergence for a declared period before any percentage (v0.34.0)
- **ADR-0042**: execution floor, stop gate and Cursor hooks — `guardrail.py` audited against the TLC harness-toolkit (Felipe Rodrigues, Sep 2026; Elastic 2.0, so ideas, not code). Five new floor rules with no `modos` and no `liberados`: secret reads via shell and the `Read` tool (`grep` allowed), hook wiring (`.cursor/hooks.json` and `.codex/hooks.json` whole; only the `hooks` block of `.claude/settings*.json`), `rm -rf` on a variable, out-of-project destruction, machine control. A stop gate on `Stop`: production written with no green gate afterwards does not end silently (born in `aviso`, never fires twice). `sync-multi-cli.py` generates `.cursor/hooks.json`; the Cursor payload is recognised by shape and answered in its dialect — telemetry and guardrails now exist on Cursor. `test_guardrail.py` suite in CI (v0.35.0)
- **ADR-0043**: blind judge, a sealed set that does not leak, and verdicts with contrast — audit against *Harness²* (Google Research, Oct 2026; Apache 2.0, but ideas, not code). Their loop (the agent rewriting its own harness from its own trajectory) stays out — it is the auto-graft ADR-0037 rejected — while the mechanisms that make it trustworthy without ground truth come in. A sixth judge-hygiene rule in `/avaliar`: when comparing versions the judge sees `A`/`B` in an order shuffled with seed `sha1(case|digest)`, the baseline always in the pool, and the letter map opened only after the verdict is recorded. `prova.py selado`: a sealed case copied into a persona, skill, `contextos/`, test or doc, or repeated in the visible set, exits 1 — in `release.py check` and in the project's CI (82 real cases tried, zero false positives). `/evoluir` gives the previous evolution a verdict before choosing the next (`ajudou`/`piorou`/`sem efeito observado`/`confundido`, the last being the default; adoption is not evidence), the EVOL record stores a baseline, and a lesson reaches `.agents/memory/` only with a contrast. A Harness² lab over the forge itself is deferred until a sealed benchmark of 30+ tasks exists (v0.36.0)
- **ADR-0044**: autonomy measured from git, a benchmark harvested from history, and an inbox — a reading of Warp's *Factories*, whose headline metric is the share of PRs merged with no human push and which, though sold as an autonomous factory, does not merge for you. `telemetria.py prs` measures PR autonomy from history (an agent commit carries the `Fabrica: kairos-forge` trailer, `Co-Authored-By: Claude`, or the `kairos-forge` author; `gh` with a fallback to git merges), so the number exists in Codex, OpenCode and CI; the teammate prompt, the anti-drift, `/otimizar` and `corrigir.yml` now write the trailer; `/auditar` reports it next to Autonomy without scoring it. `prova.py colher [--validar]` turns a merged delivery with tests into a candidate case (`evals/entregas/candidatos.jsonl`), keeping only oracles that fail on the base and pass on the delivery — the benchmark source ADR-0043 asked for. `painel.py --caixa [--github]` gathers what is waiting on a person. Human gates and the merge stay human: autonomy is measured before it is granted; self-improvement PRs, auto-merge, push notifications and dollar cost stay out (v0.37.0)
- **ADR-0045**: make it right, and attack the premise — Robert C. Martin's ub-mode absorbed into the factory (the skill's repository declares no license, so ideas, not text; the crapper, dryer and mutator tools are 0BSD and supply the formula and thresholds). `qualidade.py` adds three gates over the functions the diff touched: `crap` below 10, `duplicacao` below 0.8, and `mutacao` with `return x` → `return None` among its mutants; a legacy ratchet (`legado_acima` does not fail, getting worse does); `.gitattributes` takes the generated mirrors out of the measurement. The three run in `/validar` (step 4.1) and Ricardo owns the numbers. `ciclo.py` gains `atacando_premissa_*` (contract 1.2): on the third consecutive failure of the same gate with no progress, the next fix only starts once the premise is written down and new to the streak. `anti-drift.md` gains "make it work, then make it right", and commit bodies now say why, what changed and how it was proven (v0.38.0)

## Critical design constraints

- **All output in PT-BR**: agents communicate in Portuguese, even when invoked from English-language projects. The plugin itself is multilingual (English AGENTS.md, Portuguese CLAUDE.md), but agent personas are Portuguese-native.
- **Squad agents speak in first person**: When running a squad (`/kairos-forge:rodar`), each agent introduces itself by name/role and stays in character.
- **Agent naming**: Format `Name [Role]` with emoji icon (e.g., 👩‍💼 Laura [Tech Lead], 🔐 Helena [Security]).
- **Support squads are non-coding**: Squads with `tipo: apoio` NEVER implement code — they produce textual artifacts only.
- **Name collisions are explicit**: Three pairs share first names across core/support (Marcos, Helena, Elisa). Laura disambiguates before invoking when the user mentions only the first name.
- **Installing personas into a CLI**: `sync-multi-cli.py instalar --cli <codex|opencode|cursor|todos> [--escopo global] [--dry-run]`. Codex and OpenCode discover subagents in their own config dir, not the plugin's. The command is idempotent, removes our own orphans, and **preserves the user's files** when a name collides (detected via the generated-file marker).
- **`.agents/`, `.codex/agents/`, `.opencode/agent/` and `.cursor/` are generated, not edited**: The Claude Code paths (`agents/`, `skills/`) are canonical. Edits to a generated mirror are lost on the next sync, and `guardrail.py` blocks them (class `gerado`, ADR-0037).
- **Failure after work starts** (ADR-0036): `quadro.py varrer` blocks tasks past their deadline and frees the wave slot — a silently dead worker used to hold it forever with no error. `quadro.py compensar <task>` undoes an invalidated task and only its dependents, in reverse order, refusing the whole plan if any affected task declared no `--reverter`.
- **mobilizar runs on all four CLIs** (ADR-0035): of the four native tools the skill used to require, only the **shared task board with dependencies** had no Codex equivalent — so the board moved out of the session into a repo file (`scripts/quadro.py`, state in `.agents/quadro/`). Each CLI now only needs to spawn parallel workers and wait, which Claude Code (`Agent` + `team_name`) and Codex (`spawn_agent`/`wait_agent`) both do. All four CLIs can spawn parallel workers; only the launch adapter differs. On OpenCode parallelism lives in *how you call*: one wave is **one** message with several `task` calls (call-wait-call is a queue with extra steps, and the end result looks identical — which is why the mistake goes unnoticed). On Cursor there is no spawn tool at all: the main agent orchestrates `.cursor/agents/`, and there is no channel to a running worker, so a resolved block means a fresh subagent with full context.
- **The board decides, not the model**: wave ceiling (6), file-ownership collisions and "can I say this is done?" are computed by `quadro.py`, not judged by the agent — same reasoning as `ciclo.py` (ADR-0029). `.agents/quadro/**` is guardrail-protected: the worker never closes its own task.
