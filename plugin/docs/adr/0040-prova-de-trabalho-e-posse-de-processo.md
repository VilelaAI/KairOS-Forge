# ADR-0040 — Prova de trabalho, gate que não rodou e posse do processo

- **Status:** aceito
- **Data:** 2026-09-06
- **Versão:** v0.32.0

## Contexto

Três lacunas do mesmo tipo, apontadas pela [análise do pwdev-claude-marketplace](../revisoes/2026-09-06-analise-pwdev-claude-marketplace.md):
o harness aceitava uma **afirmação** onde poderia exigir um **fato verificável**.

1. **"Concluída" que o git não enxerga.** `quadro.py concluir` exigia evidência em texto e
   o resultado do gate. Nada conferia se algum arquivo mudou. JSON bem formado descrevendo
   trabalho que ninguém fez passava — e é a forma mais barata de um teammate "terminar".
   O vizinho fecha isso em dois lugares: `review-package.sh` recusa montar o pacote de
   revisão quando `base == head`, e o runner de frota pergunta ao git se o estágio deixou
   diff (`stage_produced_work`), com um preflight que recusa contrato gitignored porque
   git nunca vê path ignorado como sujo.
2. **Reprovação legítima e gate quebrado eram o mesmo `bloqueado`.** Se `npm test` não
   roda porque o banco de teste caiu, o relatório de validação não tinha como dizer isso:
   ou mentia `aprovado`, ou dizia `bloqueado` e o `ciclo.py` cobrava uma rodada de correção
   — e o laço corrigia código para consertar um ambiente. O vizinho separa `status` do
   estágio (rodou? `OK|FAILED|NEEDS_HUMAN`) de `verdict` sobre a feature, e documenta que
   um `verify` que rejeita é `OK + REJECTED`, não `FAILED`.
3. **Vaga devolvida por cima de um worker vivo.** `quadro.py varrer` (ADR-0036) bloqueia a
   tarefa vencida e libera a vaga da onda por prazo. Se o worker é um processo que ainda
   está escrevendo nos arquivos de posse, a vaga liberada é dois workers na mesma posse —
   o que a posse existe para impedir. O vizinho lança o provider como líder de grupo,
   manda TERM, espera, manda KILL, e **retém o lock** quando não prova que o grupo morreu:
   "an orphaned lock is a deliberate signal that a human must look".

E uma quarta, descoberta pela suíte do ADR-0039: `quadro.salvar` escrevia o quadro
direto, sem troca atômica. Um crash no meio deixava o arquivo que decide o que o time
lança pela metade.

## Decisão

### 1. Prova de trabalho no `concluir`

`iniciar` grava o HEAD do momento. `concluir` aceita se, e só se, uma destas valer:

- o HEAD avançou desde o `iniciar`;
- `git status --porcelain --untracked-files=all` mostra mudança sob os padrões de posse
  (pathspec `:(glob)`, para `**` funcionar);
- `--sem-diff "motivo"` foi declarado — tarefa de análise ou decisão que legitimamente
  não muda arquivo. Fica em `prova_trabalho`, ao lado da evidência.

Fora de repositório git a checagem não roda e o comando diz isso. Silêncio honesto é
melhor que achado inventado — a mesma regra do `gerados_modificados` (ADR-0037).

`adicionar` avisa quando o prefixo estático de um padrão de posse é gitignored: a prova
não vai enxergar aquele path. Ou a tarefa declara `--sem-diff`, ou o path sai do
`.gitignore`.

### 2. `executado: false` nos três contratos de relatório

Campo opcional, default `true`. `false` exige `motivo` e veredicto `nao_executado`;
`nao_executado` sem `executado: false` é incoerência recusada. Nenhuma checagem de
contagem ou cobertura se aplica — não houve gate. O `contrato.py esquema` publica o
campo; versão do contrato `1.0 → 1.1` (campo opcional novo é MENOR).

