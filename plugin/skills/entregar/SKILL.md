---
name: entregar
description: Conduz o ciclo completo da fábrica de ponta a ponta com o arco fechado — especificar, aprovar, construir, validar, corrigir, revisar, corrigir e abrir PR — roteando cada falha de volta ao agente responsável dentro de um orçamento declarado de rodadas, sem o usuário digitar o próximo comando. Use quando quiser entregar uma feature inteira em vez de encadear skills à mão. Não use para uma etapa isolada (chame a skill dela direto) nem para deploy em produção — isso é lancar, que tem gate humano próprio.
---

# Entregar — o arco fechado da fábrica

Você está sendo invocado para conduzir **o ciclo inteiro** — da descrição ao PR
— fechando os loops de correção sozinho. As outras skills são as etapas; esta é
a linha de montagem que as liga.

## Regra de ouro

**O arco fecha sozinho dentro do orçamento; estourou, encerra honesto.** Falha
em validação ou revisão não devolve o problema ao usuário — volta ao agente
responsável, dentro de um número de rodadas declarado antes de começar. Quando o
orçamento acaba, você entrega o melhor estado atual com as pendências
**declaradas explicitamente** e para. Nunca estoure o orçamento em silêncio "pra
terminar", e nunca esconda falha parcial atrás de um resumo fluente.

## O que esta skill NÃO automatiza

O arco fechado tira o humano da **digitação do próximo comando**, não do
**julgamento**. Estes gates continuam existindo e você **sempre** para neles:

| Gate | Por quê |
|---|---|
| **Aprovação da SPEC** antes de implementar | Implementar a coisa errada rápido é pior que devagar. Sem SIM, não constrói |
| **Pare e Pergunte** (ADR-0015) | Conteúdo que apareceria ao usuário final como verdade sem fonte — texto institucional, fórmula de negócio, dado pessoal, referência visual. Inventar é dívida silenciosa |
| **Deploy de produção** | É do `/kairos-forge:lancar`, que exige SIM explícito sem default |
| **Mudança irreversível** | Migration destrutiva, deleção de dados, janela de corte. Ação irreversível não roda em fluxo autônomo (ADR-0024) |
| **Merge do PR** | A decisão de integrar é do dono do repositório |

Escolha **reversível** não trava o arco: declare o default recomendado, registre
a premissa e siga (ADR-0019).

## Pré-condições

Antes da rodada 1, verifique. Faltando qualquer uma, diga o que falta e pare:

| Condição | Verificação | Se faltar |
|---|---|---|
| Git limpo | `git status` sem mudança não commitada | Commit ou stash — o arco precisa de revert barato |
| Branch própria | Não estar em `main`/`master` | Crie a branch antes |
| Gates conhecidos | `contextos/testes.md` ou comandos evidentes do projeto | Registre como `<a definir>` e avise que a validação fica mais fraca |
| Telemetria (recomendado) | `.agents/execucoes/` existe | Sem ela o `/validar` não corrobora evidência (ADR-0021) — siga, mas declare |

## Quem decide o próximo passo (ADR-0029)

**Não é você.** O arco é uma máquina de estados em `scripts/ciclo.py`, e a
transição é decidida por código. Você **executa** o passo e **registra** o que
aconteceu; o script diz o que vem depois.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ciclo.py estado          # qual o passo agora
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ciclo.py registrar <res> # o que aconteceu
```

Três coisas deixam de depender da sua disciplina:

- **O orçamento é fato.** Esgotou, `registrar` devolve `escalado` — não existe
  "mais uma rodada, dessa vez vai".
- **Correção de revisão reabre a validação.** Você não escolhe voltar pra
  revisão: o script só tem essa aresta.
- **Veredicto vem do artefato.** `registrar aprovado` sem relatório em
  `docs/specs/validacoes/` é recusado; com relatório dizendo bloqueado, também.
  Vale igual para a revisão (`docs/specs/revisoes/`) desde a v0.24.
- **Progresso real devolve a ficha (ADR-0032).** O `ciclo.py` lê a contagem de
  achados do bloco de contrato do relatório e compara com a melhor marca do
  gate. Baixou de 5 para 2, a rodada não é cobrada; continuou em 5, é. Convergir
  não é patinar, e o orçamento plano tratava os dois igual. Um **teto absoluto**
  de rodadas segue valendo por cima — progresso não compra rodada infinita.

E o `gh pr create` fica **bloqueado pelo guardrail** enquanto o estado não for
`pronto_para_pr` (ADR-0022). Não é sugestão.

Se o `ciclo.py` não estiver disponível (CLI sem os scripts do plugin), conduza o
arco pela prosa abaixo e **diga ao usuário** que o orçamento está sendo contado
por você, não imposto.

## Passo 0 — Abrir o ciclo com o orçamento

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ciclo.py abrir SPEC-NNN \
  --orcamento-validar 2 --orcamento-revisar 2
# use --spec-aprovada quando a SPEC já existe e já foi aprovada
```

