#!/usr/bin/env python3
"""sync-multi-cli.py — Sincroniza os canônicos do Claude Code para Codex e Cursor.

Skills (`skills/<nome>/SKILL.md`) são compartilhadas entre Claude Code e Codex
sem necessidade de duplicação — ambos os CLIs leem a mesma pasta quando
empacotados como plugin. Já os SUBAGENTS têm formato distinto, e o Cursor
não tem conceito de plugin — recebe um diretório `.cursor/` completo:

    Claude Code:  agents/<id>.md               (canônico)
    Codex CLI:    .agents/<id>/AGENT.md        (gerado)
                  .codex/agents/<id>.toml      (gerado — role de subagent, ADR-0035)
    OpenCode:     .opencode/agent/<id>.md      (gerado — subagent delegável, ADR-0035)
    Cursor:       .cursor/agents/<id>.md       (gerado, frontmatter adaptado)
                  .cursor/skills/…             (gerado, mirror — Agent Skills padrão)
                  .cursor/rules/kairos-forge.mdc  (gerado — banner alwaysApply)
                  .cursor/scripts/, .cursor/templates/  (gerados — suporte às skills)
    Catálogo:     .claude-plugin/ativos.manifest.json  (gerado — manifesto de
                  ativos de IA por agente/skill, direção do ADR-0032)

Uso:
    python3 scripts/sync-multi-cli.py                      # regenera tudo (default)
    python3 scripts/sync-multi-cli.py instalar --cli codex  # instala as personas no CLI
    python3 scripts/sync-multi-cli.py instalar --cli todos --escopo global --dry-run

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

Transformação de agente para o OpenCode (ADR-0035):
    - `.opencode/agent/<id>.md` com `mode: subagent` — sem isso a persona carrega, mas
      a ferramenta `task` não consegue delegar para ela;
    - a allow-list vira `permission`, que no OpenCode é **enforced de verdade**:
      `edit: deny` para quem não tem Write/Edit no canônico, `bash: deny` para quem não
      tem Bash. É a tradução mais fiel dos quatro CLIs — mais até que o Codex, onde
      `apply_patch` sobrevive a qualquer redução;
    - `task: deny` em todos: decompor é da Laura. Sub-time dentro de teammate é como o
      file ownership vira ficção (mesma razão do `max_depth = 1` do Codex).

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
import argparse
import json
import os
import re
import shutil
import sys


ROOT = Path(__file__).resolve().parent.parent
AGENTS_SRC = ROOT / "agents"
SKILLS_SRC = ROOT / "skills"
CODEX_DIR = ROOT / ".agents"
CURSOR_DIR = ROOT / ".cursor"
PLUGIN_JSON = ROOT / ".claude-plugin" / "plugin.json"
MANIFESTO_ATIVOS = ROOT / ".claude-plugin" / "ativos.manifest.json"
PRESERVAR = {"plugins"}  # subdir mantido (marketplace.json fica em .agents/plugins/)

FERRAMENTAS_ESCRITA = {"Write", "Edit", "NotebookEdit", "Bash"}

# Assinatura dos arquivos que este script gera. O `instalar` depende dela para uma
# distinção que importa: arquivo com a marca é nosso e pode ser sobrescrito; arquivo
# sem a marca é do usuário e é PRESERVADO, mesmo que o nome coincida. Sem isso, um
# agente próprio chamado `carlos-dba.md` seria silenciosamente destruído por um sync.
MARCA_GERADO = "GERADO por scripts/sync-multi-cli.py (kairos-forge)"

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
  `mobilizar` roda aqui: o agente principal orquestra os subagents em paralelo
  e o `quadro.py` guarda dependências, posse e contagem. Descreva a onda inteira
  de uma vez — uma tarefa por vez faz o Cursor serializar.
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
            f"# {MARCA_GERADO} — não edite aqui.",
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


def gerar_agentes_opencode():
    """Escreve .opencode/agent/<id>.md — subagents delegáveis pela tool `task` (ADR-0035).

    O OpenCode varre `{agent,agents}/**/*.md` no diretório de config e só oferece à tool
    `task` os que declaram `mode: subagent`. Copiar `agents/` cru (o que a doc mandava
    fazer até aqui) carrega a persona mas não a torna delegável — e sem delegação não há
    onda paralela.
    """
    destino = ROOT / ".opencode" / "agent"
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)

    contagem = 0
    for agent_md in sorted(AGENTS_SRC.glob("*.md")):
        campos, corpo = dividir_frontmatter(agent_md.read_text(encoding="utf-8"))
        agent_id = campos.get("name") or agent_md.stem
        ferramentas = {t.strip() for t in campos.get("tools", "").split(",") if t.strip()}
        # Sem allow-list declarada, herda tudo — não invente restrição que o canônico não pede.
        edita = (not ferramentas) or bool(ferramentas & {"Write", "Edit", "NotebookEdit"})
        shell = (not ferramentas) or ("Bash" in ferramentas)

        frente = [
            "---",
            f"name: {agent_id}",
            f"description: {json.dumps(campos.get('description', ''), ensure_ascii=False)}",
            "mode: subagent",
            "permission:",
            f"  edit: {'allow' if edita else 'deny'}",
            f"  bash: {'allow' if shell else 'deny'}",
            "  task: deny",   # decompor é da Laura, não do teammate
            "---",
            "",
            f"<!-- {MARCA_GERADO} — não edite aqui. Canônico: agents/{agent_md.name} -->",
            "",
        ]
        (destino / f"{agent_id}.md").write_text("\n".join(frente) + corpo + "\n", encoding="utf-8")
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

    marca = f"\n<!-- {MARCA_GERADO} — não edite aqui. -->\n"
    return "\n".join(["---", *mantidas, "---", marca, *corpo])


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


def extrair_frontmatter(texto: str) -> dict[str, str]:
    """Frontmatter YAML simples (chave: valor por linha) — mesmo estilo do
    check-agent-security.py; sem dependência de PyYAML de propósito."""
    linhas = texto.split("\n")
    if not linhas or linhas[0].strip() != "---":
        return {}
    try:
        fim = linhas[1:].index("---") + 1
    except ValueError:
        return {}
    campos: dict[str, str] = {}
    for linha in linhas[1:fim]:
        if ":" in linha and not linha.lstrip().startswith("#"):
            chave, _, valor = linha.partition(":")
            campos[chave.strip()] = valor.strip()
    return campos


# Campos admitidos no metadata de cada ativo: identidade + permissões declaradas.
# Nunca corpo de prompt, nunca dado pessoal — o manifesto alimenta um catálogo
# externo e só carrega o que os canônicos já declaram publicamente.
METADATA_PERMITIDA = {"tools", "descricao", "time", "squad", "model"}


def gerar_manifesto_ativos() -> tuple[int, int]:
    """Consolida agentes e skills em .claude-plugin/ativos.manifest.json.

    É a direção adotada no ADR-0032 — catálogo como estrutura de dados gerada
    pelo sync, nunca mantida à mão. Cada ativo carrega identidade (`chave`,
    `versao`, `origem`) e a allow-list de tools declarada no canônico.
    Determinístico: ordenação estável por (tipoAtivo, chave), tools na ordem
    declarada, versão lida do plugin.json.
    """
    versao = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
    ativos = []

    for agent_md in sorted(AGENTS_SRC.glob("*.md")):
        texto = agent_md.read_text(encoding="utf-8")
        fm = extrair_frontmatter(texto)
        tools = [t.strip() for t in fm.get("tools", "").split(",") if t.strip()]
        metadata: dict = {"tools": tools, "descricao": fm.get("description", "")}
        m = re.search(r"\*\*Time:\*\*\s*(.+)", texto)
        if m:
            metadata["time"] = m.group(1).strip()
            if metadata["time"].startswith("Apoio · "):
                metadata["squad"] = metadata["time"].removeprefix("Apoio · ")
        if fm.get("model"):
            metadata["model"] = fm["model"]
        ativos.append({
            "tipoAtivo": "agente",
            "chave": agent_md.stem,
            "versao": versao,
            "origem": "in_house",
            "metadata": metadata,
        })

    for skill_md in sorted(SKILLS_SRC.glob("*/SKILL.md")):
        fm = extrair_frontmatter(skill_md.read_text(encoding="utf-8"))
        ativos.append({
            "tipoAtivo": "skill",
            "chave": skill_md.parent.name,
            "versao": versao,
            "origem": "in_house",
            # Skills não declaram allow-list própria — rodam com as tools de
            # quem as invoca. Lista vazia = nada declarado (derivado, não inventado).
            "metadata": {"tools": [], "descricao": fm.get("description", "")},
        })

    ativos.sort(key=lambda a: (a["tipoAtivo"], a["chave"]))
    manifesto = {"geradoPor": "sync-multi-cli", "versaoPlugin": versao, "ativos": ativos}
    MANIFESTO_ATIVOS.write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n_agentes = sum(1 for a in ativos if a["tipoAtivo"] == "agente")
    return n_agentes, len(ativos) - n_agentes


def validar_manifesto() -> list[str]:
    """Auto-teste barato: recarrega o manifesto gerado e confere shape e contagens
    contra o filesystem — mesma disciplina do release.py com as contagens."""
    problemas: list[str] = []
    try:
        manifesto = json.loads(MANIFESTO_ATIVOS.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"{MANIFESTO_ATIVOS.name}: JSON inválido — {e}"]

    if set(manifesto) != {"geradoPor", "versaoPlugin", "ativos"}:
        problemas.append(f"{MANIFESTO_ATIVOS.name}: chaves de topo fora do contrato")

    vistos: set[tuple] = set()
    n_por_tipo = {"agente": 0, "skill": 0}
    for ativo in manifesto.get("ativos", []):
        tipo, chave = ativo.get("tipoAtivo"), ativo.get("chave")
        if tipo not in n_por_tipo:
            problemas.append(f"ativo '{chave}': tipoAtivo '{tipo}' inválido")
            continue
        n_por_tipo[tipo] += 1
        if (tipo, chave) in vistos:
            problemas.append(f"ativo '{chave}': duplicado")
        vistos.add((tipo, chave))
        if not chave or ativo.get("versao") != manifesto.get("versaoPlugin") \
                or ativo.get("origem") != "in_house":
            problemas.append(f"ativo '{chave}': chave/versao/origem fora do contrato")
        metadata = ativo.get("metadata", {})
        if not isinstance(metadata.get("tools"), list):
            problemas.append(f"ativo '{chave}': metadata.tools ausente ou não-lista")
        elif tipo == "agente" and not metadata["tools"]:
            problemas.append(f"agente '{chave}': allow-list vazia (regra 4 do CLAUDE.md)")
        extras = set(metadata) - METADATA_PERMITIDA
        if extras:
            problemas.append(f"ativo '{chave}': metadata com campo(s) fora do "
                             f"admitido: {sorted(extras)}")

    esperado = {"agente": len(list(AGENTS_SRC.glob("*.md"))),
                "skill": len(list(SKILLS_SRC.glob("*/SKILL.md")))}
    for tipo, qtd in esperado.items():
        if n_por_tipo[tipo] != qtd:
            problemas.append(f"manifesto tem {n_por_tipo[tipo]} {tipo}(s), "
                             f"filesystem tem {qtd}")
    return problemas


# --- instalação nos CLIs (ADR-0035) --------------------------------------------------
# Codex e OpenCode descobrem subagents no diretório de config DELES, não no do plugin.
# Até aqui isso era um `cp` no README — passo manual, fácil de esquecer e de errar o
# caminho, e o sintoma (a persona não resolve) não aponta para a causa.
ALVOS = {
    "codex": {
        "origem": ".codex/agents", "padrao": "*.toml",
        "projeto": ".codex/agents", "global": "~/.codex/agents",
        "nota": "`spawn_agent(agent_type: \"<id>\")` passa a resolver a persona",
    },
    "opencode": {
        "origem": ".opencode/agent", "padrao": "*.md",
        "projeto": ".opencode/agent", "global": None,   # XDG — resolvido em destino_de()
        "nota": "`task(subagent_type: \"<id>\")` passa a delegar com permission enforced",
    },
    "cursor": {
        "origem": ".cursor/agents", "padrao": "*.md",
        "projeto": ".cursor/agents", "global": "~/.cursor/agents",
        "nota": "os subagents aparecem para o agente principal orquestrar",
    },
}


def destino_de(cli: str, escopo: str) -> Path:
    if escopo == "projeto":
        return Path.cwd() / ALVOS[cli]["projeto"]
    if cli == "opencode":
        # OpenCode segue XDG: $XDG_CONFIG_HOME/opencode, com ~/.config de fallback.
        base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
        return Path(base) / "opencode" / "agent"
    return Path(ALVOS[cli]["global"]).expanduser()


def instalar(cli: str, escopo: str, destino: Path | None, dry_run: bool) -> int:
    alvo = ALVOS[cli]
    origem = ROOT / alvo["origem"]
    if not origem.is_dir():
        print(f"❌ {alvo['origem']} não existe — rode o sync primeiro.", file=sys.stderr)
        return 1
    arquivos = sorted(origem.glob(alvo["padrao"]))
    if not arquivos:
        print(f"❌ nenhum arquivo em {alvo['origem']} — rode o sync primeiro.", file=sys.stderr)
        return 1

    pasta = destino or destino_de(cli, escopo)
    rotulo = "simulação" if dry_run else "instalação"
    print(f"📦 {cli} ({escopo}) → {pasta}  [{rotulo}]")

    novos = atualizados = iguais = 0
    preservados: list[str] = []
    if not dry_run:
        pasta.mkdir(parents=True, exist_ok=True)

    esperados = set()
    for arq in arquivos:
        esperados.add(arq.name)
        alvo_arq = pasta / arq.name
        conteudo = arq.read_bytes()
        if not alvo_arq.exists():
            novos += 1
        else:
            atual = alvo_arq.read_bytes()
            if atual == conteudo:
                iguais += 1
                continue
            # Nome coincide mas o arquivo não é nosso: é do usuário. Não toque.
            if MARCA_GERADO not in atual.decode("utf-8", errors="replace"):
                preservados.append(arq.name)
                continue
            atualizados += 1
        if not dry_run:
            alvo_arq.write_bytes(conteudo)

    # Persona renomeada/removida no canônico deixa um órfão que ainda casa em
    # `agent_type` — só removemos o que carrega a nossa marca.
    removidos = 0
    if pasta.is_dir():
        for existente in sorted(pasta.glob(alvo["padrao"])):
            if existente.name in esperados:
                continue
            if MARCA_GERADO in existente.read_text(encoding="utf-8", errors="replace"):
                removidos += 1
                if not dry_run:
                    existente.unlink()

    partes = [f"{novos} novo(s)", f"{atualizados} atualizado(s)", f"{iguais} inalterado(s)"]
    if removidos:
        partes.append(f"{removidos} órfão(s) removido(s)")
    print(f"  ✓ {' · '.join(partes)}")
    if preservados:
        print(f"  ⚠️  {len(preservados)} arquivo(s) SEUS preservados (nome coincide, "
              f"conteúdo não é gerado): {', '.join(preservados[:5])}"
              + ("…" if len(preservados) > 5 else ""))
        print("      Renomeie o seu ou o nosso — enquanto os dois disputam o nome, "
              "o CLI resolve um só.")
    if not dry_run and (novos or atualizados or removidos):
        print(f"  → {alvo['nota']}")
    return 0


def sincronizar_tudo() -> int:
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

    print("🐙 gerando subagents do OpenCode (.opencode/agent/*.md, ADR-0035)...")
    n_oc = gerar_agentes_opencode()
    print(f"  ✓ {n_oc} subagents — `task(subagent_type: \"<id>\")` delega com permission enforced")

    print("🖱️ regenerando .cursor/ (Claude Code → Cursor, ADR-0011)...")
    n_agents, n_skills = sincronizar_cursor()
    print(f"  ✓ {n_agents} subagents adaptados em .cursor/agents/")
    print(f"  ✓ {n_skills} skills espelhadas em .cursor/skills/ + rule, scripts e templates")

    print("🗂️ gerando manifesto de ativos de IA (ADR-0032)...")
    n_ativos_ag, n_ativos_sk = gerar_manifesto_ativos()
    problemas = validar_manifesto()
    if problemas:
        print(f"❌ manifesto de ativos inconsistente ({len(problemas)} problema(s)):",
              file=sys.stderr)
        for p in problemas:
            print(f"  ✗ {p}", file=sys.stderr)
        return 1
    print(f"  ✓ {n_ativos_ag} agentes + {n_ativos_sk} skills em "
          f"{MANIFESTO_ATIVOS.relative_to(ROOT)}")

    print(f"\n✅ Sincronizado: .agents/ (Codex), .cursor/ (Cursor) e manifesto de ativos")
    print("\nLembre-se de commitar .agents/, .cursor/ e .claude-plugin/ativos.manifest.json no git para que usuários de Codex e Cursor peguem os arquivos prontos.")
    print("\nNota: skills/ é compartilhado entre Claude Code e Codex; o Cursor recebe mirror gerado em .cursor/skills/.")
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if not argv:                       # comportamento default: o sync, como sempre
        return sincronizar_tudo()

    ap = argparse.ArgumentParser(prog="sync-multi-cli.py",
                                 description="Sincroniza e instala os canônicos por CLI.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync", help="regenera .agents/, .codex/, .opencode/, .cursor/ (default)")

    p = sub.add_parser("instalar", help="copia as personas para o diretório do CLI")
    p.add_argument("--cli", required=True, choices=[*ALVOS, "todos"])
    p.add_argument("--escopo", default="projeto", choices=["projeto", "global"])
    p.add_argument("--destino", type=Path, default=None,
                   help="sobrescreve o diretório de destino (implica um --cli só)")
    p.add_argument("--dry-run", action="store_true", help="mostra o que faria")

    a = ap.parse_args(argv)
    if a.cmd == "sync":
        return sincronizar_tudo()

    clis = list(ALVOS) if a.cli == "todos" else [a.cli]
    if a.destino and len(clis) > 1:
        print("❌ --destino exige um --cli específico.", file=sys.stderr)
        return 1
    codigo = 0
    for cli in clis:
        codigo |= instalar(cli, a.escopo, a.destino, a.dry_run)
    if a.dry_run:
        print("\n(simulação — nada foi escrito; repita sem --dry-run para instalar)")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
