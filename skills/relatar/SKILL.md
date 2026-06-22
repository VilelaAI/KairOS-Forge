---
name: relatar
description: Gera relatórios de telemetria da SESSÃO do kairos-forge (não métricas do produto do usuário). Coleta o máximo de informações da sessão e dos subagentes acionados — ferramentas usadas, arquivos, subagentes Task, skills rodadas, commits, artefatos, tokens e custo estimado — e produz dois entregáveis (executivo para cliente e técnico para o time) mais um painel acumulado entre sessões. Use ao fim de uma sessão de trabalho ou quando o usuário pedir um relatório/entregável de métricas da sessão. Read-only no projeto, exceto pelos três arquivos que grava em decisoes/relatorios/.
---

# Relatar — telemetria de sessão como entregável

Você está sendo invocado para transformar a sessão de trabalho atual da fábrica
kairos-forge em **entregável**: o que foi feito, quais subagentes foram
acionados, quanto custou e o que ainda falta.

## O que isto NÃO é

Não confunda com os agentes de apoio **Otávio (Métricas)** e **Lia
(Instrumentação)**: aqueles definem métricas do **produto do usuário** (AARRR,
tracking plan). Esta skill mede a **sessão do kairos-forge** — o trabalho da
fábrica nesta conversa.

## Quando usar

- Ao final de uma sessão de trabalho, para registrar o que foi entregue.
- Depois de `/kairos-forge:mobilizar` ou `/kairos-forge:rodar`, para medir os subagentes acionados.
- Quando o usuário pedir "um relatório", "as métricas da sessão" ou "um entregável do que fizemos".
- Como passo final recorrente do fluxo, depois de `auditar`/`validar`.

## Regra de ouro

Read-only no projeto, **exceto** pelos três arquivos que você grava em
`decisoes/relatorios/`. Não corrija código, não rode gates. Apenas colete,
agregue e relate — com honestidade sobre o que foi **medido**, **estimado** ou
**aproximado**.

## Fluxo

### 1. Localizar a fonte de dados

A coleta tem um núcleo portável (transcript) e um enriquecimento opcional (hook).

1. **Transcript da sessão (fonte principal, multi-CLI quando disponível).**
   No Claude Code, o transcript JSONL fica em
   `~/.claude/projects/<slug-do-cwd>/<session-uuid>.jsonl`. O `<slug-do-cwd>` é
   o caminho absoluto do projeto com `/` e `.` trocados por `-`. Escolha o
   `.jsonl` mais recentemente modificado se houver dúvida sobre qual é a sessão
   atual. Confirme com o usuário em caso de ambiguidade.
2. **Log de hook (enriquecimento opcional, Claude Code).** Se existir
   `.agents/metricas/sessao-<id>.jsonl` no projeto, passe-o em `--jsonl` para
   refinar a duração dos subagentes.
3. **Degradação honesta.** No Codex/OpenCode (ou se não achar o transcript),
   rode a agregação só com `--git --projeto` — o relatório sai parcial e marca
   explicitamente o que ficou indisponível (tokens, custo, subagentes Task).

### 2. Agregar com o helper

Rode o coletor (todo o parsing pesado vive nele, não nesta skill):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/coletar-metricas.py \
  --agregar <CAMINHO_DO_TRANSCRIPT.jsonl> \
  --jsonl .agents/metricas/sessao-<id>.jsonl \  # se existir
  --git --projeto .
```

A saída é um JSON agregado com: `duracao_segundos`, `ferramentas`,
`arquivos_escritos`, `comandos_bash_total`, `subagentes_task`,
`personas_conversacionais`, `skills_rodadas`, `commits`, `artefatos`, `tokens`,
`custo_usd`, `modelos`, `fontes` e `avisos`. Use esse JSON como fonte única dos
relatórios — não invente números que não estejam nele.

### 3. Classificar a confiabilidade

Ao montar os relatórios, rotule cada bloco pela fonte:

- **Medido** — ferramentas, arquivos, commits, subagentes **Task**, tokens (vêm do transcript/hook/git).
- **Estimado** — personas conversacionais do `/rodar` ("Oi, <Nome> aqui"): o
  modo conversacional **não** gera subagente Task e é invisível a hooks. Sempre
  rotule "conversacional (estimado)" e **nunca** conte como Task.
- **Aproximado** — custo em USD (tokens × tabela de preço do modelo).

Repasse os `avisos` do JSON para a seção "Notas de precisão".

### 4. Gerar os três arquivos

Salve em `decisoes/relatorios/` no projeto. Use a data/hora local (`YYYY-MM-DD-HHMM`):

1. `RELATORIO-EXECUTIVO-YYYY-MM-DD-HHMM.md` — público **cliente/stakeholder**.
2. `RELATORIO-TECNICO-YYYY-MM-DD-HHMM.md` — público **time técnico**.
3. `PAINEL.md` — **acumulado**: acrescente uma linha e recompute os tops.

## Formato — relatório executivo (cliente)

Linguagem de negócio. Sem tokens crus nem custo em USD.

```markdown
# Relatório de Sessão (Executivo) — <projeto> — YYYY-MM-DD HH:MM

