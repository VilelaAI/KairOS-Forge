# kairos-forge — guia para o Claude

Plugin Claude Code / Codex CLI / OpenCode que entrega uma fábrica de software de 45 agentes em PT-BR. Você está editando o próprio plugin.

## O que este projeto é

Plugin multi-CLI (não runtime, não SDK). 45 agentes (24 core + 21 apoio em 7 squads), 7 skills, hooks por CLI, coordenação por Laura (Tech Lead).

## Posicionamento vs kairos-ai

`kairos-forge` é a **versão MIT genérica** (qualquer projeto). O [`kairos-ai`](https://github.com/VilelaAI/kairos-ai) é a **versão regulada** (LGPD, NRs, OAB, etc.) com squads negociais, guardrails legais, assertions binárias, Ralph Loop e Advisor Opus.

Não duplique funcionalidade entre os dois. Se algo é **regulatório**, vai pro kairos-ai. Se é **técnico genérico**, pode ir pros dois (mas o forge nunca importa do kairos-ai — independência total).

## Convenções obrigatórias

1. **PT-BR em tudo.** Skills, agentes, comandos, comentários, mensagens de commit, ADRs. Exceção única: `AGENTS.md` na raiz é em inglês (formato padrão Codex/OpenCode).
2. **Verbos no infinitivo nos nomes de skills.** `especificar`, não `spec`.
3. **Skills ≤ 500 linhas no SKILL.md.** Material pesado vai em `references/` da skill.
4. **Agentes têm allow-list explícita de ferramentas.** Nunca dar acesso total a todos.
5. **Acentuação PT-BR correta.** `solução`, não `solucao`. Verifique antes de commitar.
6. **Personas consistentes.** Os 45 agentes têm nomes e personalidades fixas. Não invente novos — use existentes ou peça via ADR.

## Workflow para mudanças (CRÍTICO)

Os arquivos canônicos são **`agents/`** e **`skills/`** (formato Claude Code). O diretório **`.agents/`** é GERADO automaticamente para Codex CLI.

**Sempre que alterar agents/ ou skills/, rode antes de commitar:**

```bash
python3 scripts/sync-multi-cli.py
git add agents/ skills/ .agents/
```

Sem o sync, usuários do Codex CLI pegam versão desatualizada.

- Mudar prompt de agente ou skill → bump patch (0.4.x) + rodar sync
- Adicionar agente ou skill → bump minor (0.x.0) + ADR + rodar sync
- Mudar contrato fundamental → bump major (x.0.0) + ADR + rodar sync

## Estrutura

| Path | O que tem | Mantido por |
|---|---|---|
| `.claude-plugin/plugin.json` | Manifest Claude Code | manual |
| `.claude-plugin/marketplace.json` | Catalog do marketplace Claude Code | manual |
| `.codex-plugin/plugin.json` | Manifest Codex CLI | manual |
| `.agents/plugins/marketplace.json` | Catalog do marketplace Codex (mesmo conteúdo do Claude Code mas em path próprio) | manual |
| `agents/<id>.md` | 45 subagentes (canônico Claude Code) | manual |
| `.agents/<id>/AGENT.md` | Mirror Codex dos subagents | **gerado** por `scripts/sync-multi-cli.py` |
| `skills/<verbo>/SKILL.md` | 7 skills (compartilhadas — Claude Code e Codex leem da mesma pasta) | manual |
| `hooks/hooks.json` | Hooks Claude Code (SessionStart + PostToolUse) | manual |
| `.codex/hooks.json` | Hooks Codex (apenas SessionStart — Codex não suporta `Write\|Edit` matcher) | manual |
| `AGENTS.md` | Espelho em inglês do CLAUDE.md raiz, para Codex/OpenCode | manual |
| `templates/` | `CLAUDE.md.template`, `squad-fabrica.yaml`, `anti-drift.md` | manual |
| `docs/adr/` | ADRs | manual |
| `scripts/sync-multi-cli.py` | Regenera `.agents/<id>/AGENT.md` a partir de `agents/` | manual |

> **Importante: skills/ é compartilhada.** Tanto Claude Code quanto Codex CLI descobrem skills em `skills/<nome>/SKILL.md` quando empacotados como plugin. Não há duplicação. Apenas os subagents (`agents/<id>.md` no Claude Code, `.agents/<id>/AGENT.md` no Codex) é que precisam de mirror.

> **Importante: dois marketplace.json.** Claude Code procura em `.claude-plugin/marketplace.json` e Codex em `.agents/plugins/marketplace.json`. Os dois têm o mesmo conteúdo. Quando bumpar versão, atualize ambos juntos (existe TODO de unificar via script de release).

## Decisões já tomadas

- **ADR-0001**: plugin em vez de runtime standalone
- **ADR-0002**: relação com kairos-ai — forge é lite/MIT, kairos-ai é regulado/PRO
- **ADR-0003**: portagem dos 21 agentes de apoio
- **ADR-0004**: compatibilidade multi-CLI (Claude Code + Codex + OpenCode)

## Limitações conhecidas por CLI

| Item | Claude Code | Codex CLI | OpenCode |
|---|---|---|---|
| `/kairos-forge:mobilizar` (Agent Teams) | ✅ | ❌ skill avisa e sugere `rodar` | ❌ skill avisa e sugere `rodar` |
| Hook PostToolUse pedagógico | ✅ | ❌ | ❌ (sem `oh-my-opencode`) |
| SessionStart banner | ✅ | ✅ | ❌ (sem `oh-my-opencode`) |

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
