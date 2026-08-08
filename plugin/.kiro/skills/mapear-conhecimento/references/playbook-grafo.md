# Playbook do grafo de conhecimento — prompts, contratos e escala

Material de apoio da skill `mapear-conhecimento`. Adaptado do playbook *Knowledge Graph Engineering for Multi-Agentic Systems* (síntese do cookbook público da Anthropic "Knowledge Graph Construction with Claude" e do guia "Building Effective AI Agents") para o contexto da fábrica kairos-forge.

## 1. Contratos de dados (os "schemas" do pipeline)

O playbook original usa saídas estruturadas validadas por schema — o schema é o único "dado de treino" do pipeline. Aqui o contrato são os JSONL abaixo. Trate-os como contrato rígido: linha que não valida não entra (rode `grafo.py validar`).

`entidades.jsonl` — uma entidade canônica por linha:

```json
{"nome": "API de relatórios", "tipo": "COMPONENTE", "descricao": "Serviço que gera e exporta relatórios em CSV", "fontes": ["docs/specs/SPEC-001-exportar-csv.md"], "mencoes": 3}
```

`relacoes.jsonl` — uma aresta dirigida por linha:

```json
{"origem": "API de relatórios", "predicado": "depende de", "destino": "PostgreSQL", "fonte": "docs/adr/0002-banco.md"}
```

`aliases.jsonl` — uma forma de superfície por linha:

```json
{"alias": "relatorios-api", "canonico": "API de relatórios"}
```

Regras do contrato:

- `origem`/`destino` de toda relação precisam resolver (direto ou via alias) para um `nome` de `entidades.jsonl` — aresta órfã é erro.
- Um alias aponta para exatamente um canônico — alias ambíguo é erro.
- `fonte` é path relativo ao repo do projeto. Aresta sem fonte é erro.
- Grafo é dirigido e multi-aresta: dois nós podem ter várias arestas com predicados distintos; direção importa ("Laura coordena mobilização" ≠ "mobilização coordena Laura").

## 2. Modelo de `esquema.md`

```markdown
# Esquema do grafo de conhecimento

**Versão:** 1
**Última alteração:** YYYY-MM-DD — criação inicial via /kairos-forge:mapear-conhecimento

## Tipos de entidade

| Tipo | O que é | Exemplos |
|---|---|---|
| COMPONENTE | Módulo, serviço, pacote ou camada do sistema | API de relatórios, worker de fila |
| FEATURE | Capacidade voltada ao usuário | Exportar CSV, login social |
| SPEC | SPEC rastreável em docs/specs/ | SPEC-001 |
| ADR | Decisão arquitetural registrada | ADR-0003 |
| DECISÃO | Decisão técnica fora de ADR (decisoes/log.md) | "Adotar pnpm" |
| TECNOLOGIA | Linguagem, framework, banco, serviço externo | PostgreSQL, React |
| PESSOA | Pessoa real do time ou stakeholder | Allyson |
| AGENTE | Persona da fábrica | Laura, Helena |
| INCIDENTE | Memória de incidente (.agents/memory/) | "Timeout no deploy de sexta" |
| AMBIENTE | Ambiente ou infraestrutura | produção, staging, cluster EKS |

## Predicados aceitos

Verbos curtos, em PT-BR, no presente: `implementa`, `depende de`, `expõe`, `consome`,
`decidiu usar`, `substitui`, `bloqueia`, `cobre`, `valida`, `causou`, `mitiga`,
`pertence a`, `responsável por`, `documenta`.

Predicado novo é permitido se for verbo curto e raciocinável — registre-o aqui na
próxima revisão. Predicado vago ("está relacionado a", "envolve") é proibido.

## Histórico de versões

| Versão | Data | Mudança |
|---|---|---|
| 1 | YYYY-MM-DD | Esquema inicial |
```

Quando mudar tipos ou predicados: bump da versão, linha no histórico e nota em `GRAFO.md`. Entidades extraídas sob esquemas diferentes precisam ser distinguíveis (na dúvida, re-extraia as fontes afetadas).

## 3. Prompt de extração (por documento)

A redação controla diretamente o trade-off precisão/recall. "Só entidades centrais" favorece precisão (correto para corpus grande — entidade falsa gera relações falsas); "todas as entidades mencionadas" favorece recall (aceitável em corpus pequeno). Comece pelo padrão abaixo e ajuste com o loop de avaliação (seção 8).

```text
Extraia um grafo de conhecimento do documento abaixo.

<documento>
{texto}
</documento>

Diretrizes:
- Extraia apenas entidades CENTRAIS ao que este documento trata — pule menções
  incidentais.
- Para cada entidade, escreva uma descrição de UMA frase, ancorada neste
  documento. Essas descrições serão usadas depois para desambiguar entidades
  com nomes parecidos.
- Tipos permitidos: os do esquema.md do projeto (versão vigente).
- Predicados são verbos curtos em PT-BR ("implementa", "depende de",
  "decidiu usar"). Nada de predicado vago.
- Toda relação precisa conectar duas entidades que você extraiu.

Devolva no formato:
ENTIDADE: <nome> | <TIPO> | <descrição de uma frase>
RELACAO: <origem> | <predicado> | <destino>
```

