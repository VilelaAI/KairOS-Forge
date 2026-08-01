---
name: auditar
description: Audita o estado da fábrica no projeto atual. Use semanalmente (sugestão sexta-feira) ou quando sentir que o setup está estagnando. Pontua 0–120 em seis dimensões — Fundação, Pipeline, Guardrails, Conhecimento, Estrutura, Autonomia — e devolve as 3 lacunas de maior alavancagem para corrigir na próxima semana. Read-only: não modifica nenhum arquivo. Não audita o código do produto nem aceite de SPEC — para o diff use revisar, para aceite use validar.
---

# Auditar — pontuação da fábrica

Você está sendo invocado para auditar quão bem a fábrica kairos-forge está montada neste projeto.

## Como funciona

Audita 6 dimensões. Cada uma vale 20 pontos. Total: 120.

| Dimensão | O que mede |
|---|---|
| **Fundação** | CLAUDE.md, contextos/, decisoes/, ADRs |
| **Pipeline** | Skills, SPECs rastreáveis, validações e agentes em uso |
| **Guardrails** | Hooks, lints, testes, CI, gates e security checks |
| **Conhecimento** | Grafo de conhecimento, memória persistente, estado operacional, references/, documentação |
| **Estrutura** | Arquitetura modular, ownership, acoplamento, threat model |
| **Autonomia** | Quanto a fábrica anda sozinha — medido da telemetria, não da impressão (ADR-0021) |

Read-only: você só lê arquivos e roda comandos de leitura. Não modifica nada.

> **Nota de escala.** Até a v0.16 a auditoria tinha 5 dimensões e total 100. A partir da
> v0.17 são 6 e o total é 120. Compare auditorias antigas com novas **pelo percentual**,
> nunca pelo número absoluto — e registre a mudança de escala no histórico.

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
| Lint configurado e passando (procurar `.eslintrc`, `pyproject.toml [tool.ruff]`, etc.) | 3 |
| Suite de testes existe e roda (`pytest`, `npm test`, `go test`) | 4 |
| CI configurado (`.github/workflows/`, `.gitlab-ci.yml`) | 3 |
| `contextos/testes.md` documenta gates reais de lint/test/build | 3 |
| Hooks de pre-commit ou guardrail equivalente configurado (`.pre-commit-config.yaml`, Husky, CI obrigatório) | 3 |
| Setup de agentes/hooks customizados auditado: se o projeto definiu agentes em `.claude/agents/` ou hooks, eles têm allow-list de ferramentas explícita, sem segredos hardcoded, sem injeção em hook (rode `check-agent-security.py` apontando para `.claude`). Sem config customizada, pontue cheio. | 4 |

### Conhecimento (20 pts)

| Critério | Pontos |
|---|---|
| `references/` ou `docs/references/` com material de apoio | 2 |
| README do projeto cobre instalação, uso e contribuição | 2 |
| `decisoes/estado-operacional.md` existe e tem ao menos uma seção preenchida (não só headers vazios) | 3 |
| `.agents/memory/MEMORY.md` existe (índice de memórias de incidente — ADR-E003) | 2 |
| Memórias de incidente em `.agents/memory/<slug>.md` com frontmatter `name`/`description` (escala): 1-2 = 2 pts, 3+ = 4 pts | 0-4 |
| Pelo menos 1 ADR explicando decisão arquitetural não-óbvia | 2 |
| Grafo de conhecimento (ADR-0009), em escala: `.agents/grafo/` com `entidades.jsonl` + `relacoes.jsonl` + `esquema.md` versionado = 2 pts; `grafo.py validar` sai limpo = +2 pts; construção/atualização ≤ 30 dias registrada em `GRAFO.md` = +1 pt | 0-5 |

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

### Autonomia (20 pts)

Mede quanto a fábrica anda **sem intervenção humana** — a diferença entre L3 (humano no planejamento e na revisão final) e L4 (pipelines autônomos, time confiando no harness). É a única dimensão que **não se pontua por leitura de arquivo**: sai da telemetria.

