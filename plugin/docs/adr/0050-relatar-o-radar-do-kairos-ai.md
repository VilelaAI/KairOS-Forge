# ADR-0050 — Relatar: o radar do kairos-ai como prestação de contas da fábrica

- **Status:** aceito
- **Data:** 2026-11-03
- **Versão:** v0.42.0

## Contexto

O kairos-ai tem a skill `radar`, a camada de observabilidade dele. Ela responde três
perguntas: o que foi entregue, por que foi assim e quanto custou. Também monta o relatório
executivo da sprint.

A fábrica já mede tudo isso, mas espalhado:
- `telemetria.py prs` conta os PRs mesclados e quantos não tiveram commit humano (ADR-0044);
- `telemetria.py tokens` e `quadro.py ledger` dão os tokens por sessão e por tarefa
  (ADR-0048);
- `telemetria.py resumo` e `ruido` mostram o processo: gates de primeira, rodadas de
  correção, guardrail e ruído da revisão;
- `painel.py` mostra o estado das SPECs, dos ciclos e dos relatórios, e `--caixa` o que
  espera por alguém;
- as decisões estão em `docs/adr/`, `decisoes/` e no grafo.

Faltava quem juntasse. Para saber "o que entregamos esta semana", o usuário precisava rodar
seis comandos e montar a resposta de cabeça. E a Talita [Entregas], cuja persona é status
report com evidência, não aparecia em nenhuma skill: era uma das 20 personas sem uso apontadas
na auditoria do ADR-0049.

## Decisão

Uma skill nova, **`/kairos-forge:relatar`**, com a Talita como dona.

- **O nome é verbo.** `radar` é substantivo, e a convenção 2 do projeto pede verbo no
  infinitivo.
- **Nenhum script novo.** A skill é uma tabela que diz qual comando já existente responde
  cada pergunta, mais as regras do relatório:
  - número sem fonte não entra;
  - sem dado, "não medido", nunca 0;
  - custo em tokens, nunca em dinheiro;
  - pronto só com `verificado:`;
  - notícia ruim primeiro.
- **O status do período** segue o formato que a persona da Talita já descrevia e é salvo em
  `decisoes/gestao/STATUS-<slug>-AAAA-MM-DD.md` só quando pedido.
- **"Por que decidimos"** é respondido citando `arquivo:linha` de ADR, `decisoes/` ou SPEC.
  Sem registro, a resposta é "decisão não registrada", e não uma reconstrução de memória.

### O que do radar não entra

| Do radar | Por quê |
|---|---|
| Custo em dólar e por tier de modelo | O plugin não conhece preço nem plano (ADR-0044, ADR-0048) |
| Modo live com `radar-state.json` e statusline | Arquivo de progresso que um worker atualiza é estado paralelo. O painel é renderização (ADR-0013/0032), e o `painel.py` já é o acompanhamento ao vivo |
| Golden dataset por agente | No kairos-ai, é o release gate dos agentes negociais. No Forge, o equivalente é o `/avaliar` com conjunto selado (ADR-0025/0043) |
| Atualizações legislativas e consistência entre blueprints | Regulatório: fica no kairos-ai |
| Fallback e cache de modelo | Existem no worker 24/7 do kairos-ai, que não é portado |
| Drift em `.kairos/drift-log.md` | No Forge, o sinal sai das rodadas de correção (`telemetria.py resumo`) e dos ciclos em `atacando_premissa_*` ou `escalado` (painel) |

## Consequências

- A skill é só leitura e não toca em contrato: `ciclo`, `quadro` e as fences não mudam.
- O relatório herda as limitações por CLI. No Codex e no OpenCode, tokens e trajetória saem
  "não medidos"; os PRs vêm do git em qualquer CLI.
- Com a fonte `git`, merge por squash não aparece na contagem de PRs. Com o `gh` autenticado,
  aparece. O relatório diz qual fonte usou.
- São 19 skills. A soma das descrições continua no orçamento estático do `release.py check`
  (ADR-0038).

## Alternativas consideradas

- **Portar o `radar` como está.** Recusado. Metade dele depende do runtime do kairos-ai
  (worker, `radar-state.json`, cache, fallback) ou do domínio regulado.
- **Um `relatorio.py` que junta tudo num JSON.** Adiado. Os seis comandos já são
  determinísticos e testados, e um agregador seria o sétimo lugar dizendo o mesmo número. Se
  o relatório passar a rodar sem pessoa, por gatilho de CI, o agregador volta à mesa.
