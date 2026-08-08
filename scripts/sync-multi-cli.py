#!/usr/bin/env python3
"""sync-multi-cli.py — Sincroniza os canônicos do Claude Code para Codex, Cursor e Kiro.

Skills (`skills/<nome>/SKILL.md`) são compartilhadas entre Claude Code e Codex
sem necessidade de duplicação — ambos os CLIs leem a mesma pasta quando
empacotados como plugin. Já os SUBAGENTS têm formato distinto, e Cursor e Kiro
não têm conceito de plugin — recebem diretórios completos:

    Claude Code:  agents/<id>.md               (canônico)
    Codex CLI:    .agents/<id>/AGENT.md        (gerado)
    Cursor:       .cursor/agents/<id>.md       (gerado, frontmatter adaptado)
                  .cursor/skills/…             (gerado, mirror — Agent Skills padrão)
                  .cursor/rules/kairos-forge.mdc  (gerado — banner alwaysApply)
                  .cursor/scripts/, .cursor/templates/  (gerados — suporte às skills)
    Kiro CLI:     .kiro/agents/<id>.json       (gerado — config de agente do Kiro)
                  .kiro/skills/…               (gerado, mirror — mesmo SKILL.md)
                  .kiro/steering/kairos-forge.md  (gerado — contexto sempre carregado)
                  .kiro/scripts/, .kiro/templates/  (gerados — suporte às skills)

Uso:
    python3 scripts/sync-multi-cli.py

Roda este script sempre que mudar arquivos em agents/ ou skills/. O resultado é
commitado no git. Usuário final do Codex/Cursor/Kiro pega os arquivos prontos.

Transformação de agente para o Cursor (ADR-0011):
    - mantém `name`, `description` e o corpo da persona;
    - remove `tools:` (Cursor não tem allow-list) e `model:` (valores não mapeiam);
    - adiciona `readonly: true` quando a allow-list original não tem ferramenta
      de escrita (Write/Edit/NotebookEdit/Bash) — preserva o espírito da allow-list.

Transformação de agente para o Kiro (ADR-0035):
    - corpo da persona vira `prompt`; `name` e `description` seguem iguais;
    - `tools:` é TRADUZIDO (Read→fs_read, Bash→execute_bash, …) por scripts/kiro.py,
      que é a mesma tabela usada nos matchers de hook — allow-list de verdade,
      não degradação como no Cursor;
    - `model:` sai (os identificadores do Kiro não mapeiam 1:1);
    - cada config carrega os hooks de telemetria e guardrail, porque no Kiro os
      hooks moram na config do agente, não num arquivo global.

NÃO modifica:
    - agents/ e skills/ (canônicos)
    - hooks/hooks.json (Claude Code) — Codex usa .codex/hooks.json
    - .codex-plugin/plugin.json e .agents/plugins/marketplace.json (manuais)
"""
from pathlib import Path
import json
import shutil
import sys

sys.dont_write_bytecode = True  # não sujar scripts/ com __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kiro  # noqa: E402  — tabela de ferramentas e adaptador de hook (ADR-0035)


ROOT = Path(__file__).resolve().parent.parent
AGENTS_SRC = ROOT / "agents"
SKILLS_SRC = ROOT / "skills"
CODEX_DIR = ROOT / ".agents"
CURSOR_DIR = ROOT / ".cursor"
KIRO_DIR = ROOT / ".kiro"
PRESERVAR = {"plugins"}  # subdir mantido (marketplace.json fica em .agents/plugins/)

FERRAMENTAS_ESCRITA = {"Write", "Edit", "NotebookEdit", "Bash"}

# Versão e contagem citadas nos artefatos gerados para o Kiro. Reescritas pelo
# `release.py bump` a partir do filesystem — não edite à mão.
VERSAO = "0.28"
CONTAGEM = "71 agentes (40 core + 31 apoio em 10 squads)"

# Scripts referenciados pelas skills via ${CLAUDE_PLUGIN_ROOT}/scripts/ — o Cursor
# e o Kiro precisam deles ao lado das skills. Copiados se existirem (a lista tolera
# ausência para que o sync funcione em qualquer ponto do histórico).
SCRIPTS_DE_SUPORTE = ["grafo.py", "telemetria.py", "execucao.py", "guardrail.py",
                      "diagnostico.py", "ciclo.py", "contrato.py", "painel.py",
                      "kiro.py"]


