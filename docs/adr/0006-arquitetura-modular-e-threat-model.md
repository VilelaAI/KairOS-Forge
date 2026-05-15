# ADR-0006 — Arquitetura modular, threat model e dimensão Estrutura na auditoria

**Status:** Aceito
**Data:** 2026-05-15

## Contexto

A v0.5.0 fechou a lacuna de **rastreabilidade** entre SPEC, implementação e validação (`/especificar` com IDs e gates, `/validar` separado de `/revisar`). Restavam duas lacunas estruturais identificadas na análise do marketplace tlc:

1. O `kairos-forge` não tinha trilha para projetos **brownfield** ou para refatoração estrutural — Diego/Rafael/Fernanda/Thiago são citados, mas não há skill que produza um mapa honesto de acoplamento, duplicação e bounded contexts antes de uma decisão arquitetural grande.
2. Helena entrava só dentro de `/revisar` (pré-PR) e `/validar` (pós-implementação). Não havia momento explícito para antecipar **antes** da implementação — o que justifica modelo de ameaças em features sensíveis (auth, PII, multi-tenant, billing, IA).

A auditoria semanal também não enxergava essas dimensões: o `score` de 100 pontos sobre Fundação/Pipeline/Guardrails/Conhecimento podia dar 95/100 enquanto a arquitetura virava monolito com hotspots sem dono.

## Decisão

A partir da v0.6.0:

- **Nova skill `/kairos-forge:mapear-arquitetura`** — coordenada por Diego (com Fernanda/Thiago/Rafael conforme dimensões), produz `docs/arquitetura/MAPA-YYYY-MM-DD.md` com inventário, acoplamento, duplicação de domínio, bounded contexts e plano incremental de decomposição. Read-only. Toda afirmação exige evidência ou marcação "hipótese".
- **Nova skill `/kairos-forge:analisar-ameacas`** — coordenada por Helena (com Carlos/Marcos/Thiago/Gabriel/Renata conforme escopo), produz `docs/seguranca/AMEACAS-<feature>-YYYY-MM-DD.md` com ativos, trust boundaries, entrypoints, perfis realistas de atacante, abuse paths e mitigações priorizadas por camada. Usada **antes** de implementar features sensíveis.
- **`/kairos-forge:auditar` passa a ter 5 dimensões em vez de 4**, com a nova dimensão **Estrutura** (20 pts) cobrindo CODEOWNERS, mapa recente, modelo de ameaças, hotspots órfãos, acoplamento documentado e ausência de duplicação grave. As outras quatro dimensões caem de 25 para 20 pontos cada para manter o total em 100.
- Total de skills sobe de 8 para 10. As descrições em `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` e `marketplace.json` mencionam as novas.

## Consequências

Boas:

- Projetos brownfield ganham um ponto de entrada (mapa) antes de cair direto em `/especificar`.
- Features sensíveis ganham um passo de antecipação de risco antes de virar código.
- A auditoria semanal passa a sinalizar dívida arquitetural e ownership, não só presença de artefatos.
- Helena, Diego e Rafael têm momento próprio na fábrica, sem precisar passar por `/revisar` para entrar.

Custos:

- O catálogo de skills cresce — usuários novos precisam aprender quando usar cada uma. Mitigação: `/onboardar` e README explicam a ordem natural (`onboardar` → `mapear-arquitetura` em brownfield → `especificar` → `analisar-ameacas` se sensível → `mobilizar`/`rodar` → `validar` → `revisar`).
- A dimensão Estrutura tende a sair baixa nas primeiras auditorias de projetos antigos. É esperado e útil.
- Threat model em escopo errado vira ruído. A skill `analisar-ameacas` é explícita sobre **não** usar em features triviais.

## Alternativas consideradas

1. **Embutir mapa arquitetural dentro de `/auditar`.**
   Rejeitado: confunde inventário estrutural (1-2 horas de trabalho focado) com pontuação semanal (10-15 minutos). Mapa precisa de escopo declarado pelo usuário.

2. **Embutir threat model dentro de `/especificar` ou `/revisar`.**
   Rejeitado por dois motivos: `especificar` ficaria longo demais para features pequenas, e `revisar` é pré-PR — tarde demais para antecipar.

3. **Criar uma só skill `seguranca` que cobre threat model + revisão de segurança.**
   Rejeitado: revisão de segurança já está em `/revisar` (com Helena participando). Threat model é antecipatório; revisão é reativa. Misturar mata os dois.

4. **Manter 4 dimensões em `/auditar` e medir Estrutura embutida em Guardrails.**
   Rejeitado: Estrutura é sobre forma do código, Guardrails é sobre processos de proteção. Misturar penalizaria projetos com CI bom mas arquitetura ruim, ou vice-versa.

## Roadmap subsequente

P2 (próximo bump 0.7.0):

- `/kairos-forge:migrar` para refatorações grandes baseadas em mapa.
- Modo RFC no `/especificar` para decisões grandes antes de virar SPEC.
- Modo `/revisar web` para auditoria de frontend (performance, acessibilidade, SEO, Core Web Vitals).

P3 (0.8.0):

- Skill opcional de aprendizado para times.
- Diagramas Mermaid integrados em ADRs, SPECs e mapas arquiteturais.
