---
name: evoluir
description: Entrevista semanal depois do auditar: escolhe UMA capacidade nova da fábrica para a próxima semana. Não constrói, especifica. Melhorar métrica específica é o otimizar.
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

## Antes da entrevista: evidência da semana

Colete evidência **antes** de perguntar. A regra vale para as duas fontes abaixo:
evidência provoca a pergunta, nunca responde por ela. A escolha continua sendo do
usuário — e é ele, não você, quem decide o que a fábrica vira (ADR-0022).

### Trajetória do próprio harness (ADR-0021)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/telemetria.py resumo --dias 7
```

A fábrica registra a própria execução desde a v0.17, e até aqui esse registro só
alimentava o `/kairos-forge:auditar` — quem **relata**. O `/evoluir`, que é quem
**melhora**, perguntava de memória. Instrumento sem consumidor do lado da melhoria é
metade do laço.

Leia os números como perguntas, não como diagnóstico:

| O que o resumo mostra | O que perguntar |
|---|---|
| Autonomia baixa | Onde você teve de intervir? É sempre no mesmo ponto? |
| Gate verde de primeira baixo | O gate está pegando erro real ou está mal calibrado? |
| Muitas rodadas de correção | Qual agente patina? Falta contexto ou falta critério? |
| Recusas de guardrail por classe | Regra apertada demais, ou hábito que precisa mudar? |

Sem hooks no CLI, `.agents/execucoes/` fica vazio e o resumo vem zerado. Isso é
comportamento honesto, não bug: **diga que não há trajetória** e siga para a entrevista
sem inventar tendência a partir de nada.

### Memória de sessão (se houver)

Se as tools MCP `memory_*` estiverem disponíveis (ai-memory, ADR-0010): `memory_recent` e `memory_query` sobre a semana (prompts repetidos, tarefas que apareceram várias vezes, sessões longas no mesmo problema). Use como **provocação concreta** nas perguntas — "vi que você pediu geração de fixture 4 vezes esta semana; isso é a repetição?" — em vez de depender só da lembrança do usuário. A resposta continua sendo dele: evidência sugere, não decide.

## Fechar a evolução anterior (ADR-0043)

Antes de escolher a próxima, dê veredicto à última. Abra o `decisoes/evolucoes/EVOL-*.md`
mais recente, leia o critério de pronto e a linha de base que ele gravou, e compare com a
evidência que você acabou de coletar. Escreva **um** veredicto, com o contraste que o
sustenta:

| Veredicto | Quando |
|---|---|
| `ajudou` | O que o critério de pronto nomeia mudou na direção prevista, comparado com a linha de base |
| `piorou` | O que a evolução devia melhorar piorou, ou ela trouxe custo novo (atrito, recusa, rodada a mais) |
| `sem efeito observado` | Entrou na fábrica e nada do que ela nomeava mudou |
| `confundido` | Mais de uma coisa mudou na semana (outra capacidade, modelo, tipo de trabalho), ou uma ocorrência só sustenta a diferença. **É o default** quando não dá para isolar |

- **Adoção não é evidência.** "Está instalada e o usuário gostou" não é `ajudou`: a
  pergunta é o que mudou em relação à linha de base, não se a coisa existe.
- **Prefira `confundido` a uma atribuição inventada.** Lição errada envenena todo ciclo
  seguinte; `confundido` honesto é registro útil.
- **`piorou` volta à mesa.** A candidata natural da semana passa a ser desfazer ou
  corrigir a evolução anterior, não construir por cima dela.
- **Sem registro anterior, ou registro sem linha de base** (anteriores ao ADR-0043):
  diga isso e siga. O veredicto começa a valer a partir do primeiro EVOL com linha de base.

**Lição só com contraste.** Com `ajudou` ou `piorou` e contraste concreto, a lição que
transfere pode subir para `.agents/memory/<slug>.md`, com quatro campos:

- **Quando reconhecer:** a forma da situação, não o fato deste projeto.
- **Como aplicar:** a operação na fábrica, nomeando o componente (skill, hook, persona,
  contexto, guardrail).
- **Evidência:** linha de base → agora, e onde se viu.
- **Confiança:** alta, média ou baixa, e por quê.

Genérica demais não muda nada ("documentar melhor"); específica demais nunca dispara de
novo ("o teste de pagamento demora 40 s"). O alvo fica entre as duas: "quando o mesmo gate
fica vermelho por fixture faltando em sessões seguidas, um script que gera a fixture corta
mais rodadas de correção do que uma instrução na skill". Sem contraste, o registro diz
`sem lição` — o veredicto continua valendo.

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
   - **Padrão contra modo de falha compreendido** (ADR-0012): só recomende capacidade nova se o modo de falha atual é claro e a capacidade o endereça diretamente — o padrão mais barato que resolve é o certo. Se o modo de falha ainda é incerto, a evolução da semana é **medir** (criar a métrica, o log ou o gate que vai revelá-lo), não construir. E se a dor é "temos métrica mas ela não melhora", a resposta pode não ser capacidade nova: rode `/kairos-forge:otimizar` sobre ela.

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

Como saberemos que está funcionando. Concreto, verificável — e o contraste que vai
provar: o que muda em relação à linha de base abaixo.

## Linha de base

(O número ou comportamento que o critério de pronto vai comparar no próximo ciclo,
medido agora: linha do `telemetria.py resumo`, contagem, ocorrência. Sem trajetória,
diga como vai observar.)

## Veredicto da evolução anterior

**Item:** <nome> (EVOL-YYYY-MM-DD) · **Veredicto:** ajudou | piorou | sem efeito observado | confundido
**Contraste:** <linha de base → agora, e onde se viu>
**Lição:** <.agents/memory/<slug>.md> | sem lição

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

- **Veredicto antes da escolha.** A evolução anterior recebe veredicto antes de a próxima
  ser escolhida. `confundido` é resposta válida; `ajudou` sem contraste não é.
- **Uma pergunta por vez.** Não enfileire as 5.
- **Não construa nada agora.** Esta skill produz a SPEC do que será construído. A construção é trabalho do arquiteto + codificador na semana seguinte.
- **Recomende UM item.** Mesmo que apareçam 5 candidatos. Disciplina é o que faz a fábrica evoluir consistentemente.
- **Não puxe respostas.** Se o usuário disser "nenhum prompt repetido esta semana", aceite. Próxima pergunta.
- **Salve o registro mesmo se nada novo emergir.** Padrão "esta semana sem novidade" é informação útil — talvez a fábrica esteja madura, talvez você não tenha trabalhado o suficiente, ambas hipóteses interessantes.