def montar_rule(skills: list[str]) -> str:
    """Rule do Cursor com a lista de skills DERIVADA do filesystem.

    Derivar em vez de digitar elimina a classe de bug "lista de skills desatualizada"
    — mesma disciplina que o release.py aplica às contagens.
    """
    sem_mobilizar = [s for s in skills if s != "mobilizar"]
    lista = ", ".join(sem_mobilizar)
    return f"""\
---
description: "Fábrica de software kairos-forge — 71 agentes e 18 skills em PT-BR"
alwaysApply: true
---

🔥 kairos-forge v0.28 ativo (Cursor) — 71 agentes (40 core + 31 apoio em 10 squads).

- As skills da fábrica estão no menu `/` (Agent Skills): {lista}. A skill
  `mobilizar` requer Agent Teams do Claude Code — no Cursor, use `rodar` (cobre
  o fluxo em modo sequencial).
- As 71 personas são subagents (Laura, Tech Lead, é o ponto de entrada: ela
  analisa a tarefa e decide quem entra). Cada agente responde em primeira
  pessoa e se apresenta pelo nome.
- Resolução de caminhos: quando uma skill referenciar
  `${{CLAUDE_PLUGIN_ROOT}}/<path>`, resolva para `<path>` dentro do diretório
  `.cursor/` onde o kairos-forge foi instalado — ex.: `.cursor/scripts/grafo.py`
  no projeto, ou `~/.cursor/scripts/grafo.py` se a instalação foi global.
- Telemetria (ADR-0021): o Cursor não tem hooks equivalentes aos do Claude Code,
  então `.agents/execucoes/` fica vazio e a dimensão Autonomia do `/auditar`
  pontua 0. Para medir autonomia neste editor, rode os checks no CI do projeto
  (`templates/ci/`).
- Idioma: PT-BR em tudo — mensagens, comentários de código, commits.

> Arquivo GERADO por scripts/sync-multi-cli.py (kairos-forge). Não edite aqui —
> edite os canônicos agents/ e skills/ e rode o sync.
"""


def limpar_subagents_codex():
    """Remove apenas as pastas de subagent em .agents/, preservando outras (plugins/)."""
    if not CODEX_DIR.exists():
        CODEX_DIR.mkdir()
        return
    for item in CODEX_DIR.iterdir():
        if item.is_dir() and item.name not in PRESERVAR:
            shutil.rmtree(item)


def sincronizar_subagents():
    """Copia agents/<id>.md → .agents/<id>/AGENT.md (formato Codex)."""
    contagem = 0
    for agent_md in AGENTS_SRC.glob("*.md"):
        nome = agent_md.stem
        target_dir = CODEX_DIR / nome
        target_dir.mkdir()
        shutil.copy2(agent_md, target_dir / "AGENT.md")
        contagem += 1
    return contagem


def transformar_agente_cursor(texto: str) -> str:
    """Converte frontmatter Claude Code → Cursor (ADR-0011)."""
    linhas = texto.split("\n")
    if not linhas or linhas[0].strip() != "---":
        return texto  # sem frontmatter — copia como está
    try:
        fim = linhas[1:].index("---") + 1
    except ValueError:
        return texto
    frontmatter, corpo = linhas[1:fim], linhas[fim + 1:]

    mantidas, tools = [], ""
    for linha in frontmatter:
        chave = linha.split(":", 1)[0].strip()
        if chave == "tools":
            tools = linha.split(":", 1)[1]
        elif chave == "model":
            continue  # valores do Cursor (inherit/fast) não mapeiam
        else:
            mantidas.append(linha)

    ferramentas = {t.strip() for t in tools.split(",") if t.strip()}
    if tools and not (ferramentas & FERRAMENTAS_ESCRITA):
        mantidas.append("readonly: true")

    return "\n".join(["---", *mantidas, "---", *corpo])


def sincronizar_cursor():
    """Regenera .cursor/ completo: agents adaptados, skills espelhadas, rule, suporte."""
    if CURSOR_DIR.exists():
        shutil.rmtree(CURSOR_DIR)

    # 1. Subagents (frontmatter adaptado)
    (CURSOR_DIR / "agents").mkdir(parents=True)
    n_agents = 0
    for agent_md in sorted(AGENTS_SRC.glob("*.md")):
        destino = CURSOR_DIR / "agents" / agent_md.name
        destino.write_text(transformar_agente_cursor(agent_md.read_text(encoding="utf-8")),
                           encoding="utf-8")
        n_agents += 1

    # 2. Skills (mirror — mesmo formato Agent Skills)
    shutil.copytree(SKILLS_SRC, CURSOR_DIR / "skills")
    n_skills = sum(1 for _ in (CURSOR_DIR / "skills").glob("*/SKILL.md"))

    # 3. Rule alwaysApply (papel do banner de SessionStart) — lista derivada
    nomes_skills = sorted(p.parent.name for p in SKILLS_SRC.glob("*/SKILL.md"))
    (CURSOR_DIR / "rules").mkdir()
    (CURSOR_DIR / "rules" / "kairos-forge.mdc").write_text(
        montar_rule(nomes_skills), encoding="utf-8"
    )

    # 4. Suporte referenciado pelas skills via ${CLAUDE_PLUGIN_ROOT}
    (CURSOR_DIR / "scripts").mkdir()
    for nome in SCRIPTS_DE_SUPORTE:
        origem = ROOT / "scripts" / nome
        if origem.exists():
            shutil.copy2(origem, CURSOR_DIR / "scripts" / nome)
    shutil.copytree(ROOT / "templates", CURSOR_DIR / "templates")

    return n_agents, n_skills


