---
inclusion: always
---

🔥 kairos-forge v0.28 ativo (Kiro) — 71 agentes (40 core + 31 apoio em 10 squads).

- Skills da fábrica em `.kiro/skills/`: analisar-ameacas, auditar, avaliar, desenhar, diagnosticar, entregar, especificar, evoluir, lancar, mapear-arquitetura, mapear-conhecimento, migrar, onboardar, otimizar, revisar, rodar, validar. A skill `mobilizar`
  precisa de Agent Teams do Claude Code — aqui use `rodar` (mesmo fluxo, modo
  sequencial).
- As personas são configs de agente em `.kiro/agents/<id>.json`. Laura
  (`laura-tech-lead`) é o ponto de entrada: ela analisa a tarefa e decide quem
  entra. Cada agente responde em primeira pessoa e se apresenta pelo nome.
  No Kiro Crew, cada uma roda como `kiro-cli acp --agent <id>`.
- Resolução de caminhos: quando uma skill referenciar `${CLAUDE_PLUGIN_ROOT}/<path>`,
  resolva para `<path>` dentro do `.kiro/` onde o kairos-forge foi instalado —
  ex.: `.kiro/scripts/grafo.py` no projeto, ou `~/.kiro/scripts/grafo.py` se a
  instalação foi global.
- Telemetria e guardrails (ADR-0021/0022) vêm nos hooks de cada config de agente.
  Se os hooks não dispararem na sua superfície do Kiro, `.agents/execucoes/` fica
  vazio, a dimensão Autonomia do `/auditar` pontua 0 e o `/validar` pula a
  corroboração de trajetória — comportamento honesto, não bug. O caminho nesse
  caso é rodar os checks no CI do projeto (`.kiro/templates/ci/`) e, sob Kiro
  Crew, pendurar o `guardrail.py verificar` no gate de PreToolUse do Gateway.
- Idioma: PT-BR em tudo — mensagens, comentários de código, commits.

> Arquivo GERADO por scripts/sync-multi-cli.py (kairos-forge). Não edite aqui —
> edite os canônicos agents/ e skills/ e rode o sync.
