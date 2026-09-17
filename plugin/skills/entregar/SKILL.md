---
name: entregar
description: Arco fechado de uma feature inteira: especificar, construir, validar, revisar e PR, com correção roteada ao agente responsável dentro de um orçamento. Etapa isolada usa a skill dela; deploy é o lancar.
---

# Entregar — o arco fechado da fábrica

Você conduz **o ciclo inteiro** — da descrição ao PR — fechando os loops de correção sozinho.
As outras skills são as etapas; esta é a linha de montagem que as liga.

## Regra de ouro

**O arco fecha sozinho dentro do orçamento; estourou, encerra honesto.** Falha em validação ou revisão volta
ao agente responsável, dentro de rodadas declaradas antes de começar. Orçamento acabou: entregue o melhor estado
atual com as pendências **declaradas explicitamente** e pare — nunca estoure em silêncio, nunca esconda falha parcial.

## O que esta skill NÃO automatiza

O arco tira o humano da **digitação do próximo comando**, não do **julgamento**. Você **sempre** para aqui:

| Gate | Por quê |
|---|---|
| **Aprovação da SPEC** antes de implementar | Implementar a coisa errada rápido é pior que devagar. Sem SIM, não constrói |
| **Pare e Pergunte** (ADR-0015) | Conteúdo que apareceria ao usuário final como verdade sem fonte — texto institucional, fórmula de negócio, dado pessoal, referência visual. Inventar é dívida silenciosa |
| **Deploy de produção** | É do `/kairos-forge:lancar`, que exige SIM explícito sem default |
| **Mudança irreversível** | Migration destrutiva, deleção de dados, janela de corte. Ação irreversível não roda em fluxo autônomo (ADR-0024) |
| **Merge do PR** | A decisão de integrar é do dono do repositório |

Escolha **reversível** não trava o arco: declare o default recomendado, registre a premissa e siga (ADR-0019).

## Quem decide o próximo passo (ADR-0029)

**Não é você.** O arco é uma máquina de estados em `scripts/ciclo.py`: você **executa** e **registra**; o script diz o que vem depois.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ciclo.py estado          # qual o passo agora
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ciclo.py registrar <res> # o que aconteceu
```

- **O orçamento é fato.** Esgotou, `registrar` devolve `escalado`.
- **Correção de revisão reabre a validação.** `corrigindo_revisao` só sai para `validando`.
- **Veredicto vem do artefato.** `registrar aprovado` sem relatório em `docs/specs/validacoes/` é recusado;
  com relatório dizendo bloqueado, também. Vale igual para `docs/specs/criticas/` e `docs/specs/revisoes/`.
- **Progresso real devolve a ficha (ADR-0032).** Achados abaixo da melhor marca do gate não cobram
  rodada; um **teto absoluto** segue valendo por cima.
- **A SPEC aprovada é selada.** Ao entrar em `construindo` o `ciclo.py` grava o digest do contrato da
  SPEC (Status e Verificação fora). Mudou requisito, critério ou plano depois disso, `estado` avisa e
  `registrar aprovado`/`limpo` é recusado até o **usuário** aceitar a versão nova (`ciclo.py reaprovar`)
  ou a SPEC voltar. SPEC reescrita para casar com o construído é o `verificado:` pelo avesso.
- `gh pr create` fica **bloqueado pelo guardrail** fora de `pronto_para_pr` (ADR-0022).
- Sem `ciclo.py` disponível, conduza pela prosa e **diga ao usuário** que o orçamento é contado por você, não imposto.

## Passo 0 — Abrir o ciclo com o orçamento

**Pré-condições** — git limpo (`git status`), branch própria (não `main`/`master`), gates conhecidos
(`contextos/testes.md` ou comandos evidentes) e, de preferência, telemetria em `.agents/execucoes/`
(sem ela o `/validar` não corrobora evidência — ADR-0021). Faltando qualquer uma, diga o que falta e
pare; o que fazer em cada caso: `references/maquina-de-estados.md`.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ciclo.py abrir SPEC-NNN \
  --orcamento-criticar 2 --orcamento-validar 2 --orcamento-revisar 2
# use --spec-aprovada quando a SPEC já existe e já foi aprovada
```

