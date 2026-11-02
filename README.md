# kairos-forge

> Marketplace single-plugin do **kairos-forge**: fábrica de software autônoma com 71 agentes em PT-BR para Claude Code, Codex CLI, OpenCode e Cursor. MIT.

Este repositório é ao mesmo tempo a **fonte do plugin** e o **marketplace catalog** que distribui o plugin `kairos-forge`. Para a documentação completa do plugin (agentes, skills, comandos), veja [`plugin/README.md`](plugin/README.md).

## O plugin distribuído

**`kairos-forge`** — 71 agentes (40 core + 31 apoio em 10 squads) coordenados por Laura (Tech Lead), 18 skills cobrindo o ciclo completo (onboarding → mapa arquitetural brownfield → diagnóstico de sistema existente → especificação rastreável → threat model → design → execução paralela/sequencial → validação contra SPEC → revisão → lançamento com gates → grafo de conhecimento com proveniência → auditoria em 6 dimensões → evolução). O `/kairos-forge:entregar` percorre o trecho central sozinho, até o PR; `otimizar` (catraca contra métrica), `migrar` (estrangulamento de legado) e `avaliar` (evals com rubrica) entram sob demanda.

A partir da v0.17 o harness se instrumenta e se contém: **telemetria de execução** gravada por hook (a autonomia da fábrica vira número), **guardrails determinísticos** que bloqueiam comando destrutivo e SPEC sem evidência, o **arco fechado** do `/kairos-forge:entregar` (a falha volta ao agente responsável, não ao usuário) e **gatilhos por evento** prontos para o CI do seu projeto.

E a partir da v0.23 o gate decide pela variável certa: a **faixa de raio de explosão** do `/kairos-forge:revisar` pergunta *quanto custa desfazer*, não *quão confiante estou* — confiança é a variável fraca, e é justamente a que o modelo controla. Mudança contida fecha com gate verde; mudança difícil de reverter é do humano, sempre.

