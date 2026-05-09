# ADR-0001 — Plugin Claude Code em vez de runtime standalone

**Status:** Aceito
**Data:** 2026-05-03
**Autor:** Allyson Vilela

## Contexto

Em iterações anteriores deste projeto (sob nome de trabalho "KairOS-OpenClaw" e depois "KairOS Forge"), a ideia era construir um runtime autônomo de agentes — processo próprio, orquestração via Lobster YAML, integração via Telegram (agente "Bia"), memória via Basic Memory, e nove produtos SaaS scaffoldados em cima. A intenção era ter algo executando 24/7 sem depender de uma sessão humana ativa.

Em maio de 2026, a discussão foi reaberta a partir de dois artigos de operadores que demonstraram fábricas funcionais rodando inteiramente dentro do Claude Code — sem runtime próprio, sem orquestrador externo. Os dois exemplos:

- regent0x_ — fábrica de software de 5 agentes via subagents nativos do Claude Code
- nateherk — sistema operacional pessoal/empresarial via skills do Claude Code

Ambos rodam num plano $20/mês de Claude e cabem em um afternoon de setup.

Nenhum dos dois usa runtime próprio.

## Decisão

O `kairos-forge` é distribuído e executado **exclusivamente como plugin do Claude Code**.

- Manifest em `.claude-plugin/plugin.json`
- Subagentes nativos em `agents/`
- Skills nativas em `skills/`
- Hooks nativos em `hooks/hooks.json`
- Sem processo próprio, sem SDK próprio, sem orquestrador externo

Distribuição via `/plugin install` a partir de marketplace Git.

## Alternativas consideradas

### A) Runtime standalone Node/Python

Processo próprio que orquestra agentes via API da Anthropic, com fila de tarefas, agendamento, dashboard.

**Rejeitado porque:**
- Custo de manutenção desproporcional ao MVP
- Duplica capacidades já nativas do Claude Code (subagents, skills, hooks)
- Cria dependência de infra (servidor, banco, monitoring) que o usuário precisaria operar
- Atrasa validação do mental model em meses

### B) Híbrido — plugin agora + runtime depois

Começar como plugin, evoluir para runtime quando necessário.

**Não rejeitado, apenas adiado.** Esta decisão **não fecha** a porta para um runtime futuro. Se em algum momento a fábrica precisar rodar com laptop fechado, processar webhooks, ou orquestrar dezenas de agentes em paralelo de forma persistente, um runtime separado pode ser construído **consumindo** o `kairos-forge` (skills e agentes reaproveitáveis) em vez de substituí-lo.

A sequência é: plugin primeiro, validação de uso real, depois decidir se runtime adiciona valor suficiente.

### C) Framework próprio em Python

Construir abstração própria sobre LLMs com tipo "LangChain mas pra fábrica de software".

**Rejeitado porque:**
- O Claude Code já é o framework. Construir outro em cima é redundante.
- Lock-in invertido: prendiamos o usuário a uma camada nossa em vez de aproveitar a camada que ele já usa.

## Consequências

### Positivas

- Tempo até primeiro uso real medido em dias, não meses
- Zero infraestrutura a operar (usuário tem Claude Code, tem fábrica)
- Cada nova capacidade do Claude Code (novos hooks, novos eventos, novos modelos) chega de graça
- Tamanho do projeto cabe em ~20 arquivos Markdown + 1 JSON
- Filipe não precisa validar termos de SLA de runtime próprio

### Negativas

- Limitado às capacidades expostas pelo Claude Code (sem orquestração paralela nativa, sem agendamento próprio)
- Atualização do plugin exige `/reload-plugins` — não há hot-reload puro
- Distribuição depende do mecanismo de marketplaces do Claude Code

### Mitigações

- Para orquestração paralela: documentar uso de `claude-squad` (terceiro) em vez de implementar
- Para agendamento: documentar uso de Cloud Routines do próprio Claude Code (não precisa reimplementar)

## Revisão futura

Esta decisão será revisitada se uma das condições abaixo ocorrer:

1. Mais de 10 usuários reportarem necessidade clara de uso headless (sem sessão humana)
2. Uma capacidade essencial não conseguir ser implementada como skill/agent/hook
3. Anthropic deprecar plugins do Claude Code (improvável a curto prazo, lançado em GA em 2025)
