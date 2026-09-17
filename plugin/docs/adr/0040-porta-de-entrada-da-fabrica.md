# ADR-0040 — Porta de entrada da fábrica: triagem por issue, POC descartável, `DESIGN.md` e teto de apetite

- **Status:** aceito
- **Data:** 2026-09-17
- **Versão:** v0.33.0

## Contexto

O ADR-0039 absorveu do *TLC AI Dev Flow* a estação de verificação. Este absorve o que a
aula que apresentou aquelas skills (*A Próxima Fase da Fábrica de Software Agêntica*, Tech
Leads Club, set/2026) mostra sobre **por onde o trabalho entra** — e o diagrama da "fábrica
V2" deixa claro o que o forge não tinha: entre o Backlog e o Research existe uma coluna
**Triagem**, feita por agente, e o item só anda porque alguém o moveu.

Hoje a fábrica acorda de cinco jeitos: skill digitada, PR aberto, CI vermelho, cron e
mensagem no Telegram via Hermes (ADR-0019/0026). Não existe "issue criada → classificar →
planejar → construir". A demo da aula (Triagem → confiança alta → plano → "To do automático"
→ implementação → PR) é literalmente o `/entregar` disparado por issue; o arco existe com
máquina de estados e orçamento (ADR-0029), o que falta é a estação de entrada.

Mais quatro pontos da aula, cruzados com o plugin:

| Da aula | O que o forge tinha | A lacuna |
|---|---|---|
| Branch de POC: "dá uma missão e credenciais, deixa tentar sozinho; depois estuda a POC, planeja e implementa de verdade" | `rodar debate` para decisão travada; worktree por teammate (ADR-0024) | Nenhum modo exploratório. Feature incerta ia direto para o `/especificar`, que interroga sobre o que ninguém ainda tocou |
| `DESIGN.md` (getdesign.md) como formato padrão do sistema de design, aplicado e verificado com Playwright | `/desenhar` cita "o design system do projeto" sem convenção de arquivo | Pablo não tinha onde ler nem onde escrever o sistema; `desenhar verificar` conferia a feature, não a consistência com o sistema |
| Teto de tamanho de task: ~1,5 semana de trabalho humano; acima disso o agente planeja sobre o que ainda não existe | Apetite (tarde, semana, ciclo — ADR-0015) | Sem teto: apetite "ciclo" virava uma SPEC só |
| Discovery consulta MCPs internos (banco, métricas) antes de perguntar ao humano; design doc no Notion, task no Linear com link; o agente segue os links | Grafo e ai-memory consultados antes da entrevista (ADR-0009/0010) | Nada sobre tracker, board ou dados vivos do projeto; a SPEC não registrava de onde o pedido veio |

Um ponto de tensão, registrado para não ser reaberto: a aula diz que microtasks de 1 a 2
horas viraram overhead. O `modelo-spec.md` exige tarefas de no máximo 1 dia — mas essas
tarefas são a **unidade de posse e paralelismo do quadro** (`quadro.py`), não tarefas para
humano. A "task" da aula é a SPEC inteira; o apetite é o tamanho dela. As duas escalas
convivem, e agora o texto diz isso.

Sobre "o que commitar": o instrutor diz que depende do contexto e que dev solo ou monorepo
mantém tudo no repo. O forge escolheu repo como fonte da verdade (ADR-0009/0010) e mantém;
o que muda é a SPEC poder apontar por link para um design doc externo quando o time revisa
lá, com o contrato (requisitos, plano, matriz) continuando no repo.

## Decisão

**1. `templates/ci/kairos-forge-triar.yml` — a estação de triagem.** Issue aberta ou
reaberta (ou rotulada `forge:triar` pelo humano) é lida por Laura e Joana e recebe **um**
de quatro rótulos: `forge:pronto` (escopo claro, critério verificável, Pequeno), `forge:precisa-spec`
(feature ou Médio+), `forge:falta-informacao` (Pare e Pergunte — o comentário lista as
perguntas, com default quando reversível) ou `forge:aguardar` (depende de outra coisa). O
rótulo é **fila, lock e pausa** ao mesmo tempo: quem consome o backlog filtra por ele; issue
que já tem rótulo `forge:*` não é triada de novo, então dois agentes nunca pegam a mesma; e
o workflow **nunca aplica `forge:construir`** — esse é do humano, e movê-lo é a aprovação de
intenção, a mesma fronteira do ADR-0023. Só escreve rótulo e comentário, permissão mínima,
uma execução por issue, timeout, pula sem credencial (ADR-0026). Sobre GitHub Issues porque
o forge é MIT genérico; Linear, Jira e Notion entram pela seção do `CLAUDE.md` do projeto
(item 5), que diz ao agente onde está o backlog e que ele segue links via MCP.

O consumidor de `forge:construir` — o arco `/entregar` headless disparado por rótulo —
**não entra aqui.** Entra quando o arco headless tiver trajetória medida em projeto real;
a régua é a dimensão Autonomia do `/auditar`, e a direção é o kairos-symphony dirigindo o
contrato do ADR-0034.

**2. `rodar explorar <missão>` — POC descartável em worktree.** Para feature incerta, o
usuário dá uma missão, os limites (tempo-box, credenciais, o que não tocar) e a fábrica
tenta sozinha em `.worktrees/poc-<slug>`, branch `poc/<slug>`. Saída obrigatória:
`docs/pocs/POC-<slug>.md` — o que funcionou, o que não, decisões que a tentativa revelou,
custo, e o que jogar fora. O código da POC **nunca vira PR**: o `/especificar` consome as
notas, não o código, e o `guardrail.py` bloqueia `gh pr create` em branch `poc/*`. É o ADR-0024
aplicado ao discovery: POC em worktree é a mudança mais reversível que existe.

