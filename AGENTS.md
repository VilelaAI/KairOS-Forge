# AGENTS.md

> This file mirrors `CLAUDE.md` for Codex CLI and OpenCode compatibility.
> See `CLAUDE.md` for the canonical (Portuguese) version.

## Project Overview

**kairos-forge** is a Claude Code / Codex CLI / OpenCode plugin that delivers a 45-agent software factory in Brazilian Portuguese. The factory consists of **24 core agents** organized in 9 teams (leadership, product, architecture, frontend, backend, data, quality, platform, docs) and **21 support agents** in 7 squads (microcopy, narrative, naming, value, observability, DX, architectural review).

The factory is coordinated by **Laura (Tech Lead)** who analyzes task complexity and only mobilizes the relevant agents. Agents respond in the first person with consistent personas.

## Positioning vs kairos-ai

`kairos-forge` is the **MIT generic** version of the KairOS factory. For projects in **Brazilian regulated domains** (LGPD, IT Security, NRs, OAB, MEC-LDB, ANVISA, BACEN), use [kairos-ai](https://github.com/VilelaAI/kairos-ai), which adds business squads, legal guardrails, binary assertions, Ralph Loop, and a regulatory advisor.

The two plugins are independent — one does not import from the other. The 24 core agents are intentionally duplicated and may diverge over time.

## Plugin Structure

- `.claude-plugin/plugin.json` — Plugin manifest (Claude Code)
- `agents/` — 45 subagents as `<id>.md` files (Claude Code format)
- `skills/<name>/SKILL.md` — 7 skills, invoked as `/kairos-forge:<name>` (Claude Code format)
- `hooks/hooks.json` — Claude Code hooks (SessionStart banner + PostToolUse pedagogical reminder)
- `.agents/` — Same content as `agents/` and `skills/`, in Codex CLI format (`<id>/AGENT.md` for agents, `skills/<name>/SKILL.md` for skills)
- `.codex/hooks.json` — Codex-specific hooks (no `Write|Edit` matcher; only Bash supported)
- `templates/` — `CLAUDE.md.template`, `squad-fabrica.yaml`, `anti-drift.md`
- `docs/adr/` — Architecture Decision Records
- `scripts/sync-multi-cli.py` — Regenerates `.agents/` from `agents/` + `skills/` whenever the canonical Claude Code sources change

## Cross-platform compatibility

| Component | Claude Code | Codex CLI | OpenCode |
|---|---|---|---|
| Plugin manifest | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` | n/a |
| Marketplace catalog | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` | n/a |
| Install command | `/plugin marketplace add` (TUI) | `codex plugin marketplace add` + TUI selection | `cp -R skills/ .opencode/skills/` |
| Skills | `skills/<name>/SKILL.md` | same `skills/` folder (shared) | `.opencode/skills/` or `.claude/skills/` |
| Subagents | `agents/<id>.md` | `.agents/<id>/AGENT.md` | via copy of `agents/` |
| SessionStart hook | `hooks/hooks.json` | `.codex/hooks.json` | via `oh-my-opencode` |
| PostToolUse hook | `hooks/hooks.json` | ❌ (only Bash matcher) | via `oh-my-opencode` |
| Agent Teams (`/mobilizar`) | ✅ native (`TeamCreate`) | ❌ no equivalent | ❌ no equivalent |
| Project instructions | `CLAUDE.md` | `AGENTS.md` | `CLAUDE.md` (fallback) or `AGENTS.md` |

**Skills are shared, not duplicated.** Both Claude Code and Codex discover skills at `skills/<name>/SKILL.md` when packaged as plugin. Only the manifest, marketplace catalog, and the subagent format differ.

### Skill availability per CLI

All 7 skills live in `skills/` and are accessible to both Claude Code and Codex.

| Skill | Claude Code | Codex CLI | OpenCode |
|---|---|---|---|
| `onboardar` | ✅ | ✅ | ✅ |
| `especificar` | ✅ | ✅ | ✅ |
| `rodar` | ✅ | ✅ | ✅ |
| `mobilizar` | ✅ | ⚠️ skill loads but detects environment and redirects to `rodar` | ⚠️ same as Codex |
| `revisar` | ✅ | ✅ | ✅ |
| `auditar` | ✅ | ✅ | ✅ |
| `evoluir` | ✅ | ✅ | ✅ |

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
5. **Personas are fixed.** The 24 core agents and 21 support agents have stable names and personalities. Do not invent new ones — use existing or open an ADR for a new persona.
6. **Support agents never code.** They produce textual artifacts (Markdown, lists, tables, plans).

## Workflow for changes

- Modify a skill or agent → run `python3 scripts/sync-multi-cli.py` → bump patch version
- Add new agent or skill → run sync → bump minor version + new ADR
- Change fundamental contract (e.g., file ownership protocol, SPEC format) → bump major + new ADR

Always run `/reload-plugins` (Claude Code) or restart the CLI (Codex/OpenCode) after sync.

## Decisions made

- **ADR-0001**: plugin instead of standalone runtime (independent of Claude Code internals)
- **ADR-0002**: relationship with kairos-ai — Forge is lite/MIT, kairos-ai is regulated/PRO
- **ADR-0003**: porting of the 21 support agents from kairos-ai
- **ADR-0004**: multi-CLI compatibility — Claude Code canonical, Codex via `.agents/` mirror, OpenCode via fallback paths

## Critical design constraints

- **All output in PT-BR**: agents communicate in Portuguese, even when invoked from English-language projects. The plugin itself is multilingual (English AGENTS.md, Portuguese CLAUDE.md), but agent personas are Portuguese-native.
- **Squad agents speak in first person**: When running a squad (`/kairos-forge:rodar`), each agent introduces itself by name/role and stays in character.
- **Agent naming**: Format `Name [Role]` with emoji icon (e.g., 👩‍💼 Laura [Tech Lead], 🔐 Helena [Security]).
- **Support squads are non-coding**: Squads with `tipo: apoio` NEVER implement code — they produce textual artifacts only.
- **Name collisions are explicit**: Three pairs share first names across core/support (Marcos, Helena, Elisa). Laura disambiguates before invoking when the user mentions only the first name.
- **`.agents/` is generated, not edited**: The Claude Code paths (`agents/`, `skills/`) are canonical. Edits to `.agents/` will be lost on next sync.
- **mobilizar is Claude Code-exclusive**: Agent Teams require `TeamCreate`/`TaskCreate` which only exist in Claude Code. The skill is mirrored to `.agents/skills/` but informs the user when invoked under Codex/OpenCode.