Anuncie o contrato da autonomia (modelo em `references/maquina-de-estados.md`): 2 rodadas sem progresso por
gate (`criticar` · `validar` · `revisar`), teto 6 cada; checkpoints em entendimento · abordagem · SPEC · antes
do PR; escalação por orçamento esgotado, teto atingido ou 2 falhas materialmente iguais; evidência mínima: P1 sem
bloqueio no `/validar` + zero 🔴 no `/revisar`; modo `mobilizar` (tarefas independentes e Agent Teams
disponível) ou `rodar` (o resto — e sempre em Codex, OpenCode, Cursor ou headless).

**Avisa-e-pausa (ADR-0013):** ao cruzar ~80% de qualquer limite, avise no checkpoint seguinte.
`ciclo.py estado` mostra as rodadas consumidas; `painel.py` mostra o arco inteiro:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/painel.py SPEC-NNN
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/painel.py SPEC-NNN --html quadro.html  # para mandar pra alguém
```

## O arco

**Planejamento** (ADR-0033) — três checkpoints, e uma crítica antes de você ver:

```
enquadrando ─▶ aguardando_entendimento ─▶ desenhando ─▶ aguardando_abordagem
                        │ ajustar                             │ ajustar
                        └──────▶ enquadrando                  └──▶ desenhando
                                                                    │ escolhida
                              ┌─────────────────────────────────────┘
                              ▼
                       especificando ─▶ criticando ──┐ com_achados (orçamento)
                                            ▲        ▼
                                            └── corrigindo_spec
                                            │ limpa
                                            ▼
                                   aguardando_aprovacao
```

**Construção:**

```
aguardando_aprovacao ─▶ construindo ─▶ validando ──┐
                             ▲                     │ bloqueado
                    corrigindo_validacao ◀─────────┘ (orçamento)
                                                    │ aprovado
                   ┌────────────────────────────────┘
                   ▼
             revisando ──┐ critico (orçamento)
                         ▼
                corrigindo_revisao ──▶ validando   ← reabre a validação
                   │ limpo
                   ▼
            pronto_para_pr ──▶ encerrado
