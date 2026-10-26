# kairos-forge

> Fábrica de software autônoma como plugin do **Claude Code**, **Codex CLI**, **OpenCode** e **Cursor**.
> **71 agentes em 21 times** (40 core + 31 apoio). PT-BR oficial. MIT.

Plugin que transforma uma sessão genérica de qualquer CLI compatível em um time completo de desenvolvimento mais um time de apoio textual. Cada agente tem persona, comportamento, allow-list de ferramentas, e personalidade consistente em primeira pessoa. Eles colaboram via `/kairos-forge:rodar` (sequencial) ou trabalham em paralelo via `/kairos-forge:mobilizar` — os dois em qualquer dos quatro CLIs: no paralelo, o quadro de tarefas é o mesmo arquivo do repositório e só muda o mecanismo de lançamento (Agent Teams no Claude Code, `spawn_agent` no Codex, `task` no OpenCode, subagents orquestrados no Cursor).

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
| **Valor** ⚖️ | Hugo, Sofia, Rui | Priorização RICE/WSJF (ICE na triagem), lançamento, audit ROI |
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
| `/kairos-forge:desenhar <spec>` | Handoff de design: fluxos, cinco estados por view, acessibilidade; modo `verificar` inspeciona o implementado e confere contra o `DESIGN.md` da raiz (ADR-0040) | Todos os CLIs |
| `/kairos-forge:validar <spec>` | Depois de implementar; valida aceite contra SPEC com gates do barato ao caro (para no primeiro vermelho), prova negativa dos testes (`prova.py`), chamadores fora do diff (`grafo.py contexto`) e evidência corroborada pela trajetória | Todos os CLIs |
| `/kairos-forge:rodar [agente\|time\|apoio-X]` | Conversacional/sequencial — modo padrão; modos `debate <decisão>` (ADR-0018) e `explorar <missão>` (POC descartável em worktree, nunca PR — ADR-0040) | Todos os CLIs |
| `/kairos-forge:mobilizar <spec>` | Time paralelo sobre o quadro `quadro.py`: dependências, teto de 6 por onda, `varrer` (tempo limite) e `compensar` (desfaz em ordem inversa) | Todos os CLIs (adaptador por CLI) |
| `/kairos-forge:entregar <feature>` | **O ciclo inteiro sozinho**: especificar → criticar → aprovar → construir → validar ⇄ corrigir → revisar ⇄ corrigir → PR, com orçamento de rodadas declarado | Todos os CLIs |
| `/kairos-forge:revisar` | Pré-PR. Helena + Patrícia + outros, com faixa de raio de explosão decidindo o rigor; segunda passada sobre os próprios achados e ruído medido (`descartado:` + `telemetria.py ruido`) | Todos os CLIs |
| `/kairos-forge:avaliar <comportamento>` | Eval de comportamento não-determinístico (LLM, agente, extração): gold set versionado, rubrica em 5 eixos, limiar de regressão, gate no CI; conjunto selado conferido por `prova.py selado` e juiz cego à versão | Todos os CLIs |
| `/kairos-forge:mapear-conhecimento` | Grafo de conhecimento do projeto: construir, atualizar, consultar (multi-hop com citação de arestas) e diagnosticar | Todos os CLIs |
| `/kairos-forge:otimizar <métrica>` | Ciclo de catraca: 1 mudança por rodada, medir, manter ou reverter via git, com sentinelas e orçamento | Todos os CLIs |
| `/kairos-forge:migrar` | Modernização por estrangulamento com Ivan: escada de prontidão em cinco degraus, testes de caracterização, corte em sombra antes do percentual e manter-ou-reverter | Todos os CLIs |
| `/kairos-forge:lancar` | Do merge à produção: checklist pré-deploy, aprovação explícita, health check em 3 camadas, rollback anotado | Todos os CLIs |
| `/kairos-forge:auditar` | Semanal. Pontuação 0–120 em 6 dimensões (Fundação, Pipeline, Guardrails, Conhecimento, Estrutura, **Autonomia**) | Todos os CLIs |
| `/kairos-forge:evoluir` | Semanal pós-auditoria: lê a trajetória (`telemetria.py resumo`), dá veredicto à evolução anterior e escolhe UMA capacidade nova | Todos os CLIs |

Ordem natural: `onboardar` → `mapear-arquitetura` (brownfield) → `diagnosticar` (sistema existente) → `especificar` → `analisar-ameacas` (features sensíveis) → `desenhar` (features com UI) → `mobilizar`/`rodar` → `validar` → `revisar` → `lancar` → `mapear-conhecimento` (quando docs acumulam) → `auditar` → `evoluir`.

**Ou pule o encadeamento:** `/kairos-forge:entregar` percorre o trecho central sozinho — especificar (com crítica adversarial antes da sua aprovação) → construir → validar ⇄ corrigir → revisar ⇄ corrigir → PR — roteando cada falha de volta ao agente responsável dentro de um orçamento declarado (ADR-0023). Sob demanda, fora do fluxo: `otimizar` (métrica mensurável a melhorar), `migrar` (legado) e `avaliar` (comportamento de IA).

