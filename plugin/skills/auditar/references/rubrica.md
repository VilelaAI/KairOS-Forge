# Rubrica de pontuação — auditar

Material de apoio da skill `auditar`. Leia ao pontuar cada dimensão: tabelas critério a critério, penalidades de Autonomia e a tabela de níveis. Valores aqui são a fonte da verdade da pontuação.

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
python3 <plugin>/scripts/painel.py --dias 30      # o mesmo estado com as SPECs ao lado
```

| Critério | Pontos |
|---|---|
| Telemetria ativa: `.agents/execucoes/` existe com eventos dos últimos 30 dias | 2 |
| **Taxa de autonomia** (ciclos sem intervenção ÷ ciclos), em escala: < 20% = 0 · 20–49% = 2 · 50–79% = 4 · ≥ 80% = 6 | 0-6 |
| **Gates verdes de primeira** ≥ 70% (primeira execução do gate já passa — mede a qualidade do contexto, não a sorte) | 3 |
| Arco fechado em uso: ao menos 1 ciclo de `/kairos-forge:entregar` registrado nos últimos 30 dias | 2 |
| Guardrails determinísticos ativos: `guardrail.py` instalado nos hooks **ou** rodando no CI do projeto (ADR-0022) | 3 |
| Recusas do guardrail sob controle: `recusas_total` na telemetria com tendência estável ou caindo. Recusa **crescente** é sinal de agente batendo em limite repetidamente — não pontue se estiver subindo (ADR-0030) | 2 |
| Gatilho por evento: ao menos 1 workflow da fábrica em `.github/workflows/` disparado por PR, falha de CI ou cron (ADR-0026) | 2 |

**Recusa é sinal, não vitória.** O bloqueio ter funcionado não zera o fato de o agente ter tentado: um agente que passa na validação alcançando ferramenta que não tem não está passando. Leia `recusas_por_classe` no `telemetria.py resumo` — recusa concentrada numa classe indica regra mal calibrada (se for falso positivo) ou instrução faltando (se for tentativa legítima recorrente).

**Regra em modo aviso é regra em observação, não regra cumprida.** Se `recusas_em_modo_aviso` está alto e estável, ou a regra vira `bloqueio` ou ela sai — regra que só avisa para sempre é decoração.

Penalidade dura: **sessões com escrita em código de produção e nenhum gate rodado** (campo `sessoes_com_producao_sem_gate`) — subtraia 2 pontos por ocorrência, até zerar a dimensão. Código de produção escrito sem nenhuma verificação é o oposto exato de autonomia confiável; é vibe coding com mais etapas.

**Sem telemetria no projeto:** pontue 0 na dimensão inteira e registre no relatório *"telemetria não instalada — autonomia não medida"*. Não estime. A regra da casa vale aqui com força total: autonomia sem instrumento é chute, e chute otimista sobre autonomia é exatamente como se produz um pipeline sem supervisão.

Renata (Observabilidade) é a responsável sugerida por lacunas desta dimensão; Marcos (DevOps) pelos gatilhos de CI.

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
