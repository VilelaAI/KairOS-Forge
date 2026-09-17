---
name: especificar
description: Inicia o spec-driven development: Laura classifica, arquitetos interrogam, SPEC rastreável em docs/specs/. Use antes de codar qualquer mudança não-trivial; trivial (1 arquivo, <20 linhas) vai direto.
---

# Especificar — fluxo spec-driven

Você está sendo invocado para iniciar o ciclo de design **antes** da implementação.
Esta raiz dá o fluxo, os checkpoints e os pontos de decisão; o detalhe de cada etapa
está em `references/` (índice no fim) — leia só o que a etapa em curso pede.

## Regra de ouro

Não codifique. Não chame teammate de implementação. Esta skill produz **artefato textual** — uma SPEC — que servirá de contrato para `/kairos-forge:mobilizar` ou execução manual depois.

## Fluxo

### 1. Laura entra primeiro

Invoque o agente `laura-tech-lead`. Ela ouve a descrição do usuário, classifica o tamanho pela matriz abaixo, decide quais arquitetos da fábrica entram e define o nível de cerimônia necessário.

### 1.1. Auto-sizing obrigatório

Laura classifica antes de perguntar demais:

| Tamanho | Sinais | Saída esperada |
|---|---|---|
| **Trivial** | 1 arquivo, < 20 linhas, typo, rename, formatação | Não criar SPEC. Encaminhar execução direta. |
| **Pequeno** | 1-2 arquivos, sem schema/API/auth, baixo risco | SPEC curta ou plano inline com gate de teste. |
| **Médio** | 3+ arquivos, endpoint novo, tela nova, regra de negócio | SPEC completa com requisitos rastreáveis. |
| **Grande** | Banco + API + UI, integração externa, dados críticos | SPEC completa + tarefas atômicas + matriz de testes. |
| **Complexo** | Auth, PII, segurança, migração irreversível, decisão arquitetural | SPEC completa + ADR sugerido + validação formal antes de PR. |

Se for trivial, pare e diga por que a SPEC não compensa. Se for pequeno ou maior, continue.

**Apetite antes de escopo (Shape Up — ADR-0015):** junto do tamanho, Laura pergunta quanto **vale** investir ("isso é uma tarde, uma semana ou um ciclo?"). O apetite é fixo; o escopo é que varia para caber nele — se a feature não cabe no apetite, corta-se escopo (e o corte vira não-objetivo na SPEC), não se estica o investimento em silêncio.

### 1.2. Trilhas por tema (modo guiado — ADR-0013)

Antes de interrogar do zero, cheque se a feature casa com uma trilha em `${CLAUDE_PLUGIN_ROOT}/templates/trilhas/` (índice em `TRILHAS.md`): auth, pagamentos, painel-admin, api, seed-dados. Se casar, **parta da trilha em vez do zero** — trilha é rascunho, não fôrma: o arquiteto adapta ao stack (`contextos/stack.md`) e corta o que não se aplica. Como cada parte da trilha entra na SPEC: `references/trilhas.md`.

### 2. Laura aciona o(s) arquiteto(s)

| Tipo de mudança | Arquiteto principal |
|---|---|
| Feature com banco novo | **Fernanda** (dados) |
| Feature com API/integração | **Thiago** (integrações) |
| Feature com fluxo complexo entre componentes | **Diego** (sistemas) |
| Decisão de tecnologia ou padrão | **Rafael** (Staff) |
| Múltiplas dimensões | **Diego coordena**, chama Fernanda/Thiago conforme necessário |

Se a tarefa for primariamente de produto (escopo, priorização, MVP), Laura aciona **Camila (PM)** antes ou junto.

### 2.1. Consultar o grafo de conhecimento (se existir)

