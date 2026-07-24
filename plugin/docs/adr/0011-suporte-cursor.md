# ADR-0011 — Suporte ao Cursor: quarto CLI da fábrica

**Status:** Aceito
**Data:** 2026-07-24

## Contexto

O kairos-forge nasceu multi-CLI (ADR-0004): Claude Code é o canônico, Codex CLI recebe mirror gerado (`.agents/<id>/AGENT.md`) e OpenCode usa paths de fallback. O Cursor ficou de fora porque, à época, não tinha superfície de extensão compatível — rules estáticas não comportavam 52 personas nem 11 skills procedurais.

Isso mudou. O estado do Cursor em meados de 2026:

- **Agent Skills (Cursor 2.1+):** o Cursor adota o padrão aberto Agent Skills (agentskills.io) — o **mesmo formato `SKILL.md` do Claude Code** que o forge já usa. Descoberta em `.cursor/skills/<nome>/SKILL.md` (projeto) e `~/.cursor/skills/` (global), com fallback para `.claude/skills/` e `.codex/skills/`. Invocação pelo menu `/` ou automática pela `description`. Suporta `references/` e `scripts/` dentro da skill.
- **Subagents (Cursor 2.4+):** personas em `.cursor/agents/<id>.md` (projeto) e `~/.cursor/agents/` (global), markdown com frontmatter YAML (`name`, `description`, `model`, `readonly`, `is_background`) — deliberadamente compatível com o formato de subagents do Claude Code; em colisão de nome, `.cursor/` tem precedência sobre `.claude/`/`.codex/`.
- **Rules:** `.cursor/rules/*.mdc` com frontmatter (`description`, `alwaysApply`) — cobre o papel do banner de SessionStart.
- **AGENTS.md:** lido como instrução de projeto (mesmo formato que o Codex).

Ou seja: as skills do forge rodam no Cursor **sem transformação nenhuma**, e os agentes precisam só de uma transformação leve de frontmatter.

## Decisão

A partir da **v0.9.0**, o Cursor é o quarto CLI suportado, via um diretório **`.cursor/` gerado e commitado** (mesmo modelo do `.agents/` para Codex):

```
.cursor/
├── rules/kairos-forge.mdc      # gerado — banner/contexto alwaysApply + resolução de ${CLAUDE_PLUGIN_ROOT}
├── agents/<id>.md              # gerado — 52 personas em formato subagent do Cursor
├── skills/<verbo>/SKILL.md     # gerado — mirror das 11 skills (formato idêntico, padrão Agent Skills)
├── scripts/grafo.py            # gerado — cópia (skills referenciam via ${CLAUDE_PLUGIN_ROOT}/scripts/)
└── templates/                  # gerado — cópia (squad-fabrica.yaml, anti-drift.md, CLAUDE.md.template)
```

Tudo regenerado por `scripts/sync-multi-cli.py`. Instalação = um único copy:

```bash
git clone https://github.com/VilelaAI/kairos-forge.git
cp -R kairos-forge/plugin/.cursor /caminho/do/projeto/.cursor   # por projeto
# ou, para todos os projetos:
cp -R kairos-forge/plugin/.cursor/* ~/.cursor/
```

### Transformação dos agentes (Claude Code → Cursor)

| Campo | Tratamento | Por quê |
|---|---|---|
| `name`, `description` | preservados | mesmos semânticos nos dois formatos |
| corpo (persona, fronteiras, limites) | preservado | é o valor do agente |
| `tools:` (allow-list) | **removido**, com compensação | o Cursor não tem allow-list por agente; ver abaixo |
| `model:` | removido | valores do Cursor (`inherit`/`fast`) não mapeiam para `opus` |
| `readonly: true` | **adicionado quando a allow-list original não tem ferramenta de escrita** (Write/Edit/NotebookEdit/Bash) | preserva o espírito da allow-list na semântica que o Cursor oferece |