Cada diretriz mata um modo de falha específico: a 1ª controla recall/ruído; a 2ª alimenta a resolução; a 3ª e a 4ª mantêm o grafo raciocinável; a 5ª impede aresta órfã (referência pendurada).

## 4. Prompt de resolução (por tipo de entidade)

Rode um lote por tipo (PESSOA com PESSOA, COMPONENTE com COMPONENTE). As descrições são a chave: sem elas o resolvedor só vê nomes e recai exatamente na falha de similaridade de string que o pipeline existe para evitar ("Edwin Aldrin" e "Buzz Aldrin" não compartilham um caractere; "Armstrong astronauta" e "Armstrong trompetista" compartilham todos).

```text
Abaixo estão entidades do tipo {tipo} extraídas de vários documentos deste
projeto. Algumas são formas diferentes de escrever a MESMA entidade do mundo real.

<entidades>
{lista: nome — descrição (fonte)}
</entidades>

Agrupe-as em clusters. Restrições:
- Cada nome de entrada aparece em EXATAMENTE um cluster (lista de aliases).
- Entidades genuinamente distintas ganham cluster próprio, mesmo unitário.
- Use as descrições para NÃO fundir entidades que apenas compartilham nome.
- O nome canônico é a forma mais completa e sem ambiguidade.

Devolva no formato:
CLUSTER: <canônico> | <alias 1>; <alias 2>; ...
```

Modos de falha a monitorar em toda rodada:

1. **Perda silenciosa** — nome que ficou fora de todo cluster some do grafo. Contramedida: fallback obrigatório de cluster unitário + `grafo.py validar` (acusa aresta órfã).
2. **Over-merge** — específico fundido no genérico ("Gemini 12" dentro de "Projeto Gemini") porque as descrições se parecem. Contramedida: amostragem humana + na dúvida, não funde.

## 5. Prompt de sumarização de perfil (hubs, grau ≥ 3)

```text
Gere um perfil de grafo de conhecimento para esta entidade.

Entidade: {nome} ({tipo})

Trechos das fontes que a mencionam:
{excertos}

Relações conhecidas no grafo:
{triplas}

Escreva um resumo factual de 2-3 parágrafos sintetizado dos trechos,
resolvendo contradições ao preferir a afirmação MAIS ESPECÍFICA.
Inclua 3-5 fatos-chave atômicos, cada um rastreável às fontes.
Para o intervalo temporal, use AAAA ou AAAA-MM.
NÃO invente fatos que os trechos não sustentam.
```

"Preferir a afirmação mais específica" resolve contradições sem inventar; "não invente fatos" é o análogo de sumarização do "sem evidência não é aprovado" do `/validar` — default de cautela.

Salve em `perfis/<slug>.md` com frontmatter mínimo:

```markdown
---
entidade: API de relatórios
tipo: COMPONENTE
fontes: [docs/specs/SPEC-001-exportar-csv.md, docs/adr/0002-banco.md]
atualizado: YYYY-MM-DD
---
```

Re-sumarize **somente** quando o conjunto de fontes mudar — fonte igual, perfil igual, custo zero.

## 6. Prompt de consulta fundamentada

```text
Responda usando SOMENTE o grafo de conhecimento abaixo. Cite as arestas
específicas que sustentam cada afirmação, no formato
(origem) --[predicado]--> (destino) [fonte: arquivo].

<grafo>
{triplas serializadas por grafo.py subgrafo}
</grafo>

Pergunta: {pergunta}

Se o grafo não contiver informação suficiente, diga exatamente o que falta.
Não complete com conhecimento externo.
```

A restrição "somente o grafo" é o que torna a resposta rastreável: o modelo não pode recorrer ao pré-treino e cada citação pode ser conferida por comparação literal com as triplas de entrada. Devolva junto da resposta a lista de triplas usadas — quem chamou (agente ou humano) confere cada citação.

## 7. Checklist de produção — 10 itens

Cada item mapeia um modo de falha com nome. Grafo com os 10 está pronto; sem qualquer um deles, o risco é específico e vai aparecer.

