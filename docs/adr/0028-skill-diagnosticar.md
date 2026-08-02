# ADR-0028 — Skill `diagnosticar`: a porta de entrada de sistema existente

- **Status:** aceito
- **Data:** 2026-08-02
- **Versão:** v0.20.0

## Contexto

A fábrica sabia construir e sabia modernizar. Não sabia **decidir por onde começar** num
sistema que já existe.

Olhando a cadeia atual com honestidade:

- `/mapear-arquitetura` (Diego) produz mapa de **estrutura** — inventário, acoplamento,
  duplicação, plano de decomposição. Não pontua saúde, não mede nada, não prioriza por
  impacto e não tem horizonte de tempo.
- `/auditar` pontua **a fábrica**, e a própria skill declara: *"não audita o código do
  produto"*.
- `/otimizar` abre com *"sem métrica honesta, pare"* — exige a métrica **já escolhida**.
- `/migrar` tem na description do Ivan: *"não use para decidir SE migra"* — exige a decisão
  **já tomada**.

Ou seja: **duas skills exigiam um insumo que nenhuma outra produzia.** Quem herdava um
legado tinha os especialistas (Ivan, Vinícius, Carlos, Renata, Helena, Rafael, Hugo, Rui) e
nenhum ritual que os transformasse num documento de decisão com número e ordem.

