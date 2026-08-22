# ADR-0036 — Tempo limite e compensação: o que fazer quando o trabalho já feito perde a validade

- **Status:** aceito
- **Data:** 2026-08-22
- **Versão:** v0.29.0

## Contexto

Revisão do material *Arquitetura de Sistemas com IA* (Ahirton Lopes), um curso que
constrói uma plataforma multi-agente do zero. A maior parte do conteúdo já estava
coberta pelos ADRs existentes — orquestrador–trabalhadores (ADR-0009), Sequential e
Parallel (`/rodar` e `/mobilizar`), Supervisor (Laura), roteamento por tier (ADR-0013),
retry com limite (`rodadas_por_task`), observabilidade (ADR-0021), antipadrão da
reimplementação (ADR-0034).

Três coisas não estavam, e as três são da mesma família: **o que a fábrica faz quando
algo dá errado depois que o trabalho já começou.**

A ironia que organizou este ADR: a skill `/kairos-forge:diagnosticar` audita o sistema
do usuário exatamente por **timeout, retry e idempotência**, e o Murilo
(`murilo-eventos`) é dono desse assunto como especialidade. O orquestrador da própria
fábrica não tinha nenhum dos três. Casa de ferreiro.

### O que faltava, concretamente

**1. Tempo.** O `quadro.py` não tinha nenhum conceito de tempo. Uma tarefa
`em_progresso` cujo worker morre sem avisar fica em progresso para sempre: a vaga da
onda nunca é devolvida, o teto nunca libera, a onda seguinte nunca sai — e **nada nunca
dá erro**. A mobilização trava em silêncio, que é pior que falhar alto.

**2. Falha tardia.** Quando uma tarefa **já concluída** se revela inválida — mudou a
premissa, o requisito, o schema — o quadro só tinha duas saídas, ambas ruins: declarar
lacuna e parar (desperdiça o trabalho ainda válido) ou refazer tudo (desperdiça o
trabalho todo). Faltava o meio-termo.

**3. Idempotência.** Não estava declarada. Estava implementada em parte, por acidente
de implementação, o que é diferente de ser contrato.

## Decisão

**1. Tempo limite por tarefa, com varredura explícita.** `abrir --tempo-limite` define o
default do quadro (60 min), `adicionar --tempo-limite` sobrescreve por tarefa.
`quadro.py varrer` bloqueia o que passou do prazo e **devolve a vaga da onda**.

O número não é estimativa de esforço. É o ponto em que "ainda trabalhando" e "morreu sem
avisar" deixam de ser distinguíveis de fora — e é por isso que ele existe mesmo sendo
impreciso: sem ele, os dois casos são tratados como o primeiro para sempre.

Bloqueia, não conclui: o tempo estourou, não há evidência nenhuma de que ficou pronto.
E `varrer` é comando separado, não efeito colateral de `estado` ou `prontas` — relatar
pode acontecer em qualquer render; agir precisa ser pedido.

**2. Compensação em vez de reinício — padrão Saga.** `quadro.py compensar <task>` devolve
à fila **a tarefa inválida e só o que foi construído sobre ela**, na ordem inversa da
execução. O que não dependia dela permanece concluído.

O padrão Saga trata cada etapa como transação independente com a própria ação de
desfazer, em vez de tratar o fluxo inteiro como transação indivisível. **A metade cara
disso o forge já tinha**: o `--reverter` do ADR-0024 é exatamente a ação compensatória
que o Saga pede — declarada antes de executar, como o ADR-0024 exigia por outro motivo
(admissão de autonomia). Faltava só a orquestração.

Três regras fecham o comportamento:

- **Ordem inversa é obrigatória.** Derrubar a base antes do que se apoia nela deixa o
  repositório num estado que ninguém desenhou.
- **Plano tudo-ou-nada.** Se qualquer tarefa afetada não declarou `--reverter`, o plano
  inteiro é recusado. Compensação pela metade é pior que não ter começado, e tarefa
  irreversível para no usuário (ADR-0024).
- **A rodada queima só na raiz.** Ela produziu a saída errada; as dependentes estavam
  certas sobre uma base que mudou. Cobrar orçamento delas é punir o inocente.

**3. Idempotência vira contrato, não acidente.** `concluir` e `encerrar` repetidos não
duplicam efeito, e isso passa a estar declarado em `contrato.py`/`quadro.py contrato` —
com `estado --json` ganhando `vencidas` (contrato 1.0 → 1.1, campo novo = MENOR).

## Consequências

**O modo de falha silencioso mais provável do `/mobilizar` deixa de existir.** Worker que
morre sem avisar era a falha que não produzia sintoma — e a única que a fábrica não
sabia nomear. Agora produz `vencidas` no `estado`, no `painel.py` e no `--json`.

**Falha tardia deixa de ser tudo-ou-nada.** Numa mobilização com uma cadeia de quatro
tarefas mais uma independente, uma invalidação na raiz preserva a independente em vez de
descartá-la "por precaução".

**O que NÃO entrou, e por quê.** O mesmo material trazia Semantic Cache, Prompt Cache,
RAG básico, KServe/Kubeflow e model serving. Todos ficam fora por ADR-0001: o forge é
plugin, não runtime — não é dono do caminho de inferência e não deve fingir que é. O
domínio regulado do material (ICF, CSR, ICH E3, Anvisa/FDA, approval gate com peso
jurídico) é kairos-ai por ADR-0002.

**Controle otimista de versão também ficou fora**, e essa merece nota porque parece
lacuna e não é: o forge resolve conflito de escrita por **partição** (posse de arquivo
serializada pelo quadro). O controle otimista é a alternativa para quando não dá para
particionar — caso que o quadro proíbe de propósito. Adotar os dois seria manter dois
mecanismos para o mesmo problema, com o segundo só valendo onde o primeiro foi violado.

## Alternativas descartadas

**`varrer` automático dentro de `prontas`/`estado`.** Tentador: ninguém esquece de rodar.
Descartado porque transformaria um comando de leitura em um que muda estado — e o
`painel.py` renderiza `estado` a cada checkpoint. Um `--json` chamado por CI passaria a
bloquear tarefas como efeito colateral de olhar.

**Compensar automaticamente ao detectar inconsistência.** Descartado: qual tarefa está
inválida é julgamento sobre o domínio, não sobre o grafo. O quadro sabe *quem depende de
quem*; não sabe *quem errou*. Ele calcula o plano e recusa o irreversível — a decisão de
qual é a raiz continua sendo de quem leu o problema.

**Timeout como falha dura, encerrando a mobilização.** Descartado por desproporção: o
caso comum é uma tarefa grande demais para o limite, não o time inteiro travado. Bloquear
e devolver a vaga deixa o resto da onda seguir.