```

Orçamento esgotado em qualquer dos **três** gates (`criticar`, `validar`, `revisar`) → `escalado`, terminal
até o usuário destravar. Os nomes são os estados reais do `ciclo.py`.

### 1. `enquadrando` → `aguardando_entendimento` — gate humano 1/3

`/kairos-forge:especificar` até o passo 4: Laura dimensiona, os arquitetos interrogam, você **espelha o
entendimento** — nada de SPEC ainda. Perguntas do Pare e Pergunte chegam ao usuário **agora**; nunca
responda por ele. `registrar entendimento_pronto`, espere: `confirmado` ou `ajustar`.

### 2. `desenhando` → `aguardando_abordagem` — gate humano 2/3

Passo 5: 2-3 abordagens com trade-offs e uma recomendada; decisão arquiteturalmente significativa vira RFC
(ADR-0018). `registrar abordagens_prontas`, espere: `escolhida` ou `ajustar`. **Nunca escolha pelo usuário.**

**Feature Pequena em sessão (ADR-0038):** os gates 1 e 2 vão numa mensagem só — entendimento
espelhado e a abordagem recomendada como premissa, sem 2-3 alternativas — e o usuário responde
uma vez. Os registros no `ciclo.py` continuam os mesmos, na ordem: `entendimento_pronto`,
`confirmado`, `abordagens_prontas`, `escolhida`. Em execução headless não há atalho: cada
gate espera de verdade, porque ali ninguém está lendo (ADR-0033).

### 3. `especificando` → `criticando` — a crítica adversarial

Escreva a SPEC (passo 6) e `registrar spec_pronta`. **Antes de mostrar ao usuário**, ao menos dois críticos que
não a escreveram atacam premissa, requisito, plano e testabilidade (passo 7); relatório em `docs/specs/criticas/`
com bloco `kairos-critica`. `registrar limpa` ou `registrar com_achados`; achado → `corrigindo_spec`, e
`registrar pronto` reabre a crítica.

### 4. `aguardando_aprovacao` — gate humano 3/3

Apresente objetivo, requisitos P1, não-objetivos, perguntas abertas, plano de tarefas **e o que a crítica
encontrou**. Espere **SIM / NÃO / AJUSTAR**: `registrar aprovada` ou `registrar recusada`. Sem SIM não há aresta.

### 5. `construindo`

`/kairos-forge:mobilizar SPEC-NNN` ou `/kairos-forge:rodar`, conforme o modo declarado. Cada tarefa mantém seu gate
e seu "Done when"; **Concluído** só com célula `verificado:` preenchida — o guardrail bloqueia o contrário (ADR-0022).
Ao final, `registrar pronto`.

### 6. `validando` / `corrigindo_validacao` — o primeiro loop

`/kairos-forge:validar SPEC-NNN`; registre o veredicto do relatório (`kairos-validacao`): `registrar aprovado`,
`registrar aprovado_com_ressalvas` ou `registrar bloqueado`. Em `corrigindo_validacao`, acione **só os
agentes dos achados** que o relatório nomeou, rode o gate do requisito afetado, atualize `verificado:` e
`registrar pronto`. Quantas rodadas cabem não é decisão sua. Detalhe: `references/loops-de-correcao.md`.

### 7. `revisando` / `corrigindo_revisao` — o segundo loop

`/kairos-forge:revisar`; pelo relatório (`kairos-revisao`): `registrar limpo` (zero 🔴) ou `registrar critico`.
🟠 e 🟡 viram follow-up no corpo do PR. Correção de segurança **nunca vira workaround** — sem caminho,
`ciclo.py escalar --motivo "..."`. Depois de corrigir, `registrar pronto` leva a **`validando`**, não a `revisando`.

### 7.5. Evidência proporcional à faixa (ADR-0031)

O `/revisar` classifica o diff em faixa de raio de explosão. **Faixa 1**: gates verdes. **Faixa 2**: gates
verdes **e** trajetória limpa (`telemetria.py`). **Faixa 3**: para e pergunta — `ciclo.py escalar --motivo
"faixa 3: <o que é irreversível>"`, mesma fronteira do ADR-0024. Diga a faixa no corpo do PR.

### 8. `pronto_para_pr` — abrir o PR

Só com P1 sem bloqueio e revisão sem 🔴. Título `<tipo>(<escopo>): <o que muda>` em PT-BR; corpo com
evidência, ressalvas, follow-ups e rodadas consumidas (`ciclo.py estado`). **Nunca** faça merge — `gh pr merge`
fica bloqueado durante ciclo aberto. Depois: `ciclo.py registrar pr_aberto`.

### 9. Encerrar e registrar

Salve `docs/specs/entregas/ENTREGA-<SPEC-NNN>-YYYY-MM-DD.md` com desfecho, linhagem de rodadas (do `historico`
em `ciclo.py estado --json`, **inclusive as que falharam**), evidência, ressalvas e o que ficou de fora —
modelo em `references/relatorio-de-entrega.md`. Ao final, `ciclo.py encerrar --motivo "PR #N aberto"`.

## Escalação

O `ciclo.py` escala **sozinho** quando o orçamento esgota. Escale manualmente (`ciclo.py escalar --motivo "..."`)
com duas falhas materialmente iguais na mesma etapa, achado que exige decisão fora da SPEC, gate da fronteira
de aprovação tocado ou Pare e Pergunte disparado na construção. Formatos: `references/escalacao.md`.

## Quando NÃO usar

Etapa isolada (chame a skill direto); deploy (`/kairos-forge:lancar`); exploração ou decisão travada
(`/kairos-forge:rodar`, modo debate); melhorar métrica (`/kairos-forge:otimizar`); mudança trivial — 1 arquivo, < 20 linhas.

## Regras

- **Ciclo aberto no `ciclo.py` antes da rodada 1**; quem conta rodada e decide transição é o script.
  **Nunca contorne o estado** — guardrail bloqueou? `ciclo.py estado` e faça o que falta.
- **Falha volta ao agente, não ao usuário**; **só os agentes dos achados** corrigem. **Toda rodada entra na linhagem.**
- **Nunca faça merge nem deploy. Nunca abra PR com P1 bloqueado ou 🔴 aberto. PT-BR em tudo.**

## Referências

| Arquivo | Leia quando |
|---|---|
| `references/maquina-de-estados.md` | Ao abrir o ciclo (Passo 0): pré-condições completas, anúncio do orçamento, avisa-e-pausa e por que o `ciclo.py` decide a transição |
| `references/loops-de-correcao.md` | Estiver em `criticando`, `corrigindo_spec`, `corrigindo_validacao`, `corrigindo_revisao` ou `revisando` — detalhe de cada loop e faixas de evidência |
| `references/relatorio-de-entrega.md` | Estiver em `pronto_para_pr` (título e corpo do PR) ou encerrando (modelo do relatório de entrega) |
| `references/escalacao.md` | O `ciclo.py` devolver `escalado`, precisar escalar manualmente ou encerrar por orçamento — gatilhos e formatos das mensagens |
