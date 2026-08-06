# Análise — "The Agentic SDLC Handbook" vs. kairos-forge

**Data:** 2026-08-06
**Fonte analisada:** Meppiel, D. — *The Agentic SDLC Handbook* (danielmeppiel.github.io/agentic-sdlc-handbook; 23 capítulos, 2 apêndices e 4 estudos de caso, ~830 KB de fonte Quarto, CC BY-NC-ND). Bloco de praticantes lido na íntegra (ch11–ch22), mais ch07 (economia) e ch13 (PROSE).
**Versão do kairos-forge analisada:** v0.27.2 (commit `1a5a489`)
**Objetivo:** separar o que o handbook confirma do que ele expõe como lacuna, e propor só o que tem alavancagem.

---

## 1. Por que este handbook importa depois do whitepaper Day-1

A análise anterior (`2026-08-01`) partiu do whitepaper do Google, que **argumenta uma tese**: o harness domina o comportamento, agente = modelo + harness, sem eval é vibe coding. Este handbook é de outro gênero — é **catálogo de referência**. Ele não tenta convencer que o harness importa; ele assume isso e passa 400 KB nomeando as peças: quatro partes da máquina, quatro fases do carregamento, cinco modos de binding, dezenove anti-padrões, um Rosetta Stone que traduz padrão agêntico para GoF e sistemas distribuídos.

Para o kairos-forge isso muda a natureza do que dá para extrair. Do whitepaper saiu **direção** (observabilidade, guardrails, arco fechado — v0.17→v0.27). Deste handbook sai **vocabulário e régua**: nomes para mecanismos que a fábrica já tem sem nome, e testes falseáveis para mecanismos que a fábrica tem sem verificação.

Vale registrar uma coincidência que não é coincidência: o handbook foi produzido por um pipeline agêntico de 11 personas com revisão adversarial (CTO Proxy, Dev Lead Proxy, Fact Checker) e **checkpoint de autor no fim** — a mesma forma do `/revisar` + `/avaliar` + fronteira de aprovação do `/entregar`. Duas equipes que não se conhecem chegaram no mesmo desenho. Isso é evidência fraca de que o desenho está certo, mas é evidência.

---

## 2. Onde o handbook confirma decisões já tomadas

Não é auto-elogio: é o que estabelece que as lacunas da seção 3 são lacunas de verdade, e não "ainda não começamos".

| O que o handbook prescreve | Onde o kairos-forge já faz | ADR |
|---|---|---|
| *"The trail must be on a surface the agent cannot rewrite"* (Audit Trail, ch19) | `.agents/execucoes/` e `.agents/guardrails.json` inegociáveis — o agente não escreve o próprio medidor | 0022 |
| *"Agent self-reports are generated text, not system logs"* (Trust Fall, ch20 — "o padrão mais perigoso do capítulo") | Corroboração de trajetória no `/validar`: o `verificado:` do relatório é conferido contra o registro de execução | 0021 |
| *"Operators of long-lived agentic systems should plan to install all three [Audit Trail, Agent Stack Trace, Lockfile] on day one; retrofitting them after the first incident is an order of magnitude more expensive"* (ch19) | Telemetria + guardrails + assinatura de contratos entraram antes do primeiro incidente, não depois | 0021/0022/0034 |
| **Tool Subset** (Interface Segregation aplicado a ferramentas, ch19) | Allow-list explícita por agente — regra 4 do CLAUDE.md, verificada no `check-agent-security.py` | — |
| **Panel** + os três anti-padrões herdados (`PANEL-WITHOUT-SYNTHESIS`, `PANEL-IN-ONE-CONTEXT`, `IMBALANCED PANEL`) | Crítica adversarial da SPEC com dois críticos **independentes** cobrados pelo parser; painel de juízes no `/avaliar` | 0033/0031 |
| **Wave** + `STAGE COLLAPSE` (*"I will plan as I go" — o plano vira post-hoc e infalseável*) | Planejamento em fases: os checkpoints do `/especificar` viram estado porque prosa não para um runner headless | 0033 |
| **Supervised Execution, forma forte** — *"the agent never holds the write capability"* | `guardrail.py` em `PreToolUse` bloqueia antes da chamada; `gh pr create` recusado fora de estado | 0022/0029 |
| **Model Router** e **Gradient Workflow** (ch19/ch07) | Roteamento de modelo por tier no `/mobilizar` (rápido/padrão/preciso) | 0013 |
| Fronteira estático × dinâmico como decisão de arquitetura versionada; disclosure progressivo | Orçamento estático verificado no `release.py check`, limite de 500 linhas por skill | 0027 |
| *"Every wave ends with green tests"* / checkpoint discipline | Gates com orçamento e escalação decididos por código no `ciclo.py` | 0029/0033 |
| **Schema-Checked Transformer** (Adapter no seam) | Fences `kairos-*` + `contrato.py` como módulo puro sem I/O | 0032/0034 |

