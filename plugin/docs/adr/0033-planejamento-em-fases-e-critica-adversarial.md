# ADR-0033 — Planejamento em fases, crítica adversarial da SPEC e teto de onda

- **Status:** aceito
- **Data:** 2026-08-05
- **Versão:** v0.26.0

## Contexto

Análise da landing page do curso *Inverted Agentic Orchestration* (Yan Justino, ago/2026)
e segunda passada nos pipelines `/featdevelop` + `/featbuild` do LionCode.

Ressalva de método, registrada: a página do curso é **material de venda**, não conteúdo
de aula. Dela saem afirmações e desenho, não lições. O que sustenta este ADR é o código
do LionCode, que está no disco e foi lido.

O achado que organiza os três itens é uma pergunta: **por que o pipeline do LionCode tem
gate em cada fase do planejamento, e o nosso `/especificar` não?**

A resposta não é que eles pensaram melhor. É que os gates dele existem para um regime que
nós ainda não tínhamos: **ninguém lendo**. Em sessão interativa, uma premissa errada na
SPEC é pega porque um humano lê o documento antes de aprovar. Num arco conduzido por
script — que é para onde o `ciclo.py` vem apontando desde o ADR-0029 e que a conversa do
runtime torna concreto — o orçamento inteiro queima construindo a coisa errada com
disciplina impecável.

É o ADR-0024 (isolamento proporcional à supervisão) aplicado ao **planejamento** em vez
da execução.

E uma constatação de inventário: os checkpoints **já existem**. O `/especificar` para em
"espelhar entendimento" (passo 4) e em "propor 2-3 abordagens" (passo 5), com Pare e
Pergunte e modo RFC embutidos. O problema é que são **conversacionais, não estado** — o
`ciclo.py` não sabe que existem, então não há onde um runner parar.

## Decisão

### A — Os checkpoints do `/especificar` viram estado

O planejamento deixa de ser um estado (`especificando`) e passa a ser sete:

```
enquadrando ─▶ aguardando_entendimento ─▶ desenhando ─▶ aguardando_abordagem
   ▲ ajustar          │                      ▲ ajustar        │ escolhida
   └──────────────────┘                      └────────────────┤
                                                              ▼
              aguardando_aprovacao ◀── criticando ◀── especificando
                                          ▲ │ com_achados
                                          └─┴─ corrigindo_spec
```

Os dois gates novos (`aguardando_entendimento`, `aguardando_abordagem`) **não são
fricção nova**: são os mesmos três pontos em que o `/especificar` já parava — espelhar,
escolher, aprovar. A diferença é que agora estão escritos, e um script consegue honrá-los.

O que **não** foi adotado: o desdobramento do LionCode em quatro documentos
(`prd → tech → spec → sprints`). O ADR-0005 escolheu **uma** SPEC rastreável de ponta a
ponta, e o ADR-0013 recusou a planilha paralela — quatro artefatos para manter em
sincronia é exatamente isso. As fases são checkpoints na produção de um documento.

### B — Crítica adversarial da SPEC, antes do gate humano

Verificação prévia: a fábrica tinha **zero** validação adversarial da SPEC. Os arquitetos
debatem *durante* a redação; ninguém ataca o resultado *depois*. É a única etapa do arco
sem contraditório — `/validar` tem Ricardo e Patrícia, `/revisar` tem Helena e Patrícia,
`/avaliar` tem painel de juízes (ADR-0031), e a SPEC, que é a raiz de todo o resto, tinha
o autor.

Novo estado `criticando`: **ao menos dois críticos que não escreveram a SPEC** atacam
premissa, requisito, plano e testabilidade, escolhidos por eixo de risco entre as personas
existentes (Joana/Norma em requisito, Diego/Fernanda/Thiago em arquitetura,
Ricardo/Patrícia em testabilidade, Helena em segurança, Camila/Hugo em escopo). Sem
persona nova.

