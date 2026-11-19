# Contrato de integração do kairos-forge

> Para quem **dirige** a fábrica de fora: [kairos-symphony](https://github.com/VilelaAI/kairos-symphony),
> um runner próprio, um job de CI, um bot. Decisão: [ADR-0034](adr/0034-contrato-de-integracao.md).

O kairos-forge é um plugin: quem executa é o CLI, quem decide o próximo passo é o
`ciclo.py`, e quem consome pode ser um daemon lá fora. Este documento define **o que é
estável** nessa fronteira — e, por consequência, o que não é.

A regra que organiza tudo:

> **Se não está aqui, é interno e pode mudar sem aviso.** Se está aqui, só muda com bump
> de versão, e o CI recusa mudança silenciosa de forma.

## Os três contratos

| Contrato | Comando | Versão | Para quê |
|---|---|---|---|
| `kairos-forge/ciclo` | `ciclo.py estado <SPEC> --json` | 1.4 | Qual o próximo passo, precisa de humano, o que registrar, se a SPEC mudou |
| `kairos-forge/contrato` | `contrato.py <gate> <arquivo>` | 1.3 | Ler o veredicto dos relatórios sem parsear prosa |
| `kairos-forge/quadro` | `quadro.py estado <slug> --json` | 1.3 | O que o `/mobilizar` pode lançar agora, o que venceu o prazo, se o quadro pode encerrar (ADR-0035/0036) |

A versão vigente de cada um é a de `contratos/ASSINATURA.json`. Os três se publicam
sozinhos, legíveis por máquina:

```bash
python3 scripts/ciclo.py contrato          # estados, terminais, gates, TRANSIÇÕES, campos
python3 scripts/contrato.py esquema        # as três fences, campos e regras de aceitação
python3 scripts/quadro.py contrato --json  # estados de tarefa, padrões, campos e regras
```

(`quadro.py contrato` sem `--json` imprime um resumo para humano; os outros dois sempre
saem em JSON.)

**Leia a declaração em vez de repetir a máquina do seu lado.** O `ciclo.py contrato`
publica o grafo inteiro de transições; reimplementar por fora é garantir que os dois
discordem na primeira aresta nova.

## Contrato 1 — o estado do arco

```bash
python3 scripts/ciclo.py estado SPEC-001 --json
```

Campos garantidos:

| Campo | Tipo | O que faz por você |
|---|---|---|
| `contrato` | string | Versão deste contrato |
| `spec` | string | Qual SPEC |
| `estado` | string | Um de `estados` |
| `terminal` | boolean | Nada mais a registrar (veja `escalado` no laço abaixo) |
| `aguardando_humano` | boolean | **Precisa de gente, não de agente** |
| `gate` | string\|null | Gate em jogo (`criticar`/`validar`/`revisar`) |
| `proximo_passo` | string | Instrução legível para o agente |
| `resultados_validos` | string[] | O que `registrar` aceita **neste** estado |
| `orcamento`/`rodadas`/`rodadas_totais`/`teto`/`marca` | object | Fichas por gate |
| `historico` | object[] | Toda transição, com horário e contagem (a forma de cada item não é contrato) |
| `spec_alterada` | boolean\|null | **O contrato da SPEC mudou depois da aprovação** (requisito, critério, prioridade, plano — Status e Verificação não contam). `null` = sem digest (SPEC não encontrada, ou ciclo anterior à v1.1). `true` = resultado verde de gate será recusado até um humano rodar `ciclo.py reaprovar` (ou a SPEC voltar ao texto selado). Desde 1.1 |
| `pendentes_revisao` | string[] | Os ids (`achados`) dos 🔴 da revisão bloqueada que a revisão seguinte ainda não marcou como resolvidos. Com algum pendente, `registrar limpo` exige cada um em `anteriores` como `resolvido`. Sai sempre, `[]` quando não há. Desde 1.3 |
| `motivo_escalacao` | string, opcional | Por que escalou: orçamento esgotado sem progresso, teto absoluto ou `ciclo.py escalar --motivo`. Na escalação por orçamento, leva a premissa das correções quando a sequência de falhas teve uma (1.4). Ausente até a primeira escalação |
| `motivo_encerramento` | string, opcional | O `--motivo` de `ciclo.py encerrar`. Encerramento por `registrar` (`pr_aberto`, `recusada`) não o preenche |

Os quatro derivados no topo existem para você **não comparar string de estado**. Um
consumidor que faz `if estado == "aguardando_aprovacao"` quebra quando um estado é
renomeado; `if aguardando_humano` não.

### O laço mínimo

```
1. ciclo.py estado <SPEC> --json
2. terminal?           → `escalado`: leve `motivo_escalacao` ao humano; só ele
                          destrava (novo `abrir`, orçamento ampliado)
                          `encerrado`: pare
3. aguardando_humano?  → leve ao humano pelo SEU canal (issue, chat, PR)
                          e registre a resposta quando vier
4. spec_alterada?      → leve o diff da SPEC ao humano: ele aceita a versão nova
                          (`ciclo.py reaprovar <SPEC>`) ou desfaz a mudança
5. senão               → invoque o CLI com `proximo_passo` e o nome da SPEC
6. ciclo.py registrar <um de resultados_validos> <SPEC>
                          `pr_aberto` leva `--pr <URL ou número>`;
                          `premissa_escrita` leva `--nota "<a premissa>"`
   exit 1?             → releia `estado`: mudou = já registrado, siga;
                          não mudou = recusa real, motivo no stderr
7. volte ao 1
```

Os passos 2 e 4 são os que um laço ingênuo erra:

- **`escalado` é terminal, mas não é fim.** Não há mais nada a registrar, e o caso vai
  para gente. Nenhum derivado separa os dois terminais, então aqui, e só aqui, compare
  `estado` com a lista `terminais` publicada pelo `ciclo.py contrato`. O novo `abrir`
  sobrescreve o arquivo do ciclo e o `historico` da rodada escalada não é preservado:
  se você precisa dele para auditoria, leve-o junto quando levar o caso ao humano.
- **`spec_alterada: true` não liga `aguardando_humano`, mas pede decisão humana.** O
  ciclo segue aceitando `pronto` e resultado negativo, e recusa `aprovado`,
  `aprovado_com_ressalvas` e `limpo` até o `reaprovar`. Um laço que só invoca o agente
  roda o gate, registra `aprovado`, é recusado e roda o gate de novo.

Desde a 1.2 (ADR-0045) há três estados a mais: `atacando_premissa_spec`,
`atacando_premissa_validacao` e `atacando_premissa_revisao`. O ciclo entra num deles na
terceira falha seguida do mesmo gate sem baixar a contagem de achados (duas correções
frustradas) e só sai com `registrar premissa_escrita <SPEC> --nota "<a premissa>"`: a
suposição que as correções compartilharam, em uma frase, diferente das já atacadas na
mesma sequência. Sem `--nota`, com nota de menos de 20 caracteres ou com uma premissa
repetida, o `registrar` sai 1. Um laço que segue `resultados_validos` e `proximo_passo` não
muda nada: o agente lê a instrução e escreve a premissa.

Desde a 1.4 (ADR-0061), o destino de `premissa_escrita` é calculado, e a declaração o
publica como `null`, como o do resultado negativo. Com orçamento sobrando, a premissa reabre
a correção do gate. Quando a falha que trouxe até ali esgotou o orçamento, o ciclo vai para
`escalado`, com a premissa no `motivo_escalacao`. É o caso do orçamento padrão (2): a
terceira falha não paga correção, passa pelo `atacando_premissa_*` sem gastar ficha, e a
premissa segue com a escalação. O `proximo_passo` diz qual dos dois caminhos vem. Com
orçamento 1, a escalada chega na segunda falha, antes desses estados. E, com qualquer
orçamento, a escalação por orçamento esgotado leva a última premissa atacada na sequência,
quando houve uma.

Em `revisando`, a revisão limpa na faixa 3 não fecha (ADR-0031). Desde a 1.4 (ADR-0061),
`registrar limpo` com `faixa: 3` no bloco da revisão sai 1, e o caminho é `ciclo.py escalar
<SPEC> --motivo "faixa 3: ..."`, como faz o `/entregar`. O `proximo_passo` de `revisando`
diz isso. Relatório sem bloco não tem faixa lida, e a faixa não recusa o `limpo` dele: ali,
leia a `faixa` na prosa antes de registrar (ver as regras do Contrato 2).

Em `pronto_para_pr`, `registrar pr_aberto` exige `--pr` desde a 1.4 (ADR-0061): o número,
com ou sem `#`, ou a URL `…/pull/N` que o `gh pr create` imprime. Sem ele, ou com algo que
não é referência de PR, sai 1. Com o `gh` respondendo, o PR precisa existir e estar aberto
ou mesclado; o inexistente e o fechado sem merge saem 1. Quando o `gh` falta ou falha por
outro motivo (sem login, sem rede, fora de um repositório), o ciclo encerra assim mesmo,
com aviso no stderr e `pr_conferido: false` no evento do `historico`: o `--pr` pega a
omissão, não prova que o PR existe. PR de outra branch que não a do ciclo encerra com
aviso. O `proximo_passo` já traz o `--pr`; o runner que monta o `registrar` sozinho precisa
passar a URL ou o número.

Duas coisas que a POC de um runner externo (`docs/pocs/POC-mhl-entregar.md`, na branch
`poc/mhl-entregar`) mostrou que o consumidor precisa saber:

- **Passe a SPEC sempre.** Sem ela, `estado` resolve "o único ciclo aberto" — conveniência
  de sessão, não contrato — e **falha quando o ciclo já fechou**: stdout vazio, e o runner
  fica sem ler `terminal`. Com a SPEC explícita, ciclo encerrado responde normalmente.
- **`proximo_passo` não nomeia a SPEC.** É instrução do estado, igual para todo ciclo. O
  prompt que o runner monta para o agente precisa dizer qual SPEC é; um agente que
  "descobre" a SPEC listando `docs/specs/` pega a primeira, e a primeira pode ser outra.

**O `ciclo.py` já faz o que um runner precisaria fazer sozinho:** recusa resultado
inválido no estado, cobra o veredicto do artefato, conta ficha com devolução por
progresso, impõe teto absoluto e escala sozinho quando o orçamento acaba. Desde a 1.4
(ADR-0061), também recusa o `limpo` da faixa 3 e o `pr_aberto` sem PR. Não reimplemente
nada disso — chame.

E o estado vive em `.agents/ciclo/<spec>.json`, atômico via `os.replace`: sobrevive a
restart do seu daemon, troca de CLI e reset de contexto. Não guarde cópia.

### Exit 1 do `registrar`

**Registrar é idempotente por construção, e há teste para isso** (`scripts/tests/test_ciclo.py`):
um runner com semântica at-least-once que repete `registrar <resultado> <SPEC>` depois de
um crash não avança dois estados — o resultado deixa de ser válido no estado novo e é
recusado com exit 1.

Mas exit 1 não quer dizer só "já registrei". O `registrar` sai com 1, stdout vazio e o
motivo no **stderr** nestes casos:

- resultado fora de `resultados_validos` — a repetição, ou o agente registrou errado;
- ciclo em estado terminal — inclusive quando a repetição cai num terminal
  (`pr_aberto` → `encerrado`);
- resultado verde de gate com `spec_alterada: true`;
- resultado verde com o relatório mais recente do gate dizendo `bloqueado`;
- resultado verde com o bloco de contrato do relatório recusado pelo parser
  (`json_invalido`, `estrutural`, `sem_cobertura` — o código vai entre colchetes);
- resultado verde sem relatório do gate, ou com relatório legado (sem bloco) e sem linha
  `**Veredicto:**` reconhecível;
- `limpo` com `pendentes_revisao` sem cada id em `anteriores` como `resolvido`, ou sem
  bloco válido para dizê-lo (1.3);
- `limpo` com `faixa: 3` no bloco da revisão (1.4);
- `premissa_escrita` sem `--nota`, com nota de menos de 20 caracteres ou com premissa já
  atacada na mesma sequência (1.2);
- `pr_aberto` sem `--pr`, com referência que não é de PR, ou com PR que o `gh` diz não
  existir ou estar fechado sem merge (1.4);
- SPEC sem ciclo (`abrir` nunca rodou para ela).

A regra: **depois de exit 1, releia `estado`.** Mudou desde a leitura que precedeu o
`registrar`? A transição já tinha acontecido — siga. Não mudou? É recusa real: leve o
stderr a quem resolve (o agente, se falta relatório, se ele diz `bloqueado`, se falta a
premissa ou o `--pr`, ou se o PR não existe ou foi fechado sem merge; o humano, se
`spec_alterada`) e não repita o mesmo `registrar` sem mudar nada, porque isso é laço. Na
faixa 3 não há o que repetir: o caminho é `ciclo.py escalar`. O texto do stderr é para
gente, não é contrato: repasse, não parseie.

## Contrato 2 — os relatórios

Três gates, **três fences distintas**, nunca compartilhadas:

| Gate | Fence | Arquivo | Contagem | Lista de cobertura |
|---|---|---|---|---|
| `criticar` | ` ```kairos-critica ` | `docs/specs/criticas/CRITICA-<SPEC>-<AAAA-MM-DD>.md` | `achados` | `examinado` |
| `validar` | ` ```kairos-validacao ` | `docs/specs/validacoes/VALIDACAO-<SPEC>-<AAAA-MM-DD>.md` | `bloqueios` | `verificado` |
| `revisar` | ` ```kairos-revisao ` | `docs/specs/revisoes/REVISAO-<SPEC>-<AAAA-MM-DD>.md` | `criticos` | `examinado` |

A separação é o ponto: os três relatórios carregam a mesma linha `**Veredicto:**`, e
fence compartilhada deixaria um ser lido como o outro no dia errado.

As regras que o parser cobra, e que o seu lado deve cobrar igual se reimplementar:

1. **Coerência** — `veredicto` é `aprovado`, `aprovado_com_ressalvas` ou `bloqueado`
   (maiúscula e espaço normalizados), a contagem é inteiro ≥ 0, e `bloqueado` ⟺ contagem ≥ 1.
   A exceção é a revisão incompleta: desde 1.3, `bloqueado` com `criticos: 0` vale quando
   `incompletos` não está vazio (regra 4a).
2. **Prova de cobertura** — contagem 0 com veredicto que não é `bloqueado` exige a lista de
   cobertura não-vazia: `verificado` na validação, `examinado` na crítica e na revisão. O
   `bloqueado` da revisão incompleta não aprova nada e não exige a lista (1.3): quando nenhum
   revisor rodou, a lista honesta é vazia.
3. **Independência** (só na crítica) — ao menos 2 nomes distintos em `criticado_por`,
   sem diferenciar maiúscula.
4. **Faixa** (só na revisão) — `faixa` obrigatória: 1 (contida), 2 (ampla) ou 3 (difícil
   de reverter).
4a. **Completude** (só na revisão, desde 1.1 — ADR-0046) — o campo opcional `incompletos`
   lista o revisor da faixa que não entregou parecer (erro, tempo, contexto estourado).
   Não-vazio exige `bloqueado`: revisor que não rodou não aprovou, e o código é
   `sem_cobertura`. Desde 1.3 (ADR-0061), sustenta o `bloqueado` também com `criticos: 0`
   e `examinado` vazio, e o `ciclo.py` não conta a contagem dessa rodada como progresso: a
   ficha queima. Relatório sem o campo continua valendo como antes.
4b. **Falta de prova** (só na validação, desde 1.2 — ADR-0048) — o opcional `sem_evidencia`
   conta os bloqueios que são requisito sem prova e não passa de `bloqueios` (`estrutural`).
   Igual a `bloqueios`, acima de 0, a validação está bloqueada só por falta de prova: onde
   o orçamento mandaria corrigir, o `ciclo.py` manda para `provando`.
4c. **Ids dos 🔴** (só na revisão, desde 1.2 — ADR-0048) — os opcionais `achados` (um id
   por 🔴) e `anteriores` (o que a re-revisão diz de cada 🔴 da rodada anterior:
   `resolvido` ou `nao_resolvido`). Os ids em `achados` são conferidos só quando
   preenchidos: tantos quanto `criticos`, sem repetição. Vazio ou ausente é aceito e não
   cria pendência no ciclo. `nao_resolvido` em `anteriores` exige `bloqueado`. Os erros
   são `estrutural`.
5. **Último bloco fechado vence** — rascunho anterior é ignorado; bloco sem fence de
   fechamento não conta e vira `ausente` (tolera CRLF, fence colada no texto anterior e
   indentação até 3 espaços).
6. **Teto de itens** — lista com mais de 200 itens é `estrutural`.

E duas que o parser não cobra, mas que mudam o que o runner faz:

- **Faixa 3 nunca fecha por evidência** (ADR-0031). Está declarada no `esquema`, mas o
  parser só confere o valor. Quem cobra é o `ciclo.py`: desde a 1.4 (ADR-0061),
  `registrar limpo` com `faixa: 3` no bloco sai 1. O caminho é `ciclo.py escalar <SPEC>
  --motivo "faixa 3: ..."`, como faz o `/entregar`; um runner deve fazer o mesmo.
  Relatório sem bloco não tem faixa lida, e a faixa não recusa o `limpo` dele: ali, quem
  para é o runner, lendo a faixa na prosa.
- **Qual relatório o `ciclo.py` lê** (comportamento atual, fora do `esquema`). Na pasta
  do gate, procura `<PREFIXO>-<SPEC>-*.md` (na SPEC, todo caractere fora de
  `[A-Za-z0-9_-]` vira `-`) e fica com o **maior nome em ordem lexicográfica**, não com o
  arquivo mais novo. Relatório nomeado por outra coisa que não a SPEC (a revisão aceita
  slug de branch) não é encontrado. Segunda rodada no mesmo dia sobrescreve o mesmo nome;
  sufixo como `-2` ordena *antes* do nome sem sufixo e não é lido.

Códigos de erro, e o que fazer com cada um:

| Código | Significado | Ação |
|---|---|---|
| `ausente` | Sem bloco fechado com a fence | Relatório legado — degrade, não falhe |
| `json_invalido` | Bloco não é JSON | Cabe **1 retry** com a mensagem de erro |
| `estrutural` | Campo/tipo/coerência/faixa/independência/teto | Cabe **1 retry** |
| `sem_cobertura` | Limpo sem lista, ou limpo com revisor que não rodou | **Achado**, não retry — o relatório está errado |

O `registrar` aplica esta tabela. Só `ausente` cai para a linha `**Veredicto:**` da prosa,
sem contagem — é o relatório legado. Qualquer outro código recusa resultado verde, com o
código no stderr: a linha `**Veredicto:**` não substitui um bloco que o parser recusou, senão
o "limpo sem lista do que foi examinado" passaria por ela. Resultado negativo com bloco
recusado é aceito com aviso: é o lado conservador, e a rodada queima ficha porque sem bloco
válido não há contagem para medir progresso. No `historico`, a transição sai com
`fonte: "invalido"`.

## Contrato 3 — o quadro do `/mobilizar`

```bash
python3 scripts/quadro.py estado <slug> --json
```

O slug é obrigatório (não há "o único quadro aberto"); quadro inexistente sai com exit 1.

Campos garantidos (`campos` da declaração):

| Campo | Tipo | O que faz por você |
|---|---|---|
| `slug` | string | Qual quadro |
| `spec` | string, opcional | SPEC declarada no `abrir` (`null` se não houve) |
| `cli` | string, opcional | CLI declarado no `abrir` (`null` se não houve) |
| `encerrado` | boolean | `encerrar` já rodou — pare |
| `onda` | integer | Onda corrente: a última aberta por `iniciar` (0 antes do primeiro) |
| `teto_onda` | integer | Máximo de tarefas em voo ao mesmo tempo |
| `total` | integer | Tarefas no quadro |
| `por_estado` | object<string,integer> | Contagem por estado de tarefa (`planejada`, `em_progresso`, `concluida`, `bloqueada`) |
| `completo` | boolean | Toda tarefa concluída com o gate rodado (a concluída com gate pulado não conta, desde 1.3; a `--leitura` sem gate declarado não tem gate a pular). Quadro sem tarefa não é completo |
| `pode_encerrar` | boolean | **O que `encerrar` aceita**: quadro com tarefa, e toda tarefa aberta ou concluída com gate pulado com lacuna declarada. Desde 1.3; antes, o quadro vazio e o gate pulado passavam |
| `em_voo` | string[] | Ids em progresso |
| `prontas` | string[] | **O que lançar agora**: planejada, dependências concluídas, posse livre, vaga na onda |
| `bloqueadas` | string[] | Ids bloqueados |
| `vencidas` | string[] | Em progresso além do tempo limite. Só relata; `quadro.py varrer <slug>` bloqueia e devolve a vaga. Desde 1.1 |
| `lacunas` | string[] | Lacunas declaradas (`encerrar --lacuna "T7: motivo"`) |
| `tasks` | object | As tarefas, por id (a forma de cada uma não é contrato) |

`pode_encerrar` e `vencidas` existem pelo mesmo motivo dos derivados do ciclo: para o
runner não reimplementar "posso dizer que acabou?" e "esse worker morreu?". `iniciar`
recusa tarefa fora de `prontas` e `encerrar` recusa quadro sem `pode_encerrar` — o
quadro decide, o runner lança.

O `concluir` também recusa: com `--evidencia` vazia, sem resultado de gate (`--gate-ok`,
ou `--gate-pulado` com motivo não vazio; os dois juntos recusam desde 1.3), com arquivo
mudado fora da posse (salvo `--fora-da-posse "motivo"`) e, desde 1.3 (ADR-0061), quando
falta uma das duas fotos do checkout, a do `iniciar` ou a de agora (salvo `--sem-foto
"motivo"`, que fica no `ledger`). Quem roda o teammate num worktree próprio passa
`--checkout <worktree>` no `iniciar` e conclui antes de remover o worktree: sem ele, a foto
de agora não sai. E a concluída com gate pulado pede uma lacuna no `encerrar`, como a
tarefa aberta. O quadro sugere o texto: `--lacuna "Tn: gate pulado — motivo"`.

Duas ressalvas de precisão. A saída também traz `contrato` (a versão), mas a declaração
do quadro não o lista em `campos`: leia a versão em `quadro.py contrato --json`. E o
`prontas --json` é citado como público no código, mas não entra na declaração assinada;
prefira o `prontas` do `estado --json`, que é o mesmo cálculo.

## Versionamento

| Mudança | `ciclo` | `contrato` (relatórios) | `quadro` |
|---|---|---|---|
| **MENOR** (1.x) — consumidor antigo segue válido | Campo novo, estado novo, aresta nova | Campo **opcional** novo, fence nova, mensagem de erro diferente | Campo novo, estado novo |
| **MAIOR** (x.0) | Campo removido/renomeado, semântica alterada, aresta removida | Campo **obrigatório** novo ou removido, regra de aceitação mais estrita | Campo removido/renomeado, semântica alterada |

A assimetria dos relatórios tem motivo: ali o consumidor também é **produtor** do
bloco, e campo obrigatório novo faz ser recusado o bloco que ele já emite.

No `ciclo` e no `quadro`, aceitação mais estrita sobe MENOR. Os precedentes são o `ciclo`
1.1 (o verde recusado com a SPEC alterada), o `ciclo` 1.3 (a re-revisão que presta contas)
e o `quadro` 1.2 (a posse exercida). As três versões da v0.54.0 são MENOR (ADR-0061):

- **`ciclo` 1.4** — `premissa_escrita` passa a ter destino calculado (`null` na
  declaração, como o do resultado negativo). Nenhuma aresta saiu: o resultado segue aceito
  nos três `atacando_premissa_*`, e quem relê `estado` depois de cada `registrar`, como o
  laço mínimo manda, não percebe a diferença. O `registrar` passa a recusar o `limpo` da
  faixa 3 e o `pr_aberto` sem PR, e a revisão incompleta deixa de contar como progresso.
- **`contrato` 1.3** — o `bloqueado` da revisão incompleta com `criticos: 0` passa a valer.
  A regra afrouxou: todo bloco que valia segue valendo.
- **`quadro` 1.3** — `completo` deixa de contar a concluída com gate pulado, `pode_encerrar`
  passa a pedir tarefa no quadro e lacuna para o gate pulado, o `concluir` sem uma das
  fotos do checkout pede `--sem-foto`, e o `concluir` com `--gate-ok` e `--gate-pulado`
  juntos é recusado.

A tabela chama de MAIOR a "semântica alterada" do quadro, e o `completo` mudou o que
conta. Ainda assim é MENOR, porque é aceitação mais estrita e não semântica nova. Os dois
campos respondem à mesma pergunta de antes: `completo`, se tudo ficou pronto; `pode_encerrar`,
o que o `encerrar` aceita. Só dizem `true` em menos casos, e cada `false` novo é um `true`
antigo que escondia um gate pulado ou um quadro sem tarefa. O consumidor que já os lia
assim segue certo sem mudar uma linha, e a recusa do `encerrar` diz o que fazer. MAIOR seria
o campo passar a responder outra pergunta.

Quem dirige o arco por fora sente uma mudança: o `registrar pr_aberto` sem `--pr` sai 1, e
um runner antigo o repetiria em laço. O `proximo_passo` já traz o `--pr`. Duas outras pesam
menos. O `registrar limpo` com `faixa: 3` no bloco sai 1, e só muda algo para o runner que
registrava `limpo` em vez de escalar, como o Contrato 2 já pedia. E, com o orçamento padrão,
os estados `atacando_premissa_*` passam a aparecer, sem mudar nada para o laço que segue
`resultados_validos` e `proximo_passo`. Quem dirige o quadro passa a ver recusados o
`concluir` sem foto, o `concluir` com os dois resultados de gate, o `encerrar` com gate
pulado sem lacuna e o `encerrar` de quadro vazio, e cada recusa diz o que fazer.

`contratos/ASSINATURA.json` guarda versão + `sha256` de cada declaração, e o
`release.py check` recalcula em todo PR. Mudou a forma sem reassinar → **CI vermelho**,
com a mensagem dizendo qual bump considerar. Para o `ciclo`, o check também confere que a
saída real de `estado --json` traz todo campo obrigatório declarado; no `contrato` e no
`quadro`, só o digest da declaração. E o digest pega forma, não semântica (ADR-0034):
trocar o significado de um campo mantendo nome e tipo passa no check — isso quem cobre é
revisão.

Isso existe porque contrato que ninguém verifica é promessa: sem o digest, um campo
renomeado passa no code review, é espelhado no `plugin/`, sai numa release, e quem
descobre é o consumidor em produção.

Ao mudar de propósito:

```bash
python3 scripts/release.py assinar-contratos   # depois de ajustar CONTRATO_VERSAO
```

## O que **não** é contrato

- Formato do `.agents/ciclo/<spec>.json` e do `.agents/quadro/<slug>.json` em disco —
  leia via `estado --json` de cada um.
- A forma de cada item de `historico` (ciclo) e de `tasks` (quadro): o contrato declara o
  tipo (`object[]`, `object`), não os campos de dentro.
- Campos que aparecem no `estado --json` sem estar em `campos` — `aberto_em`, `branch`,
  `spec_digest`, `premissas`, `escalacao_apos_premissa` e afins. Saem porque a vista
  espalha o arquivo do ciclo, não porque são promessa; o guardrail usa `branch` para julgar
  o `gh pr create` pelos ciclos da branch atual.
- Saída de terminal de qualquer script — é para humano. Inclui o texto das recusas no
  stderr.
- Nomes de estado como string comparável — use os derivados. A única exceção é separar
  `escalado` de `encerrado`, que nenhum derivado distingue.
- `telemetria.py`, `painel.py`, `diagnostico.py`, `guardrail.py` — úteis, sem promessa
  de estabilidade. Peça promoção a contrato se precisar.
- Nomes e quantidade das 71 personas. São estáveis por convenção do projeto
  (`CLAUDE.md`), não por contrato versionado.

## Pré-requisito do outro lado

Antes de dirigir a fábrica, o repositório precisa estar **harness-ready**: plugin
instalado, `CLAUDE.md`/`AGENTS.md` preenchidos, `contextos/` populado, gates conhecidos,
e telemetria ativa se você quiser corroboração de evidência.

`/kairos-forge:onboardar` faz isso, e `/kairos-forge:auditar` mede. Orquestrador sobre
repositório sem harness não produz autonomia — produz N PRs ruins em paralelo.
