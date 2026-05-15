---
name: auditar
description: Audita o estado da fábrica no projeto atual. Use semanalmente (sugestão sexta-feira) ou quando sentir que o setup está estagnando. Pontua 0–100 em cinco dimensões — Fundação, Pipeline, Guardrails, Conhecimento, Estrutura — e devolve as 3 lacunas de maior alavancagem para corrigir na próxima semana. Read-only: não modifica nenhum arquivo.
---

# Auditar — pontuação da fábrica

Você está sendo invocado para auditar quão bem a fábrica kairos-forge está montada neste projeto.

## Como funciona

Audita 5 dimensões. Cada uma vale 20 pontos. Total: 100.

| Dimensão | O que mede |
|---|---|
| **Fundação** | CLAUDE.md, contextos/, decisoes/, ADRs |
| **Pipeline** | Skills, SPECs rastreáveis, validações e agentes em uso |
| **Guardrails** | Hooks, lints, testes, CI, gates e security checks |
| **Conhecimento** | Wiki/memória persistente, estado operacional, references/, documentação |
| **Estrutura** | Arquitetura modular, ownership, acoplamento, threat model |

Read-only: você só lê arquivos. Não modifica nada.

## Fluxo

1. **Identificar o projeto.** Confirmar diretório raiz com o usuário.

2. **Coletar evidências.** Para cada dimensão, rode os checks abaixo.

3. **Pontuar 0–25 por dimensão** seguindo a rubrica.

4. **Salvar resultado** em `decisoes/auditorias/AUDIT-YYYY-MM-DD.md` no projeto.

5. **Apresentar relatório** ao usuário com top 3 lacunas ranqueadas por alavancagem.

## Rubrica detalhada

### Fundação (20 pts)

| Critério | Pontos |
|---|---|
| `CLAUDE.md` existe e tem ≥ 50 linhas de contexto real (não template) | 8 |
| `contextos/` com pelo menos 3 arquivos de contexto preenchidos | 4 |
| `decisoes/log.md` com pelo menos 3 entradas datadas | 4 |
| `docs/adr/` com pelo menos 1 ADR escrito | 4 |

### Pipeline (20 pts)

| Critério | Pontos |
|---|---|
| Plugin kairos-forge instalado e ativo (este check é trivial: você está rodando) | 4 |
| Pelo menos 1 SPEC criada em `docs/specs/` com requisitos rastreáveis | 4 |
| Pelo menos 1 relatório em `docs/specs/validacoes/` ou evidência de `/validar` | 4 |
| Histórico de uso de pelo menos 3 agentes (verificar referências em decisões, specs ou commits) | 4 |
| Pelo menos 1 skill ou comando customizado criado para este projeto específico (em `.claude/skills/`) | 4 |

### Guardrails (20 pts)

| Critério | Pontos |
|---|---|
| Lint configurado e passando (procurar `.eslintrc`, `pyproject.toml [tool.ruff]`, etc.) | 4 |
| Suite de testes existe e roda (`pytest`, `npm test`, `go test`) | 4 |
| CI configurado (`.github/workflows/`, `.gitlab-ci.yml`) | 4 |
| `contextos/testes.md` documenta gates reais de lint/test/build | 4 |
| Hooks de pre-commit ou guardrail equivalente configurado (`.pre-commit-config.yaml`, Husky, CI obrigatório) | 4 |

### Conhecimento (20 pts)

| Critério | Pontos |
|---|---|
| `references/` ou `docs/references/` com material de apoio | 4 |
| README do projeto cobre instalação, uso e contribuição | 4 |
| Wiki/memória persistente configurada (Basic Memory, Obsidian vault, `wiki/` ou `decisoes/estado-operacional.md`) | 8 |
| Pelo menos 1 ADR explicando decisão arquitetural não-óbvia | 4 |

### Estrutura (20 pts)

Mede arquitetura modular, propriedade do código e antecipação de riscos. Em projetos brownfield, é normal esta dimensão começar baixa.

| Critério | Pontos |
|---|---|
| `CODEOWNERS` (raiz ou `.github/`) existe e cobre as áreas críticas do código | 3 |
| Mapa arquitetural recente em `docs/arquitetura/MAPA-*.md` (≤ 90 dias) | 4 |
| Ao menos 1 modelo de ameaças em `docs/seguranca/AMEACAS-*.md` para áreas sensíveis (auth, PII, billing, multi-tenant) | 4 |
| Hotspots de churn sem dono claro: verificar se top-10 arquivos mais alterados em 90d têm dono em CODEOWNERS. Pontuar 0 se mais de 3 ficam sem dono. | 3 |
| Acoplamento documentado: alguma evidência de fronteiras de módulo (barril `index`/`mod`/`__init__`, camadas declaradas, ADR sobre estrutura) | 3 |
| Ausência de duplicação grave de domínio (mesmo conceito modelado em 2+ módulos sem justificativa): pontuar 0 se houver caso evidente sem ADR | 3 |

## Formato do relatório

```markdown
# Auditoria — <projeto> — YYYY-MM-DD

**Pontuação total: NN/100**

| Dimensão | Pontos | % |
|---|---|---|
| Fundação | NN/20 | NN% |
| Pipeline | NN/20 | NN% |
| Guardrails | NN/20 | NN% |
| Conhecimento | NN/20 | NN% |
| Estrutura | NN/20 | NN% |

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

| Data | Total | Fundação | Pipeline | Guardrails | Conhecimento | Estrutura |
|---|---|---|---|---|---|---|
| YYYY-MM-DD | NN | NN | NN | NN | NN | NN |
```

## Coletar evidências para Estrutura

Comandos sugeridos (read-only, sem dependências fora do projeto):

- Existência de `CODEOWNERS`: `ls CODEOWNERS .github/CODEOWNERS docs/CODEOWNERS 2>/dev/null`.
- Mapa recente: `ls docs/arquitetura/MAPA-*.md 2>/dev/null` e checar data no nome.
- Modelo de ameaças: `ls docs/seguranca/AMEACAS-*.md 2>/dev/null`.
- Top-10 churn 90d: `git log --since='90 days ago' --pretty=format: --name-only | sort | uniq -c | sort -rn | head -10`. Cruzar com `CODEOWNERS`.
- Acoplamento e duplicação: amostragem manual. Marque como hipótese se não houver mapa.

Helena, Rafael ou Diego podem ser citados no relatório como responsáveis sugeridos por fechar lacunas desta dimensão.

## Lacunas de Estrutura: follow-ups típicos

Se a dimensão Estrutura ficar baixa, as ações naturais costumam ser:

- Sem mapa arquitetural ou acoplamento alto → rodar `/kairos-forge:mapear-arquitetura`.
- Sem modelo de ameaças em área sensível → rodar `/kairos-forge:analisar-ameacas`.
- Sem CODEOWNERS → abrir tarefa para Rafael/Diego definirem fronteiras de propriedade.
- Hotspots órfãos → registrar em `decisoes/estado-operacional.md` e atribuir.

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
