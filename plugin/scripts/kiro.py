#!/usr/bin/env python3
"""kiro.py — fronteira entre o kairos-forge e o Kiro CLI / Kiro Crew (ADR-0035).

Uma fonte da verdade para duas coisas que precisam concordar entre si:

  1. MAPEAMENTO DE FERRAMENTAS — a allow-list dos 71 agentes é escrita em nomes
     do Claude Code (`Read, Write, Edit, Grep, Glob, Bash`). O Kiro usa nomes
     próprios (`fs_read`, `fs_write`, `grep`, `glob`, `execute_bash`). O sync
     traduz a allow-list com esta tabela; os matchers de hook usam a MESMA
     tabela. Se as duas divergissem, o guardrail ficaria pendurado num matcher
     que nunca casa — um medidor que mede nada e diz que está tudo bem.

  2. ADAPTADOR DE PAYLOAD DE HOOK — `guardrail.py` e `execucao.py` falam o
     formato do Claude Code (`tool_name`, `tool_input.file_path`,
     `tool_input.command`). O Kiro entrega outro formato no stdin do hook.
     Em vez de espalhar `if kiro:` dentro dos scripts canônicos — que são a
     superfície assinada da fábrica — a tradução mora aqui, na fronteira.

## Modo adaptador

    kiro.py adaptar <script.py> <args...>

Lê o payload do Kiro no stdin, normaliza para o formato do Claude Code, e
executa `<script.py>` (irmão deste arquivo) com o payload normalizado no stdin.
O código de saída do script é propagado INTACTO — é o que faz o exit 2 do
`guardrail.py` continuar bloqueando a ferramenta do lado do Kiro.

## Modo tabela

    kiro.py ferramentas        # imprime o mapeamento (usado no CI e no debug)

Só stdlib, igual ao resto de scripts/.

## O que NÃO está verificado

O nome exato do campo que carrega os argumentos da ferramenta variou entre
versões do Kiro (`tool_input`, `toolArgs`, `tool_args`) e há issue aberta sobre
o IDE entregar `{}` onde a CLI entrega o contexto completo. Por isso o
adaptador aceita as três grafias em vez de apostar numa. Quando o campo
estabilizar, esta tolerância vira uma linha só — e o teste do CI acusa.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# --- 1. mapeamento de ferramentas ----------------------------------------------------

# Claude Code → Kiro. Cobre exatamente as 8 ferramentas que os 71 agentes
# declaram hoje; ferramenta nova sem entrada aqui é erro explícito no sync,
# não silêncio.
#
# `web` é a única entrada que NÃO é um nome de tool builtin do Kiro: é uma
# categoria aceita no campo `tools` (junto de read/write/shell). Os 6 agentes
# que pedem WebSearch/WebFetch caem nela. Se a categoria sumir do Kiro, o
# sintoma é a config recusada na carga — barulhento, que é como se quer.
FERRAMENTAS: dict[str, str] = {
    "Read": "fs_read",
    "Grep": "grep",
    "Glob": "glob",
    "Write": "fs_write",
    "Edit": "fs_write",
    "NotebookEdit": "fs_write",
    "Bash": "execute_bash",
    "WebSearch": "web",
    "WebFetch": "web",
}

# Kiro → Claude, para o adaptador devolver ao guardrail o nome que ele conhece.
# `fs_write` volta como `Write`: `checar_escrita` e `checar_spec` tratam Write e
# Edit pela mesma porta (leem file_path/content), então colapsar não perde regra.
DE_KIRO: dict[str, str] = {
    "fs_read": "Read",
    "grep": "Grep",
    "glob": "Glob",
    "fs_write": "Write",
    "execute_bash": "Bash",
    # aliases que o Kiro aceita nos matchers e pode ecoar no payload
    "read": "Read",
    "write": "Write",
    "shell": "Bash",
}

# Ferramentas de leitura pura — as únicas pré-aprovadas (`allowedTools`).
# Escrita e shell continuam pedindo confirmação: é a mesma fronteira que o
# Claude Code aplica por padrão e o critério de admissão do ADR-0024. Quem
# quiser autonomia mais larga afrouxa no lado do Kiro, conscientemente.
PRE_APROVADAS = ("fs_read", "grep", "glob")


def traduzir_ferramentas(tools: str) -> tuple[list[str], list[str]]:
    """`"Read, Write, Bash"` → (`["fs_read","fs_write","execute_bash"]`, pré-aprovadas).

    Levanta KeyError em ferramenta desconhecida — o sync falha alto em vez de
    gerar um agente com allow-list silenciosamente menor do que a declarada.
    """
    nomes: list[str] = []
    for bruto in tools.split(","):
        nome = bruto.strip()
        if not nome:
            continue
        kiro = FERRAMENTAS[nome]  # KeyError proposital
        if kiro not in nomes:
            nomes.append(kiro)
    permitidas = [t for t in nomes if t in PRE_APROVADAS]
    return nomes, permitidas


# --- 2. adaptador de payload ---------------------------------------------------------

# Grafias observadas para o mesmo campo em versões/superfícies diferentes do Kiro.
_CHAVES_NOME = ("tool_name", "toolName", "tool")
_CHAVES_ARGS = ("tool_input", "toolArgs", "tool_args", "toolInput", "input", "arguments")
# Dentro dos args: Kiro nomeia o caminho de `path` e o conteúdo de `file_text`
# (criação) ou `new_str` (substituição). O guardrail lê `file_path` e `content`.
_CHAVES_CAMINHO = ("file_path", "path", "filePath")
_CHAVES_CONTEUDO = ("content", "file_text", "new_str", "fileText", "newStr")
# Verbos que o `fs_write` do Kiro coloca no campo `command`.
_VERBOS_ESCRITA = {"create", "str_replace", "insert", "append"}


def _primeiro(d: dict, chaves: tuple[str, ...]):
    for k in chaves:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def normalizar(payload: dict) -> dict:
    """Payload do Kiro → formato que guardrail.py e execucao.py já falam.

    Nunca levanta: hook que explode por payload inesperado é pior que hook
    ausente. Campo que não deu para traduzir simplesmente não aparece, e os
    scripts a jusante já tratam ausência (`.get(...) or {}`).
    """
    if not isinstance(payload, dict):
        return {}

    bruto_nome = _primeiro(payload, _CHAVES_NOME)
    nome = DE_KIRO.get(str(bruto_nome), bruto_nome) if bruto_nome else None

    args = _primeiro(payload, _CHAVES_ARGS)
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (ValueError, TypeError):
            args = {"command": args}
    if not isinstance(args, dict):
        args = {}

    entrada = dict(args)
    caminho = _primeiro(args, _CHAVES_CAMINHO)
    if caminho is not None:
        entrada["file_path"] = caminho
    conteudo = _primeiro(args, _CHAVES_CONTEUDO)
    if conteudo is not None:
        entrada["content"] = conteudo

    # O `fs_write` do Kiro carrega o VERBO da escrita (`create`, `str_replace`, …)
    # num campo `command` — mesmo nome que o `execute_bash` usa para a linha de
    # shell. Deixar os dois com o mesmo nome é convidar quem lê o evento a tratar
    # "create" como comando executado. Some quando já sabemos que é escrita.
    if nome == "Write" and str(entrada.get("command", "")) in _VERBOS_ESCRITA:
        entrada.pop("command", None)

    saida: dict = {"tool_input": entrada}
    if nome:
        saida["tool_name"] = nome
    for campo in ("session_id", "cwd", "hook_event_name", "tool_response", "prompt"):
        if payload.get(campo) is not None:
            saida[campo] = payload[campo]
    # `hook_event_name` do Kiro vem em camelCase (preToolUse); os scripts não
    # dependem dele hoje, mas quem ler o JSONL depois merece o valor original.
    return saida


def adaptar(argv: list[str]) -> int:
    """Normaliza o stdin e repassa para o script irmão, propagando o exit code."""
    if not argv:
        print(__doc__.strip(), file=sys.stderr)
        return 1
    alvo = RAIZ / Path(argv[0]).name  # só irmãos — não é ponte para shell arbitrário
    if not alvo.is_file():
        print(f"kairos-forge: {alvo.name} não encontrado em {RAIZ}", file=sys.stderr)
        return 1

    try:
        bruto = sys.stdin.read()
    except Exception:
        bruto = ""
    try:
        payload = json.loads(bruto) if bruto.strip() else {}
    except ValueError:
        payload = {}

    entrada = json.dumps(normalizar(payload), ensure_ascii=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        proc = subprocess.run(
            [sys.executable, str(alvo), *argv[1:]],
            input=entrada, text=True, env=env,
        )
    except Exception as e:
        print(f"kairos-forge: falha ao rodar {alvo.name} — {e}", file=sys.stderr)
        return 1
    return proc.returncode


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "adaptar":
        return adaptar(args[1:])
    if args == ["ferramentas"]:
        for claude, kiro in FERRAMENTAS.items():
            marca = " (pré-aprovada)" if kiro in PRE_APROVADAS else ""
            print(f"{claude:<14} → {kiro}{marca}")
        return 0
    print(__doc__.strip())
    return 1


if __name__ == "__main__":
    sys.exit(main())
