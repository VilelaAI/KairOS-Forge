#!/usr/bin/env python3
"""sync-multi-cli.py — Sincroniza os canônicos do Claude Code para Codex e Cursor.

Skills (`skills/<nome>/SKILL.md`) são compartilhadas entre Claude Code e Codex
sem necessidade de duplicação — ambos os CLIs leem a mesma pasta quando
empacotados como plugin. Já os SUBAGENTS têm formato distinto, e o Cursor
não tem conceito de plugin — recebe um diretório `.cursor/` completo:

    Claude Code:  agents/<id>.md               (canônico)
    Codex CLI:    .agents/<id>/AGENT.md        (gerado)
                  .codex/agents/<id>.toml      (gerado — role de subagent, ADR-0035)
    Cursor:       .cursor/agents/<id>.md       (gerado, frontmatter adaptado)
                  .cursor/skills/…             (gerado, mirror — Agent Skills padrão)
                  .cursor/rules/kairos-forge.mdc  (gerado — banner alwaysApply)
                  .cursor/scripts/, .cursor/templates/  (gerados — suporte às skills)

Uso:
    python3 scripts/sync-multi-cli.py

Roda este script sempre que mudar arquivos em agents/ ou skills/. O resultado é
commitado no git. Usuário final do Codex/Cursor pega os arquivos prontos.

Transformação de agente para o Codex (ADR-0035):
    - `.agents/<id>/AGENT.md` continua sendo o mirror lido como subagent de sessão;
    - `.codex/agents/<id>.toml` é o que faz `spawn_agent(agent_type: "<id>")`
      funcionar: o Codex resolve roles a partir de arquivos .toml em `<config>/agents/`.
      `description` vira o gatilho de roteamento, o corpo da persona vira
      `developer_instructions`, `model: opus` vira `model_reasoning_effort = "high"`
      (o Codex não tem "opus"; o que aquele campo significava aqui era tier preciso)
      e agente sem ferramenta de escrita na allow-list ganha `shell_tool = false`.

    Sobre a degradação da allow-list: o Codex NÃO aplica `sandbox_mode` a partir de
    um role file (só `developer_instructions`, `model*`, `personality`, `service_tier`,
    `features` e `skills` — estes dois últimos apenas para DESABILITAR). Então o
    read-only do Codex é parcial: `shell_tool = false` tira a execução de comando,
    mas `apply_patch` continua disponível. Para os agentes consultivos a fronteira
    real segue sendo a instrução, como no Cursor — não anuncie mais do que se aplica.

Transformação de agente para o Cursor (ADR-0011):
    - mantém `name`, `description` e o corpo da persona;
    - remove `tools:` (Cursor não tem allow-list) e `model:` (valores não mapeiam);
    - adiciona `readonly: true` quando a allow-list original não tem ferramenta
      de escrita (Write/Edit/NotebookEdit/Bash) — preserva o espírito da allow-list.

NÃO modifica:
    - agents/ e skills/ (canônicos)
    - hooks/hooks.json (Claude Code) — Codex usa .codex/hooks.json
    - .codex-plugin/plugin.json e .agents/plugins/marketplace.json (manuais)
"""
from pathlib import Path
import re
import shutil
import sys


ROOT = Path(__file__).resolve().parent.parent
AGENTS_SRC = ROOT / "agents"
SKILLS_SRC = ROOT / "skills"
CODEX_DIR = ROOT / ".agents"
CURSOR_DIR = ROOT / ".cursor"
PRESERVAR = {"plugins"}  # subdir mantido (marketplace.json fica em .agents/plugins/)

FERRAMENTAS_ESCRITA = {"Write", "Edit", "NotebookEdit", "Bash"}

# Scripts referenciados pelas skills via ${CLAUDE_PLUGIN_ROOT}/scripts/ — o Cursor
# precisa deles ao lado das skills. Copiados se existirem (a lista tolera ausência
# para que o sync funcione em qualquer ponto do histórico).
SCRIPTS_DE_SUPORTE = ["grafo.py", "telemetria.py", "execucao.py", "guardrail.py",
                      "diagnostico.py", "ciclo.py", "contrato.py", "painel.py",
                      "quadro.py"]


