# ADR-0025 — Skill `avaliar`: eval com rubrica como gate, no projeto e no próprio plugin

- **Status:** aceito
- **Data:** 2026-08-01
- **Versão:** v0.19.0

## Contexto

O whitepaper Day-1 estabelece um teste **binário** para separar engenharia agêntica de
vibe coding, e não deixa margem:

> *"Tests verify the deterministic parts of the system... Evaluations, or evals, verify the
> parts that are not deterministic: did the agent take the right trajectory of steps, choose
> the right tools, and produce a final response that meets the quality bar. **Without both,
> the practice is always vibe coding, regardless of how sophisticated the prompts are.**"*

E a régua para líderes: *"Set the bar at the eval, not the demo. A working demo proves an
agent can succeed once. A passing eval suite proves it succeeds reliably. **But an eval
without a clear rubric measures nothing.** Define what you are scoring: task success, tool
use quality, trajectory compliance, hallucination, and response quality."*

Aplicando isso ao que o kairos-forge entregava até a v0.18:

- **Testes:** cobertos e maduros — Ricardo, matriz de testes por requisito na SPEC, gates
  por tarefa, `contextos/testes.md`, e o `/validar` re-executando os gates de forma
  independente.
- **Evals:** **um** em todo o repositório (`evals/roteamento-laura/`, 60 casos). Dogfooding
  do plugin, explicitamente não distribuído (*"só na raiz, não distribui"*), e com a
  acurácia apurada **à mão, em sessão**, pela Alice. O CI só verificava que os ids citados
  existiam em `agents/`.

Duas conclusões desconfortáveis. Primeira: pela régua do próprio paper, **o usuário do
kairos-forge recebia disciplina de teste e nenhuma disciplina de eval** — no eixo de
verificação, o harness entregue ficava em "structured AI-assisted coding". Segunda: **o
plugin pregava o eval e media o dele por impressão.**

A Alice existia como agente desde a v0.13 e é excelente ("assume quebrado até provar o
contrário", "o gerador nunca avalia a si mesmo"), mas não havia skill, template, rubrica
nem gate que materializasse isso no projeto de ninguém.

## Decisão

### 1. Skill `avaliar` (dona: Alice) — 16 → 17 skills

Operacionaliza o que a Alice já defende, em oito passos: delimitar **um** comportamento,
construir gold set versionado fora dos prompts, escrever a rubrica, medir baseline e fixar
limiar, rodar, **diagnosticar por agrupamento de causa raiz**, instalar o gate no CI,
registrar.

**A rubrica usa os cinco eixos que o paper nomeia**, e a skill obriga a declarar quais
foram descartados e por quê. O eixo destacado é **conformidade de trajetória** — o mais
esquecido e o que mais dói, porque uma saída fluente que pulou a verificação parece certa.
É o mesmo princípio que o ADR-0021 aplicou ao `verificado:`, agora no comportamento do
produto do usuário em vez de no processo da fábrica.

Duas regras de composição do gold set merecem destaque por serem contraintuitivas:

- **Casos reais valem mais que sintéticos.** Caso inventado testa a imaginação de quem
  escreveu, não o sistema.
- **Inclua o "deve recusar".** Casos onde a resposta certa é não responder são os que mais
  separam sistema bom de sistema confiante.

O passo de **agrupamento por causa raiz** é o que a skill trata como não-negociável: sete
casos com a mesma causa são um problema, não sete. Corrigir caso a caso é ajustar o sistema
ao gold set — Goodhart pela porta dos fundos.

E o **volante de qualidade** do paper vira ciclo explícito: avaliar → agrupar → corrigir a
causa → verificar contra o gold set → monitorar produção. Falha nova encontrada em produção
**vira caso no gold set antes de ser corrigida** — é o que faz o gold set crescer no lugar
certo em vez de crescer por invenção.

### 2. `evals/roteamento-laura/rodar.py` — o dogfooding

O gold set do próprio plugin passa a rodar headless: apresenta cada `pedido` à Laura via
`claude -p`, extrai o id acionado, compara com os aceitáveis e falha abaixo do limiar (90%).

Duas decisões de desenho:

- **Sem o CLI `claude` disponível, sai com 0 e diz que pulou.** CI sem credencial não
  quebra o build por ausência de chave: falso vermelho treina o time a ignorar o vermelho.
- **Resposta ambígua conta como erro.** Se a Laura cita dois ids, ela não escolheu — e
  roteamento que não escolhe não roteia.

O job no CI do plugin roda em `workflow_dispatch` e no merge para `main`, não em todo PR:
o eval custa tokens, e a skill que prega orçamento declarado precisa respeitar o próprio.

## Consequências

**Positivas**

- O usuário passa a ter as duas metades da verificação. Pela régua do paper, é o que move o
  produto de "structured AI-assisted coding" para engenharia agêntica no eixo que faltava.
- O plugin para de pregar o que não pratica: o eval de roteamento vira executável e falhável.
- A dimensão Autonomia do `/auditar` ganha um vizinho natural — evals são o que justifica
  confiar no harness quando ninguém lê o diff.
- Alice sai de agente consultivo para dona de um ritual com artefato versionado.

**Negativas e limites, declarados**

- **Eval custa tokens, e mais que teste.** Por isso o gate é declarado por regra de
  regressão ("mudou X, roda") e não em todo commit.
- **Juiz-LLM tem viés e variância.** A skill limita seu uso ao que não é verificável
  programaticamente e exige critério escrito + amostra conferida à mão para calibrar. Não
  elimina o problema; torna-o visível.
- **Gold set envelhece.** Sem o passo de "falha de produção vira caso", ele vira museu que
  aprova tudo. A skill coloca isso no volante, mas quem mantém é o time.
- **~30 casos é um mínimo frouxo.** Suficiente para o percentual não ser ruído puro,
  insuficiente para estatística séria. A skill manda declarar o N junto do percentual
  sempre, o que é a mitigação honesta possível.
- **17 skills começa a ser muito para rotear.** O `avaliar` tem fronteira explícita contra
  Ricardo (determinístico), Helena (segurança clássica), Patrícia (estratégia) e `otimizar`
  (métrica que já existe), e o gold set de roteamento ganhou casos para essas fronteiras.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Deixar evals como responsabilidade só da Alice, sem skill | Era o estado até a v0.18. Agente sem ritual não produz artefato: nenhum projeto ganhou gold set em três versões |
| Embutir o eval dentro do `/validar` | Validar responde "cumpre a SPEC?" com gates determinísticos. Misturar as duas coisas confunde o que é teste e o que é eval — exatamente a distinção que o paper diz ser o divisor de águas |
| Rodar o eval de roteamento em todo PR | Caro e lento para um repo cujo PR médio mexe em prosa. Regra de regressão declarada entrega o mesmo com uma fração do custo |
| Falhar o CI quando não há `ANTHROPIC_API_KEY` | Todo fork e todo PR externo ficaria vermelho por falta de credencial. Vermelho que não significa nada é pior que ausência de check |
