# kairos-forge

> Fábrica de software autônoma como plugin do **Claude Code**, **Codex CLI** e **OpenCode**.
> **45 agentes em 16 times** (24 core + 21 apoio). PT-BR oficial. MIT.

Plugin que transforma uma sessão genérica de qualquer CLI compatível em um time completo de desenvolvimento mais um time de apoio textual. Cada agente tem persona, comportamento, allow-list de ferramentas, e personalidade consistente em primeira pessoa. Eles colaboram via `/kairos-forge:rodar` (sequencial) em qualquer CLI ou trabalham em paralelo via Agent Teams nativos (`/kairos-forge:mobilizar`, exclusivo Claude Code).

## Posicionamento

`kairos-forge` é a **versão lite/MIT genérica** da fábrica do KairOS. Cobre o squad técnico + squads de apoio universais.

Para projetos em **domínios regulados brasileiros** (LGPD, Segurança-TI, NRs, OAB, MEC-LDB, ANVISA, BACEN), use o [kairos-ai](https://github.com/VilelaAI/kairos-ai) — que adiciona squads negociais, guardrails com referência legal, assertions binárias, Ralph Loop e Advisor regulatório.

## Os 24 agentes core

| Time | Agentes |
|---|---|
| **Liderança** | 👩‍💼 Laura (Tech Lead) · 🧭 Rafael (Staff) |
| **Produto** | 🎯 Camila (PM) · 🔬 Isabela (UX) |
| **Arquitetura** | 📐 Diego (Sistemas) · 🗄️ Fernanda (Dados) · 🔗 Thiago (Integrações) |
| **Frontend** | ⚛️ Marina (Frontend) · 🎨 Pablo (UI) · ♿ Ada (Acessibilidade) |
| **Backend** | ⚙️ Lucas (Backend) · 🤖 Gabriel (IA) · 📊 Juliana (ETL) |
| **Dados** | 🛢️ Carlos (DBA) · 🔎 André (Busca) |
| **Qualidade** | ✅ Patrícia (QA Lead) · 🧪 Ricardo (Testes) · ⚡ Vinícius (Performance) |
| **Plataforma** | 🚀 Marcos (DevOps) · ☁️ Elisa (Cloud) · 🔐 Helena (Security) · 👁️ Renata (Observabilidade) |
| **Documentação** | 📝 Beatriz (Docs) · 📖 Felipe (API Docs) |

## Os 21 agentes de apoio (7 squads)

Squads de apoio **nunca implementam código** — produzem artefatos textuais.

| Squad | Agentes | Quando |
|---|---|---|
| **Microcopy** ✍️ | Celina, Renato, Letícia | Texto de UI, mensagem de erro, empty state |
| **Narrativa** 📋 | Marcos [Specs], Helena [Apresentação], Dante | ADR, demo, decisão travada |
| **Naming** 🏷️ | Elisa [Naming], Bruno, Cora | Nomenclatura, taxonomia, voz |
| **Valor** ⚖️ | Hugo, Sofia, Rui | Priorização ICE, lançamento, audit ROI |
| **Observabilidade** 📡 | Lia, Otávio, Vera | Tracking plan, AARRR, A/B |
| **DX** 🛠️ | Enzo, Clara, Tomás | Developer journey, contributor ladder, DORA |
| **Revisão Arquitetural** 🔄 | Álvaro, Lúcia, Félix | Pre-mortem, red team, Inversão de Munger |

> ⚠️ **Atenção a colisões de nome:** existem dois Marcos (DevOps/Specs), duas Helenas (Security/Apresentação) e duas Elisas (Cloud/Naming). Quando você disser apenas o primeiro nome, Laura desambigua antes de invocar.

Acionar:

```
/kairos-forge:rodar apoio-naming
/kairos-forge:rodar apoio-revisao-arquitetural
```

## As 7 skills

| Skill | Quando usar | Disponível em |
|---|---|---|
| `/kairos-forge:onboardar` | Primeira vez no projeto | Todos os CLIs |
| `/kairos-forge:especificar <ideia>` | Antes de codar não-trivial | Todos os CLIs |
| `/kairos-forge:rodar [agente\|time\|apoio-X]` | Conversacional/sequencial — modo padrão | Todos os CLIs |
| `/kairos-forge:mobilizar <spec>` | Paralelo via Agent Teams | **Apenas Claude Code** |
| `/kairos-forge:revisar` | Pré-PR. Helena + Patrícia + outros | Todos os CLIs |
| `/kairos-forge:auditar` | Semanal. Pontuação 0–100 da fábrica | Todos os CLIs |
| `/kairos-forge:evoluir` | Semanal pós-auditoria | Todos os CLIs |

## Compatibilidade entre plataformas

| Componente | Claude Code | Codex CLI | OpenCode |
|---|---|---|---|
| Manifest | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` | n/a (lê como skills repo-locais) |
| Marketplace catalog | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` | n/a |
| Comando de instalação | `/plugin marketplace add` (TUI) | `codex plugin marketplace add` + escolher na TUI | `cp -R skills/ .opencode/skills/` |
| Skills | `skills/<nome>/SKILL.md` | mesma pasta `skills/` (compartilhada) | `.opencode/skills/` ou `.claude/skills/` |
| Subagents | `agents/<id>.md` | `.agents/<id>/AGENT.md` | via copy de `agents/` |
| SessionStart hook | `hooks/hooks.json` | `.codex/hooks.json` | via `oh-my-opencode` |
| PostToolUse hook | ✅ | ❌ Codex só matcher Bash | via `oh-my-opencode` |
| Agent Teams (`/mobilizar`) | ✅ nativo | ❌ sem `TeamCreate` | ❌ sem equivalente |
| Instruções de projeto | `CLAUDE.md` | `AGENTS.md` | `CLAUDE.md` (fallback) ou `AGENTS.md` |

> **Nota sobre skills compartilhadas:** Tanto Claude Code quanto Codex descobrem skills em `skills/<nome>/SKILL.md` quando empacotados como plugin. Não há duplicação — a mesma pasta serve aos dois CLIs. Apenas os manifests (`.claude-plugin/` vs `.codex-plugin/`) e os subagents é que diferem.

> **Nota sobre `mobilizar`:** Esta skill é exclusiva do Claude Code. Em Codex/OpenCode ela detecta o ambiente e orienta o usuário a usar `/kairos-forge:rodar` como alternativa.

> **Nota sobre `.agents/<id>/AGENT.md`:** O diretório é **gerado** a partir de `agents/` pelo script `scripts/sync-multi-cli.py`. Não edite arquivos lá — alterações são perdidas no próximo sync. Sempre edite o canônico (`agents/`) e rode o sync.

## Instalação

### Claude Code (recomendado)

```
/plugin marketplace add VilelaAI/kairos-forge
/plugin install kairos-forge
/reload-plugins
```

Para `/mobilizar` paralelo:

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

### Codex CLI

O Codex usa o subcomando `plugin marketplace add` para registrar marketplaces. **Não há flag `--plugin-dir` nem `codex plugin install` na CLI** — a instalação do plugin acontece dentro da TUI depois do marketplace estar registrado.

#### Para desenvolvimento local (a partir do clone)

Em **Linux**:

```bash
git clone https://github.com/VilelaAI/kairos-forge.git
cd kairos-forge

# Registra este diretório como marketplace local
codex plugin marketplace add .

# Abre a TUI do Codex
codex
```

Em **macOS** (usar `cp -R` em vez de `cp -T`):

```bash
git clone https://github.com/VilelaAI/kairos-forge.git
cd kairos-forge

codex plugin marketplace add "$(pwd)"
codex
```

Dentro da TUI, abra o menu de plugins (`/plugin` ou navegação interativa) e instale o `kairos-forge` da marketplace `kairos-forge`.

#### Após publicar no GitHub

```bash
codex plugin marketplace add VilelaAI/kairos-forge
codex
# Dentro da TUI: /plugin → escolher kairos-forge → instalar
```

#### Onde mora o quê (Codex)

- `.codex-plugin/plugin.json` — manifest do plugin
- `.agents/plugins/marketplace.json` — marketplace catalog (necessário pra `marketplace add` funcionar no Codex)
- `skills/<nome>/SKILL.md` — skills (mesmo path do Claude Code)
- `.agents/<id>/AGENT.md` — subagents no formato Codex (gerados a partir de `agents/`)
- `.codex/hooks.json` — hooks Codex (apenas SessionStart — Codex não suporta `Write|Edit` matcher)

Para ativar o hook de SessionStart no Codex, adicione ao seu `~/.codex/config.toml`:

```toml
[features]
codex_hooks = true
```

### OpenCode

```bash
git clone https://github.com/VilelaAI/kairos-forge.git

# Opção A: copiar pra path nativa do OpenCode
cp -r kairos-forge/skills/* .opencode/skills/

# Opção B: usar path de compatibilidade Claude Code
cp -r kairos-forge/skills/* .claude/skills/
```

OpenCode lê `CLAUDE.md` ou `AGENTS.md` automaticamente. Para hooks, instale [oh-my-opencode](https://github.com/fractalmind-ai/oh-my-opencode).

## Primeiros passos

```
/kairos-forge:onboardar
```

Depois (qualquer CLI):

```
/kairos-forge:especificar quero exportar relatorios em CSV
   └─ Laura aciona Diego, que produz SPEC-001

/kairos-forge:rodar apoio-naming
   └─ Elisa, Bruno, Cora ajudam a nomear "exportar" vs "baixar" vs "gerar"

/kairos-forge:rodar
   └─ Laura coordena Carlos, Lucas, Marina, Ricardo em modo conversacional

# Apenas Claude Code:
/kairos-forge:mobilizar SPEC-001
   └─ Carlos + Lucas + Marina + Ricardo em paralelo via Agent Teams

/kairos-forge:rodar apoio-revisao-arquitetural
   └─ Álvaro faz pre-mortem da SPEC antes do merge

/kairos-forge:revisar
   └─ Helena + Patrícia + outros leem o diff
```

## Para contribuidores

Quando alterar arquivos em `agents/` ou `skills/`, **sempre rode o sync** antes de commitar:

```bash
python3 scripts/sync-multi-cli.py
git add agents/ skills/ .agents/
git commit -m "feat(<modulo>): <descrição>"
```

Sem o sync, usuários do Codex CLI ficam desatualizados.

## Convenções

- **PT-BR oficial.** Skills, agentes, comandos, comentários, mensagens de commit.
- **Verbos no infinitivo.** `especificar`, não `spec`.
- **Persona explícita.** Agentes se apresentam: "Oi, Marina aqui — Frontend."
- **Apoio nunca codifica.** Squads de apoio entregam texto.
- **`.agents/` é gerado, não editado.** Edite `agents/` e rode o sync.

## Roadmap

- **v0.4** (atual) — multi-CLI (Claude Code + Codex + OpenCode), 45 agentes, 7 skills
- **v0.5** — integração com Basic Memory para wiki persistente
- **v0.6** — workflow stages YAML (feature-completa, bug-fix, evolucao-noturna)
- **v0.7** — modo debate usando squad apoio-revisao-arquitetural

## Documentação

- [Início rápido](docs/inicio-rapido.md)
- [ADR-0001](docs/adr/0001-plugin-em-vez-de-runtime.md) — plugin não runtime
- [ADR-0002](docs/adr/0002-relacao-com-kairos-ai.md) — Forge vs kairos-ai
- [ADR-0003](docs/adr/0003-portagem-squads-apoio.md) — squads de apoio
- [ADR-0004](docs/adr/0004-multi-cli.md) — compatibilidade Claude Code/Codex/OpenCode

## Licença

MIT. Ver [LICENSE](LICENSE).

## Sobre

Mantido por [VilelaAI](https://vilela.tech). Faz parte da camada Build do KairOS, junto com [kairos-ai](https://github.com/VilelaAI/kairos-ai), kairos-runtime, kairos-domains, kairos-studio e kairos-platform.