Onze prescrições, onze já implementadas. O handbook não tem nada a ensinar ao forge sobre *o que* construir. Tem sobre *como saber se o que foi construído cobre o que precisa cobrir* — que é a seção seguinte.

---

## 3. As sete lacunas que valem trabalho

### L1 — Os gates da fábrica nunca foram classificados por modo de falha

**O que o handbook diz (ch16).** O espaço de desenho de gates fecha num 2×2: **quem** dá o veredicto (interno ao processo do agente × externo) por **como** dá (programático × julgamento). Quatro células, e cada uma pega bem *uma* forma de falha e mal as outras três. O capítulo lista os quatro erros de casamento, e o primeiro é o que mais dói:

> *"Using programmatic-internal to catch goal drift. The test suite is green. The lint passes. The agent has implemented the wrong feature. (…) A team that responds to a wrong-feature incident by adding more tests is misreading the failure."*

E a regra de seleção: *"pick the cell that matches the failure mode you are guarding against, not the first gate that fits."*

**Onde o forge está.** A fábrica tem, contados: gate de teste (`validar`), gate de revisão (`revisar`), gate de crítica adversarial da SPEC (`criticar`), guardrails determinísticos em quatro classes, prova de cobertura no `contrato.py`, rubrica de eval no `/avaliar`, faixa de raio de explosão, e a fronteira de aprovação humana do `/entregar`. Oito mecanismos. **Nenhum documento diz qual célula cada um ocupa nem qual falha cada um foi feito para pegar.** Sem esse mapa, não dá para responder a pergunta que importa: *que modo de falha está descoberto?*

Um exemplo concreto de por que isso não é exercício de taxonomia. O `contrato.py` roda como hook — o parser está **fora** do controle do agente. Isso o torna programático-externo, a célula mais cara de construir e a que o handbook diz ser a mais rara na prática. A fábrica tem uma e não sabe que tem. Do outro lado: goal drift ("implementou a feature errada com todos os gates verdes") é coberto pelo `/validar` via rastreabilidade SPEC ↔ artefato, mas isso é julgamento-interno — e o handbook avisa que julgamento-interno é justamente o que não pega violação de forma. Os dois se complementam por acidente feliz, não por desenho declarado.

**Proposta.** Uma tabela canônica de gates — célula, modo de falha alvo, o que ele explicitamente **não** pega — em `docs/` ou num ADR, e um critério de admissão: *gate novo declara sua célula, ou não entra.* Custo: um documento e uma linha no `release.py check` conferindo que todo gate declarado no `ciclo.py` aparece na tabela. Ganho: a próxima falha em produção tem endereço antes de virar "vamos adicionar mais testes".

---

### L2 — A taxa de autonomia tem teto, não tem piso

**O que o handbook diz (ch17).** A taxa de intervenção humana é métrica de duas caudas:

> *"Rates significantly above 20% may indicate underspecified plans. **Rates below 5% warrant scrutiny — the work may be too simple for multi-agent orchestration, or review may be insufficient.**"*

**Onde o forge está.** A dimensão Autonomia do `/auditar` (ADR-0021) pontua assim:

