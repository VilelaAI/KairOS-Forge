---
name: relatar
description: Responde o que foi entregue, por que foi decidido assim e quanto custou em tokens, com a fonte de cada número, e monta o status do período. Use para "o que entregamos", "quanto gastamos", "por que decidimos". Pontuar a fábrica é o auditar.
---

# Relatar — o que entregamos, por que e quanto custou

Você está sendo invocado para dizer, com evidência, o que a fábrica entregou num período,
por que as decisões foram tomadas e quanto isso custou. Quem fala é a **Talita [Entregas]**
(`apoio-talita-entregas`): status é leitura de evidência, nunca sentimento.

Esta skill **lê e relata**. Não roda gate, não muda SPEC, ciclo nem quadro. A única escrita
é o arquivo do relatório, quando ele for pedido.

## Regras

1. **Número sem fonte não entra.** Todo número vem de um comando abaixo ou de um arquivo, e
   leva a fonte ao lado. O modelo escreve a prosa; os números são dos scripts.
2. **Sem dado, escreva "não medido".** Nunca 0 e nunca estimativa. Tokens e trajetória só
   existem onde há hook (no Claude Code completo; no Codex e no OpenCode, não). PRs saem do
   git em qualquer CLI.
3. **Custo é em tokens, nunca em dinheiro.** O plugin não conhece preço nem plano (ADR-0044,
   ADR-0048).
4. **Pronto só com `verificado:`.** Requisito "Concluído" sem verificação conta como em
   andamento, a mesma régua do `painel.py`.
5. **Notícia ruim primeiro.** Ciclo escalado, tarefa bloqueada e gate esperando alguém abrem
   o relatório.
6. **Meça a linha, nunca as pessoas.** Nenhum número por nome de pessoa: painel com nome vira
   ranking, e ranking faz o time contornar a medição.

## Passo 0 — janela e alvo

- Sem argumento: os últimos **7 dias**, a fábrica toda.
- `relatar 30`: os últimos 30 dias.
- `relatar SPEC-012`: só essa SPEC (passe o id ao `painel.py`).

Os scripts ficam em `<plugin>/scripts/`. No Tucano, em `.kairos-forge/scripts/`. Rode-os na
raiz do projeto.

## De onde vem cada resposta

| Pergunta | Comando | O que ler |
|---|---|---|
| O que entregamos? | `telemetria.py prs --dias N` | PRs mesclados, quantos têm código da fábrica e quantos não tiveram nenhum commit humano. Com `--fonte git`, só merges com commit de merge (squash não aparece) |
| O que entregamos aguenta? | `telemetria.py comparar --dias N` | PRs revertidos ou corrigidos em até 14 dias, da fábrica e das pessoas lado a lado. Só compara com 5+ PRs de janela fechada em cada grupo; abaixo disso, diga "não comparável" e dê os N |
| Em que pé estão as SPECs? | `painel.py --json --dias N [SPEC]` | Progresso por SPEC, P1 abertos, `sem_prova`, último veredicto de crítica, validação e revisão, estado de cada ciclo |
| O que espera por alguém? | `painel.py --caixa` (com `--github` se o usuário autorizar o `gh`) | Gate humano, SPEC alterada depois de aprovada, ciclo escalado, tarefa bloqueada ou vencida |
| Quanto custou? | `telemetria.py por-spec --dias N`; por sessão, `telemetria.py tokens`; por tarefa, `quadro.py ledger <slug>` | Tokens novos e cache lido por SPEC (a chave é o branch do ciclo, o id no nome do branch ou o id citado; o resto fica em "sem SPEC"); no ledger, por tarefa concluída, desfeita e em aberto |
| Onde o trabalho esperou? | `telemetria.py espera --dias N` | Por ciclo: lead time, trabalho e espera por pessoa (os gates `aguardando_*` e o PR esperando merge), a maior espera e as voltas de correção |
| Como foi o processo? | `telemetria.py resumo --dias N` | Gates verdes de primeira, rodadas de correção, recusas e falhas do guardrail, sessões com produção sem gate, e as perguntas por falta de fonte (`falta-fonte`), por fonte |
| A revisão está acertando? | `telemetria.py ruido --dias N [--github]` | Achados descartados por revisor; com `--github`, também na revisão do gatilho no PR |
| Que decisões entraram? | `git log --since="N days ago" --diff-filter=A --name-only --format= -- docs/adr decisoes` | ADRs e registros novos no período; o título é a primeira linha `# ` |
| Por que decidimos X? | `grep -rni "<termo>" docs/adr decisoes docs/specs`; com grafo, `grafo.py subgrafo <entidade>` | Cite `arquivo:linha`. Sem registro, diga "decisão não registrada" e sugira um ADR, sem reconstruir o porquê de memória |

Para uma pergunta só, rode só o comando dela e responda em poucas linhas, com a fonte.

## O status do período

Quando o pedido for o relatório inteiro ("status da semana", "relatório executivo", "resumo
da sprint"), rode os comandos da tabela e monte nesta ordem:

```markdown
# Status — <projeto> — <AAAA-MM-DD> (últimos N dias)

Entregue: <1 linha> · Em andamento: <1 linha> · Travado: <1 linha>

## Esperando alguém
<da caixa: gate humano, escalado, bloqueado — com o comando que mostra cada um>

## Entregue
<PRs mesclados com número e título; SPECs com requisitos verificados no período; o que
voltou (revertido ou corrigido) e a comparação com a entrega humana, se comparável>

## Em andamento
<SPEC, progresso, estado do ciclo, último veredicto de cada gate>

## Decisões do período
<ADR ou registro, uma linha de porquê tirada do próprio arquivo>

## Processo
<gates verdes de primeira, rodadas de correção, recusas e falhas do guardrail, ruído da revisão>

## Onde esperou
<espera por pessoa em % do tempo de ciclo, a maior espera e em qual estado>

## Custo em tokens
<por SPEC, novos e cache lido; "não medido" onde não há hook>

## Riscos e próximos passos
<RAID do Breno, se existir em decisoes/gestao/; follow-ups com dono e data>

## Fontes
<cada comando rodado, com a data>
```

Seção sem dado fica com uma linha dizendo isso. Não remova a seção.

Se o usuário pediu o relatório, salve em `decisoes/gestao/STATUS-<slug>-AAAA-MM-DD.md` (o slug
é a SPEC ou `fabrica`). Se ele só perguntou, responda na conversa e ofereça salvar.

## Ao vivo

O acompanhamento ao vivo é o `painel.py`: no terminal, ou `painel.py --html painel.html` numa
página autocontida. O painel é renderização, nunca estado (ADR-0013/0032), então esta skill
não grava arquivo de progresso.

## Fronteiras

- Pontuar a montagem da fábrica no projeto é o `/kairos-forge:auditar`; esta skill relata o
  trabalho.
- Escolher a melhoria da semana é o `/kairos-forge:evoluir`.
- O plano e os marcos são da Iara; os riscos, do Breno; o lançamento, da Sofia. A Talita cita
  os artefatos deles quando existem e não os inventa.
