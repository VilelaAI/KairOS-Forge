# ADR-0043 — Juiz cego, selado que não vaza e veredicto com contraste

- **Status:** aceito
- **Data:** 2026-10-19
- **Versão:** v0.36.0

## Contexto

Em outubro de 2026 o Google Research publicou o **Harness²** (*Recursive Agent Harnessing
for an Open World*, arXiv 2610.14224, Apache 2.0, v0.1.0). É um framework de pesquisa que
melhora o harness em volta de um modelo de pesos fixos. Harness, no sentido deles, é tudo o
que cerca o modelo: prompt, guardrails, memória, orientação de ferramenta, subagentes,
skills, scripts e plugins. São dois laços:

- **Por tarefa (Propose–Probe–Compose).** A partir de execuções de referência, dois
  propositores editam o harness em separado: o INV cuida de *como o agente trabalha*, o
  DOM de *o que um especialista sabe*. Cada candidata roda na mesma tarefa, e um
  compositor monta o harness final pelo contraste entre as trajetórias, sem gabarito.
  "Manter a base" é resposta válida.
- **Entre tarefas.** Uma reflexão grava numa biblioteca por domínio o harness adotado e no
  máximo uma lição (`cue`, `lesson`, `evidence`, `confidence`), que as tarefas seguintes
  do domínio leem antes de propor.

Pela definição deles, o forge **é** um harness, e os dois executores que eles suportam
(OpenCode e Codex) são formatos que o `sync-multi-cli.py` já gera (ADR-0035):

| Componente do Harness² | No forge |
|---|---|
| system prompt | `CLAUDE.md`/`AGENTS.md`, rule `alwaysApply` do Cursor |
| guardrails | `scripts/guardrail.py` + `.agents/guardrails.json` |
| memory | `.agents/memory/`, `contextos/`, `.agents/grafo/` |
| tool guidance | allow-lists das personas, instruções de uso dos scripts nas skills |
| subagents | `agents/` |
| skills | `skills/` |
| scripts | `scripts/*.py` |
| plugins (middleware) | `hooks/hooks.json` |

**A tensão que define o recorte.** O laço do Harness² é o agente reescrevendo o próprio
harness a partir da própria trajetória. É o auto-graft que o ADR-0037 recusou, e o que o
ADR-0022 proíbe: o agente não escreve o próprio medidor nem a própria regra. Guardrails e
plugins, editáveis lá, são piso aqui. O laço não entra. Os mecanismos que o tornam
confiável sem gabarito, sim, e a auditoria encontrou três lacunas concretas:

| Mecanismo do Harness² | O que o forge tinha | A lacuna |
|---|---|---|
| Seleção às cegas: candidatos viram `A`, `B`, `C` por embaralhamento semeado (`assign_ids`, semente `sha1(tarefa\|k\|modo)`); na variante *mixed* a base entra no pool com o aviso de que escolhê-la é esperado; o juiz só roda depois da seleção gravada | Cinco regras de higiene do juiz no `/avaliar`: família diferente, painel, checável vai para código, versão pinada, nunca recompensar forma (ADR-0031) | O juiz sabia qual saída era a baseline e qual era a candidata, e a expectativa de quem pede o eval é que a candidata seja melhor |
| `assert_no_grader_verdicts` e `leak_globs`: alarme que aborta a execução se algo do avaliador chegar ao contexto do modelo. O próprio `docs/EXPERIMENTS.md` registra que, num teste de validação, um executor Codex **baixou a rubrica da tarefa sem ninguém pedir** | "O gold set fica fora do contexto" e "só o selado aprova" (ADR-0030), em prosa; o `release.py check` valida a forma dos gold sets, não o vazamento | Nada notava um caso selado colado como exemplo numa persona, numa skill ou num teste, nem o mesmo caso nos dois arquivos |
| Reflexão com veredicto por edição — `helped`, `hurt`, `no observed effect`, `confounded`, este o default quando nada isola a edição — e lição só com contraste, senão `NO_ENTRY`. *"Adoption alone never establishes that an edit helped"* | O `/otimizar` atribui por uma mudança por rodada; o `/evoluir` lê a trajetória antes da entrevista (ADR-0037); `.agents/memory/` só tem formato de incidente | O `/evoluir` escolhia a próxima evolução sem julgar se a anterior funcionou: a capacidade entrava na fábrica e nunca recebia veredicto |

