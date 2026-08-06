# Análise — "The New SDLC With Vibe Coding" vs. kairos-forge: o caminho até L4

**Data:** 2026-08-01
**Fonte analisada:** Osmani, A.; Saboo, S.; Kartakis, S. — *The New SDLC With Vibe Coding: From ad-hoc prompting to Agentic Engineering* (Google, Agents Whitepaper Series, Day 1, maio/2026), 51 páginas.
**Versão do kairos-forge analisada:** v0.16.0 (commit `f933a49`)
**Objetivo:** identificar as lacunas do harness que separam a fábrica do nível **L4 — Fábrica (100% de autonomia)**.

---

## 1. O que o whitepaper afirma (teses operativas)

Sete teses do paper têm consequência direta sobre o desenho do kairos-forge.

**T1 — Agente = Modelo + Harness.** O comportamento que o usuário sente é dominado pelo harness, não pelo modelo. O paper cita números: no Terminal Bench 2.0 um time saiu de fora do Top 30 para o Top 5 **mudando só o harness**, sem trocar o modelo; a LangChain ganhou 13,7 pontos no mesmo benchmark mexendo apenas em system prompt, tools e middleware. A conclusão é dura: *"most agent failures, examined honestly, are configuration failures."*

**T2 — O harness tem seis componentes.** Instruções/rule files, tools, **sandboxes e ambientes de execução**, lógica de orquestração, **guardrails/hooks (código determinístico em pontos do ciclo de vida)** e **observabilidade (logs, traces, evals, medição de custo e latência)**. E o paper avisa: *"Without observability, there is no way to tell whether the agent is doing well or quietly drifting."*

**T3 — Testes e evals, os dois.** *"Tests verify the deterministic parts... Evals verify the parts that are not deterministic... Without both, the practice is always vibe coding, regardless of how sophisticated the prompts are."* É um teste binário, não um espectro: sem eval, é vibe coding — por mais disciplinado que o resto seja.

**T4 — Avaliação de trajetória, não só de saída.** *"a fluent output that skipped its verification steps is a more dangerous failure than one with a visible error."* Verificar o artefato final não basta; é preciso verificar o caminho.

**T5 — Modelo de fábrica com cinco partes.** Specs/contexto, agentes, testes e gates, **loops de feedback que roteiam falhas de volta aos agentes para correção**, e guardrails. O loop é parte da fábrica, não do operador humano.

**T6 — Contexto estático vs. dinâmico é decisão de arquitetura.** *"The best systems treat this boundary as a first-class architectural decision, reviewed and versioned like any other configuration."* Agent Skills com disclosure progressivo é o padrão recomendado — o agente carrega metadados na largada, instruções no match, referências pesadas só sob demanda.

**T7 — Economia: CapEx alto, OpEx baixo.** Engenharia agêntica investe adiantado (schemas, suites, contexto estruturado) para derrubar o custo marginal por feature. Roteamento inteligente de modelo (modelo caro só onde importa) e engenharia de contexto são alavancas financeiras, não só técnicas.

E a régua para líderes: *"Set the bar at the eval, not the demo."* Com rubrica explícita nomeando o que se pontua: **task success, tool use quality, trajectory compliance, hallucination, response quality.**

---

## 2. O que L4 exige (decodificando a imagem)

| Nível | Descrição | Autonomia |
|---|---|---|
| L2 — Babá | Usa modo agente, mas aprova cada etapa | 30% |
| L3 — Gerente | Spec-driven development, confia na IA para executar o plano. Humanos focam em planejamento, tarefas paralelas e **revisão final do pull request** | 80% |
| **L4 — Fábrica** | **Pipelines autônomos** cuidam de correções, QA, protótipos e fluxos repetíveis. **O time confia mais no harness do que em revisão individual de código** | **100%** |

Duas leituras erradas a evitar antes de qualquer coisa:

- **L4 não é "sem humano".** O paper defende times híbridos onde humanos definem direção e agentes implementam, com protocolos de handoff claros. O que muda de L3 para L4 não é *quem decide*, é *onde o humano gasta atenção*: sai de ler cada diff, entra em direção, exceção e julgamento.
- **L4 não é mais autonomia dentro de uma execução.** É **arco fechado** (a falha volta ao agente sozinha, com orçamento) **mais confiança conquistada** (existe instrumento que justifica confiar no harness em vez de ler o diff).

