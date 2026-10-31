#!/usr/bin/env python3
"""tucano.py — a fábrica como um time do Tucano (ADR-0047).

O [Tucano](https://github.com/eduwxyz/tucano) (Apache 2.0) é um app local em que agentes
com nome trabalham em canais e cada um pensa com o Claude Code, o Codex ou o OpenCode
da máquina. Ele roda a CLI isolada de propósito — sem plugin, sem hook, sem skill do
usuário —, então a fábrica não entra como plugin: entra como **time**, pelo formato que
o próprio Tucano importa (um Markdown com um bloco ```json tucano-team).

Este script traduz os canônicos para esse formato:

- **personas → agentes**: nome, papel, cor, modelo (o modelo decide o harness), esforço
  e instruções — o corpo da persona precedido de um preâmbulo que explica ao agente
  como a fábrica funciona dentro do Tucano;
- **skills → skills**: o corpo do SKILL.md com as `references/` embutidas, porque o
  Tucano lê uma receita só, e `${CLAUDE_PLUGIN_ROOT}` reescrito para `.kairos-forge`;
- **um canal** com o nome da pasta do projeto e **a rotina** da auditoria semanal.

Os scripts determinísticos (`ciclo.py`, `quadro.py`, `prova.py`, `qualidade.py`,
`guardrail.py`…) vão para dentro do projeto, em `.kairos-forge/scripts/`, onde o agente
os roda pelo computador que o Tucano dá a ele.

Uso:
    tucano.py gerar                     # regenera .tucano/ (o sync-multi-cli.py chama)
    tucano.py instalar [--canal NOME] [--opencode-modelo PROVEDOR/MODELO]
                       [--projeto DIR] [--dry-run]

`instalar` roda na raiz do projeto: copia scripts e templates para `.kairos-forge/` e
grava `.kairos-forge/time-tucano.md`, que se importa no Tucano em Configurações → Time.

Só stdlib.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARCA_GERADO = "GERADO por scripts/sync-multi-cli.py (kairos-forge)"
PASTA = ".kairos-forge"           # dentro do projeto do usuário
ARQUIVO_GERADO = ".tucano/kairos-forge-entrega.md"
CANAL_PADRAO = "fabrica"

# --- o que o Tucano aceita (src/core/team.ts e src/shared/types.ts, v0.2.2) ---------
# Modelo desconhecido vira `sonnet` sem aviso na importação: por isso a lista é fechada.
MODELOS = {"sonnet": "claude", "opus": "claude", "haiku": "claude",
           "gpt-5.6-luna": "codex", "gpt-5.6-terra": "codex", "gpt-5.6-sol": "codex"}
MOTORES_COM_NOME = ("claude", "codex", "opencode", "pi")   # `<motor>:<modelo>`
CORES = {"sky", "indigo", "violet", "rose", "amber", "green", "teal", "graphite"}
ESFORCOS = {"low", "medium", "high", "xhigh"}
HANDLE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,31}$")          # o regex da @menção
BLOCO = re.compile(r"```json (?:tucano-team|agent-desk-team)\n([\s\S]*?)\n```")
HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
TETO_RESULTADO = 60_000   # o Tucano corta resultado de ferramenta (ler_skill) aqui

# --- o pacote de entrega ------------------------------------------------------------
# Quem constrói pensa com o Claude Code; quem revisa, com o Codex — revisão por outra
# família de modelo, a regra do juiz do ADR-0031. O Ricardo vai para o OpenCode quando
# a instalação recebe um modelo dele.
PACOTE_ENTREGA = [
    # (id da persona, handle, nome, papel, cor, modelo, esforço)
    ("laura-tech-lead", "laura", "Laura", "Tech Lead", "violet", "opus", "medium"),
    ("apoio-joana-elicitacao", "joana", "Joana", "Requisitos", "amber", "sonnet", "medium"),
    ("lucas-backend", "lucas", "Lucas", "Backend", "sky", "sonnet", "high"),
    ("marina-frontend", "marina", "Marina", "Frontend", "rose", "sonnet", "high"),
    ("ricardo-testes", "ricardo", "Ricardo", "Testes", "green", "sonnet", "medium"),
    ("helena-security", "helena", "Helena", "Segurança", "graphite", "gpt-5.6-terra", "high"),
    ("patricia-qa", "patricia", "Patrícia", "QA", "teal", "gpt-5.6-terra", "medium"),
]
NO_OPENCODE = "ricardo"
SKILLS_ENTREGA = {
    "especificar": ["laura", "joana"],
    "entregar": ["laura"],
    "analisar-ameacas": ["helena"],
    "validar": ["ricardo", "patricia"],
    "revisar": ["helena", "patricia"],
    "auditar": ["laura"],
}
ESCRITA = {"Write", "Edit", "NotebookEdit"}


# --- leitura dos canônicos ------------------------------------------------------------

def separar(texto: str) -> tuple[dict[str, str], str]:
    """(frontmatter simples chave: valor, corpo)."""
    m = re.match(r"^---\n(.*?)\n---\n?", texto, re.S)
    if not m:
        return {}, texto
    campos = dict(re.findall(r"^([\w-]+):\s*(.*)$", m.group(1), re.M))
    return campos, texto[m.end():]


def para_o_projeto(texto: str) -> str:
    """Os caminhos do plugin viram os do projeto: o agente roda tudo da raiz dele."""
    return texto.replace("${CLAUDE_PLUGIN_ROOT}", PASTA).replace("<plugin>/", f"{PASTA}/")


def preambulo(nome: str, papel: str, ferramentas: set[str]) -> str:
    consultivo = "" if ferramentas & ESCRITA else (
        "- Na fábrica você é **consultivo**: lê, roda comandos de leitura e dá parecer, mas "
        "não edita arquivos do projeto. Mudança, peça a quem constrói.\n")
    return (
        f"## Você está no Tucano, como {nome} ({papel}) da fábrica KairOS-Forge\n\n"
        "- **O canal é o projeto.** Cada canal da fábrica tem o nome da pasta do projeto: no "
        "#loja, trabalhe na pasta emprestada `loja` (em `/projetos/`). Sem a pasta "
        "emprestada, peça antes de começar.\n"
        f"- **Os scripts da fábrica estão no projeto, em `{PASTA}/scripts/`.** Rode-os pelo seu "
        f"computador, da raiz do projeto: `python3 {PASTA}/scripts/<script>.py`. Onde uma skill "
        "citar `/kairos-forge:<nome>`, leia e siga a skill `<nome>`.\n"
        "- **O estado mora no repositório, não na conversa:** SPEC em `docs/specs/`, ciclo do "
        f"`/entregar` em `python3 {PASTA}/scripts/ciclo.py estado <SPEC> --json`, relatórios em "
        "`docs/specs/validacoes/` e `docs/specs/revisoes/`. Leia o estado antes de agir e "
        "registre depois.\n"
        "- **Passe a vez com @handle**, fora de bloco de código, dizendo o que o próximo faz e "
        "onde está o artefato. Um próximo por vez.\n"
        "- **Os guardrails em hook da fábrica não rodam aqui.** Respeite-os por conta própria: "
        "nada de `--no-verify`, nada de afrouxar teste existente ou config do linter sem dizer "
        f"por quê. Antes de pedir o PR, rode `python3 {PASTA}/scripts/guardrail.py verificar .`.\n"
        "- **Merge é do humano.** Commit em `agent/<tema>`, PR com `abrir_pr`.\n"
        "- **Não proponha mudança nas skills da fábrica** com `propor_skill`: skill da fábrica "
        "se muda no repositório da fábrica, com ADR.\n"
        + consultivo
        + "\n---\n\n"
    )


def agente(entrada: tuple, opencode_modelo: str | None) -> dict:
    pid, handle, nome, papel, cor, modelo, esforco = entrada
    campos, corpo = separar((ROOT / "agents" / f"{pid}.md").read_text(encoding="utf-8"))
    ferramentas = {t.strip() for t in campos.get("tools", "").split(",") if t.strip()}
    if opencode_modelo and handle == NO_OPENCODE:
        modelo = f"opencode:{opencode_modelo}"
    return {"handle": handle, "name": nome, "role": papel, "color": cor,
            "instructions": preambulo(nome, papel, ferramentas) + para_o_projeto(corpo.strip()),
            "model": modelo, "effort": esforco, "limit": 0, "web": True, "computer": False,
            "grants": {}}


def skill(nome: str, agentes: list[str]) -> dict:
    pasta = ROOT / "skills" / nome
    campos, corpo = separar((pasta / "SKILL.md").read_text(encoding="utf-8"))
    partes = [corpo.strip()]
    for ref in sorted((pasta / "references").glob("*.md")):
        partes.append(f"# Referência: references/{ref.name}\n\n"
                      + ref.read_text(encoding="utf-8").strip())
    return {"name": nome, "description": campos.get("description", "").strip(),
            "body": para_o_projeto("\n\n---\n\n".join(partes)), "agents": agentes}


def montar_time(canal: str = CANAL_PADRAO, opencode_modelo: str | None = None) -> dict:
    handles = [e[1] for e in PACOTE_ENTREGA]
    return {
        "version": 1,
        "agents": [agente(e, opencode_modelo) for e in PACOTE_ENTREGA],
        "skills": [skill(n, a) for n, a in SKILLS_ENTREGA.items()],
        "channels": [{"name": canal, "topic": f"Fábrica KairOS-Forge no projeto {canal}",
                      "members": handles}],
        "routines": [{"name": "Auditoria semanal da fábrica", "agent": "laura",
                      "where": f"#{canal}", "schedule": {"days": [1], "time": "08:37"},
                      "prompt": "Rode a skill auditar neste projeto e poste o relatório "
                                "com o top 3 de lacunas."}],
    }


# --- o arquivo de time ----------------------------------------------------------------

def rotulo_do_modelo(modelo: str) -> str:
    return modelo.split(":", 1)[1] if ":" in modelo else modelo


def markdown(time: dict) -> str:
    """O mesmo desenho do arquivo que o Tucano exporta: prosa para gente, bloco para o app."""
    linhas = [f"<!-- {MARCA_GERADO} — edite agents/ e skills/ e rode o sync -->",
              "# Time KairOS-Forge — entrega", "",
              "A fábrica de software KairOS-Forge como um time do Tucano. Importe em "
              "Configurações → Time → Importar time. Depois: empreste a pasta do projeto a "
              "quem mexe em código, ligue o computador de cada um e, se quiser, a rotina.", "",
              "## Agentes"]
    linhas += [f"- **{a['name']}** (@{a['handle']}) · {a['role']} · {rotulo_do_modelo(a['model'])}"
               for a in time["agents"]]
    linhas += ["", "## Skills"] + [f"- **{k['name']}**: {k['description']}" for k in time["skills"]]
    linhas += ["", "## Canais"] + [f"- #{c['name']}: " + ", ".join(f"@{h}" for h in c["members"])
                                   for c in time["channels"]]
    linhas += ["", "## Rotinas"] + [f"- **{r['name']}** (@{r['agent']}, {r['where']}): "
                                    f"segunda, {r['schedule']['time']} — entra desligada"
                                    for r in time["routines"]]
    linhas += ["", "<!-- O bloco abaixo é o que o app importa. -->",
               "```json tucano-team", json.dumps(time, ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(linhas)


def ler_bloco(texto: str) -> dict | None:
    """O que o `importTeam` do Tucano leria deste texto; None se ele recusaria."""
    m = BLOCO.search(texto)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


# --- validação: as regras do importador, para não importar meio time -----------------

def modelo_valido(modelo: str) -> bool:
    if modelo in MODELOS:
        return True
    motor, _, nome = modelo.partition(":")
    return motor in MOTORES_COM_NOME and bool(nome.strip())


def problemas_dos_agentes(agentes: list[dict]) -> list[str]:
    problemas = []
    vistos: set[str] = set()
    for a in agentes:
        h = a.get("handle", "")
        if not HANDLE.match(h) or h in vistos:
            problemas.append(f"handle inválido ou repetido: {h!r}")
        vistos.add(h)
        if not modelo_valido(a.get("model", "")):
            problemas.append(f"@{h}: modelo {a.get('model')!r} viraria sonnet na importação")
        if a.get("color") not in CORES or a.get("effort") not in ESFORCOS:
            problemas.append(f"@{h}: cor ou esforço fora do que o Tucano conhece")
    return problemas


def problemas_das_skills(skills: list[dict], handles: set[str]) -> list[str]:
    problemas = []
    for k in skills:
        if set(k["agents"]) - handles:
            problemas.append(f"skill {k['name']}: agente que não está no time")
        if len(k["body"]) > TETO_RESULTADO:
            problemas.append(f"skill {k['name']}: {len(k['body'])} caracteres — o ler_skill corta")
        if "${CLAUDE_PLUGIN_ROOT}" in k["body"]:
            problemas.append(f"skill {k['name']}: caminho do plugin não reescrito")
    return problemas


def problemas_dos_canais(time: dict, handles: set[str]) -> list[str]:
    canais = {f"#{c['name']}" for c in time["channels"]}
    problemas = [f"canal #{c['name']}: membro que não está no time"
                 for c in time["channels"] if set(c["members"]) - handles]
    for r in time["routines"]:
        agenda = r["schedule"]
        if r["agent"] not in handles or r["where"] not in canais | {"dm"}:
            problemas.append(f"rotina {r['name']}: agente ou canal inexistente")
        if not HORA.match(agenda["time"]) or not set(agenda["days"]) <= set(range(7)):
            problemas.append(f"rotina {r['name']}: agenda inválida")
    return problemas


def validar(time: dict | None) -> list[str]:
    if not time or time.get("version") != 1:
        return ["o bloco não é um time versão 1 que o Tucano importe"]
    handles = {a["handle"] for a in time["agents"]}
    return (problemas_dos_agentes(time["agents"])
            + problemas_das_skills(time["skills"], handles)
            + problemas_dos_canais(time, handles))


# --- gerar e instalar -----------------------------------------------------------------

def gerar(raiz: Path = ROOT) -> Path:
    """Regenera `.tucano/` — chamado pelo sync, como os espelhos dos outros CLIs."""
    texto = markdown(montar_time())
    problemas = validar(ler_bloco(texto))
    if problemas:
        raise ValueError("time do Tucano inválido: " + "; ".join(problemas))
    destino = raiz / ARQUIVO_GERADO
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(texto, encoding="utf-8")
    return destino


def canal_de(projeto: Path) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", projeto.resolve().name.lower()).strip("-")
    return slug or CANAL_PADRAO


def _sync():
    spec = importlib.util.spec_from_file_location("sync_multi_cli", ROOT / "scripts" / "sync-multi-cli.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def copiar_suporte(destino: Path) -> int:
    """Os scripts que as skills citam e os templates, como o alvo Cursor já copia."""
    (destino / "scripts").mkdir(parents=True, exist_ok=True)
    n = 0
    for nome in _sync().SCRIPTS_DE_SUPORTE:
        origem = ROOT / "scripts" / nome
        if origem.is_file():
            shutil.copy2(origem, destino / "scripts" / nome)
            n += 1
    shutil.copytree(ROOT / "templates", destino / "templates", dirs_exist_ok=True)
    return n


def instalar(projeto: Path, canal: str | None, opencode_modelo: str | None,
             dry_run: bool) -> int:
    canal = canal or canal_de(projeto)
    time = montar_time(canal, opencode_modelo)
    problemas = validar(time)
    if problemas:
        print("❌ " + "; ".join(problemas), file=sys.stderr)
        return 1
    destino = projeto / PASTA
    print(f"📦 Tucano → {destino}  [{'simulação' if dry_run else 'instalação'}]")
    if not dry_run:
        n = copiar_suporte(destino)
        (destino / "time-tucano.md").write_text(markdown(time), encoding="utf-8")
        print(f"  ✓ {n} scripts e os templates em {PASTA}/, time em {PASTA}/time-tucano.md")
    motores = sorted({MODELOS.get(a["model"], a["model"].partition(":")[0]) for a in time["agents"]})
    print(f"  · canal #{canal} · {len(time['agents'])} agentes ({', '.join(motores)}) · "
          f"{len(time['skills'])} skills")
    print("  → No Tucano: Configurações → Time → Importar time… e escolha o arquivo.\n"
          f"    Depois empreste a pasta do projeto, ligue o computador de cada agente e "
          f"chame @laura no #{canal}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tucano.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gerar", help=f"regenera {ARQUIVO_GERADO}")
    p = sub.add_parser("instalar", help="prepara um projeto para o time do Tucano")
    p.add_argument("--projeto", type=Path, default=Path.cwd())
    p.add_argument("--canal", help="nome do canal (padrão: o nome da pasta do projeto)")
    p.add_argument("--opencode-modelo", help="provedor/modelo do OpenCode para o @ricardo "
                                             "(veja `opencode models`)")
    p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "gerar":
        print(f"✓ {gerar().relative_to(ROOT)}")
        return 0
    return instalar(a.projeto, a.canal, a.opencode_modelo, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