| # | Item | Pergunte-se | Falha se faltar |
|---|---|---|---|
| 1 | Gold set | Há um conjunto avaliado à mão para ao menos 2 documentos representativos? | Sem loop de feedback; mudança de prompt é às cegas |
| 2 | Mapa de aliases do scorer | O gold set reconhece os canônicos que a resolução produz? | Artefato de medição — recall parece pior do que é |
| 3 | Esquema versionado | `esquema.md` tem versão e histórico? | Entidades incompatíveis entre versões de prompt |
| 4 | Cap de extração | Há limite de documentos por rodada (default 30)? | Custo sem teto em erro de ingestão |
| 5 | Fallback de resolução | Nome sem cluster vira cluster unitário? | Perda silenciosa de nós |
| 6 | Proveniência | Toda aresta carrega fonte? | Resposta sem fundamento; `/validar` não checa nada |
| 7 | Atualização incremental | Documento novo entra sem reconstruir o grafo? | Custo de rebuild cresce com o corpus, não com o delta |
| 8 | Monitor de conectividade | Componentes conexos conferidos após cada resolução? | Grafo fragmentado — elos entre documentos perdidos |
| 9 | Gatilho de re-sumarização | Perfil só re-sintetiza quando as fontes mudam? | Custo desperdiçado em entidade inalterada |
| 10 | Amostra humana | Alguém lê um nó aleatório regularmente (`grafo.py amostrar`)? | Apodrecimento de compreensão — o grafo cresce além do entendimento |

Itens 1-2 dão o loop de avaliação; 3-5 impedem corrupção silenciosa; 6-8 mantêm o grafo estruturalmente são; 9-10 controlam custo e compreensão. O pipeline não está pronto quando roda — está pronto quando dá pra dizer, numa manhã qualquer, se o que ele produziu está certo.

## 8. Loop de avaliação (o que separa demo de produção)

1. Monte um gold set: para 2+ documentos representativos, liste à mão as entidades e relações esperadas.
2. Rode a extração e compare: precisão (do que extraí, quanto está certo?) e recall (do que existia, quanto peguei?).
3. Relações: compare por par (origem, destino) ignorando a redação do predicado — detecta erro estrutural, que é o que importa.
4. Mude o prompt de extração → rode de novo → observe o F1 se mover. Toda mudança de prompt passa por aqui antes de virar padrão.

Precisão 1.0 com recall 0.4-0.6 é o perfil esperado (e desejável) do prompt "só entidades centrais": extrator conservador. Falso positivo é pior que falso negativo — entidade errada propaga relações erradas pelo multi-hop; entidade faltando produz grafo incompleto porém correto.

## 9. Guia de escala

- **Extração:** custo linear no corpus; é a etapa a delegar para modelo rápido/barato e, quando disponível, processamento em lote. O cap por rodada (item 4) limita o pior caso.
- **Resolução com blocking:** milhares de entidades de um tipo não entram num prompt só. Bloqueie por sinal barato (tokens do nome em comum, mesmo prefixo) e deixe o modelo arbitrar só dentro de blocos de 50-100. Híbrido: determinístico agrupa, modelo julga.
- **Chunking de documento longo:** corte em fronteira de seção com overlap de um parágrafo (co-ocorrência entidade-relação preservada); deduplicação exata entre chunks do mesmo documento antes da resolução.
- **Armazenamento:** JSONL cobre até algumas centenas de milhares de arestas com folga num repo. Além disso, o mesmo contrato mapeia direto para 3 tabelas Postgres (`entidades`, `relacoes`, `aliases`) ou um property graph (Neo4j). **Só a persistência muda — prompts e esquema ficam.** Essa migração é decisão de infraestrutura do projeto do usuário (Fernanda/Carlos entram), não do plugin.
- **Monitoramento (4 sinais):** taxa de extração por documento (queda = corpus mudou de domínio; pico = ruído periférico), taxa de compressão da resolução, número/tamanho de componentes conexos, latência/custo por consulta (pré-serialize subgrafos dos hubs mais consultados se precisar).

## 10. Papéis do grafo nos padrões multi-agente (mapa de integração)

| Padrão | Papel do grafo | Na fábrica |
|---|---|---|
| LLM aumentado | Fonte de recuperação estrutural (travessia em vez de similaridade) | `consultar` em qualquer sessão |
| Encadeamento de prompts | Sinal de gate entre etapas (entidade nova conflita com nó existente?) | `especificar` antes de fechar SPEC |
| Roteamento | Tipo e grau da entidade roteiam sem chamada de modelo | Laura decide quem entra |
| Orquestrador–workers | **Memória compartilhada** — workers leem/escrevem o grafo; contexto do orquestrador fica pequeno | `/mobilizar` |
| Avaliador–otimizador | **Camada de fundamentação** — avaliador checa afirmações contra arestas com proveniência | `/validar` |
| Loop persistente | **Modelo de mundo** que sobrevive ao flush de contexto | ciclo `/auditar` → `/evoluir` |

A afirmação sem aresta que a sustente não é aceita nem rejeitada em silêncio: **escala para o humano**. O grafo move a base da decisão de estimativa do modelo para fato extraído — mas a decisão continua com os agentes e com quem os desenhou.