A frase operativa da imagem é *"confia mais no harness do que em revisão individual de código"*. Confiança não se declara — se mede. É isso que define a agenda técnica abaixo.

---

## 3. Onde o kairos-forge está hoje

### 3.1. Pontuação por componente do harness (T2)

| Componente | Estado | Nota |
|---|---|---|
| **Instruções / rule files** | 71 agentes com persona, fronteiras nomeadas e seção de Limites; 15 skills com disclosure progressivo e gatilho negativo na description; `anti-drift.md`; 5 trilhas por tema; `CLAUDE.md.template` | ⭐⭐⭐⭐⭐ |
| **Tools** | Allow-list explícita por agente **verificada no CI** (`check-agent-security.py`); `grafo.py` como tool determinística real; consumo oportunista de MCP (`memory_*`) | ⭐⭐⭐⭐ |
| **Orquestração** | Roteamento da Laura; grafo de dependências no `mobilizar` (com teste da aresta real e auditoria de recurso compartilhado); tiers de modelo; fan-in em camadas; orçamento de complexidade com avisa-e-pausa | ⭐⭐⭐⭐ |
| **Guardrails / hooks** | **Dois hooks, ambos `echo`.** SessionStart imprime banner; PostToolUse imprime "lembre de chamar Ricardo". Nenhum bloqueia nada. Sem PreToolUse, sem Stop, sem SessionEnd | ⭐⭐ |
| **Sandbox / ambiente** | File ownership é, nas palavras da própria skill, *"Enforced via prompt"*. Sem worktree, sem container, sem fronteira de escrita imposta por código | ⭐ |
| **Observabilidade** | Praticamente ausente. O ledger do `mobilizar` é tabela digitada pela Laura no encerramento, auto-reportada, não persistida — e a própria skill declara: *"O plugin não mede tokens de dentro da sessão"*. Sem trace de execução, sem custo, sem latência, sem sinal de drift | ⭐ |

### 3.2. Contra a tese binária de verificação (T3)

| Eixo | Estado |
|---|---|
| **Testes** | Coberto e maduro — Ricardo, matriz de testes por requisito, gates por tarefa, `contextos/testes.md`, `validar` **re-executa** os gates de forma independente |
| **Evals** | Existe **um** eval em todo o repositório (`evals/roteamento-laura/`, 60 casos). Ele é dogfooding do plugin, **explicitamente não distribuído** aos usuários, e sua acurácia é apurada **manualmente em sessão** pela Alice. O CI só valida que os ids do gold set existem |

Aplicando o teste do paper ao próprio produto: **o usuário do kairos-forge recebe disciplina de teste e nenhuma disciplina de eval.** No eixo de verificação, o harness entregue ao usuário fica em "structured AI-assisted coding", não em engenharia agêntica plena. E o plugin, que tem um eval, não o roda em CI — a Alice o roda à mão.

### 3.3. Nível atual, por eixo

| Eixo | Nível | Evidência |
|---|---|---|
| Especificação | **L4** | SPEC rastreável com IDs, prioridade, critério verificável, Status × Verificação; modo RFC; trilhas; apetite antes de escopo |
| Execução multi-agente | **L3+** | `mobilizar` com grafo de dependências, file ownership, orçamento declarado, checkpoints, encerramento honesto |
| Verificação de saída | **L3** | `validar` re-roda gates e exige `verificado:`; `revisar` multi-agente com severidade e regra de bloqueio |
| Verificação de trajetória | **L1** | Não existe. Toda evidência é auto-reportada pelo agente que executou |
| Loop de correção | **L2 no plugin / L3 na ponte** | Dentro da task existe (autocrítica ≤ 2 rodadas; correção ≤ 2 rodadas no `mobilizar`). **Entre skills, o loop é manual** — `validar` declara "Não implemente correções nesta skill" e devolve recomendação para o usuário digitar o próximo comando |
| Gatilho | **L2** | 15 skills, todas por slash command. Nenhum gatilho por evento |
| Observabilidade | **L1** | Sem registro de execução, sem histórico, sem número de autonomia |
| Contenção de raio | **L2** | Ownership por prompt; reversibilidade só existe no `otimizar` (catraca) e no `lancar` (rollback anotado) |

