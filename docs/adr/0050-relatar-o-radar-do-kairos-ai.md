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
