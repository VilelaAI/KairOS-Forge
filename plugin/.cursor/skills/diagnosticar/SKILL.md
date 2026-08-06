---
name: diagnosticar
description: Produz o diagnóstico técnico de um sistema existente — mede o que dá para medir, pontua seis dimensões com rubrica publicada, prioriza achados por impacto × esforço e entrega um roadmap por horizonte em docs/diagnosticos/. Dono é Rafael (Staff), com os especialistas medindo cada dimensão. Use como porta de entrada de projeto legado ou de terceiro, antes de decidir o que atacar. Não use para pontuar a fábrica (isso é auditar), para mapear só a estrutura sem julgamento de saúde (isso é mapear-arquitetura) nem para revisar um diff (isso é revisar).
---

# Diagnosticar — a saúde do sistema, com número e ordem

Você está sendo invocado para responder três perguntas sobre um sistema que já
existe: **o que dói, quanto dói, e em que ordem atacar.**

Quem conduz é **Rafael (Staff)** — o artefato é um documento de decisão. Os
especialistas medem cada um na sua dimensão; Rafael consolida e prioriza.

## Regra de ouro

**Todo número carrega sua origem.** Cada afirmação do relatório é rotulada
`medido`, `inferido` ou `não verificável`. Diagnóstico onde tudo é inferência é
opinião — legítima, mas precisa dizer que é. Número inventado num documento que
vai para terceiro não é otimismo: é dívida que aparece na primeira vez que o
outro lado mede.

## Onde esta skill se encaixa

Duas skills da fábrica exigem um insumo que ninguém produzia:

- `/kairos-forge:otimizar` abre com *"sem métrica honesta, pare"* — exige a
  métrica **já escolhida**.
- `/kairos-forge:migrar` (Ivan) não decide **se** migra — exige a decisão
  **já tomada**.

O diagnóstico é esse insumo. Ele termina encaminhando cada achado:

```
diagnosticar ──┬──▶ otimizar     (achado com métrica mensurável e alvo)
               ├──▶ migrar       (achado estrutural que exige estrangulamento)
               ├──▶ especificar  (achado que é feature/mudança de comportamento)
               └──▶ analisar-ameacas  (superfície sensível sem threat model)
```

## Escada de evidência — declare o nível antes de medir

O que você pode afirmar depende do acesso que você tem. Estabeleça isto **no
começo**, com o usuário, e registre no relatório:

| Nível | Acesso | O que vira `medido` |
|---|---|---|
| **1** | Só o repositório | Churn e hotspots, concentração de autoria, razão teste/produção, inventário de dependências, densidade de dívida marcada, distribuição de tamanho |
| **2** | + ambiente executável (local/staging) | Latência real por endpoint, P95, tempo de query, plano de execução, N+1 observado, tempo de build e de suíte |
| **3** | + telemetria de produção | Comportamento sob carga real, taxa de erro, saturação, custo por requisição |

Diagnóstico de nível 1 é legítimo e útil — **desde que diga que é nível 1.**
Prometer conclusão de nível 3 com acesso de nível 1 é o erro que destrói a
credibilidade do documento inteiro.

## Fluxo

### 1. Delimitar e combinar acesso

Antes de qualquer coisa, com o usuário:

- **Qual sistema** e qual recorte (repo inteiro? um serviço? um módulo?).
- **Para quem é o documento** — decisão interna do time ou entrega a cliente.
  Muda o registro, não o rigor.
- **Que acesso existe** — repositório, ambiente executável, telemetria. Isso fixa
  o nível da escada.
- **Qual a dor declarada**, se houver ("está lento", "quebra toda semana"). Ela
  entra como hipótese a testar, nunca como conclusão.

Se o acesso prometido não se materializar (ambiente não sobe, credencial não
vem), **rebaixe o nível e diga isso** — não substitua medição por suposição.

### 2. Coletar a evidência de nível 1