**Duração da sessão:** Xh Ymin

## Resumo executivo
<2-3 frases: o que esta sessão entregou, em linguagem de negócio>

## O que foi construído
- <entregue 1, em termos de valor>
- <entregue 2>

## Times e especialistas envolvidos
<Agentes/squads que participaram, por nome e papel — ex.: "Helena (Segurança)
revisou o fluxo de login". Inclua Task e conversacionais, sem jargão técnico.>

## Artefatos entregues
- <docs/specs/SPEC-...md — "Especificação rastreável da feature X">
- <decisoes/auditorias/AUDIT-...md — "Auditoria semanal da fábrica">

## Próximos passos
1. ...
2. ...
```

## Formato — relatório técnico (time interno)

Espelha `auditar`/`validar`: tabela principal + detalhe + narrativa + próximos passos + notas.

```markdown
# Relatório de Sessão (Técnico) — <projeto> — YYYY-MM-DD HH:MM

**Duração:** Xh Ymin · **Sessão:** <id curto> · **CLI:** Claude Code|Codex|OpenCode
**Fontes:** transcript <sim/não> · log de hook <sim/não> · git <sim/não>

| Métrica | Valor |
|---|---|
| Ferramentas usadas | NN (Write NN, Edit NN, Bash NN, Task NN, ...) |
| Arquivos escritos/editados | NN |
| Comandos bash | NN |
| Subagentes Task | NN |
| Skills rodadas | <lista> |
| Commits na sessão | NN |
| Artefatos produzidos | NN |
| Tokens (in / out / cache cria / cache leitura) | NN / NN / NN / NN |
| Custo estimado | US$ N,NN (aprox.) |

## Subagentes acionados
| Agente | Modo | Duração | Sucesso |
|---|---|---|---|
| renata-observabilidade | Task | 1m12s | ✅ |
| marina-frontend | conversacional (estimado) | — | — |

## Artefatos produzidos
- <lista de caminhos>

## Commits na sessão
- <hash curto> <subject>

## Narrativa
<2-4 parágrafos: o que a sessão fez, picos de atividade, gargalos, onde o tempo/custo foi>

## Próximos passos
1. ...

## Notas de precisão
- Personas conversacionais (`/rodar`) são ESTIMADAS por parsing do transcript — não contadas como Task.
- Custo é APROXIMADO (tokens × tabela de preço do modelo).
- <repasse os `avisos` do JSON agregado, ex.: indisponibilidades por CLI>
```

## Formato — painel acumulado (`PAINEL.md`)

Se já existir, **leia** o painel, acrescente a linha desta sessão e recompute os
tops. Se não existir, crie com cabeçalho.

```markdown
# Painel de Sessões — <projeto>

Acumulado de telemetria das sessões do kairos-forge. Atualizado por `/kairos-forge:relatar`.

## Histórico

| Data | Duração | Ferramentas | Subagentes | Skills | Commits | Tokens (in/out) | Custo (aprox.) |
|---|---|---|---|---|---|---|---|
| YYYY-MM-DD HH:MM | Xh Ym | NN | NN | <n> | NN | NN/NN | US$ N,NN |

## Top agentes acionados (acumulado)
1. <agente> — N sessões
2. ...

## Top skills rodadas (acumulado)
1. <skill> — N vezes
2. ...
```

## 5. Responder ao usuário

Resumo curto com os destaques e os caminhos salvos:

```markdown
Relatório da sessão gerado.

Duração: Xh Ymin · Subagentes: NN · Artefatos: NN · Custo aprox.: US$ N,NN.

Salvos em:
- decisoes/relatorios/RELATORIO-EXECUTIVO-YYYY-MM-DD-HHMM.md (cliente)
- decisoes/relatorios/RELATORIO-TECNICO-YYYY-MM-DD-HHMM.md (time)
- decisoes/relatorios/PAINEL.md (acumulado)
```

## Coleta passiva (opcional, Claude Code)

Para timing fino de subagentes Task, o plugin pode gravar um log durante a
sessão via hooks (`Pre/PostToolUse`, `SubagentStop`, `SessionEnd` →
`coletar-metricas.py --hook` → `.agents/metricas/sessao-<id>.jsonl`). É
**opcional e exclusivo do Claude Code** — Codex só tem `SessionStart` e OpenCode
não tem hooks. Sem o log, esta skill ainda funciona pelo transcript; a duração
de subagente apenas fica estimada pelos timestamps em vez de medida pelos pares.

## Regras

- **Não invente números.** Toda métrica vem do JSON agregado. Se uma fonte
  faltou, diga "indisponível neste CLI" — não chute.
- **Separe medido de estimado de aproximado.** É o que dá credibilidade ao entregável.
- **Não conte persona conversacional como subagente Task.** São coisas diferentes.
- **Não suba o log cru.** `.agents/metricas/*.jsonl` é efêmero (está no `.gitignore`); o que se versiona é o relatório em `decisoes/relatorios/`.
- **PT-BR em tudo.**
