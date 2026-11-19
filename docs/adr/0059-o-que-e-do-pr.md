# ADR-0059 — O que é do PR e o que já existia

- **Status:** aceito
- **Data:** 2026-11-18
- **Versão:** v0.52.0

## Contexto

O `/revisar` classificava cada achado só pela gravidade. Um problema antigo, numa linha que o
PR não tocou, entrava como 🔴 igual ao que o PR introduziu, e bloqueava um PR que não tinha
culpa dele. São dois custos:

- **O PR fica parado.** Ou vira um PR maior para consertar o que ninguém pediu.
- **A revisão perde crédito.** Bloqueio por coisa velha é um falso positivo para quem
  escreveu o diff, e revisão com ruído é a que o time aprende a ignorar (ADR-0039).

A `corno-revisa`, do [corno-skills](https://github.com/adlernatanael/corno-skills), separa as
duas coisas:

- **O que é do PR**, as linhas que o diff introduziu ou piorou: pede ajuste.
- **O que já existia**, ou uma mudança de arquitetura maior que o PR: fica como observação
  para outra tarefa, sem bloquear.
- **A exceção:** o PR que depende do problema antigo, ou o piora, passa a responder por ele.

O repositório não declara licença: daqui sai a ideia, não o texto (ADR-0058). É o mesmo
princípio da catraca do legado do `qualidade.py` (ADR-0045): tocar código ruim não obriga a
reescrevê-lo, mas proíbe piorá-lo.

## Decisão

### Na skill

Cada achado diz onde está (`arquivo:linha`).

- **O que já existia antes do PR** vai para a seção nova **"Fora deste PR (já existia; não
  bloqueia)"**, com o lugar e o que fazer em outra tarefa. Não bloqueia nem conta entre os 🟠.
- **O PR que depende do problema antigo ou o piora** deixa o achado na gravidade dele. A
  linha ganha ` · o PR depende: <como>` ou ` · o PR piora: <como>`. Exemplos: chama o código
  defeituoso num caminho novo, passa a alimentá-lo com dado de fora, amplia o uso.

O contrato `kairos-revisao` não muda. `criticos` conta os 🔴 do PR, e o que vai para "Fora
deste PR" sai dele.

### A conferência pela linha: `prova.py origem`

`prova.py origem REVISAO.md [--base REF]` lê o relatório e confere cada `arquivo:linha` do 🔴,
do 🟠 e de "Fora deste PR" contra o diff. O diff inclui o que ainda não foi commitado. Arquivo
novo e não rastreado entram inteiros, e linha apagada conta no ponto onde estava.

Ele sai 1 em dois casos:

- **Achado que bloqueia numa linha que o PR não tocou, sem a marca.** Tem folga de 3 linhas,
  porque o revisor pode citar a assinatura ao lado da linha mexida. Sem a marca, é problema
  antigo: vai para "Fora deste PR".
- **Observação numa linha que o PR escreveu.** Aqui a comparação é exata, sem folga: é do PR,
  e volta para a gravidade dele.

Os dois casos são simétricos. A revisão não bloqueia o PR pelo que ele não fez, nem esconde em
"Fora deste PR" o que ele fez. Ficam de fora da conferência:

- o achado sem `arquivo:linha`, que aparece como "não conferido";
- o 🟡 e o 🔵, que não bloqueiam;
- o achado `· descartado:` (ADR-0039);
- o que está dentro de bloco de código.

A skill roda o `origem` depois de salvar o relatório e o corrige até sair 0.

### No gatilho de CI

No `kairos-forge-revisar.yml`, o agente não escreve arquivo nem roda `python3`, e o relatório
sai no `revisao.md`. Um passo novo, depois do agente:

- roda `prova.py origem revisao.md --base <base do PR>`;
- passa a saída pelo `guardrail.py ocultar`, como todo texto publicado (ADR-0057);
- só quando há achado fora do lugar, põe uma seção "Conferência da origem dos achados" no
  comentário.

O passo nunca falha o job. O parecer continua consultivo.

### No eval de tarefa

`t12-revisar-defeito-antigo`: um diff correto e testado no `relatorio.py`, e uma injeção de SQL
antiga em `vendas/consulta.py`, que o PR não toca nem chama.

- **A resposta certa** aprova e anota o defeito em "Fora deste PR".
- **As três erradas** reprovam: a que bloqueia pelo defeito antigo (contrato e `bloqueios`), a
  que o ignora (`arquivo`) e a que corrige em vez de revisar (`intocado`).

É a medida que faltava ao `evals/tarefas-fabrica/`: a `t10` cobre o falso positivo dentro do
diff, e a `t12`, o falso positivo fora dele.

## Prova

- **`prova.py origem` num repositório descartável.** No relatório que bloqueia pelo antigo e
  anota o novo como observação, os dois erros aparecem e o comando sai 1. No relatório certo, ele
  sai 0.
- **`scripts/tests/test_origem.py`, com 25 testes num git de verdade.** Cobrem:
  - o 🔴 e o 🟠 fora do diff;
  - o do PR que passa, inclusive com intervalo de linhas;
  - a folga ao lado da linha mexida, no limite exato, e o longe dela;
  - a linha apagada, a removida que parece cabeçalho de diff (um comentário SQL), as duas
    marcas (sem diferença de maiúscula) e o arquivo novo inteiro;
  - o 🟡, o 🔵 e o descartado, que não são conferidos, e o achado sem local;
  - a observação no código do PR, a do código antigo, a ao lado da mudança e a logo depois
    da linha apagada;
  - o leitor das seções, do bloco de código e dos campos;
  - o comando, com a saída 1 e 0, o JSON e os três erros numa linha;
  - a impressão, com o título e a dica de cada erro, o texto longo cortado, a base padrão e o
    relatório ilegível;
  - os passos do `kairos-forge-revisar.yml` rodados de verdade, com um `gh` falso: o comentário
    traz a conferência quando há achado fora do lugar, e não traz quando não há.
- **O eval de tarefa:** `rodar.py validar` em 12 de 12, com a `t12` distinguindo a base e as três
  erradas da solução.

## Limites

- **A linha é a do relatório.** O revisor pode citar a linha errada; aí a conferência erra junto.
  O achado sem linha não é conferido.
- **"O PR depende" e "o PR piora" são declarados pelo revisor.** O `origem` cobra que seja dito,
  não que seja verdade. Quem julga é a pessoa que lê o PR.
- **No gatilho de CI, a conferência só aponta.** O comentário mostra o achado fora do lugar, mas o
  agente não corrige o relatório ali, porque não escreve arquivo.
