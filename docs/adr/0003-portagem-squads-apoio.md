# ADR-0003 — Portagem dos squads de apoio do kairos-ai

**Status:** Aceito
**Data:** 2026-05-06
**Autor:** Allyson Vilela

## Contexto

O `kairos-ai` mantém em `scripts/squads-apoio/` sete squads de apoio à engenharia, totalizando 21 agentes:

- `apoio-microcopy` (3)
- `apoio-narrativa` (3)
- `apoio-naming` (3)
- `apoio-valor` (3)
- `apoio-observabilidade` (3)
- `apoio-dx` (3)
- `apoio-revisao-arquitetural` (3)

Esses squads não são específicos de domínio regulado. Os frameworks que usam (Sparkline de Duarte, Inversão de Munger, AARRR, ICE, DORA, Schwartz, MECE, FMEA) são universais e aplicáveis a qualquer projeto de software.

A questão era: portar para o `kairos-forge` (MIT genérico) ou manter exclusivamente no `kairos-ai`?

## Decisão

**Portar os 21 agentes** para o `kairos-forge` v0.3, com adaptações:

1. **Prefixo `apoio-` no id de arquivo** para evitar colisão com agentes core (ex: `apoio-marcos-specs.md` vs `marcos-devops.md`).
2. **Generalização de referências regulatórias** — referências a LGPD, NRs, ANPD nas instruções dos agentes foram substituídas por linguagem genérica ("regulamentação aplicável", "termos técnicos consagrados").
3. **Tools restritas** — agentes de apoio recebem `Read, Grep, Glob, Write, Edit` (escrevem em arquivos de doc/markdown), mas **nunca** `Bash` arbitrário. Os puramente analíticos (Letícia revisão, Dante desbloqueio, Álvaro/Lúcia/Félix da revisão arquitetural) recebem só `Read, Grep, Glob`.
4. **Nota explícita de migração para kairos-ai** — cada agente de apoio inclui no rodapé: "Se a tarefa envolver requisito regulado específico, recomende migrar para o kairos-ai."

## Justificativa

Os squads de apoio são **camada universal**, não regulatória. Mantê-los só no kairos-ai PRO seria:

- Negar valor genuíno ao usuário MIT (frameworks como Inversão de Munger ou DORA não dependem de LGPD)
- Quebrar a paridade de funcionalidade técnica que justifica usar Forge antes de migrar pro PRO
- Criar barreira artificial — alguém que precisa de um pre-mortem não deveria precisar pagar PRO por isso

A diferença entre Forge e kairos-ai continua clara mesmo com a portagem: o que define o PRO é o squad **negocial** (DPO, Mapeamento, Consentimento) e os **domínios regulados** com guardrails legais — nada disso entra no Forge.

## Colisões de nome

A portagem cria três pares Nome+Papel onde o primeiro nome se repete:

| Core | Apoio | Como desambiguar |
|---|---|---|
| Marcos [DevOps] | Marcos [Specs] | "Marcos qual? DevOps (deploy/CI) ou Specs (ADR/spec)?" |
| Helena [Security] | Helena [Apresentação] | "Helena qual? Security (audit) ou Apresentação (demo)?" |
| Elisa [Cloud] | Elisa [Naming] | "Elisa qual? Cloud (provedor) ou Naming (nomenclatura)?" |

**Mitigação:**

- Os ids de arquivo são distintos (`marcos-devops.md` vs `apoio-marcos-specs.md`)
- O prefixo visual `Marcos [DevOps]` vs `Marcos [Specs]` desambigua na resposta
- Laura tem instrução explícita (na sua spec de agente) para perguntar contexto antes de invocar quando o usuário disser apenas o primeiro nome
- O `description` do frontmatter é distinto e ajuda o roteador automático do Claude Code

**Por que não renomear?**

