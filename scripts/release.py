#!/usr/bin/env python3
"""release.py — bump de versão e verificação de consistência do kairos-forge.

As contagens (agentes, times, squads, skills) são CALCULADAS do filesystem —
nunca digitadas à mão. Isso elimina a classe de bug "contagem desatualizada".

Uso:
  python3 scripts/release.py check         # verifica consistência (usado no CI)
  python3 scripts/release.py bump 0.14.0   # injeta versão+contagens, roda os
                                           # dois syncs e espelha em plugin/

Só stdlib — sem dependências, igual ao grafo.py.
"""

import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# O que é espelhado root → plugin/ (diretórios inteiros e arquivos avulsos).
DIRS_ESPELHADOS = [
    "agents", "skills", "templates", "hooks", ".codex", ".codex-plugin",
    "scripts", "docs", "hermes",
]
ARQUIVOS_ESPELHADOS = ["CLAUDE.md", "AGENTS.md", ".claude-plugin/plugin.json"]
# Diferem por desenho entre root e plugin/ — nunca copiar nem comparar.
EXCECOES_ESPELHO = {"docs/adr/0004-multi-cli.md"}
# Gerados pelo sync — paridade é verificada, cópia é via sync de cada lado.
DIRS_GERADOS = [".agents", ".cursor"]


def derivar():
    """Extrai as contagens reais do filesystem."""
    agentes = sorted(p.stem for p in (RAIZ / "agents").glob("*.md"))
    total = len(agentes)

    yaml_texto = (RAIZ / "templates/squad-fabrica.yaml").read_text(encoding="utf-8")
    bloco_times = re.search(r"\n  times:\n(.*?)\n  \w", yaml_texto, re.S)
    if not bloco_times:
        sys.exit("erro: bloco 'times:' não encontrado no squad-fabrica.yaml")
    bloco = bloco_times.group(1)
    times_core = len(re.findall(r"- nome:", bloco))
    ids_core = []
    for lista in re.findall(r"agentes: \[([^\]]+)\]", bloco):
        ids_core += [a.strip() for a in lista.split(",")]
    ids_core = sorted(set(ids_core))

    squads = set()
    apoio_arquivos = sorted((RAIZ / "agents").glob("apoio-*.md"))
    for p in apoio_arquivos:
        m = re.search(r"\*\*Time:\*\* Apoio · (.+)", p.read_text(encoding="utf-8"))
        if m:
            squads.add(m.group(1).strip())

    skills = sorted(p.parent.name for p in (RAIZ / "skills").glob("*/SKILL.md"))

    n = {
        "total": total,
        "core": len(ids_core),
        "apoio": total - len(ids_core),
        "times_core": times_core,
        "squads": len(squads),
        "times_total": times_core + len(squads),
        "skills": len(skills),
        "nomes_skills": skills,
        "ids_agentes": agentes,
        "ids_core": ids_core,
        "qtd_arquivos_apoio": len(apoio_arquivos),
    }

    # Sanidade: o YAML e o filesystem precisam contar a mesma história.
    erros = []
    for aid in ids_core:
        if aid not in agentes:
            erros.append(f"squad-fabrica.yaml cita '{aid}' mas agents/{aid}.md não existe")
        if aid.startswith("apoio-"):
            erros.append(f"'{aid}' é apoio mas está listado como core no YAML")
    if n["apoio"] != n["qtd_arquivos_apoio"]:
        erros.append(
            f"apoio derivado ({n['apoio']} = {total} total − {n['core']} core) difere da "
            f"contagem de agents/apoio-*.md ({n['qtd_arquivos_apoio']}) — "
            "agente core fora do YAML ou apoio sem prefixo apoio-?"
        )
    if erros:
        for e in erros:
            print(f"  ✗ {e}")
        sys.exit(1)
    return n