No `ciclo.py`, relatório `nao_executado` **recusa qualquer resultado** no estado de gate
e não move a máquina: nem `aprovado`, nem `bloqueado`, nem rodada cobrada. A mensagem
manda consertar o ambiente e rodar de novo, ou `escalar --motivo` se não der. O contrato
do `ciclo.py` não muda de forma (mesmos estados, mesmas arestas): é uma recusa a mais,
não uma transição a mais.

### 3. Posse do processo no `varrer`

`iniciar --pid` registra o processo quando o worker é um processo deste host (runner de
CI, `claude -p`, Hermes). `varrer`, para tarefa vencida com pid:

1. TERM ao grupo do processo (cai para o processo só, se o grupo não for nosso), espera
   2 s; KILL, espera 2 s.
2. Provou ausência → bloqueia e libera a vaga, registrando `processo: encerrado (pid N)`.
3. **Não provou → retém a vaga.** A tarefa fica `em_progresso` com `processo:
   vivo_apos_kill`, o histórico ganha `reteve_vaga`, o comando sai com 1. Um humano
   olha antes de qualquer relançamento naquela posse.

Sem pid, o comportamento anterior continua, com `processo: nao_provado (sem pid)` no
registro — o `varrer` diz o que não conseguiu verificar em vez de fingir que verificou.

`processo_vivo` lê `/proc/<pid>/stat` (ou `ps -o stat=`) e trata zumbi como morto:
`kill(pid, 0)` responde sucesso para um processo morto que ninguém colheu, e quem chama
o `varrer` raramente é o pai do worker. Sem isso, todo worker morto num sandbox sem init
que colha órfãos apareceria como "sobreviveu a KILL" — o que o teste do ADR-0039
demonstrou na primeira rodada.

### 4. Publicação atômica com limpeza

`quadro.salvar` passa a escrever ao lado e trocar com `os.replace`, como o `ciclo.gravar`
já fazia. Nos dois, falha na troca apaga o `.tmp` e propaga: o estado anterior continua
válido e nenhum temporário sobra para ser confundido com estado. Contrato do quadro
`1.1 → 1.2` (regras novas declaradas em `contrato_publico`).

## Consequências

**Positivas**

- "Concluída" passa a ser fato do git, não frase do agente. É a versão para o quadro do
  que o ADR-0032 fez para o ciclo (progresso lido do artefato, não da alegação).
- Ambiente quebrado deixa de consumir o orçamento de correção — e deixa de ser
  "corrigido" com mudança de código.
- Vaga retida é sinal; vaga liberada por cima de processo vivo era silêncio.

**Negativas e limites, declarados**

- **Tarefa de texto precisa declarar.** Teammate de apoio que produz decisão em conversa,
  sem arquivo, passa a precisar de `--sem-diff`. É atrito deliberado: a declaração fica
  registrada, e "não mudei nada porque a saída é uma decisão" é exatamente o que se quer
  ler no ledger.
- **Posse por pid só cobre worker que é processo.** Teammate do Agent Teams ou
  `spawn_agent` do Codex não é processo deste host; para eles o `varrer` continua
  bloqueando por prazo e registrando que não provou. Não há como provar o que não se vê.
- **`--sem-diff` é contornável** — é uma declaração. A diferença para antes é que fica
  gravada como tal, distinta de "diff em 3 arquivos", e o `ledger` mostra.
- **Contrato do `contrato.py` em 1.1.** Consumidor que valida com esquema próprio precisa
  aceitar `executado`/`motivo` e o veredicto `nao_executado`; consumidor que ignora
  campos desconhecidos continua válido.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Exigir commit (não só diff) para concluir | O quadro não decide a convenção de commit do projeto; diff em arquivo de posse já prova que alguém trabalhou ali |
| Estado `gate_nao_executado` no `ciclo.py` | Aresta nova muda o contrato v1.0 do ciclo para todo consumidor; uma recusa sem transição resolve o mesmo caso sem tocar o grafo |
| `varrer` sempre mata por nome de comando | Mataria processo que não é o worker. Só pid registrado no `iniciar` é posse declarada |
| Liberar a vaga mesmo sem prova, com aviso | É o comportamento que o ADR corrige. Aviso que ninguém lê a tempo é silêncio com mais texto |
