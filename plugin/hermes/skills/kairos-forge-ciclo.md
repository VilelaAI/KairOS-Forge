---
name: kairos-forge-ciclo
description: Use para conduzir o ciclo completo da fábrica em modo headless — o arco /kairos-forge:entregar com os três gates do fundador (entendimento, abordagem, SPEC), construção, validação, revisão e PR — lendo o estado pelo ciclo.py e devolvendo evidência ao kanban do Hermes a cada parada
version: 3.0.0
tags: [ciclo, headless, kairos-forge, entrega]
---

## Visão geral

Executa o ciclo da fábrica de ponta a ponta via `claude -p` (headless), com o
Hermes como operador: o kanban espelha cada transição e as decisões humanas
passam pelo fundador no chat.

**O arco inteiro vive dentro da fábrica.** `/kairos-forge:entregar` (ADR-0023)
conduz planejamento e construção, e quem decide cada transição é o `ciclo.py`
(ADR-0029): orçamento, escalação e "correção da revisão reabre a validação" são
código, não instrução. Esta skill **não reimplementa esse loop** — ela opera o que
só o Hermes faz: o canal com o fundador, o kanban e a memória entre sessões.

Em headless, cada gate humano é uma parada de verdade (ADR-0033): o `claude -p`
apresenta o gate e termina; você leva ao fundador, registra a resposta e retoma.
Uma entrega custa ao menos quatro invocações — até o gate 1/3, até o 2/3, até o
3/3 e a construção.

## Quando usar

- A skill `kairos-forge-fabrica` roteou a tarefa para a fábrica e o fundador
  não vai acompanhar interativamente
- Card do kanban em Ready com descrição suficiente para especificar

## Pré-requisitos

- Os da skill `kairos-forge-fabrica` (Claude Code + plugin + projeto)
- Plugin kairos-forge **v0.34.1 ou superior**: fases com gate (v0.26), `estado
  --json` como contrato (v0.27), `reaprovar` e `spec_alterada` (contrato 1.1).
  Confira com `python3 <plugin>/scripts/ciclo.py contrato` — `versao` 1.1 ou
  maior. Em versão anterior, atualize; sem como, use o procedimento legado no
  rodapé.
- Projeto com git limpo e numa branch própria (não `main`/`master`) — senão o
  `entregar` para no Passo 0 e diz o que falta
- Nenhum outro ciclo aberto nesta cópia do repositório, nem parado em gate (o
  porquê está nas armadilhas da `kairos-forge-fabrica`)
- Card no kanban do Hermes representando a tarefa

`<plugin>` é o diretório do plugin kairos-forge que o Claude Code carrega. Rode o
`ciclo.py` **no diretório do projeto** (o estado fica em `.agents/ciclo/<spec>.json`,
relativo a ele) e passe **sempre** a SPEC.

## Procedimento

### 0. Antes do arco, quando couber

- **Feature sensível** (auth, PII, pagamento, upload, IA com input externo):
  `claude -p "/kairos-forge:analisar-ameacas <feature, quem usa, que dado sensível>"`.
  O modelo de ameaças sai em `docs/seguranca/`; cite o arquivo no prompt do passo 1
  para as mitigações nascerem como requisito na SPEC.
- **Feature com UI:** o `desenhar` precisa da SPEC — ele entra no passo 4.

### 1. Abrir o arco

Toda invocação do `entregar` leva este bloco no fim do prompt — é o que faz cada
gate parar de verdade:

```text
Execução headless conduzida pelo Hermes: ninguém lê esta sessão.
Em estado aguardando_*, com SPEC alterada depois da aprovação ou em escalado,
apresente o que o ciclo.py pede e ENCERRE. Não registre resultado de gate
humano nem rode reaprovar: quem registra a resposta do fundador é o Hermes.
Termine dizendo a SPEC-NNN do ciclo e o estado em que parou.
```

No diretório do projeto:

```bash
claude -p "/kairos-forge:entregar <tarefa com contexto do handoff>
<bloco headless>"
```

Saída esperada: ciclo aberto e parado no gate 1/3. Confirme com
`python3 <plugin>/scripts/ciclo.py estado SPEC-NNN --json` (`ciclo.py listar` mostra
os ciclos, se a saída não disser a SPEC). Card → "aguardando fundador".

**SPEC já aprovada pelo fundador** (sessão interativa, card antigo): pule o
planejamento com `claude -p "/kairos-forge:entregar SPEC-NNN — SPEC aprovada pelo
fundador em <data>; abra o ciclo com --spec-aprovada. <bloco headless>"` e vá ao
passo 4. Só com a aprovação dele registrada no card ou na memória:
`--spec-aprovada` pula os três gates e a crítica.

### 2. Ler o estado depois de cada invocação

Decida pelos campos do contrato (ADR-0034), nunca comparando nome de estado:

| Leitura de `estado SPEC-NNN --json` | Card | O que você faz |
|---|---|---|
| `terminal: true` | ver passo 6 | O desfecho |
| `aguardando_humano: true` | aguardando fundador | Passo 3 |
| `spec_alterada: true` | Blocked | Passo 5 — não liga `aguardando_humano`, mas é decisão do fundador |
| nenhum dos três | Running | O `claude -p` parou no meio (queda, timeout): retome. Parou de novo no mesmo estado → trate como escalação |

`resultados_validos` diz o que o `registrar` aceita agora; `gate` diz qual loop
está em jogo (`criticar`/`validar`/`revisar`).

### 3. Os três gates do fundador

| Gate | O que vai ao chat | Resposta → `registrar` |
|---|---|---|
| 1/3 entendimento | Entendimento espelhado e as perguntas do Pare e Pergunte | confirma → `confirmado` · corrige → `ajustar` |
| 2/3 abordagem | 2-3 abordagens com trade-offs e a recomendada | escolhe → `escolhida` · nenhuma serve → `ajustar` |
| 3/3 SPEC | Objetivo, P1, não-objetivos, perguntas abertas, plano de tarefas e o que a crítica adversarial encontrou | SIM → `aprovada` · NÃO → `recusada` · AJUSTAR → nada a registrar |

Registre a resposta você mesmo e retome colando o que ele disse — a conversa não
atravessa invocações:

```bash
python3 <plugin>/scripts/ciclo.py registrar <resultado> SPEC-NNN
claude -p "/kairos-forge:entregar SPEC-NNN — retome do estado atual do ciclo.py.
O fundador respondeu ao gate <N/3>: <resposta literal>
<bloco headless>"
```

- **Nunca responda por ele.** Pergunta do Pare e Pergunte sem resposta é gate não
  confirmado.
- **AJUSTAR no 3/3 não tem aresta** — ali o `ciclo.py` só aceita `aprovada` e
  `recusada`. Não registre: retome com o ajuste e espere a SPEC voltar ao gate.
- **Em headless não há atalho de feature Pequena:** os gates 1 e 2 numa mensagem só
  valem em sessão interativa (ADR-0038).
- **`registrar` saiu 1?** Releia `estado`: mudou, já estava registrado — siga; não
  mudou, é recusa real — o motivo está no stderr.

Entre o 2/3 e o 3/3 a fábrica escreve a SPEC e ao menos dois críticos que não a
escreveram a atacam; achado volta para a SPEC e a crítica reabre. Orçamento da
crítica esgotado chega como `escalado` (passo 6).

### 4. Construção — o arco fecha sozinho

Com `aprovada`, o ciclo entra em construção e a SPEC aprovada fica **selada**
(digest do contrato). **Feature com UI:** antes de retomar, rode
`claude -p "/kairos-forge:desenhar SPEC-NNN"` e releia o `estado` — critério visual
que entra na SPEC liga `spec_alterada`: siga o passo 5 com o DESIGN junto.

```bash
claude -p "/kairos-forge:entregar SPEC-NNN — retome do estado atual do ciclo.py.
<bloco headless>"
```

Card → Running. Enquanto roda, a fábrica:

- constrói pela SPEC por `rodar` — em headless o `entregar` não usa `mobilizar`;
- valida e, se bloquear em P1, corrige e revalida;
- revisa e, se houver achado 🔴, corrige — e a correção **reabre a validação**
  antes de nova revisão;
- na faixa 3 do raio de explosão (migration destrutiva, deleção, produção, dinheiro,
  credencial) não fecha por evidência: escala;
- abre o PR com a evidência no corpo.

O orçamento é do `ciclo.py`: por padrão 2 rodadas **sem progresso** por gate —
rodada que baixa a contagem de achados devolve a ficha — e teto absoluto de 6. Não
negocie rodada no prompt: quem conta é o script.

O relatório final sai em `docs/specs/entregas/ENTREGA-SPEC-NNN-<data>.md`, com a
linhagem de rodadas. **Use esse arquivo como nota de progresso do card** — ele já
tem o que o kanban precisa, incluindo as rodadas que falharam.

### 5. SPEC alterada depois da aprovação

Com `spec_alterada: true`, o `ciclo.py` recusa resultado verde de gate até um humano
aceitar a versão nova. Leve ao fundador o diff que o `entregar` apresentou (e o
DESIGN, se veio do `desenhar`):

- aceitou → `python3 <plugin>/scripts/ciclo.py reaprovar SPEC-NNN` e retome;
- não aceitou → retome pedindo que a SPEC volte à versão aprovada.

**`reaprovar` é decisão dele — nunca rode por conta própria.**

### 6. Ler o desfecho e agir

Nenhum derivado separa os dois terminais: com `terminal: true`, e só aí, o `estado`
diz como acabou.