**Veredicto:** o kairos-forge é um **L3 forte** — cabe quase palavra por palavra na descrição da coluna L3 da imagem ("spec-driven development, confia na IA para executar o plano, humanos focam em planejamento, tarefas paralelas e revisão final do PR"). Tem bolsões genuínos de L4 (a catraca do `otimizar` é um pipeline autônomo de verdade, com manter-ou-reverter e linhagem) e um eixo travado em L1 que **estruturalmente impede** L4: sem observabilidade, ninguém tem base para confiar no harness mais do que na leitura do diff — e ninguém consegue nem medir se a autonomia subiu.

---

## 4. Lacunas, ranqueadas por alavancagem

### G1 — Observabilidade do harness: inexistente `🔴 bloqueia L4`

O paper é categórico (T2) e a imagem depende disso: confiar no harness exige histórico. Hoje não há como responder à única pergunta que define o nível de autonomia — **"que porcentagem dos ciclos a fábrica termina sem intervenção humana?"**. O `auditar` pontua o *setup* da fábrica em 5 dimensões; nenhuma delas olha para as *execuções*.

Sem G1, todo o resto é fé. Com G1, a autonomia vira número — e número que sobe é o que autoriza o time a parar de ler cada diff.

**Ação:** registro determinístico de execução em `.agents/execucoes/*.jsonl` (skill, SPEC, duração, gates rodados e resultado, rodadas de correção, escalações, veredicto, tier de modelo, intervenções humanas), escrito por hook `Stop`/`SubagentStop` — não pelo modelo. `scripts/telemetria.py` agrega. Nova dimensão **Autonomia** no `auditar`.

### G2 — Loop fechado existe, mas está preso na ponte Hermes `🔴 bloqueia L4`

Este é o achado mais acionável da análise. O arco que o paper descreve em T5 **já foi desenhado** — em `hermes/skills/kairos-forge-ciclo.md`: validar bloqueia em P1 → volta à etapa de construção, máximo 2 rodadas, escala ao fundador na terceira; achado 🔴 no revisar → volta à construção. É exatamente o loop de feedback da fábrica.

Só que ele vive numa skill do Hermes, executada pelo agente do Hermes. **O usuário do plugin em Claude Code, Codex, OpenCode ou Cursor não tem esse arco.** Ele tem 15 verbos e digita a sequência à mão. É a diferença entre uma linha de montagem e uma bancada com ferramentas boas.

**Ação:** promover o arco para dentro do plugin como skill de ciclo (`entregar`), com orçamento declarado, rodadas limitadas, regra de escalação e encerramento honesto — a mesma disciplina que o `mobilizar` já aplica dentro de uma task, aplicada entre skills.

### G3 — Hooks pedagógicos onde deveriam ser determinísticos `🟠 alto`

O paper define hooks como *"deterministic code that runs at specific lifecycle points... the place for things the agent should never forget but often does"*. Os dois hooks do kairos-forge imprimem texto. O PostToolUse detecta arquivo de produção modificado e sugere lembrar do Ricardo — não impede nada.

Enquanto isso, as regras **duras** da fábrica (file ownership, `verificado:` obrigatório, Pare e Pergunte, Definition of Done, PT-BR, proibição de inventar conteúdo) moram todas em prosa que o modelo pode driftar. É a inversão exata do que T1 recomenda: o que não pode falhar deveria estar no código determinístico, não no prompt.

**Ação:** `PreToolUse` bloqueando escrita fora do file ownership do teammate (exit 2) e comandos destrutivos sem aprovação; `PostToolUse` em `docs/specs/*.md` recusando "Concluído" sem `verificado:` no momento da escrita, em vez de esperar o `validar`; `Stop` gravando o registro do G1. Como o Codex só suporta SessionStart, o mesmo conteúdo precisa existir como `scripts/guardrail.py` chamável de CI/pre-commit em qualquer CLI.

### G4 — Evals para o projeto do usuário: ausentes `🟠 alto`

Pela régua binária de T3, esta é a lacuna que impede chamar o produto entregue de engenharia agêntica plena. A Alice existe como agente e é excelente ("assume quebrado até provar o contrário", "o gerador nunca avalia a si mesmo"), mas não há skill, template, rubrica nem gate que materialize isso no projeto do usuário. Nenhuma das 15 skills produz um eval.

