---
name: auditar
description: Audita o estado da fábrica no projeto atual. Use semanalmente (sugestão sexta-feira) ou quando sentir que o setup está estagnando. Pontua 0–100 em quatro dimensões — Fundação, Pipeline, Guardrails, Conhecimento — e devolve as 3 lacunas de maior alavancagem para corrigir na próxima semana. Read-only: não modifica nenhum arquivo.
---

# Auditar — pontuação da fábrica

Você está sendo invocado para auditar quão bem a fábrica kairos-forge está montada neste projeto.

## Como funciona

Audita 4 dimensões. Cada uma vale 25 pontos. Total: 100.

| Dimensão | O que mede |
|---|---|
| **Fundação** | CLAUDE.md, contextos/, decisoes/, ADRs |
| **Pipeline** | Skills, agentes, comandos disponíveis e em uso |
| **Guardrails** | Hooks, lints, testes, CI, security checks |
| **Conhecimento** | Wiki/memória persistente, references/, documentação |

Read-only: você só lê arquivos. Não modifica nada.

## Fluxo

1. **Identificar o projeto.** Confirmar diretório raiz com o usuário.

2. **Coletar evidências.** Para cada dimensão, rode os checks abaixo.

3. **Pontuar 0–25 por dimensão** seguindo a rubrica.

4. **Salvar resultado** em `decisoes/auditorias/AUDIT-YYYY-MM-DD.md` no projeto.

5. **Apresentar relatório** ao usuário com top 3 lacunas ranqueadas por alavancagem.

## Rubrica detalhada

### Fundação (25 pts)

| Critério | Pontos |
|---|---|
| `CLAUDE.md` existe e tem ≥ 50 linhas de contexto real (não template) | 10 |
| `contextos/` com pelo menos 3 arquivos de contexto preenchidos | 5 |
| `decisoes/log.md` com pelo menos 3 entradas datadas | 5 |
| `docs/adr/` com pelo menos 1 ADR escrito | 5 |

### Pipeline (25 pts)

| Critério | Pontos |
|---|---|
| Plugin kairos-forge instalado e ativo (este check é trivial: você está rodando) | 5 |
| Pelo menos 1 SPEC criada em `docs/specs/` | 5 |
| Histórico de uso de pelo menos 3 dos 5 agentes (verificar se há referências em decisões ou commits) | 10 |
| Pelo menos 1 skill ou comando customizado criado para este projeto específico (em `.claude/skills/`) | 5 |

### Guardrails (25 pts)

| Critério | Pontos |
|---|---|
| Lint configurado e passando (procurar `.eslintrc`, `pyproject.toml [tool.ruff]`, etc.) | 5 |
| Suite de testes existe e roda (`pytest`, `npm test`, `go test`) | 5 |
| CI configurado (`.github/workflows/`, `.gitlab-ci.yml`) | 5 |
| `.gitignore` cobre segredos e artefatos locais | 5 |
| Hooks de pre-commit configurados (`.pre-commit-config.yaml` ou Husky) | 5 |

### Conhecimento (25 pts)

| Critério | Pontos |
|---|---|
| `references/` ou `docs/references/` com material de apoio | 5 |
| README do projeto cobre instalação, uso e contribuição | 5 |
| Wiki/memória persistente configurada (Basic Memory, Obsidian vault, ou estrutura `wiki/` com `_index.md` e `_log.md`) | 10 |
| Pelo menos 1 ADR explicando decisão arquitetural não-óbvia | 5 |

## Formato do relatório

```markdown
# Auditoria — <projeto> — YYYY-MM-DD

**Pontuação total: NN/100**

| Dimensão | Pontos | % |
|---|---|---|
| Fundação | NN/25 | NN% |
| Pipeline | NN/25 | NN% |
| Guardrails | NN/25 | NN% |
| Conhecimento | NN/25 | NN% |

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

| Data | Total | Fundação | Pipeline | Guardrails | Conhecimento |
|---|---|---|---|---|---|
| YYYY-MM-DD | NN | NN | NN | NN | NN |
```

## Como ranquear lacunas por alavancagem

Não é por dimensão mais baixa. É por:

1. **Multiplicador.** Lacuna que destrava muitas outras (ex.: sem CLAUDE.md, todo o resto fica fraco).
2. **Custo de adiar.** Lacuna que vai doer mais a cada semana sem (ex.: sem testes, dívida cresce exponencial).
3. **Esforço para fechar.** Empate entre duas lacunas? Recomende a de menor esforço primeiro.

## Regras

- **Read-only.** Não modifique código, configs, nem nada do projeto.
- **Não invente evidência.** Se não conseguiu verificar um critério, pontue 0 e mencione "não foi possível verificar" no relatório.
- **Não suavize.** A primeira auditoria de quem nunca fez isso costuma dar 30/100 ou menos. Isso é normal e útil.
- **Salve o relatório.** Mesmo se o usuário não pedir explicitamente. É como você mede progresso ao longo do tempo.