Anuncie ao usuário o que foi aberto — é o contrato da autonomia deste ciclo:

```
🔁 Entrega — <feature/SPEC> — orçamento declarado

Rodadas sem progresso por gate: 2 (validar) · 2 (revisar) — teto absoluto 6 cada
Checkpoint com você:           aprovação da SPEC · antes do PR
Escalação:                     orçamento sem progresso esgotado, teto atingido,
                               ou 2 falhas materialmente iguais
Evidência mínima pra encerrar: P1 sem bloqueio no /validar + zero 🔴 no /revisar
Modo de construção:            mobilizar (paralelo) | rodar (sequencial)
```

**Avisa-e-pausa (ADR-0013):** ao cruzar ~80% de qualquer limite, avise no
checkpoint seguinte. O `ciclo.py estado` mostra as rodadas consumidas a qualquer
momento.

Escolha do modo de construção: `mobilizar` se as tarefas forem independentes e
as ferramentas de Agent Teams existirem; `rodar` no resto (e sempre em Codex,
OpenCode, Cursor ou execução headless).

## O arco

```
especificando ─▶ aguardando_aprovacao ─▶ construindo ─▶ validando ──┐
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

Orçamento esgotado em qualquer gate → `escalado`, que é terminal até o usuário
destravar. Os nomes acima são os estados reais do `ciclo.py`.

### 1. `especificando`

Rode `/kairos-forge:especificar`. As perguntas do Pare e Pergunte chegam ao
usuário **agora** — nunca responda por ele, nunca preencha com achismo.

Ao final: `ciclo.py registrar spec_pronta`.

### 2. `aguardando_aprovacao` — gate humano

Apresente: objetivo, requisitos P1, não-objetivos, perguntas abertas e o plano
de tarefas. Espere **SIM / NÃO / AJUSTAR**.

`ciclo.py registrar aprovada` ou `registrar recusada`. Sem SIM, o arco não
avança — e o script não tem aresta que permita avançar.

### 3. `construindo`

`/kairos-forge:mobilizar SPEC-NNN` ou `/kairos-forge:rodar`, conforme o modo
declarado. Cada tarefa mantém seu gate e seu "Done when". A SPEC só recebe
status **Concluído** com célula `verificado:` preenchida — o guardrail
determinístico bloqueia o contrário (ADR-0022).

### 4. `validando` / `corrigindo_validacao` — o primeiro loop

Rode `/kairos-forge:validar SPEC-NNN` e registre o veredicto do relatório:
`registrar aprovado`, `registrar aprovado_com_ressalvas` ou `registrar bloqueado`.

Em `corrigindo_validacao`, **não devolva o problema ao usuário**:

1. Para cada achado bloqueante, identifique o agente que o relatório indicou (o
   `/validar` já nomeia: Ricardo em cobertura, Helena em segurança, Carlos em
   dados, e assim por diante).
2. Acione **só os agentes dos achados** — corrigir é cirurgia, não mutirão.
3. Rode o gate do requisito afetado e atualize a célula `verificado:`.
4. `registrar pronto` — o script devolve `validando`.

Quantas rodadas cabem não é decisão sua: o `ciclo.py` conta e escala sozinho.

### 5. `revisando` / `corrigindo_revisao` — o segundo loop

Rode `/kairos-forge:revisar`. Depois: `registrar limpo` (zero 🔴) ou
`registrar critico`. Achados 🟠 e 🟡 viram follow-up no corpo do PR.

Correção de segurança **nunca vira workaround** — se o único caminho for
contornar em vez de corrigir, use `ciclo.py escalar --motivo "..."`.

Depois de corrigir um 🔴, `registrar pronto` leva a **`validando`**, não a
`revisando`. Correção que quebra requisito já validado é o modo de falha
silencioso deste arco — e agora ele está fechado por construção, não por
lembrança.

### 5.5. Evidência proporcional à faixa (ADR-0031)

O `/revisar` classificou o diff em faixa de raio de explosão. A faixa decide o que basta:

- **Faixa 1** — gates verdes fecham.
- **Faixa 2** — gates verdes **e** trajetória limpa: sem alerta de patinação, sem recusa
  de guardrail registrada, `verificado:` corroborado (`telemetria.py`).
- **Faixa 3** — **para e pergunta.** Escale com `ciclo.py escalar --motivo "faixa 3:
  <o que é irreversível>"`. Não existe pontuação que abra essa faixa; é a mesma fronteira
  do ADR-0024.

Diga a faixa no corpo do PR. Quem revisa precisa saber onde olhar antes de abrir o diff.

### 6. `pronto_para_pr` — abrir o PR

Com validação sem bloqueio em P1 e revisão sem 🔴:

- Título: `<tipo>(<escopo>): <o que muda>` em PT-BR.
- Corpo: objetivo da SPEC, requisitos P1 com evidência, gates rodados, ressalvas
  aceitas e follow-ups abertos, rodadas de correção consumidas (`ciclo.py estado`).
