# Embratur Skills

Pacote oficial de **skills** da Embratur para acelerar o desenvolvimento de software com agentes de IA.

Compatível com:

- [**Lovable**](https://lovable.dev) — workspace-scoped skills
- [**Replit Agent**](https://replit.com) — diretório `/.agents/skills/`
- [**Claude Code**](https://claude.ai/code), [**Codex CLI**](https://github.com/openai/codex), [**Cursor**](https://cursor.sh) e qualquer outro agente que siga o padrão aberto SKILL.md

## O que tem aqui

19 skills em PT-BR, organizadas em duas famílias:

### 🧑‍💼 10 skills de personas (a fábrica)

Cada skill representa um time temático com personas especializadas. Use quando quiser delegar uma tarefa para o "papel" certo.

| Skill | Personas embutidas | Quando usar |
|---|---|---|
| [`arquitetar-sistema`](skills/arquitetar-sistema/SKILL.md) | Laura, Rafael, Diego, Fernanda, Thiago | Desenhar feature antes de codar |
| [`desenvolver-backend`](skills/desenvolver-backend/SKILL.md) | Lucas, Carlos, Vinícius, Juliana, Gabriel, André | Implementar API, banco, lógica de servidor |
| [`desenvolver-frontend`](skills/desenvolver-frontend/SKILL.md) | Marina, Pablo, Isabela, Ada | Construir telas, componentes, UX |
| [`operar-infraestrutura`](skills/operar-infraestrutura/SKILL.md) | Elisa, Marcos, Renata | Cloud, CI/CD, observabilidade |
| [`garantir-qualidade`](skills/garantir-qualidade/SKILL.md) | Patrícia, Ricardo, Helena | Testes, segurança, regressão |
| [`gerenciar-produto`](skills/gerenciar-produto/SKILL.md) | Camila, Hugo, Sofia, Rui | Escopo, priorização, lançamento |
| [`documentar-software`](skills/documentar-software/SKILL.md) | Beatriz, Felipe, Marcos [Specs], Renato, Helena [Apresentação] | README, ADR, OpenAPI, demos |
| [`comunicar-produto`](skills/comunicar-produto/SKILL.md) | Celina, Cora, Elisa [Naming], Bruno, Letícia | Microcopy, voz, naming, taxonomia |
| [`medir-e-experimentar`](skills/medir-e-experimentar/SKILL.md) | Lia, Otávio, Vera, Tomás, Clara, Enzo | Tracking, KPIs, A/B, DORA |
| [`revisar-decisoes`](skills/revisar-decisoes/SKILL.md) | Álvaro, Lúcia, Félix, Dante | Pre-mortem, red team, debate |

### 🛠️ 9 skills de processo (o fluxo)

Skills que organizam o ciclo de vida — onboarding, especificação, validação, revisão, auditoria.

| Skill | Quando usar |
|---|---|
| [`onboardar`](skills/onboardar/SKILL.md) | Primeira vez em um projeto — gera CLAUDE.md e estrutura |
| [`mapear-arquitetura`](skills/mapear-arquitetura/SKILL.md) | Antes de refatorações grandes em projeto brownfield |
| [`especificar`](skills/especificar/SKILL.md) | Antes de codar feature não-trivial — produz SPEC rastreável |
| [`analisar-ameacas`](skills/analisar-ameacas/SKILL.md) | Antes de feature sensível (auth, PII, billing) — threat model |
| [`orquestrar-fabrica`](skills/orquestrar-fabrica/SKILL.md) | Tarefa que precisa de múltiplas personas conversando |
| [`validar`](skills/validar/SKILL.md) | Depois de implementar — aceite contra SPEC |
| [`revisar`](skills/revisar/SKILL.md) | Antes de PR — revisão multi-dimensão (segurança, QA, performance) |
| [`auditar`](skills/auditar/SKILL.md) | Sexta-feira — pontua o setup do projeto em 5 dimensões |
| [`evoluir`](skills/evoluir/SKILL.md) | Depois de auditar — escolhe UMA capacidade nova pra construir |

## Como instalar

### No Lovable

1. No chat do seu projeto Lovable, abra a sidebar **Skills**.
2. Para cada skill que quer adicionar, clique **Create skill** e cole o conteúdo do `SKILL.md` correspondente.
3. O Lovable indexa o frontmatter (`name`, `description`) e ativa a skill automaticamente quando o contexto bate com a descrição.

Alternativa via repo: faça fork deste repositório, conecte-o ao Lovable como fonte de skills do workspace, e o catálogo aparece pronto.

📖 Doc oficial: https://lovable.dev/blog/introducing-skills

### No Replit Agent

1. Clone este repo no seu projeto Replit, ou copie o conteúdo da pasta `skills/`.
2. Coloque cada skill em `.agents/skills/<nome>/SKILL.md` na raiz do projeto Replit.
3. O Replit Agent passa a descobrir as skills automaticamente.

Exemplo via terminal Replit:

```bash
git clone https://github.com/embratur/embratur-skills /tmp/embratur-skills
mkdir -p .agents/skills
cp -r /tmp/embratur-skills/skills/* .agents/skills/
```

📖 Doc oficial: https://docs.replit.com/core-concepts/agent/skills

### No Claude Code / Codex CLI / Cursor

Estas ferramentas leem skills da raiz do projeto ou de plugins. Você pode:

- **Por projeto**: copiar a pasta `skills/` para a raiz do seu repo.
- **Global**: clonar este repo em `~/.claude/skills/` (Claude Code), `~/.codex/skills/` (Codex) ou equivalente.

## Convenções

Todas as skills seguem 4 regras rígidas:

1. **PT-BR.** Nomes, descrições, instruções, exemplos — tudo em português brasileiro.
2. **Verbos no infinitivo no nome.** `especificar`, não `spec`.
3. **`description` no formato "Use when..."** — é o que faz a skill ser descoberta automaticamente pelo agente.
4. **Personas mantêm consistência.** Laura é sempre Laura, Marina é sempre Marina. Skills temáticas embutem personas, não inventam novas.

## Como contribuir

Veja [`CONTRIBUTING.md`](CONTRIBUTING.md) para adicionar uma skill nova, propor mudança ou reportar bug.

## Atribuição

Este pacote é derivado do [`kairos-forge`](https://github.com/VilelaAI/kairos-forge) (MIT, VilelaAI), curado pela Embratur para uso interno e disponibilizado publicamente sob a mesma licença MIT.

A skill `mobilizar` do `kairos-forge` original **não foi portada** — ela depende de Agent Teams nativos do Claude Code e não funciona em Lovable nem em Replit. A skill `orquestrar-fabrica` substitui o caso de uso conversacional.

## Licença

MIT — veja [`LICENSE`](LICENSE).