```
Taxa de autonomia (ciclos sem intervenção ÷ ciclos):
  < 20% = 0 · 20–49% = 2 · 50–79% = 4 · ≥ 80% = 6
```

A escala é **monotônica pra cima e aberta no topo**. Uma fábrica que reporta 100% de autonomia por 30 dias tira nota máxima. O handbook diz que essa fábrica ou está fazendo trabalho trivial ou não está olhando — e as duas hipóteses são ruins.

Isso contradiz a própria doutrina da casa, escrita três parágrafos abaixo na mesma skill: *"Recusa é sinal, não vitória. O bloqueio ter funcionado não zera o fato de o agente ter tentado."* Recusa crescente já não pontua. Intervenção **zero**, que é o espelho exato, pontua máximo.

**Proposta.** Fechar a escala no topo e cruzar com o raio de explosão:

- Faixa saudável 80–95%; **≥ 96% com faixa de raio 2 ou 3 no período não pontua** — pede nota no relatório (*"autonomia alta sem trabalho de risco: verifique se a revisão está acontecendo"*).
- Autonomia alta **com 100% dos ciclos em faixa 1** deixa de ser autonomia e vira volume: a fábrica está entregando texto de UI e teste, não decisão.

Custo: uma linha na rubrica do `/auditar` e um campo derivado no `telemetria.py resumo` (faixa predominante do período — o dado já está no relatório de revisão). Ganho: a métrica que mede autonomia para de premiar cegueira.

---

### L3 — `description` é a API, e mudar API é breaking change

**O que o handbook diz (ch21).** A regra é explícita e tem tabela de SemVer:

> *"The public surface is the description in the `SKILL.md` frontmatter (…). Rewording the description — *activate when reviewing code* becomes *use whenever an agent is asked about code* — changes which threads the skill binds in. That is a breaking change."*

| Mudança | Regra |
|---|---|
| Editar o corpo sem tocar description | Patch |
| Adicionar slot ou asset | Minor |
| **Reescrever o critério de ativação da description** | **Major** |

**Onde o forge está.** A regra da casa (CLAUDE.md) diz:

> *Mudar prompt de agente ou skill → bump patch (0.4.x) + rodar sync*

Isso trata corpo e description como a mesma coisa. **São coisas diferentes:** o corpo é implementação, a description é o que decide se a skill é chamada. E o forge sabe disso melhor que a maioria — tem um eval dedicado (`evals/roteamento-laura/`) cuja única função é medir se as descriptions roteiam certo, e uma regra que manda rodá-lo *"se mudou prompt da Laura, `description` de agente ou roteamento"*.

Ou seja: a regra de versionamento e a regra de eval **discordam sobre a mesma mudança**. A do eval está certa; a de versionamento está frouxa. E nenhuma das duas é verificada — mudar uma description e commitar com patch passa hoje.

**Proposta.** Duas linhas de código e uma de doc:

1. `release.py check` compara as `description:` de `skills/*/SKILL.md` e `agents/*.md` contra a última tag. Mudou description → exige bump **minor** no mínimo e recusa patch.
2. A mesma checagem exige evidência de que o eval de roteamento rodou (arquivo de resultado com hash do gold set — o `/avaliar` já sela conjunto e digest, ADR-0030).

Custo: baixo, reaproveita máquina existente. Ganho: fecha o único caminho pelo qual o roteamento da fábrica pode mudar sem ninguém medir. É a mesma tese do ADR-0034 (*"contrato que ninguém verifica é promessa"*) aplicada à superfície que o ADR-0034 não cobriu.

---

### L4 — Overlap essencial sem fonte única: a deriva que ainda não aconteceu

**O que o handbook diz (ch21).** O capítulo abre com duas skills que carregam cada uma sua cópia do mesmo checklist de revisão, editadas por pessoas diferentes com três meses de distância, e que numa segunda-feira dão **veredictos opostos sobre o mesmo diff**. O diagnóstico:

> *"Coincidental overlap — two unrelated skills that happen to use a similar phrase — is fine (…). Essential overlap — content that is supposed to be the same in both places because the team has one position on it — is not. The cure (…) is always the same: extract a package, declare a dependency, delete the copy."*