Colete primeiro:

```bash
python3 <plugin>/scripts/telemetria.py resumo --dias 30
```

| Critério | Pontos |
|---|---|
| Telemetria ativa: `.agents/execucoes/` existe com eventos dos últimos 30 dias | 3 |
| **Taxa de autonomia** (ciclos sem intervenção ÷ ciclos), em escala: < 20% = 0 · 20–49% = 2 · 50–79% = 4 · ≥ 80% = 6 | 0-6 |
| **Gates verdes de primeira** ≥ 70% (primeira execução do gate já passa — mede a qualidade do contexto, não a sorte) | 3 |
| Arco fechado em uso: ao menos 1 ciclo de `/kairos-forge:entregar` registrado nos últimos 30 dias | 3 |
| Guardrails determinísticos ativos: `guardrail.py` instalado nos hooks **ou** rodando no CI do projeto (ADR-0022) | 3 |
| Gatilho por evento: ao menos 1 workflow da fábrica em `.github/workflows/` disparado por PR, falha de CI ou cron (ADR-0026) | 2 |

Penalidade dura: **sessões com escrita em código de produção e nenhum gate rodado** (campo `sessoes_com_producao_sem_gate`) — subtraia 2 pontos por ocorrência, até zerar a dimensão. Código de produção escrito sem nenhuma verificação é o oposto exato de autonomia confiável; é vibe coding com mais etapas.

**Sem telemetria no projeto:** pontue 0 na dimensão inteira e registre no relatório *"telemetria não instalada — autonomia não medida"*. Não estime. A regra da casa vale aqui com força total: autonomia sem instrumento é chute, e chute otimista sobre autonomia é exatamente como se produz um pipeline sem supervisão.

Renata (Observabilidade) é a responsável sugerida por lacunas desta dimensão; Marcos (DevOps) pelos gatilhos de CI.

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

## Autonomia medida (últimos 30 dias)

| Indicador | Valor |
|---|---|
| Ciclos registrados | NN |
| Ciclos sem intervenção humana | NN (NN%) |
| Intervenções por ciclo (mediana) | N |
| Gates verdes de primeira | NN% |
| Rodadas de correção | NN |
| Produção escrita sem gate | NN sessão(ões) |

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

## Como nomear o nível de autonomia

A tabela abaixo traduz a telemetria em nível. Use-a para preencher "Nível estimado" — e não
arredonde para cima: o nível é o **menor** que ainda descreve a evidência.

| Nível | Assinatura na telemetria |
|---|---|
| **L2 — Babá** | Autonomia < 20%; mediana de intervenções ≥ 3; humano aprova etapa a etapa |
| **L3 — Gerente** | Autonomia 20–79%; SPECs rastreáveis em uso; humano no planejamento e na revisão final do PR |
| **L4 — Fábrica** | Autonomia ≥ 80%; gates verdes de primeira ≥ 70%; arco fechado (`entregar`) em uso; guardrails determinísticos ativos; ao menos um gatilho por evento; zero sessões com produção sem gate |

L4 exige **todos** os critérios da linha, não a média deles. Uma fábrica com 90% de autonomia e
nenhum guardrail determinístico não é L4 — é pipeline sem supervisão, e o relatório deve dizer
isso com essas palavras.

## Coletar evidências para Estrutura

Comandos sugeridos (read-only, sem dependências fora do projeto):

- Existência de `CODEOWNERS`: `ls CODEOWNERS .github/CODEOWNERS docs/CODEOWNERS 2>/dev/null`.
- Mapa recente: `ls docs/arquitetura/MAPA-*.md 2>/dev/null` e checar data no nome.
- Modelo de ameaças: `ls docs/seguranca/AMEACAS-*.md 2>/dev/null`.
- Top-10 churn 90d: `git log --since='90 days ago' --pretty=format: --name-only | sort | uniq -c | sort -rn | head -10`. Cruzar com `CODEOWNERS`.
- Acoplamento e duplicação: amostragem manual. Marque como hipótese se não houver mapa.

