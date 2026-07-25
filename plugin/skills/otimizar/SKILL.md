---
name: otimizar
description: Conduz um ciclo de catraca (ratchet) de otimização guiado por métrica — uma mudança por rodada, medir, manter se melhorou ou reverter via git, registrando a linhagem completa. Use quando houver uma métrica mensurável por comando a melhorar (latência, bundle, custo de query, F1 de extração, cobertura) dentro de um orçamento de rodadas. Requer métrica honesta, git limpo e arquivos mutáveis delimitados; a skill se recusa sem isso.
---

# Otimizar — ciclo de catraca guiado por métrica

Você está sendo invocado para conduzir um **ratchet loop**: melhorar uma métrica concreta por experimentação disciplinada — uma mudança motivada por vez, medição imediata, manter-ou-reverter, linhagem registrada. A catraca só gira pra frente: estado retido nunca piora a métrica.

## Regra de ouro

**Uma mudança por rodada.** É o que dá atribuição causal: se a métrica mudou, você sabe por quê. Duas mudanças na mesma rodada = rodada inválida. E **falha parcial nunca se esconde**: rodada revertida é evidência registrada, não vergonha apagada.

## Pré-condições (sem elas, pare)

As quatro condições que fazem a catraca funcionar. Verifique **antes** de começar; se faltar qualquer uma, diga o que falta e o que fazer primeiro:

| Condição | Verificação | Se faltar |
|---|---|---|
| **Saída verificável** | Existe comando que devolve a métrica como número? | Defina o gate primeiro (`contextos/testes.md`, script de benchmark) |
| **Ação reversível** | `git status` limpo? Working tree commitada? | Commit ou stash antes; a catraca depende de revert barato |
| **Horizonte curto** | Uma rodada (mudar + medir) cabe em minutos? | Reduza o escopo da medição (subset, amostra, benchmark local) |
| **Ambiente delimitado** | Dá pra listar os arquivos que PODEM mudar? | Delimite com o usuário; catraca sem fronteira vira deriva |

Mudança irreversível (migration destrutiva, drop de dados) **não entra em catraca** — isso é `/kairos-forge:especificar` com plano e rollback.

## Quem lidera (Laura roteia pela métrica)

| Métrica | Especialista |
|---|---|
| Latência de endpoint, tempo de query | Vinícius + Carlos |
| Bundle size, Core Web Vitals | Marina + Vinícius |
| Custo cloud, consumo de recurso | Elisa |
| Precisão/recall/F1 de extração do grafo | Olívia |
| Qualidade de prompt/eval de IA do produto | Gabriel |
| Cobertura de testes, flakiness | Ricardo |
| Tempo de build/CI | Marcos |

O especialista conduz em primeira pessoa. Métrica fora da tabela: Laura decide quem entra.

## Fluxo

### 1. Escrever o programa de otimização

Antes de qualquer mudança, crie `decisoes/otimizacoes/OTIM-<slug>.md`. Este arquivo **programa o programa** — é o contrato da autonomia da catraca:

```markdown
# OTIM-<slug> — <título>

**Métrica:** <comando exato> → <número>. Direção: <menor|maior> é melhor.
**Baseline:** <valor medido antes da rodada 1> (<data>)
**Sentinelas (não podem degradar):** suite verde (`<comando>`), <memória ≤ X>, <outra>
**Arquivos mutáveis:** <globs explícitos>
**Arquivos protegidos:** <o que NUNCA muda — ex.: o script da métrica, migrations, config de CI>
**Orçamento:** <N> rodadas | <tempo máx.> | interrupção pelo usuário a qualquer momento
**Critério de exaustão:** <N> rodadas seguidas sem melhora → encerrar
**Escalação:** mudança fora dos mutáveis, dúvida de segurança, ou sentinela ambígua → perguntar ao usuário

## Linhagem

| # | Hipótese | Commit | Métrica | Sentinelas | Decisão |
|---|---|---|---|---|---|
```

Regras do programa:

- **A métrica é sagrada.** O comando que a mede fica nos protegidos — otimizar o medidor é o modo de falha clássico (Goodhart).
- **Sentinelas obrigatórias.** A catraca melhora a métrica que enxerga e só ela; sentinelas guardam o que ela não enxerga. Mínimo: a suite de testes relevante verde.
- **Orçamento antes da rodada 1.** Sem orçamento, catraca vira consumo sem fim.

### 2. Medir o baseline

Rode o comando da métrica no estado atual. Registre no programa. Sem baseline não existe "melhorou".

### 3. Rodar a catraca

Para cada rodada, exatamente isto:

1. **Inspecionar** o estado atual e a linhagem (o que já foi tentado? o que descartamos e por quê?).
2. **Propor UMA mudança** com hipótese explícita: "reduzir N+1 na listagem deve cortar ~30% da latência".
3. **Commitar a candidata**: `exp(<slug>): <hipótese em uma linha>`.
4. **Medir**: comando da métrica + sentinelas.
5. **Crash?** Erro mecânico (import, typo) → conserte e meça de novo. Erro não-óbvio → reverta e registre como `crash`.
6. **Decidir**: melhorou a métrica **e** sentinelas intactas → mantém. Senão → `git reset --hard` para o último estado retido, registre como `revertida`.
7. **Registrar a rodada** na tabela de linhagem — mantidas e revertidas, com o valor medido. Rodada descartada ensina: a hipótese que falhou não será tentada de novo.
8. **Checar orçamento e exaustão**: estourou rodadas/tempo, ou N rodadas seguidas sem melhora → encerrar. Senão, próxima rodada.

Ao longo das rodadas, **releia a linhagem antes de propor**: as melhores hipóteses novas nascem do padrão das descartadas.

### 4. Encerramento honesto

Sempre, inclusive por exaustão de orçamento:

```markdown
✅ OTIM-<slug> encerrada: <motivo — meta atingida | orçamento esgotado | exaustão>.

Métrica: <baseline> → <final> (<±X%>). Sentinelas: intactas.
Rodadas: <N> total — <M> mantidas, <K> revertidas, <C> crash.

Mantidas: <lista curta: hipótese → ganho>
Descartadas que ensinam: <hipóteses que falharam e por quê — evita re-tentativa>
Não tentado (candidatos pra próxima catraca): <lista>

Registro completo em decisoes/otimizacoes/OTIM-<slug>.md.
```

Se a métrica final for igual ao baseline, diga isso — "rodamos N rodadas e nada superou o baseline" é resultado válido e informativo.

### 5. Subir o durável de camada

A linhagem é o **grafo de trabalho** (o que foi tentado, de onde descende — o git guarda). Ela não substitui o grafo de conhecimento: se uma otimização mantida revela fato estrutural ("o gargalo do relatório era o índice X, não a serialização"), recomende `/kairos-forge:mapear-conhecimento atualizar` para o fato virar aresta com proveniência — e, se a lição foi cara, `.agents/memory/`.

## Quando NÃO usar

- **Sem métrica honesta** — "deixar o código mais limpo" não é métrica. Use `/kairos-forge:revisar` ou refatoração com SPEC.
- **Mudança irreversível** — migrations destrutivas, deleção de dados. Catraca pressupõe revert barato.
- **Trabalho que exige contexto coerente único** — design de arquitetura, decisão de produto, escrita. Fragmentar em rodadas degrada (limite conhecido do padrão).
- **Tarefa paralela por natureza** — auditar N arquivos independentes é `/kairos-forge:mobilizar`, não catraca (a catraca é deliberadamente serial).

## Regras

- **Uma mudança por rodada.** Sem exceção.
- **Nunca tocar os protegidos** — em especial o comando da métrica e as sentinelas.
- **Registrar toda rodada**, inclusive revertidas e crashes. Linhagem incompleta = experimento não-auditável.
- **Orçamento declarado antes da rodada 1.** Esgotou → encerramento honesto, nunca "só mais uma rodada" em silêncio.
- **Melhora que viola sentinela é derrota**, não vitória. Reverta.
- **Escale em vez de decidir sozinho** quando a mudança boa estiver fora dos mutáveis.
- **PT-BR em tudo** — programa, hipóteses, mensagens de commit (`exp(<slug>): ...`), relatório.
