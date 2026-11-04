# Template do relatório — auditar

Material de apoio da skill `auditar`. Leia ao salvar o resultado em `decisoes/auditorias/AUDIT-YYYY-MM-DD.md`.

## Formato do relatório

```markdown
# Auditoria — <projeto> — YYYY-MM-DD

**Pontuação total: NN/120 (NN%)**

| Dimensão | Pontos | % |
|---|---|---|
| Fundação | NN/20 | NN% |
| Pipeline | NN/20 | NN% |
| Guardrails | NN/20 | NN% |
| Conhecimento | NN/20 | NN% |
| Estrutura | NN/20 | NN% |
| Autonomia | NN/20 | NN% |

**Dimensão que limita:** <a de menor %> — NN%. <uma linha: o que ela impede>

**Cruzamentos:** <os verdadeiros, um por linha — "Autonomia acima de Guardrails: velocidade sem
freio" · "gatilho por evento com Fundação abaixo de 50%" · "Pipeline acima de 50% com Autonomia
não medida" — ou "nenhum">

## Autonomia medida (últimos 30 dias)

| Indicador | Valor |
|---|---|
| Ciclos registrados | NN |
| Ciclos sem intervenção humana | NN (NN%) |
| Intervenções por ciclo (mediana) | N |
| Gates verdes de primeira | NN% |
| Rodadas de correção | NN |
| Produção escrita sem gate | NN sessão(ões) |
| Tempo de ciclo esperando pessoa | NN% (`telemetria.py espera`; maior espera: <estado>) |
| Perguntas por falta de fonte | NN, por fonte (`telemetria.py resumo`), ou "não medidas" |
| Entrega da fábrica × humana (90 dias) | voltaram NN% × NN% (N = NN × NN), ou "não comparável" com os N (`telemetria.py comparar`) |

**Nível estimado:** L<N> — <justificativa em uma linha, ancorada nos números acima>

(Sem telemetria: escrever "não medida" em todas as linhas. Nunca preencher por estimativa.)

## Top 3 lacunas (ranqueadas por alavancagem)

### 1. <título da lacuna>
**Dimensão:** <qual>
**Esforço estimado:** <pequeno/médio/grande>
**Por que esta primeiro:** <justificativa em 1 frase>
**Como fechar:** <ação concreta em 1-3 bullets>

### 2. <título>
...

### 3. <título>
...

## Histórico

(Se houver auditorias anteriores em `decisoes/auditorias/`, listar pontuações para mostrar tendência)

| Data | Total | % | Fundação | Pipeline | Guardrails | Conhecimento | Estrutura | Autonomia |
|---|---|---|---|---|---|---|---|---|
| YYYY-MM-DD | NN/120 | NN% | NN | NN | NN | NN | NN | NN |

(Auditorias anteriores à v0.17 têm total /100 e não têm coluna Autonomia — marque com `*` e
compare pelo percentual.)
```
