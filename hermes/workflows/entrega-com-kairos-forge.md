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
   SPEC, migração, eval de IA) — senão, roteia pro caminho simples (Codex ou
   o próprio Hermes).
3. `kairos-forge-ciclo` roda: especificar → **aprovação do fundador** →
   construir → validar → revisar → PR.
4. Perguntas da fábrica (Pare e Pergunte) chegam ao fundador pelo chat; as
   respostas voltam ao ciclo.
5. Merge aprovado → card Done, evidência e aprendizados na memória do Hermes.

## Gates do fundador

Aprovação humana somente no que é irreversível: SPEC antes de implementar,
release de produção, rollback, janela de corte de migração, mudança
destrutiva de dados. Todo o resto segue com defaults declarados.

## Verificação

- PR aberto com SPEC rastreável, validação sem bloqueio em P1 e revisão sem
  achados críticos
- Kanban espelhou cada transição com evidência
- Memória do Hermes registra o que foi entregue e o que foi aprendido
