# Máquina de estados, orçamento e pré-condições

Material de apoio da skill `entregar`. Leia quando for **abrir um ciclo** (Passo 0),
quando precisar entender **por que o `ciclo.py` decide a transição** e não você, ou
quando o `ciclo.py` não estiver disponível e o arco tiver de ser conduzido pela prosa.

## Pré-condições

Antes da rodada 1, verifique. Faltando qualquer uma, diga o que falta e pare:

| Condição | Verificação | Se faltar |
|---|---|---|
| Git limpo | `git status` sem mudança não commitada | Commit ou stash — o arco precisa de revert barato |
| Branch própria | Não estar em `main`/`master` | Crie a branch antes |
| Gates conhecidos | `contextos/testes.md` ou comandos evidentes do projeto | Registre como `<a definir>` e avise que a validação fica mais fraca |
| Telemetria (recomendado) | `.agents/execucoes/` existe | Sem ela o `/validar` não corrobora evidência (ADR-0021) — siga, mas declare |

## Quem decide o próximo passo (ADR-0029)

**Não é você.** O arco é uma máquina de estados em `scripts/ciclo.py`, e a
transição é decidida por código. Você **executa** o passo e **registra** o que
aconteceu; o script diz o que vem depois.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ciclo.py estado          # qual o passo agora
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ciclo.py registrar <res> # o que aconteceu
```

Três coisas deixam de depender da sua disciplina:

- **O orçamento é fato.** Esgotou, `registrar` devolve `escalado` — não existe
  "mais uma rodada, dessa vez vai".
- **Correção de revisão reabre a validação.** Você não escolhe voltar pra
  revisão: o script só tem essa aresta.
- **Veredicto vem do artefato.** `registrar aprovado` sem relatório em
  `docs/specs/validacoes/` é recusado; com relatório dizendo bloqueado, também.
  Vale igual para a revisão (`docs/specs/revisoes/`) desde a v0.24.
- **Progresso real devolve a ficha (ADR-0032).** O `ciclo.py` lê a contagem de
  achados do bloco de contrato do relatório e compara com a melhor marca do
  gate. Baixou de 5 para 2, a rodada não é cobrada; continuou em 5, é. Convergir
  não é patinar, e o orçamento plano tratava os dois igual. Um **teto absoluto**
  de rodadas segue valendo por cima — progresso não compra rodada infinita.

E o `gh pr create` fica **bloqueado pelo guardrail** enquanto o estado não for
`pronto_para_pr` (ADR-0022). Não é sugestão.

Se o `ciclo.py` não estiver disponível (CLI sem os scripts do plugin), conduza o
arco pela prosa abaixo e **diga ao usuário** que o orçamento está sendo contado
por você, não imposto.

## Passo 0 — Abrir o ciclo com o orçamento

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ciclo.py abrir SPEC-NNN \
  --orcamento-criticar 2 --orcamento-validar 2 --orcamento-revisar 2
# use --spec-aprovada quando a SPEC já existe e já foi aprovada
```

Anuncie ao usuário o que foi aberto — é o contrato da autonomia deste ciclo:

```
🔁 Entrega — <feature/SPEC> — orçamento declarado

Rodadas sem progresso por gate: 2 em criticar · validar · revisar — teto 6 cada
Checkpoint com você:           entendimento · abordagem · SPEC · antes do PR
Escalação:                     orçamento sem progresso esgotado, teto atingido,
                               ou 2 falhas materialmente iguais
Evidência mínima pra encerrar: P1 sem bloqueio no /validar + zero 🔴 no /revisar
Modo de construção:            mobilizar (paralelo) | rodar (sequencial)
```

**Avisa-e-pausa (ADR-0013):** ao cruzar ~80% de qualquer limite, avise no
checkpoint seguinte. O `ciclo.py estado` mostra as rodadas consumidas a qualquer
momento, e `painel.py <SPEC>` mostra o arco inteiro numa tela — requisitos,
fichas, veredicto dos dois gates e trajetória:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/painel.py SPEC-NNN
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/painel.py SPEC-NNN --html quadro.html  # para mandar pra alguém
```

Escolha do modo de construção: `mobilizar` se as tarefas forem independentes e
as ferramentas de Agent Teams existirem; `rodar` no resto (e sempre em Codex,
OpenCode, Cursor ou execução headless).