# --- Kiro CLI / Kiro Crew (ADR-0035) -------------------------------------------------

# No Kiro os hooks moram na config do AGENTE, não num arquivo global, e o payload
# tem formato próprio — scripts/kiro.py traduz nos dois sentidos. `$KF` resolve a
# instalação com a mesma precedência que o resto do Kiro usa: workspace (.kiro/)
# na frente de global (~/.kiro/).
PREFIXO_HOOK = (
    'KF=.kiro/scripts; [ -f "$KF/kiro.py" ] || KF="$HOME/.kiro/scripts"; '
    'python3 "$KF/kiro.py" adaptar'
)
# Telemetria falha aberta (observabilidade quebrada não trava sessão); guardrail
# falha fechada e propaga o exit 2 — mesma divisão do hooks/hooks.json.
TELEMETRIA = "2>/dev/null || true"


def montar_steering(skills: list[str], versao: str, contagem: str) -> str:
    """Steering do Kiro — a CLI carrega tudo de .kiro/steering/ em toda sessão."""
    sem_mobilizar = ", ".join(s for s in skills if s != "mobilizar")
    return f"""\
---
inclusion: always
---

🔥 kairos-forge v{versao} ativo (Kiro) — {contagem}.

- Skills da fábrica em `.kiro/skills/`: {sem_mobilizar}. A skill `mobilizar`
  precisa de Agent Teams do Claude Code — aqui use `rodar` (mesmo fluxo, modo
  sequencial).
- As personas são configs de agente em `.kiro/agents/<id>.json`. Laura
  (`laura-tech-lead`) é o ponto de entrada: ela analisa a tarefa e decide quem
  entra. Cada agente responde em primeira pessoa e se apresenta pelo nome.
  No Kiro Crew, cada uma roda como `kiro-cli acp --agent <id>`.
- Resolução de caminhos: quando uma skill referenciar `${{CLAUDE_PLUGIN_ROOT}}/<path>`,
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
"""


def hooks_kiro(banner: str) -> dict:
    """Espelha hooks/hooks.json nos nomes de evento e de ferramenta do Kiro.

    Os matchers usam os nomes canônicos do Kiro vindos de kiro.py — a mesma
    tabela que traduz a allow-list. Uma entrada por ferramenta em vez de
    alternância `a|b`: o suporte a regex no matcher do Kiro não está verificado,
    e matcher que não casa é guardrail que não guarda.
    """
    seguro = banner.replace("'", "'\\''")
    tele = lambda acao: f"{PREFIXO_HOOK} execucao.py {acao} {TELEMETRIA}"  # noqa: E731
    return {
        "agentSpawn": [
            {"command": f"echo '{seguro}'"},
            {"command": tele("inicio")},
        ],
        "userPromptSubmit": [{"command": tele("prompt")}],
        "preToolUse": [
            {"matcher": "execute_bash", "command": f"{PREFIXO_HOOK} guardrail.py comando"},
            {"matcher": "fs_write", "command": f"{PREFIXO_HOOK} guardrail.py escrita"},
        ],
        "postToolUse": [
            {"matcher": "fs_write", "command": tele("ferramenta")},
            {"matcher": "execute_bash", "command": tele("ferramenta")},
            {"matcher": "fs_write", "command": tele("alerta")},
            {"matcher": "execute_bash", "command": tele("alerta")},
            {"matcher": "fs_write", "command": f"{PREFIXO_HOOK} guardrail.py spec"},
            {"matcher": "fs_write", "command": f"{PREFIXO_HOOK} guardrail.py contrato"},
        ],
        "stop": [{"command": tele("fim")}],
    }