**Onde o forge está.** A faixa de raio de explosão (ADR-0031) está definida em tabela em `skills/revisar/SKILL.md:67-71` e reafirmada em consequências operacionais em `skills/entregar/SKILL.md:233-238`. **Hoje as duas concordam** — conferi. Nada garante que continuem concordando. É exatamente a cena de abertura do capítulo, no estágio anterior ao incidente.

O mesmo vale para "Pare e Pergunte" (ADR-0015), reescrito em seis skills e dois agentes, e para o vocabulário de gates que já envelheceu calado uma vez — a mensagem do guardrail e a linha do painel listavam `validar` e `revisar` depois que o ADR-0033 acrescentou `criticar`, e isso só foi pego percorrendo o roteiro de teste local (commit `1a5a489`). A cura aplicada lá foi a certa: derivar do estado em vez de repetir. Falta generalizar.

**Proposta.** Declarar um conjunto pequeno de **blocos canônicos** — faixa de raio, condição de parada, definição dos gates — com fonte única em `skills/<dona>/references/` ou em `templates/`, e as demais skills apontando por link em vez de reescrever. Onde a repetição for inevitável (o CLI não segue link em toda situação), um check de deriva no `release.py check`: hash do bloco canônico × hash das cópias, divergiu sem reassinar → falha, na mesma forma do `contratos/ASSINATURA.json`.

Custo: médio — exige inventariar o overlap antes de decidir o que é essencial. Ganho: o forge já centralizou o contrato **legível por máquina** (`contrato.py`); isto centraliza o contrato **legível por humano**, que é onde a deriva de fato acontece.

---

### L5 — "Um arquivo, um agente por onda" é convenção, não verificação

**O que o handbook diz (ch17).** É a regra que ele chama de mais importante do paralelismo, e o motivo é mecânico:

> *"Most agent tooling edits files using string matching (…). If Agent A modifies `install.py` and then Agent B tries to edit the same file, the text Agent B expects to find has already changed. The edit fails silently or produces corrupted output. **This is not a theoretical risk. It is the most common failure mode in parallel agent execution.**"*

**Onde o forge está.** O `/mobilizar` faz quase tudo certo: cada task declara `Arquivos:` no corpo, há tabela de propriedade de caminho por agente, e o passo 4 manda auditar **independência falsa** — *"escrevem no mesmo arquivo (…) conflito de escrita exige aresta (ou serialização via file ownership) mesmo com zero dado cruzando."*

O texto está correto e nada o verifica. É julgamento — e a própria skill escreveu, três parágrafos antes, por que julgamento não basta:

> *"Isto era julgamento e virou número por um motivo: **julgamento funciona enquanto tem alguém olhando.** Em execução conduzida por script, 'não exagere no paralelismo' não impõe nada — 6 impõe."*

O teto de 6 virou número. A propriedade de arquivo não. É a mesma lacuna, na regra que o handbook considera mais crítica das duas.

**Proposta.** Um subcomando determinístico — `ciclo.py ondas --verificar` ou equivalente — que lê os `Arquivos:` declarados nas tasks da onda corrente, expande os globs e **recusa a onda com interseção não vazia entre teammates**, apontando o par em conflito. Duas saídas legítimas para o autor: fundir as duas tasks num teammate, ou empurrar uma para a onda seguinte — exatamente as duas resoluções que o handbook prescreve.

Custo: baixo (parsing de campo que já existe + `fnmatch`). Ganho: converte o modo de falha nº 1 do paralelismo de "esperamos que a Laura perceba" em "o script recusa". Em CLI sem hooks, roda como check de CI via `templates/ci/` (ADR-0026).

---

### L6 — Não existe resposta para "por que minha skill não disparou"

**O que o handbook diz (ch14).** O capítulo inteiro é sobre isso, e abre com uma engenheira perdendo uma hora numa skill que estava perfeita — o problema era um `applyTo: "**/*.py"` de outro arquivo consumindo 6.200 tokens e afogando o dispatcher. A cura é dividir o carregamento em quatro fases, cada uma com **um teste falseável de um minuto**:

| Fase | Falha típica | Teste |
|---|---|---|
| Resolve | dependência fantasma | closure em dry-run |
| Materialize | arquivo no path que *este* CLI não lê | `ls` no path do harness |
| Bind | frontmatter inválido → invisível ao dispatcher | validar YAML |
| Activate | description fraca **ou orçamento estático estourado** | log verboso: "registrada, não puxada" |

**Onde o forge está.** Tem as peças e não tem o diagnóstico. `sync-multi-cli.py` é a fase Materialize (e é boa: gera `.agents/` e `.cursor/` a partir do canônico). `release.py check` mede o orçamento estático — que é a causa raiz da fase Activate. A revisão de 2026-07-25 verificou frontmatter e casing, que é a fase Bind. **Três das quatro fases estão instrumentadas, para o mantenedor, em três scripts diferentes, e nenhuma delas responde ao usuário.**

E o forge tem mais motivo que a média para se importar: ele distribui em quatro CLIs com paths e capacidades diferentes. A história de abertura do ch11 — mesmos arquivos, mesmo modelo, harness diferente, silêncio — é literalmente o modo de falha de um plugin multi-CLI.

**Proposta.** Um `scripts/carregamento.py diagnosticar` que, dado o CLI detectado, responde as quatro perguntas em sequência e para na primeira que falhar: (1) os arquivos estão no path que este CLI lê? (2) o frontmatter parseia? (3) o orçamento estático deste CLI está dentro do teto? (4) qual description casou com a tarefa? Reaproveita `sync-multi-cli.py` e `release.py check` — é embrulho, não código novo. Entra no `/onboardar` como passo de verificação e no `/auditar` como evidência da dimensão Fundação.

Custo: baixo-médio. Ganho: o suporte de "não funcionou" passa de conversa a comando.

---

### L7 — O plano está em disco, mas ninguém manda reler

**O que o handbook diz (ch15).** É a terceira alavanca da economia de atenção, e a mais contraintuitiva:

> *"The plan begins at the head of context. Twenty turns later, when it matters, it has slipped into the trough. **Re-reading the plan file pulls it back to the tail, where attention is strongest, exactly when the model needs it.**"*

O ponto não é persistir o plano — é **reler de propósito**, em momentos declarados: início de cada passo, retorno de cada spawn, depois de cada falha de ferramenta.

**Onde o forge está.** Metade feita, e a metade mais difícil. O ADR-0033 tornou as fases do planejamento **estado em disco** justamente porque prosa não para um runner headless; o `ciclo.py` é a memória durável do arco. Isso resolve *o plano sobrevive*. Não resolve *o plano volta para a cauda do contexto*: nenhuma skill instrui a reler a SPEC ou o estado da fase antes de uma decisão consequente. O `/mobilizar` roda por horas; a `entregar` atravessa três gates com rodadas de correção no meio. São exatamente as sessões em que a cabeça do contexto vira meio de contexto.

**Proposta.** A mais barata das sete: uma linha no `/mobilizar` (antes de cada fan-in) e no `/entregar` (antes de cada transição de gate) mandando **reler o estado do ciclo e o requisito da SPEC em vez de responder de memória**. O comando já existe (`ciclo.py estado --json`, ADR-0034). Complementarmente, o `execucao.py` já registra a trajetória — dá para medir se a releitura aconteceu, o que a torna verificável em vez de exortação.

Custo: trivial. Ganho: ataca patinação em sessão longa na causa, não no sintoma (o alerta de patinação do ADR-0030 detecta *depois*).

---

### Itens menores, registrados sem proposta