Helena, Rafael ou Diego podem ser citados no relatório como responsáveis sugeridos por fechar lacunas desta dimensão.

## Coletar evidências para Conhecimento: grafo

Para o critério do grafo de conhecimento (read-only, sem dependências):

- Existência: `ls .agents/grafo/entidades.jsonl .agents/grafo/relacoes.jsonl .agents/grafo/esquema.md 2>/dev/null`.
- Contrato: `python3 <plugin>/scripts/grafo.py validar` — exit 0 = +2 pts; erros = 0 nesse subcritério e liste os 3 primeiros no relatório.
- Frescor: data de "Última construção" em `.agents/grafo/GRAFO.md` ≤ 30 dias = +1 pt.
- Bônus de diagnóstico (não pontua, mas entra no relatório): `grafo.py diagnosticar` — mais de 1 componente conexo ou densidade < 0.5 são lacunas candidatas ao top 3.
- Memória de sessão (não pontua — ADR-0010): se as tools MCP `memory_*` (ai-memory) estiverem disponíveis, registre no relatório "memória de sessão ativa" (com `memory_status` se quiser detalhe); se não, registre "inativa — camada opcional, ver docs/memoria-persistente.md".

Olívia é a responsável sugerida por lacunas deste critério.

## Coletar evidências para Guardrails: segurança do setup

O kairos-forge embarca `scripts/check-agent-security.py`, que audita a *configuração de agentes/hooks* — não o código do produto. Para o critério de setup customizado, rode-o apontando para a config do projeto:

- `python3 <plugin>/scripts/check-agent-security.py .claude` — varre `.claude/agents/`, hooks e segredos.
- Exit 0 = pontue cheio (4). Achados ALTA (allow-list ausente/curinga, segredo hardcoded) = pontue 0 e liste no relatório.
- Projeto sem agentes/hooks customizados em `.claude/` = pontue cheio (não há superfície de risco a auditar).

Helena é a responsável sugerida por achados desta verificação.

## Lacunas de Estrutura: follow-ups típicos

Se a dimensão Estrutura ficar baixa, as ações naturais costumam ser:

- Sem mapa arquitetural ou acoplamento alto → rodar `/kairos-forge:mapear-arquitetura`.
- Sem modelo de ameaças em área sensível → rodar `/kairos-forge:analisar-ameacas`.
- Sem grafo de conhecimento, grafo quebrando `validar` ou parado > 30 dias → rodar `/kairos-forge:mapear-conhecimento` (construir ou atualizar).
- Sem CODEOWNERS → abrir tarefa para Rafael/Diego definirem fronteiras de propriedade.
- Hotspots órfãos → registrar em `decisoes/estado-operacional.md` e atribuir.

## Lacunas de Autonomia: follow-ups típicos

A ordem importa — instrumentar antes de conter, conter antes de disparar. Recomendar gatilho
por evento a um projeto sem guardrail determinístico é recomendar pipeline sem supervisão:

1. Sem telemetria → instalar os hooks do plugin (ou rodar `execucao.py` via CI). Sem isso, as outras lacunas desta dimensão nem são mensuráveis.
2. Autonomia baixa com muitas intervenções → o ciclo está sendo conduzido à mão; rodar `/kairos-forge:entregar` em vez de encadear skills manualmente.
3. Gates verdes de primeira abaixo de 70% → problema de **contexto**, não de modelo: SPEC vaga, `contextos/testes.md` desatualizado ou ausência de trilha. Vale um `/kairos-forge:evoluir` focado nisso.
4. Produção escrita sem gate → lacuna de Guardrails antes de Autonomia; ativar `guardrail.py` e exigir gate na SPEC.
5. Tudo verde e ainda sem gatilho por evento → copiar `templates/ci/` para o projeto (ADR-0026).

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
