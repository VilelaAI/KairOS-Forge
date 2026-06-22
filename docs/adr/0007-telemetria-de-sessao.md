# ADR-0007 — Telemetria de sessão como entregável

**Status:** Aceito
**Data:** 2026-06-22

## Contexto

As skills do kairos-forge produzem entregáveis sobre o **produto** (SPEC, mapa,
threat model, validação, auditoria), mas nada media a **própria sessão da
fábrica**: quanto trabalho foi feito, quais subagentes foram acionados, quantas
ferramentas e commits, quanto custou. Faltava um entregável que respondesse "o
que esta sessão produziu?" — útil tanto para apresentar a clientes (valor
entregue) quanto para o time interno (observabilidade, custo, gargalos).

Os hooks existentes (`hooks/hooks.json`, `.codex/hooks.json`) eram apenas
informativos (banner + lembrete pedagógico). Não havia coleta. Os agentes de
apoio Otávio (Métricas) e Lia (Instrumentação) tratam de métricas do **produto
do usuário** (AARRR, tracking plan), não da sessão do forge — territórios que
não devem se confundir.

Restrições técnicas relevantes:

- Hooks do Claude Code entregam no stdin `session_id`, `transcript_path`, `cwd`,
  `hook_event_name` + campos por evento (`tool_name`, `tool_input`,
  `tool_response`, `source`, `reason`). **Tokens/custo não vêm nos hooks** — só
  do `transcript_path` (`message.usage` por mensagem).
- Multi-CLI (ADR-0004): Codex só dispara `SessionStart`; OpenCode não tem hooks.
  Coleta passiva por hook é, portanto, **exclusiva do Claude Code**.
- Subagentes são acionados de duas formas: (a) **Task** real (`/mobilizar`,
  Agent Teams) — visível a hooks/transcript; (b) **persona conversacional** do
  `/rodar` ("Oi, Renata aqui") — **invisível** a hooks, só inferível por regex
  no transcript.

## Decisão

A partir da v0.7.0:

- **Nova skill `/kairos-forge:relatar`** — gera, ao fim de uma sessão, **dois
  relatórios por público** (`RELATORIO-EXECUTIVO-*` para cliente,
  `RELATORIO-TECNICO-*` para o time) mais um **painel acumulado** (`PAINEL.md`)
  com tendência entre sessões, no estilo do histórico do `/auditar`. Salva em
  novo diretório-convenção `decisoes/relatorios/`. Read-only no projeto exceto
  por esses arquivos.
- **Núcleo no transcript (multi-CLI).** A skill lê o transcript da sessão, cruza
  com `git log` e varre os diretórios-convenção de artefatos. Funciona em
  qualquer CLI que exponha um transcript legível; degrada honestamente para
  `git + disco` quando não há transcript, marcando o que ficou indisponível.
- **Hooks como enriquecimento opcional (Claude Code only).** `Pre/PostToolUse`,
  `SubagentStop` e `SessionEnd` chamam `scripts/coletar-metricas.py --hook`,
  que faz append num log `.agents/metricas/sessao-<id>.jsonl`. Esse log refina a
  **duração** dos subagentes Task. Se ausente, a skill cai para estimativa por
  timestamps do transcript.
- **Novo script `scripts/coletar-metricas.py`** (stdlib only) com modos `--hook`
  (coleta passiva) e `--agregar` (parsing + agregação → JSON consumido pela
  skill). Toda a lógica pesada vive no script; `hooks.json` e a skill ficam finos.
- **Três níveis de confiabilidade, sempre rotulados:** **medido** (ferramentas,
  arquivos, commits, subagentes Task, tokens), **estimado** (personas
  conversacionais do `/rodar`), **aproximado** (custo em USD = tokens × tabela de
  preço embutida no script).
- O log cru `.agents/metricas/*.jsonl` vai para o `.gitignore` (efêmero); o que
  se versiona é o relatório em `decisoes/relatorios/`.
- Total de skills sobe de 10 para 11. Manifests e marketplaces vão a 0.7.0.

## Consequências

Boas:

- A fábrica passa a ter um entregável sobre si mesma, em duas linguagens
  (negócio e técnica), reaproveitável em apresentações e retrospectivas.
- O painel acumulado mostra tendência (agentes/skills mais usados, custo por
  sessão) sem ferramenta externa.
- O núcleo no transcript mantém a portabilidade multi-CLI; o hook é um "nice to
  have" degradável, não um acoplamento ao Claude Code.

Custos:

- O custo em USD é aproximado (preço de tabela por modelo) e pode desatualizar —
  está marcado como aproximado no relatório e na tabela do script.
- Personas conversacionais do `/rodar` são estimadas por regex e podem errar —
  sempre rotuladas "estimado" e nunca contadas como Task.
- Mais um arquivo a manter no fluxo de release (script + skill). O `hooks.json`
  cresce com os eventos de coleta.

## Alternativas consideradas

1. **Skill única que lê o transcript sob demanda, sem hooks.**
   Mais simples e portável, mas perde o timing fino de subagentes Task e um
   carimbo confiável de início/fim. Adotado como **núcleo**, com o hook por cima.
2. **Coleta só por hook (sem ler transcript).**
   Rejeitado: seria Claude-Code-only (contra ADR-0004), não pegaria tokens/custo
   e não seria retroativo (exige sessão instrumentada desde o início).
3. **Reusar Otávio/Lia (apoio-observabilidade) para o relatório.**
   Rejeitado: eles medem o **produto** do usuário (AARRR/tracking). Misturar com
   telemetria da sessão do forge confundiria os dois territórios. Por isso o
   verbo `relatar` (e não `medir`/`telemetrar`, que soam a métrica de produto).
4. **Um único relatório.**
   Rejeitado: cliente e time querem coisas diferentes (valor entregue vs. custo e
   gargalos). Dois relatórios + painel atende ambos sem poluir nenhum.

## Limitações por CLI

| Item | Claude Code | Codex CLI | OpenCode |
|---|---|---|---|
| Skill `/kairos-forge:relatar` | ✅ | ✅ (núcleo via transcript/git) | ✅ (núcleo via transcript/git) |
| Coleta passiva por hook (`--hook`) | ✅ | ❌ (só `SessionStart`) | ❌ (sem hooks) |
| Timing fino de subagentes Task | ✅ (com log de hook) | ⚠️ estimado pelo transcript | ⚠️ estimado pelo transcript |
| Tokens/custo | ✅ (transcript) | ⚠️ depende do transcript disponível | ⚠️ idem |