- **Bounded-Scope Grounding (ch16/ch19).** *"Declare what an external corpus is authoritative for."* Relevante para o grafo (`mapear-conhecimento`) e para qualquer leitura de doc externo: uma fonte carregada para responder X não vira autoridade sobre Y. O grafo já tem proveniência por entidade — falta a declaração de escopo de autoridade. Provavelmente cabe como campo no grafo, não como skill nova.
- **Forma fraca × forma forte por CLI (ch16).** O handbook manda documentar, quando se aceita forma fraca, **qual é o controle compensatório**. A tabela de limitações por CLI do CLAUDE.md já é honesta sobre a ausência de hooks e aponta o CI como caminho; falta explicitar que isso é forma fraca e nomear o compensatório por linha. Mudança de uma tabela.
- **Teste de autossuficiência (ch18).** *"Can an agent complete this task without asking me a question?"* — se não, a task não está pronta. O forge tem "Done when" e gate por task, que é vizinho, mas não o complemento. Cabe como uma linha no passo 4 do `/mobilizar`.
- **Triplete de autoria de skill (ch21): O QUÊ / COMO / OPERAÇÕES.** Estrutura de revisão para skill nova — o quê ela codifica e como se mede o sucesso; como ela compõe e qual o limite de recursão; o que a telemetria diz quando ela roda. Boa checklist para o ritual de contribuição; não é código.

---

## 4. O que **não** portar

- **APM, manifesto e lockfile de primitivas.** O capítulo 21 é excelente e resolve um problema que o forge não tem: o plugin é autocontido, com zero dependências externas de primitivas. Fecho transitivo de um grafo com um nó é o próprio nó. O que o lockfile entrega de verdade — *"qual versão da rubrica estava carregada no agente que aprovou o PR #4711?"* — o forge já entrega por outro caminho: `contratos/ASSINATURA.json` + versão do plugin no registro de execução. Adotar manifesto seria cerimônia.
- **PROSE como vocabulário.** As cinco restrições estão certas e o forge já obedece todas por outros nomes (disclosure progressivo = ADR-0027; escopo reduzido = orçamento de complexidade; composição = 71 agentes finos com processo nas skills; fronteiras de segurança = allow-lists + guardrails; hierarquia explícita = CLAUDE.md do projeto + skills + references). Importar um acrônimo concorrente fragmentaria o vocabulário da casa sem ganhar nada. Citar de onde veio a régua, sim; renomear o que já existe, não.
- **Bloco de líderes (ch03–ch08): 5 camadas, staffing, modelo operacional de custo central.** É material de organização, não de plugin. Se algum dia interessar, interessa ao kairos-ai.
- **Cache-Aware Prefix como padrão explícito.** A superfície estática do forge é ~1,9k tokens e estável (banner, rule do Cursor, template). Não há invalidador de cache para caçar. Registrar que a fronteira foi medida (ADR-0027) já cobre; virar padrão nomeado seria estrutura prematura.

---

## 5. Sequência sugerida

Ordenado por (ganho ÷ custo), não por importância:

| # | Lacuna | Custo | Onde entra |
|---|---|---|---|
| 1 | **L7** — reler plano nas transições | trivial | patch, duas linhas em skills |
| 2 | **L3** — description é breaking change | baixo | patch + check no `release.py` |
| 3 | **L2** — teto na taxa de autonomia | baixo | patch na rubrica do `/auditar` |
| 4 | **L5** — file ownership verificado por onda | baixo | minor + ADR (script novo) |
| 5 | **L1** — tabela canônica de gates por célula | baixo-médio | ADR + doc |
| 6 | **L6** — diagnóstico de carregamento | médio | minor + ADR |
| 7 | **L4** — blocos canônicos e check de deriva | médio | minor + ADR (exige inventário) |

Os quatro primeiros cabem numa `v0.27.3`/`v0.28.0` sem ADR novo — são apertos de regras existentes, e três deles fecham contradições internas do próprio repositório (regra de versionamento × regra de eval; recusa é sinal × intervenção zero é vitória; teto de onda é número × propriedade de arquivo é julgamento). Os três últimos merecem ADR porque criam mecanismo.

A leitura mais dura do handbook sobre o kairos-forge é essa: a fábrica não tem lacuna de mecanismo. Ela tem, em três lugares medidos aqui, **regra escrita que nada verifica** — e a doutrina da casa, escrita pela própria fábrica no ADR-0033, já diz o que fazer com isso.
