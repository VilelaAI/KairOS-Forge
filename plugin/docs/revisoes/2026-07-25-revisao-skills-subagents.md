# Revisão de qualidade — 12 skills e 52 subagents (2026-07-25)

Revisão completa do catálogo do plugin aplicando a metodologia de três skills públicas do [tech-leads-club/agent-skills](https://github.com/tech-leads-club/agent-skills): **skill-architect** (checklist estrutural + qualidade de description com fronteiras de escopo + disclosure progressivo), **subagent-creator** (description como sinal de delegação, responsabilidade única, prompt conciso) e **cursor-subagent-creator** (frontmatter Cursor: `readonly`, `model`, `is_background`).

## O que foi verificado

| Verificação | Resultado |
|---|---|
| SKILL.md com casing exato, frontmatter `---`, `name` = pasta, pasta kebab-case | ✅ 12/12 |
| Description em linha única, ≤ 1024 chars, sem angle brackets | ⚠️ 1 violação (corrigida) |
| Sem README.md dentro de pasta de skill | ✅ 12/12 |
| Corpo ≤ 500 linhas; material pesado em `references/` | ✅ 12/12 (maior: mobilizar, 302) |
| Instruções críticas no topo (regra de ouro), sem hard-wrap de prosa | ✅ |
| Description com fronteira de escopo ("não use para…") | ❌ 0/12 (corrigido em 12/12) |
| Agents: `name` kebab-case = arquivo, description com sinal de delegação | ✅ 52/52 |
| Agents: allow-list `tools:` explícita (regra 4 do CLAUDE.md) | ✅ 52/52 |
| Agents: responsabilidade única + seção de Limites + fronteiras nomeadas | ✅ 52/52 |
| Cursor: `readonly` correto por derivação da allow-list | ✅ 14 readonly (verificado) |

## Correções aplicadas (v0.10.1)

1. **`analisar-ameacas`: angle brackets na description** (`AMEACAS-<feature>-…`) — violação de regra dura do padrão Agent Skills (quebra parsers de frontmatter). Trocado por `AMEACAS-*.md`.
2. **Fronteiras de escopo nas 12 descriptions.** Nenhuma description tinha gatilho negativo, e o catálogo tem pares com sobreposição real de trigger. Cada description agora fecha com "não use para X — use Y" no par correto:
   - `validar` ↔ `revisar` (aceite de SPEC × code review)
   - `rodar` ↔ `mobilizar` (sequencial × paralelo; exclusividade Claude Code agora declarada na description do mobilizar)
   - `mapear-arquitetura` ↔ `mapear-conhecimento` (estrutura de código × grafo de fatos)
   - `otimizar` ↔ `evoluir` ↔ `revisar` (melhorar métrica × escolher capacidade × qualidade sem métrica)
   - `analisar-ameacas` ↔ `revisar` (desenho antes × auditoria depois)
   - `auditar` (fábrica, não produto), `especificar` (não para trivial), `onboardar` (não para projeto já onboardado)

## Decisões deliberadas (avaliadas e mantidas como estão)

1. **Personas sem processo/formato de saída por agente.** O subagent-creator recomenda "When invoked: 1..2..3 + Report format" por agente. Na fábrica, o **processo mora nas skills** (especificar/validar/revisar…) e as personas ficam finas (comportamento + fronteiras + limites) — composability deliberada: 52 prompts com processo duplicariam as skills e dessincronizariam. A seção "Quando você é invocado" cumpre o papel do "When invoked" do template.
2. **Helena não-readonly no Cursor.** A allow-list dela (`Read, Grep, Glob, Bash`) não tem Write/Edit, mas tem Bash (necessário para rodar scanners como `check-agent-security.py`). Bash é capaz de escrita, então a derivação conservadora do sync está correta em não marcá-la `readonly`. Os 14 readonly derivados conferem com as allow-lists.
3. **Sem `license`/`metadata` no frontmatter das skills.** Convenção do catálogo tech-leads-club, não exigência do padrão Agent Skills que os CLIs leem. O licenciamento do plugin é o MIT do repositório.
4. **Descriptions dos 21 apoio com "Quando precisar…" em vez de "Use…".** Sinal de delegação equivalente, com `sinais_ativacao` e a restrição "NÃO implementa código" — já cumprem o critério.

## Como reproduzir esta revisão

Checks estruturais são automatizáveis (foram rodados via script nesta revisão): casing, frontmatter, kebab-case, tamanho/linha única/brackets da description, limite de 500 linhas, presença de `tools:` nos 52 agents, derivação de `readonly` no `.cursor/`. Os critérios qualitativos (fronteira de escopo, responsabilidade única, teste mental de triggers) seguem os checklists das três skills citadas. Sugestão de ritual: repetir a cada minor que adicionar skill ou agente.
