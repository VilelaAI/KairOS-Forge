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
| `kairos-forge/ciclo` | `ciclo.py estado <SPEC> --json` | 1.1 | Qual o próximo passo, precisa de humano, o que registrar, se a SPEC mudou |
| `kairos-forge/contrato` | `contrato.py <gate> <arquivo>` | 1.0 | Ler o veredicto dos relatórios sem parsear prosa |
| `kairos-forge/quadro` | `quadro.py estado <slug> --json` | 1.1 | O que o `/mobilizar` pode lançar agora, o que venceu o prazo, se o quadro pode encerrar (ADR-0035/0036) |

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
| `motivo_escalacao` | string, opcional | Por que escalou: orçamento esgotado sem progresso, teto absoluto ou `ciclo.py escalar --motivo`. Ausente até a primeira escalação |
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

E em `revisando`, antes de `registrar limpo`, leia a `faixa` do relatório: com `3`, o
`/entregar` não registra `limpo`, escala (ver as regras do Contrato 2).

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
progresso, impõe teto absoluto e escala sozinho. Não reimplemente nada disso — chame.

E o estado vive em `.agents/ciclo/<spec>.json`, atômico via `os.replace`: sobrevive a
restart do seu daemon, troca de CLI e reset de contexto. Não guarde cópia.

### Exit 1 do `registrar`

**Registrar é idempotente por construção, e há teste para isso** (`scripts/tests/test_ciclo.py`):
um runner com semântica at-least-once que repete `registrar <resultado> <SPEC>` depois de
um crash não avança dois estados — o resultado deixa de ser válido no estado novo e é
recusado com exit 1.

Mas exit 1 não quer dizer só "já registrei". O `registrar` sai com 1, stdout vazio e o
motivo no **stderr** em seis casos:

- resultado fora de `resultados_validos` — a repetição, ou o agente registrou errado;
- ciclo em estado terminal — inclusive quando a repetição cai num terminal
  (`pr_aberto` → `encerrado`);
- resultado verde de gate com `spec_alterada: true`;
- resultado verde com o relatório mais recente do gate dizendo `bloqueado`;
- resultado verde sem relatório do gate, ou com relatório sem bloco válido e sem linha
  `**Veredicto:**` reconhecível;
- SPEC sem ciclo (`abrir` nunca rodou para ela).

A regra: **depois de exit 1, releia `estado`.** Mudou desde a leitura que precedeu o
`registrar`? A transição já tinha acontecido — siga. Não mudou? É recusa real: leve o
stderr a quem resolve (o agente, se falta relatório ou ele diz `bloqueado`; o humano, se
`spec_alterada`) e não repita o mesmo `registrar` sem mudar nada, porque isso é laço. O
texto do stderr é para gente, não é contrato: repasse, não parseie.

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
2. **Prova de cobertura** — contagem 0 exige a lista de cobertura não-vazia: `verificado`
   na validação, `examinado` na crítica e na revisão.
3. **Independência** (só na crítica) — ao menos 2 nomes distintos em `criticado_por`,
   sem diferenciar maiúscula.
4. **Faixa** (só na revisão) — `faixa` obrigatória: 1 (contida), 2 (ampla) ou 3 (difícil
   de reverter).
5. **Último bloco fechado vence** — rascunho anterior é ignorado; bloco sem fence de
   fechamento não conta e vira `ausente` (tolera CRLF, fence colada no texto anterior e
   indentação até 3 espaços).
6. **Teto de itens** — lista com mais de 200 itens é `estrutural`.

E duas que o parser não cobra, mas que mudam o que o runner faz:

- **Faixa 3 nunca fecha por evidência** (ADR-0031). Está declarada no `esquema`, mas o
  parser só confere o valor, e o `ciclo.py` aceita `registrar limpo` com `faixa: 3`.
  Quem para é o `/entregar`, com `ciclo.py escalar <SPEC> --motivo "faixa 3: ..."`; um
  runner deve fazer o mesmo.
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
| `sem_cobertura` | Limpo sem lista | **Achado**, não retry — o relatório está errado |

Atenção: o `ciclo.py` aplica essa tabela só em parte. **Qualquer** falha do bloco, não só
`ausente`, o faz cair para a linha `**Veredicto:**` da prosa, sem contagem — um relatório
`sem_cobertura` com `**Veredicto:** aprovado` passa no `registrar aprovado`. Quem quer a
regra cobrada roda `contrato.py <gate> <arquivo>` antes de registrar e não registra
resultado verde quando ele sai 1 (o código de erro sai no stderr, entre colchetes).

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
| `completo` | boolean | Toda tarefa concluída |
| `pode_encerrar` | boolean | **O que `encerrar` aceita**: `completo`, ou toda tarefa aberta com lacuna declarada |
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
