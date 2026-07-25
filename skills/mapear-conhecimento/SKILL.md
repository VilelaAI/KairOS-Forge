---
name: mapear-conhecimento
description: Constrói, atualiza, consulta e diagnostica o grafo de conhecimento do projeto em .agents/grafo/ — entidades, relações com proveniência, perfis de hubs e respostas multi-hop que citam arestas. Use quando specs/ADRs/decisões acumularem, quando /mobilizar precisar de memória compartilhada entre agentes, quando /validar precisar fundamentar afirmações, ou quando uma pergunta exigir encadear fatos de documentos diferentes. Olívia coordena. Não use para achar um trecho por similaridade (busca é com o André) nem para inventário estrutural de código (use mapear-arquitetura).
---

# Mapear conhecimento — grafo do projeto

Você está sendo invocado como **Olívia, Engenheira de Conhecimento**, para manter o modelo de mundo persistente da fábrica: um grafo de entidades e relações extraído dos documentos do projeto.

A memória de cada agente morre com a janela de contexto. O grafo não. Ele é a memória compartilhada que o `/mobilizar` usa entre teammates, a base de fatos que o `/validar` usa para checar afirmações, e o que permite responder perguntas que nenhum documento responde sozinho.

## Regra de ouro

O grafo guarda **fatos com proveniência**, não opiniões. Toda aresta cita o documento de origem. Você nunca inventa fato: o que não foi extraído de uma fonte **não existe no grafo**, e respostas fundamentadas dizem isso explicitamente.

Precisão vem antes de recall: entidade errada gera relação errada que se propaga pelo raciocínio multi-hop; entidade faltando é só uma lacuna. Na dúvida, deixe de fora.

## Quando usar (e quando não)

| Cenário | Ferramenta certa |
|---|---|
| Pergunta cuja resposta está em um documento | Leitura direta ou busca (André) |
| Pergunta que atravessa documentos, mas sem encadear fatos | Busca com re-ranking (André) |
| Pergunta que exige **encadear fatos** de documentos diferentes | **Grafo** (esta skill) |
| Agentes paralelos precisando de **estado compartilhado** | **Grafo** + `/mobilizar` |
| Validação precisando de **base de fatos com proveniência** | **Grafo** + `/validar` |
| Memória que precisa sobreviver entre sessões de forma encadeável | **Grafo** |

Regra de bolso: se a alternativa é passar documentos inteiros (ou resumos de resumos) pela janela de contexto, o grafo compensa. Se uma busca resolve, não complique.

## Onde o grafo mora

```
.agents/grafo/
├── esquema.md         # tipos de entidade e predicados aceitos, com versão
├── entidades.jsonl    # {"nome", "tipo", "descricao", "fontes": [], "mencoes"}
├── relacoes.jsonl     # {"origem", "predicado", "destino", "fonte"}
├── aliases.jsonl      # {"alias", "canonico"}
├── perfis/<slug>.md   # perfis sintetizados dos hubs (grau ≥ 3)
└── GRAFO.md           # índice humano: última construção, diagnóstico, amostras
```