Se o projeto tem `.agents/grafo/entidades.jsonl`, antes de interrogar o usuário o arquiteto puxa o que a fábrica já sabe sobre as entidades da feature:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/grafo.py subgrafo "<componente/feature citado>" --saltos 2
```

Decisões, dependências e restrições já registradas (com fonte) entram na SPEC em vez de serem redescobertas — e conflito entre a feature nova e uma aresta existente ("X substitui Y", "X depende de Z") vira pergunta ao usuário antes de virar requisito.

**Se as tools MCP `memory_*` estiverem disponíveis** (ai-memory, ADR-0010), complemente com `memory_query` sobre as entidades da feature: tentativas passadas, abordagens descartadas e discussões de sessões anteriores que nunca chegaram aos arquivos curados. Abordagem já descartada volta para a SPEC como não-objetivo, com o porquê.

### 3. Arquiteto(s) interrogam em primeira pessoa

Cada arquiteto pergunta no seu eixo — repertório por persona em `references/perguntas-arquitetos.md`. Duas regras valem em toda interrogação:

- **Métrica de sucesso sem baseline não é métrica.** "De 5 para 3,5 minutos até setembro" é verificável; "reduzir 30%" sem o valor atual não é. Se o valor de hoje não for conhecido, o requisito P1 vira **medir primeiro**.
- **Pergunta com default recomendado (ADR-0019):** escolha **reversível** não trava o fluxo — o arquiteto declara o default ("recomendo X por Y; sigo com isso se você não disser o contrário"), registra a premissa na SPEC e continua. No **irreversível e no conteúdo inventável** não existe default, existe pergunta (passo 4.1).

### 4. Espelhar entendimento

Antes de escrever a SPEC, o arquiteto líder **resume em 3 bullets** o problema como entendeu. Pede correção do usuário.

Inclua o **Working Backwards** (ADR-0015): "se isso fosse lançado hoje, o que o usuário veria funcionando?" — a resposta é o critério de sucesso visível, e ancora quais requisitos são P1.

### 4.1. Pare e Pergunte — condições de parada (ADR-0015)

Antes de escrever qualquer requisito, verifique se dá para escrevê-lo **honestamente**. Situações que obrigam a parar e perguntar — nunca preencher com achismo, placeholder ou texto genérico: conteúdo institucional/jurídico/regulatório sem fonte oficial · integração externa sem provedor definido · cálculo de negócio sem fórmula · dados pessoais reais como exemplo · "igual ao site X" sem referência acessível · asset de terceiro em domínio alheio · tela vaga ("dashboard") sem saber o que mostra. A pergunta obrigatória de cada situação está em `references/pare-e-pergunte.md`.

**Regra de ouro:** se a única forma de escrever o requisito é inventar conteúdo que aparecerá ao usuário final como verdade, **pare**. Inventar é dívida silenciosa — só aparece quando alguém de fora descobre o erro.

### 5. Propor 2-3 abordagens

Cada uma com trade-offs explícitos (complexidade, custo, reversibilidade). Recomendar uma.

**Feature Pequena segue com o default (ADR-0038).** Na classificação **Pequeno** do auto-sizing, os passos 4 e 5 vão numa mensagem só: o entendimento espelhado e **a abordagem recomendada como premissa** ("sigo com X por Y; diga se não for isso"), registrada na SPEC. Não há 2-3 alternativas para comparar — em mudança pequena e reversível isso é teatro, e a segunda parada não compra nada (ADR-0019). Médio, Grande e Complexo mantêm as alternativas e as duas confirmações. O Pare e Pergunte e a aprovação da SPEC (passo 8) valem para todo porte.

### 5.1. Modo RFC — decisões arquiteturalmente significativas (ADR-0018)

Quando a mudança for **Complexa**, cruzar **2+ times**, ter **reversibilidade baixa** (migração, troca de tecnologia, contrato público) — ou o usuário invocar `especificar rfc` — as abordagens do passo 5 não morrem no chat: viram RFC em `docs/rfcs/RFC-<NNN>-<slug>.md` ANTES da SPEC. **Rafael revisa todo RFC.** Template e regras (RFC contestado → `/kairos-forge:rodar debate`; aceito → ADR em `decisoes/`; recusado fica no repo): `references/modo-rfc.md`.

> **Os passos 4, 5 e 7 são checkpoints de verdade, não formalidade** (ADR-0033). Em
> sessão, você espelha o entendimento, o usuário confirma, e a conversa segue — o
> checkpoint acontece e ninguém precisa nomeá-lo. Conduzido pelo `ciclo.py`, cada um é
> um **estado**: `enquadrando → aguardando_entendimento → desenhando →
> aguardando_abordagem → especificando → criticando → aguardando_aprovacao`. É a mesma
> disciplina, escrita — porque sem ninguém lendo, uma premissa errada não é pega no
> passo 4; é pega depois de o orçamento inteiro construir a coisa errada.
> Por isso o atalho da feature Pequena acima é **de sessão**: conduzido pelo `ciclo.py`,
> cada gate humano continua esperando `confirmado`/`escolhida` — o contrato não muda.

### 6. Após aprovação, escrever a SPEC

Em `docs/specs/SPEC-<NNN>-<slug>.md` no projeto do usuário. Seções obrigatórias (Contexto → Próximo passo), template mínimo, prioridades P1/P2/P3 e os estados de Status × Verificação: `references/modelo-spec.md`.

Em SPEC Média+ com fluxo entre componentes, inclua um bloco Mermaid do desenho — à mão ou partindo do grafo:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/grafo.py mermaid "<entidade>" --saltos 2
```

O diagrama deriva do texto, nunca o substitui.

Se o projeto tiver `contextos/testes.md`, use os comandos de lá. Se não tiver, registre o gate como `<a definir>` e recomende preencher esse contexto.

### 7. Crítica adversarial antes da aprovação (ADR-0033)

A SPEC escrita **não vai direto para o usuário**. Antes, ao menos **dois críticos que não a escreveram** atacam o documento, escolhidos pelo eixo de risco: requisito (Joana, Norma) · arquitetura (Diego, Fernanda, Thiago) · testabilidade (Ricardo, Patrícia) · segurança (Helena) · escopo (Camila, Hugo). Cada achado vem **com localização** — seção, ID do requisito, linha do plano; "a SPEC parece boa" não é crítica.

