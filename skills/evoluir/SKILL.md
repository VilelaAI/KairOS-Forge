---
name: evoluir
description: Conduz entrevista semanal de evolução da fábrica. Use depois do /kairos-forge:auditar, tipicamente sexta-feira. Faz 5 perguntas sobre a semana que passou e identifica UMA capacidade nova para construir na próxima (skill, agente, hook ou contexto). Cada execução = um item entregue na semana seguinte. Não constrói nada agora — produz especificação do que será construído.
---

# Evoluir — ciclo semanal de aprendizado

Você está sendo invocado para conduzir o ritual semanal que mantém a fábrica melhorando.

## Filosofia

A fábrica não fica boa em uma semana. Fica boa porque toda semana ela aprende uma coisa nova, baseada no que doeu na semana anterior. Esta skill captura essa dor e transforma em capacidade nova.

**Regra de ouro: uma execução = uma capacidade entregue.** Não três. Não cinco. Uma.

## Pré-requisito

Idealmente o usuário acabou de rodar `/kairos-forge:auditar`. Se não rodou, sugira:

> "Recomendo rodar `/kairos-forge:auditar` antes deste ciclo, para olharmos a foto atual da fábrica. Quer que eu rode primeiro?"

Se o usuário disser para seguir sem auditar, prossiga.

## A entrevista — 5 perguntas

Faça **uma pergunta por vez**. Sem enfileirar.

### 1. Repetição

> "Que prompt ou pedido você fez para o Claude Code 3 ou mais vezes esta semana? Algo que você se pegou redigitando."

Se houver: candidato natural a virar skill nova.

### 2. Atrito

> "Que tarefa esta semana foi entediante, repetitiva ou copy-paste pesado? Qual foi a parte que doeu mais?"

Se houver: candidato a virar hook ou comando.

### 3. Teste do estagiário

> "Que coisa você fez esta semana que um estagiário inteligente conseguiria fazer, mas explicar levaria mais tempo do que fazer? Você fez sozinho por preguiça de explicar, certo?"

Se houver: candidato a virar agente especializado ou skill.

### 4. Restrição

> "Se 5 vezes mais demanda chegasse na próxima segunda — 5x mais features pedidas, 5x mais bugs, 5x mais clientes —, o que quebra primeiro? Onde está o gargalo?"

Se houver: candidato a virar guardrail (lint, hook, CI rule).

### 5. Alavanca

> "Qual UMA coisa, se rodasse sozinha em background, te faria ganhar mais tempo? Não pense em 'deveria existir'. Pense em 'eu pessoalmente economizaria horas se isso rodasse automático'."

Se houver: candidato a virar background task, scheduled job ou hook proativo.

## Após as 5 respostas

1. **Listar os candidatos** que emergiram (de zero a cinco).

2. **Recomendar UM**, com critério explícito:

   - Maior alavancagem (impacto x frequência)
   - Menor esforço de implementação
   - Empate? O que está há mais tempo sendo dor

3. **Especificar o item escolhido** com este formato, salvando em `decisoes/evolucoes/EVOL-YYYY-MM-DD.md`:

```markdown
# Evolução semanal — YYYY-MM-DD

## Item escolhido

**Tipo:** [skill | agente | hook | comando | contexto | guardrail]
**Nome:** <nome-no-infinitivo-ou-substantivo>
**Origem:** <qual das 5 perguntas gerou>

## Problema que resolve

(2-3 frases descrevendo a dor real, vinda das respostas da entrevista)

## Comportamento esperado

(Como vai se manifestar quando estiver pronto. "Quando o usuário X, o Y acontece automaticamente.")

## Plano de implementação

- [ ] Etapa 1
- [ ] Etapa 2
- [ ] Etapa 3

## Critério de pronto

Como saberemos que está funcionando. Concreto, verificável.

## Outros candidatos descartados nesta rodada

- <candidato 1> — descartado porque <motivo>
- <candidato 2> — descartado porque <motivo>
(Servem para o próximo ciclo)
```

4. **Confirmar com o usuário:**

```
✅ Evolução da semana definida: <nome do item>

Próximos passos:
1. Rode /kairos-forge:especificar para o arquiteto produzir a SPEC detalhada
2. Implemente até a próxima sexta
3. No próximo ciclo de evolução, este item já estará na fábrica

Outros candidatos ficaram registrados para os próximos ciclos.
```

## Regras

- **Uma pergunta por vez.** Não enfileire as 5.
- **Não construa nada agora.** Esta skill produz a SPEC do que será construído. A construção é trabalho do arquiteto + codificador na semana seguinte.
- **Recomende UM item.** Mesmo que apareçam 5 candidatos. Disciplina é o que faz a fábrica evoluir consistentemente.
- **Não puxe respostas.** Se o usuário disser "nenhum prompt repetido esta semana", aceite. Próxima pergunta.
- **Salve o registro mesmo se nada novo emergir.** Padrão "esta semana sem novidade" é informação útil — talvez a fábrica esteja madura, talvez você não tenha trabalhado o suficiente, ambas hipóteses interessantes.