Sempre, mesmo quando houver acesso maior — é barata e é a espinha do documento:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/diagnostico.py coletar <caminho> --dias 90
```

Ela entrega, já medido: atividade e frequência de commit, hotspots de código,
hotspots com **autor único** (concentração de conhecimento), razão
teste/produção, inventário de dependências com contagem sem versão fixa,
densidade de marcadores de dívida, distribuição de tamanho de arquivo e **revisões de
SPEC** — incluindo quantas aconteceram no mesmo commit que código de produção.

Essa última merece leitura cuidadosa: SPEC alterada junto com o código é, às vezes, a
especificação sendo reescrita para casar com o que foi construído — o `verificado:` pelo
avesso. Nem sempre é isso (SPEC viva também é revisada por bom motivo), e por isso o
script reporta e não julga.

O script **não** pontua nem infere causa de propósito. Ler "arquivo X mudou 25
vezes e tem autor único" é dado; dizer "X é o gargalo de manutenção" é
julgamento — e o julgamento é seu, rotulado como `inferido`.

### 3. Medir por dimensão — cada especialista na sua

| Dimensão | Quem | O que busca | Como vira `medido` |
|---|---|---|---|
| **Performance** | Vinícius (+ Carlos em query) | Latência, N+1, ausência de paginação, cache | Nível 2+: tempo real por endpoint, `EXPLAIN ANALYZE` |
| **Confiabilidade** | Sérgio (+ Ricardo) | Cobertura de caminho de erro, retry, timeout, idempotência | Suíte executada, taxa de falha, teste de regressão |
| **Segurança** | Helena | Auth, input externo, segredo em repo, dependência vulnerável | `check-agent-security.py`, varredura de segredo, versão de dep |
| **Manutenibilidade** | Rafael + Diego | Acoplamento, duplicação de domínio, tamanho, bus factor, **scope creep** | Nível 1 (churn, autoria, tamanho, revisão de SPEC) + leitura de estrutura |
| **Observabilidade** | Renata | Log estruturado, correlação de request, métrica de negócio, alerta | Existência e formato verificados no código; nível 3 confirma uso |
| **Custo** | Elisa | Recurso ocioso, consulta cara, egress, tier errado | Nível 3, ou fatura quando o usuário fornecer |

Especialista sem acesso para medir a própria dimensão **declara isso** e pontua
com confiança reduzida — não inventa.

### 4. Pontuar — com a rubrica dentro do documento

Cada dimensão recebe **0–100**. A rubrica que você usou vai **publicada no
relatório**, com o critério que levou a cada faixa. Score cuja conta o leitor não
consegue refazer é teatro.

| Faixa | Leitura |
|---|---|
| 85–100 | Saudável — sem ação prioritária nesta dimensão |
| 70–84 | Moderado — dívida conhecida e contornável |
| 50–69 | Frágil — falha provável sob crescimento |
| < 50 | Crítico — falha provável no estado atual |

O **Score Geral** é a média simples das dimensões e **nunca aparece sozinho**: a
tabela por dimensão vai ao lado, porque média esconde variância — 6 dimensões em
80 e uma em 20 dá 70, e esse 20 é a história toda.

Junto do score, a **confiança**: `alta` (maioria medido em nível 2+), `média`
(nível 1 + inferência estruturada), `baixa` (predominantemente inferido).

### 5. Priorizar por impacto × esforço

Cada achado ganha severidade (🔴 crítico / 🟠 alto / 🟡 médio / 🔵 baixo) e
esforço (P/M/G). A ordem do roadmap sai do cruzamento, com **Hugo** (ICE) quando
houver disputa e **Rui** quando a decisão for de custo-benefício.

Regra de ordenação: **alto impacto e baixo esforço primeiro**, sempre. Um achado
crítico e caro perde para dois achados altos e baratos quando o objetivo é
destravar o sistema — e o documento diz por quê.

### 6. Estimar ganho — a parte que exige mais disciplina

Ganho projetado é a informação mais valiosa e a mais fácil de corromper. Três
regras, inegociáveis:

1. **Faixa, não número único.** "50–200ms" e não "48ms".
2. **Base declarada.** De onde vem a faixa: medição comparável, plano de
   execução, benchmark do próprio projeto, ou literatura da tecnologia.
3. **Sem base, sem número.** Escreva "ganho não estimável com o acesso atual —
   exige nível 2" e siga. Isso é mais forte que um percentual bonito, porque é
   verificável.

Exemplo do que passa: *"índice em `pedidos.cliente_id` deve levar a listagem de
~1,9s para a faixa de 50–200ms — base: `EXPLAIN ANALYZE` atual mostra seq scan em
tabela de 2,1M linhas; medição de nível 2 confirma ou refuta."*

Exemplo do que **não** passa: *"-96% no tempo de resposta"* sem nada atrás.

Isto é o Pare e Pergunte (ADR-0015) aplicado a número, com um agravante: aqui o
conteúdo vai para alguém que pode conferir.

### 7. Escrever o relatório

`docs/diagnosticos/DIAGNOSTICO-<sistema>-YYYY-MM-DD.md`:

```markdown
# Diagnóstico técnico — <sistema> — YYYY-MM-DD

