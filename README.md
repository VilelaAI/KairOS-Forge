# kairos-forge

> Marketplace single-plugin do **kairos-forge**: fábrica de software autônoma com 71 agentes em PT-BR para Claude Code, Codex CLI, OpenCode e Cursor. MIT.

Este repositório é um **marketplace catalog** que distribui o plugin `kairos-forge`. Para a documentação completa do plugin (agentes, skills, comandos), veja [`plugin/README.md`](plugin/README.md).

## O plugin distribuído

**`kairos-forge`** — 71 agentes (40 core + 31 apoio em 10 squads) coordenados por Laura (Tech Lead), 17 skills cobrindo o ciclo completo (onboarding → mapa arquitetural brownfield → especificação rastreável → threat model → design → execução paralela/sequencial → validação contra SPEC → revisão → lançamento com gates → grafo de conhecimento com proveniência → evals com rubrica → auditoria em 6 dimensões → evolução).

A partir da v0.17 o harness se instrumenta e se contém: **telemetria de execução** gravada por hook (a autonomia da fábrica vira número), **guardrails determinísticos** que bloqueiam comando destrutivo e SPEC sem evidência, o **arco fechado** do `/kairos-forge:entregar` (a falha volta ao agente responsável, não ao usuário) e **gatilhos por evento** prontos para o CI do seu projeto.

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

Isso entrega os 71 subagents, as 17 skills no menu `/`, a rule com o banner da fábrica e os arquivos de suporte (`grafo.py`, `telemetria.py`, `guardrail.py`, templates). `mobilizar` detecta o Cursor e redireciona pra `rodar`.

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
/kairos-forge:entregar <feature>      # o ciclo inteiro sozinho, até o PR (caminho curto)
```

Ou etapa por etapa, quando você quer conduzir:

```
/kairos-forge:especificar <ideia>     # Laura aciona arquitetos, produz SPEC
/kairos-forge:rodar                   # execução conversacional sequencial
/kairos-forge:mobilizar SPEC-NNN      # paralelo via Agent Teams (Claude Code)
/kairos-forge:validar SPEC-NNN        # aceite contra SPEC, corroborado pela trajetória
/kairos-forge:revisar                 # Helena + Patrícia + outros
/kairos-forge:lancar                  # deploy com gates, health check e rollback anotado
/kairos-forge:avaliar <comportamento> # eval com gold set e rubrica, como gate de CI
/kairos-forge:mapear-conhecimento     # grafo de conhecimento: memória compartilhada da fábrica
/kairos-forge:otimizar <métrica>      # ciclo de catraca: 1 mudança por rodada, manter ou reverter
/kairos-forge:auditar                 # semanal, 0–120 em 6 dimensões (inclui Autonomia medida)
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

Para bumpar versão, **não edite os manifests à mão** — o script de release calcula as
contagens do filesystem, injeta versão e números em todos os manifests, banners e docs,
roda os dois syncs e espelha em `plugin/`:

```bash
python3 scripts/release.py bump 0.20.0   # tudo de uma vez
python3 scripts/release.py check         # o que o CI roda em todo PR
```

O `check` verifica versão, contagens, paridade raiz↔`plugin/`, JSON válido, mirrors,
orçamento de contexto estático e o limite de 500 linhas por skill.

## Licença

MIT. Ver [LICENSE](LICENSE).

## Sobre

Mantido por [VilelaAI](https://vilela.tech). Faz parte da camada Build do KairOS, junto com [kairos-ai](https://github.com/VilelaAI/kairos-ai), kairos-runtime, kairos-domains, kairos-studio e kairos-platform.