## Decisão

**1. Juiz cego à versão — sexta regra de higiene do `/avaliar`.** Quando o juiz compara
mais de uma versão (baseline × candidata, variantes de prompt, dois modelos), as saídas
chegam como `A`, `B`, `C`, sem nome, commit ou rótulo que denuncie a origem. A ordem é
embaralhada com semente `sha1(<id do caso>|<digest do artefato>)`, usando o digest que o
passo 3.5 já registra: a mesma versão dá a mesma ordem em toda reexecução, e versão nova
reembaralha. A baseline está sempre no pool, e a instrução do juiz diz que preferi-la é
resultado válido. O mapa letra → versão vai para `evals/<slug>/mapa-YYYY-MM-DD.tsv`, fora
do diretório do juiz, e só abre depois que o veredicto de cada caso foi gravado. A receita,
em stdlib, está em `skills/avaliar/references/higiene-do-juiz.md`, e o relatório ganha a
linha **Juiz cego**.

**2. `prova.py selado` — a terceira prova do `prova.py`.** Mesma família do ADR-0039: gate
verde que não prova nada. Cada string de cada caso de `evals/<slug>/selado.jsonl` (menos o
`id`) vira um trecho normalizado (minúsculas, só palavras, espaço único). Trecho com seis
ou mais palavras é procurado, com fronteira de palavra, em todo arquivo de texto do
repositório, menos `evals/` (o eval e os relatórios), `.agents/execucoes/` (a trajetória de
quem rodou o eval) e diretórios de dependência. O `gold.jsonl` irmão é lido à parte: caso
selado repetido no visível também é vazamento. Sai 1 com achado ou com linha ilegível, e
sai 0 dizendo "nada a proteger" quando não há selado. Roda no `release.py check` (o CI do
plugin) e entra no passo 7 do `/avaliar` como gate no CI do projeto do usuário. A suíte
`scripts/tests/test_prova.py` cobre o que acusa e o que libera.

Medido antes de decidir: com os 82 casos reais dos dois gold sets do plugin tratados como
selados, o alarme não acusou nada no repositório inteiro e rodou em cerca de um segundo.
Nenhum falso positivo para afrouxar.

**3. Veredicto da evolução anterior no `/evoluir`, e lição só com contraste.** Antes de
escolher a próxima evolução, a skill abre o EVOL mais recente e escreve um veredicto entre
quatro — `ajudou`, `piorou`, `sem efeito observado`, `confundido` —, com o contraste que o
sustenta. `confundido` é o default quando outra coisa mudou na mesma semana ou só uma
ocorrência sustenta a diferença; adoção não é evidência; `piorou` volta à mesa como
candidata da semana. Para isso o registro EVOL ganha duas seções: **Linha de base**
(medida no dia da escolha) e **Veredicto da evolução anterior**. A lição que transfere
sobe para `.agents/memory/` com quatro campos (quando reconhecer, como aplicar, evidência,
confiança), ou o registro diz `sem lição`. O `/otimizar` nomeia o resultado da rodada com
duas mudanças (`confundido`) e usa o mesmo formato de lição, com as rodadas da linhagem
como evidência. O índice `MEMORY.md` criado pelo `/onboardar` passa a descrever os dois
formatos.

É o laço entre tarefas do Harness² com o humano dentro: o laço fecha, mas quem escreve o
veredicto é o ritual semanal com o usuário, não um agente sobre o próprio traço. O que o
ADR-0037 recusou continua recusado.

## Consequências

| O que | Antes | Depois |
|---|---|---|
| Juiz comparando baseline e candidata | sabia qual era qual | vê `A`/`B` em ordem semeada; mapa aberto depois do veredicto |
| Caso selado colado numa persona ou skill | passava | `prova.py selado` sai 1; o `release.py check` também |
| Mesmo caso no visível e no selado | passava | acusado como vazamento |
| Evolução da semana anterior | nunca recebia veredicto | veredicto com contraste antes da próxima escolha |
| Lição em `.agents/memory/` vinda de mudança | sem formato | quatro campos, ou `sem lição` |
| Higiene do juiz | 5 regras | 6 |