**Score geral:** NN/100 (<faixa>) · **Confiança:** alta | média | baixa
**Nível de evidência:** 1 | 2 | 3 — <o que isso permite e o que não permite afirmar>
**Escopo analisado:** <recorte> · **Janela:** <N dias>

## Resumo executivo

(3–5 frases em linguagem de negócio: o que está em risco, o que está saudável,
qual a primeira coisa a fazer. Sem jargão — este parágrafo é o que o decisor lê.)

## Pontuação por dimensão

| Dimensão | Score | Confiança | Principal achado |
|---|---|---|---|
| Performance | NN | medido/inferido | ... |

## Rubrica utilizada

(Como cada faixa foi atribuída. O leitor precisa conseguir refazer a conta.)

## Achados

| # | Achado | Dimensão | Severidade | Esforço | Evidência | Origem |
|---|---|---|---|---|---|---|
| 1 | ... | Performance | 🔴 | M | `<comando/saída ou arquivo:linha>` | medido |

## Ganho estimado

| Achado | Situação atual | Faixa esperada | Base da estimativa |
|---|---|---|---|

## Roadmap sugerido

| Horizonte | Achados | Por que agora |
|---|---|---|
| Curto (1–2 semanas) | #1, #4 | Alto impacto, baixo esforço |
| Médio (3–6 semanas) | #2, #5 | ... |
| Longo (6–12 semanas) | #3 | Exige decisão arquitetural |

## O que não foi possível verificar

(Lista explícita: o que exigiria nível 2 ou 3, e o que muda na conclusão se for
medido. Esta seção é obrigatória e nunca fica vazia num diagnóstico de nível 1.)

## Encaminhamento

| Achado | Próximo passo na fábrica |
|---|---|
| #1 | `/kairos-forge:otimizar` — métrica: `<comando>`, alvo: `<faixa>` |
| #3 | `/kairos-forge:migrar` — fatia inicial sugerida: `<módulo>` |
| #5 | `/kairos-forge:especificar` — vira feature, não otimização |
```

### 8. Versão para o cliente (se for entrega externa)

O markdown acima é o documento técnico completo. Para entrega a terceiro:

- **Helena [Apresentação]** (apoio-narrativa) adapta o registro — executivo
  primeiro, técnico em anexo.
- **Sofia** (apoio-valor) entra se virar proposta comercial.
- A diagramação **não é desta skill**: o conteúdo verificável sai aqui; layout e
  identidade visual são de uma skill de documento.

O conteúdo não muda entre as versões. **Se um número não pode ser dito ao
cliente, ele também não deveria estar no documento interno.**

## Quando NÃO usar

- **Pontuar a fábrica** (setup, skills, guardrails) → `/kairos-forge:auditar`.
- **Só mapear estrutura**, sem julgamento de saúde → `/kairos-forge:mapear-arquitetura`
  (e ele é um ótimo insumo para a dimensão Manutenibilidade daqui).
- **Revisar um diff** antes do PR → `/kairos-forge:revisar`.
- **Já sei o que atacar e tenho a métrica** → vá direto ao `/kairos-forge:otimizar`.
- **Threat model de uma feature** → `/kairos-forge:analisar-ameacas`.

## Regras

- **Toda afirmação rotulada** `medido` / `inferido` / `não verificável`.
- **Nível de evidência declarado** no topo, e rebaixado sem cerimônia quando o
  acesso não se confirma.
- **Rubrica publicada** junto do score.
- **Score geral nunca sozinho** — a tabela por dimensão anda com ele.
- **Ganho só com faixa e base.** Sem base, escreva que não é estimável.
- **A seção "o que não foi possível verificar" é obrigatória.**
- **Não implemente correção nesta skill.** Diagnóstico produz decisão; a execução
  é `/otimizar`, `/migrar` ou `/especificar`.
- **PT-BR em tudo.**