- **Estender o `/auditar`.** Recusado. O `/auditar` pontua a montagem da fábrica no projeto;
  o `/relatar` presta contas do trabalho. Juntar os dois mistura nota com status.

## Emenda (v0.42.2): medir a linha

A aula 5 do Tech Leads Club (Fábricas Agênticas) parte da lei de Amdahl: acelerar o código 10×
rende uns 10% na entrega, porque o trabalho passa a maior parte do tempo esperando alguém. O
`/relatar` dizia o que foi entregue e quanto custou por sessão, mas não onde o trabalho
esperou, nem quanto custou cada SPEC. Três peças, todas só leitura:

- **`telemetria.py espera`.** Tempo por estado de cada ciclo, lido do `historico` que o
  `ciclo.py` já grava. Mostra o lead time, o trabalho e a espera por pessoa (os gates
  `aguardando_*` e o `pronto_para_pr`, o PR esperando merge), a maior espera e as voltas de
  correção. Os terminais param o relógio. Nada novo é coletado.
- **`telemetria.py por-spec`.** Os tokens de cada sessão somados por SPEC. A chave comum é o
  branch, como na fábrica da aula, que usa o ID da issue no nome do branch.
  - O hook grava o branch no início e em cada `Stop`, lendo o `.git` sem rodar git, porque o
    `/entregar` troca de branch no meio da sessão.
  - Do prompt, o hook guarda só os ids de SPEC citados, nunca o texto.
  - A SPEC sai do ciclo aberto naquele branch, do id no nome do branch ou do primeiro id
    citado, nesta ordem. O resto fica em "sem SPEC" e continua medido: o hook mede e nunca
    bloqueia o início da sessão.
- **`/auditar` pela dimensão que limita.** O total 0–120 soma, e pontos altos numa dimensão
  compensavam a fraqueza de outra. O relatório passa a nomear a dimensão de menor percentual e
  três cruzamentos:
  - autonomia acima dos guardrails;
  - gatilho por evento sem fundação;
  - pipeline sem medição.

O `/relatar` ganha a regra "meça a linha, nunca as pessoas" e as linhas "Onde o trabalho
esperou?" e "Quanto custou?", esta agora por SPEC.

## Emenda (v0.42.13): este período ao lado do anterior

O status dizia o que aconteceu no período, mas não se o período foi melhor ou pior que o
anterior. A ideia veio da página do Synapse (Maitha), um relatório de entrega que põe cada
número ao lado do período anterior; é a única peça dela que cabe num plugin.

`telemetria.py periodo --dias N` põe os últimos N dias ao lado dos N anteriores, com a
variação calculada pelo script. O modelo não subtrai: a regra 1 do `/relatar` passa a dizer
isso. São doze linhas em três grupos, cada uma pela função do comando de origem:

- **Entregue** (`prs`): PRs mesclados, com código da fábrica, sem commit humano e a autonomia
  de PR.
- **Processo** (`resumo`): sessões, autonomia de ciclo, gates verdes de primeira, rodadas de
  correção, recusas do guardrail e sessões com produção sem gate.
- **Custo** (`tokens`): tokens novos e cache lido.

Regras da conta:

- **Uma carga, duas metades.** O script carrega 2N dias uma vez e reparte. O PR conta no
  período em que foi mesclado, como no `prs --dias N`.
- **A sessão conta inteira no período em que começou.** Os dois lados somam os 2N dias sem
  contar duas vezes o mesmo token. O custo é que o lado de agora pode diferir do `resumo --dias
  N`, que corta por evento, pelas sessões que começaram antes da fronteira; a saída diz isso.
- **Taxa vem com a conta ao lado** (`50,0% (1/2)`), e a variação em pontos percentuais. Com
  menos de 5 no denominador, o script marca "amostra pequena", o mesmo mínimo do `comparar`.
- **"Não medido" dos dois lados.** Sem trajetória nos 2N dias, processo e custo saem "não
  medido", nunca 0; os PRs saem do git em qualquer CLI.

### Limites

- **Reversões e correções (`comparar`) ficam de fora.** Um PR só entra nelas 14 dias depois de
  mesclado, e um período de 7 dias ainda não fechou essa janela.
- **Espera e ruído também.** A espera é por ciclo, e um ciclo aberto atravessa os dois
  períodos; o ruído é por relatório de revisão. Os dois seguem no próprio comando, com
  `--dias`.
- **Com a fonte `git`, squash e rebase não aparecem**, como no `prs`. A saída repete o aviso.
