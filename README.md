# kairos-forge

> Marketplace single-plugin do **kairos-forge**: fábrica de software autônoma com 71 agentes em PT-BR para Claude Code, Codex CLI, OpenCode e Cursor. MIT.

Este repositório é um **marketplace catalog** que distribui o plugin `kairos-forge`. Para a documentação completa do plugin (agentes, skills, comandos), veja [`plugin/README.md`](plugin/README.md).

## O plugin distribuído

**`kairos-forge`** — 71 agentes (40 core + 31 apoio em 10 squads) coordenados por Laura (Tech Lead), 13 skills cobrindo o ciclo completo (onboarding → mapa arquitetural brownfield → especificação rastreável → threat model → execução paralela/sequencial → validação contra SPEC → revisão → grafo de conhecimento com proveniência → auditoria em 5 dimensões → evolução).

Para projetos em **domínios regulados brasileiros** (LGPD, NRs, OAB, etc.), use [kairos-ai](https://github.com/VilelaAI/kairos-ai) em vez deste — adiciona squads negociais, guardrails legais, assertions binárias e advisor regulatório.

## Estrutura deste repositório

```
kairos-forge/                          ← repo = MARKETPLACE
├── README.md                          ← este arquivo
├── LICENSE
├── .gitignore
├── .claude-plugin/
│   └── marketplace.json               ← catalog Claude Code
├── .agents/
│   └── plugins/
│       └── marketplace.json           ← catalog Codex CLI
└── plugin/                            ← o plugin propriamente dito
    ├── README.md                      ← documentação completa do plugin
    ├── CLAUDE.md, AGENTS.md
    ├── .claude-plugin/plugin.json     ← manifest Claude Code
    ├── .codex-plugin/plugin.json      ← manifest Codex CLI
    ├── skills/, agents/, hooks/
    ├── .agents/, .codex/               ← mirror Codex (gerado)
    ├── .cursor/                        ← distribuição Cursor (gerada)
    ├── docs/, templates/, scripts/
    └── ...
```

A separação `repo (marketplace) ↔ plugin/ (subdir)` é exigência dos dois CLIs — eles esperam plugin em subdiretório, com o marketplace catalog apontando pra ele via campo `source`.

## Instalação

### Claude Code

```
/plugin marketplace add VilelaAI/kairos-forge
/plugin install kairos-forge@kairos-forge
/reload-plugins
```

Para `/kairos-forge:mobilizar` (Agent Teams paralelo):

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

### Codex CLI

```bash
# Adicionar marketplace (local ou GitHub)
codex plugin marketplace add VilelaAI/kairos-forge
# ou local:
codex plugin marketplace add "$(pwd)"

# Abrir TUI e instalar via menu
codex
# Dentro da TUI: digite /plugin → escolher kairos-forge → instalar
```

Para ativar o hook de SessionStart, adicione ao `~/.codex/config.toml`:

```toml
[features]
codex_hooks = true
```

### Cursor

Sem marketplace no Cursor — a instalação é uma cópia única da distribuição gerada `.cursor/` (requer Cursor 2.4+ para os subagents):

```bash
git clone https://github.com/VilelaAI/kairos-forge.git

# Por projeto:
cp -R kairos-forge/plugin/.cursor /caminho/do/projeto/.cursor

# Ou global (todos os projetos):
cp -R kairos-forge/plugin/.cursor/* ~/.cursor/
```

Isso entrega os 71 subagents, as 13 skills no menu `/`, a rule com o banner da fábrica e os arquivos de suporte (`grafo.py`, templates). `mobilizar` detecta o Cursor e redireciona pra `rodar`.

### Hermes Agent (bot 24/7 — ponte)

A fábrica também opera como **motor de engenharia do [Hermes Agent](https://hermes-agent.nousresearch.com)**: você pede pelo Telegram, o Hermes opera (kanban, aprovações) e a fábrica especifica/constrói/valida dentro do Claude Code. Instalação e arquitetura em [`hermes/README.md`](plugin/hermes/README.md) (ADR-0019).

### OpenCode

```bash
git clone https://github.com/VilelaAI/kairos-forge.git
# Opção A: path nativo OpenCode
cp -R kairos-forge/plugin/skills/* .opencode/skills/

# Opção B: fallback Claude Code
cp -R kairos-forge/plugin/skills/* .claude/skills/
```

## Primeiros passos

Após instalar:

```
/kairos-forge:onboardar
```

Entrevista de 7 perguntas que prepara seu projeto. Depois disso o ciclo padrão é:

```
/kairos-forge:especificar <ideia>     # Laura aciona arquitetos, produz SPEC
/kairos-forge:rodar                   # execução conversacional sequencial
/kairos-forge:mobilizar SPEC-NNN      # paralelo via Agent Teams (Claude Code)
/kairos-forge:validar SPEC-NNN        # aceite contra requisitos/gates da SPEC
/kairos-forge:revisar                 # Helena + Patrícia + outros
/kairos-forge:mapear-conhecimento     # grafo de conhecimento: memória compartilhada da fábrica
/kairos-forge:otimizar <métrica>      # ciclo de catraca: 1 mudança por rodada, manter ou reverter
/kairos-forge:auditar                 # semanal, pontuação 0–100
/kairos-forge:evoluir                 # 1 capacidade nova/semana
```

Documentação completa em [`plugin/README.md`](plugin/README.md).

## Para contribuidores

Quando alterar `plugin/agents/` ou `plugin/skills/`, rode o sync antes de commitar:

```bash
cd plugin
python3 scripts/sync-multi-cli.py
git add agents/ skills/ .agents/ .cursor/
```

Quando bumpar versão, atualize **todos** os 4 arquivos:

- `.claude-plugin/marketplace.json` (catalog)
- `.agents/plugins/marketplace.json` (catalog)
- `plugin/.claude-plugin/plugin.json` (manifest Claude Code)
- `plugin/.codex-plugin/plugin.json` (manifest Codex)

## Licença

MIT. Ver [LICENSE](LICENSE).

## Sobre

Mantido por [VilelaAI](https://vilela.tech). Faz parte da camada Build do KairOS, junto com [kairos-ai](https://github.com/VilelaAI/kairos-ai), kairos-runtime, kairos-domains, kairos-studio e kairos-platform.