Relatório em `docs/specs/criticas/CRITICA-<SPEC>-<data>.md`, com fence própria
` ```kairos-critica ` e **três regras verificadas por código** — as duas primeiras iguais
às dos outros contratos (ADR-0032), a terceira só daqui:

1. **Coerência** — `bloqueado` ⟺ `achados ≥ 1`.
2. **Prova de cobertura** — `achados: 0` exige `examinado` não-vazio.
3. **Independência** — ao menos 2 nomes distintos em `criticado_por`. **Um olhar só é
   revisão, não crítica**, e quem recusa é o parser.

Por que dois e por que não o autor: pedir a quem escreveu que releia sem âncora externa é
a autocorreção intrínseca que o anti-drift já recusa (Huang et al., ICLR 2024). O que
funciona é olhar independente com critério explícito.

Por que **antes** do gate humano: um usuário que recebe SPEC com premissa furada gasta a
atenção dele achando o que dois agentes achariam de graça.

O gate tem orçamento próprio, com progresso devolvendo ficha e teto absoluto — mesma
mecânica do ADR-0032, agora em três gates (`criticar`, `validar`, `revisar`) em vez de
dois.

### C — Teto numérico de onda no `/mobilizar`

O LionCode tem `FEATURE_BUILD_MAX_WAVE_CHILDREN = 8` com sub-lotes acima. O nosso
`/mobilizar` dizia *"mais teammates ≠ melhor"* — julgamento.

Agora: **máximo 6 teammates simultâneos**, times maiores rodam em ondas com fan-in entre
elas. O 6 não é novo — é o mesmo número que a skill já usava para o fan-in em camadas.

**Julgamento funciona enquanto tem alguém olhando.** Em execução conduzida por script,
"não exagere no paralelismo" não impõe nada; 6 impõe.

### D — Correção de simetria: `limpo` da revisão também exige artefato

Achado ao implementar: o ADR-0032 fez a revisão ser salva em disco, mas o `ciclo.py` só
checava o artefato para `validando`. `registrar limpo` continuava aceito na palavra do
agente. Corrigido — os três gates agora usam a mesma tabela.

## Consequências

**Positivas**

- A SPEC deixa de ser a única etapa do arco sem contraditório, e é a que mais custa quando
  está errada — todo o resto deriva dela.
- O planejamento fica conduzível por script sem perder nenhum dos pontos em que o humano
  já decidia.
- Três gates com a mesma mecânica de orçamento, contrato e artefato. Menos casos especiais
  do que quando eram dois e meio.
- O teto de onda transforma a última regra de paralelismo que era conselho em número.

**Negativas e limites, declarados**

- **O arco ficou mais longo.** São 7 estados de planejamento onde havia 2, e uma rodada de
  crítica antes de o usuário ver a SPEC. Em feature pequena isso é cerimônia — e a saída é
  `--spec-aprovada`, que pula o planejamento inteiro, ou chamar `/especificar` direto sem
  o `ciclo.py`.
- **A independência é verificada por nome, não por identidade.** Nada impede o mesmo agente
  de assinar como "Joana" e "Ricardo". O contrato cobra dois nomes distintos; que sejam
  dois olhares de verdade é disciplina, como o conjunto selado do ADR-0030.
- **Dois críticos não são um painel.** O ADR-0031 exige família diferente para juiz de
  eval; aqui todos os críticos são o mesmo modelo com personas diferentes. Isso vale como
  contraditório estruturado, **não** como independência estatística — e a diferença está
  registrada de propósito.
- **O 6 do teto de onda é herdado, não medido.** Veio do fan-in da própria skill e casa com
  a ordem de grandeza do LionCode (8). Ninguém mediu onde a coordenação degrada de fato.
- **Mais um contrato para os relatórios legados não terem.** Como no ADR-0032, o guardrail
  só morde bloco presente-e-errado; SPEC antiga sem crítica segue passando.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Adotar `prd → tech → spec → sprints` como quatro documentos | ADR-0005 (uma SPEC rastreável) e ADR-0013 (nada de planilha paralela). Quatro artefatos para sincronizar é o anti-padrão, não a solução |
| Um crítico só, para economizar | É revisão, não crítica. E o modo de falha que interessa — o autor achando que está bom — não é resolvido por mais uma passada do mesmo tipo de olhar |
| Crítica **depois** do gate humano | Inverte quem paga o custo do erro barato. O humano deve decidir sobre uma SPEC já criticada, não descobrir os furos por conta própria |
| Deixar a crítica sem contrato, registrada na palavra do agente | Seria o único dos três gates fora da regra do ADR-0029. Um gate que se auto-declara limpo não é gate |
| Adotar `pick` (o harness escolhe a próxima feature) | Cruza a fronteira de aprovação: escolher o próximo trabalho é decisão do usuário, não do arco |
| Teto de onda configurável desde já | Número sem uso não tem base para ser ajustado. Fixa em 6, mede, depois abre se doer |