**Positivas**

- A regra "só o selado aprova" ganha dente: o caminho mais curto do caso até o sistema
  avaliado, a cópia, passa a ser verificado por código.
- O juiz que compara versões fica reproduzível: mesma semente, mesmas letras, e quem
  audita refaz a rodada.
- O `/evoluir` passa a medir a si mesmo: capacidade que não mudou nada aparece como
  `sem efeito observado`, em vez de ficar na fábrica por inércia.

**Negativas e limites, declarados**

- **O alarme pega cópia, não paráfrase.** Quem reescreve o caso selado com outras palavras
  passa; quem mede esse ajuste é a divergência visível × selado do relatório, que já
  existia. Trecho com menos de seis palavras não é comparado e sai contado como "curto",
  nunca como "limpo".
- **O alarme não sabe a direção.** Um caso selado escrito copiando uma frase da skill é
  acusado igual a uma skill que copiou o caso. Nos dois sentidos o caso mede leitura e não
  comportamento, e a correção é a mesma: reescrever o caso.
- **No repositório do plugin, hoje, o alarme não tem o que guardar.** Os dois gold sets do
  plugin não têm divisão selada. O check fica armado para quando tiverem; dividir é
  trabalho da Alice, não deste ADR.
- **Juiz cego é procedimento.** Nada impede quem conduz o eval de contar ao juiz qual é a
  versão nova. A receita torna a rodada conferível (semente e mapa), não inviolável.
- **O veredicto semanal depende de linha de base gravada.** Os EVOL anteriores não têm, e
  a skill manda dizer isso em vez de inventar. Semana com várias mudanças sai `confundido`
  quase sempre: é o resultado honesto, e um incentivo a uma evolução por semana, que já era
  a regra.
- **Sem hooks (Codex, OpenCode), a linha de base vem de observação**, não de telemetria,
  e o contraste é mais fraco. A skill pede que se diga como vai ser observado.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Usar o Harness² como laboratório sobre o próprio forge: um `BenchmarkAdapter` com a saída OpenCode do sync como harness base e o piso congelado na superfície editável | Adiado, não descartado. Falta benchmark no formato: o `comportamento-fabrica` tem 14 casos, abaixo dos ~30 que o `/avaliar` exige, e o `roteamento-laura` é classificação de um tiro só, que refinar por caso ajustaria ao gold set. O custo é de 4k execuções e 3k sessões de melhoria por tarefa, com Vertex AI obrigatório, e o executor Codex roda sem sandbox e com rede liberada. Volta quando houver 30+ tarefas do tamanho de uma SPEC com parte selada, e a saída entra no `/evoluir` como evidência, nunca como patch |
| Refinar o harness por tarefa dentro do `/entregar` | É a fábrica reescrevendo skill ou persona no meio da feature do usuário (ADR-0022, ADR-0037), e multiplica por quatro o custo de toda entrega |
| Biblioteca de harness por domínio que se alimenta sozinha | O equivalente aqui é a memória curada, e quem sobe de camada é o humano (ADR-0010) |
| Classe no `guardrail.py` bloqueando a leitura de `selado.jsonl` | No Claude Code o avaliador (a Alice) e o sistema avaliado podem estar na mesma sessão; o hook não distingue quem lê e bloquearia o próprio avaliador. O vazamento que persiste é o que fica escrito na instrução, e esse é verificável no repositório |
| Comparar por similaridade (n-gramas, embedding) em vez de cópia literal | Pegaria paráfrase, ao custo de falso positivo e de dependência. A divergência visível × selado já mede o ajuste sem rastro literal; a regra cresce por evidência |
| Importar o código do Harness² | A Apache 2.0 permitiria, com aviso, mas o forge é plugin stdlib sem runtime (ADR-0001), e o que se aproveita cabe em poucas dezenas de linhas |
| Portar já a tabela do "componente mais barato que resolve" (o template INV) e a separação fato do projeto × procedimento | Ficam para um corte seguinte. Entram se os veredictos das evoluções mostrarem a escolha do tipo de componente como causa recorrente de `sem efeito observado` |