O gatilho concreto veio de um formato comercial que circula entre devs — o "diagnóstico
técnico" de três páginas vendido a cliente: score geral, achados priorizados, impacto
estimado e roadmap por horizonte. O formato é bom e o mercado existe. O que ele traz junto
é um risco: os ganhos projetados costumam ser números sem base ("-96% no tempo de
resposta"), e isso é exatamente o tipo de conteúdo que o ADR-0015 proíbe — com o agravante
de ir para um terceiro que pode conferir.

## Decisão

Skill **`diagnosticar`** (17 → 18 skills), dona **Rafael (Staff)**, mais o script
`scripts/diagnostico.py` que produz a evidência determinística.

### Nenhum agente novo

Os especialistas já existiam e cobrem as seis dimensões: Vinícius (performance), Sérgio +
Ricardo (confiabilidade), Helena (segurança), Rafael + Diego (manutenibilidade), Renata
(observabilidade), Elisa (custo), com Hugo (ICE) e Rui (ROI) na priorização.

Rafael é dono por ser o artefato um **documento de decisão** — e permanece consultivo
(`Read, Grep, Glob, WebSearch, WebFetch`, sem escrita), o que reforça a última regra da
skill: diagnóstico produz decisão, não correção. Mesmo padrão de Isabela no `/desenhar` e
Diego no `/mapear-arquitetura`.

### Escada de evidência declarada

O que se pode afirmar depende do acesso, e o nível vai no topo do relatório:

| Nível | Acesso | O que vira `medido` |
|---|---|---|
| 1 | Só o repositório | Churn, autoria, razão teste/produção, dependências, dívida marcada, tamanho |
| 2 | + ambiente executável | Latência real, P95, plano de execução, N+1 observado |
| 3 | + telemetria de produção | Carga real, taxa de erro, saturação, custo |

Diagnóstico de nível 1 é legítimo — **desde que diga que é nível 1**. Se o acesso prometido
não se materializa, a skill manda rebaixar o nível e declarar, nunca substituir medição por
suposição.

### `scripts/diagnostico.py` — a camada que pode ser citada como `medido`

Sem ele, todo número do relatório seria impressão do modelo. O script mede, só com stdlib e
sem executar a aplicação: atividade e frequência de commit, hotspots **de código** (manifest
e doc contados à parte, para não afogar o sinal), **concentração de autoria nos hotspots**
(o bus factor onde importa), razão teste/produção, inventário de dependências com contagem
sem versão fixa, densidade de marcadores de dívida e distribuição de tamanho de arquivo.

Ele deliberadamente **não pontua e não infere causa**. "Arquivo X mudou 25 vezes e tem autor
único" é dado; "X é o gargalo de manutenção" é julgamento — e julgamento é da skill,
rotulado como `inferido`.

### As três regras que sustentam o documento

1. **Toda afirmação rotulada** `medido` / `inferido` / `não verificável`.
2. **Rubrica publicada junto do score.** Score cuja conta o leitor não consegue refazer é
   teatro. E o Score Geral nunca aparece sozinho — a tabela por dimensão anda com ele,
   porque média esconde variância.
3. **Ganho projetado só com faixa e base declarada.** "50–200ms, base: `EXPLAIN ANALYZE`
   mostra seq scan em tabela de 2,1M linhas" passa. "-96%" não passa. Sem base, escreve-se
   "não estimável com o acesso atual" — que é mais forte, porque é verificável.

A seção **"o que não foi possível verificar"** é obrigatória e nunca fica vazia num
diagnóstico de nível 1.

### Encaminhamento — é isso que fecha o fluxo

O relatório termina roteando cada achado para a skill que o executa: `/otimizar` (achado com
métrica e alvo), `/migrar` (achado estrutural), `/especificar` (achado que é feature),
`/analisar-ameacas` (superfície sensível sem threat model).

## Consequências

**Positivas**

- Preenche o vão entre "herdei um sistema" e "sei o que atacar" — as duas skills que
  exigiam insumo passam a tê-lo.
- O `diagnostico.py` dá ao relatório uma espinha medida, em vez de opinião com casa decimal.
  Rodado contra dois repositórios reais durante o desenvolvimento, ele já expôs sinal
  legítimo (concentração de autoria em 10/10 hotspots num deles).
- Habilita o uso comercial (diagnóstico como entregável) **com** a disciplina de evidência
  da fábrica, em vez de sem ela.
- Formaliza uma distinção que estava implícita: `auditar` olha a fábrica, `diagnosticar`
  olha o produto.

**Negativas e limites, declarados**

- **Nível 1 é o único garantido.** Níveis 2 e 3 dependem de acesso que o plugin não
  controla. Muitos diagnósticos vão sair com confiança "média" — e é melhor dizer isso do
  que inflar.
- **Score é julgamento com rubrica, não medição.** A rubrica publicada torna a conta
  auditável; não torna a escala objetiva. Duas pessoas competentes podem pontuar 68 e 74.
- **`diagnostico.py` é heurístico.** Extensão define "código", regex define "teste", e
  parsing de manifesto cobre os ecossistemas comuns — não todos. Falha em silêncio para
  formato desconhecido (campo `null`), o que é preferível a chutar.
- **Churn de 90 dias não vê dívida antiga e estável.** Módulo horroroso que ninguém toca não
  aparece nos hotspots — e às vezes é exatamente o problema. A leitura de estrutura
  (Manutenibilidade) precisa cobrir isso.
- **18 skills.** A fronteira com `auditar`, `mapear-arquitetura` e `revisar` está na
  description com gatilho negativo, e o gold set de roteamento ganhou casos — mas o custo de
  roteamento cresce a cada skill.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Estender `/mapear-arquitetura` com score e roadmap | Mistura duas perguntas diferentes: "como está organizado" e "quão saudável está". A description ficaria impossível de rotear, e o mapa perderia o foco estrutural que já funciona |
| Estender `/auditar` para pontuar o produto | A skill declara explicitamente que não audita o produto, e o sujeito é outro (setup da fábrica × sistema do cliente). Somar as duas escalas confundiria as duas leituras |
| Criar um agente "Diagnosticador" | Os oito especialistas necessários já existem. A lição do ADR-0021 vale aqui: a resposta não é o agente nº 72 |
| Deixar o script pontuar e priorizar | Pontuação é julgamento com trade-off — território do Rafael. Script que pontua daria aparência de objetividade a uma escolha subjetiva, que é pior que a escolha assumida |
| Gerar o PDF/layout na própria skill | Conteúdo verificável e diagramação são preocupações separadas. A skill entrega markdown auditável; identidade visual é de uma skill de documento |
