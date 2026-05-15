# ADR-0005 — SPEC rastreável e validação contra contrato

**Status:** Aceito
**Data:** 2026-05-15

## Contexto

O `kairos-forge` já tinha um fluxo spec-driven com Laura, arquitetos, `/especificar`, `/mobilizar` e `/revisar`. O ponto fraco era operacional: a SPEC descrevia plano e testes, mas não obrigava IDs de requisito, critérios de aceite verificáveis, gates por tarefa nem uma etapa explícita de aceite antes do review pré-PR.

Isso deixava uma lacuna entre "implementamos algo parecido com a SPEC" e "temos evidência de que todos os P1 foram atendidos".

## Decisão

A partir da v0.5.0:

- `/kairos-forge:especificar` classifica complexidade por auto-sizing.
- SPECs passam a incluir requisitos rastreáveis, prioridades P1/P2/P3, critérios de aceite, matriz de testes e gates.
- `/kairos-forge:mobilizar` passa a consumir tarefas com requisito, Done when, gate e evidência obrigatória.
- `/kairos-forge:onboardar` cria `contextos/testes.md` e `decisoes/estado-operacional.md`.
- Nova skill `/kairos-forge:validar` valida implementação contra SPEC antes de `/kairos-forge:revisar`.
- `/kairos-forge:auditar` mede rastreabilidade, validações e gates.

## Consequências

Boas:

- Menos drift entre intenção, implementação e revisão.
- Revisão pré-PR fica mais limpa: primeiro se valida "cumpre a SPEC?", depois "o código está pronto?".
- Ricardo e Patrícia ganham critérios mais objetivos.
- Claude Code, Codex CLI e OpenCode continuam usando a mesma pasta `skills/`.

Custos:

- SPECs médias e grandes ficam mais formais.
- Projetos sem comandos de teste claros precisam preencher `contextos/testes.md`.
- Há uma nova skill no ciclo, então o onboarding e a documentação precisam mencionar 8 skills.

## Alternativas consideradas

1. Expandir `/revisar` para também validar SPEC.
   - Rejeitado: mistura aceite funcional com code review de segurança/qualidade.

2. Criar uma raiz `.specs/` separada.
   - Rejeitado: conflita com a taxonomia existente (`contextos/`, `decisoes/`, `docs/specs/`, `docs/adr/`).

3. Tornar commit por tarefa obrigatório.
   - Rejeitado: bom para Agent Teams, rígido demais para todos os CLIs e fluxos.