def transformar_agente_kiro(texto: str, agente_id: str, hooks: dict) -> dict:
    """Frontmatter Claude Code + corpo → config de agente do Kiro (ADR-0035)."""
    linhas = texto.split("\n")
    frontmatter, corpo = [], linhas
    if linhas and linhas[0].strip() == "---":
        try:
            fim = linhas[1:].index("---") + 1
            frontmatter, corpo = linhas[1:fim], linhas[fim + 1:]
        except ValueError:
            pass

    campos = {}
    for linha in frontmatter:
        if ":" in linha:
            chave, valor = linha.split(":", 1)
            campos[chave.strip()] = valor.strip()

    # KeyError proposital em ferramenta sem tradução: melhor o sync quebrar do que
    # gerar um agente com allow-list menor do que a que o canônico declara.
    tools, permitidas = kiro.traduzir_ferramentas(campos.get("tools", ""))

    # `model:` não vem: os identificadores do Kiro não mapeiam 1:1 com opus/sonnet.
    return {
        "name": campos.get("name", agente_id),
        "description": campos.get("description", ""),
        "prompt": "\n".join(corpo).strip(),
        "tools": tools,
        "allowedTools": permitidas,
        "hooks": hooks,
    }


def sincronizar_kiro(banner: str, versao: str, contagem: str):
    """Regenera .kiro/ completo: configs de agente, skills, steering, suporte."""
    if KIRO_DIR.exists():
        shutil.rmtree(KIRO_DIR)

    hooks = hooks_kiro(banner)
    (KIRO_DIR / "agents").mkdir(parents=True)
    n_agents = 0
    for agent_md in sorted(AGENTS_SRC.glob("*.md")):
        cfg = transformar_agente_kiro(
            agent_md.read_text(encoding="utf-8"), agent_md.stem, hooks
        )
        (KIRO_DIR / "agents" / f"{agent_md.stem}.json").write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        n_agents += 1

    shutil.copytree(SKILLS_SRC, KIRO_DIR / "skills")
    n_skills = sum(1 for _ in (KIRO_DIR / "skills").glob("*/SKILL.md"))

    nomes_skills = sorted(p.parent.name for p in SKILLS_SRC.glob("*/SKILL.md"))
    (KIRO_DIR / "steering").mkdir()
    (KIRO_DIR / "steering" / "kairos-forge.md").write_text(
        montar_steering(nomes_skills, versao, contagem), encoding="utf-8"
    )

    (KIRO_DIR / "scripts").mkdir()
    for nome in SCRIPTS_DE_SUPORTE:
        origem = ROOT / "scripts" / nome
        if origem.exists():
            shutil.copy2(origem, KIRO_DIR / "scripts" / nome)
    shutil.copytree(ROOT / "templates", KIRO_DIR / "templates")

    return n_agents, n_skills


def main() -> int:
    if not AGENTS_SRC.exists():
        print(f"❌ agents/ não encontrado em {ROOT}", file=sys.stderr)
        return 1

    print(f"📂 root: {ROOT}")
    print("🧹 limpando subagents antigos em .agents/ (preservando plugins/)...")
    limpar_subagents_codex()

    print("👥 sincronizando subagents (Claude Code → Codex)...")
    n = sincronizar_subagents()
    print(f"  ✓ {n} subagents copiados como .agents/<id>/AGENT.md")

    print("🖱️ regenerando .cursor/ (Claude Code → Cursor, ADR-0011)...")
    n_agents, n_skills = sincronizar_cursor()
    print(f"  ✓ {n_agents} subagents adaptados em .cursor/agents/")
    print(f"  ✓ {n_skills} skills espelhadas em .cursor/skills/ + rule, scripts e templates")

    print("🤖 regenerando .kiro/ (Claude Code → Kiro CLI, ADR-0035)...")
    nomes_skills = sorted(p.parent.name for p in SKILLS_SRC.glob("*/SKILL.md"))
    banner = (f"🔥 kairos-forge v{VERSAO} ativo (Kiro) — {CONTAGEM} | "
              f"{len(nomes_skills)} skills: {' '.join(nomes_skills)} | "
              "mobilizar requer Claude Code com TeamCreate")
    try:
        k_agents, k_skills = sincronizar_kiro(banner, VERSAO, CONTAGEM)
    except KeyError as e:
        print(f"❌ ferramenta sem tradução para o Kiro: {e} — "
              "adicione em scripts/kiro.py:FERRAMENTAS", file=sys.stderr)
        return 1
    print(f"  ✓ {k_agents} configs de agente em .kiro/agents/ (allow-list traduzida)")
    print(f"  ✓ {k_skills} skills espelhadas em .kiro/skills/ + steering, scripts e templates")

    print("\n✅ Sincronizado: .agents/ (Codex), .cursor/ (Cursor) e .kiro/ (Kiro)")
    print("\nLembre-se de commitar .agents/, .cursor/ e .kiro/ no git para que usuários de Codex, Cursor e Kiro peguem os arquivos prontos.")
    print("\nNota: skills/ é compartilhado entre Claude Code e Codex; Cursor e Kiro recebem mirror gerado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