**Ação:** skill `avaliar` (dona: Alice) que constrói gold set versionado, define rubrica nos cinco eixos que o paper nomeia (sucesso da tarefa, qualidade de uso de tool, conformidade de trajetória, alucinação, qualidade de resposta), fixa limiar de regressão e instala o gate no CI do projeto. E, por dogfooding, tornar o `evals/roteamento-laura/` executável headless no CI do próprio plugin — hoje a fábrica prega o eval e apura o dela à mão.

### G5 — Validação de trajetória: ausente `🟠 alto`

T4 nomeia o modo de falha mais perigoso, e o kairos-forge está exposto a ele: a célula `verificado:` é escrita **pelo mesmo agente que fez o trabalho**. O `validar` re-executa os gates de forma independente (isso é real e vale crédito), mas nada registra nem confere *o que o agente fez durante a execução* — se rodou o gate antes de declarar verificado, se tocou arquivo fora do ownership, se consultou o grafo. A própria Alice define o princípio que o harness viola no seu próprio nível: o gerador não avalia a si mesmo.

**Ação:** o registro do G1 **é** a trajetória. Com ele, o `validar` ganha um passo barato: cruzar cada `verificado:` com o comando correspondente na trajetória registrada. Alegação sem lastro vira "evidência não corroborada" e bloqueia igual a "sem evidência".

### G6 — Nenhum gatilho sem humano `🟠 alto (mas depende de G1/G3/G7)`

"Pipelines autônomos cuidam de correções, QA, protótipos e fluxos repetíveis" é, por definição, orientado a evento. As 15 skills são todas invocadas por slash command. A ponte Hermes adiciona chat 24/7 e cron, mas cada unidade de trabalho ainda começa com uma frase do fundador — e o merge continua sendo dele. O repositório tem CI para si mesmo e **não entrega nenhuma receita de CI para o projeto do usuário**.

**Ação:** `templates/ci/` com workflows prontos: revisão automática no PR; correção automática em falha de CI (limitada a 2 rodadas, abre PR, nunca escreve na main); auditoria semanal por cron que abre issue com as 3 lacunas de maior alavancagem. Este é o movimento mais visível de L4 — a fábrica trabalhando enquanto ninguém olha.

**Ordem importa:** disparar antes de instrumentar (G1), conter (G3/G7) e provar (G4) não é autonomia, é pipeline sem supervisão. G6 vem depois.

### G7 — Contenção de raio: ownership por prompt `🟡 médio, vira alto com G6`

A tabela comparativa do `mobilizar` declara honestamente: file ownership é *"Enforced via prompt"*. Em L3, com humano lendo o PR, isso basta. Em L4, com ninguém lendo o diff, é a diferença entre pipeline autônomo e pipeline sem supervisão.

**Ação:** isolamento por `git worktree` por teammate no `mobilizar` (conflito deixa de ser disciplina de prompt e vira impossibilidade física, com a Laura fazendo o merge); reversibilidade declarada por tarefa autônoma (comando de revert anotado antes de executar — o que o `otimizar` já faz na catraca e o `lancar` exige no rollback, generalizado); lista explícita de irreversíveis que **nunca** rodam sem humano.

### G8 — Fronteira estático/dinâmico não é decisão versionada `🔵 baixo`

T6 pede que essa fronteira seja decisão de arquitetura revisada e versionada. O kairos-forge acerta o padrão **por bom gosto**, não por decisão registrada: skills ≤ 500 linhas é regra do CLAUDE.md, mas só 1 das 15 skills usa `references/`, e não há ADR nem orçamento de tokens declarando o que é estático (banner, CLAUDE.md do projeto, persona ativa) versus dinâmico (skill no match, referência sob demanda, subgrafo por consulta).

**Ação:** ADR da fronteira + check de orçamento de contexto estático no `release.py check`.

### G9 — Roteamento de modelo declarado, não medido `🔵 baixo, sai de graça com G1`

Os tiers do ADR-0013 (rápido/padrão/preciso) são anunciados na largada e nunca verificados. A tese de OpEx de T7 fica não-testável. Com o registro de execução carregando o tier, vira análise de uma linha.

### G10 — Interoperabilidade (MCP/A2A) `🔵 estratégico, não urgente`

