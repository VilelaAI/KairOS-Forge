# ADR-0004 — Compatibilidade multi-CLI (Claude Code, Codex CLI, OpenCode)

**Status:** Aceito (revisão 0.4.2 corrige erros adicionais descobertos em teste real)
**Data:** 2026-05-08
**Autor:** Allyson Vilela

## Histórico de revisões

- **v0.4.0** — primeira tentativa, com erros estruturais (documentou flag `--plugin-dir` inexistente e mirror `.agents/skills/` desnecessário)
- **v0.4.1** — corrigiu o mirror duplicado e o nome do subcomando, mas ainda assumia `codex plugin install` como existente
- **v0.4.2** — testado em ambiente real (macOS); corrige (a) `codex plugin install` não é subcomando da CLI — install acontece dentro da TUI; (b) `cp -T` é GNU coreutils-only, falha no macOS; (c) marketplace.json para Claude Code precisa estar em `.claude-plugin/marketplace.json`, separado do path do Codex (`.agents/plugins/marketplace.json`)
- **v0.4.3** — testado em Codex CLI v0.129.0 real; descobriu que **plugin precisa estar em subdiretório, não na raiz do marketplace**. Reorganizou todo o repo: raiz vira marketplace catalog, conteúdo do plugin move para `plugin/`. Schema do `marketplace.json` Codex corrigido — `source` é objeto `{source: "local", path: "./plugin"}`, com `policy` e `category` obrigatórios.

## Contexto

O `kairos-forge` foi originalmente concebido como plugin Claude Code (ADR-0001). Em 2026 três CLIs concorrentes coexistem no ecossistema de coding agents:

- **Claude Code** (Anthropic) — formato canônico inicial (`.claude-plugin/plugin.json`, `skills/`, `agents/`, `hooks/`).
- **Codex CLI** (OpenAI) — adoção crescente, segue a "open agent skills specification" e introduziu sistema próprio de plugins via `codex plugin` subcomando.
- **OpenCode** (open-source) — fallback de paths Claude Code; sem hooks nativos (depende do plugin externo `oh-my-opencode`).

O `kairos-ai` (PRO) já oferece compatibilidade nominal com os três. Manter o `kairos-forge` apenas Claude Code criava assimetria — a versão paga era mais portável que a gratuita.

## Decisão

`kairos-forge` é **multi-CLI compatível** desde a v0.4, com adaptações por CLI.

### Estrutura real (revisão v0.4.1)

A v0.4.0 inicial tinha erros estruturais — havia documentação do `codex --plugin-dir` (flag inexistente) e duplicação desnecessária de skills em `.agents/skills/`. A revisão v0.4.1 corrige:

| Componente | Path | Compartilhado? |
|---|---|---|
| Manifest Claude Code | `.claude-plugin/plugin.json` | não |
| Manifest Codex CLI | `.codex-plugin/plugin.json` | não |
| Marketplace catalog (Codex) | `.agents/plugins/marketplace.json` | não |
| **Skills** | `skills/<nome>/SKILL.md` | **sim — Claude Code e Codex leem da mesma pasta** |
| Subagents Claude Code | `agents/<id>.md` | não (formato Claude Code) |
| Subagents Codex | `.agents/<id>/AGENT.md` | não (formato Codex; gerado por sync) |
| Hooks Claude Code | `hooks/hooks.json` | não |
| Hooks Codex | `.codex/hooks.json` | não |
| Instruções projeto | `CLAUDE.md` (PT-BR) + `AGENTS.md` (EN) | parcial |

A descoberta principal — que **`skills/` é compartilhado entre Claude Code e Codex quando empacotado como plugin** — eliminou a necessidade de mirror em `.agents/skills/`. Apenas os manifests e subagents é que precisam de duplicação.

### Comandos de instalação corretos

#### Claude Code

```
/plugin marketplace add VilelaAI/kairos-forge
/plugin install kairos-forge
/reload-plugins
```

#### Codex CLI

```bash
# Codex usa subcomando `plugin marketplace add`. NÃO existe flag `--plugin-dir`,
# e `codex plugin install` NÃO é subcomando da CLI — install acontece na TUI.

# Local (development, a partir do clone)
git clone https://github.com/VilelaAI/kairos-forge.git
cd kairos-forge
codex plugin marketplace add "$(pwd)"   # use absolute path para evitar edge cases
codex                                     # abre a TUI
# Dentro da TUI: /plugin → escolher kairos-forge → instalar

# GitHub (após publicar)
codex plugin marketplace add VilelaAI/kairos-forge
codex
# Dentro da TUI: /plugin → escolher kairos-forge → instalar
```