- **Nunca** faça merge — e o guardrail bloqueia `gh pr merge` durante um ciclo
  aberto. A integração é decisão do dono do repositório.
- Depois: `ciclo.py registrar pr_aberto`.

### 7. Encerrar e registrar

Salve `docs/specs/entregas/ENTREGA-<SPEC-NNN>-YYYY-MM-DD.md`:

```markdown
# Entrega — SPEC-NNN — YYYY-MM-DD

**Desfecho:** PR aberto / encerrado por orçamento / escalado
**Modo:** mobilizar | rodar
**Orçamento:** validar N/2 · revisar N/2

## Linhagem de rodadas

| # | Etapa | Achado | Agente | Ação | Bloqueios | Resultado |
|---|---|---|---|---|---|---|
| 1 | validar | 3 P1 sem teste | Ricardo | testes de erro adicionados | 3 → 1 | ficha devolvida |
| 2 | validar | EXP-02 sem teste | Ricardo | teste de erro adicionado | 1 → 0 | aprovado |

## Evidência final
## Ressalvas e follow-ups aceitos
## O que ficou de fora (se encerrou por orçamento)
## Próximo passo
```

A linhagem não é digitada de memória: `ciclo.py estado --json` traz o
`historico` completo com cada transição, o resultado registrado e o horário.
A tabela registra **também as rodadas que falharam** — rodada revertida ou
escalada é evidência, não vergonha apagada, e é o que impede a próxima entrega de
repetir a mesma tentativa.

Ao final, `ciclo.py encerrar --motivo "PR #N aberto"`.

## Escalação

O `ciclo.py` escala **sozinho** quando o orçamento de um gate esgota. Você escala
manualmente (`ciclo.py escalar --motivo "..."`) quando:

- **Duas falhas materialmente iguais** na mesma etapa. Insistir na terceira é
  gastar orçamento em ruído. Se o gate falha pelo mesmo motivo depois de uma
  correção, o problema não é a correção — é o entendimento.
- **Orçamento esgotado** em qualquer loop.
- **Achado exige decisão fora da SPEC** — trade-off arquitetural, mudança de
  escopo, requisito que se revelou impossível.
- **Qualquer gate da fronteira de aprovação** foi tocado.
- **Pare e Pergunte disparou** durante a construção.

Formato da escalação — específica, com o que você já tentou (o `historico` do
`ciclo.py estado --json` tem os dados):

```
⏸️ Entrega pausada na etapa <N> (<etapa>).

Motivo: <duas falhas iguais | orçamento | decisão fora da SPEC>
Achado: <o achado exato, com arquivo:linha>
Já tentei: <as rodadas consumidas e o que cada uma mudou>
Preciso de: <a decisão específica que destrava>

Estado atual: <o que está pronto e verificado, o que não está>
```

## Encerramento honesto por orçamento

Quando o orçamento acaba sem fechar o arco, entregue o estado real:

```
🔁 Entrega encerrada por orçamento — SPEC-NNN

Concluídos e verificados: <lista com evidência>
Não concluídos: <lista com o que falta em cada um>
Rodadas: validar 2/2 · revisar 1/2
Último bloqueio: <achado exato e agente sugerido>

PR NÃO foi aberto porque <motivo>.
Próximo passo: <ampliar orçamento | decidir X | fatiar a SPEC>
```

Nunca abra PR com P1 bloqueado. "Quase pronto" não é pronto, e PR aberto com
gate vermelho transfere para o revisor humano exatamente o trabalho que o arco
existe para absorver.

## Quando NÃO usar

- **Uma etapa isolada** — chame a skill dela direto (`/validar`, `/revisar`).
- **Deploy em produção** — é o `/kairos-forge:lancar`, com gate próprio.
- **Exploração, brainstorm, decisão travada** — `/kairos-forge:rodar` (modo
  debate se for decisão).
- **Melhorar uma métrica existente** — `/kairos-forge:otimizar` (a catraca já é
  um arco fechado, com manter-ou-reverter).
- **Mudança trivial** — 1 arquivo, menos de 20 linhas. O arco custa mais que a
  mudança.

## Regras

- **O ciclo é aberto no `ciclo.py` antes da rodada 1**, com o orçamento. Quem conta
  rodada e decide transição é o script — você executa e registra.
- **Nunca contorne o estado.** Se o guardrail bloqueou o `gh pr create`, o problema
  não é o guardrail: rode `ciclo.py estado` e faça o que falta.
- **Falha volta ao agente, não ao usuário** — dentro do orçamento. É isso que
  separa esta skill de encadear comandos à mão.
- **Só os agentes dos achados** entram na correção.
- **Toda rodada entra na linhagem**, inclusive as que falharam.
- **Nunca faça merge nem deploy.** O arco termina no PR.
- **Nunca abra PR com P1 bloqueado ou 🔴 aberto.**
- **PT-BR em tudo** — commits, corpo do PR, relatório e conversa.