def montar_rule(skills: list[str]) -> str:
    """Rule do Cursor com a lista de skills DERIVADA do filesystem.

    Derivar em vez de digitar elimina a classe de bug "lista de skills desatualizada"
    — mesma disciplina que o release.py aplica às contagens.
    """
    lista = ", ".join(skills)   # mobilizar volta à lista: degrada, não recusa (ADR-0035)
    return f"""\
---
description: "Fábrica de software kairos-forge — 71 agentes e 18 skills em PT-BR"
alwaysApply: true
---

🔥 kairos-forge v0.28 ativo (Cursor) — 71 agentes (40 core + 31 apoio em 10 squads).

- As skills da fábrica estão no menu `/` (Agent Skills): {lista}. A skill
  `mobilizar` precisa lançar worker em paralelo, o que o Cursor não expõe: ela
  abre o quadro (`quadro.py`) e executa em série — mesmo rastreio, sem
  paralelismo. Para conversa sequencial simples, `rodar`.
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


def dividir_frontmatter(texto: str) -> tuple[dict, str]:
    """Frontmatter YAML simples (chave: valor) + corpo. Sem dependência externa."""
    linhas = texto.split("\n")
    if not linhas or linhas[0].strip() != "---":
        return {}, texto
    try:
        fim = linhas[1:].index("---") + 1
    except ValueError:
        return {}, texto
    campos = {}
    for linha in linhas[1:fim]:
        if ":" in linha:
            chave, valor = linha.split(":", 1)
            campos[chave.strip()] = valor.strip()
    return campos, "\n".join(linhas[fim + 1:]).strip()


def toml_basico(valor: str) -> str:
    """String TOML multi-linha, escapando o que quebraria o literal."""
    limpo = valor.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return '"""\n' + limpo + '\n"""'


def apelido_de(corpo: str, agent_id: str) -> str:
    """Primeiro nome da persona, do H1 (`# 🛢️ Carlos — DBA` → `Carlos`)."""
    for linha in corpo.split("\n"):
        if linha.startswith("# "):
            titulo = linha[2:].strip()
            for parte in re.split(r"[—–-]", titulo, maxsplit=1)[0].split():
                if parte[:1].isalpha():
                    return parte
    return agent_id.split("-")[0].capitalize()


def gerar_roles_codex():
    """Escreve .codex/agents/<id>.toml — o que torna as 71 personas usáveis no
    `spawn_agent` do Codex (ADR-0035).

    Sem isso o `/mobilizar` no Codex só conseguiria colar a persona no prompt de um
    agente genérico: a persona viraria texto, não papel. Com o role file, o Codex
    resolve `agent_type` e aplica o papel ao filho independentemente de quanto
    histórico foi herdado.
    """
    destino = ROOT / ".codex" / "agents"
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)

    contagem = 0
    for agent_md in sorted(AGENTS_SRC.glob("*.md")):
        campos, corpo = dividir_frontmatter(agent_md.read_text(encoding="utf-8"))
        agent_id = campos.get("name") or agent_md.stem
        descricao = campos.get("description", "")
        ferramentas = {t.strip() for t in campos.get("tools", "").split(",") if t.strip()}
        escreve = bool(ferramentas & FERRAMENTAS_ESCRITA)

        linhas = [
            "# GERADO por scripts/sync-multi-cli.py (kairos-forge) — não edite aqui.",
            f"# Canônico: agents/{agent_md.name}",
            "",
            f'name = "{agent_id}"',
            f"description = {toml_basico(descricao)}",
            f'nickname_candidates = ["{apelido_de(corpo, agent_id)}"]',
        ]
        # `model: opus` no canônico significa tier preciso. O Codex não tem "opus" e
        # o slug de modelo varia por conta — esforço de raciocínio é o que traduz sem
        # inventar nome de modelo que pode não existir do outro lado.
        if campos.get("model") == "opus":
            linhas.append('model_reasoning_effort = "high"')
        linhas += ["", f"developer_instructions = {toml_basico(corpo)}"]
        if ferramentas and not escreve:
            linhas += [
                "",
                "# Allow-list original sem ferramenta de escrita: agente consultivo.",
                "# `shell_tool = false` é a única redução de capacidade que um role",
                "# file do Codex aplica de fato — `apply_patch` continua disponível,",
                "# então a fronteira restante é a instrução, como no Cursor.",
                "[features]",
                "shell_tool = false",
            ]
        (destino / f"{agent_id}.toml").write_text("\n".join(linhas) + "\n", encoding="utf-8")
        contagem += 1
    return contagem


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

    print("🧩 gerando roles de subagent do Codex (.codex/agents/*.toml, ADR-0035)...")
    n_roles = gerar_roles_codex()
    print(f"  ✓ {n_roles} roles — `spawn_agent(agent_type: \"<id>\")` resolve a persona")

    print("🖱️ regenerando .cursor/ (Claude Code → Cursor, ADR-0011)...")
    n_agents, n_skills = sincronizar_cursor()
    print(f"  ✓ {n_agents} subagents adaptados em .cursor/agents/")
    print(f"  ✓ {n_skills} skills espelhadas em .cursor/skills/ + rule, scripts e templates")

    print(f"\n✅ Sincronizado: .agents/ (Codex) e .cursor/ (Cursor)")
    print("\nLembre-se de commitar .agents/ e .cursor/ no git para que usuários de Codex e Cursor peguem os arquivos prontos.")
    print("\nNota: skills/ é compartilhado entre Claude Code e Codex; o Cursor recebe mirror gerado em .cursor/skills/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
