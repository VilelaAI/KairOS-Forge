# kairos-forge

> Fábrica de software autônoma como plugin do **Claude Code**, **Codex CLI**, **OpenCode** e **Cursor**.
> **71 agentes em 21 times** (40 core + 31 apoio). PT-BR oficial. MIT.

Plugin que transforma uma sessão genérica de qualquer CLI compatível em um time completo de desenvolvimento mais um time de apoio textual. Cada agente tem persona, comportamento, allow-list de ferramentas, e personalidade consistente em primeira pessoa. Eles colaboram via `/kairos-forge:rodar` (sequencial) em qualquer CLI ou trabalham em paralelo via Agent Teams nativos (`/kairos-forge:mobilizar`, exclusivo Claude Code).

## Posicionamento

`kairos-forge` é a **versão lite/MIT genérica** da fábrica do KairOS. Cobre o squad técnico + squads de apoio universais.

Para projetos em **domínios regulados brasileiros** (LGPD, Segurança-TI, NRs, OAB, MEC-LDB, ANVISA, BACEN), use o [kairos-ai](https://github.com/VilelaAI/kairos-ai) — que adiciona squads negociais, guardrails com referência legal, assertions binárias, Ralph Loop e Advisor regulatório.

## Os 40 agentes core

| Time | Agentes |
|---|---|
| **Liderança** | 👩‍💼 Laura (Tech Lead) · 🧭 Rafael (Staff) |
| **Produto** | 🎯 Camila (PM) · 🔬 Isabela (UX) |
| **Arquitetura** | 📐 Diego (Sistemas) · 🗄️ Fernanda (Dados) · 🔗 Thiago (Integrações) · 🧱 Ivan (Modernização) · 📨 Murilo (Eventos) |
| **Frontend** | ⚛️ Marina (Frontend) · 🎨 Pablo (UI) · ♿ Ada (Acessibilidade) |
| **Mobile** | 📱 Yasmin (Mobile) · 🏪 Théo (Distribuição) |
| **Backend** | ⚙️ Lucas (Backend) · 🤖 Gabriel (IA) · 📊 Juliana (ETL) |
| **Dados** | 🛢️ Carlos (DBA) · 🔎 André (Busca) · 🕸️ Olívia (Conhecimento) · 📈 Bento (Analytics) |
| **Ciência de Dados** | 🔬 Davi (Ciência de Dados) · 🧠 Milena (ML) · 🚢 Heitor (MLOps) |
| **Qualidade** | ✅ Patrícia (QA Lead) · 🧪 Ricardo (Testes) · ⚡ Vinícius (Performance) · 🎯 Alice (Evals de IA) |
| **Plataforma** | 🚀 Marcos (DevOps) · ☁️ Elisa (Cloud) · 🔐 Helena (Security) · 👁️ Renata (Observabilidade) · 🏗️ Igor (IaC) · ☸️ Kaique (Kubernetes) · 🔁 Gael (GitOps) · 🌐 Nina (Redes) · 🧯 Sérgio (SRE) · 🔮 Aline (AIOps) |
| **Documentação** | 📝 Beatriz (Docs) · 📖 Felipe (API Docs) |

## Os 31 agentes de apoio (10 squads)

Squads de apoio **nunca implementam código** — produzem artefatos textuais.

| Squad | Agentes | Quando |
|---|---|---|
| **Microcopy** ✍️ | Celina, Renato, Letícia, Ingrid | Texto de UI, mensagem de erro, empty state, i18n/l10n |
| **Narrativa** 📋 | Marcos [Specs], Helena [Apresentação], Dante | ADR, demo, decisão travada |
| **Naming** 🏷️ | Elisa [Naming], Bruno, Cora | Nomenclatura, taxonomia, voz |
| **Valor** ⚖️ | Hugo, Sofia, Rui | Priorização ICE, lançamento, audit ROI |
| **Observabilidade** 📡 | Lia, Otávio, Vera | Tracking plan, AARRR, A/B |
| **DX** 🛠️ | Enzo, Clara, Tomás | Developer journey, contributor ladder, DORA |
| **Revisão Arquitetural** 🔄 | Álvaro, Lúcia, Félix | Pre-mortem, red team, Inversão de Munger |
| **Requisitos** 🎤 | Joana, Caio, Norma | Elicitação, critérios de aceite, NFRs e consistência |
| **Gestão** 🗓️ | Iara, Breno, Talita | Plano por marcos, riscos/RAID, status de entrega |
| **Governança** 🗂️ | Vitor, Regina, Paula | Catálogo/linhagem, qualidade de dados, políticas de acesso |

> ⚠️ **Atenção a colisões de nome:** existem dois Marcos (DevOps/Specs), duas Helenas (Security/Apresentação) e duas Elisas (Cloud/Naming). Quando você disser apenas o primeiro nome, Laura desambigua antes de invocar.

Acionar:

```
/kairos-forge:rodar apoio-naming
/kairos-forge:rodar apoio-revisao-arquitetural
```

## As 18 skills

| Skill | Quando usar | Disponível em |
|---|---|---|
| `/kairos-forge:onboardar` | Primeira vez no projeto | Todos os CLIs |
| `/kairos-forge:mapear-arquitetura` | Brownfield: inventário, acoplamento e plano de decomposição | Todos os CLIs |
| `/kairos-forge:diagnosticar <sistema>` | Porta de entrada de sistema existente: mede, pontua 6 dimensões com rubrica publicada, prioriza por impacto × esforço e entrega roadmap por horizonte | Todos os CLIs |
| `/kairos-forge:especificar <ideia>` | Antes de codar não-trivial; gera SPEC rastreável | Todos os CLIs |
| `/kairos-forge:analisar-ameacas <feature>` | Threat model antes de implementar feature sensível (auth, PII, billing, IA) | Todos os CLIs |
| `/kairos-forge:desenhar <spec>` | Handoff de design: fluxos, cinco estados por view, acessibilidade; modo `verificar` inspeciona o implementado | Todos os CLIs |
| `/kairos-forge:validar <spec>` | Depois de implementar; valida aceite contra SPEC e gates, corroborando a evidência contra a trajetória registrada | Todos os CLIs |
| `/kairos-forge:rodar [agente\|time\|apoio-X]` | Conversacional/sequencial — modo padrão | Todos os CLIs |
| `/kairos-forge:mobilizar <spec>` | Paralelo via Agent Teams | **Apenas Claude Code** |
| `/kairos-forge:entregar <feature>` | **O ciclo inteiro sozinho**: especificar → aprovar → construir → validar ⇄ corrigir → revisar ⇄ corrigir → PR, com orçamento de rodadas declarado | Todos os CLIs |
| `/kairos-forge:revisar` | Pré-PR. Helena + Patrícia + outros, com faixa de raio de explosão decidindo o rigor | Todos os CLIs |
| `/kairos-forge:avaliar <comportamento>` | Eval de comportamento não-determinístico (LLM, agente, extração): gold set versionado, rubrica em 5 eixos, limiar de regressão, gate no CI | Todos os CLIs |
| `/kairos-forge:mapear-conhecimento` | Grafo de conhecimento do projeto: construir, atualizar, consultar (multi-hop com citação de arestas) e diagnosticar | Todos os CLIs |
| `/kairos-forge:otimizar <métrica>` | Ciclo de catraca: 1 mudança por rodada, medir, manter ou reverter via git, com sentinelas e orçamento | Todos os CLIs |
| `/kairos-forge:migrar` | Modernização por estrangulamento com Ivan: fatias, testes de caracterização, rota de corte e manter-ou-reverter | Todos os CLIs |
| `/kairos-forge:lancar` | Do merge à produção: checklist pré-deploy, aprovação explícita, health check em 3 camadas, rollback anotado | Todos os CLIs |
| `/kairos-forge:auditar` | Semanal. Pontuação 0–120 em 6 dimensões (Fundação, Pipeline, Guardrails, Conhecimento, Estrutura, **Autonomia**) | Todos os CLIs |
| `/kairos-forge:evoluir` | Semanal pós-auditoria | Todos os CLIs |

Ordem natural: `onboardar` → `mapear-arquitetura` (brownfield) → `diagnosticar` (sistema existente) → `especificar` → `analisar-ameacas` (features sensíveis) → `desenhar` (features com UI) → `mobilizar`/`rodar` → `validar` → `revisar` → `lancar` → `mapear-conhecimento` (quando docs acumulam) → `auditar` → `evoluir`.

**Ou pule o encadeamento:** `/kairos-forge:entregar` percorre o trecho central sozinho — especificar → construir → validar ⇄ corrigir → revisar ⇄ corrigir → PR — roteando cada falha de volta ao agente responsável dentro de um orçamento declarado (ADR-0023). Sob demanda, fora do fluxo: `otimizar` (métrica mensurável a melhorar), `migrar` (legado) e `avaliar` (comportamento de IA).

**Modo guiado (trilhas por tema, ADR-0013):** quem não sabe por onde começar diz só o tema — "quero login", "preciso de checkout" — e a fábrica reconhece a trilha (`templates/trilhas/`: auth, pagamentos, painel-admin, api, seed-dados) e conduz: requisitos típicos prontos, perguntas certas, riscos pro threat model e plano de partida. No `/mobilizar`, o encerramento traz **ledger da execução** (tier de modelo, tasks e rodadas por teammate) e os checkpoints renderizam um **quadro vivo** — "Pronto" só com gate rodado.

### Grafo de conhecimento (Graph Engineering)

A partir da v0.8.0, a fábrica mantém um **grafo de conhecimento por projeto** em `.agents/grafo/` (ADR-0009): entidades e relações com proveniência, extraídas de SPECs, ADRs, decisões e memórias — arquivos JSONL versionados no git, sem banco nem dependência externa. Ele resolve o problema estrutural de qualquer sistema multi-agente: **a memória de cada agente morre com a janela de contexto; o grafo não.**

- `/mobilizar` usa o grafo como **memória compartilhada**: teammates recebem subgrafos em vez de contexto inteiro e devolvem fatos novos.
- `/validar` usa o grafo como **base de fatos**: afirmações checadas contra arestas ("a tripla X não existe; o que existe é Y, da fonte Z"); fato ausente escala pro humano.
- Perguntas **multi-hop** ("o que depende do componente que essa SPEC muda?") ganham resposta fundamentada, aresta por aresta.

🕸️ Olívia (Engenheira de Conhecimento, time Dados) é a dona; `scripts/grafo.py` (stdlib-only) cuida da parte determinística (validar contrato, diagnosticar, serializar subgrafo, amostrar).

### Memória persistente em camadas

O grafo é a camada **estrutural** de um modelo de três camadas (ADR-0010): a camada **episódica** (sessões, handoffs entre CLIs) vem do companion externo opcional [ai-memory](https://github.com/akitaonrails/ai-memory) — detectado pelas tools MCP `memory_*`, nunca embarcado, com degradação graciosa na ausência; a camada **curada** são os arquivos do repo (`decisoes/`, `.agents/memory/`, `contextos/`). Com o ai-memory ativo, Laura abre `/rodar` e `/mobilizar` com o handoff "onde paramos", `/evoluir` usa a semana capturada como evidência, e dá pra sair do Claude Code no meio de uma SPEC e continuar no Codex. Guia completo: [`docs/memoria-persistente.md`](docs/memoria-persistente.md).

## O harness: autonomia medida, contida e disparável

A partir da v0.17, a fábrica instrumenta e contém a si mesma. A referência é o
whitepaper [*The New SDLC With Vibe Coding*](https://addyosmani.com/blog/agentic-engineering/)
(Google, 2026), que define o harness como o que cerca o modelo — instruções,
tools, sandbox, orquestração, **guardrails** e **observabilidade** — e resume:
*"most agent failures, examined honestly, are configuration failures."*

Três peças, nesta ordem, porque cada uma torna a seguinte segura:

### 1. Telemetria — a autonomia vira número (ADR-0021)

Os hooks gravam a **trajetória** em `.agents/execucoes/*.jsonl`, por código, não
pelo modelo. O evento-chave é o prompt: **cada prompt humano depois do primeiro é
uma intervenção**; um ciclo com zero intervenções rodou sozinho.

```bash
python3 scripts/telemetria.py resumo --dias 30
#  Autonomia:            72.0%  (18/25 ciclos sem intervenção)
#  Gates verdes de 1ª:   81.0%
#  Rodadas de correção:  9
```

Isso alimenta a 6ª dimensão do `/auditar` e responde a única pergunta que define
o nível de autonomia da fábrica. Sem instrumento, qualquer afirmação sobre o
nível é opinião — inclusive a otimista, que é como se produz um pipeline sem
supervisão achando que se produziu autonomia.

O `/validar` usa a mesma trajetória para **corroborar**: a célula `verificado:` da
SPEC é escrita pelo agente que fez o trabalho, então passa a ser alegação a
conferir, não fato a aceitar. Alegação sem lastro bloqueia P1 igual a "sem
evidência".

### 2. Guardrails determinísticos — o que não pode falhar sai da prosa (ADR-0022)

`scripts/guardrail.py` roda em `PreToolUse`/`PostToolUse` e **bloqueia**:

- **comando destrutivo** — `rm -rf /`, force-push em branch protegida, `DROP`/`TRUNCATE`, `DELETE` sem `WHERE`, `curl | sh`, exfiltração de `.env`;
- **caminho protegido** — segredos, chaves, configuração de CI;
- **SPEC inconsistente** — status "Concluído" sem célula `verificado:`, recusado no momento da escrita.

Dois caminhos são **inegociáveis**: `.agents/execucoes/` e
`.agents/guardrails.json`. O agente não escreve o próprio medidor nem a própria
regra — corroboração que ele reescreve não corrobora, e guardrail que ele afrouxa
não guarda. É o mesmo princípio que o `/otimizar` já aplicava ao comando da
métrica, agora no harness.

Nos CLIs sem `PreToolUse`, o mesmo contrato roda como CLI:
`guardrail.py verificar .` — checa depois em vez de antes, e vale no CI.

### 3. Gatilhos por evento — a fábrica acorda sozinha (ADR-0026)

`templates/ci/` traz workflows prontos para **o seu projeto**: revisar no PR,
corrigir em CI vermelho (abre PR, **nunca** escreve na base) e auditar por cron.

```bash
cp <plugin>/templates/ci/kairos-forge-*.yml .github/workflows/
```

> **Instale nesta ordem.** Gatilho por evento sem telemetria e sem guardrail não
> é autonomia — é pipeline sem supervisão. O `/auditar` recomenda as lacunas
> nessa ordem de propósito.

### 4. Quadro vivo — onde tudo está, numa tela (ADR-0013/0032)

As três peças acima produzem estado em quatro lugares. `scripts/painel.py` junta:

```bash
python3 scripts/painel.py                      # tudo
python3 scripts/painel.py SPEC-001             # uma SPEC
python3 scripts/painel.py --html quadro.html   # página autocontida, abre sem rede
python3 scripts/painel.py --json               # pra outra ferramenta consumir
```

Requisitos por coluna, progresso da SPEC, estado do arco com as fichas de
orçamento, veredicto dos dois gates com a cobertura declarada, e a trajetória.

Duas regras que definem o script. **É renderização, nunca estado** — não escreve
nada além do arquivo que você pediu, porque quadro persistido vira a planilha
paralela que o ADR-0013 recusou; se o número está errado, o bug está na fonte. E
**"Concluído" sem `verificado:` não conta como pronto** — cai para "Em progresso"
e vira aviso. Um quadro que somasse a palavra mostraria progresso que a própria
`/validar` recusaria.

### O que a autonomia **não** inclui

Cinco gates humanos atravessam tudo isso intactos e estão em tabela no topo da
skill `entregar`: aprovação da SPEC, Pare e Pergunte (conteúdo inventável),
deploy de produção, mudança irreversível e merge do PR.

O que sai do caminho do humano é a digitação do próximo comando e a leitura de
cada diff. O julgamento fica. É a diferença entre "o time confia no harness" e
"ninguém revisa nada".

## Compatibilidade entre plataformas

| Componente | Claude Code | Codex CLI | OpenCode | Cursor |
|---|---|---|---|---|
| Manifest | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` | n/a (lê como skills repo-locais) | n/a |
| Marketplace catalog | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` | n/a | n/a |
| Comando de instalação | `/plugin marketplace add` (TUI) | `codex plugin marketplace add` + escolher na TUI | `cp -R skills/ .opencode/skills/` | `cp -R plugin/.cursor <projeto>/.cursor` (ou `~/.cursor/`) |
| Skills | `skills/<nome>/SKILL.md` | mesma pasta `skills/` (compartilhada) | `.opencode/skills/` ou `.claude/skills/` | `.cursor/skills/` (mirror gerado, padrão Agent Skills) |
| Subagents | `agents/<id>.md` | `.agents/<id>/AGENT.md` | via copy de `agents/` | `.cursor/agents/<id>.md` (gerado, frontmatter adaptado) |
| SessionStart hook | `hooks/hooks.json` | `.codex/hooks.json` | via `oh-my-opencode` | rule `alwaysApply` (`.cursor/rules/kairos-forge.mdc`) |
| PostToolUse hook | ✅ | ❌ Codex só matcher Bash | via `oh-my-opencode` | ❌ |
| Telemetria de execução (ADR-0021) | ✅ completa (4 pontos do ciclo) | ⚠️ só SessionStart — sem trajetória útil | ❌ | ❌ |
| Guardrails que bloqueiam (ADR-0022) | ✅ `PreToolUse` | ⚠️ via `guardrail.py verificar` no CI | ⚠️ idem | ⚠️ idem |
| Agent Teams (`/mobilizar`) | ✅ nativo | ❌ sem `TeamCreate` | ❌ sem equivalente | ❌ (subagents paralelos existem, mas sem protocolo de Teams) |
| Instruções de projeto | `CLAUDE.md` | `AGENTS.md` | `CLAUDE.md` (fallback) ou `AGENTS.md` | `AGENTS.md` |

> **Nota sobre skills compartilhadas:** Tanto Claude Code quanto Codex descobrem skills em `skills/<nome>/SKILL.md` quando empacotados como plugin. Não há duplicação — a mesma pasta serve aos dois CLIs. Apenas os manifests (`.claude-plugin/` vs `.codex-plugin/`) e os subagents é que diferem.

> **Nota sobre `mobilizar`:** Esta skill é exclusiva do Claude Code. Em Codex/OpenCode/Cursor ela detecta o ambiente e orienta o usuário a usar `/kairos-forge:rodar` como alternativa.

> **Nota sobre telemetria fora do Claude Code:** sem hooks completos, `.agents/execucoes/` fica vazio, a dimensão **Autonomia** do `/auditar` pontua 0 e o `/validar` pula a corroboração de trajetória. Isso é honesto, não bug: sem hook não há trajetória. O caminho nesses CLIs é `templates/ci/` — os mesmos checks rodando no pipeline do projeto.

> **Nota sobre `.agents/` e `.cursor/`:** Os dois diretórios são **gerados** a partir de `agents/` + `skills/` pelo script `scripts/sync-multi-cli.py`. Não edite arquivos lá — alterações são perdidas no próximo sync. Sempre edite o canônico e rode o sync.

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

### Cursor

O Cursor não tem marketplace de plugins — a instalação é uma cópia única da distribuição gerada `.cursor/` (requer Cursor 2.4+ para subagents; skills a partir do 2.1):

```bash
git clone https://github.com/VilelaAI/kairos-forge.git

# Por projeto:
cp -R kairos-forge/plugin/.cursor /caminho/do/projeto/.cursor

# Ou global (todos os projetos):
cp -R kairos-forge/plugin/.cursor/* ~/.cursor/
```

### Hermes Agent (bot 24/7 — ponte)

Com o [Hermes Agent](https://hermes-agent.nousresearch.com) rodando num VPS, a ponte em [`hermes/`](hermes/README.md) instala as skills que roteiam engenharia estruturada pra fábrica: você manda "construir com a fábrica: …" no Telegram, o Hermes opera o ciclo e a fábrica especifica, constrói, valida e revisa dentro do Claude Code (ADR-0019).

```bash
bash hermes/install.sh
```

O que chega: 71 subagents em `.cursor/agents/` (agentes consultivos viram `readonly` — o Cursor não tem allow-list por ferramenta), 18 skills no menu `/` (`.cursor/skills/`, padrão Agent Skills), a rule `alwaysApply` com o banner da fábrica e a resolução de `${CLAUDE_PLUGIN_ROOT}`, mais os scripts de suporte (`grafo.py`, `telemetria.py`, `guardrail.py`, `execucao.py`) e `templates/`. Instruções de projeto: o Cursor lê `AGENTS.md` — o `/kairos-forge:onboardar` oferece gerá-lo junto do `CLAUDE.md`.

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

Depois, o caminho curto — a fábrica percorre o ciclo e volta com o PR:

```
/kairos-forge:entregar exportar relatorios em CSV no dashboard
   └─ Laura declara o orçamento, especifica, PARA para você aprovar a SPEC,
      constrói, valida, corrige o que bloqueou, revisa, corrige o que era 🔴,
      abre o PR — e encerra honesto se o orçamento acabar antes
```

Ou etapa por etapa, quando você quer ver cada passo (qualquer CLI):

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

/kairos-forge:validar SPEC-001
   └─ Ricardo + Patrícia validam requisitos, critérios de aceite e gates

/kairos-forge:rodar apoio-revisao-arquitetural
   └─ Álvaro faz pre-mortem da SPEC antes do merge

/kairos-forge:revisar
   └─ Helena + Patrícia + outros leem o diff

/kairos-forge:mapear-conhecimento atualizar
   └─ Olívia registra as entidades e decisões deste ciclo no grafo (.agents/grafo/)

/kairos-forge:avaliar o resumo automatico de tickets
   └─ Alice monta gold set, rubrica nos 5 eixos e instala o gate no CI

/kairos-forge:auditar
   └─ 6 dimensões, incluindo Autonomia medida da telemetria — com o nível (L2/L3/L4)
```

## Para contribuidores

Quando alterar arquivos em `agents/` ou `skills/`, **sempre rode o sync** antes de commitar:

```bash
python3 scripts/sync-multi-cli.py
git add agents/ skills/ .agents/ .cursor/
git commit -m "feat(<modulo>): <descrição>"
```

Sem o sync, usuários de Codex CLI e Cursor ficam desatualizados.

## Convenções

- **PT-BR oficial.** Skills, agentes, comandos, comentários, mensagens de commit.
- **Verbos no infinitivo.** `especificar`, não `spec`.
- **Persona explícita.** Agentes se apresentam: "Oi, Marina aqui — Frontend."
- **Apoio nunca codifica.** Squads de apoio entregam texto.
- **`.agents/` é gerado, não editado.** Edite `agents/` e rode o sync.

## Roadmap

- **v0.5** — SPEC rastreável, `/validar`, gates por tarefa, estado operacional
- **v0.6** — `/mapear-arquitetura`, `/analisar-ameacas`, dimensão Estrutura em `/auditar` (5 dimensões)
- **v0.7** — 6 especialistas de plataforma/ops (Igor, Kaique, Gael, Nina, Sérgio, Aline)
- **v0.8** — Graph Engineering: `/mapear-conhecimento`, Olívia, grafo em `.agents/grafo/`, fundamentação no `/validar` e memória compartilhada no `/mobilizar`; memória em camadas com ai-memory opcional (ADR-0010)
- **v0.9** — suporte ao Cursor: `.cursor/` gerado com subagents, skills (Agent Skills), rule e suporte (ADR-0011)
- **v0.10** — ciclo de catraca (`/otimizar`, ADR-0012); ledger, quadro vivo e trilhas por tema (ADR-0013)
- **v0.11** — squads de apoio Requisitos e Gestão (ADR-0014); Pare e Pergunte (ADR-0015)
- **v0.12** — time core Ciência de Dados (Davi, Milena, Heitor) e squad Governança (Vitor, Regina, Paula) (ADR-0016)
- **v0.13** — sete perfis especializados: time Mobile (Yasmin, Théo), Ivan (Modernização), Alice (Evals de IA), Bento (Analytics), Murilo (Eventos) e Ingrid (Localização) (ADR-0017); infra de release: `scripts/release.py`, CI e eval de roteamento da Laura
- **v0.14** — `/migrar` (estrangulamento com Ivan), modo RFC no `/especificar`, diagramas Mermaid via `grafo.py mermaid` em SPEC/RFC/ADR, modo debate no `/rodar` (ADR-0018)
- **v0.15** — ponte Hermes: a fábrica como motor de engenharia do Hermes Agent, operável 24/7 pelo Telegram (ADR-0019)
- **v0.16** — skills `desenhar` e `lancar`: o ciclo de produto do oh-my-hermes nas partes compatíveis com plugin (ADR-0020)
- **v0.17** — observabilidade do harness: registro determinístico por hook, `telemetria.py`, corroboração de trajetória no `/validar` e 6ª dimensão **Autonomia** no `/auditar` (ADR-0021)
- **v0.18** — o arco fechado: guardrails que bloqueiam (ADR-0022), skill `entregar` (ADR-0023) e contenção de raio com worktree e reversibilidade declarada (ADR-0024)
- **v0.19** — provar e disparar: skill `avaliar` com rubrica como gate (ADR-0025), gatilhos por evento em `templates/ci/` (ADR-0026) e orçamento de contexto estático (ADR-0027)
- **v0.20** — skill `diagnosticar`: a porta de entrada de sistema existente, com escada de evidência declarada e `diagnostico.py` como camada medida (ADR-0028)
- **v0.21** — máquina de estados do arco: `ciclo.py` decide transição, orçamento e escalação por código; `corrigindo_revisao` só sai para `validando` e o veredicto vem do relatório em disco (ADR-0029)
- **v0.22** — artefato ajustado ao resultado (conjunto selado + digest no `/avaliar`), ergonomia de guardrail (recusa na trajetória, modo `aviso`) e detecção de patinação em voo (ADR-0030)
- **v0.23** — higiene do juiz no `/avaliar`, gold set de comportamento da fábrica, faixa de raio de explosão no `/revisar`+`/entregar` e taxa de reversão no `diagnostico.py` (ADR-0031)
- **v0.24** — contratos de fronteira nos relatórios (`contrato.py`), progresso real devolve a ficha do orçamento no `ciclo.py`, e a revisão passa a ser lida do disco (ADR-0032)
- **v0.25** (atual) — quadro vivo: `painel.py` renderiza SPEC + arco + veredictos + trajetória numa tela (terminal, HTML autocontido ou JSON), com "Concluído" sem `verificado:` não contando como pronto (ADR-0013/0032)
- **v0.24** (planejado) — perfis Tier 3 sob demanda via `/evoluir` (SEO técnico, UX research, desktop, base de suporte), mais trilhas por tema

## Documentação

- [Início rápido](docs/inicio-rapido.md)
- [ADR-0001](docs/adr/0001-plugin-em-vez-de-runtime.md) — plugin não runtime
- [ADR-0002](docs/adr/0002-relacao-com-kairos-ai.md) — Forge vs kairos-ai
- [ADR-0003](docs/adr/0003-portagem-squads-apoio.md) — squads de apoio
- [ADR-0004](docs/adr/0004-multi-cli.md) — compatibilidade Claude Code/Codex/OpenCode
- [ADR-0005](docs/adr/0005-spec-rastreavel-validacao.md) — SPEC rastreável e `/validar`
- [ADR-0006](docs/adr/0006-arquitetura-modular-e-threat-model.md) — `/mapear-arquitetura`, `/analisar-ameacas` e dimensão Estrutura
- [ADR-0007](docs/adr/0007-especialistas-infra.md) — especialistas de infra no squad Plataforma (Igor, Kaique, Gael, Nina)
- [ADR-0008](docs/adr/0008-especialistas-aiops.md) — SRE/Incident Commander (Sérgio) e Engenheiro AIOps (Aline)
- [ADR-0009](docs/adr/0009-graph-engineering.md) — Graph Engineering: grafo de conhecimento como memória compartilhada da fábrica
- [ADR-0010](docs/adr/0010-memoria-persistente-em-camadas.md) — memória persistente em camadas e integração opcional com ai-memory
- [ADR-0011](docs/adr/0011-suporte-cursor.md) — suporte ao Cursor (subagents + Agent Skills + rules)
- [ADR-0012](docs/adr/0012-ciclo-de-catraca.md) — ciclo de catraca: `/otimizar`, orçamento de complexidade, reflexão e rastreabilidade
- [ADR-0013](docs/adr/0013-ledger-quadro-trilhas.md) — ledger de consumo, quadro vivo e trilhas por tema (inspirações KodeOne)
- [ADR-0014](docs/adr/0014-squads-requisitos-e-gestao.md) — squads de apoio Requisitos e Gestão de Projetos & Entregas
- [ADR-0015](docs/adr/0015-pare-e-pergunte.md) — Pare e Pergunte: condições de parada contra invenção de conteúdo
- [ADR-0016](docs/adr/0016-ciencia-de-dados-e-governanca.md) — time core Ciência de Dados e squad de apoio Governança
- [ADR-0017](docs/adr/0017-mobile-evals-modernizacao.md) — sete perfis: Mobile, Modernização, Evals de IA, Analytics, Eventos e Localização
- [ADR-0018](docs/adr/0018-migrar-rfc-mermaid-debate.md) — skill `migrar`, modo RFC, diagramas Mermaid e modo debate
- [ADR-0019](docs/adr/0019-ponte-hermes.md) — ponte Hermes: a fábrica como motor de engenharia de um agente 24/7
- [ADR-0020](docs/adr/0020-desenhar-e-lancar.md) — skills `desenhar` e `lancar`: o ciclo de produto nas partes compatíveis com plugin
- [ADR-0021](docs/adr/0021-observabilidade-do-harness.md) — observabilidade do harness: registro de execução, telemetria e dimensão Autonomia
- [ADR-0022](docs/adr/0022-guardrails-deterministicos.md) — guardrails determinísticos: hooks que bloqueiam, com fallback por script
- [ADR-0023](docs/adr/0023-skill-entregar-arco-fechado.md) — skill `entregar`: o arco fechado dentro do plugin
- [ADR-0024](docs/adr/0024-contencao-de-raio.md) — contenção de raio: worktree por teammate e reversibilidade declarada
- [ADR-0025](docs/adr/0025-skill-avaliar.md) — skill `avaliar`: eval com rubrica como gate, no projeto e no próprio plugin
- [ADR-0026](docs/adr/0026-gatilhos-por-evento.md) — gatilhos por evento: a fábrica acorda sem ninguém digitar
- [ADR-0027](docs/adr/0027-fronteira-estatico-dinamico.md) — fronteira estático/dinâmico e orçamento de contexto
- [ADR-0028](docs/adr/0028-skill-diagnosticar.md) — skill `diagnosticar`: a porta de entrada de sistema existente
- [ADR-0029](docs/adr/0029-maquina-de-estados-do-arco.md) — máquina de estados do arco: a transição decidida por código
- [ADR-0030](docs/adr/0030-artefato-ergonomia-e-deteccao.md) — artefato ajustado ao resultado, ergonomia de guardrail e detecção em voo
- [ADR-0031](docs/adr/0031-higiene-de-juiz-e-faixa-de-raio.md) — higiene do juiz e faixa de raio de explosão: o gate pergunta quanto custa desfazer
- [ADR-0032](docs/adr/0032-relacao-lioncode-e-contratos-de-fronteira.md) — relação com o LionCode e contratos de fronteira: progresso devolve ficha, limpo exige cobertura
- [Memória persistente](docs/memoria-persistente.md) — guia das 3 camadas e instalação opcional do ai-memory
- [Análise: o novo SDLC e o caminho até L4](docs/revisoes/2026-08-01-analise-whitepaper-novo-sdlc-e-caminho-l4.md) — o harness da fábrica medido contra o whitepaper Day-1 do Google, com as lacunas e o que cada uma virou

## Licença

MIT. Ver [LICENSE](LICENSE).

## Sobre

Mantido por [VilelaAI](https://vilela.tech). Faz parte da camada Build do KairOS, junto com [kairos-ai](https://github.com/VilelaAI/kairos-ai), kairos-runtime, kairos-domains, kairos-studio e kairos-platform.
