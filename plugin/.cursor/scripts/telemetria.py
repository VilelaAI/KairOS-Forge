#!/usr/bin/env python3
"""telemetria.py — agrega o registro de execução da fábrica (ADR-0021).

Lê `.agents/execucoes/*.jsonl` (escrito pelos hooks via execucao.py) e responde
a pergunta que define o nível de autonomia da fábrica:

    "que fração dos ciclos terminou sem intervenção humana?"

Enquanto essa pergunta não tem número, qualquer afirmação sobre L3/L4 é opinião.

Uso:
    telemetria.py resumo [--dias 7] [--json]      # números para o /auditar
    telemetria.py sessoes [--dias 7]              # uma linha por ciclo
    telemetria.py corroborar "<comando>" [--dias 30] [--json]
                                                  # usado pelo /validar: esse gate
                                                  # realmente rodou? com que resultado?

Definições (explícitas de propósito — métrica sem definição é chute com casa decimal):

  ciclo         sessão que invocou ao menos uma skill da fábrica
  intervenção   prompt humano DEPOIS do primeiro; o primeiro é o gatilho, não
                intervenção. Um ciclo com 0 intervenções rodou sozinho.
  autonomia     ciclos com 0 intervenções ÷ ciclos totais
  gate          comando classificado como teste/lint/tipos/build/migração
  verde de 1ª   primeira execução daquele gate na sessão saiu ok
  rodada de     execuções do mesmo gate além da primeira, na mesma sessão
  correção
  indeterminado saída do comando não permitiu afirmar sucesso nem falha. Conta
                separado — nunca vira "verde" por otimismo.

Só stdlib.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def carregar(raiz: Path, dias: int | None) -> list[dict]:
    pasta = raiz / ".agents" / "execucoes"
    if not pasta.is_dir():
        return []
    corte = None
    if dias:
        corte = datetime.now(timezone.utc) - timedelta(days=dias)
    eventos = []
    for arq in sorted(pasta.glob("*.jsonl")):
        for linha in arq.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            try:
                ev = json.loads(linha)
            except Exception:
                continue
            if corte:
                try:
                    if datetime.fromisoformat(ev["t"]) < corte:
                        continue
                except Exception:
                    pass
            eventos.append(ev)
    return eventos


def por_sessao(eventos: list[dict]) -> dict[str, dict]:
    s: dict[str, dict] = defaultdict(
        lambda: {
            "prompts": 0, "skills": [], "gates": [], "escritas": 0,
            "producao": 0, "delegacoes": 0, "inicio": None, "fim": None,
        }
    )
    for ev in eventos:
        d = s[ev.get("sessao", "?")]
        t = ev.get("t")
        if t and (d["inicio"] is None or t < d["inicio"]):
            d["inicio"] = t
        if t and (d["fim"] is None or t > d["fim"]):
            d["fim"] = t
        tipo = ev.get("tipo")
        if tipo == "prompt":
            d["prompts"] += 1
            if ev.get("skill"):
                d["skills"].append(ev["skill"])
        elif tipo == "comando" and ev.get("gate"):
            d["gates"].append((ev["gate"], ev.get("cmd", ""), ev.get("ok")))
        elif tipo == "escrita":
            d["escritas"] += 1
            if ev.get("producao"):
                d["producao"] += 1
        elif tipo == "delegacao":
            d["delegacoes"] += 1
    return dict(s)


def metricas(sessoes: dict[str, dict]) -> dict:
    ciclos = {k: v for k, v in sessoes.items() if v["skills"] and v["prompts"]}
    autonomos = [k for k, v in ciclos.items() if v["prompts"] <= 1]

    primeira_verde = falhou_primeira = indeterminada = 0
    rodadas_correcao = 0
    for v in sessoes.values():
        vistos: dict[str, bool | None] = {}
        for _, cmd, ok in v["gates"]:
            if cmd in vistos:
                rodadas_correcao += 1
                continue
            vistos[cmd] = ok
            if ok is True:
                primeira_verde += 1
            elif ok is False:
                falhou_primeira += 1
            else:
                indeterminada += 1
    total_gates = primeira_verde + falhou_primeira + indeterminada

    sem_gate = [
        k for k, v in sessoes.items()
        if v["producao"] and not v["gates"]
    ]

    def pct(a: int, b: int) -> float | None:
        return round(100 * a / b, 1) if b else None

    return {
        "ciclos": len(ciclos),
        "ciclos_autonomos": len(autonomos),
        "autonomia_pct": pct(len(autonomos), len(ciclos)),
        "intervencoes_medianas": mediana(
            [max(0, v["prompts"] - 1) for v in ciclos.values()]
        ),
        "gates_distintos": total_gates,
        "verdes_de_primeira": primeira_verde,
        "verdes_de_primeira_pct": pct(primeira_verde, total_gates),
        "falharam_de_primeira": falhou_primeira,
        "indeterminados": indeterminada,
        "rodadas_de_correcao": rodadas_correcao,
        "sessoes_com_producao_sem_gate": len(sem_gate),
        "sessoes_totais": len(sessoes),
        "skills_usadas": contar_skills(sessoes),
    }


def mediana(valores: list[int]) -> float | None:
    if not valores:
        return None
    v = sorted(valores)
    meio = len(v) // 2
    return float(v[meio]) if len(v) % 2 else (v[meio - 1] + v[meio]) / 2


def contar_skills(sessoes: dict[str, dict]) -> dict[str, int]:
    c: dict[str, int] = defaultdict(int)
    for v in sessoes.values():
        for s in v["skills"]:
            c[s] += 1
    return dict(sorted(c.items(), key=lambda kv: -kv[1]))


def normalizar(cmd: str) -> str:
    return " ".join(cmd.lower().split())


def corroborar(eventos: list[dict], alvo: str) -> dict:
    """O comando alegado em `verificado:` aparece na trajetória? Com que resultado?"""
    alvo_n = normalizar(alvo)
    achados = []
    for ev in eventos:
        if ev.get("tipo") != "comando":
            continue
        cmd_n = normalizar(ev.get("cmd", ""))
        if not cmd_n:
            continue
        if alvo_n in cmd_n or cmd_n in alvo_n:
            achados.append(
                {"t": ev.get("t"), "cmd": ev.get("cmd"), "ok": ev.get("ok"),
                 "gate": ev.get("gate"), "sessao": ev.get("sessao")}
            )
    if not achados:
        veredicto = "nao_corroborado"
    elif any(a["ok"] is True for a in achados):
        veredicto = "corroborado"
    elif all(a["ok"] is False for a in achados):
        veredicto = "corroborado_com_falha"
    else:
        veredicto = "corroborado_indeterminado"
    return {"alegado": alvo, "veredicto": veredicto,
            "execucoes": achados[-5:], "total": len(achados)}


# --- apresentação ------------------------------------------------------------------

def imprimir_resumo(m: dict, dias: int | None) -> None:
    janela = f"últimos {dias} dias" if dias else "todo o histórico"
    print(f"📊 Telemetria da fábrica — {janela}\n")
    if not m["sessoes_totais"]:
        print("  sem registro de execução ainda.")
        print("  Os hooks gravam em .agents/execucoes/ — veja ADR-0021 se estiver vazio")
        print("  depois de algumas sessões (hooks não instalados ou CLI sem suporte).")
        return

    aut = m["autonomia_pct"]
    print(f"  Autonomia:            {aut if aut is not None else '—'}%"
          f"  ({m['ciclos_autonomos']}/{m['ciclos']} ciclos sem intervenção)")
    print(f"  Intervenções/ciclo:   {m['intervencoes_medianas']} (mediana)")
    vp = m["verdes_de_primeira_pct"]
    print(f"  Gates verdes de 1ª:   {vp if vp is not None else '—'}%"
          f"  ({m['verdes_de_primeira']}/{m['gates_distintos']})")
    print(f"  Rodadas de correção:  {m['rodadas_de_correcao']}")
    if m["indeterminados"]:
        print(f"  Indeterminados:       {m['indeterminados']}  (saída não permitiu afirmar)")
    if m["sessoes_com_producao_sem_gate"]:
        print(f"  ⚠️  Código de produção escrito sem nenhum gate: "
              f"{m['sessoes_com_producao_sem_gate']} sessão(ões)")
    if m["skills_usadas"]:
        top = ", ".join(f"{k} ({v})" for k, v in list(m["skills_usadas"].items())[:6])
        print(f"\n  Skills mais usadas:   {top}")


def imprimir_sessoes(sessoes: dict[str, dict]) -> None:
    if not sessoes:
        print("sem registro de execução ainda.")
        return
    print(f"{'sessão':<18} {'skills':<28} {'prompts':>7} {'gates':>6} {'prod':>5}")
    print("-" * 68)
    for sid, v in sorted(sessoes.items(), key=lambda kv: kv[1]["inicio"] or ""):
        skills = ",".join(dict.fromkeys(v["skills"]))[:26]
        print(f"{sid:<18} {skills:<28} {v['prompts']:>7} {len(v['gates']):>6} {v['producao']:>5}")


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__.strip())
        return 1

    como_json = "--json" in args
    args = [a for a in args if a != "--json"]

    dias: int | None = None
    if "--dias" in args:
        i = args.index("--dias")
        try:
            dias = int(args[i + 1])
        except (IndexError, ValueError):
            print("erro: --dias precisa de um número", file=sys.stderr)
            return 1
        args = args[:i] + args[i + 2:]

    raiz = Path.cwd()
    comando = args[0]
    eventos = carregar(raiz, dias)

    if comando == "resumo":
        m = metricas(por_sessao(eventos))
        if como_json:
            print(json.dumps(m, ensure_ascii=False, indent=2))
        else:
            imprimir_resumo(m, dias)
        return 0

    if comando == "sessoes":
        imprimir_sessoes(por_sessao(eventos))
        return 0

    if comando == "corroborar":
        if len(args) < 2:
            print('erro: uso — telemetria.py corroborar "<comando>"', file=sys.stderr)
            return 1
        r = corroborar(carregar(raiz, dias or 30), args[1])
        if como_json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            rotulo = {
                "corroborado": "✅ corroborado — o comando rodou e passou",
                "corroborado_com_falha": "❌ corroborado, mas FALHOU nas execuções registradas",
                "corroborado_indeterminado": "⚠️  rodou, mas a saída não permite afirmar o resultado",
                "nao_corroborado": "🚫 NÃO corroborado — nenhuma execução registrada",
            }[r["veredicto"]]
            print(f'{rotulo}\n   alegado: {r["alegado"]}\n   execuções: {r["total"]}')
            for e in r["execucoes"]:
                print(f'   · {e["t"]}  ok={e["ok"]}  {e["cmd"][:70]}')
        # Exit 1 quando a alegação não se sustenta — usável em CI/pre-commit.
        return 0 if r["veredicto"] == "corroborado" else 1

    print(__doc__.strip())
    return 1


if __name__ == "__main__":
    sys.exit(main())
