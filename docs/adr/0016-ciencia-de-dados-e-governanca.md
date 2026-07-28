# ADR-0016 — Time core Ciência de Dados & ML e squad de apoio Governança

**Status:** Aceito
**Data:** 2026-07-28

## Contexto

Inventário pedido pelo usuário revelou duas lacunas reais no catálogo (a terceira área perguntada, observabilidade, está coberta em duas camadas — Renata/Aline/Sérgio no core e apoio-observabilidade no produto):

1. **Ciência de dados & ML.** As peças existentes são adjacentes, não o papel: Gabriel faz IA **de produto** centrada em LLM (prompts, RAG, evals); Aline faz ML **de operações** (anomalia em telemetria); Juliana move dados (ETL); André faz retrieval. Ninguém cobre ciência de dados clássica (EDA, estatística, hipóteses, experimentos), engenharia de ML (features, treino, avaliação, versionamento) nem MLOps (deploy e monitoramento de modelo).
2. **Governança.** Existe governança de engenharia difusa (Rafael/ADRs, CODEOWNERS na auditoria, allow-lists, Helena no setup), mas não governança **de dados** (catálogo, linhagem, qualidade como requisito, políticas de acesso) nem dono do tema. Fronteira crítica: governança **regulatória** (DPO, LGPD, guardrails legais) é do kairos-ai (ADR-0002) e continua lá.

## Decisão

A partir da **v0.12.0**, a fábrica passa de 58 para **64 agentes** — **34 core em 10 times + 30 apoio em 10 squads** (20 times no total).

### 1. Time core novo: **Ciência de Dados** (3 agentes)

DS/ML **implementa código** (notebooks, features, treino, pipelines de modelo) — por definição não pode ser squad de apoio (ADR-0003). Entra como décimo time core:

| Agente | Papel | Especialidade |
|---|---|---|
| 🔬 **Davi** (`davi-ciencia-dados`) | Cientista de Dados | EDA, estatística (testes de hipótese, intervalos, significância), formulação de hipóteses, desenho de experimentos, storytelling com dados |
| 🧠 **Milena** (`milena-ml`) | Engenheira de ML | Feature engineering, treino e avaliação (baseline primeiro, métricas honestas, validação cruzada, leakage), versionamento de modelo e dataset |
| 🚢 **Heitor** (`heitor-mlops`) | Engenheiro de MLOps | Deploy de modelo (batch/online), monitoramento de drift e performance em produção, retraining, model registry, rollback de modelo |

**Fronteiras (para não duplicar):**

- **Davi × Otávio (apoio-observabilidade):** Otávio define métricas de produto (AARRR); Davi faz a ciência em cima dos dados (estatística, causalidade, experimento bem desenhado).
- **Milena × Gabriel:** Gabriel = IA de produto com LLM; Milena = ML clássico (supervisionado, séries, recomendação). Feature com LLM é do Gabriel; modelo treinado em dado do produto é da Milena.
- **Milena × Aline:** Aline aplica ML **na telemetria de operações**; Milena constrói ML **do produto/negócio**.
- **Heitor × Marcos:** Marcos faz CI/CD **da aplicação**; Heitor faz o ciclo de vida **do modelo** (deploy, drift, retraining, registry). Pipelines se tocam; os artefatos são distintos.
- **Heitor × Renata:** Renata instrumenta o sistema; Heitor monitora **o modelo** (drift de dados/conceito, qualidade de predição).
- **Juliana → Milena:** Juliana entrega os dados (ETL); Milena transforma em features e modelo.

### 2. Squad de apoio novo: **apoio-governanca** (3 agentes)

Governança técnica produz políticas, catálogos e critérios — artefatos textuais: apoio.

| Agente | Papel | Especialidade |
|---|---|---|
| 🗂️ **Vitor** (`apoio-vitor-catalogo`) | Catalogador de Dados | Catálogo de dados (o que existe, onde, quem é dono), linhagem documentada (de onde vem, o que transforma, quem consome), dicionário de dados |
| 🧪 **Regina** (`apoio-regina-qualidade`) | Analista de Qualidade de Dados | Qualidade como requisito com número (completude, unicidade, validade, freshness), contratos de dados entre produtor e consumidor, detecção de degradação |
| 🔑 **Paula** (`apoio-paula-politicas`) | Analista de Políticas de Acesso | Políticas de acesso técnico (quem lê/escreve o quê, por quê), matriz de ownership de dados e sistemas, revisão periódica de acessos, princípio do menor privilégio como política documentada |

**Fronteiras:**

- **Vitor × Olívia:** Olívia mantém o grafo de **conhecimento da fábrica** (decisões, entidades do projeto); Vitor cataloga os **dados do produto** (tabelas, eventos, datasets). Os dois artefatos podem se alimentar (catálogo vira fonte de extração do grafo).
- **Vitor × Fernanda:** Fernanda desenha o schema; Vitor documenta o que existe, a linhagem e os donos.
- **Regina × Patrícia/Ricardo:** eles cuidam da qualidade **do código**; Regina, da qualidade **dos dados**. Contrato de dados quebrado é achado dela, não caso de teste deles.
- **Regina × Norma (apoio-requisitos):** Norma cobre NFRs em geral na SPEC; Regina aprofunda o NFR específico de dados quando o projeto é data-intensive.
- **Paula × Helena:** Helena audita segurança técnica (OWASP, secrets, superfície); Paula escreve a **política** (quem deveria ter acesso, ownership, revisão). Helena verifica; Paula normatiza.
- **Paula × kairos-ai:** política com força **legal** (LGPD, DPO, retenção regulatória) é do kairos-ai — Paula trata do genérico técnico e recomenda a migração quando o requisito for regulado.

### Colisões de nome

Nenhuma nova: Davi, Milena, Heitor, Vitor, Regina e Paula são inéditos no catálogo. Os pares existentes (Marcos, Helena, Elisa) seguem sendo os únicos.

## Versão

Agentes novos → bump **minor**: 0.11.1 → **0.12.0**.

## Consequências

Boas: a fábrica cobre o ciclo de dados de ponta a ponta — mover (Juliana) → catalogar/qualificar (Vitor/Regina) → analisar (Davi) → modelar (Milena) → operar modelo (Heitor) — com governança de acesso (Paula) e sem invadir o regulatório. Custos: 6 personas a mais (mitigado: roteamento por sinais e por Laura); risco de sobreposição percebida com Gabriel/Aline/Olívia/Helena (mitigado: fronteiras explícitas nos prompts e neste ADR).

## Alternativas consideradas

1. **Ampliar Gabriel para cobrir ML clássico.** Rejeitado: acumularia LLM + ML numa persona e esconderia a fronteira produto×clássico — o racional anti-acúmulo dos ADRs 0007/0008/0014.
2. **DS/ML como squad de apoio.** Rejeitado: apoio nunca codifica; DS/ML é trabalho de implementação.
3. **Governança como time core.** Rejeitado: os artefatos são políticas/catálogos/critérios (texto); quem implementa controles técnicos continua sendo o core (Carlos, Helena, Marcos) a partir das políticas.
4. **Esperar o kairos-ai cobrir governança.** Rejeitado: o kairos-ai cobre o **regulatório**; catálogo/linhagem/qualidade/acesso são necessidade técnica genérica de qualquer projeto com dados.
