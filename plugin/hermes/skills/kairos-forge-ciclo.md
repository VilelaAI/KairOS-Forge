---
name: kairos-forge-ciclo
description: Use para conduzir o ciclo completo da fábrica em modo headless — especificar, aprovar, construir, validar, revisar e abrir PR — devolvendo evidência ao kanban do Hermes a cada etapa
version: 1.0.0
tags: [ciclo, headless, kairos-forge, entrega]
---

## Visão geral

Executa o ciclo da fábrica de ponta a ponta via `claude -p` (headless), com o
Hermes como operador: cada etapa devolve evidência ao kanban e as decisões
irreversíveis passam pelo fundador no chat. O ciclo usa `rodar` (sequencial);
`mobilizar` (paralelo via Agent Teams) requer sessão interativa e fica fora
do modo headless.

## Quando usar

- A skill `kairos-forge-fabrica` roteou a tarefa para a fábrica e o fundador
  não vai acompanhar interativamente
- Card do kanban em Ready com descrição suficiente para especificar

## Pré-requisitos

- Os da skill `kairos-forge-fabrica` (Claude Code + plugin + projeto)
- Card no kanban do Hermes representando a tarefa

## Procedimento

Etapas em sequência — cada uma atualiza o card antes da próxima:

1. **Especificar.** No diretório do projeto:

   ```bash
   claude -p "/kairos-forge:especificar <tarefa com contexto do handoff>"
   ```

   Saída esperada: `docs/specs/SPEC-NNN-<slug>.md`. Card → "aguardando
   aprovação" com o caminho da SPEC e o resumo dos requisitos P1.

2. **Gate do fundador.** Envie ao chat: objetivo da SPEC, requisitos P1,
   não-objetivos e perguntas abertas. Espere SIM / NÃO / AJUSTAR. Se a SPEC
   tiver perguntas abertas (Pare e Pergunte), elas vão nesta mensagem —
   nunca responda por ele.

3. **Construir.**

   ```bash
   claude -p "/kairos-forge:rodar — implementar a SPEC-NNN seguindo o plano de tarefas, com os gates de cada tarefa"
   ```

   Card → Running, com o quadro vivo da fábrica (tarefas Pronto ✓gate) como
   nota de progresso.

4. **Validar.**

   ```bash
   claude -p "/kairos-forge:validar SPEC-NNN"
   ```

   Bloqueio em requisito P1 → card → Blocked com o motivo exato e volta à
   etapa 3 (máximo 2 rodadas de correção; na terceira, escale ao fundador).

5. **Revisar e abrir PR.**

   ```bash
   claude -p "/kairos-forge:revisar"
   ```

   Achado crítico 🔴 volta à etapa 3. Sem críticos → abrir PR com o resumo
   da revisão no corpo. Card → "aguardando merge" com o link do PR.

6. **Encerrar.** Merge é decisão do fundador (ou do fluxo de PR do
   oh-my-hermes, se instalado). Após o merge: card → Done, salve na memória
   do Hermes `SPEC-NNN entregue em <data>, PR #N` e registre aprendizados
   relevantes.

## Armadilhas

- Não pule a etapa 2: implementar SPEC não aprovada desperdiça o ciclo
  inteiro quando o fundador queria outra coisa.
- `claude -p` não guarda estado entre etapas — cada comando cita a SPEC-NNN
  explicitamente.
- Duas falhas materialmente iguais na mesma etapa: pare e pergunte ao
  fundador em vez de insistir (mesma regra do Hermes).

## Verificação

- SPEC aprovada pelo fundador antes de qualquer implementação
- `/kairos-forge:validar` sem bloqueio em P1
- PR aberto com revisão sem achados críticos
- Card do kanban espelha cada transição com evidência
