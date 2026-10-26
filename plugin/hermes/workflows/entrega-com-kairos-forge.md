# Workflow: Entrega com kairos-forge

De uma frase do fundador a um PR validado, com a fábrica kairos-forge como
motor de engenharia e o Hermes como operador 24/7.

## Gatilho

```text
construir com a fábrica: [uma frase]
```

## Fluxo

1. Hermes lê o contexto do projeto e a memória; cria o card no kanban.
2. `kairos-forge-fabrica` decide se a tarefa pede a fábrica (multi-arquivo,
   SPEC, legado, UI, eval de IA, deploy) — senão, roteia pro caminho simples
   (Codex ou o próprio Hermes). Feature sensível passa antes por
   `analisar-ameacas`.
3. `kairos-forge-ciclo` conduz o `/kairos-forge:entregar`: enquadrar →
   **gate 1/3 entendimento** → abordagens → **gate 2/3 abordagem** → SPEC →
   crítica adversarial ⇄ corrigir SPEC → **gate 3/3 aprovação da SPEC** →
   (`desenhar`, se houver UI) → construir → validar ⇄ corrigir → revisar →
   corrigir 🔴 → validar e revisar de novo → PR.
4. Cada gate é uma parada: o `claude -p` termina, o Hermes leva ao fundador o
   que a fábrica apresentou — com as perguntas do Pare e Pergunte —, registra a
   resposta no `ciclo.py` e retoma.
5. Depois de cada parada o Hermes lê `ciclo.py estado SPEC-NNN --json` para
   saber se acabou, se precisa do fundador ou se a SPEC mudou depois da
   aprovação.
6. Merge aprovado → card Done, evidência e aprendizados na memória do Hermes.
   Produção, se pedida: `/kairos-forge:lancar`, com SIM explícito.

## Gates do fundador

Aprovação humana no que só gente decide — e, em headless, cada um espera de
verdade:

- os três gates do planejamento: entendimento, abordagem e aprovação da SPEC;
- perguntas do Pare e Pergunte;
- SPEC alterada depois da aprovação (`ciclo.py reaprovar` é decisão do fundador);
- faixa 3 do raio de explosão e qualquer escalação — só o fundador destrava;
- release de produção (SIM explícito, sem default), janela de corte de
  migração, mudança destrutiva de dados e merge.

Escolha reversível no meio do arco segue com o default recomendado e a premissa
registrada.

## Verificação

- PR aberto com SPEC rastreável e criticada, validação sem bloqueio em P1 e
  revisão sem achados críticos
- `historico` do ciclo mostra os três gates respondidos pelo fundador
- Kanban espelhou cada transição com evidência
- Memória do Hermes registra o que foi entregue e o que foi aprendido
