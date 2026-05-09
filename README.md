# kairos-forge

> Marketplace single-plugin do **kairos-forge**: fábrica de software autônoma com 45 agentes em PT-BR para Claude Code, Codex CLI e OpenCode. MIT.

Este repositório é um **marketplace catalog** que distribui o plugin `kairos-forge`. Para a documentação completa do plugin (agentes, skills, comandos), veja [`plugin/README.md`](plugin/README.md).

## O plugin distribuído

**`kairos-forge`** — 45 agentes (24 core + 21 apoio em 7 squads) coordenados por Laura (Tech Lead), 7 skills cobrindo o ciclo completo (onboarding → especificação → execução paralela → revisão → auditoria → evolução).

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
    ├── .agents/, .codex/
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
/kairos-forge:revisar                 # Helena + Patrícia + outros
/kairos-forge:auditar                 # semanal, pontuação 0–100
/kairos-forge:evoluir                 # 1 capacidade nova/semana
```

Documentação completa em [`plugin/README.md`](plugin/README.md).

## Para contribuidores

Quando alterar `plugin/agents/` ou `plugin/skills/`, rode o sync antes de commitar:

```bash
cd plugin
python3 scripts/sync-multi-cli.py
git add agents/ .agents/
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
