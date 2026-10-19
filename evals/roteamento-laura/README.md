# Eval de roteamento da Laura

Gold set de pedidos em linguagem natural → agente(s) que a Laura (Tech Lead)
deveria acionar. É o eval de regressão do roteamento da fábrica: sempre que um
prompt de agente, uma `description` ou o `squad-fabrica.yaml` mudar, rode antes
de commitar. Conduzido pela **Alice (Evals de IA)** — o gerador nunca avalia a
si mesmo, e é exatamente por isso que o gold set vive fora dos prompts.

> Este diretório é do **desenvolvimento do plugin** (dogfooding) — não é
> distribuído em `plugin/` nem chega aos usuários finais.

## Formato

`gold.jsonl` — um caso por linha:

```json
{"pedido": "A fila está entregando a mesma mensagem duas vezes", "esperado": ["murilo-eventos"]}
```

- `pedido` — o que o usuário diria, sem citar nome de agente.
- `esperado` — lista de ids aceitáveis (acerto = a Laura acionar **qualquer um**
  deles; casos com mais de um id são fronteiras onde múltiplas respostas são
  defensáveis, como o trio do pre-mortem).

## Como rodar

**Na sessão (manual):** peça à Alice — "Alice, roda o eval de roteamento da
Laura em `evals/roteamento-laura/gold.jsonl`". Para cada caso ela apresenta o
`pedido` à Laura (sem revelar o esperado), registra qual agente foi acionado e
fecha o relatório com acurácia e os erros caso a caso.

**Headless (ADR-0025):** o `rodar.py` apresenta cada `pedido` à Laura via `claude -p`,
com o catálogo de ids injetado, compara com o `esperado` e falha abaixo do limiar:

```bash
python3 evals/roteamento-laura/rodar.py                  # todos os casos, limiar 90%
python3 evals/roteamento-laura/rodar.py --amostra 15     # subconjunto barato
python3 evals/roteamento-laura/rodar.py --limiar 85 --json
```

Sem o CLI `claude` ou sem credencial ele sai 0 e diz que pulou: CLI deslogado é eval
que não rodou, não 0% de acurácia. No CI, o job `eval-roteamento` roda no merge para
`main` ou por disparo manual — não em todo PR, porque custa tokens.

## Critérios

- **Limiar:** ≥ 90% de acerto. Abaixo disso, a mudança que causou a queda volta.
- **Empate/fronteira:** se a Laura acionar um agente defensável que não está no
  `esperado`, discuta — ou o gold set ganha o id (fronteira legítima), ou a
  `description` do agente precisa ficar mais nítida. Nunca ajuste o gold set só
  para o número passar (Goodhart).
- **Regra de regressão:** mudou prompt da Laura, `description` de agente ou
  roteamento no `squad-fabrica.yaml` → rode o eval na sessão antes do commit.

## Parte determinística

`scripts/release.py check` (roda em todo PR) valida que todo id citado em
`esperado` existe em `agents/` — gold set nunca aponta para agente morto.
A acurácia depende de LLM: é o `rodar.py`, no job à parte, ou a Alice na sessão.

## Ainda sem conjunto selado

Os 68 casos estão todos no visível. O `/kairos-forge:avaliar` manda separar ~40% em
`selado.jsonl` e aprovar só pelo selado (ADR-0030), e o `prova.py selado` — que já roda
dentro do `release.py check` — passa a proteger esse arquivo assim que ele existir:
caso selado copiado para uma `description` ou repetido no `gold.jsonl` reprova o CI
(ADR-0043). Enquanto não houver divisão, o número deste eval mede o visível, onde os
prompts já foram ajustados.