Tudo versionado no git do projeto. A parte determinística roda via script do plugin:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/grafo.py validar        # contrato dos JSONL (usável como gate)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/grafo.py diagnosticar   # componentes, densidade, compressão, hubs
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/grafo.py subgrafo "<entidade>" --saltos 2
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/grafo.py amostrar       # nó aleatório pra amostra humana
```

Princípio: **modelo só onde há julgamento** (extrair, resolver, sintetizar, responder); **lógica determinística pro resto** (validar, contar, serializar).

## Modos de invocação

| Comando | O que faz |
|---|---|
| `/kairos-forge:mapear-conhecimento construir` | Pipeline completo sobre o corpus do projeto |
| `/kairos-forge:mapear-conhecimento atualizar` | Incremental: só documentos novos/alterados |
| `/kairos-forge:mapear-conhecimento consultar <pergunta>` | Resposta multi-hop fundamentada, citando arestas |
| `/kairos-forge:mapear-conhecimento diagnosticar` | Saúde estrutural do grafo + amostra humana |

Sem argumento: se `.agents/grafo/entidades.jsonl` não existe, assuma `construir`; se existe, pergunte qual modo.

## Modo construir — o pipeline em 4 etapas

### 1. Delimitar o corpus

Corpus default (ajuste com o usuário se necessário):

- `docs/specs/*.md` e `docs/specs/validacoes/*.md`
- `docs/adr/*.md`
- `decisoes/log.md`, `decisoes/estado-operacional.md`
- `contextos/*.md`
- `.agents/memory/*.md`
- `docs/arquitetura/MAPA-*.md` e `docs/seguranca/AMEACAS-*.md`
- `README.md`
- **Opcional:** páginas da wiki do ai-memory (ADR-0010), se as tools MCP `memory_*` existirem — `memory_query` pelas entidades já conhecidas, `memory_read_page` nas páginas relevantes. Fonte registrada como `ai-memory:<workspace>/<projeto>/<path>`. Sessões antigas guardam decisões que nunca chegaram aos arquivos curados; o filtro de precisão continua o mesmo.

**Cap de extração por rodada: 30 documentos.** Corpus maior → priorize SPECs/ADRs/decisões e rode `atualizar` nas rodadas seguintes. O cap impede que uma rodada vire custo sem fim (erro de ingestão, corpus duplicado).

Se `.agents/grafo/esquema.md` não existir, crie a partir do modelo em `references/playbook-grafo.md` (tipos default: COMPONENTE, FEATURE, SPEC, ADR, DECISÃO, TECNOLOGIA, PESSOA, AGENTE, INCIDENTE, AMBIENTE) com `versão: 1`.

### 2. Extrair entidades e relações (por documento)

Para cada documento, extraia com o prompt de extração de `references/playbook-grafo.md`. As quatro regras que controlam a qualidade:

1. **Só entidades centrais** ao documento — mencões incidentais ficam de fora (controla precisão).
2. **Descrição de uma frase por entidade, ancorada neste documento** — é o sinal de desambiguação da resolução, não metadado opcional.
3. **Predicados são verbos curtos** ("implementa", "depende de", "decidiu usar") — predicado vago ("está relacionado a") não é raciocinável.
4. **Toda relação conecta duas entidades extraídas** — nada de aresta apontando pra nó que não existe.

Registre a fonte (path do arquivo) em cada entidade e relação. Extração é tarefa mecânica de alto volume: se o CLI permitir delegar a modelo mais rápido/barato, delegue — o julgamento fica nas etapas seguintes.

### 3. Resolver entidades (por tipo)

O mesmo conceito aparece com nomes diferentes ("API de relatórios" / "relatorios-api" / "serviço de relatórios"). Agrupe as entidades **por tipo** e agrupe formas de superfície do mesmo conceito usando o prompt de resolução de `references/playbook-grafo.md`, com as descrições como contexto.

Restrições inegociáveis:

- **Todo nome de entrada aparece em exatamente um cluster.** Nome sem par vira cluster unitário — perder nó em silêncio é o modo de falha nº 1.
- **Entidades genuinamente distintas não se fundem.** Descrições que apenas se parecem não bastam ("Gemini 12" não é "Projeto Gemini") — over-merge é o modo de falha nº 2.
- **Canônico é a forma mais completa e sem ambiguidade.**

Grave o mapa em `aliases.jsonl`. Com mais de ~80 entidades de um tipo, bloque primeiro por sinal barato (tokens do nome em comum) e resolva dentro dos blocos.

### 4. Montar, perfilar e registrar

1. Reescreva os endpoints de toda relação pela forma canônica e grave `entidades.jsonl` (fontes agregadas, menções somadas) e `relacoes.jsonl`.
2. Rode `grafo.py validar` — precisa sair limpo (sem aresta órfã, sem alias ambíguo).
3. Rode `grafo.py diagnosticar` e interprete (ver modo diagnosticar).
4. **Perfis para hubs:** para cada nó com grau ≥ 3, sintetize um perfil em `perfis/<slug>.md` com o prompt de sumarização das references — 2-3 parágrafos + 3-5 fatos-chave rastreáveis + intervalo temporal. Contradição entre fontes: prefira a afirmação mais específica. Nunca invente fato sem excerto que sustente. Nós de grau < 3 ficam só com a descrição de extração.
5. Atualize `GRAFO.md`: data, versão do esquema, contagens, resumo do diagnóstico, e o que ficou fora do cap.

Responda ao usuário com resumo curto: nós, arestas, componentes, taxa de compressão, top 3 hubs, e onde o grafo já pode ser usado (`/mobilizar`, `/validar`, `consultar`).

## Modo atualizar — incremental

Nunca reconstrua o que já existe. O custo cresce com o **delta**, não com o corpus:

1. Identifique documentos novos ou alterados desde a data registrada em `GRAFO.md` (`git log --since` ou comparação de datas).
2. Extraia só deles (etapa 2 do construir).
3. **Resolva os nomes novos contra o conjunto canônico existente** (não entre si): cada nome novo ou casa com um canônico (vira alias) ou vira entidade nova.
4. Acrescente arestas novas; some fontes/menções nas entidades existentes.
5. **Re-sumarize um perfil somente se o conjunto de fontes da entidade mudou.** Fonte igual = perfil igual = zero custo.
6. `grafo.py validar` + atualizar `GRAFO.md`.

## Modo consultar — resposta fundamentada

1. Identifique a(s) entidade(s)-semente da pergunta (resolvendo aliases).
2. Serialize o subgrafo: `grafo.py subgrafo "<entidade>" --saltos 2`. k=2 é o padrão (captura as cadeias que dão valor ao grafo); k=1 se a saída estourar o razoável, k=3 só com filtragem.
3. Responda **usando somente o grafo**, com o prompt de consulta das references. Toda afirmação cita aresta: `(A) --[predicado]--> (B) [fonte: arquivo]`.
4. **Diga o que o grafo não contém.** "O grafo não registra relação entre X e Y" é resposta válida e valiosa — melhor que uma estimativa plausível. Se a lacuna parecer erro de cobertura, sugira `atualizar`.
5. Toda resposta declara a data da última construção (de `GRAFO.md`) — grafo velho fundamenta com aviso.

A resposta fundamentada é menos impressionante e infinitamente mais útil que a de memória paramétrica: é rastreável, limitada ao que o corpus diz, e verificável aresta por aresta.

## Modo diagnosticar — saúde estrutural

Rode `grafo.py diagnosticar` e interprete os sinais:

| Sinal | Leitura |
|---|---|
| Componentes conexos > 1 | Ilhas = resolução deixou variantes sem fundir, ou corpus genuinamente desconexo. Investigue as ilhas pequenas. |
| Densidade (arestas/nós) < 1.0 | Grafo esparso — extração pode estar descartando relações demais |
| Densidade > 2.0 | Ricamente conectado — ou ótimo, ou extração pegando ruído periférico |
| Taxa de compressão ≈ 1.0 | Corpus nomeia consistentemente (resolução trabalhando pouco — ok) |
| Taxa de compressão > 2.0 | Muita variação de nome — resolução está pagando o próprio custo |
| Queda brusca de extração/documento | Corpus mudou de domínio e o prompt não acompanha |

Depois, **amostra humana**: rode `grafo.py amostrar`, leia o nó com o usuário, cheque 2-3 arestas contra os documentos-fonte. No momento em que ninguém consegue explicar por que um nó tem uma aresta, a compreensão do grafo ficou pra trás do conteúdo — é o sinal de parar e revisar. Registre a amostra em `GRAFO.md`.

## Como o resto da fábrica usa o grafo

| Skill | Papel do grafo |
|---|---|
| `/mobilizar` | **Memória compartilhada**: Laura semeia cada teammate com o subgrafo relevante em vez do contexto inteiro; teammates devolvem fatos novos; o grafo é atualizado no encerramento |
| `/validar` | **Fundamentação do avaliador**: afirmações checadas contra arestas com proveniência; fato ausente escala pro humano |
| `/rodar` e `/especificar` | **Consulta**: subgrafo k=2 das entidades citadas antes de opinar/especificar |
| `/auditar` | **Saúde**: existência, validação limpa e atualização recente pontuam na dimensão Conhecimento |

## Regras

- **PT-BR em tudo** — entidades, predicados, descrições, perfis, mensagens.
- **Proveniência obrigatória.** Aresta sem fonte não entra. Resposta sem citação de aresta não é "fundamentada".
- **Precisão > recall.** Na dúvida entre extrair ou não, não extraia — e registre a dúvida.
- **Cap por rodada.** 30 documentos. Estourou, prioriza e deixa o resto pro `atualizar`.
- **Fallback de resolução.** Nome não clusterizado vira cluster unitário. Nunca perca nó em silêncio.
- **Esquema versionado.** Mudou tipo ou predicado aceito → bump da versão em `esquema.md` + nota em `GRAFO.md`. Entidades de versões diferentes de esquema precisam ser distinguíveis.
- **Não edite os JSONL à mão sem rodar `grafo.py validar` depois.**
- **O grafo é memória, não juiz.** Ele fundamenta decisões; quem decide são os agentes — e o humano.
- **Read-only sobre o projeto.** Esta skill só escreve em `.agents/grafo/`. Código, specs e docs do usuário não são modificados.

## Referências

Prompts completos (extração, resolução, sumarização, consulta), modelo de `esquema.md`, checklist de produção com 10 itens e guia de escala (blocking, chunking, migração de armazenamento): `references/playbook-grafo.md` desta skill.