- Os nomes vieram do kairos-ai e mantê-los preserva paridade entre os dois plugins
- Renomear "Marcos [Specs]" para algo como "Beto [Specs]" descaracterizaria a fonte
- Se o usuário tem familiaridade com kairos-ai, encontrar os mesmos nomes no Forge reduz fricção

## Como os squads de apoio funcionam no Forge

Diferente da fábrica core (sempre ativa), os squads de apoio são **carregados sob demanda**:

```
/kairos-forge:rodar apoio-naming      # ativa Elisa, Bruno, Cora
/kairos-forge:rodar apoio-narrativa   # ativa Marcos [Specs], Helena [Apresentação], Dante
```

Apenas **1 squad de apoio ativo por vez** na sessão. Trocar é OK, misturar não — a regra vem do README original do kairos-ai e foi mantida.

Laura conhece os squads de apoio e pode sugerir invocá-los baseada nos sinais de ativação (palavras-chave em `templates/squad-fabrica.yaml`).

## Tools por categoria

| Categoria de agente | Tools | Justificativa |
|---|---|---|
| Microcopy/Naming/Valor (escrevem markdown) | Read, Grep, Glob, Write, Edit | Produzem listas, glossários, planos em md |
| Narrativa Specs/Apresentação | Read, Grep, Glob, Write, Edit | Escrevem ADRs e roteiros |
| Narrativa Desbloqueio (Dante) | Read, Grep, Glob | Facilita decisão, não escreve artefato |
| Microcopy Revisão (Letícia) | Read, Grep, Glob | Revisa, não cria texto novo |
| Observabilidade/DX | Read, Grep, Glob, Write, Edit | Tracking plans e journey docs |
| Tomás (Impacto/DORA) | Read, Grep, Glob, WebSearch, WebFetch | Pesquisa benchmarks externos de DORA |
| Revisão Arquitetural (Álvaro/Lúcia/Félix) | Read, Grep, Glob | Análise pura, entrega relatório verbal |

**Nenhum agente de apoio recebe `Bash`** — isso reforça a regra "apoio nunca implementa código".

## Modelo

`opus` para os agentes que tomam decisões pesadas:

- `apoio-alvaro-inversao` — Inversão de Munger requer raciocínio cuidadoso
- `apoio-lucia-principios` — Aplicar SOLID/CAP/Conway requer julgamento
- `apoio-felix-provocador` — Red Team com cenários concretos
- `apoio-rui-audit` — TCO e ROI dependem de análise multi-fator
- `apoio-hugo-priorizacao` — Value Equation + ICE
- `apoio-marcos-specs` — ADRs precisam de raciocínio cuidadoso

Os demais usam o modelo padrão da sessão.

## Consequências

### Positivas

- Forge passa de 24 para 45 agentes — paridade técnica completa com kairos-ai
- Frameworks valiosos (Sparkline, Inversão, AARRR, DORA) ficam acessíveis no MIT
- Forge fica mais auto-suficiente — usuário consegue todo o ciclo (design → naming → spec → impl → revisão → lançamento → audit) sem migrar pro PRO

### Negativas

- Plugin cresceu — 21 arquivos novos em `agents/`
- Colisões de nome criam fricção pequena na invocação
- Manutenção dupla: melhorias nos agentes de apoio precisam ser portadas manualmente do kairos-ai pro Forge (e vice-versa)

### Mitigações

- Documentar colisões explicitamente no README e na spec da Laura
- ADR-0002 (relação Forge ↔ kairos-ai) já estabelece independência: cada plugin evolui separado, não há sync automático
- Quando uma melhoria comum acontece, abrir issues cruzadas em ambos os repos

## Revisão futura

Esta decisão será revisitada se:

1. Os squads de apoio começarem a divergir significativamente entre os dois plugins (sinal de que precisam de tratamento diferenciado)
2. Surgir um squad de apoio claramente regulado-only (ex: "apoio-dpo-comunicacao") — esse fica só no kairos-ai
3. Laura ou usuários reportarem confusão recorrente nas colisões de nome — pode levar a renaming dos agentes Forge