Da v0.28 à v0.40 o que era prosa virou código:
- O `/kairos-forge:mobilizar` roda nos quatro CLIs. O quadro de tarefas virou arquivo (`quadro.py`), com tempo limite e compensação em ordem inversa (ADR-0035/0036).
- Teste novo que passa sem a mudança é acusado (`prova.py`, ADR-0039).
- O grafo ganha uma camada de código extraída por AST (ADR-0041).
- O guardrail ganha um piso que não se configura (leitura de segredo, fiação dos hooks, `rm -rf` não provável) e um gate de parada, com hooks também no Cursor (ADR-0042).
- O juiz dos evals fica cego à versão, o conjunto selado não pode vazar para a instrução, e o `/evoluir` dá veredicto à evolução da semana anterior (ADR-0043).
- A autonomia passa a ser medida pelo histórico do git, em qualquer CLI: PRs mesclados da fábrica sem nenhum commit humano (`telemetria.py prs`). Cada entrega mesclada com teste vira caso de benchmark (`prova.py colher`), e `painel.py --caixa` mostra o que está esperando por você (ADR-0044).
- O "deixar certo" vira gate no diff: CRAP abaixo de 10, duplicação estrutural abaixo de 0,8 e mutação nas linhas tocadas (`qualidade.py`), com catraca para o legado. Na terceira falha seguida do mesmo gate, o `/entregar` só volta a corrigir depois de escrever a premissa que vai atacar (ADR-0045).
- Pular o pre-commit (`--no-verify`, `HUSKY=0`) entra no piso do guardrail; mexer na config do linter ou calar uma linha com `# noqa` deixa rastro; e revisão com um revisor a menos, ou com um 🔴 só em dúvida, não fecha limpa (ADR-0046).
- A fábrica entra no [Tucano](https://github.com/eduwxyz/tucano) como um time importado: sete personas, cada uma no seu harness (quem constrói no Claude Code, quem revisa no Codex, um no OpenCode), as skills e os scripts no projeto (`tucano.py instalar`, ADR-0047).

Para projetos em **domínios regulados brasileiros** (LGPD, NRs, OAB, etc.), use [kairos-ai](https://github.com/VilelaAI/kairos-ai) em vez deste — adiciona squads negociais, guardrails legais, assertions binárias e advisor regulatório.

## Estrutura deste repositório

```
kairos-forge/                          ← repo = fonte canônica + MARKETPLACE
├── README.md                          ← este arquivo
├── LICENSE, .gitignore
├── CLAUDE.md, AGENTS.md               ← guia de quem edita o plugin
├── .claude-plugin/
│   ├── marketplace.json               ← catalog Claude Code (source: ./plugin)
│   ├── plugin.json                    ← manifest Claude Code
│   └── ativos.manifest.json           ← manifesto de ativos (gerado)
├── .codex-plugin/plugin.json          ← manifest Codex CLI
├── .agents/plugins/marketplace.json   ← catalog Codex CLI (aponta para ./plugin)
├── agents/, skills/                   ← CANÔNICOS: 71 personas, 18 skills
├── hooks/, scripts/, templates/, contratos/
├── docs/, hermes/
├── evals/                             ← gold sets do próprio plugin (não distribuídos)
├── .agents/, .codex/agents/           ← mirror Codex (gerado)
├── .opencode/agent/                   ← subagents OpenCode (gerado)
├── .cursor/                           ← distribuição Cursor (gerada)
└── plugin/                            ← a cópia distribuída, escrita pelo release.py
    ├── README.md                      ← documentação completa do plugin (mantida à mão)
    ├── CLAUDE.md, AGENTS.md
    ├── .claude-plugin/, .codex-plugin/
    ├── agents/, skills/, hooks/, scripts/, templates/, contratos/
    ├── .agents/, .codex/, .opencode/, .cursor/
    └── docs/, hermes/
```

A separação `raiz (fonte + marketplace) ↔ plugin/ (subdir)` é exigência dos dois CLIs com marketplace — eles esperam o plugin em subdiretório, com o catalog apontando pra ele via campo `source`. Nada em `plugin/` se edita à mão, exceto o `plugin/README.md`: o `release.py bump` reescreve o resto a partir da raiz.

## Instalação

### Claude Code

```
/plugin marketplace add VilelaAI/kairos-forge
/plugin install kairos-forge@kairos-forge
/reload-plugins
```

Para `/kairos-forge:mobilizar` (time paralelo via Agent Teams):

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

Para `/kairos-forge:mobilizar` (time paralelo via subagents nativos, ADR-0035), instale
os roles das 71 personas — é o que faz `spawn_agent(agent_type: "carlos-dba")` resolver
o agente em vez de receber a persona colada no prompt:

```bash
python3 <plugin>/scripts/sync-multi-cli.py instalar --cli codex --escopo global
```

Use `--escopo projeto` para instalar só no projeto atual, `--dry-run` para ver o que
mudaria antes, e `--cli todos` para instalar Codex, OpenCode e Cursor de uma vez. O
comando é idempotente e **preserva agentes seus** que tenham nome coincidente.

O teto de concorrência do Codex (`agents.max_concurrent_threads_per_session`, default 6)
coincide com o teto de onda da fábrica. Se você baixar um, baixe o outro junto.

### Cursor

Sem marketplace no Cursor — a instalação é uma cópia da distribuição gerada `.cursor/` (requer Cursor 2.4+ para os subagents):

```bash
git clone https://github.com/VilelaAI/kairos-forge.git

# Por projeto (o /. no fim copia o conteúdo — não aninha .cursor/.cursor se a pasta já existe):
mkdir -p /caminho/do/projeto/.cursor && cp -R kairos-forge/plugin/.cursor/. /caminho/do/projeto/.cursor/

# Ou global (todos os projetos) — personas, skills, rule, scripts e templates:
mkdir -p ~/.cursor && cp -R kairos-forge/plugin/.cursor/{agents,skills,rules,scripts,templates} ~/.cursor/
```

Isso entrega os 71 subagents, as 18 skills no menu `/`, a rule com o banner da fábrica, os scripts que as skills chamam (`grafo.py`, `telemetria.py`, `execucao.py`, `guardrail.py`, `diagnostico.py`, `ciclo.py`, `contrato.py`, `painel.py`, `quadro.py`, `prova.py`), os templates e o `hooks.json` que liga telemetria e guardrail aos eventos do Cursor (ADR-0042). A cópia global deixa o `hooks.json` de fora de propósito: ele chama `.cursor/scripts/` relativo à raiz do projeto, então telemetria e guardrail exigem a instalação por projeto. Para atualizar só as personas: `python3 kairos-forge/scripts/sync-multi-cli.py instalar --cli cursor`. `mobilizar` roda no Cursor: o agente principal orquestra os subagents em paralelo enquanto o `quadro.py` guarda dependências, posse e contagem.

### OpenCode

```bash
git clone https://github.com/VilelaAI/kairos-forge.git
# Opção A: path nativo OpenCode
cp -R kairos-forge/plugin/skills/* .opencode/skills/

# Opção B: fallback Claude Code
cp -R kairos-forge/plugin/skills/* .claude/skills/

# Personas como subagents delegáveis (mode: subagent, allow-list enforced como permission).
# Sem isso, o task(subagent_type) do /mobilizar não delega:
python3 kairos-forge/scripts/sync-multi-cli.py instalar --cli opencode   # --escopo global → $XDG_CONFIG_HOME/opencode/agent
```

### Hermes Agent (bot 24/7 — ponte)

A fábrica também opera como **motor de engenharia do [Hermes Agent](https://hermes-agent.nousresearch.com)**: você pede pelo Telegram, o Hermes opera (kanban, aprovações) e a fábrica especifica/constrói/valida dentro do Claude Code. Instalação e arquitetura em [`hermes/README.md`](plugin/hermes/README.md) (ADR-0019).

### O que cada CLI ganha em hooks

As skills e as personas são as mesmas nos quatro CLIs; o que muda é o que roda sozinho:

| | Claude Code | Cursor | Codex CLI | OpenCode |
|---|---|---|---|---|
| Telemetria de execução | ✅ | ✅ (`.cursor/hooks.json`) | ⚠️ só SessionStart | ❌ |
| Guardrail em hook | ✅ todas as classes | ✅ comando, leitura, SPEC, contrato e parada; escrita só no modo CLI | ❌ só modo CLI | ❌ só modo CLI |

Onde não há hook, a dimensão Autonomia do `/auditar` fica em 0 e o `/validar` pula a corroboração de trajetória — comportamento honesto, não bug. O caminho é rodar `python3 <plugin>/scripts/guardrail.py verificar .` e os gatilhos de `plugin/templates/ci/` no CI do projeto.

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
/kairos-forge:mapear-arquitetura      # brownfield: inventário estrutural (Diego)
/kairos-forge:diagnosticar            # sistema existente: seis dimensões, evidência medida (Rafael)
/kairos-forge:especificar <ideia>     # Laura aciona arquitetos, produz SPEC
/kairos-forge:analisar-ameacas <spec> # threat model antes de feature sensível (Helena)
/kairos-forge:desenhar SPEC-NNN       # feature com UI: handoff de design e verificação visual
/kairos-forge:rodar                   # execução conversacional sequencial
/kairos-forge:mobilizar SPEC-NNN      # time paralelo (Claude Code, Codex, OpenCode e Cursor)
/kairos-forge:validar SPEC-NNN        # aceite contra SPEC, corroborado pela trajetória
/kairos-forge:revisar                 # Helena + Patrícia + outros
/kairos-forge:lancar                  # deploy com gates, health check e rollback anotado
/kairos-forge:mapear-conhecimento     # grafo de conhecimento: memória compartilhada da fábrica
/kairos-forge:auditar                 # semanal, 0–120 em 6 dimensões (inclui Autonomia medida)
/kairos-forge:evoluir                 # veredicto da evolução anterior + 1 capacidade nova/semana
```

Sob demanda:

```
/kairos-forge:avaliar <comportamento> # eval com gold set selado, rubrica e juiz cego, como gate de CI
/kairos-forge:otimizar <métrica>      # ciclo de catraca: 1 mudança por rodada, manter ou reverter
/kairos-forge:migrar <legado>         # modernização por estrangulamento, fatia por fatia (Ivan)
```

Documentação completa em [`plugin/README.md`](plugin/README.md).

## Para contribuidores

Os canônicos são `agents/` e `skills/` **na raiz** — não em `plugin/`, que é reescrito
pelo `release.py`. Quando alterar um deles, rode o sync na raiz antes de commitar:

```bash
python3 scripts/sync-multi-cli.py
git add agents/ skills/ .agents/ .codex/agents/ .opencode/ .cursor/ .claude-plugin/ativos.manifest.json
```

Para bumpar versão, **não edite os manifests à mão** — o script de release calcula as
contagens do filesystem, injeta versão e números em todos os manifests, banners e docs,
roda os dois syncs e espelha em `plugin/`:

```bash
python3 scripts/release.py bump X.Y.Z   # tudo de uma vez
python3 scripts/release.py check        # o que o CI roda em todo PR
```

O `check` verifica:
- versão e contagens;
- paridade raiz↔`plugin/`, JSON válido e mirrors;
- orçamento de contexto estático, o limite de 500 linhas por skill e o teto de `description` de skill e de agente;
- skills citadas nos banners e manifests;
- integridade dos gold sets e o alarme do conjunto selado (ADR-0043);
- scripts citados pelas skills presentes em `.cursor/scripts/`;
- contratos de integração assinados (ADR-0034).

Em todo PR o CI também roda:
- sync sem diff pendente;
- `check-agent-security.py`;
- `guardrail.py verificar`;
- `python3 -m unittest discover -s scripts/tests -t scripts`.

Mudou o prompt da Laura, uma `description` de agente ou o roteamento? Rode também o eval de roteamento (`evals/roteamento-laura/`). Detalhes e convenções em [`CLAUDE.md`](CLAUDE.md).

## Licença

MIT. Ver [LICENSE](LICENSE).

## Sobre

Mantido por [VilelaAI](https://vilela.tech). Faz parte da camada Build do KairOS, junto com [kairos-ai](https://github.com/VilelaAI/kairos-ai), kairos-runtime, kairos-domains, kairos-studio e kairos-platform.