Salve em `docs/specs/criticas/CRITICA-SPEC-NNN-YYYY-MM-DD.md` com a fence `kairos-critica` — o contrato lido pelo `ciclo.py`, com **três regras verificadas por código** (`contrato.py`):

1. **Coerência** — `bloqueado` exige `achados ≥ 1`; qualquer outro veredicto exige 0.
2. **Prova de cobertura** — `achados: 0` exige `examinado` não-vazio.
3. **Independência** — ao menos **2 críticos distintos** em `criticado_por`.

Achado 🔴 volta para a SPEC (`registrar com_achados`); corrigido, a crítica **reabre**, igual ao arco de validação. Achado que você discorda: corrija ou **escreva na SPEC por que não** — deixar sem resposta não é opção. Tabela de críticos por eixo, formato do arquivo com a fence e o porquê de dois críticos: `references/critica-adversarial.md`.

### 8. Confirmação ao usuário

```
✅ SPEC-NNN-<slug>.md criada por <Diego/Fernanda/etc>.

Plano tem N tarefas atribuídas a M agentes.

Próximos passos:
1. Revise a SPEC e ajuste se algo não bater
2. Feature com UI? Rode antes: /kairos-forge:desenhar SPEC-NNN
3. Quando aprovada, rode: /kairos-forge:mobilizar SPEC-NNN
   (ou execução sequencial: /kairos-forge:rodar)
4. Após implementar: /kairos-forge:validar SPEC-NNN
   (com UI: /kairos-forge:desenhar verificar DESIGN-NNN)
5. Antes do PR: /kairos-forge:revisar
6. Pra colocar em produção: /kairos-forge:lancar
```

## Quando NÃO escrever SPEC

Pular SPEC é OK pra:

- Mudança em 1 arquivo, < 20 linhas
- Renomeação, formatação, atualização de dep menor
- Correção de typo

NÃO pule pra:

- Endpoint novo
- Mudança em schema de banco
- Integração com sistema externo
- Mudança em auth/autorização/PII
- Refactor que toca 3+ arquivos

## Regras

- **Não pule a interrogação.** Mesmo que o usuário insista que "é simples". Se for, sai rápido.
- **Não escreva código nesta skill.** Implementação é com `/mobilizar` ou invocação direta dos devs.
- **Não invente requisitos.** Se o arquiteto não conseguiu obter clareza, registre como pergunta aberta na SPEC e pare.
- **Nomeie agentes específicos no plano de implementação.** Não escreva "developer" genérico — escreva "Marina" ou "Lucas".
- **Todo requisito P1 precisa de critério de aceite verificável.** Se não dá para verificar, ainda não é requisito pronto.
- **Critério de aceite tem valor, não adjetivo (ADR-0039).** "Rápido", "robusto", "amigável" não são critério; `WHEN <evento> THEN <resultado com valor>` é ("em ≤ 2 s", "status 403", "3 itens"). Adjetivo no critério é o que o crítico de testabilidade recusa.
- **A primeira tarefa do plano é uma fatia fim a fim (ADR-0039).** Um caminho fino que atravessa todas as camadas e já é testável; as tarefas seguintes aprofundam. Deixado sozinho, o modelo constrói por camada — banco, depois API, depois tela — e não há nada verificável até a última.
- **Todo item de implementação precisa de gate.** Pode ser teste automatizado, build, lint ou validação manual explícita.
- **Status "Concluído" exige célula Verificação iniciando com `verificado:`.** A regra existe para impedir o anti-padrão de marcar pronto sem rodar nada. Inspirada no checklist do Replit-Orchestrator (`briefing.md`): só vale verificado depois que o agente rodou o comando, abriu a URL ou executou o teste. Confiança em "escrevi o código, deve funcionar" não conta.

## Referências

Leia sob demanda, na etapa correspondente — caminho completo `${CLAUDE_PLUGIN_ROOT}/skills/especificar/references/<arquivo>`:

| Arquivo | Quando ler |
|---|---|
| `references/trilhas.md` | Passo 1.2 — a feature casa com auth, pagamentos, painel-admin, api ou seed-dados |
| `references/perguntas-arquitetos.md` | Passo 3 — repertório de perguntas de Diego, Fernanda, Thiago, Rafael e Camila |
| `references/pare-e-pergunte.md` | Passo 4.1 — tabela completa de situação × pergunta obrigatória, antes do primeiro requisito |
| `references/modo-rfc.md` | Passo 5.1 — template do RFC e regras (Rafael, debate, RFC aceito/recusado) |
| `references/modelo-spec.md` | Passo 6 — seções obrigatórias, template mínimo e estados de Status × Verificação |
| `references/critica-adversarial.md` | Passo 7 — críticos por eixo, formato do arquivo de crítica e a fence `kairos-critica` |
