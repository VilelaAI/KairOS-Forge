# ADR-0012 — Ciclo de catraca: otimização guiada por métrica, orçamento de complexidade e reflexão estruturada

**Status:** Aceito
**Data:** 2026-07-25

## Contexto

Dois estudos motivaram esta rodada:

1. *From Loops to Graphs* (síntese do autoresearch/AgentHub de Karpathy + infraestrutura de workflows da Anthropic). O padrão central é o **ratchet loop** (catraca) do autoresearch: um agente dentro de um harness executável propõe **uma** mudança motivada por vez, mede uma métrica fixa, **mantém o commit se melhorou e reverte se não**, e registra tudo — ~700 experimentos em dois dias, 20 otimizações retidas. Quatro condições fazem o loop funcionar: saída **verificável** (métrica mensurável), ação **reversível** (git), horizonte **curto** (rodadas de minutos) e ambiente **delimitado** (arquivos mutáveis explícitos). A peça mais transferível é o `program.md` que "programa o programa": instruções em linguagem natural configurando uma organização autônoma (métrica e direção, arquivos mutáveis/protegidos, orçamento, regras de commit/revert, política de escalação, critério de exaustão). O paper também nomeia o **orçamento de complexidade** (declarar limites antes de rodar; no esgotamento, devolver o melhor artefato **com as lacunas declaradas** — nunca esconder falha parcial atrás de resposta fluente) e a **frase de rastreabilidade** como régua de confiabilidade.
2. *Andrew Ng — 4 agentic steps*. A evidência HumanEval (GPT-3.5 zero-shot 48,1% → com workflow agêntico 95,1%, contra GPT-4 zero-shot 67,0%): **arquitetura de workflow importa mais que upgrade de modelo**. Dos 4 padrões, Reflection é o mais robusto ("quase sempre consigo fazer funcionar") — com disciplina específica: **separar crítica de reescrita** (lista estruturada de defeitos primeiro, revisão depois), avaliador citando evidência, limite de iterações. E a regra de maturidade: adicione o próximo padrão **só quando o modo de falha atual é compreendido** e o padrão o endereça; senão, meça antes.

O que a fábrica já cobre dos dois papers: pipeline de grafo com proveniência (ADR-0009), grafo como memória compartilhada/fundamentação/modelo de mundo, memória em camadas (ADR-0010), disciplina de grafo de dependências no `/mobilizar`, modelo por etapa. O que **falta**: um ciclo de melhoria guiado por métrica com manter-ou-reverter, orçamento explícito no fan-out, reflexão estruturada no Definition of Done e a régua de rastreabilidade na validação.

## Decisão

A partir da **v0.10.0**, quatro adições:

### 1. Nova skill: `otimizar` (12ª skill)

Ciclo de catraca em sessão: o usuário aponta um alvo com métrica mensurável por comando; a skill escreve o **programa de otimização** (`decisoes/otimizacoes/OTIM-<slug>.md` — métrica e direção, sentinelas, arquivos mutáveis/protegidos, orçamento, critério de exaustão), mede o baseline e roda a catraca — uma mudança por rodada, medir, manter-ou-reverter via git, registrar a linhagem (hipótese, commit, métrica, decisão) inclusive das rodadas descartadas, que são evidência. Encerramento honesto: melhor estado, o que foi tentado e descartado, o que ficou sem tentar.

Salvaguardas de projeto:

- **Pré-condições obrigatórias** (as 4 do autoresearch). Sem métrica honesta, sem git limpo, sem delimitação de arquivos → a skill para e diz o que falta.
- **Sentinelas anti-Goodhart.** A catraca melhora a métrica que enxerga; toda otimização declara métricas-sentinela que não podem degradar (suite verde, memória, latência…). Melhora que viola sentinela = revertida.
- **Quem lidera depende da métrica** (Laura roteia): latência/query → Vinícius + Carlos; bundle/Web Vitals → Marina + Vinícius; custo cloud → Elisa; F1 de extração do grafo → Olívia; prompt de IA do produto → Gabriel; cobertura → Ricardo. Nenhuma persona nova.
- **Linhagem de trabalho × grafo de conhecimento são complementares, não colapsáveis** (lição do AgentHub): o git responde "o que mudou, de onde descende, o que foi tentado"; o grafo responde "o que é verdade sobre o quê". Aprendizado durável de uma otimização sobe de camada via `/mapear-conhecimento atualizar`.