def padroes(n, versao):
    """(arquivo, [(regex, substituto)]) — todo número citado em docs/manifests."""
    v_curta = ".".join(versao.split(".")[:2])  # 0.14.0 → banner "v0.14"
    t, c, a, sq, sk = n["total"], n["core"], n["apoio"], n["squads"], n["skills"]
    tt, tc = n["times_total"], n["times_core"]
    contagem_parens = f"{t} agentes ({c} core + {a} apoio em {sq} squads)"

    return [
        (".claude-plugin/plugin.json", [
            (r'"version": "\d+\.\d+\.\d+"', f'"version": "{versao}"'),
            (r"\d+ agentes em \d+ times — \d+ core", f"{t} agentes em {tt} times — {c} core"),
            (r"e \d+ de apoio em \d+ squads", f"e {a} de apoio em {sq} squads"),
            (r"\d+ skills:", f"{sk} skills:"),
        ]),
        (".codex-plugin/plugin.json", [
            (r'"version": "\d+\.\d+\.\d+"', f'"version": "{versao}"'),
            (r"\d+ agentes em \d+ times — \d+ core", f"{t} agentes em {tt} times — {c} core"),
            (r"e \d+ de apoio em \d+ squads", f"e {a} de apoio em {sq} squads"),
            (r"\d+ skills:", f"{sk} skills:"),
        ]),
        (".claude-plugin/marketplace.json", [
            (r'"version": "\d+\.\d+\.\d+"', f'"version": "{versao}"'),
            (r"\d+ agentes \(\d+ core \+ \d+ apoio\)", f"{t} agentes ({c} core + {a} apoio)"),
            (r"\d+ skills cobrindo", f"{sk} skills cobrindo"),
        ]),
        ("hooks/hooks.json", [
            (r"v\d+\.\d+ ativo", f"v{v_curta} ativo"),
            (r"\d+ agentes \(\d+ core \+ \d+ apoio em \d+ squads\)", contagem_parens),
            (r"\d+ skills:", f"{sk} skills:"),
        ]),
        (".codex/hooks.json", [
            (r"v\d+\.\d+ ativo", f"v{v_curta} ativo"),
            (r"\d+ agentes \(\d+ core \+ \d+ apoio em \d+ squads\)", contagem_parens),
            (r"\d+ skills:", f"{sk} skills:"),
        ]),
        ("scripts/sync-multi-cli.py", [
            (r"\d+ agentes e \d+ skills", f"{t} agentes e {sk} skills"),
            (r"v\d+\.\d+ ativo \(Cursor\) — \d+ agentes \(\d+ core \+ \d+ apoio em \d+ squads\)",
             f"v{v_curta} ativo (Cursor) — {contagem_parens}"),
            (r"As \d+ personas", f"As {t} personas"),
        ]),
        ("CLAUDE.md", [
            (r"fábrica de software de \d+ agentes", f"fábrica de software de {t} agentes"),
            (r"\d+ agentes \(\d+ core \+ \d+ apoio em \d+ squads\), \d+ skills",
             f"{contagem_parens}, {sk} skills"),
            (r"Os \d+ agentes têm nomes", f"Os {t} agentes têm nomes"),
            (r"`agents/<id>\.md` \| \d+ subagentes", f"`agents/<id>.md` | {t} subagentes"),
            (r"\d+ skills \(compartilhadas", f"{sk} skills (compartilhadas"),
        ]),
        ("AGENTS.md", [
            (r"a \d+-agent software factory", f"a {t}-agent software factory"),
            (r"\*\*\d+ core agents\*\* organized in \d+ teams",
             f"**{c} core agents** organized in {tc} teams"),
            (r"\*\*\d+ support agents\*\* in \d+ squads", f"**{a} support agents** in {sq} squads"),
            (r"`agents/` — \d+ subagents", f"`agents/` — {t} subagents"),
            (r"\d+ skills, invoked", f"{sk} skills, invoked"),
            (r"All \d+ skills live", f"All {sk} skills live"),
            (r"the \d+ subagents \(`\.cursor/agents/`\), the \d+ skills",
             f"the {t} subagents (`.cursor/agents/`), the {sk} skills"),
            (r"The \d+ core agents and \d+ support agents",
             f"The {c} core agents and {a} support agents"),
        ]),
        ("README.md", [
            (r"autônoma com \d+ agentes", f"autônoma com {t} agentes"),
            (r"\d+ agentes \(\d+ core \+ \d+ apoio em \d+ squads\) coordenados",
             f"{contagem_parens} coordenados"),
            (r"\d+ skills cobrindo", f"{sk} skills cobrindo"),
            (r"os \d+ subagents, as \d+ skills", f"os {t} subagents, as {sk} skills"),
        ]),
        ("plugin/README.md", [
            (r"\*\*\d+ agentes em \d+ times\*\* \(\d+ core \+ \d+ apoio\)",
             f"**{t} agentes em {tt} times** ({c} core + {a} apoio)"),
            (r"## Os \d+ agentes core", f"## Os {c} agentes core"),
            (r"## Os \d+ agentes de apoio \(\d+ squads\)", f"## Os {a} agentes de apoio ({sq} squads)"),
            (r"## As \d+ skills", f"## As {sk} skills"),
            (r"O que chega: \d+ subagents", f"O que chega: {t} subagents"),
            (r"\d+ skills no menu", f"{sk} skills no menu"),
        ]),
        ("docs/inicio-rapido.md", [
            (r"fábrica de \d+ agentes", f"fábrica de {t} agentes"),
            (r"v\d+\.\d+ ativo — \d+ agentes \(\d+ core \+ \d+ apoio em \d+ squads\)",
             f"v{v_curta} ativo — {contagem_parens}"),
            (r"os \d+ agentes core são organizados", f"os {c} agentes core são organizados"),
        ]),
        ("templates/squad-fabrica.yaml", [
            (r'versao: "\d+\.\d+\.\d+"', f'versao: "{versao}"'),
            (r"com \d+ agentes especializados, organizada em \d+ times",
             f"com {c} agentes especializados, organizada em {tc} times"),
        ]),
        ("hermes/README.md", [
            (r"\d+ agentes \(\d+ core \+ \d+ apoio em \d+ squads\)", contagem_parens),
            (r"As \d+ skills do ciclo", f"As {sk} skills do ciclo"),
        ]),
    ]