O paper recomenda MCP e A2A como padrões abertos. O kairos-forge **consome** MCP (`memory_*`) e não **expõe** nada. Para L4 com múltiplos pipelines conversando, um servidor MCP expondo `grafo.py` e a telemetria deixaria outros agentes consultarem a memória da fábrica. Opcionalidade estratégica, não lacuna imediata.

---

## 5. Roteiro proposto — três ondas

O princípio de ordenação: **instrumentar → fechar e conter → provar e disparar.** Cada onda torna a seguinte segura.

### Onda 1 — Instrumentar (v0.17) · *"não se confia no que não se mede"*

| Item | Entrega | Lacuna |
|---|---|---|
| Registro de execução | `.agents/execucoes/*.jsonl` escrito por hook `Stop`, não pelo modelo | G1 |
| Agregador | `scripts/telemetria.py` — taxa de conclusão sem intervenção, rodadas médias de correção, gates verdes de primeira, distribuição de tier | G1, G9 |
| Dimensão Autonomia | Sexta dimensão no `auditar` (0–20), pontuando a partir da telemetria | G1 |
| Cruzamento de trajetória | Passo novo no `validar`: `verificado:` sem comando correspondente na trajetória = evidência não corroborada | G5 |

**Critério de pronto:** o `auditar` responde, com número, "que fração dos ciclos terminou sem intervenção humana na última semana?".

### Onda 2 — Fechar e conter (v0.18) · *"o arco fecha sozinho e erra barato"*

| Item | Entrega | Lacuna |
|---|---|---|
| Skill de ciclo | `entregar` — arco especificar → construir → validar → corrigir → revisar → corrigir → PR, com orçamento, rodadas limitadas e escalação (promoção do que já existe na ponte Hermes) | G2 |
| Hooks determinísticos | `PreToolUse` de ownership e de comando destrutivo; `PostToolUse` de `verificado:`; equivalente em `scripts/guardrail.py` para CLIs sem hook | G3 |
| Isolamento real | `git worktree` por teammate no `mobilizar`; reversibilidade declarada por tarefa autônoma; lista de irreversíveis | G7 |

**Critério de pronto:** um bloqueio de P1 no `validar` dispara correção e revalidação **sem o usuário digitar nada**, dentro de orçamento declarado, com escalação honesta ao estourar.

### Onda 3 — Provar e disparar (v0.19 → v1.0) · *"evidência que justifica a confiança"*

| Item | Entrega | Lacuna |
|---|---|---|
| Skill de evals | `avaliar` (Alice) — gold set, rubrica nos 5 eixos do paper, limiar de regressão, gate de CI no projeto do usuário | G4 |
| Dogfooding do eval | `evals/roteamento-laura/` rodando headless no CI do plugin | G4 |
| Gatilhos por evento | `templates/ci/` — revisar no PR, corrigir em falha de CI, auditar por cron | G6 |
| Orçamento de contexto | ADR da fronteira estático/dinâmico + check no `release.py check` | G8 |
| Superfície MCP | Servidor MCP expondo grafo e telemetria (opcional) | G10 |

**Critério de pronto:** a fábrica abre PR corrigindo CI vermelho sem ninguém ter pedido, e o eval de regressão é pré-condição de merge.

### ADRs propostos

- **ADR-0021** — Observabilidade do harness: registro de execução, telemetria e dimensão Autonomia
- **ADR-0022** — Guardrails determinísticos: hooks que bloqueiam + fallback por script para CLIs sem suporte
- **ADR-0023** — Skill `entregar`: o arco fechado do plugin (promoção do ciclo da ponte Hermes)
- **ADR-0024** — Skill `avaliar`: evals com rubrica como gate, no projeto do usuário e no próprio plugin
- **ADR-0025** — Contenção de raio: worktree por teammate, reversibilidade declarada e lista de irreversíveis
- **ADR-0026** — Gatilhos por evento: receitas de CI para o projeto do usuário
- **ADR-0027** — Fronteira estático/dinâmico e orçamento de contexto

---

## 6. O que o kairos-forge já acerta (e não deve perder na corrida para L4)

Vale registrar, porque a tentação de reescrever tudo em nome da autonomia é real. Estes itens já são estado da arte segundo o próprio paper:

- **O ritual `verificado:`** — Status "Concluído" só com prova de execução citada. É antídoto direto contra o modo de falha que T4 descreve. Poucas fábricas têm isso.
- **Encerramento honesto e orçamento de complexidade** — "nunca esconda falha parcial atrás de um resumo fluente", avisa-e-pausa em 80%, pausa em 100%. É a resposta certa ao problema dos 80% do paper.
- **Pare e Pergunte (ADR-0015)** — endereça nominalmente um dos modos de falha conceitual que o paper lista: *"failure to seek clarification on ambiguous requirements"*.
- **Allow-list de ferramentas verificada em CI** — o paper pede "scoped permissions per agent"; o kairos-forge **checa isso automaticamente**. Raríssimo.
- **Grafo como memória compartilhada** — cobre o tipo de contexto "Memory" de T6 e o padrão de shared state entre agentes, com proveniência.
- **Disclosure progressivo por skill** — exatamente o padrão Agent Skills que o paper endossa.
- **Catraca do `otimizar`** — é um pipeline autônomo genuíno de L4: hipótese, medição, manter-ou-reverter, linhagem auditável, sentinelas contra Goodhart.
- **Roteamento de modelo por tier** — a seção Intelligent Model Routing do paper, já concebida (falta medir).

---

## 7. Três armadilhas a evitar

**1. Confundir L4 com ausência de humano.** A imagem diz "confia mais no harness do que em **revisão individual de código**" — o que sai é a leitura de cada diff, não o julgamento. O `SIM explícito` do `lancar` e o Pare e Pergunte do ADR-0015 devem **sobreviver intactos** a L4; são precisamente o "humanos definem direção, agentes implementam, handoff claro na fronteira" que o paper defende para times híbridos.

**2. Responder com o agente nº 72.** T1 é explícito: a maioria das falhas de agente é falha de configuração, não de capacidade. O retorno marginal de mais uma persona no kairos-forge é próximo de zero; o retorno de observabilidade, evals e hooks determinísticos é enorme. Os 71 agentes são a parte forte — o que falta é tudo que é determinístico ao redor deles.

**3. Declarar L4 sem o número.** Autonomia sem instrumento é chute. Enquanto o `auditar` não responder "que fração dos ciclos terminou sem intervenção", qualquer afirmação sobre o nível da fábrica é opinião. Por isso a Onda 1 vem primeiro, mesmo sendo a menos vistosa.

---

## 8. Síntese

O kairos-forge acerta com folga a metade do harness que o whitepaper chama de **instruções, tools e orquestração** — e nessas dimensões está acima do que o paper descreve como prática corrente. As três dimensões restantes — **sandbox, guardrails determinísticos e observabilidade** — estão entre fracas e ausentes, e são exatamente as que sustentam a frase que define L4.

A distância até L4 não é de agentes, personas ou skills novas. É de **quatro peças determinísticas**: um registro de execução, um arco que se fecha sozinho, hooks que bloqueiam de verdade e um eval com rubrica. Duas delas já existem em forma de projeto dentro do repositório — o loop, desenhado na ponte Hermes; o eval, existindo como dogfooding não distribuído. Promover essas duas e construir as outras duas é o trabalho.

> *"Generation is solved. Verification, judgment, and direction are the new craft."*
> — conclusão do whitepaper, e a melhor descrição do que falta ao harness da fábrica.

---

## 9. Execução — o que foi construído (v0.17.0 → v0.19.0)

As três ondas foram implementadas na mesma data desta análise. Registro do que cada lacuna
virou, para este documento continuar servindo como leitura do "antes" sem induzir a erro
sobre o estado atual.

