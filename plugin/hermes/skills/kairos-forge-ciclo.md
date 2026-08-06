---
name: kairos-forge-ciclo
description: Use para conduzir o ciclo completo da fábrica em modo headless — especificar, aprovar, entregar (construir, validar, corrigir, revisar, corrigir, PR) — devolvendo evidência ao kanban do Hermes a cada etapa
version: 2.0.0
tags: [ciclo, headless, kairos-forge, entrega]
---

## Visão geral

Executa o ciclo da fábrica de ponta a ponta via `claude -p` (headless), com o
Hermes como operador: o kanban espelha cada transição e as decisões
irreversíveis passam pelo fundador no chat.

**Desde a v0.18 do plugin, o arco de correção vive dentro da fábrica.** A skill
`/kairos-forge:entregar` (ADR-0023) já faz construir → validar ⇄ corrigir →
revisar ⇄ corrigir → PR, roteando cada falha ao agente responsável dentro de um
orçamento declarado. Esta skill **não reimplementa esse loop** — ela opera o que
só o Hermes faz: o canal com o fundador, o kanban e a memória entre sessões.

## Quando usar

- A skill `kairos-forge-fabrica` roteou a tarefa para a fábrica e o fundador
  não vai acompanhar interativamente
- Card do kanban em Ready com descrição suficiente para especificar

## Pré-requisitos

- Os da skill `kairos-forge-fabrica` (Claude Code + plugin + projeto)
- Plugin kairos-forge **v0.18.0 ou superior** (a skill `entregar` precisa
  existir). Em versão anterior, use o procedimento legado no rodapé.
- Card no kanban do Hermes representando a tarefa

## Procedimento

### 1. Especificar

No diretório do projeto:

```bash
claude -p "/kairos-forge:especificar <tarefa com contexto do handoff>"
```

Saída esperada: `docs/specs/SPEC-NNN-<slug>.md`. Card → "aguardando aprovação"
com o caminho da SPEC e o resumo dos requisitos P1.

### 2. Gate do fundador — o ponto que só existe aqui

Envie ao chat: objetivo da SPEC, requisitos P1, não-objetivos e perguntas
abertas. Espere **SIM / NÃO / AJUSTAR**.

Se a SPEC tiver perguntas abertas (Pare e Pergunte), elas vão nesta mensagem —
**nunca responda por ele**. Este é o gate que a fábrica não pode fechar sozinha,
e é a razão de o ciclo ser duas invocações e não uma.

### 3. Entregar — o arco fechado roda dentro da fábrica

```bash
claude -p "/kairos-forge:entregar SPEC-NNN — a SPEC já foi aprovada pelo fundador,
comece do passo 3 (construir). Orçamento: 2 rodadas de correção por gate.
Se precisar de decisão fora da SPEC, ou se o orçamento esgotar, PARE e reporte
em vez de seguir."
```

Card → Running. Enquanto roda, a fábrica:

- constrói pela SPEC (`rodar` — `mobilizar` exige sessão interativa);
- valida e, se bloquear em P1, corrige e revalida (até 2 rodadas);
- revisa e, se houver achado 🔴, corrige e rerrevisa (até 2 rodadas);
- abre o PR com a evidência no corpo.

O relatório final sai em `docs/specs/entregas/ENTREGA-SPEC-NNN-<data>.md`, com a
linhagem de rodadas. **Use esse arquivo como nota de progresso do card** — ele já
tem o que o kanban precisa, incluindo as rodadas que falharam.

### 4. Ler o desfecho e agir

A skill `entregar` encerra em um de três estados. Cada um tem um destino
diferente no kanban:

| Desfecho | Card | O que você faz |
|---|---|---|
| **PR aberto** | "aguardando merge" + link | Nada além de avisar o fundador |
| **Escalado** | Blocked | Leve ao chat a pergunta específica que a fábrica formulou, com o que já foi tentado |
| **Encerrado por orçamento** | Blocked | Leve ao chat: o que ficou pronto, o que faltou, e a escolha — ampliar orçamento ou fatiar a SPEC |

Nos dois últimos casos, **não reinvoque o `entregar` por conta própria.** Duas
falhas materialmente iguais nunca viram terceira tentativa — é a mesma regra do
Hermes e da fábrica, e reiniciar o arco sem decisão nova só queima orçamento.

### 5. Lançar (opcional, pós-merge)

Se o fundador pedir produção:

```bash
claude -p "/kairos-forge:lancar — release da SPEC-NNN"
```

O gate de aprovação do deploy chega ao fundador pelo chat (**SIM explícito, sem
default**). Health check em três camadas e rollback anotado fazem parte da skill.

### 6. Encerrar

Merge é decisão do fundador (ou do fluxo de PR do oh-my-hermes, se instalado).
Após o merge: card → Done, salve na memória do Hermes `SPEC-NNN entregue em
<data>, PR #N` e registre aprendizados relevantes.

## Armadilhas

- **Não pule a etapa 2.** Implementar SPEC não aprovada desperdiça o ciclo
  inteiro quando o fundador queria outra coisa.
- **`claude -p` não guarda estado entre etapas** — cada comando cita a SPEC-NNN
  explicitamente e diz de onde começar.
- **Não reimplemente o loop de correção aqui.** Se o `entregar` falhou, a
  informação útil é o motivo que ele reportou, não uma segunda tentativa cega.
- **Telemetria não cruza invocações de `claude -p` como cruza uma sessão
  interativa.** A dimensão Autonomia do `/auditar` vai enxergar cada invocação
  como um ciclo próprio — ao ler o número, lembre que o fluxo Hermes é headless
  por desenho.

## Verificação

- SPEC aprovada pelo fundador antes de qualquer implementação
- `entregar` encerrou com PR aberto, ou o motivo do bloqueio foi levado ao chat
- Card do kanban espelha cada transição com evidência
- `docs/specs/entregas/ENTREGA-*.md` existe e registra as rodadas consumidas

---

## Procedimento legado (plugin anterior à v0.18)

Sem a skill `entregar`, o Hermes conduz o loop à mão — era o comportamento da
v1.0 desta skill:

1. `claude -p "/kairos-forge:rodar — implementar a SPEC-NNN seguindo o plano de tarefas, com os gates de cada tarefa"`
2. `claude -p "/kairos-forge:validar SPEC-NNN"` — bloqueio em P1 volta ao passo 1
   (máximo 2 rodadas; na terceira, escale ao fundador)
3. `claude -p "/kairos-forge:revisar"` — achado 🔴 volta ao passo 1; sem críticos,
   abra o PR

Atualize o plugin quando puder: o arco dentro da fábrica preserva contexto entre
as etapas, o que o encadeamento de `claude -p` não faz.
