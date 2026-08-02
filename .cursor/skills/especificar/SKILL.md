---
name: especificar
description: Inicia o fluxo de spec-driven development para uma feature ou mudança. Use no início de qualquer trabalho não-trivial — antes de escrever código. Aciona Laura (Tech Lead) que classifica complexidade, decide arquitetos, registra requisitos rastreáveis e gates. Resultado é uma SPEC em docs/specs/SPEC-NNN-slug.md pronta para /mobilizar, /rodar e /validar. Não use para mudança trivial (1 arquivo, menos de 20 linhas) — nesse caso execute direto, sem SPEC.
---

# Especificar — fluxo spec-driven

Você está sendo invocado para iniciar o ciclo de design **antes** da implementação.

## Regra de ouro

Não codifique. Não chame teammate de implementação. Esta skill produz **artefato textual** — uma SPEC — que servirá de contrato para `/kairos-forge:mobilizar` ou execução manual depois.

## Fluxo

### 1. Laura entra primeiro

Invoque o agente `laura-tech-lead`. Ela vai:

- Ouvir a descrição do usuário
- Classificar o tamanho usando a matriz abaixo
- Decidir quais arquitetos da fábrica entram
- Definir o nível de cerimônia necessário

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

Antes de interrogar do zero, cheque se a feature casa com uma trilha em `${CLAUDE_PLUGIN_ROOT}/templates/trilhas/` (índice em `TRILHAS.md`): auth, pagamentos, painel-admin, api, seed-dados. Sinais são diretos — "quero login" → trilha-auth; "checkout"/"cobrar" → trilha-pagamentos; "painel"/"admin" → trilha-painel-admin.

Se casar, **parta da trilha em vez do zero**: os requisitos típicos viram rascunho da tabela (renumerados pro projeto), as "perguntas que o arquiteto DEVE fazer" entram na interrogação, os riscos alimentam o `/kairos-forge:analisar-ameacas` (obrigatório nas trilhas marcadas como sensíveis), e as tarefas/gates sugeridos são o ponto de partida do plano. **Trilha é rascunho, não fôrma**: o arquiteto adapta ao stack (`contextos/stack.md`) e corta o que não se aplica. Pro usuário iniciante, isso é o modo guiado — ele diz o tema, a fábrica já sabe o caminho e o que perguntar.

### 2. Laura aciona o(s) arquiteto(s)

Mapeamento que Laura usa:

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

Perguntas típicas por agente:

- **Diego**: "Qual o fluxo de dados? Quem chama quem? Eventos síncronos ou assíncronos?"
- **Fernanda**: "Quantos registros esperados? Cardinalidade? Padrão de leitura/escrita?"
- **Thiago**: "Quem consome essa API? Versionamento? Auth?"
- **Rafael**: "Por que essa abordagem e não a alternativa óbvia? Trade-off de escala?"
- **Camila**: "Isso é MVP ou V2? Qual métrica de sucesso — e qual o valor dela **hoje**?"

**Métrica de sucesso sem baseline não é métrica.** "Reduzir o tempo de onboarding em 30%" não é verificável sem saber de quanto para quanto; "de 5 para 3,5 minutos até setembro" é. Se o valor atual não for conhecido, o requisito P1 vira **medir primeiro** — e isso é honesto, não atraso.

**Pergunta com default recomendado (ADR-0019):** escolha **reversível** não trava o fluxo — o arquiteto declara o default ("recomendo X por Y; sigo com isso se você não disser o contrário"), registra a premissa na SPEC e continua. O Pare e Pergunte (ADR-0015) permanece absoluto no **irreversível e no conteúdo inventável**: lá não existe default, existe pergunta.

### 4. Espelhar entendimento

Antes de escrever a SPEC, o arquiteto líder **resume em 3 bullets** o problema como entendeu. Pede correção do usuário.

Inclua o **Working Backwards** (ADR-0015): "se isso fosse lançado hoje, o que o usuário veria funcionando?" — a resposta é o critério de sucesso visível, e ancora quais requisitos são P1.

### 4.1. Pare e Pergunte — condições de parada (ADR-0015)

Antes de escrever qualquer requisito, verifique se dá para escrevê-lo **honestamente**. Se a tarefa cair numa condição abaixo, **pare e faça a pergunta** — nunca preencha a lacuna com achismo, placeholder ou texto genérico:

| Situação | Pergunta obrigatória |
|---|---|
| Conteúdo institucional/jurídico/regulatório citado sem fonte oficial | "De onde vem o texto? Você cola o oficial, ou adiamos até ter a fonte?" — proibido redigir "com base na legislação aplicável" (domínio regulado de verdade → kairos-ai) |
| Integração externa sem provedor definido (pagamento, e-mail, mapa) | "Qual provedor exatamente?" |
| Cálculo de negócio (preço, imposto, prazo) sem fórmula | "Qual a fórmula exata? Arredondamento? Qual o caso-teste esperado?" |
| Dados pessoais reais que apareceriam como exemplo/conteúdo | "Confirma esses dados? Posso usar exatamente assim?" — nunca 'Fulano de Tal' achando que alguém revisa depois |
| "Igual ao site X" sem URL acessível ou screenshot | "Tem referência que carrega? Sem ela não é pixel-perfect, é estimativa" |
| Asset de terceiro (PDF, imagem, vídeo) em domínio alheio | "Linko a URL externa (risco de 404) ou baixamos e hospedamos? Decisão registrada na SPEC" |
| Tela/funcionalidade vaga ("dashboard") sem saber o que mostra | "O que exatamente essa tela mostra? Quais dados, quais ações?" (caso pra Joana, do apoio-requisitos) |