### 2. Orçamento de complexidade no `/mobilizar`

Antes de lançar o time, Laura declara: máximo de teammates, de rodadas de correção, de tempo e a evidência mínima para encerrar. Orçamento esgotado → entrega o melhor estado atual **com lacunas e pendências declaradas explicitamente** — em vez de continuar consumindo tokens ou fingir completude.

### 3. Reflexão estruturada no Definition of Done (anti-drift)

O `templates/anti-drift.md` (injetado em todo teammate) ganha a disciplina de Ng no DoD: antes de marcar `completed`, o teammate **critica o próprio artefato contra o "Done when"** produzindo lista estruturada de defeitos (critério a critério, com evidência), corrige, e só então marca. Crítica separada da reescrita; "olhei e parece bom" não é crítica.

### 4. Régua de rastreabilidade no `/validar`

A frase-régua dos papers vira regra do veredicto: *toda saída importante rastreia até requisito → artefato/diff → fonte (gate rodado ou aresta do grafo) → decisão de avaliador*. Cadeia quebrada = não é "aprovado". O `/evoluir` ganha a regra de maturidade correspondente: recomendar capacidade nova só contra modo de falha compreendido; modo de falha incerto → a evolução da semana é **medir**.

## Fronteira com o Ralph Loop (kairos-ai) — por que isto NÃO é portagem

O kairos-ai tem o **Ralph Loop** (auto-correção de assertions até 3 tentativas), item da lista "não portar" (ADR-0002). A fronteira:

| | Ralph Loop (kairos-ai) | `otimizar` (forge) |
|---|---|---|
| Alvo | Assertions binárias de **compliance regulatório** | **Métrica técnica** contínua escolhida pelo usuário |
| Modo | Auto-correção até passar (runtime, workflow fixo) | Experimentação manter-ou-reverter (em sessão, catraca) |
| Base | Domínios regulados (LGPD, NRs…) | Genérico: performance, custo, qualidade de extração |
| Veredito | Passa/não passa contra regra legal | Melhorou/não melhorou contra baseline + sentinelas |

`otimizar` é técnico genérico (critério do ADR-0002: pode ir pros dois lados); não importa nada do kairos-ai e não introduz guardrail com referência legal. O limite de runtime também permanece: a catraca roda **em sessão**, com o usuário presente — não é worker headless 24/7.

## Versão

Nova skill → bump **minor** 0.9.0 → **0.10.0**. O roadmap aspiracional da v0.10 (`/migrar`, modo RFC, Mermaid, debate) desloca para o minor seguinte — mesma precedência dos ADRs 0007/0011.

## Consequências

Boas:

- A fábrica ganha o loop que os dois papers apontam como o átomo do progresso autônomo: melhoria mensurável, reversível e com linhagem auditável.
- `/mobilizar` deixa de ter custo em aberto: orçamento declarado e falha parcial visível.
- O DoD dos teammates herda o padrão mais robusto de Ng (reflexão) no ponto mais barato (antes do completed).
- Rastreabilidade vira critério objetivo de veredicto, não aspiração.

Custos:

- Risco de Goodhart (otimizar a métrica errada). Mitigado: sentinelas obrigatórias no programa + baseline + revert barato.
- Risco de confundir com o Ralph Loop. Mitigado: fronteira explícita neste ADR.
- Mais uma skill para conhecer. Mitigado: Laura roteia; pré-condições fazem a skill se recusar quando não é o caso.

## Alternativas consideradas

1. **Portar o Ralph Loop.** Rejeitado: regulatório e de runtime — dupla violação do ADR-0002.
2. **Embutir a catraca dentro do `/evoluir`.** Rejeitado: `/evoluir` decide *o que* construir (semanal, entrevista); `otimizar` executa *melhoria contínua de uma métrica* (sob demanda, horas). Ritmos e artefatos diferentes.
3. **Fazer da catraca um modo do `/mobilizar`.** Rejeitado: mobilizar paraleliza tarefas independentes; a catraca é deliberadamente serial (uma mudança por vez é o que dá atribuição causal à métrica).
4. **Não adicionar nada (já temos validar/auditar).** Rejeitado: validar/auditar julgam estados; nenhuma skill melhora um estado iterativamente contra métrica com manter-ou-reverter — exatamente o gap que os papers apontam.
