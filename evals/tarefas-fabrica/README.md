# Eval de tarefa concluída da fábrica

Irmão dos outros dois evals:
- o `evals/roteamento-laura/` mede se a Laura chama o agente certo;
- o `evals/comportamento-fabrica/` mede se a fábrica se comporta quando o mundo diz não;
- este mede **se a tarefa ficou pronta**.

É o número que decide entre arquiteturas. Uma persona só deixa de ser subagente, ou passa a
ser, se a tarefa concluída não piorar (ADR-0049).

> Este diretório é do **desenvolvimento do plugin** (dogfooding): não é distribuído em
> `plugin/` nem chega aos usuários finais. Base: o artigo da Anthropic *Building agents: when to
> fold subagents into your main agent loop* e o
> [single-agent-loop-kit](https://github.com/anthropics/single-agent-loop-kit) (Apache 2.0), de
> onde vêm o desenho em variantes, a comparação por tarefa e a regra de uma mudança por rodada.
> O código aqui é próprio.

## As tarefas

O projeto de todas é o `relatorio-vendas` da demo (Python, só biblioteca padrão). Cada tarefa
acrescenta o que precisa por cima dele.

| Tarefa | Tipo | O que decide se ficou pronta | O que ela testa na auditoria |
|---|---|---|---|
| `t01-csv-sujo` | corrigir | oráculo | caso simples: o loop principal resolve sozinho? |
| `t02-entregar-exportar-json` | construir | oráculo + SPEC + ciclo em `pronto_para_pr` + relatórios de validação e revisão válidos | o arco inteiro do `/entregar` |
| `t03-media-por-regiao` | corrigir | oráculo (com regressão escondida) e uma solução errada conhecida | correção que não quebra o que não estava no pedido |
| `t04-revisar-traversal` | verificar | relatório de revisão bloqueado, citando o defeito plantado, sem corrigir o código | verificação: com e sem contexto independente |
| `t05-criticar-spec` | verificar | crítica bloqueada, com os dois defeitos plantados e ao menos 2 críticos | crítica adversarial: com e sem contexto independente |
| `t06-perguntar-moeda` | perguntar | código intocado, e a resposta pergunta pela moeda ou pelo câmbio | Pare e Pergunte (ADR-0015) |
| `t07-dois-modulos` | construir | oráculo | trabalho independente: paralelo vale a pena? |
| `t08-corrigir-traversal` | corrigir | oráculo e uma solução errada conhecida | segurança: correção de verdade, não ingênua |
| `t09-revisar-caminho-absoluto` | verificar | revisão bloqueada no caminho absoluto que o validador deixa passar, sem bloquear a isca (`subprocess` seguro), sem corrigir | verificação que não vai pelo padrão: o `..` já é recusado, e os testes do diff passam |
| `t10-revisar-sem-defeito` | verificar | revisão aprovada, com a lista do que foi examinado, de um diff correto e testado com iscas | o falso positivo: bloquear o que estava certo |
| `t11-criticar-spec-sutil` | verificar | crítica bloqueada no critério de um sentido só e na matriz que não prova, sem bloquear o requisito bem feito | crítica além do adjetivo e da contradição direta |

### Por que t09, t10 e t11

Na linha de base, a fábrica acertou a `t04` e a `t05` em todas as rodadas. Um path traversal de
manual num arquivo de três linhas, um adjetivo e uma contradição direta não separam uma variante
da outra: as duas acertam. E as duas só mediam o acerto. A verificação isolada do ADR-0049 pode
achar mais, e pode também bloquear mais à toa, e só medindo os dois lados dá para saber se ela
ajuda.

- **O defeito não vai pelo padrão.**
  - Na `t09`, o validador já recusa `..`, os testes do diff passam e o buraco é o caminho
    absoluto: `Path("relatorios") / "/etc/passwd"` é `/etc/passwd`. É a mesma armadilha da
    solução errada "só `..`" da `t08`, do lado de quem revisa.
  - Na `t11`, o critério de REG-02 proíbe o caso ruim sem garantir o bom (ADR-0053), e a matriz
    aponta REG-03 para um teste que mede outra coisa.
- **Cada tarefa tem uma isca, e bloquear a isca reprova.** São elas o `subprocess` com lista e
  `--` na `t09`, a divisão já protegida e o `TODO` na `t10`, e o REG-04 incomum mas bem
  especificado na `t11`.
- **A `t10` não tem defeito nenhum.** O certo é aprovar e dizer o que foi lido. A base dela já
  sai com a leitura do CSV corrigida (a solução da `t01`), para nenhum defeito anterior ao diff
  ficar no caminho.

Cada uma tem soluções erradas conhecidas que o `validar` exige reprovar:
- na `t09`, a revisão que só vê o `..` e a que bloqueia o `subprocess`;
- na `t10`, a que bloqueia a isca e a que mexe no código em vez de só revisar;
- na `t11`, a que acha um defeito só e a que bloqueia a isca.

## Formato de uma tarefa

```text
tarefas/<id>/
├── tarefa.json   id, tipo, título, prompt, oraculo (true/false), checagens, tempo_limite_s
├── projeto/      o que entra por cima de tarefas/_comum antes do commit "base"
├── mudanca/      opcional: commit seguinte numa branch (a tarefa de revisão revisa este diff)
├── oraculo/      testes escondidos: só entram no projeto depois da rodada
├── solucao/      a solução de referência (com resposta.txt, se a checagem lê a resposta final)
└── erradas/<n>/  soluções erradas conhecidas, que o oráculo tem de reprovar
```

As checagens são lidas do disco, por código:

| Checagem | Passa quando |
|---|---|
| `arquivo` | algum arquivo do `glob` casa com todas as `regex` |
| `contrato` | o último arquivo do `glob` tem bloco de contrato válido pelo `scripts/contrato.py`, com os `campos` e os `minimos` pedidos |
| `ciclo` | algum `.agents/ciclo/*.json` está num dos `estados` |
| `intocado` | nada mudou nos `caminhos` desde o commit de referência, nem em commit nem em arquivo novo |
| `resposta` | a resposta final da sessão casa com todas as `regex` |
| `bloqueios` | no último arquivo do `glob`, cada regex de `exige` casa com algum achado bloqueante, e nenhuma de `proibido` casa |

Para a checagem `bloqueios`, achado bloqueante é:
- a linha que traz 🔴;
- a linha de lista ou de tabela dentro de uma seção cujo título traz 🔴.

Ficam de fora o bloco de contrato (o `examinado` cita arquivo sem acusar) e a linha marcada
`descartado` (ADR-0039).

Em `contrato`, um campo pode pedir uma lista de valores aceitos: `"veredicto": ["aprovado",
"aprovado_com_ressalvas"]`. Em `tarefa.json`, `"mudanca"` pode ser um objeto com `branch` e
`mensagem` do commit da mudança. Com `true`, valem `feature/download` e a mensagem de download.

A tarefa passa quando o oráculo passa (se houver) e todas as checagens passam.

## O que é decidido por código e o que fica de fora

Tudo o que dá nota é código: oráculo, checagem e contrato. Não há juiz-LLM neste eval.

Ficam de fora, declarados:
- **Qualidade do texto** de SPEC, crítica e revisão, além do que as regex e o contrato pegam.
- **Tokens de teammates do Agent Teams**, que rodam em sessões próprias. O `result` do
  `stream-json` traz o uso da sessão principal.
- **Dinheiro**, pelo mesmo motivo do ADR-0044.

## Como rodar

**Sem modelo e sem custo** (é o que o CI roda):

```bash
python3 evals/tarefas-fabrica/rodar.py validar
python3 -m unittest discover -s evals/tarefas-fabrica -p 'test_*.py'
```

O `validar` monta cada tarefa e exige três coisas:
- o projeto como está é reprovado;
- a solução de referência é aprovada;
- cada solução errada conhecida é reprovada.

Oráculo que não distingue as três situações mede nada.

**Pago:** cada tarefa × rep vira uma sessão `claude -p` numa pasta temporária. A sessão carrega
o plugin pelo `--plugin-dir` e roda sem as configurações de quem a dispara
(`--setting-sources ""`):

```bash
python3 evals/tarefas-fabrica/rodar.py rodar --variante base --reps 2
python3 evals/tarefas-fabrica/rodar.py estimar base --reps 3        # antes da próxima rodada
python3 evals/tarefas-fabrica/rodar.py comparar base v1-verificacao-isolada
```

- **Cada rodada paga pede um ok** com o tamanho (tarefas × reps) e a estimativa de tokens. A
  primeira não tem medida anterior, então começa por uma sonda pequena.
- **Uma mudança por variante.** Se duas coisas mudam juntas, ninguém sabe qual mexeu no número.
- **Leia as rotas, não só a nota.** O `comparar` lista as tarefas cuja rota de subagentes mudou.
  Tarefa que continua passando por um caminho mais caro também é resultado.
- **Mais reps de uma variante já comparada viram outra variante** (`base-rerun`). O runner recusa
  acrescentar a uma variante que já tem resultados.
- **A sessão roda com `--permission-mode bypassPermissions`** numa pasta temporária. Rode numa
  máquina ou num container descartável.
- **Os resultados ficam fora do git** (`resultados/`). Quando o time quiser, a conclusão sobe
  para o ADR ou para a auditoria.

## Variantes previstas

A ordem vem da lista de trabalho de `docs/loop-unico/AUDITORIA.md`. Cada variante muda uma
coisa em relação à última que ficou:

1. `base` — a fábrica como está (v0.43.0).
2. `v1-verificacao-isolada` — crítica e revisão em subagente de contexto limpo, com o bloco de
   contrato como resultado. Mede-se em `t04`, `t05`, `t09`, `t10` e `t11`: o acerto e o bloqueio à
   toa.
3. `v2-apoio-juntado` — os squads de apoio sem papel juntados dentro do squad. Mede-se pelo
   roteamento e por todas as tarefas, para ver se nada piora.
4. `v3-correcao-no-loop` — o loop de correção do `/entregar` sem repasse. Mede-se em `t02`.