**3. `DESIGN.md` na raiz é o sistema de design; `docs/design/DESIGN-NNN.md` é a feature.**
Adotado o formato do getdesign.md (cores, tipografia, espaçamento, componentes), dono
**Pablo**. `/onboardar` detecta a ausência num projeto com UI e sugere criar; `/desenhar`
reusa do `DESIGN.md` na seção de componentes (novo exige justificativa) e o modo `verificar`
confere a implementação contra os dois — a feature e o sistema.

**4. Teto de apetite.** Apetite **ciclo** (mais de ~1,5 semana de trabalho humano
equivalente) não vira uma SPEC: vira SPECs encadeadas, cada uma com fatia fim a fim própria
(ADR-0039). Acima disso o agente planeja sobre o que ainda não existe e decide demais no
escuro. E a distinção de escalas fica escrita: tarefa de ≤ 1 dia é unidade de posse do
quadro, não microtask para humano.

**5. Origem, tracker e dados vivos no `/especificar`.** A entrada pode ser uma issue ou card
(`especificar #123`): o agente lê via CLI ou MCP, trata como descrição do usuário e registra
**Origem** na SPEC (issue, card, link do design doc externo). Antes de perguntar ao humano
o que a máquina sabe, consulta MCPs de dados do projeto quando existem (banco, métricas,
tracker). O `CLAUDE.md.template` ganha a seção **Porta de entrada**: qual backlog, que o
formato de tarefa é o da SPEC (outras skills instaladas não mudam o formato), onde vive o
design doc, e os rótulos de triagem.

**6. Vocabulário para quem chega da aula.** O `docs/inicio-rapido.md` ganha a tabela PRD /
Design Doc / RFC / ADR / task → o que é no forge, para o leitor reconhecer o plugin sem
tradução.

## Consequências

| O que | Antes | Depois |
|---|---|---|
| Entrada por issue | não existia | `triar.yml`: um rótulo, lock, pausa humana |
| Feature incerta | `/especificar` no escuro | `rodar explorar` → notas de POC → `/especificar` |
| Sistema de design | "o design system do projeto" | `DESIGN.md`, dono Pablo, verificado |
| Apetite ciclo | uma SPEC | SPECs encadeadas |
| Origem do pedido | não registrada | campo Origem na SPEC |
| Gatilhos em `templates/ci/` | 3 | 4 |

**Positivas**

- A fábrica passa a ter a coluna que faltava no diagrama V2, sem abrir mão da fronteira de
  aprovação: o humano continua movendo o item.
- POC deixa de ser "vou tentar aqui rapidinho" na branch de trabalho.
- Pablo ganha artefato próprio, e o `verificar` ganha o que conferir.

**Negativas e limites, declarados**

- **A triagem é um prompt.** Classificação errada é possível; por isso o rótulo é
  reversível, o comentário mostra o raciocínio e `forge:triar` re-tria. Sem trajetória de
  CI (ADR-0021 não roda em Actions), a taxa de acerto se mede à mão até o arco headless
  chegar — e o `/auditar` não pontua o gatilho além do "existe".
- **Só GitHub Issues sai da caixa.** Linear/Jira/Notion dependem de MCP do usuário; o
  template diz ao agente onde olhar, não faz a integração.
- **POC em worktree exige `.worktrees/` no `.gitignore`** e disciplina de tempo-box; o
  bloqueio de PR é determinístico, o tempo-box é prosa.
- **`DESIGN.md` não é gerado.** O plugin adota o formato; criar o arquivo é do Pablo (ou do
  `npx getdesign.md`, ferramenta de terceiro fora do plugin).
- **O teto de apetite é julgamento da Laura.** "1,5 semana de trabalho humano equivalente"
  é a régua do instrutor; a fábrica não mede isso, declara.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Triagem que já dispara o `/entregar` (o "To do automático" da aula) | O arco headless não tem trajetória medida em projeto real; ligar entrada automática a construção automática sem instrumento é o pipeline sem supervisão que o `templates/ci/README.md` avisa. Fica como próximo passo, com rótulo reservado |
| Triagem por tracker externo (Linear) em vez de GitHub Issues | Forge é MIT genérico; Issues é o que todo repo tem. Os demais entram por MCP e pela seção do `CLAUDE.md` |
| POC como skill própria (`explorar`) | Skill nova exige bump minor e entrada no roteamento da Laura; como modo do `rodar` reaproveita a orquestração em primeira pessoa e a tabela de modos que já existe (`debate` é o precedente) |
| `DESIGN.md` gerado pelo `/onboardar` | Extrair sistema de design de código é trabalho de Pablo com julgamento; gerar esqueleto vazio é placeholder, que o Pare e Pergunte proíbe |
| Tarefas do plano maiores (a "task" da aula) | Confunde as escalas: a tarefa de ≤ 1 dia é a unidade de posse do quadro; o tamanho da aula é o apetite da SPEC, e o teto entra lá |
| Campo `origem` na fence `kairos-critica`/`kairos-validacao` | Muda o contrato assinado (ADR-0034) por metadado que o cabeçalho da SPEC carrega igual |
