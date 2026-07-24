# ADR-0009 — Graph Engineering: grafo de conhecimento como memória compartilhada da fábrica

**Status:** Aceito
**Data:** 2026-07-24

## Contexto

O playbook *Knowledge Graph Engineering for Multi-Agentic Systems* (síntese de estudo do cookbook público da Anthropic — "Knowledge Graph Construction with Claude" — e do guia "Building Effective AI Agents") nomeia a fraqueza estrutural de qualquer sistema multi-agente: **a memória de cada agente morre com a janela de contexto**. Quando a resposta exige encadear fatos que nunca aparecem no mesmo documento (raciocínio multi-hop), ou quando vários agentes precisam de um modelo de mundo comum entre sessões, janela de contexto e busca por similaridade não bastam.

A fábrica do kairos-forge sofre exatamente disso em três pontos:

1. **`/mobilizar` (orquestrador–workers).** Cada teammate trabalha em contexto isolado e reporta para a Laura. O contexto da Laura cresce linearmente com o número de teammates — o mesmo gargalo que o playbook descreve. Não existe memória estruturada que um teammate escreva e outro leia.
2. **`/validar` (avaliador–otimizador).** A validação julga "isso parece cumprir a SPEC" com base em leitura, sem uma base de fatos com proveniência para checar afirmações. O playbook mostra o ganho de transformar o avaliador de leitor em **verificador de fatos**: "a tripla (X, predicado, Y) não existe; o que existe é (X, outro-predicado, Z), da fonte W".
3. **Ciclo semanal (`/auditar` → `/evoluir`).** A fábrica já tem memória textual (`decisoes/estado-operacional.md`, `.agents/memory/`, ADRs, SPECs) — boa para humanos lerem, ruim para máquina encadear. Cada sessão re-deriva o modelo de mundo do projeto lendo texto livre.

O playbook mostra que o pipeline clássico de NLP (NER treinado + classificador de relações + heurísticas de resolução) colapsa em **uma sequência de prompts com saída estruturada**: extração de entidades e triplas sujeito–predicado–objeto, resolução de formas de superfície em nós canônicos, montagem de um grafo consultável e resposta multi-hop com citação de arestas. Sem modelo treinado, sem biblioteca de NLP, sem banco de grafo. Isso é 100% compatível com o que o forge é: personas + prompts + arquivos no repo.

## Decisão

A partir da **v0.8.0**, o kairos-forge adota Graph Engineering como camada de infraestrutura da fábrica, em cinco peças:

### 1. Grafo de conhecimento por projeto, em arquivos

O grafo vive em **`.agents/grafo/`** no projeto do usuário (ao lado de `.agents/memory/`), versionado no git:

```
.agents/grafo/
├── esquema.md         # tipos de entidade e predicados aceitos, com versão
├── entidades.jsonl    # 1 entidade por linha: nome, tipo, descrição, fontes, menções
├── relacoes.jsonl     # 1 aresta por linha: origem, predicado, destino, fonte
├── aliases.jsonl      # 1 alias por linha: alias → canônico
├── perfis/<slug>.md   # perfis sintetizados dos hubs (grau ≥ 3)
└── GRAFO.md           # índice humano: última construção, diagnóstico, amostras
```

Sem Neo4j, sem Postgres, sem NetworkX: arquivos JSONL append-friendly com proveniência por linha. É o análogo de grafo do princípio que o forge já usa para memória de incidentes: **o agente esquece, o repo não**.

### 2. Nova skill: `mapear-conhecimento`

Implementa o pipeline do playbook em quatro modos: `construir` (extração → resolução → montagem → perfis), `atualizar` (incremental: docs novos resolvem contra o conjunto canônico existente), `consultar` (serializa subgrafo k-hop e responde **somente** com o grafo, citando arestas) e `diagnosticar` (componentes conexos, densidade, taxa de compressão, hubs, amostra humana). Os prompts completos de extração/resolução/sumarização/consulta e o checklist de produção moram em `references/playbook-grafo.md` da skill.

### 3. Nova persona: 🕸️ Olívia — Engenheira de Conhecimento (`olivia-grafos`)

Time Dados (com Carlos e André). Dona do grafo: esquema, extração, resolução, perfis, consultas e saúde estrutural. A fábrica passa de 51 para 52 agentes (core de 30 para 31).

Fronteiras explícitas (para não duplicar):

- **Olívia × André:** André é busca por **similaridade** (FTS, vetorial, RAG — single-hop); Olívia é raciocínio **estrutural** (entidades, arestas, multi-hop, proveniência). O playbook é explícito: RAG e grafo são complementares, não concorrentes.
- **Olívia × Fernanda:** Fernanda modela o **schema relacional do produto**; Olívia modela o **esquema de conhecimento da fábrica** (tipos de entidade e predicados).
- **Olívia × Gabriel:** Gabriel constrói features de IA **do produto**; Olívia mantém a infraestrutura de conhecimento **da fábrica**. Se o produto do usuário precisar de um knowledge graph como feature, Gabriel implementa com o desenho da Olívia.
- **Olívia × Juliana:** Juliana faz ETL de **dados** do produto; Olívia faz o pipeline de **conhecimento** (documentos → triplas).