**Regra de ouro:** se a única forma de escrever o requisito é inventar conteúdo que aparecerá ao usuário final como verdade, **pare**. Inventar é dívida silenciosa — só aparece quando alguém de fora descobre o erro.

### 5. Propor 2-3 abordagens

Cada uma com trade-offs explícitos (complexidade, custo, reversibilidade). Recomendar uma.

### 5.1. Modo RFC — decisões arquiteturalmente significativas (ADR-0018)

Quando a mudança for **Complexa**, cruzar **2+ times**, ter **reversibilidade baixa** (migração, troca de tecnologia, contrato público) — ou o usuário invocar `especificar rfc` — as abordagens do passo 5 não morrem no chat: viram RFC em `docs/rfcs/RFC-<NNN>-<slug>.md` ANTES da SPEC:

```markdown
# RFC-NNN — <decisão em uma frase>

- **Status:** rascunho | em discussão | aceito | recusado
- **Drivers:** o que pesa na decisão (custo, prazo, reversibilidade, time)

## Contexto
## Decisão proposta
## Diagrama

(bloco Mermaid do fluxo proposto — se o grafo existir, parta de
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/grafo.py mermaid "<entidade>" --saltos 2`)

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|

## Consequências

Positivas e negativas — inclusive o que fica mais difícil.
```

Regras do modo RFC:

- **Rafael revisa todo RFC.** Decisão de tecnologia/padrão é o território dele.
- **RFC "em discussão" contestado** → `/kairos-forge:rodar debate` estrutura o confronto (Álvaro/Lúcia/Félix) e a síntese volta pro RFC.
- **RFC aceito** → vira ADR curto em `decisoes/` (o porquê, permanente) e a SPEC referencia ambos (`RFC-NNN` no Contexto). SPEC continua sendo o contrato do *o quê* — o RFC guarda o *porquê*.
- **RFC recusado fica no repo.** Alternativa descartada com o motivo registrado é o que impede a fábrica de redescobri-la daqui a 6 meses.

### 6. Após aprovação, escrever a SPEC

Em `docs/specs/SPEC-<NNN>-<slug>.md` no projeto do usuário, com seções:

- **Contexto e problema** — qual dor real (referencie o RFC, se houver)
- **Objetivo** — uma frase
- **Não-objetivos** — o que está fora
- **Invariantes** — o que precisa ser verdade ao final
- **Diagrama** — em SPEC Média+ com fluxo entre componentes, bloco Mermaid do desenho (à mão ou via `grafo.py mermaid`); o diagrama deriva do texto, nunca o substitui
- **Requisitos rastreáveis** — IDs estáveis, prioridade, critério de aceite e status
- **Plano de implementação** — tarefas atômicas, cada item ≤ 1 dia, com agente, arquivos, dependências e gates
- **Matriz de testes** — tipo de teste por requisito/tarefa, comando esperado e responsável
- **Riscos e mitigações**
- **Perguntas abertas** — se houver qualquer incerteza bloqueante
- **Próximo passo** — sugestão de comando (`/kairos-forge:mobilizar SPEC-<NNN>`)

Use este template mínimo:

```markdown
# SPEC-NNN — <título>

## Contexto e problema

## Objetivo

## Não-objetivos

## Invariantes

## Requisitos rastreáveis

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| <SLUG>-01 | Como <persona>, quero <ação>, para <resultado>. | P1 | WHEN <evento> THEN <resultado> SHALL <comportamento verificável>. | Pendente | — |

Prioridades:
- **P1**: necessário para entregar a mudança
- **P2**: importante, mas pode sair em follow-up se explicitamente aprovado
- **P3**: desejável, não bloqueia entrega

Estados de Status × conteúdo obrigatório em Verificação:
- **Pendente** → Verificação = `—` (ainda não iniciado).
- **Em progresso** → Verificação começa com `em progresso: <o que ainda falta>`. Conta 0.5 no progresso da SPEC.
- **Concluído** → Verificação começa com `verificado: <como confirmei> (<dd/mm>)`. Sem essa linha, a `/validar` trata como "sem evidência" e bloqueia P1.

## Plano de implementação

| Tarefa | Agente | Requisito(s) | Arquivos/áreas | Depende de | Done when | Gate |
|---|---|---|---|---|---|---|
| T1 | [Carlos] | <SLUG>-01 | `migrations/` | - | Schema aplicado e rollback definido. | `npm test -- migrations` |

## Matriz de testes

| Requisito | Tipo | Responsável | Comando/gate | Evidência esperada |
|---|---|---|---|---|
| <SLUG>-01 | unit/integration/e2e/manual | [Ricardo] | `<comando real ou a definir>` | Caminho feliz + 1 erro cobertos. |

## Riscos e mitigações

## Perguntas abertas

## Validação

Antes de `/kairos-forge:revisar`, rode:

`/kairos-forge:validar SPEC-NNN`

## Próximo passo
```

Se o projeto tiver `contextos/testes.md`, use os comandos de lá. Se não tiver, registre o gate como `<a definir>` e recomende preencher esse contexto.

### 7. Confirmação ao usuário

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
- **Todo item de implementação precisa de gate.** Pode ser teste automatizado, build, lint ou validação manual explícita.
- **Status "Concluído" exige célula Verificação iniciando com `verificado:`.** A regra existe para impedir o anti-padrão de marcar pronto sem rodar nada. Inspirada no checklist do Replit-Orchestrator (`briefing.md`): só vale verificado depois que o agente rodou o comando, abriu a URL ou executou o teste. Confiança em "escrevi o código, deve funcionar" não conta.