| Desfecho | Card | O que você faz |
|---|---|---|
| `encerrado`, `pr_aberto` no `historico` | "aguardando merge" + link | Nada além de avisar o fundador |
| `encerrado`, `recusada` no `historico` | Done — SPEC recusada | Registre na memória o que ele recusou e por quê |
| `escalado`, `motivo_escalacao` de orçamento ou teto | Blocked | Leve ao chat: o que ficou pronto, o que faltou, o último bloqueio, e a escolha — ampliar orçamento ou fatiar a SPEC |
| `escalado`, outro motivo | Blocked | Leve a pergunta exata que a fábrica formulou (faixa 3, decisão fora da SPEC, duas falhas iguais, Pare e Pergunte na construção), com o que já foi tentado |

`encerrado` por `ciclo.py encerrar` traz o porquê em `motivo_encerramento`.

Depois de `escalado`, **não reinvoque o `entregar` por conta própria** — só o
fundador destrava. Duas falhas materialmente iguais nunca viram terceira
tentativa. Com a decisão dele de ampliar o orçamento, copie o `historico` do
`estado --json` para a nota do card — o novo `abrir` recomeça o arquivo do ciclo do
zero —, reabra você mesmo e retome:

```bash
python3 <plugin>/scripts/ciclo.py abrir SPEC-NNN --orcamento-<gate> N [--spec-aprovada]
```

`--spec-aprovada` só se a SPEC já estava aprovada; sem ele o ciclo recomeça do
enquadramento. Fatiar a SPEC é um `entregar` novo por fatia.

### 7. Lançar (opcional, pós-merge)

Se o fundador pedir produção:

```bash
claude -p "/kairos-forge:lancar — release da SPEC-NNN"
```

O gate do deploy chega ao fundador pelo chat — o que muda, plano de rollback e
gatilho — e pede **SIM explícito, sem default**. Com o SIM, retome citando a
resposta. Health check em três camadas e rollback anotado fazem parte da skill; o
monitoramento contínuo depois é do Hermes.

### 8. Encerrar

Merge é decisão do fundador (ou do fluxo de PR do oh-my-hermes, se instalado).
Após o merge: card → Done, salve na memória do Hermes `SPEC-NNN entregue em
<data>, PR #N` e registre aprendizados relevantes.

## Armadilhas

- **Não pule gate — nem os dois primeiros.** Sem ninguém lendo, premissa errada
  queima o orçamento inteiro construindo a coisa errada com disciplina impecável.
- **A conversa não atravessa invocações; o estado, sim.** O arco persiste em
  `.agents/ciclo/<spec>.json`. Cada prompt cita a SPEC-NNN (o `proximo_passo` do
  `ciclo.py` não a nomeia) e cola o que o fundador respondeu.
- **Sempre passe a SPEC ao `ciclo.py`.** Sem ela o script procura "o único ciclo
  aberto": com dois abertos recusa, e com o ciclo já fechado não responde.
- **Leia e escreva o ciclo só pelo `ciclo.py`.** O JSON em disco não é contrato.
- **Não reimplemente o loop de correção aqui.** Se o `entregar` falhou, a
  informação útil é o motivo que ele reportou (`motivo_escalacao`), não uma
  segunda tentativa cega.
- **Telemetria não cruza invocações de `claude -p` como cruza uma sessão
  interativa.** A dimensão Autonomia do `/auditar` vai enxergar cada invocação
  como um ciclo próprio — ao ler o número, lembre que o fluxo Hermes é headless
  por desenho.

## Verificação

- Os três gates passaram pelo fundador antes de qualquer implementação — o
  `historico` mostra `confirmado`, `escolhida` e `aprovada`, ou o ciclo foi aberto
  com `--spec-aprovada` sobre SPEC que ele já tinha aprovado
- `entregar` encerrou com PR aberto, ou o motivo do bloqueio foi levado ao chat
- Card do kanban espelha cada transição com evidência
- Com PR aberto, `docs/specs/entregas/ENTREGA-*.md` existe e registra as rodadas
  consumidas

---

## Procedimento legado (plugin que não dá para atualizar)

Sem o arco do `ciclo.py` na versão exigida, o Hermes conduz o loop à mão — era o
comportamento da v1.0 desta skill. Ordem e orçamento passam a depender de você
contar certo; diga isso ao fundador.

1. `claude -p "/kairos-forge:especificar <tarefa>"` — leve ao fundador o que ela
   apresentar e só siga com a SPEC aprovada
2. `claude -p "/kairos-forge:rodar — implementar a SPEC-NNN seguindo o plano de tarefas, com os gates de cada tarefa"`
3. `claude -p "/kairos-forge:validar SPEC-NNN"` — bloqueio em P1 volta ao passo 2
   (máximo 2 rodadas; na terceira, escale ao fundador)
4. `claude -p "/kairos-forge:revisar"` — achado 🔴 volta ao passo 2 **e passa de
   novo pelo passo 3** antes de nova revisão; sem críticos, abra o PR

Atualize o plugin quando puder: no `entregar`, estado e orçamento vivem em
`.agents/ciclo/` e a transição é decidida por código — aqui, por você.