**Modo guiado (trilhas por tema, ADR-0013):** quem não sabe por onde começar diz só o tema — "quero login", "preciso de checkout" — e a fábrica reconhece a trilha (`templates/trilhas/`: auth, pagamentos, painel-admin, api, seed-dados, pipeline-dados) e conduz: requisitos típicos prontos, perguntas certas, riscos pro threat model e plano de partida. No `/mobilizar`, o encerramento traz **ledger da execução** (tier de modelo, tasks e rodadas por teammate) e os checkpoints renderizam um **quadro vivo** — "Pronto" só com gate rodado.

### Grafo de conhecimento (Graph Engineering)

A partir da v0.8.0, a fábrica mantém um **grafo de conhecimento por projeto** em `.agents/grafo/` (ADR-0009): entidades e relações com proveniência, extraídas de SPECs, ADRs, decisões e memórias — arquivos JSONL versionados no git, sem banco nem dependência externa. Ele resolve o problema estrutural de qualquer sistema multi-agente: **a memória de cada agente morre com a janela de contexto; o grafo não.**

- `/mobilizar` usa o grafo como **memória compartilhada**: teammates recebem subgrafos em vez de contexto inteiro e devolvem fatos novos.
- `/validar` usa o grafo como **base de fatos**: afirmações checadas contra arestas ("a tripla X não existe; o que existe é Y, da fonte Z"); fato ausente escala pro humano.
- Perguntas **multi-hop** ("o que depende do componente que essa SPEC muda?") ganham resposta fundamentada, aresta por aresta.
- A **camada de código** (ADR-0041) mora ao lado, em `codigo.jsonl`: arestas `importa`/`herda`/`instancia` extraídas por AST, sem modelo e regeneráveis. `/validar` lista os chamadores fora do diff; `/revisar` sobe a faixa de raio quando o arquivo tem 5+ importadores.

🕸️ Olívia (Engenheira de Conhecimento, time Dados) é a dona; `scripts/grafo.py` (stdlib-only) cuida da parte determinística: validar contrato, diagnosticar, serializar subgrafo, amostrar, diagrama `mermaid` (ADR-0018), `codigo` (grava a camada de código) e `contexto <arquivo>` (quem importa o arquivo, o que ele importa e as entidades que o citam).

### Memória persistente em camadas