def aplicar(n, versao, escrever):
    """Aplica os padrões. Com escrever=False só reporta divergências."""
    problemas = []
    for rel, subs in padroes(n, versao):
        arq = RAIZ / rel
        texto = arq.read_text(encoding="utf-8")
        novo = texto
        for rx, alvo in subs:
            if not re.search(rx, novo):
                problemas.append(f"{rel}: padrão sem match: /{rx}/")
                continue
            novo = re.sub(rx, lambda m: alvo, novo)
        if novo != texto:
            if escrever:
                arq.write_text(novo, encoding="utf-8")
                print(f"  ✍️  {rel}")
            else:
                problemas.append(f"{rel}: contagem ou versão divergente do estado real")
    return problemas


def arquivos_de(base, rel_dir):
    d = base / rel_dir
    if not d.is_dir():
        return set()
    return {
        str(p.relative_to(base))
        for p in d.rglob("*")
        if p.is_file() and ".agents/plugins" not in str(p.relative_to(base))
    }


def checar():
    n = derivar()
    versao = json.loads((RAIZ / ".claude-plugin/plugin.json").read_text())["version"]
    print(f"📦 versão: {versao} · {n['total']} agentes ({n['core']} core em "
          f"{n['times_core']} times + {n['apoio']} apoio em {n['squads']} squads) · "
          f"{n['skills']} skills")
    problemas = aplicar(n, versao, escrever=False)

    # JSON válido
    for rel in [".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
                ".codex-plugin/plugin.json", "hooks/hooks.json", ".codex/hooks.json",
                "plugin/.claude-plugin/plugin.json", "plugin/.codex-plugin/plugin.json",
                "plugin/hooks/hooks.json", "plugin/.codex/hooks.json",
                ".agents/plugins/marketplace.json"]:
        try:
            json.loads((RAIZ / rel).read_text(encoding="utf-8"))
        except Exception as e:
            problemas.append(f"{rel}: JSON inválido — {e}")

    # Mirrors gerados carregam todos os agentes
    for rel, glob in [(".agents", "*/AGENT.md"), (".cursor/agents", "*.md"),
                      ("plugin/.agents", "*/AGENT.md"), ("plugin/.cursor/agents", "*.md")]:
        achou = len(list((RAIZ / rel).glob(glob)))
        if achou != n["total"]:
            problemas.append(f"{rel}: {achou} agentes no mirror, esperado {n['total']} — rode o sync")

    # Paridade root ↔ plugin/
    plugin = RAIZ / "plugin"
    for d in DIRS_ESPELHADOS + DIRS_GERADOS:
        raiz_set, plugin_set = arquivos_de(RAIZ, d), arquivos_de(plugin, d)
        for rel in sorted(raiz_set - plugin_set):
            problemas.append(f"paridade: {rel} existe na raiz mas não em plugin/")
        for rel in sorted(plugin_set - raiz_set):
            problemas.append(f"paridade: plugin/{rel} não existe na raiz")
        for rel in sorted(raiz_set & plugin_set):
            if rel in EXCECOES_ESPELHO:
                continue
            if (RAIZ / rel).read_bytes() != (plugin / rel).read_bytes():
                problemas.append(f"paridade: {rel} difere entre raiz e plugin/")
    for rel in ARQUIVOS_ESPELHADOS:
        if (RAIZ / rel).read_bytes() != (plugin / rel).read_bytes():
            problemas.append(f"paridade: {rel} difere entre raiz e plugin/")

    # Toda skill aparece nos banners e manifests que listam skills por nome
    for rel in ["hooks/hooks.json", ".codex/hooks.json",
                ".claude-plugin/plugin.json", ".codex-plugin/plugin.json"]:
        texto = (RAIZ / rel).read_text(encoding="utf-8")
        for skill in n["nomes_skills"]:
            if skill not in texto:
                problemas.append(f"{rel}: skill '{skill}' não citada")

    # Sem cirílico nem replacement char nos fontes canônicos
    for rel_dir in ["agents", "skills", "templates", "docs", "hermes"]:
        for p in sorted((RAIZ / rel_dir).rglob("*.md")):
            texto = p.read_text(encoding="utf-8")
            if "�" in texto:
                problemas.append(f"{p.relative_to(RAIZ)}: caractere U+FFFD (emoji corrompido?)")
            for ch in set(texto):
                if ch.isalpha() and "CYRILLIC" in unicodedata.name(ch, ""):
                    problemas.append(f"{p.relative_to(RAIZ)}: caractere cirílico {ch!r}")
                    break

    # Gold set do eval de roteamento cita só agentes que existem
    gold = RAIZ / "evals/roteamento-laura/gold.jsonl"
    if gold.exists():
        for i, linha in enumerate(gold.read_text(encoding="utf-8").splitlines(), 1):
            if not linha.strip():
                continue
            try:
                caso = json.loads(linha)
            except Exception as e:
                problemas.append(f"gold.jsonl linha {i}: JSON inválido — {e}")
                continue
            for aid in caso.get("esperado", []):
                if aid not in n["ids_agentes"]:
                    problemas.append(f"gold.jsonl linha {i}: agente '{aid}' não existe")

    if problemas:
        print(f"\n❌ {len(problemas)} problema(s):")
        for p in problemas:
            print(f"  ✗ {p}")
        sys.exit(1)
    print("✅ consistente — versão, contagens, paridade e mirrors ok")