A regra 4 do CLAUDE.md ("agentes têm allow-list explícita") permanece válida **no canônico**; no Cursor ela degrada para o binário `readonly` — a melhor aproximação que a plataforma dá. Agentes consultivos (Fernanda, Helena, Patrícia, os 21 de apoio etc.) chegam ao Cursor sem poder de escrita, como no Claude Code.

### A rule `kairos-forge.mdc`

Um arquivo `alwaysApply` gerado que faz três coisas: apresenta a fábrica (contagem, Laura como entrada, PT-BR), avisa que `mobilizar` requer Agent Teams do Claude Code (no Cursor → `rodar`), e define a resolução de `${CLAUDE_PLUGIN_ROOT}`: quando uma skill referenciar `${CLAUDE_PLUGIN_ROOT}/<path>`, o agente resolve para o `.cursor/<path>` de onde o plugin foi instalado (projeto ou `~/.cursor`). É o que faz `grafo.py`, `squad-fabrica.yaml` e as references funcionarem fora do Claude Code.

### Limitações registradas

| Item | Cursor | Racional |
|---|---|---|
| `/mobilizar` (Agent Teams) | ❌ skill detecta e redireciona pra `rodar` | Cursor 2.4 tem subagents paralelos, mas não o protocolo TeamCreate/TaskCreate/SendMessage de que a skill depende |
| Hook PostToolUse pedagógico | ❌ | formato de hooks do Cursor é distinto (beta); fica para minor futuro se houver demanda |
| SessionStart banner | ✅ via rule `alwaysApply` | rules cobrem o caso melhor que hook |
| Allow-list de ferramentas | ⚠️ degrada para `readonly` | limitação da plataforma, compensada na transformação |

O ai-memory (ADR-0010) também suporta Cursor (`install-mcp --client cursor` + hooks), então a camada episódica de memória funciona lá igualmente.

## Versão

Novo CLI suportado + mudança no gerador de sync: bump **minor** 0.8.1 → **0.9.0**. O roadmap aspiracional da v0.9 (`/migrar`, modo RFC, Mermaid, debate) desloca para o minor seguinte — mesma precedência do ADR-0007.

## Consequências

Boas:

- A fábrica inteira (52 personas + 11 skills, incluindo grafo e memória) roda no editor onde parte dos usuários já vive, com instalação de um comando.
- Zero duplicação canônica: `.cursor/` é 100% gerado; a fonte continua `agents/` + `skills/`.
- Sinergia com ADR-0010: com ai-memory ativo, sair do Cursor e continuar no Claude Code (ou vice-versa) carrega o handoff.

Custos:

- Mais um mirror para regenerar a cada mudança (mitigado: mesmo comando de sync de sempre; esquecer o sync já era o risco existente do `.agents/`).
- Sem allow-list real por agente no Cursor (mitigado: `readonly` + a instrução de limites no corpo da persona).
- Duplicação física das skills no repo (`skills/` + `.cursor/skills/`); aceita porque é gerada — o mesmo trade-off já aceito para os subagents do Codex no ADR-0004.

## Alternativas consideradas

1. **Instruir o usuário a copiar `skills/` manualmente (modelo OpenCode).** Rejeitado como única via: perde os subagents (que o Cursor suporta nativamente e o OpenCode não), o banner e a resolução de `${CLAUDE_PLUGIN_ROOT}`. O copy único de `.cursor/` entrega a experiência completa.
2. **Apontar o Cursor para `.claude/skills/` via fallback.** Rejeitado: o plugin instalado pelo marketplace do Claude Code vive no cache de plugins, não em `.claude/skills/` do projeto — o fallback não o encontra. E não resolveria agents nem rules.
3. **Gerar comandos em `.cursor/commands/`.** Rejeitado: redundante — as skills já aparecem no menu `/` do Cursor com o mesmo UX.
4. **Adaptar `mobilizar` aos subagents paralelos do Cursor.** Adiado: exigiria reescrever o protocolo de coordenação (Tasks, dependências, file ownership via mensagens) sobre primitivas diferentes. Candidato a ADR próprio se houver demanda real.