O grafo é a camada **estrutural** de um modelo de três camadas (ADR-0010): a camada **episódica** (sessões, handoffs entre CLIs) vem do companion externo opcional [ai-memory](https://github.com/akitaonrails/ai-memory) — detectado pelas tools MCP `memory_*`, nunca embarcado, com degradação graciosa na ausência; a camada **curada** são os arquivos do repo (`decisoes/`, `.agents/memory/`, `contextos/`) — e lição só sobe para `.agents/memory/` com contraste: no `/evoluir`, só um veredicto `ajudou` ou `piorou` com contraste concreto (linha de base → agora) vira lição; adoção não é evidência (ADR-0043). Com o ai-memory ativo, Laura abre `/rodar` e `/mobilizar` com o handoff "onde paramos", `/evoluir` usa a semana capturada como evidência, e dá pra sair do Claude Code no meio de uma SPEC e continuar no Codex. Guia completo: [`docs/memoria-persistente.md`](docs/memoria-persistente.md).

## O harness: autonomia medida, contida e disparável

A partir da v0.17, a fábrica instrumenta e contém a si mesma. A referência é o
whitepaper [*The New SDLC With Vibe Coding*](https://addyosmani.com/blog/agentic-engineering/)
(Google, 2026), que define o harness como o que cerca o modelo — instruções,
tools, sandbox, orquestração, **guardrails** e **observabilidade** — e resume:
*"most agent failures, examined honestly, are configuration failures."*

Três peças se instalam nesta ordem, porque cada uma torna a seguinte segura
(1–3); as quatro seguintes decidem, provam e mostram o que as três produzem (4–7).

### 1. Telemetria — a autonomia vira número (ADR-0021)

Os hooks — no Claude Code e, desde a v0.35, no Cursor — gravam a **trajetória** em
`.agents/execucoes/*.jsonl`, por código, não pelo modelo. O evento-chave é o prompt:
**cada prompt humano depois do primeiro é uma intervenção**; um ciclo com zero
intervenções rodou sozinho.

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

**Autonomia de PR, pelo git (ADR-0044).** A trajetória só existe onde há hook. O
histórico do git existe em todo CLI:

```bash
python3 scripts/telemetria.py prs --dias 30
#  Mesclados: 12 · com código da fábrica: 9 · sem nenhum commit humano: 6
#  Autonomia de PR: 66.7%  (6/9)
```

Commit de agente é o que traz o trailer `Fabrica: kairos-forge` (que o teammate, o
anti-drift, o `/otimizar` e o `corrigir.yml` escrevem), o `Co-Authored-By: Claude` ou o autor
`kairos-forge`; o projeto acrescenta as suas com `--marca`. Usa o `gh` quando está
autenticado e, sem ele, os merges do git. O `/auditar` reporta ao lado da dimensão
Autonomia, sem pontuar: quando os dois números divergem, a divergência é o achado.

O `/validar` usa a mesma trajetória para **corroborar**: a célula `verificado:` da
SPEC é escrita pelo agente que fez o trabalho, então passa a ser alegação a
conferir, não fato a aceitar. Alegação sem lastro bloqueia P1 igual a "sem
evidência".

**Patinação em voo (ADR-0030).** Medir depois não impede queimar orçamento agora:
`execucao.py alerta`, no `PostToolUse`, avisa o modelo quando um padrão de agente
preso fecha — o mesmo comando falhando 3 vezes seguidas, dois comandos revezando sem
nenhum passar, 8 escritas de produção sem nenhum gate no meio. Avisa, nunca bloqueia,
e só no turno em que o padrão fecha; repetição sem falha não conta — rodar o mesmo
teste três vezes enquanto conserta é trabalho normal.

### 2. Guardrails determinísticos — o que não pode falhar sai da prosa (ADR-0022/0042)

`scripts/guardrail.py` roda nos hooks (`PreToolUse`, `PostToolUse` e `Stop` no Claude
Code; os eventos equivalentes no Cursor) e **bloqueia** por código. Oito classes:

- **comando destrutivo** — apagar a raiz ou o home, force-push em branch protegida, `DROP`/`TRUNCATE`, `DELETE` sem `WHERE`, `curl | sh`, `chmod 777`;
- **arquivo protegido** — segredos, chaves, configuração de CI;
- **artefato gerado** (ADR-0037) — mirror por CLI e manifesto: bloqueia e aponta o canônico e o sync;
- **integridade da SPEC** — status "Concluído" sem célula `verificado:`, recusado no momento da escrita;
- **contrato de relatório** — bloco `kairos-critica`/`kairos-validacao`/`kairos-revisao` malformado, incoerente ou "limpo" sem prova de cobertura (ADR-0032);
- **teste existente** (ADR-0039) — edição em teste que já existia no `HEAD`; nasce em `aviso`, porque refactor legítimo também mexe em teste, e o rastro é o que o `/validar` cobra;
- **leitura de segredo** (ADR-0042) — `cat .env`, `~/.ssh`, `*.pem`, credencial AWS e o serviço de metadados, pelo shell ou pela tool `Read` (`grep`, `ls` e `stat` passam);
- **fiação dos hooks** (ADR-0042) — `.cursor/hooks.json` e `.codex/hooks.json` inteiros, e o bloco `hooks` de `.claude/settings*.json`: mexer ali silenciaria o guardrail de uma vez.

Mais três regras de comando no **piso** (ADR-0042): `rm -rf` com alvo em variável (não
dá para provar o que apaga antes de rodar), destruição fora do projeto e controle da
máquina (`shutdown`, `reboot`). E `gh pr create` é bloqueado em dois casos — ciclo do
`/entregar` fora de `pronto_para_pr` (o da branch atual; se a branch não tem ciclo,
qualquer ciclo aberto), e branch `poc/*` —, assim como `gh pr merge` durante qualquer
ciclo aberto.

Quatro caminhos são **sagrados** — o agente nunca os escreve: `.agents/execucoes/**`,
`.agents/guardrails.json`, `.agents/ciclo/**` e `.agents/quadro/**`. O agente não
escreve o próprio medidor, a própria regra nem o estado que decide o próximo passo —
corroboração que ele reescreve não corrobora, e guardrail que ele afrouxa não guarda.
É o mesmo princípio que o `/otimizar` já aplicava ao comando da métrica, agora no
harness.

A configuração mora em `.agents/guardrails.json`: `liberados` libera um caminho de
escrita, `modos` escolhe `bloqueio` ou `aviso` por classe. O piso — sagrados, leitura
de segredo, fiação dos hooks e as três regras de comando — não se configura: roda
antes de a configuração importar.

**Gate de parada (ADR-0042).** No `Stop`, sessão que escreveu código de produção e não
rodou nenhum gate verde depois da última escrita não encerra em silêncio. Nasce em
`aviso`; em `bloqueio`, o modelo recebe a lista do que ficou sem prova e continua.
Nunca dispara duas vezes na mesma parada.

Nos CLIs sem hook (Codex, OpenCode) — e, no Cursor, para as classes de escrita, que
não têm hook antes da edição — o mesmo contrato roda como CLI:
`guardrail.py verificar .` — checa depois em vez de antes, e vale no CI.

### 3. Gatilhos por evento — a fábrica acorda sozinha (ADR-0026/0040)

`templates/ci/` traz quatro workflows prontos para **o seu projeto**:

| Workflow | Dispara quando | O que faz |
|---|---|---|
| `kairos-forge-revisar.yml` | PR aberto ou atualizado | Roda `/kairos-forge:revisar` e comenta o parecer |
| `kairos-forge-corrigir.yml` | CI do projeto fica vermelho | Tenta corrigir **abrindo PR** — **nunca** escreve na base |
| `kairos-forge-auditar.yml` | Cron semanal | Roda `/kairos-forge:auditar` e abre issue com as 3 lacunas |
| `kairos-forge-triar.yml` | Issue aberta, reaberta ou rotulada `forge:triar` | Laura e Joana classificam em `forge:pronto` · `forge:precisa-spec` · `forge:falta-informacao` · `forge:aguardar` |

```bash
mkdir -p .github/workflows
cp <plugin>/templates/ci/kairos-forge-*.yml .github/workflows/
```

Depois, crie o segredo `ANTHROPIC_API_KEY` em **Settings → Secrets → Actions**; sem
ele os workflows pulam com mensagem clara em vez de falhar. Na triagem, o rótulo é
fila, lock e pausa: `forge:construir` é do humano — o workflow nunca o aplica. Crie
os rótulos `forge:*` no repositório antes de instalar.

> **Instale nesta ordem.** Gatilho por evento sem telemetria e sem guardrail não
> é autonomia — é pipeline sem supervisão. O `/auditar` recomenda as lacunas
> nessa ordem de propósito.

### 4. Máquina de estados do arco — o próximo passo é decidido por código (ADR-0029/0033)

O `/kairos-forge:entregar` executa e registra; quem decide transição, orçamento e
escalação é `scripts/ciclo.py`, com o estado em `.agents/ciclo/`. Na construção, o arco
usa `mobilizar` no Claude Code quando as tarefas são independentes, e `rodar` no resto
— sempre no Codex, no OpenCode, no Cursor e em execução headless.

- **Planejamento em fases** (ADR-0033): entendimento, abordagem e aprovação da SPEC são estados, não prosa — um runner headless para neles de verdade. Antes da aprovação, **dois críticos** que não escreveram a SPEC a atacam (fence `kairos-critica`), e o parser recusa crítica de um crítico só.
- **Orçamento por gate**, em três gates: `criticar`, `validar` e `revisar`. Esgotou, o ciclo vai para `escalado`. Progresso real devolve a ficha (ADR-0032), com um teto absoluto por cima.
- **Veredicto vem do relatório em disco**, nunca da palavra do agente; `corrigindo_revisao` só sai para `validando`.
- **SPEC aprovada é selada por digest.** Mudou requisito, critério ou plano depois, resultado verde é recusado até o humano aceitar a versão nova com `ciclo.py reaprovar` (contrato 1.1) — SPEC reescrita para casar com o construído é o `verificado:` pelo avesso.

**Contrato público (ADR-0034).** `ciclo.py estado --json` e as três fences são
superfície estável e versionada, com campos derivados (`terminal`,
`aguardando_humano`, `gate`, `resultados_validos`) para quem dirige a fábrica de
fora — um runner, um job de CI, o [kairos-symphony](https://github.com/VilelaAI/kairos-symphony) —
não precisar comparar nome de estado. A assinatura em `contratos/ASSINATURA.json` é
verificada no CI: mudar a forma sem reassinar falha. Detalhe em
[`docs/contrato-de-integracao.md`](docs/contrato-de-integracao.md).

### 5. Quadro de tarefas — o time paralelo em qualquer CLI (ADR-0035/0036)

O `/kairos-forge:mobilizar` deixou de ser exclusivo do Claude Code quando o quadro
saiu da sessão e virou arquivo do repositório: `scripts/quadro.py`, com o estado em
`.agents/quadro/`. O que entra agora, quantos cabem e se dá para dizer que acabou
passam de prosa a código:

- **dependências** declaradas — grafo, não fila; ciclo e dependência inexistente são recusados;
- **teto de 6 por onda** (ADR-0033) — o quadro não devolve o sétimo;
- **colisão de posse** detectada na inserção — posse sobreposta nunca sai na mesma onda;
- **tempo limite** (`varrer`, ADR-0036) — worker que morre sem avisar vira `bloqueada` e devolve a vaga;
- **compensação** (`compensar`, ADR-0036) — tarefa concluída que se revelou inválida é desfeita junto com só o que foi construído sobre ela, em ordem inversa (Saga), pelo `--reverter` declarado antes;
- **`encerrar` recusa lacuna escondida** — tarefa aberta só sai com a lacuna declarada.

Quem escreve no quadro é a Laura, não o teammate. O quadro é o mesmo nos quatro CLIs;
só o adaptador de lançamento muda (veja [Compatibilidade](#compatibilidade-entre-plataformas)).

### 6. Verificação — gate verde não é prova (ADR-0039/0043)

A verificação do agente sobre o próprio trabalho não vale como prova. `scripts/prova.py`
transforma as formas silenciosas de gate verde sem prova em achado com nome:

```bash
python3 scripts/prova.py pre-patch          # teste novo rodado contra a base, sem o patch
python3 scripts/prova.py testes-alterados   # teste existente modificado ou removido no diff
python3 scripts/prova.py selado             # caso selado de eval vazado para o que o sistema lê
python3 scripts/prova.py colher --validar   # entrega mesclada com teste vira caso de benchmark
```

- `pre-patch` roda o teste escrito junto com o patch num worktree descartável da base: `passou_na_base` = o teste passa sem a mudança, então não a prova.
- `testes-alterados` lista asserção removida, caso pulado ou apagado — suíte que o agente afrouxou não é evidência.
- `selado` (ADR-0043): caso de `evals/*/selado.jsonl` copiado para persona, skill, `contextos/`, teste ou doc, ou repetido no conjunto visível, sai 1 — eval que já viu o gabarito aprova quem leu a resposta.
- `colher` (ADR-0044): cada PR mesclado da fábrica com teste no diff vira caso candidato em `evals/entregas/candidatos.jsonl` — pedido é a issue que o PR fechou, base é o commit de antes, gabarito são os testes. Com `--validar`, só fica o caso cujo teste falha na base e passa na entrega.

Nenhum é veredicto sozinho: o `/validar` cobra a justificativa, a Patrícia lê no
`/revisar`, e o `selado` roda no CI do projeto.

### 7. Quadro vivo — onde tudo está, numa tela (ADR-0013/0032)

O estado mora em cinco lugares — a SPEC, `.agents/ciclo/`, os relatórios,
`.agents/execucoes/` e `.agents/quadro/`. `scripts/painel.py` junta:

```bash
python3 scripts/painel.py                      # tudo
python3 scripts/painel.py SPEC-001             # uma SPEC
python3 scripts/painel.py --html quadro.html   # página autocontida, abre sem rede
python3 scripts/painel.py --json               # pra outra ferramenta consumir
python3 scripts/painel.py --caixa [--github]   # caixa de entrada: o que espera por uma pessoa
```

Requisitos por coluna, progresso da SPEC, estado do arco com as fichas de
orçamento, veredicto dos três gates (crítica, validação, revisão) com a cobertura
declarada, as mobilizações do quadro de tarefas e a trajetória. A `--caixa` (ADR-0044)
mostra só o que espera por uma pessoa: gate do planejamento, SPEC alterada depois de
aprovada, ciclo escalado, tarefa bloqueada ou vencida e, com `--github`, issue
`forge:falta-informacao` e PR aberto pela fábrica.

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
| Comando de instalação | `/plugin marketplace add` (TUI) | `codex plugin marketplace add` + escolher na TUI + `instalar --cli codex` | `cp -R skills/* .opencode/skills/` + `instalar --cli opencode` | `cp -R plugin/.cursor/. <projeto>/.cursor/` (ou `~/.cursor/`, sem hooks) |
| Skills | `skills/<nome>/SKILL.md` | mesma pasta `skills/` (compartilhada) | `.opencode/skills/` ou `.claude/skills/` | `.cursor/skills/` (mirror gerado, padrão Agent Skills) |
| Subagents com persona | `agents/<id>.md` (nativo) | `.agents/<id>/AGENT.md` + roles `.codex/agents/<id>.toml` (gerados) | `.opencode/agent/<id>.md` (gerado, `mode: subagent`) | `.cursor/agents/<id>.md` (gerado, frontmatter adaptado) |
| Allow-list de ferramentas do agente | ✅ enforced | ⚠️ instrução (`apply_patch` sobrevive) | ✅ enforced (traduzida para `permission`) | ⚠️ degrada para `readonly` |
| SessionStart banner | ✅ `hooks/hooks.json` | ✅ `.codex/hooks.json` | ❌ sem `oh-my-opencode` | ✅ rule `alwaysApply` (`.cursor/rules/kairos-forge.mdc`) |
| Lembrete de DoD (`PostToolUse`, uma vez por sessão — ADR-0038) | ✅ | ❌ | ❌ sem `oh-my-opencode` | ❌ |
| Telemetria de execução (ADR-0021) | ✅ completa (4 pontos do ciclo) | ⚠️ só SessionStart — sem trajetória útil | ❌ | ✅ via `.cursor/hooks.json` gerado (ADR-0042) |
| Guardrail em hook (ADR-0022/0042) | ✅ todas as classes | ❌ só modo CLI (`guardrail.py verificar`) | ❌ só modo CLI | ✅ comando, leitura, spec, contrato e parada; classes de escrita só no modo CLI (sem hook antes da edição) |
| `/mobilizar` (time paralelo, ADR-0035) | ✅ Agent Teams (exige `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) | ✅ `spawn_agent` (exige as personas instaladas) | ✅ `task` — uma onda = uma mensagem com várias chamadas | ✅ o agente principal orquestra os subagents de `.cursor/agents/` |
| Falar com worker em voo | ✅ `SendMessage` | ✅ `send_input` / `send_message` | ✅ retomar por `task_id` | ❌ — relance com contexto completo |
| Instruções de projeto | `CLAUDE.md` | `AGENTS.md` | `CLAUDE.md` (fallback) ou `AGENTS.md` | `AGENTS.md` |

> **Nota sobre skills compartilhadas:** Tanto Claude Code quanto Codex descobrem skills em `skills/<nome>/SKILL.md` quando empacotados como plugin. Não há duplicação — a mesma pasta serve aos dois CLIs. Apenas os manifests (`.claude-plugin/` vs `.codex-plugin/`) e os subagents é que diferem. OpenCode recebe cópia das skills; Cursor, o mirror gerado em `.cursor/skills/`.

> **Nota sobre `mobilizar`:** roda nos quatro CLIs (ADR-0035). O quadro `quadro.py` (estado em `.agents/quadro/`) é o mesmo em todos — dependências, teto de 6 por onda, colisão de posse, `varrer`, `compensar` e `encerrar` que recusa lacuna escondida; só o adaptador de lançamento muda, e a skill detecta o CLI no Passo 0. Em CLI sem lançamento paralelo, ela não recusa: roda o mesmo quadro em série ou oferece `/kairos-forge:rodar`.

> **Nota sobre telemetria e guardrail sem hook:** no Codex e no OpenCode, `.agents/execucoes/` não ganha trajetória útil (o Codex só registra o SessionStart; o OpenCode, nada), a dimensão **Autonomia** do `/auditar` pontua 0 e o `/validar` pula a corroboração de trajetória. Isso é honesto, não bug: sem hook não há trajetória. O Cursor tem telemetria e guardrail pelo `.cursor/hooks.json` gerado (ADR-0042), menos as classes de escrita, porque não há hook antes da edição. O caminho para o que falta é rodar `guardrail.py verificar` e os workflows de `templates/ci/` no pipeline do projeto.

> **Nota sobre artefatos gerados:** `.agents/<id>/AGENT.md`, `.codex/agents/`, `.opencode/agent/`, `.cursor/` e `.claude-plugin/ativos.manifest.json` são **gerados** a partir de `agents/` + `skills/` pelo `scripts/sync-multi-cli.py`. Não edite à mão — o guardrail bloqueia (classe `gerado`, ADR-0037) e a mudança se perderia no próximo sync. Edite o canônico e rode o sync.

## Instalação

### Claude Code (recomendado)

```
/plugin marketplace add VilelaAI/kairos-forge
/plugin install kairos-forge@kairos-forge
/reload-plugins
```

Para `/kairos-forge:mobilizar` via Agent Teams (a variável só existe no Claude Code; os outros CLIs não precisam dela):

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

Em **macOS** (use caminho absoluto):

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

#### Personas para o `/mobilizar` (ADR-0035)

O Codex procura roles de subagent no diretório de config dele, não no do plugin. Instale as 71 personas — é o que faz `spawn_agent(agent_type: "carlos-dba")` resolver o agente em vez de receber a persona colada no prompt:

```bash
# kairos-forge/ é o clone; ajuste o caminho se você já estiver dentro dele
python3 kairos-forge/scripts/sync-multi-cli.py instalar --cli codex --escopo global
```

`--escopo global` grava em `~/.codex/agents/`; sem ele, o comando instala em `.codex/agents/` do diretório atual — rode da raiz do projeto. `--dry-run` mostra antes, e `--cli todos` instala Codex, OpenCode e Cursor de uma vez. O comando é idempotente e **preserva agentes seus** com nome coincidente.

O teto de concorrência do Codex (`agents.max_concurrent_threads_per_session`, default 6) coincide com o teto de onda da fábrica. Se baixar um, baixe o outro (`--teto-onda` ao abrir o quadro) — senão o quadro libera tarefas que o Codex recusa lançar.

#### Onde mora o quê (Codex)

- `.codex-plugin/plugin.json` — manifest do plugin
- `.agents/plugins/marketplace.json` — marketplace catalog (necessário pra `marketplace add` funcionar no Codex)
- `skills/<nome>/SKILL.md` — skills (mesmo path do Claude Code)
- `.agents/<id>/AGENT.md` — subagents no formato Codex (gerados a partir de `agents/`)
- `.codex/agents/<id>.toml` — roles de subagent que o `spawn_agent` resolve (gerados; o `instalar` copia para o config do Codex)
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

# Por projeto (o único com telemetria e guardrail):
mkdir -p /caminho/do/projeto/.cursor && cp -R kairos-forge/plugin/.cursor/. /caminho/do/projeto/.cursor/

# Ou global (todos os projetos, sem hooks):
mkdir -p ~/.cursor && cp -R kairos-forge/plugin/.cursor/{agents,skills,rules,scripts,templates} ~/.cursor/
```

A forma `.cursor/.` copia o conteúdo da pasta e não aninha `.cursor/.cursor/` quando ela já existe no projeto. Na instalação global o `hooks.json` fica de fora porque chama `.cursor/scripts/` relativo ao projeto — telemetria e guardrail exigem a instalação por projeto.

Para atualizar só as personas depois de um `git pull` (sem `--escopo global`, rode da raiz do projeto):

```bash
python3 kairos-forge/scripts/sync-multi-cli.py instalar --cli cursor [--escopo global]
```

`mobilizar` roda no Cursor: o agente principal orquestra os subagents de `.cursor/agents/` em paralelo enquanto o `quadro.py` guarda dependências, posse e contagem — sem canal para falar com worker em voo; se faltar contexto, relance com o contexto completo.

O que chega: 71 subagents em `.cursor/agents/` (agentes consultivos viram `readonly` — o Cursor não tem allow-list por ferramenta), 18 skills no menu `/` (`.cursor/skills/`, padrão Agent Skills), a rule `alwaysApply` com o banner da fábrica e a resolução de `${CLAUDE_PLUGIN_ROOT}`, os dez scripts de suporte em `.cursor/scripts/` (`grafo`, `telemetria`, `execucao`, `guardrail`, `diagnostico`, `ciclo`, `contrato`, `painel`, `quadro`, `prova`), `templates/` e o `hooks.json` que liga telemetria e guardrail aos eventos do Cursor (ADR-0042). Instruções de projeto: o Cursor lê `AGENTS.md` — o `/kairos-forge:onboardar` oferece gerá-lo junto do `CLAUDE.md`.

### Hermes Agent (bot 24/7 — ponte)

Com o [Hermes Agent](https://hermes-agent.nousresearch.com) rodando num VPS, a ponte em [`hermes/`](hermes/README.md) instala as skills que roteiam engenharia estruturada pra fábrica: você manda "construir com a fábrica: …" no Telegram, o Hermes opera o ciclo e a fábrica especifica, constrói, valida e revisa dentro do Claude Code (ADR-0019).

```bash
bash hermes/install.sh
```

### OpenCode

```bash
git clone https://github.com/VilelaAI/kairos-forge.git

# Skills — opção A: path nativo do OpenCode
mkdir -p .opencode/skills && cp -r kairos-forge/skills/* .opencode/skills/

# Skills — opção B: path de compatibilidade Claude Code
mkdir -p .claude/skills && cp -r kairos-forge/skills/* .claude/skills/

# Personas (subagents para o /mobilizar e a delegação)
python3 kairos-forge/scripts/sync-multi-cli.py instalar --cli opencode
```

As personas vão para `.opencode/agent/` do diretório atual (rode da raiz do projeto); `--escopo global` usa `$XDG_CONFIG_HOME/opencode/agent` (por padrão `~/.config/opencode/agent`). São subagents com `mode: subagent` e a allow-list traduzida para `permission`, que no OpenCode é enforced. O `/mobilizar` roda por `task`: uma onda é uma mensagem com várias chamadas.

OpenCode lê `CLAUDE.md` ou `AGENTS.md` automaticamente. Para o banner e o lembrete de DoD, instale [oh-my-opencode](https://github.com/fractalmind-ai/oh-my-opencode). Telemetria e guardrail não têm hook no OpenCode: rode `guardrail.py verificar` e os workflows de `templates/ci/` no CI do projeto.

## Primeiros passos

```
/kairos-forge:onboardar
```

Depois, o caminho curto — a fábrica percorre o ciclo e volta com o PR:

```
/kairos-forge:entregar exportar relatorios em CSV no dashboard
   └─ Laura declara o orçamento, confirma com você entendimento e abordagem,
      especifica, dois críticos atacam a SPEC, PARA para você aprovar,
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

# Em paralelo (qualquer dos quatro CLIs):
/kairos-forge:mobilizar SPEC-001
   └─ Carlos + Lucas + Marina + Ricardo em paralelo, coordenados pelo quadro (quadro.py)

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

Esta pasta `plugin/` é a cópia distribuída: o canônico mora em `agents/` e `skills/` **na raiz do repositório**, e o `release.py bump` espelha a raiz aqui e regenera os mirrors — edição feita direto em `plugin/` some no próximo bump (este README é a exceção, mantido à mão). Rode os comandos abaixo na raiz.

Quando alterar `agents/` ou `skills/`, **sempre rode o sync** antes de commitar:

```bash
python3 scripts/sync-multi-cli.py
git add agents/ skills/ .agents/ .codex/agents/ .opencode/ .cursor/ .claude-plugin/ativos.manifest.json
git commit -m "feat(<modulo>): <descrição>"
```

Sem o sync, usuários de Codex CLI, OpenCode e Cursor ficam desatualizados.

Para versão, não edite manifests à mão — o script de release calcula as contagens do filesystem, injeta versão e números em manifests, banners e docs, roda os dois syncs e espelha em `plugin/`:

```bash
python3 scripts/release.py bump X.Y.Z                      # tudo de uma vez
python3 scripts/release.py check                           # o que o CI roda em todo PR
python3 -m unittest discover -s scripts/tests -t scripts   # testes de ciclo, guardrail e prova
```

Mudou o prompt da Laura, a `description` de um agente ou o roteamento → rode o eval de roteamento (`evals/roteamento-laura/`, só na raiz) com a Alice antes do commit.

## Convenções

- **PT-BR oficial.** Skills, agentes, comandos, comentários, mensagens de commit.
- **Verbos no infinitivo.** `especificar`, não `spec`.
- **Persona explícita.** Agentes se apresentam: "Oi, Marina aqui — Frontend."
- **Apoio nunca codifica.** Squads de apoio entregam texto.
- **Mirror é gerado, não editado.** `.agents/<id>/AGENT.md`, `.codex/agents/`, `.opencode/agent/`, `.cursor/` e `.claude-plugin/ativos.manifest.json` saem do sync; o guardrail bloqueia edição à mão (classe `gerado`, ADR-0037). Edite `agents/`/`skills/` da raiz e rode o sync.

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
- **v0.25** — quadro vivo: `painel.py` renderiza SPEC + arco + veredictos + trajetória numa tela (terminal, HTML autocontido ou JSON), com "Concluído" sem `verificado:` não contando como pronto (ADR-0013/0032)
- **v0.26** — planejamento em fases no arco, crítica adversarial da SPEC com dois críticos independentes, e teto de 6 teammates por onda no `/mobilizar` (ADR-0033)
- **v0.27** — contrato de integração público e versionado: `ciclo.py estado --json` e as três fences com campos derivados e assinatura verificada no CI (ADR-0034)
- **v0.28** — `/mobilizar` nos quatro CLIs: o quadro sai da sessão e vira `quadro.py`, com as 71 personas geradas no formato nativo de cada CLI (ADR-0035)
- **v0.29** — tempo limite (`varrer`) e compensação em ordem inversa (`compensar`) no quadro do `/mobilizar` (ADR-0036)
- **v0.30** — artefato gerado inegociável (classe `gerado` no guardrail), `/evoluir` lendo a trajetória antes da entrevista e trilha de pipeline de dados (ADR-0037)
- **v0.31** — instruções enxutas: descriptions curtas dentro do orçamento estático, skills maiores como roteador + `references/` e lembrete de DoD uma vez por sessão (ADR-0038)
- **v0.32** — verificação é o gargalo: `prova.py` (prova negativa e teste afrouxado), classe `teste` em `aviso`, gates do barato ao caro no `/validar` e ruído medido no `/revisar` (ADR-0039)
- **v0.33** — porta de entrada: triagem por issue (`kairos-forge-triar.yml`), `rodar explorar` (POC descartável), `DESIGN.md` como sistema de design e teto de apetite (ADR-0040)
- **v0.34** — camada de código do grafo por AST (`grafo.py codigo`/`contexto`), escada de prontidão do legado e corte em sombra no `/migrar` (ADR-0041)
- **v0.35** — piso de execução no guardrail (leitura de segredo, fiação dos hooks, destruição não provável ou fora do projeto, controle da máquina), gate de parada no `Stop` e hooks no Cursor (ADR-0042)
- **v0.36** — juiz cego à versão no `/avaliar`, `prova.py selado` contra vazamento do conjunto selado e veredicto com contraste no `/evoluir` (ADR-0043)
- **v0.37** (atual) — autonomia de PR medida pelo git em qualquer CLI (`telemetria.py prs`), benchmark colhido das entregas mescladas (`prova.py colher`) e caixa de entrada (`painel.py --caixa`) (ADR-0044)
- **Candidato, sem versão** — perfis Tier 3 sob demanda via `/evoluir` (SEO técnico, UX research, desktop, base de suporte), registrados no ADR-0017; mais trilhas por tema

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
- [ADR-0033](docs/adr/0033-planejamento-em-fases-e-critica-adversarial.md) — planejamento em fases e crítica adversarial da SPEC: a etapa que não tinha contraditório
- [ADR-0034](docs/adr/0034-contrato-de-integracao.md) — contrato de integração público e versionado
- [ADR-0035](docs/adr/0035-mobilizar-multi-cli.md) — mobilizar em qualquer CLI: o quadro sai da sessão
- [ADR-0036](docs/adr/0036-timeout-e-compensacao.md) — tempo limite e compensação: o que fazer quando o trabalho já feito perde a validade
- [ADR-0037](docs/adr/0037-artefato-gerado-e-laco-de-melhoria.md) — artefato gerado é inegociável, e a trajetória volta para quem melhora
- [ADR-0038](docs/adr/0038-instrucoes-enxutas.md) — instruções enxutas: descriptions curtas, skill como roteador e menos paradas
- [ADR-0039](docs/adr/0039-verificacao-e-o-gargalo.md) — verificação é o gargalo: prova negativa dos testes, escada de verificação e revisão calibrada
- [ADR-0040](docs/adr/0040-porta-de-entrada-da-fabrica.md) — porta de entrada da fábrica: triagem por issue, POC descartável, `DESIGN.md` e teto de apetite
- [ADR-0041](docs/adr/0041-grafo-de-codigo-e-legado-em-sombra.md) — grafo de código por AST, escada de prontidão do legado e corte em sombra
- [ADR-0042](docs/adr/0042-piso-e-gate-de-parada.md) — piso de execução, gate de parada e hooks no Cursor
- [ADR-0043](docs/adr/0043-juiz-cego-selado-e-veredicto.md) — juiz cego, selado que não vaza e veredicto com contraste
- [ADR-0044](docs/adr/0044-autonomia-medida-benchmark-e-caixa.md) — autonomia medida pelo git, benchmark colhido do histórico e caixa de entrada
- [Contrato de integração](docs/contrato-de-integracao.md) — o que é estável para quem dirige a fábrica de fora: `ciclo.py estado --json` e as três fences
- [Memória persistente](docs/memoria-persistente.md) — guia das 3 camadas e instalação opcional do ai-memory
- [Análise: o novo SDLC e o caminho até L4](docs/revisoes/2026-08-01-analise-whitepaper-novo-sdlc-e-caminho-l4.md) — o harness da fábrica medido contra o whitepaper Day-1 do Google, com as lacunas e o que cada uma virou

## Licença

MIT. Ver [LICENSE](../LICENSE).

## Sobre

Mantido por [VilelaAI](https://vilela.tech). Faz parte da camada Build do KairOS, junto com [kairos-ai](https://github.com/VilelaAI/kairos-ai), kairos-runtime, kairos-domains, kairos-studio e kairos-platform.
