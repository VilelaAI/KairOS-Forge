# ADR-0002 — Relação entre kairos-forge e kairos-ai

**Status:** Aceito
**Data:** 2026-05-03
**Autor:** Allyson Vilela

## Contexto

O `kairos-ai` foi publicado em meados de 2026 como plugin Claude Code com 31 skills, 9 agentes em 2 domínios regulados (LGPD, Segurança-TI), squad de fábrica de software com 24 agentes em 9 times, hooks, Ralph Loop, ADD (Assertion-Driven Development), Agent Teams nativos, e suporte a Codex CLI e OpenCode.

Em paralelo, foi planejada a construção do `kairos-forge` — inicialmente concebido como "fábrica de software autônoma" inspirada em [@regent0x_](https://x.com/regent0x_) e [@nateherk](https://x.com/nateherk).

Quando os dois projetos foram comparados, ficou claro que o `kairos-ai` **já contém** o squad técnico que o `kairos-forge` planejava construir (os 24 agentes em `scripts/squad-fabrica.yaml`).

A questão era: o `kairos-forge` é redundante? Deve ser descontinuado?

## Decisão

`kairos-forge` é mantido como **versão MIT genérica** (lite) do squad técnico. `kairos-ai` é a **versão para domínios regulados** (PRO).

### Divisão de responsabilidades

| Componente | kairos-forge | kairos-ai |
|---|---|---|
| 24 agentes técnicos | ✅ portados (genéricos) | ✅ originais |
| Squads negociais | ❌ | ✅ (DPO, Mapeamento, etc.) |
| Domínios regulados | ❌ | ✅ (LGPD, Segurança-TI) |
| Guardrails legais | ❌ | ✅ (com referência LGPD/OWASP) |
| Assertions binárias | ❌ | ✅ |
| Ralph Loop (auto-correção) | ❌ | ✅ |
| Advisor (Opus regulatório) | ❌ | ✅ |
| Squads de apoio | ❌ | ✅ (microcopy, naming, etc.) |
| Workflow stages YAML | ❌ (planejado v0.4) | ✅ |
| Modo debate | ❌ (planejado v0.5) | ✅ |
| Suporte multi-CLI (Codex/OpenCode) | ❌ (planejado v1.0) | ✅ |

### Independência

Os dois plugins são **independentes**. `kairos-forge` não importa código nem arquivos do `kairos-ai`. A duplicação dos 24 agentes é deliberada — são fontes paralelas que evoluem separadamente:

- Mudanças no `kairos-ai` (ex: novos agentes regulados, novos guardrails) **não propagam** para o forge.
- Mudanças no `kairos-forge` (ex: skills genéricas novas) **podem** ser portadas para o kairos-ai manualmente, mas não automaticamente.

### Quando usar cada um

| Cenário | Use |
|---|---|
| Projeto pessoal, hobby, OSS genérico | kairos-forge |
| Startup early-stage sem requisito de compliance ainda | kairos-forge |
| Produto B2B em saúde, jurídico, educação, RH | kairos-ai |
| Projeto que toca LGPD, Marco Civil, NRs | kairos-ai |
| Time grande com necessidade de rastreabilidade legal | kairos-ai |
| Quem quer experimentar a fábrica antes de pagar PRO | kairos-forge |

### Posicionamento de marketing

- **kairos-forge** é a porta de entrada do ecossistema. MIT, sem fricção, qualquer projeto.
- **kairos-ai** é o produto vertical. Domínios regulados brasileiros como diferencial.

## Alternativas consideradas

### A) Descontinuar o forge

Argumento: o kairos-ai já cobre tudo, manter dois plugins é desperdício.

**Rejeitado** porque:
- O forge serve um público diferente (devs sem compliance regulatório).
- Manter MIT puro sem apelo regulado é estratégia de funil — atrai usuário que pode migrar pro PRO.
- O kairos-ai carrega complexidade (domínios, advisor, Ralph) que pode intimidar quem só quer o squad técnico.

### B) Forge como "namespace genérico" do kairos-ai

Argumento: ter um `/kairos:rodar` (regulado) e `/kairos-forge:rodar` (genérico) no mesmo plugin.

**Rejeitado** porque:
- Mistura licenciamento (parte MIT, parte PRO) num mesmo repo é confuso.
- Dependência do kairos-ai pelo forge cria acoplamento ruim.
- Plugins separados permitem instalação independente — usuário escolhe o que quer.

### C) Forge importa agentes do kairos-ai como submódulo

Argumento: evita duplicação dos 24 agentes.

**Rejeitado** porque:
- Submódulo Git complica `git clone` e instalação via marketplace.
- O kairos-ai pode mudar agentes em direção PRO (ex: adicionar referência a guardrail) que não cabe no forge.
- Independência permite evolução em ritmos diferentes.

## Consequências

### Positivas

- Cada plugin tem foco claro e independente
- Usuários genéricos não pagam complexidade regulada
- Forge serve como vitrine MIT do ecossistema KairOS
- Possível migração `forge → kairos-ai` quando projeto cresce em regulação

### Negativas

- Duplicação dos 24 agentes (precisa sincronizar manualmente quando há melhoria comum)
- Marca dupla (kairos-forge / kairos-ai) — usuário pode se confundir

### Mitigações

- README de cada plugin explica explicitamente o outro e quando usar
- Tabela comparativa em ambos os READMEs
- Quando uma melhoria de agente comum acontece, abrir issue em ambos os repos com link cruzado

## Revisão futura

Esta decisão será revisitada se:

1. A duplicação dos 24 agentes começar a divergir significativamente (sinal de que o forge precisa ter agentes diferentes)
2. O forge ganhar tração própria e justificar features que o kairos-ai não tem
3. Anthropic mudar o modelo de plugins de forma que dependência entre plugins fique nativa
