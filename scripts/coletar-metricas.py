#!/usr/bin/env python3
"""coletar-metricas.py — Telemetria da SESSÃO do kairos-forge.

Coleta métricas da sessão e dos subagentes acionados para virar entregável
(skill `/kairos-forge:relatar`). NÃO mede o produto do usuário — mede o trabalho
da fábrica nesta sessão.

Dois modos:

  1. --hook
     Lê UM evento de hook do Claude Code no stdin (JSON) e faz append num log
     JSONL em `<cwd>/.agents/metricas/sessao-<session_id>.jsonl`. Silencioso e
     tolerante a falha (hooks nunca devem quebrar a sessão). Exclusivo do
     Claude Code — Codex/OpenCode não disparam Pre/PostToolUse/SubagentStop.

  2. --agregar <transcript-ou-jsonl>
     Faz parsing do transcript JSONL da conversa (e, se houver, do log de hook),
     cruza com `git log` e varre os diretórios-convenção de artefatos, e imprime
     no stdout UM JSON agregado que a skill `relatar` consome para montar os
     relatórios executivo, técnico e o painel acumulado.

Apenas stdlib. Sem dependências externas.

Uso:
    echo '<json-do-hook>' | python3 scripts/coletar-metricas.py --hook
    python3 scripts/coletar-metricas.py --agregar TRANSCRIPT.jsonl \\
        [--jsonl LOG.jsonl] [--git] [--projeto DIR] [--inicio ISO] [--fim ISO]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# Diretórios-convenção onde as skills do forge salvam entregáveis. Usados para
# detectar artefatos produzidos na janela da sessão (por mtime).
DIRS_ARTEFATOS = [
    "docs/specs",
    "docs/specs/validacoes",
    "docs/arquitetura",
    "docs/seguranca",
    "decisoes/auditorias",
    "decisoes/evolucoes",
    "decisoes/relatorios",
    ".agents/memory",
]

# Tabela de preço APROXIMADA por modelo, em USD por milhão de tokens.
# Chave = substring do nome do modelo. cache_read ~ 0.1x input;
# cache_creation ~ 1.25x input. Valores de referência — o custo é estimado.
PRECOS_USD_POR_MILHAO = {
    "opus": {"input": 15.0, "output": 75.0},
    "sonnet": {"input": 3.0, "output": 15.0},
    "haiku": {"input": 1.0, "output": 5.0},
}
PRECO_PADRAO = {"input": 5.0, "output": 15.0}


# ---------------------------------------------------------------------------
# Modo --hook
# ---------------------------------------------------------------------------

def modo_hook() -> int:
    """Lê um evento de hook do stdin e faz append no log JSONL da sessão.

    Tolerante a falha por design: qualquer erro retorna 0 para nunca quebrar
    a sessão do usuário.
    """
    try:
        bruto = sys.stdin.read()
        if not bruto.strip():
            return 0
        evento = json.loads(bruto)
    except Exception:
        return 0

    try:
        sessao_id = str(evento.get("session_id") or "desconhecida")
        cwd = evento.get("cwd") or "."
        registro = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "evento": evento.get("hook_event_name"),
            "tool": evento.get("tool_name"),
            "source": evento.get("source"),
            "reason": evento.get("reason"),
        }
        # Campos seletivos do tool_input (não guardar payloads grandes).
        entrada = evento.get("tool_input") or {}
        if isinstance(entrada, dict):
            for chave in ("file_path", "subagent_type", "description", "command"):
                if chave in entrada:
                    valor = entrada[chave]
                    if isinstance(valor, str) and len(valor) > 500:
                        valor = valor[:500]
                    registro[chave] = valor
        # Sucesso aproximado a partir do tool_response.
        resposta = evento.get("tool_response")
        if isinstance(resposta, dict) and "is_error" in resposta:
            registro["erro"] = bool(resposta["is_error"])

        destino_dir = Path(cwd) / ".agents" / "metricas"
        destino_dir.mkdir(parents=True, exist_ok=True)
        destino = destino_dir / f"sessao-{sessao_id}.jsonl"
        with destino.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception:
        return 0
    return 0


# ---------------------------------------------------------------------------
# Modo --agregar — helpers de parsing
# ---------------------------------------------------------------------------

def _carregar_jsonl(caminho: Path) -> list[dict]:
    linhas = []
    try:
        with caminho.open(encoding="utf-8") as fh:
            for linha in fh:
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    linhas.append(json.loads(linha))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return linhas


def _parse_ts(valor) -> datetime | None:
    if not valor or not isinstance(valor, str):
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None


def _roster_primeiros_nomes() -> dict[str, str]:
    """Mapeia primeiro nome (minúsculo) → id do agente, a partir de agents/."""
    roster: dict[str, str] = {}
    agentes_dir = ROOT / "agents"
    if not agentes_dir.exists():
        return roster
    for md in agentes_dir.glob("*.md"):
        ident = md.stem  # ex.: marina-frontend, apoio-otavio-metricas
        partes = ident.split("-")
        if partes and partes[0] == "apoio" and len(partes) > 1:
            primeiro = partes[1]
        elif partes:
            primeiro = partes[0]
        else:
            continue
        roster.setdefault(primeiro.lower(), ident)
    return roster


def _texto_assistant(msg: dict) -> str:
    conteudo = msg.get("content")
    if isinstance(conteudo, str):
        return conteudo
    partes = []
    if isinstance(conteudo, list):
        for item in conteudo:
            if isinstance(item, dict) and item.get("type") == "text":
                partes.append(item.get("text", ""))
    return "\n".join(partes)


def agregar(
    transcript: Path | None,
    jsonl_hook: Path | None,
    usar_git: bool,
    projeto: Path,
    inicio_arg: str | None,
    fim_arg: str | None,
) -> dict:
    avisos: list[str] = []
    fontes = {"transcript": False, "jsonl_hook": False, "git": False}

    ferramentas = Counter()
    arquivos = []
    comandos_bash = []
    skills_rodadas = []
    tokens = {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}
    modelos_usage = defaultdict(lambda: {"input": 0, "output": 0,
                                         "cache_creation": 0, "cache_read": 0})
    sessao_id = None
    ts_min = None
    ts_max = None

    # tool_use_id → (nome_tool, ts_inicio, input) para casar com tool_result.
    tool_use_pendente: dict[str, tuple] = {}
    subagentes: list[dict] = []

    roster = _roster_primeiros_nomes()
    personas = Counter()

    # ---- Transcript (fonte principal) ----
    if transcript and transcript.exists():
        fontes["transcript"] = True
        linhas = _carregar_jsonl(transcript)
        for entrada in linhas:
            sessao_id = sessao_id or entrada.get("sessionId") or entrada.get("session_id")
            ts = _parse_ts(entrada.get("timestamp"))
            if ts:
                ts_min = ts if ts_min is None or ts < ts_min else ts_min
                ts_max = ts if ts_max is None or ts > ts_max else ts_max

            tipo = entrada.get("type")
            msg = entrada.get("message") or {}

            if tipo == "assistant" and isinstance(msg, dict):
                # Tokens / custo.
                uso = msg.get("usage") or {}
                modelo = msg.get("model") or "desconhecido"
                if uso:
                    mapa = {
                        "input": uso.get("input_tokens", 0),
                        "output": uso.get("output_tokens", 0),
                        "cache_creation": uso.get("cache_creation_input_tokens", 0),
                        "cache_read": uso.get("cache_read_input_tokens", 0),
                    }
                    for k, v in mapa.items():
                        tokens[k] += v or 0
                        modelos_usage[modelo][k] += v or 0

                # Ferramentas chamadas e personas conversacionais.
                conteudo = msg.get("content")
                if isinstance(conteudo, list):
                    for item in conteudo:
                        if not isinstance(item, dict):
                            continue
                        if item.get("type") == "tool_use":
                            nome = item.get("name", "desconhecida")
                            ferramentas[nome] += 1
                            entr = item.get("input") or {}
                            if nome in ("Write", "Edit", "NotebookEdit") and isinstance(entr, dict):
                                fp = entr.get("file_path") or entr.get("notebook_path")
                                if fp:
                                    arquivos.append(fp)
                            if nome == "Bash" and isinstance(entr, dict):
                                cmd = entr.get("command")
                                if cmd:
                                    comandos_bash.append(cmd)
                            if nome == "Task" and isinstance(entr, dict):
                                tool_use_pendente[item.get("id", "")] = (
                                    entr.get("subagent_type") or "desconhecido",
                                    entr.get("description") or "",
                                    ts,
                                )
                # Personas conversacionais do /rodar (estimativa por regex).
                texto = _texto_assistant(msg)
                if texto and roster:
                    for m in re.finditer(r"\b[Oo]i,?\s+([A-ZÀ-Ý][a-zà-ÿ]+)\s+aqui\b", texto):
                        nome = m.group(1).lower()
                        if nome in roster:
                            personas[roster[nome]] += 1

            if tipo == "user" and isinstance(msg, dict):
                conteudo = msg.get("content")
                if isinstance(conteudo, list):
                    for item in conteudo:
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            tid = item.get("tool_use_id", "")
                            if tid in tool_use_pendente:
                                nome_ag, descr, ts_ini = tool_use_pendente.pop(tid)
                                dur = None
                                if ts_ini and ts:
                                    dur = (ts - ts_ini).total_seconds()
                                subagentes.append({
                                    "agente": nome_ag,
                                    "descricao": descr,
                                    "modo": "Task",
                                    "duracao_segundos": dur,
                                    "sucesso": not bool(item.get("is_error")),
                                })

            # Skills rodadas: procurar /kairos-forge:<verbo> em texto user/assistant.
            blob = json.dumps(entrada, ensure_ascii=False)
            for m in re.finditer(r"/kairos-forge:([a-zà-ÿ-]+)", blob):
                skills_rodadas.append(m.group(1))
    else:
        avisos.append(
            "Transcript indisponível: tokens, custo e subagentes Task não "
            "puderam ser medidos neste CLI."
        )

    # Subagentes Task que não tiveram tool_result (sem duração/sucesso).
    for nome_ag, descr, ts_ini in tool_use_pendente.values():
        subagentes.append({
            "agente": nome_ag, "descricao": descr, "modo": "Task",
            "duracao_segundos": None, "sucesso": None,
        })

    # ---- Enriquecimento opcional pelo log de hook (timing fino) ----
    if jsonl_hook and jsonl_hook.exists():
        fontes["jsonl_hook"] = True
        eventos = _carregar_jsonl(jsonl_hook)
        _refinar_com_hook(eventos, subagentes, avisos)
        for ev in eventos:
            if ev.get("evento") == "SessionStart":
                ts = _parse_ts(ev.get("ts"))
                if ts and (ts_min is None or ts < ts_min):
                    ts_min = ts
            if ev.get("evento") == "SessionEnd":
                ts = _parse_ts(ev.get("ts"))
                if ts and (ts_max is None or ts > ts_max):
                    ts_max = ts

    # ---- Janela temporal efetiva (argumentos --inicio/--fim sobrescrevem) ----
    # Vale para git, artefatos e duração, para manter tudo coerente.
    ini_efetivo = _parse_ts(inicio_arg) or ts_min
    fim_efetivo = _parse_ts(fim_arg) or ts_max

    # ---- git log na janela da sessão ----
    commits = []
    if usar_git:
        commits = _coletar_commits(projeto, ini_efetivo, fim_efetivo, avisos)
        if commits is not None:
            fontes["git"] = True
        else:
            commits = []

    # ---- Artefatos produzidos na janela da sessão (por mtime) ----
    artefatos = _coletar_artefatos(projeto, ini_efetivo, fim_efetivo)

    # ---- Janela temporal final ----
    inicio = ini_efetivo.isoformat() if ini_efetivo else None
    fim = fim_efetivo.isoformat() if fim_efetivo else None
    duracao = None
    if ini_efetivo and fim_efetivo:
        duracao = max(0.0, (fim_efetivo - ini_efetivo).total_seconds())

    # ---- Custo estimado ----
    custo, modelos_resumo = _estimar_custo(modelos_usage)

    return {
        "sessao_id": sessao_id,
        "cli": _detectar_cli(fontes),
        "projeto": str(projeto),
        "inicio": inicio,
        "fim": fim,
        "duracao_segundos": duracao,
        "ferramentas": dict(ferramentas),
        "ferramentas_total": sum(ferramentas.values()),
        "arquivos_escritos": sorted(set(arquivos)),
        "arquivos_total": len(set(arquivos)),
        "comandos_bash_total": len(comandos_bash),
        "comandos_bash": comandos_bash[:30],
        "subagentes_task": subagentes,
        "subagentes_task_total": len(subagentes),
        "personas_conversacionais": [
            {"agente": ag, "mencoes": n} for ag, n in personas.most_common()
        ],
        "skills_rodadas": sorted(set(skills_rodadas)),
        "commits": commits,
        "commits_total": len(commits),
        "artefatos": artefatos,
        "artefatos_total": len(artefatos),
        "tokens": tokens,
        "custo_usd": custo,
        "modelos": modelos_resumo,
        "fontes": fontes,
        "avisos": avisos,
    }


def _refinar_com_hook(eventos: list[dict], subagentes: list[dict], avisos: list[str]) -> None:
    """Usa pares PreToolUse/PostToolUse(Task) do log de hook para refinar
    a duração dos subagentes quando o transcript não deu timing preciso."""
    pares = []
    abertos: dict[str, datetime] = {}
    for ev in eventos:
        if ev.get("tool") != "Task":
            continue
        ts = _parse_ts(ev.get("ts"))
        chave = ev.get("subagent_type") or ev.get("description") or "task"
        if ev.get("evento") == "PreToolUse" and ts:
            abertos[chave] = ts
        elif ev.get("evento") == "PostToolUse" and ts and chave in abertos:
            dur = (ts - abertos.pop(chave)).total_seconds()
            pares.append((ev.get("subagent_type"), dur))
    # Aplica a primeira duração de hook a subagentes sem duração medida.
    duracoes_por_agente: dict[str, list[float]] = defaultdict(list)
    for nome, dur in pares:
        if nome:
            duracoes_por_agente[nome].append(dur)
    for sub in subagentes:
        if sub.get("duracao_segundos") is None:
            fila = duracoes_por_agente.get(sub["agente"])
            if fila:
                sub["duracao_segundos"] = fila.pop(0)
                sub["fonte_duracao"] = "hook"


def _coletar_commits(projeto: Path, ts_min, ts_max, avisos: list[str]):
    if ts_min is None:
        avisos.append("Sem janela temporal: commits da sessão não filtrados por data.")
    args = ["git", "-C", str(projeto), "log", "--pretty=format:%H%x09%cI%x09%s"]
    if ts_min:
        args += [f"--since={ts_min.isoformat()}"]
    if ts_max:
        args += [f"--until={ts_max.isoformat()}"]
    try:
        saida = subprocess.run(
            args, capture_output=True, text=True, timeout=15, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        avisos.append("git indisponível: commits da sessão não coletados.")
        return None
    if saida.returncode != 0:
        avisos.append("git log falhou: commits da sessão não coletados.")
        return None
    commits = []
    for linha in saida.stdout.splitlines():
        partes = linha.split("\t")
        if len(partes) >= 3:
            commits.append({"hash": partes[0][:10], "data": partes[1], "subject": partes[2]})
    return commits


def _coletar_artefatos(projeto: Path, ts_min, ts_max) -> list[str]:
    artefatos = []
    ini = ts_min.timestamp() if ts_min else None
    fim = ts_max.timestamp() if ts_max else None
    for rel in DIRS_ARTEFATOS:
        d = projeto / rel
        if not d.exists():
            continue
        for arq in d.glob("**/*.md"):
            try:
                mtime = arq.stat().st_mtime
            except OSError:
                continue
            if ini is not None and mtime < ini - 1:
                continue
            if fim is not None and mtime > fim + 86400:  # folga de 1 dia
                continue
            artefatos.append(str(arq.relative_to(projeto)))
    return sorted(set(artefatos))


def _estimar_custo(modelos_usage: dict) -> tuple[float, dict]:
    total = 0.0
    resumo = {}
    for modelo, uso in modelos_usage.items():
        preco = PRECO_PADRAO
        for chave, tabela in PRECOS_USD_POR_MILHAO.items():
            if chave in modelo.lower():
                preco = tabela
                break
        custo = (
            uso["input"] * preco["input"]
            + uso["output"] * preco["output"]
            + uso["cache_creation"] * preco["input"] * 1.25
            + uso["cache_read"] * preco["input"] * 0.1
        ) / 1_000_000
        total += custo
        resumo[modelo] = {"tokens": uso, "custo_usd": round(custo, 4)}
    return round(total, 4), resumo


def _detectar_cli(fontes: dict) -> str:
    # Heurística simples: transcript JSONL + hooks = Claude Code.
    if fontes.get("jsonl_hook") or fontes.get("transcript"):
        return "Claude Code"
    return "desconhecido (sem transcript — Codex/OpenCode)"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Telemetria de sessão do kairos-forge.")
    parser.add_argument("--hook", action="store_true",
                        help="Lê um evento de hook do stdin e faz append no log JSONL.")
    parser.add_argument("--agregar", metavar="TRANSCRIPT",
                        help="Caminho do transcript JSONL da conversa para agregar.")
    parser.add_argument("--jsonl", metavar="LOG",
                        help="Log JSONL de hook opcional (enriquecimento de timing).")
    parser.add_argument("--git", action="store_true", help="Coletar commits via git log.")
    parser.add_argument("--projeto", default=".", help="Diretório do projeto (default: cwd).")
    parser.add_argument("--inicio", help="ISO de início (sobrescreve o detectado).")
    parser.add_argument("--fim", help="ISO de fim (sobrescreve o detectado).")
    args = parser.parse_args(argv)

    if args.hook:
        return modo_hook()

    if args.agregar is not None:
        transcript = Path(args.agregar) if args.agregar else None
        jsonl_hook = Path(args.jsonl) if args.jsonl else None
        projeto = Path(args.projeto).resolve()
        resultado = agregar(transcript, jsonl_hook, args.git, projeto,
                            args.inicio, args.fim)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