### 4. Parte determinística em script: `scripts/grafo.py`

CLI stdlib-only (sem dependência externa) para tudo que não exige julgamento: `validar` (contrato dos JSONL, arestas órfãs, aliases ambíguos — usável como gate), `diagnosticar` (componentes, densidade, compressão, hubs), `subgrafo` (serialização k-hop para consulta) e `amostrar` (nó aleatório para a amostra humana diária). Segue o princípio do playbook: **modelo só onde há julgamento; lógica determinística para o resto**.

### 5. Integração nos pontos do ciclo

| Skill | Papel do grafo (padrão do playbook) |
|---|---|
| `/onboardar` | Cria `.agents/grafo/` com esquema inicial versionado |
| `/mobilizar` | **Memória compartilhada** orquestrador–workers: Laura semeia teammates com subgrafo relevante em vez de contexto inteiro; teammates devolvem fatos novos; grafo é atualizado no encerramento |
| `/validar` | **Camada de fundamentação** do avaliador: afirmações checadas contra arestas com proveniência; fato ausente do grafo é escalado ao humano, não aceito/rejeitado em silêncio |
| `/rodar`, `/especificar` | **Fonte de consulta**: subgrafo k=2 das entidades citadas antes de opinar/especificar |
| `/auditar` | Critérios de saúde do grafo na dimensão Conhecimento (existência, validação limpa, atualização recente) |
| `/mapear-arquitetura` | Componentes e bounded contexts identificados podem semear o grafo |

## Posicionamento (limite deliberado)

O forge continua **plugin, não runtime** (ADR-0001/ADR-0002). O grafo é mantido por agentes **em sessão**, via prompts — não por worker headless 24/7. Não há banco de grafo nem serviço: quando um projeto passar de alguns milhares de arestas, migrar o armazenamento (Postgres com 3 tabelas, Neo4j) é decisão de infraestrutura **do projeto do usuário** — o guia de escala na skill documenta o caminho, e o pipeline (prompts + esquema) não muda, só a persistência.

Também não entra: avaliação automática contínua com gold set rodando em CI (é loop de runtime; o forge documenta a prática e deixa a execução com o usuário) e qualquer variação regulatória de grafo (linhagem LGPD etc. — isso é kairos-ai).

## Versão

Nova skill + novo agente → bump **minor**: 0.7.0 → **0.8.0**. O roadmap aspiracional anterior da v0.8 (diagramas Mermaid, modo debate) desloca para minors seguintes — mesma precedência aplicada no ADR-0007.

## Consequências

Boas:

- `/mobilizar` escala: o contexto da Laura para de crescer linearmente com o número de teammates; o estado compartilhado vive no grafo, consultável por qualquer agente.
- `/validar` ganha base de fatos: feedback vira "a aresta X não existe; existe Y, da fonte Z" em vez de impressão de leitura.
- O conhecimento do projeto sobrevive entre sessões em forma **encadeável** (multi-hop), não só legível.
- Toda afirmação fundamentada carrega proveniência — auditável por humano.

Custos:

- Mais uma estrutura para manter por projeto (`.agents/grafo/`). Mitigado: `atualizar` é incremental, o script valida o contrato, e a auditoria cobra saúde — o custo aparece cedo, não apodrece em silêncio.
- Risco de grafo desatualizado virar fonte de erro. Mitigado: toda resposta fundamentada declara a data da última construção e o que o grafo **não** contém.
- Uma persona a mais para conhecer. Mitigado: Laura roteia; nível de acionamento próprio no `squad-fabrica.yaml`.

## Alternativas consideradas

1. **Continuar só com memória textual (`estado-operacional.md`, `.agents/memory/`).** Rejeitado como suficiente: texto livre não encadeia fatos entre documentos nem dá proveniência estruturada ao `/validar`. As memórias continuam existindo — o grafo as indexa, não as substitui.
2. **RAG/embeddings via André.** Rejeitado como substituto: similaridade resolve single-hop; falha exatamente nos casos multi-hop em que documentos não compartilham vocabulário. Complementar, não concorrente — a fronteira Olívia × André registra isso.
3. **Banco de grafo real (Neo4j/Postgres) embarcado.** Rejeitado: viraria runtime com dependência de infraestrutura, contra ADR-0001. Arquivos JSONL cobrem a escala de um repo; a migração de persistência fica documentada para quem precisar.
4. **Fazer da Fernanda ou do André o dono do grafo.** Rejeitado: acumularia dois papéis numa persona e esconderia a fronteira RAG × grafo / schema de produto × esquema de conhecimento que queremos explícita — mesmo racional do ADR-0008 (Aline × Renata).