| Lacuna | Virou | Onde |
|---|---|---|
| G1 — Observabilidade | `execucao.py` (registro por hook em 4 pontos) + `telemetria.py` (`resumo`/`sessoes`/`corroborar`) + 6ª dimensão **Autonomia** no `/auditar` | ADR-0021, v0.17.0 |
| G3 — Trajetória | Etapa 3.6 do `/validar`: cada `verificado:` é cruzado com a trajetória; não corroborado em P1 bloqueia | ADR-0021, v0.17.0 |
| G4 — Hooks pedagógicos | `guardrail.py` bloqueando em `PreToolUse`/`PostToolUse` (comando destrutivo, caminho protegido, integridade da SPEC) + fallback CLI para os demais CLIs e o CI | ADR-0022, v0.18.0 |
| G2 — Arco preso na ponte | Skill `entregar` — o loop promovido para dentro do plugin, com orçamento declarado e fronteira de aprovação intacta | ADR-0023, v0.18.0 |
| G7 — Contenção de raio | Worktree por teammate quando a supervisão humana sai do caminho + reversibilidade declarada como critério de admissão da autonomia | ADR-0024, v0.18.0 |
| G4 (evals) — Evals do usuário | Skill `avaliar` (Alice) com rubrica nos cinco eixos do paper; e o eval de roteamento do próprio plugin passa a rodar headless no CI | ADR-0025, v0.19.0 |
| G6 — Gatilhos por evento | `templates/ci/` — revisar no PR, corrigir em CI vermelho (abre PR, nunca escreve na base), auditar por cron | ADR-0026, v0.19.0 |
| G8 — Fronteira estático/dinâmico | Fronteira declarada e orçamento verificado no `release.py check`, incluindo o limite de 500 linhas por skill | ADR-0027, v0.19.0 |
| G9 — Roteamento de modelo | Coberto pelo registro de execução (o tier entra na trajetória) | ADR-0021 |
| G10 — MCP/A2A | **Não implementado** — segue como opcionalidade estratégica, não lacuna | — |

Duas observações sobre o que a execução confirmou:

**A ordem importava mesmo.** Instrumentar → conter → disparar não foi preferência estética:
o `/auditar` agora recusa recomendar gatilho por evento a um projeto sem telemetria e sem
guardrail, e a tabela de nível exige **todos** os critérios de L4, não a média. Uma fábrica
com 90% de autonomia e nenhum guardrail determinístico é classificada como pipeline sem
supervisão, com essas palavras.

**A fronteira de aprovação não se mexeu.** Os cinco gates humanos — SPEC, Pare e Pergunte,
deploy, irreversível, merge — atravessaram as três ondas intactos e estão em tabela no topo
da skill `entregar`. O que saiu do caminho do humano foi a digitação do próximo comando e a
leitura de cada diff. O julgamento ficou.

**O que ainda falta para L4 não é código.** É **uso**: a dimensão Autonomia só produz número
depois de algumas semanas de ciclos registrados, e a régua de L4 exige taxa ≥ 80%, gates
verdes de primeira ≥ 70% e zero sessões com produção escrita sem gate. O harness agora
consegue medir e sustentar isso; provar é a próxima etapa, e ela roda no calendário, não no
editor.

### 9.1. O que veio depois das três ondas (v0.20 → v0.23)

Trabalho posterior, não puxado por lacuna desta análise, mas que toca a mesma tese e por
isso fica registrado aqui:

| Versão | O que | Relação com o L4 |
|---|---|---|
| v0.20 | Skill `diagnosticar` + `diagnostico.py` (ADR-0028) | Porta de entrada para sistema existente — L4 não é só para greenfield |
| v0.21 | `ciclo.py`, a máquina de estados do arco (ADR-0029) | Transição decidida por código; o arco deixa de depender do agente lembrar |
| v0.22 | Conjunto selado + digest, recusa na trajetória, detecção em voo (ADR-0030) | Fecha o Goodhart do artefato e dá a primeira ação **durante** o problema |
| v0.23 | Higiene do juiz, gold set de comportamento, faixa de raio (ADR-0031) | Ataca a frase do L4 diretamente |

A v0.23 merece a nota. O L4 diz *"o time confia mais no harness do que em revisão
individual de código"* — e confiança, dita assim, é sentimento. A faixa de raio de explosão
troca a pergunta que o gate faz (**"quanto custa desfazer?"** no lugar de *"quão confiante
estou?"*), e a taxa de reversão dá o sinal atuarial que sustenta a resposta. É a diferença
entre confiar porque o número deu verde e confiar porque o histórico da área diz que
verde ali significa alguma coisa.

O que a v0.23 explicitamente **não** faz é o passo seguinte que a literatura de eval
engineering sugere — merge automático quando o gate passa. Integração continua sendo
decisão do dono do repositório (ADR-0023). L4 é a fábrica merecer a confiança; entregá-la
é escolha de quem instala.