#### OpenCode

```bash
git clone https://github.com/VilelaAI/kairos-forge.git
# Opção A: path nativo OpenCode
cp -r kairos-forge/skills/* .opencode/skills/
# Opção B: fallback Claude Code
cp -r kairos-forge/skills/* .claude/skills/
```

OpenCode lê `CLAUDE.md` ou `AGENTS.md` automaticamente. Para hooks, instalar [oh-my-opencode](https://github.com/fractalmind-ai/oh-my-opencode).

## Workflow do desenvolvedor

```bash
# 1. Editar canônico
vim agents/marina-frontend.md   # ou skills/<x>/SKILL.md

# 2. Sincronizar mirror Codex de subagents (skills não precisam — são compartilhadas)
python3 scripts/sync-multi-cli.py

# 3. Commitar tudo
git add agents/ skills/ .agents/
git commit -m "docs(marina): adiciona instruções sobre Suspense"
```

Sem o passo 2, usuários do Codex pegam subagents desatualizados. CLAUDE.md raiz documenta isso explicitamente.

Quando alterar **somente skills**, o sync nem é necessário — `skills/` serve aos dois CLIs sem cópia.

## Alternativas consideradas

### A) Apenas Claude Code

Manter posição original (ADR-0001) e ignorar Codex/OpenCode.

**Rejeitado** porque:
- Limita público a usuários Claude Code
- Cria assimetria com kairos-ai PRO (que é multi-CLI)
- Reduz utilidade do Forge como porta de entrada do ecossistema KairOS

### B) Manter três fontes da verdade independentes

Editar `agents/`, `.agents/<id>/AGENT.md`, `.opencode/agents/` separadamente.

**Rejeitado** porque:
- Triplica trabalho de manutenção
- Drift inevitável entre versões
- Bug fix em uma versão pode não chegar nas outras

### C) Codex como fonte da verdade

Inverter — Codex como canônico, Claude Code derivado.

**Rejeitado** porque:
- Claude Code tem ecossistema mais maduro de plugins
- Time KairOS desenvolve majoritariamente em Claude Code
- Codex é adoção crescente mas com features menos completas (sem `Write|Edit` matcher em hooks, etc.)

### D) Detecção de CLI em runtime e adaptação dinâmica

Cada skill detectaria o CLI em uso e se comportaria diferente.

**Rejeitado** parcialmente — só a skill `mobilizar` precisa disso (porque depende de `TeamCreate`, exclusivo Claude Code). Foi implementado especificamente para ela.

## Limitações declaradas

### `/kairos-forge:mobilizar` é Claude Code-exclusivo

Depende de `TeamCreate`, `TaskCreate`, `TaskUpdate`, `SendMessage` — ferramentas nativas do Claude Code com a flag `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

A skill é a mesma `skills/mobilizar/SKILL.md` carregada pelos dois CLIs (porque `skills/` é compartilhada), mas no início ela detecta e orienta:

> "A skill `/kairos-forge:mobilizar` requer Agent Teams nativos do Claude Code e não funciona neste CLI. Use `/kairos-forge:rodar` para execução conversacional sequencial — funciona em qualquer CLI."

### Hook PostToolUse com `Write|Edit` matcher é Claude Code-exclusivo

O Codex CLI suporta hooks mas o sistema de matchers limita a ferramentas Bash. O hook pedagógico do Forge ("arquivo de produção modificado") não funciona no Codex.

`.codex/hooks.json` mantém apenas o `SessionStart` banner.

OpenCode não tem hooks nativos — depende do plugin externo `oh-my-opencode`.

### OpenCode tem instalação manual de skills

OpenCode descobre skills em `.opencode/skills/` ou `.claude/skills/`. O Forge não distribui esses paths, então o usuário OpenCode copia manualmente. README documenta as duas opções.

## Erros corrigidos da v0.4.0 e v0.4.1

A primeira tentativa de adicionar multi-CLI (v0.4.0) tinha **dois erros estruturais** que foram corrigidos na v0.4.1. Em teste real (macOS) na v0.4.1, **três erros adicionais** foram descobertos e corrigidos na v0.4.2.

### v0.4.0 → v0.4.1

#### Erro 1: documentação de flag inexistente

A v0.4.0 documentava `codex --plugin-dir <caminho>`. **Essa flag não existe no Codex CLI.** O comando correto é o subcomando `codex plugin marketplace add`. O erro veio de trasladar uma documentação errada do kairos-ai original.

#### Erro 2: duplicação desnecessária de skills

A v0.4.0 tinha `.agents/skills/` como mirror das skills no formato Codex. **Era desnecessário.** Quando o repo é instalado como plugin do Codex, ele descobre skills em `skills/<nome>/SKILL.md` igual ao Claude Code.

### v0.4.1 → v0.4.2 (descobertos em teste real)

#### Erro 3: `codex plugin install` não existe como subcomando da CLI

Em teste com `codex plugin install kairos-forge@kairos-forge`, o Codex respondeu:

```
error: unrecognized subcommand 'install'
Usage: codex plugin [OPTIONS] <COMMAND>
```

A v0.4.1 documentava esse comando assumindo paralelo ao `/plugin install` do Claude Code. **No Codex, install acontece dentro da TUI** depois do `marketplace add` — abre `codex`, navega até o plugin no menu, instala interativamente.

#### Erro 4: `cp -T` é GNU coreutils-only

O comando de teste rápido sugerido (`cp -rT /tmp/kairos-forge .`) usa a flag `-T` do GNU `cp`, que **não existe no BSD `cp` do macOS**. O substituto compatível com ambos é `cp -R /tmp/kairos-forge/. .` (ponto no final do source) ou `rsync -a /tmp/kairos-forge/ .`.

#### Erro 5: faltava `.claude-plugin/marketplace.json`

A v0.4.1 colocava o marketplace catalog apenas em `.agents/plugins/marketplace.json` (path do Codex). **Para o Claude Code reconhecer o repo como marketplace, o catalog precisa estar em `.claude-plugin/marketplace.json`** — caminho diferente, mesmo conteúdo.

A v0.4.2 mantém **dois marketplace.json idênticos**, um por path-de-CLI:

```
.claude-plugin/marketplace.json    ← Claude Code
.agents/plugins/marketplace.json   ← Codex CLI
```

Quando uma versão é bumpada, ambos precisam ser atualizados juntos.

## Por que skills compartilham mas subagents não

| | Path padrão | Por que compartilha/não? |
|---|---|---|
| Skills | `skills/<nome>/SKILL.md` | Especificação aberta "open agent skills" — ambos os CLIs adotaram o mesmo formato |
| Subagents | `agents/<id>.md` (Claude) / `.agents/<id>/AGENT.md` (Codex) | Formatos historicamente diferentes — Claude Code usa um arquivo flat por agente, Codex usa diretório com `AGENT.md` |

Possível convergência futura: se Anthropic e OpenAI alinharem também o formato de subagent, esse último mirror desaparece e o `sync-multi-cli.py` se torna desnecessário.

## Por que não auto-sync via hook do git

Foi considerado um pre-commit hook que rodasse `sync-multi-cli.py` automaticamente. Decidiu-se por **sync manual** porque:

1. Pre-commit hook adiciona dependência de instalação
2. Esquecer de rodar sync é detectável em CI (uma comparação `agents/` vs `.agents/<id>/AGENT.md` mostraria divergência)
3. Sync rápido (~50ms) — custo de rodar manual é trivial
4. Mantém comportamento previsível e debugável

Em versões futuras pode entrar GitHub Action que valida sync no PR — fica como evolução, não bloqueio.

## Consequências

### Positivas

- Forge fica acessível a usuários Codex CLI e OpenCode sem fork
- Paridade com kairos-ai aumenta consistência do ecossistema KairOS
- Script de sync de ~50 linhas é manutenção barata
- Repo cresce ~45 arquivos (`.agents/<id>/AGENT.md`) mas são gerados, custo de revisão em PR é baixo

### Negativas

- Mais paths para entender no repo (canônico vs gerado)
- Esquecimento de rodar sync gera divergência silenciosa de subagents — mitigado pela documentação no CLAUDE.md raiz e por future GitHub Action
- `mobilizar` segue Claude Code-only — Forge não consegue oferecer paralelismo real em outras CLIs

### Mitigações

- README explica estrutura e workflow de sync
- CLAUDE.md raiz tem nota destacada sobre rodar sync antes de commitar
- ADR documenta decisão para futuros mantenedores
- A revisão v0.4.1 deste ADR documenta os erros da v0.4.0 para que não se repitam

## Revisão futura

Esta decisão será revisitada se:

1. Codex CLI ganhar suporte a `TeamCreate`-like → `mobilizar` pode virar multi-CLI
2. Anthropic + OpenAI alinharem formato de subagent → eliminar `.agents/<id>/AGENT.md`
3. OpenCode mainstream → pode justificar paths nativos próprios
4. Surgir um quarto CLI relevante → avaliar abstração para "N CLIs"
5. GitHub Action de validação de sync for implementada → atualizar ADR