def espelhar():
    """Copia os canônicos root → plugin/ (respeitando as exceções)."""
    plugin = RAIZ / "plugin"
    for d in DIRS_ESPELHADOS:
        raiz_set, plugin_set = arquivos_de(RAIZ, d), arquivos_de(plugin, d)
        for rel in sorted(raiz_set):
            if rel in EXCECOES_ESPELHO:
                continue
            destino = plugin / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(RAIZ / rel, destino)
        for rel in sorted(plugin_set - raiz_set):
            (plugin / rel).unlink()
            print(f"  🗑️  plugin/{rel} (não existe mais na raiz)")
    for rel in ARQUIVOS_ESPELHADOS:
        shutil.copy2(RAIZ / rel, plugin / rel)


def bump(versao):
    if not re.fullmatch(r"\d+\.\d+\.\d+", versao):
        sys.exit(f"erro: versão inválida '{versao}' (esperado X.Y.Z)")
    n = derivar()
    print(f"🔢 {n['total']} agentes ({n['core']} core em {n['times_core']} times + "
          f"{n['apoio']} apoio em {n['squads']} squads) · {n['skills']} skills → v{versao}")
    problemas = aplicar(n, versao, escrever=True)
    if problemas:
        for p in problemas:
            print(f"  ✗ {p}")
        sys.exit(1)
    print("🔄 sync raiz...")
    subprocess.run([sys.executable, str(RAIZ / "scripts/sync-multi-cli.py")],
                   check=True, capture_output=True)
    print("🪞 espelhando em plugin/...")
    espelhar()
    print("🔄 sync plugin/...")
    subprocess.run([sys.executable, str(RAIZ / "plugin/scripts/sync-multi-cli.py")],
                   check=True, capture_output=True)
    print("🔍 verificação final:")
    checar()


def main():
    args = sys.argv[1:]
    if args == ["check"]:
        checar()
    elif len(args) == 2 and args[0] == "bump":
        bump(args[1])
    else:
        sys.exit(__doc__.strip())


if __name__ == "__main__":
    main()
