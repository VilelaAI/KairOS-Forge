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
    telemetria.py ruido [--dias 90] [--json]      # achados de revisão descartados por
                                                  # revisor — calibra quem grita à toa
    telemetria.py prs [--dias 30] [--fonte gh|git] [--marca REGEX]... [--json]
                                                  # autonomia de PR, medida pelo git
                                                  # (ADR-0044) — funciona sem hook
    telemetria.py comparar [--dias 90] [--fonte gh|git] [--marca REGEX]... [--json]
                                                  # a entrega da fábrica × a humana:
                                                  # PRs revertidos e corrigidos depois
    telemetria.py tokens [--dias 7] [--json]      # tokens por sessão, como o transcript
                                                  # registrou (ADR-0048)
    telemetria.py por-spec [--dias 7] [--json]    # os mesmos tokens somados por SPEC, pela
                                                  # chave do branch (ADR-0050, emenda)
    telemetria.py espera [--dias 30] [--json]     # tempo por estado de cada ciclo: quanto
                                                  # foi trabalho e quanto esperou alguém
    telemetria.py custo-eval <pasta> [--baseline NOME] [--teto PCT] [--json]
                                                  # custo por versão no /avaliar: uma
                                                  # subpasta por versão, um `claude -p
                                                  # --output-format json` por caso

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
  ruído         achado de revisão que o humano marcou `descartado: <motivo>` na
                linha do achado, em `docs/specs/revisoes/`. Revisor com 30% de
                ruído é revisor que o time aprende a ignorar (ADR-0039) — e
                aí o 🔴 verdadeiro passa junto. Sem marcação, ruído é 0 e o
                número é declarado "não medido", não "bom".
  commit de    commit com o trailer `Fabrica: kairos-forge`, o trailer
  agente        `Co-Authored-By: Claude` que o Claude Code põe por padrão, ou
                autor `kairos-forge` (os templates de CI). Mais as `--marca`
                que o projeto declarar. Todo o resto é commit humano.
  autonomia    PRs mesclados com ao menos um commit de agente e NENHUM commit
  de PR         humano ÷ PRs mesclados com ao menos um commit de agente
                (ADR-0044). Sai do histórico, não da trajetória: o modelo não
                escreve o merge, e o número existe onde não há hook. Sem PR da
                fábrica, é "não medido", nunca 0%.
  tokens novos  entrada + escrita de cache + saída, somados por resposta do modelo
                como o transcript registrou, cada resposta uma vez (ADR-0048).
                O cache lido vem à parte: é relido a cada resposta, domina a
                soma e custa uma fração. Só o Claude Code grava hoje; nos
                outros CLIs é "não medido", nunca 0.

Só stdlib.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def carregar(raiz: Path, dias: int | None) -> list[dict]:
    pasta = pasta_do_projeto(raiz, "execucoes")       # onde o hook grava, mesmo num worktree
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


# Evento que só conta: tipo → campo da sessão.
try:
    from execucao import pasta_do_projeto
except Exception:                     # cópia avulsa do script, sem o execucao.py ao lado
    def pasta_do_projeto(raiz, nome: str) -> Path:
        return Path(raiz) / ".agents" / nome

CONTADORES = {"delegacao": "delegacoes", "guardrail_erro": "erros_guardrail"}


def por_sessao(eventos: list[dict]) -> dict[str, dict]:
    s: dict[str, dict] = defaultdict(
        lambda: {
            "prompts": 0, "skills": [], "gates": [], "escritas": 0,
            "producao": 0, "delegacoes": 0, "recusas": [], "inicio": None, "fim": None,
            "erros_guardrail": 0,
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
        elif tipo in CONTADORES:
            d[CONTADORES[tipo]] += 1
        elif tipo == "recusa":
            d["recusas"].append((ev.get("classe", "?"), ev.get("modo", "?")))
    return dict(s)


# --- tokens (ADR-0048) ------------------------------------------------------------------
USO = ("entrada", "cache_escrita", "cache_leitura", "saida", "respostas")
VINCULO = re.compile(r"quadro\.py\s+vincular\s+(\S+)\s+(\S+)")


def zero() -> dict[str, int]:
    return {campo: 0 for campo in USO}


def somar(alvo: dict[str, int], parte: dict) -> None:
    for campo in USO:
        valor = parte.get(campo)
        if isinstance(valor, int) and not isinstance(valor, bool):
            alvo[campo] += valor


def novos(uso: dict) -> int:
    """Tokens novos: o que entrou, o que foi escrito no cache e o que saiu. Sem o cache lido."""
    return sum(int(uso.get(c) or 0) for c in ("entrada", "cache_escrita", "saida"))


def _delta(leitura: dict, base: dict | None) -> dict[str, int]:
    """O que a sessão gastou desde a leitura anterior. Leitura menor que a base (transcript
    novo na mesma sessão) recomeça a contagem em vez de dar número negativo."""
    if base is None:
        return {c: int(leitura.get(c) or 0) for c in USO}
    if any(int(leitura.get(c) or 0) < int(base.get(c) or 0) for c in USO):
        return {c: int(leitura.get(c) or 0) for c in USO}
    return {c: int(leitura.get(c) or 0) - int(base.get(c) or 0) for c in USO}


def _vinculo(ev: dict, slug: str | None) -> str | None:
    """A tarefa que este evento vincula à sessão, se for o `quadro.py vincular` do quadro."""
    m = VINCULO.search(ev.get("cmd") or "") if ev.get("tipo") == "comando" else None
    return m.group(2) if m and m.group(1) == slug else None


def _leitura(ev: dict) -> dict | None:
    tokens = ev.get("tokens") if ev.get("tipo") == "sessao_fim" else None
    return tokens if isinstance(tokens, dict) else None


def _gastos(eventos: list[dict], q: dict):
    """(sessão, tarefa vinculada ou None, instante, gasto) de cada leitura dentro do quadro.

    O gasto é a diferença para a leitura anterior da mesma sessão, calculada também fora
    da janela: senão a primeira leitura de uma sessão antiga traria tudo o que veio antes.
    """
    inicio, fim = q.get("aberto_em") or "", q.get("encerrado_em") or "9999"
    corrente: dict[str, str] = {}
    anterior: dict[str, dict] = {}
    for ev in eventos:
        sessao, t = ev.get("sessao", "?"), ev.get("t", "")
        corrente[sessao] = _vinculo(ev, q.get("slug")) or corrente.get(sessao, "")
        leitura = _leitura(ev)
        if leitura is None:
            continue
        gasto, anterior[sessao] = _delta(leitura, anterior.get(sessao)), leitura
        if inicio <= t <= fim:
            yield sessao, corrente[sessao] or None, t, gasto


def _categoria(task: dict, t: str) -> str:
    """Gasto de tarefa compensada depois dele foi trabalho desfeito (ADR-0036)."""
    if any((c.get("em") or "") >= t for c in task.get("compensacoes", [])):
        return "desfeita"
    return "concluida" if task["estado"] == "concluida" else "aberta"


CATEGORIAS = ("concluida", "desfeita", "aberta")


def tokens_da_mobilizacao(eventos: list[dict], q: dict) -> dict:
    """Os tokens gastos durante um quadro do /mobilizar, divididos por tarefa.

    Cada sessão grava o acumulado a cada turno; o que ela gastou entre uma leitura e a
    seguinte vai para a tarefa a que estava vinculada naquele momento (`quadro.py
    vincular`, rodado pelo worker na própria sessão). Sem vínculo — a líder, ou um worker
    que não vinculou — o gasto fica em "sem tarefa".
    """
    por_tarefa: dict[str, dict[str, dict[str, int]]] = {}
    sem_tarefa, sessoes = zero(), set()
    for sessao, tid, t, gasto in _gastos(eventos, q):
        sessoes.add(sessao)
        task = q.get("tasks", {}).get(tid or "")
        if task is None:
            somar(sem_tarefa, gasto)
            continue
        conta = por_tarefa.setdefault(tid, {k: zero() for k in CATEGORIAS})
        somar(conta[_categoria(task, t)], gasto)
    categorias = {k: zero() for k in CATEGORIAS}
    for conta in por_tarefa.values():
        for k, uso in conta.items():
            somar(categorias[k], uso)
    categorias["sem_tarefa"] = sem_tarefa
    total = zero()
    for uso in categorias.values():
        somar(total, uso)
    return {"medido": bool(sessoes), "sessoes": len(sessoes), "total": total,
            "categorias": categorias, "por_tarefa": por_tarefa}


def ultimas_leituras(eventos: list[dict]) -> dict[str, dict]:
    """A leitura mais recente de cada sessão: o Stop grava o acumulado a cada turno."""
    saida: dict[str, dict] = {}
    for ev in eventos:
        leitura = _leitura(ev)
        if leitura is not None:
            saida[ev.get("sessao", "?")] = leitura
    return saida


def resumo_de_tokens(eventos: list[dict]) -> dict:
    uso = zero()
    leituras = ultimas_leituras(eventos)
    for leitura in leituras.values():
        somar(uso, leitura)
    return {"sessoes_com_tokens": len(leituras), "tokens_novos": novos(uso),
            "tokens_cache_lido": uso["cache_leitura"]}


def faltas_de_fonte(eventos: list[dict]) -> dict:
    """Perguntas à pessoa por falta de fonte (`falta-fonte:`), da última leitura de cada
    sessão. Só conta onde o Stop leu o transcript; sem leitura, não medido, nunca zero."""
    por_sessao: dict[str, dict] = {}
    for ev in eventos:
        if _leitura(ev) is not None:
            por_sessao[ev.get("sessao", "?")] = ev.get("faltas_de_fonte") or {}
    fontes: dict[str, dict[str, int]] = {}
    for faltas in por_sessao.values():
        for fonte, n in faltas.items():
            if isinstance(n, int) and not isinstance(n, bool) and n > 0:
                f = fontes.setdefault(str(fonte), {"perguntas": 0, "sessoes": 0})
                f["perguntas"] += n
                f["sessoes"] += 1
    return {"faltas_medidas": bool(por_sessao),
            "faltas_de_fonte": dict(sorted(fontes.items(), key=lambda kv: (-kv[1]["perguntas"], kv[0])))}


def linha_de_faltas_do_resumo(m: dict) -> str:
    if not m.get("faltas_medidas"):
        return "  Fontes que faltaram:  não medidas (o Stop só lê o transcript no Claude Code)"
    if not m["faltas_de_fonte"]:
        return "  Fontes que faltaram:  nenhuma pergunta por falta de fonte"
    partes = ", ".join(f"{f} ({v['perguntas']} pergunta(s) em {v['sessoes']} sessão(ões))"
                       for f, v in list(m["faltas_de_fonte"].items())[:5])
    return f"  Fontes que faltaram:  {partes}"


def linha_de_tokens_do_resumo(m: dict) -> str:
    if not m.get("sessoes_com_tokens"):
        return "  Tokens:               não medidos (o Stop só grava no Claude Code)"
    return (f"  Tokens novos:         {formatar(m['tokens_novos'])}  "
            f"(+ {formatar(m['tokens_cache_lido'])} de cache lido, "
            f"{m['sessoes_com_tokens']} sessão(ões) medida(s))")


def cmd_tokens(eventos: list[dict], como_json: bool) -> int:
    leituras = ultimas_leituras(eventos)
    if como_json:
        print(json.dumps(leituras, ensure_ascii=False, indent=2))
        return 0
    if not leituras:
        print("Tokens não medidos: nenhuma leitura do hook Stop na janela. Hoje só o "
              "Claude Code grava (ADR-0048).")
        return 0
    print(f"{'sessão':<18} {'respostas':>9} {'novos':>10} {'cache lido':>11}  modelos")
    print("-" * 72)
    for sid, u in leituras.items():
        print(f"{sid:<18} {u.get('respostas', 0):>9} {formatar(novos(u)):>10} "
              f"{formatar(int(u.get('cache_leitura') or 0)):>11}  "
              f"{', '.join(u.get('modelos') or [])}")
    return 0


def _cmd_sessoes(eventos: list[dict], como_json: bool) -> int:
    imprimir_sessoes(por_sessao(eventos))
    return 0


# --- custo por SPEC: a chave entre sessão e SPEC (aula 5 do Tech Leads Club) ---------
# Cada sessão grava o branch (início e cada Stop) e os ids de SPEC citados no prompt. A
# SPEC da sessão sai, nesta ordem: do ciclo aberto naquele branch, do id no nome do branch,
# do primeiro id citado. Sessão sem nenhum dos três fica em "sem SPEC" e continua medida.

SPEC_NO_TEXTO = re.compile(r"\bSPEC-\d+\b", re.I)


def ler_ciclos(raiz: Path) -> list[dict]:
    pasta = pasta_do_projeto(raiz, "ciclo")
    saida = []
    for arq in sorted(pasta.glob("*.json")) if pasta.is_dir() else []:
        try:
            saida.append(json.loads(arq.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return saida


def spec_da_sessao(evs: list[dict], spec_do_branch: dict[str, str]) -> tuple[str | None, str]:
    """(SPEC, por onde foi achada) — `ciclo`, `branch`, `prompt` ou `sem chave`."""
    branch = next((ev["branch"] for ev in reversed(evs) if ev.get("branch")), None)
    no_nome = SPEC_NO_TEXTO.search(branch or "")
    citada = next((ev["specs"][0] for ev in evs if ev.get("specs")), None)
    for spec, via in ((spec_do_branch.get(branch or ""), "ciclo"),
                      (no_nome.group(0).upper() if no_nome else None, "branch"),
                      (citada, "prompt")):
        if spec:
            return spec, via
    return None, "sem chave"


def tokens_por_spec(eventos: list[dict], raiz: Path) -> dict:
    spec_do_branch = {c["branch"]: c["spec"] for c in ler_ciclos(raiz) if c.get("branch")}
    grupos: dict[str, list[dict]] = defaultdict(list)
    for ev in eventos:
        grupos[ev.get("sessao", "?")].append(ev)
    specs: dict[str, dict] = {}
    for sid, uso in ultimas_leituras(eventos).items():
        spec, via = spec_da_sessao(grupos.get(sid, []), spec_do_branch)
        r = specs.setdefault(spec or "sem SPEC", {"sessoes": 0, "novos": 0, "cache_lido": 0,
                                                   "por": {}})
        r["sessoes"] += 1
        r["novos"] += novos(uso)
        r["cache_lido"] += int(uso.get("cache_leitura") or 0)
        r["por"][via] = r["por"].get(via, 0) + 1
    ordem = sorted(specs.items(), key=lambda kv: (kv[0] == "sem SPEC", -kv[1]["novos"]))
    return {"medido": bool(specs), "specs": dict(ordem)}


def cmd_por_spec(eventos: list[dict], raiz: Path, como_json: bool) -> int:
    r = tokens_por_spec(eventos, raiz)
    if como_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif not r["medido"]:
        print("Tokens por SPEC não medidos: nenhuma leitura do hook Stop na janela. Hoje só "
              "o Claude Code grava (ADR-0048).")
    else:
        print(f"{'SPEC':<14} {'sessões':>8} {'novos':>10} {'cache lido':>11}  chave")
        print("-" * 64)
        for spec, v in r["specs"].items():
            chave = ", ".join(f"{k} {n}" for k, n in v["por"].items())
            print(f"{spec:<14} {v['sessoes']:>8} {formatar(v['novos']):>10} "
                  f"{formatar(v['cache_lido']):>11}  {chave}")
    return 0


# --- tempo e espera por estado do ciclo (aula 5 do Tech Leads Club) ---------------
# Acelerar o código 10× rende uns 10% na entrega, porque o trabalho passa a maior parte do
# tempo esperando alguém: a lei de Amdahl no ciclo de desenvolvimento. O histórico de cada
# ciclo já tem a hora de cada transição; esta conta só lê. Esperar pessoa = os estados
# `aguardando_*` (os três gates do planejamento) e `pronto_para_pr` (o PR esperando merge).
# `escalado` e `encerrado` são terminais: o relógio para neles.

TERMINAIS_DO_CICLO = {"encerrado", "escalado"}


def esperando_pessoa(estado: str) -> bool:
    return estado.startswith("aguardando_") or estado == "pronto_para_pr"


def _instante(t) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(t))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _horas(segundos: float) -> float:
    return round(segundos / 3600, 1)


def segundos_por_estado(hist: list[tuple[str, datetime]], agora: datetime) -> dict[str, float]:
    soma: dict[str, float] = defaultdict(float)
    for i, (estado, inicio) in enumerate(hist):
        fim = hist[i + 1][1] if i + 1 < len(hist) else (None if estado in TERMINAIS_DO_CICLO
                                                       else agora)
        if fim is not None:
            soma[estado] += max(0.0, (fim - inicio).total_seconds())
    return soma


def tempos_do_ciclo(c: dict, agora: datetime) -> dict | None:
    hist = [(h.get("para"), _instante(h.get("t"))) for h in c.get("historico") or []]
    hist = [(e, t) for e, t in hist if e and t]
    if not hist:
        return None
    por_estado = segundos_por_estado(hist, agora)
    espera = {e: s for e, s in por_estado.items() if esperando_pessoa(e)}
    total = sum(por_estado.values())
    maior = max(espera.items(), key=lambda kv: kv[1], default=(None, 0.0))
    return {
        "spec": c.get("spec"), "estado": c.get("estado"), "ultima": hist[-1][1].isoformat(),
        "lead_h": _horas(total), "espera_h": _horas(sum(espera.values())),
        "trabalho_h": _horas(total - sum(espera.values())),
        "espera_pct": round(100 * sum(espera.values()) / total) if total else None,
        "maior_espera": {"estado": maior[0], "h": _horas(maior[1])} if maior[0] else None,
        "voltas": {g: sum(1 for e, _ in hist if e == f"corrigindo_{g}")
                   for g in ("spec", "validacao", "revisao")},
    }


def espera_dos_ciclos(raiz: Path, dias: int | None, agora: datetime | None = None) -> dict:
    agora = agora or datetime.now(timezone.utc)
    corte = agora - timedelta(days=dias) if dias else None
    linhas = []
    for c in ler_ciclos(raiz):
        t = tempos_do_ciclo(c, agora)
        aberto = c.get("estado") not in TERMINAIS_DO_CICLO
        if t and (aberto or corte is None or datetime.fromisoformat(t["ultima"]) >= corte):
            linhas.append(t)
    total = sum(l["lead_h"] for l in linhas)
    espera = sum(l["espera_h"] for l in linhas)
    return {"ciclos": linhas, "lead_h": round(total, 1), "espera_h": round(espera, 1),
            "espera_pct": round(100 * espera / total) if total else None}


def _h(x: float) -> str:
    return f"{x:.1f} h".replace(".", ",")


def cmd_espera(raiz: Path, dias: int | None, como_json: bool) -> int:
    r = espera_dos_ciclos(raiz, dias)
    if como_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    janela = f"últimos {dias} dias" if dias else "todo o histórico"
    print(f"⏱️  Tempo por estado do ciclo — {janela} (e os ciclos abertos)\n")
    if not r["ciclos"]:
        print("   nenhum ciclo em .agents/ciclo/ — o /entregar abre um por SPEC.")
        return 0
    for l in r["ciclos"]:
        maior = (f" · maior espera: {l['maior_espera']['estado']} {_h(l['maior_espera']['h'])}"
                 if l["maior_espera"] else "")
        voltas = ", ".join(f"{g} {n}" for g, n in l["voltas"].items() if n) or "nenhuma"
        print(f"   {l['spec']:<10} {l['estado']:<22} lead {_h(l['lead_h'])} · trabalho "
              f"{_h(l['trabalho_h'])} · esperando pessoa {_h(l['espera_h'])} "
              f"({l['espera_pct']}%){maior} · voltas: {voltas}")
    print(f"\n   Total: {len(r['ciclos'])} ciclo(s), esperando pessoa {r['espera_pct']}% do "
          "tempo. Esperar pessoa = aguardando_* e pronto_para_pr (PR esperando merge).")
    return 0


def _cmd_ruido(raiz: Path, dias: int | None, como_json: bool) -> int:
    r = ruido(raiz, dias)
    if como_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        imprimir_ruido(r, dias)
    return 0


# Comandos que só leem e mostram: (eventos, raiz, dias, json) → exit code.
SIMPLES = {
    "sessoes": lambda ev, raiz, dias, j: _cmd_sessoes(ev, j),
    "tokens": lambda ev, raiz, dias, j: cmd_tokens(ev, j),
    "por-spec": lambda ev, raiz, dias, j: cmd_por_spec(ev, raiz, j),
    "espera": lambda ev, raiz, dias, j: cmd_espera(raiz, dias, j),
    "ruido": lambda ev, raiz, dias, j: _cmd_ruido(raiz, dias, j),
}


def formatar(n: int) -> str:
    """1234567 → '1,2 mi'; 45300 → '45 mil'. Número de relatório, não de planilha."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} mi".replace(".", ",")
    if n >= 10_000:
        return f"{round(n / 1000)} mil"
    return f"{n:,}".replace(",", ".")


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

    recusas = [r for v in sessoes.values() for r in v["recusas"]]
    por_classe: dict[str, int] = defaultdict(int)
    em_aviso = 0
    for classe, modo in recusas:
        por_classe[classe] += 1
        if modo == "aviso":
            em_aviso += 1

    return {
        "recusas_total": len(recusas),
        "recusas_por_classe": dict(sorted(por_classe.items(), key=lambda kv: -kv[1])),
        "recusas_em_modo_aviso": em_aviso,
        "sessoes_com_recusa": sum(1 for v in sessoes.values() if v["recusas"]),
        "falhas_do_guardrail": sum(v["erros_guardrail"] for v in sessoes.values()),
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


# --- ruído da revisão (ADR-0039) ---------------------------------------------------
# Lê os relatórios salvos pelo /revisar, não a trajetória: o achado e a marcação de
# descarte vivem no arquivo. Convenção mínima, verificável por olho: a linha do achado
# começa com `- [Revisor]` e, se o humano o descartou, contém `descartado: <motivo>`.

SEVERIDADES = {"🔴": "critico", "🟠": "alto", "🟡": "medio", "🔵": "baixo"}
ACHADO = re.compile(r"^\s*[-*]\s*\[(?P<revisor>[^\]]+)\]\s*(?P<texto>.+)$")
DESCARTADO = re.compile(r"(?i)\bdescartad[oa]\s*:")
DATA_NO_NOME = re.compile(r"(\d{4}-\d{2}-\d{2})")


def achados_de(texto: str) -> list[dict]:
    achados, severidade = [], None
    for linha in texto.splitlines():
        if linha.startswith("#"):
            severidade = next((v for k, v in SEVERIDADES.items() if k in linha), None)
            continue
        if linha.startswith("```"):
            severidade = None
            continue
        if severidade is None:
            continue
        m = ACHADO.match(linha)
        if not m:
            continue
        achados.append({"revisor": m.group("revisor").strip(), "severidade": severidade,
                        "descartado": bool(DESCARTADO.search(m.group("texto")))})
    return achados


def ruido(raiz: Path, dias: int | None) -> dict:
    pasta = raiz / "docs" / "specs" / "revisoes"
    corte = (datetime.now(timezone.utc) - timedelta(days=dias)).date() if dias else None
    por_revisor: dict[str, dict] = defaultdict(lambda: {"achados": 0, "descartados": 0})
    por_severidade: dict[str, dict] = defaultdict(lambda: {"achados": 0, "descartados": 0})
    relatorios = 0
    for arq in sorted(pasta.glob("*.md")) if pasta.is_dir() else []:
        if corte:
            m = DATA_NO_NOME.search(arq.name)
            try:
                if m and datetime.strptime(m.group(1), "%Y-%m-%d").date() < corte:
                    continue
            except ValueError:
                pass
        relatorios += 1
        for a in achados_de(arq.read_text(encoding="utf-8", errors="replace")):
            for bucket in (por_revisor[a["revisor"]], por_severidade[a["severidade"]]):
                bucket["achados"] += 1
                bucket["descartados"] += int(a["descartado"])
    total = sum(v["achados"] for v in por_revisor.values())
    descartados = sum(v["descartados"] for v in por_revisor.values())

    def taxa(b: dict) -> float | None:
        return round(100 * b["descartados"] / b["achados"]) if b["achados"] else None

    return {
        "relatorios": relatorios,
        "achados": total,
        "descartados": descartados,
        "ruido_pct": taxa({"achados": total, "descartados": descartados}),
        "medido": descartados > 0,
        "por_revisor": {k: {**v, "ruido_pct": taxa(v)}
                        for k, v in sorted(por_revisor.items(),
                                           key=lambda kv: -kv[1]["achados"])},
        "por_severidade": {k: {**v, "ruido_pct": taxa(v)} for k, v in por_severidade.items()},
    }


def imprimir_ruido(r: dict, dias: int | None) -> None:
    janela = f"últimos {dias} dias" if dias else "todo o histórico"
    print(f"📣 Ruído da revisão — {janela}\n")
    if not r["relatorios"]:
        print("  nenhum relatório em docs/specs/revisoes/ — o /revisar salva um por rodada.")
        return
    print(f"  Relatórios: {r['relatorios']}   Achados: {r['achados']}   "
          f"Descartados: {r['descartados']}")
    if not r["medido"]:
        print("  Ruído: não medido — nenhum achado marcado `descartado: <motivo>`.\n"
              "  Zero descartes em muitos achados é mais provável ser ninguém marcando do que\n"
              "  revisor perfeito. A marcação é do humano, na linha do achado.")
        return
    print(f"  Ruído geral: {r['ruido_pct']}%   (limiar de atenção: 30% — o time passa a ignorar)\n")
    print(f"  {'revisor':<14} {'achados':>8} {'descart.':>9} {'ruído':>7}")
    print("  " + "-" * 42)
    for nome, v in r["por_revisor"].items():
        pct = f"{v['ruido_pct']}%" if v["ruido_pct"] is not None else "—"
        alerta = "  ⚠️" if (v["ruido_pct"] or 0) >= 30 and v["achados"] >= 3 else ""
        print(f"  {nome:<14} {v['achados']:>8} {v['descartados']:>9} {pct:>7}{alerta}")


# --- autonomia de PR, medida pelo git (ADR-0044) -----------------------------------
# A taxa de ciclos sem intervenção sai da trajetória, que só existe onde há hook. Esta
# sai do histórico: dos PRs mesclados em que a fábrica escreveu código, quantos chegaram
# ao merge sem nenhum commit humano. O modelo não escreve o histórico do merge, e o
# número existe no Codex, no OpenCode e no CI, onde a trajetória não existe.

MARCAS_AGENTE = (
    re.compile(r"(?im)^f[aá]brica:\s*kairos-forge\s*$"), # trailer da fábrica
    re.compile(r"(?im)^co-authored-by:\s*claude\b"),     # trailer padrão do Claude Code
)
AUTORES_AGENTE = {"kairos-forge"}                          # commits dos templates de CI
CAMPOS_GH = "number,title,headRefName,mergedAt,mergeCommit,commits,closingIssuesReferences"


def commit_de_agente(commit: dict, extras: tuple = ()) -> bool:
    msg = commit.get("mensagem") or ""
    if any(m.search(msg) for m in (*MARCAS_AGENTE, *extras)):
        return True
    return str(commit.get("autor") or "").strip().lower() in AUTORES_AGENTE


def _data(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def _prs_do_gh(raiz: Path, corte: datetime | None) -> list[dict] | None:
    """PRs mesclados pelo `gh`, cobrindo merge, squash e rebase. None se não der."""
    if not shutil.which("gh"):
        return None
    try:
        r = subprocess.run(["gh", "pr", "list", "--state", "merged", "--limit", "200",
                            "--json", CAMPOS_GH], cwd=raiz, capture_output=True,
                           text=True, timeout=90)
        dados = json.loads(r.stdout or "[]") if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if not isinstance(dados, list):
        return None
    prs = []
    for p in dados:
        quando = _data(p.get("mergedAt"))
        if corte and quando and quando < corte:
            continue
        commits = []
        for c in p.get("commits") or []:   # do mais antigo para o mais novo
            autores = c.get("authors") or [{}]
            commits.append({"oid": c.get("oid"),
                            "autor": autores[0].get("name") or autores[0].get("login") or "",
                            "mensagem": "\n\n".join(x for x in (c.get("messageHeadline"),
                                                                 c.get("messageBody")) if x)})
        prs.append({"numero": p.get("number"), "titulo": p.get("title") or "",
                    "branch": p.get("headRefName") or "", "mesclado_em": p.get("mergedAt"),
                    "entrega": (p.get("mergeCommit") or {}).get("oid"),
                    "issues": [i["number"] for i in p.get("closingIssuesReferences") or []
                               if i.get("number")],
                    "commits": commits})
    return prs


MERGE_DE_PR = re.compile(r"^Merge pull request #(\d+) from [^/\s]+/(\S+)")
MERGE_DE_BRANCH = re.compile(r"^Merge (?:remote-tracking )?branch '([^']+)'")
NUMERO_NO_TITULO = re.compile(r"\(#(\d+)\)\s*$")   # o "título (#14)" do merge do GitHub


def _prs_do_git(raiz: Path, dias: int | None) -> list[dict]:
    """Merges com commit de merge na primeira linha de HEAD. Squash e rebase não aparecem."""
    def git(*args: str) -> str:
        try:
            r = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True,
                               text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return ""
        return r.stdout if r.returncode == 0 else ""

    args = ["log", "--merges", "--first-parent", "--format=%H%x1f%P%x1f%cI%x1f%s%x1f%b%x1e"]
    if dias:
        args.append(f"--since={dias}.days")
    prs = []
    for registro in git(*args).split("\x1e"):
        partes = registro.strip("\n").split("\x1f")
        if len(partes) != 5 or len(partes[1].split()) < 2:
            continue
        oid, pais, quando, assunto, corpo = partes
        p1, p2 = pais.split()[:2]
        commits = []
        for bloco in git("log", "--no-merges", "--reverse", "--format=%H%x1f%an%x1f%B%x1e",
                         f"{p1}..{p2}").split("\x1e"):
            campos = bloco.strip("\n").split("\x1f")
            if len(campos) == 3:
                commits.append({"oid": campos[0], "autor": campos[1], "mensagem": campos[2]})
        m = MERGE_DE_PR.match(assunto)
        b = MERGE_DE_BRANCH.match(assunto)
        n = m or NUMERO_NO_TITULO.search(assunto)
        titulo = titulo_do_commit({"assunto": assunto, "corpo": corpo})
        prs.append({"numero": int(n.group(1)) if n else None, "titulo": titulo,
                    "branch": m.group(2) if m else (b.group(1) if b else ""),
                    "mesclado_em": quando, "entrega": oid, "issues": [], "commits": commits})
    return prs


def prs_mesclados(raiz: Path, dias: int | None, fonte: str | None = None) -> tuple[str, list[dict]]:
    """(fonte, PRs mesclados na janela). `gh` quando dá; senão os merges do git."""
    if fonte != "git":
        corte = datetime.now(timezone.utc) - timedelta(days=dias) if dias else None
        prs = _prs_do_gh(raiz, corte)
        if prs is not None:
            return "gh", prs
        if fonte == "gh":
            return "gh", []
    return "git", _prs_do_git(raiz, dias)


def autonomia_de_prs(prs: list[dict], extras: tuple = ()) -> dict:
    linhas = []
    for p in prs:
        agente = sum(1 for c in p["commits"] if commit_de_agente(c, extras))
        humano = len(p["commits"]) - agente
        linhas.append({"numero": p.get("numero"), "titulo": (p.get("titulo") or "")[:80],
                       "branch": p.get("branch"), "agente": agente, "humano": humano,
                       "da_fabrica": agente > 0, "autonomo": agente > 0 and humano == 0})
    da_fabrica = [l for l in linhas if l["da_fabrica"]]
    autonomos = [l for l in da_fabrica if l["autonomo"]]
    return {
        "mesclados": len(linhas),
        "da_fabrica": len(da_fabrica),
        "autonomos": len(autonomos),
        "taxa": round(100 * len(autonomos) / len(da_fabrica), 1) if da_fabrica else None,
        "prs": linhas,
    }


def imprimir_prs(r: dict, dias: int | None) -> None:
    janela = f"últimos {dias} dias" if dias else "todo o histórico"
    print(f"🔀 Autonomia de PR — {janela} (fonte: {r['fonte']})\n")
    if r["fonte"] == "git":
        print("   Fonte git: só merges com commit de merge; squash e rebase não aparecem.\n"
              "   Com o `gh` autenticado, a contagem cobre os três.\n")
    if not r["da_fabrica"]:
        print(f"   {r['mesclados']} PR(s) mesclado(s), nenhum com commit da fábrica — "
              "autonomia de PR não medida.")
        return
    print(f"   Mesclados: {r['mesclados']} · com código da fábrica: {r['da_fabrica']} · "
          f"sem nenhum commit humano: {r['autonomos']}")
    print(f"   Autonomia de PR: {r['taxa']}%  ({r['autonomos']}/{r['da_fabrica']})\n")
    for l in r["prs"]:
        if not l["da_fabrica"]:
            continue
        rotulo = f"#{l['numero']}" if l["numero"] else (l["branch"] or "merge")
        print(f"   {'✅' if l['autonomo'] else '· '} {rotulo:<10} agente {l['agente']} · "
              f"humano {l['humano']}  {l['titulo'][:60]}")


# --- a entrega da fábrica comparada com a humana (aula 5 do Tech Leads Club) -------
# "O que está faltando para nós são boas métricas para verificar se [a fábrica] está
# entregando tão bem quanto humanos." A autonomia de PR (ADR-0044) diz quanto a fábrica
# entrega sozinha; esta conta diz se o que ela entrega aguenta. Dois sinais que saem do git
# e que o modelo não consegue influenciar, os mesmos para os dois grupos:
#
#   revertido  um commit posterior desfaz o PR: `Revert "<título ou #N>"` ou
#              "This reverts commit <sha>" apontando para a entrega ou um commit do PR
#   corrigido  um commit posterior `fix:`/`hotfix:`/"corrige", em até 14 dias, mexe num
#              arquivo de código (não teste) que o PR mexeu
#
# Fábrica = PR com commit de agente (o critério do ADR-0044); humano = sem nenhum. Abaixo de
# 5 PRs num grupo, a conta mostra os números e não a taxa: amostra pequena não vira veredicto.
# PR mesclado há menos de 14 dias fica "em observação", fora dos dois grupos: a janela dele
# não fechou, e contá-lo daria vantagem a quem entregou por último.

JANELA_CORRECAO_DIAS = 14
MINIMO_DO_GRUPO = 5
CORRECAO = re.compile(r"^(fix|hotfix)(\([^)]*\))?!?:|^corrig|^conserta", re.I)
REVERTE_SHA = re.compile(r"This reverts commit ([0-9a-f]{7,40})", re.I)
REVERTE_TITULO = re.compile(r'^Revert "(.+)"', re.I)
NUMERO_CITADO = re.compile(r"#(\d+)\b")
EXT_CODIGO = re.compile(r"\.(py|ts|tsx|js|jsx|mjs|cjs|go|rs|java|rb|php|kt|swift|cs|scala|vue|svelte)$")
EH_TESTE = re.compile(r"(^|/)(tests?|specs?|__tests__|e2e)/|\.(test|spec)\.|(^|/)test_[^/]*\.py$")


def historico_principal(raiz: Path) -> list[dict]:
    """Commits da linha principal, do mais antigo ao mais novo, com os arquivos de cada um."""
    try:
        r = subprocess.run(["git", "-C", str(raiz), "log", "--reverse", "--first-parent",
                            "--diff-merges=first-parent", "--name-only",
                            "--format=%x1e%H%x1f%cI%x1f%s%x1f%b%x1f"],
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return []
    commits = []
    for bloco in r.stdout.split("\x1e")[1:] if r.returncode == 0 else []:
        partes = bloco.split("\x1f")
        if len(partes) < 5:
            continue
        arquivos = [a.strip() for a in partes[4].splitlines() if a.strip()]
        commits.append({"oid": partes[0], "quando": _data(partes[1]), "assunto": partes[2],
                        "corpo": partes[3], "arquivos": arquivos})
    return commits


def titulo_do_commit(c: dict) -> str:
    """O título que conta: no merge commit do GitHub, o assunto é "Merge pull request #N" e o
    título do PR (o `fix:` ou o `Revert "..."`) vem na primeira linha do corpo."""
    if MERGE_DE_PR.match(c["assunto"]):
        return next((l.strip() for l in c["corpo"].splitlines() if l.strip()), c["assunto"])
    return c["assunto"]


def de_codigo(arquivos) -> set[str]:
    return {a for a in arquivos if EXT_CODIGO.search(a) and not EH_TESTE.search(a)}


def reverte(c: dict, pr: dict, oids) -> bool:
    """O commit `c` desfaz o PR? Pelo sha citado ou pelo título/número entre aspas."""
    shas = REVERTE_SHA.findall(c["corpo"]) + REVERTE_SHA.findall(c["assunto"])
    if any(o.startswith(s) for s in shas for o in oids if o):
        return True
    m = REVERTE_TITULO.match(titulo_do_commit(c))
    citado = m.group(1) if m else ""
    numeros = {int(n) for n in NUMERO_CITADO.findall(citado)}
    return bool(citado) and (citado.strip() == pr["titulo"].strip() or pr["numero"] in numeros)


def corrige(c: dict, quando: datetime, codigo: set[str]) -> bool:
    dentro = c["quando"] is not None and timedelta(0) < c["quando"] - quando <= timedelta(
        days=JANELA_CORRECAO_DIAS)
    return (dentro and bool(CORRECAO.match(titulo_do_commit(c)))
            and bool(codigo & de_codigo(c["arquivos"])))


def _oids_do_pr(pr: dict) -> set[str]:
    oids = {pr.get("entrega") or ""} | {c.get("oid") or "" for c in pr["commits"]}
    return oids - {""}


def _posteriores(historico: list[dict], quando: datetime, oids: set[str]) -> list[dict]:
    return [c for c in historico if c["quando"] and c["quando"] > quando and c["oid"] not in oids]


def _rotulo(c: dict | None) -> str | None:
    return f"{c['oid'][:9]} {titulo_do_commit(c)[:60]}" if c else None


def sinais_do_pr(pr: dict, historico: list[dict]) -> dict:
    quando = _data(pr.get("mesclado_em"))
    if quando is None:
        return {"revertido": None, "corrigido": None}
    oids = _oids_do_pr(pr)
    entrega = next((c for c in historico if c["oid"] == pr.get("entrega")), None)
    codigo = de_codigo(entrega["arquivos"]) if entrega else set()
    depois = _posteriores(historico, quando, oids)
    return {"revertido": _rotulo(next((c for c in depois if reverte(c, pr, oids)), None)),
            "corrigido": _rotulo(next((c for c in depois if corrige(c, quando, codigo)), None))}


def _grupo(itens: list[dict]) -> dict:
    n = len(itens)
    rev = sum(1 for i in itens if i["revertido"])
    cor = sum(1 for i in itens if i["corrigido"])
    voltou = sum(1 for i in itens if i["revertido"] or i["corrigido"])
    def taxa(k: int) -> float | None:
        return round(100 * k / n, 1) if n >= MINIMO_DO_GRUPO else None
    return {"prs": n, "revertidos": rev, "corrigidos": cor, "voltaram": voltou,
            "taxa_reversao": taxa(rev), "taxa_correcao": taxa(cor), "taxa_voltaram": taxa(voltou),
            "voltaram_lista": [i for i in itens if i["revertido"] or i["corrigido"]]}


def janela_fechada(pr: dict, agora: datetime) -> bool:
    quando = _data(pr.get("mesclado_em"))
    return quando is not None and agora - quando >= timedelta(days=JANELA_CORRECAO_DIAS)


def comparar_entregas(raiz: Path, prs: list[dict], extras: tuple = (),
                      agora: datetime | None = None) -> dict:
    agora = agora or datetime.now(timezone.utc)
    historico = historico_principal(raiz)
    grupos: dict[str, list[dict]] = {"fabrica": [], "humano": []}
    em_observacao = {"fabrica": 0, "humano": 0}
    for pr in prs:
        lado = "fabrica" if any(commit_de_agente(c, extras) for c in pr["commits"]) else "humano"
        if not janela_fechada(pr, agora):
            em_observacao[lado] += 1
            continue
        grupos[lado].append({"numero": pr.get("numero"), "titulo": (pr.get("titulo") or "")[:80],
                             **sinais_do_pr(pr, historico)})
    f, h = _grupo(grupos["fabrica"]), _grupo(grupos["humano"])
    comparavel = f["taxa_voltaram"] is not None and h["taxa_voltaram"] is not None
    return {"janela_correcao_dias": JANELA_CORRECAO_DIAS, "minimo_do_grupo": MINIMO_DO_GRUPO,
            "fabrica": f, "humano": h, "em_observacao": em_observacao, "comparavel": comparavel,
            "diferenca_pp": round(f["taxa_voltaram"] - h["taxa_voltaram"], 1) if comparavel else None}


def _linha_do_grupo(nome: str, g: dict) -> str:
    if g["taxa_voltaram"] is None:
        return (f"   {nome:<8} {g['prs']} PR(s) — amostra pequena (menos de {MINIMO_DO_GRUPO}): "
                f"{g['revertidos']} revertido(s), {g['corrigidos']} corrigido(s), sem taxa")
    return (f"   {nome:<8} {g['prs']} PR(s) — voltaram {g['taxa_voltaram']}% "
            f"(revertidos {g['taxa_reversao']}%, corrigidos em até {JANELA_CORRECAO_DIAS} dias "
            f"{g['taxa_correcao']}%)")


def _frase_da_diferenca(r: dict) -> str:
    if not r["comparavel"]:
        return f"Não comparável: precisa de ao menos {MINIMO_DO_GRUPO} PRs mesclados em cada grupo."
    d = r["diferenca_pp"]
    if d == 0:
        return "A entrega da fábrica volta tanto quanto a das pessoas."
    return f"A entrega da fábrica volta {abs(d)} p.p. {'acima' if d > 0 else 'abaixo'} da das pessoas."


def _os_que_voltaram(r: dict) -> list[str]:
    linhas = []
    for nome, g in (("fábrica", r["fabrica"]), ("humano", r["humano"])):
        for i in g["voltaram_lista"][:10]:
            rotulo = f"#{i['numero']}" if i["numero"] else "merge"
            sinal = "; ".join(f"{k}: {i[k]}" for k in ("revertido", "corrigido") if i[k])
            linhas.append(f"   · [{nome}] {rotulo} {i['titulo'][:50]} — {sinal}")
    return linhas


def imprimir_comparacao(r: dict, dias: int | None) -> None:
    janela = f"últimos {dias} dias" if dias else "todo o histórico"
    print(f"⚖️  Entrega da fábrica × humana — {janela} (fonte: {r['fonte']})\n")
    print(_linha_do_grupo("fábrica", r["fabrica"]))
    print(_linha_do_grupo("humano", r["humano"]))
    obs = r.get("em_observacao") or {}
    if any(obs.values()):
        print(f"   em observação (mesclados há menos de {JANELA_CORRECAO_DIAS} dias, fora da conta): "
              f"fábrica {obs.get('fabrica', 0)}, humano {obs.get('humano', 0)}")
    print(f"\n   {_frase_da_diferenca(r)}")
    for linha in _os_que_voltaram(r):
        print(linha)


def _opcoes_de_pr(args: list[str]) -> tuple[str | None, list] | str:
    """(fonte, marcas extras) de `--fonte` e `--marca`; ou a mensagem de erro."""
    fonte, extras = None, []
    while "--fonte" in args or "--marca" in args:
        flag = "--fonte" if "--fonte" in args else "--marca"
        i = args.index(flag)
        if i + 1 >= len(args):
            return f"erro: {flag} precisa de um valor"
        valor = args.pop(i + 1)
        args.pop(i)
        try:
            if flag == "--fonte":
                fonte = valor
            else:
                extras.append(re.compile(valor, re.I | re.M))
        except re.error as e:
            return f"erro: --marca inválida — {e}"
    if fonte not in (None, "gh", "git"):
        return "erro: --fonte é gh ou git"
    return fonte, extras


def _cmd_prs(raiz: Path, dias: int | None, fonte, extras, como_json: bool) -> int:
    origem, prs = prs_mesclados(raiz, dias, fonte)
    r = {"fonte": origem, **autonomia_de_prs(prs, tuple(extras))}
    print(json.dumps(r, ensure_ascii=False, indent=2)) if como_json else imprimir_prs(r, dias)
    return 0


def _cmd_comparar(raiz: Path, dias: int | None, fonte, extras, como_json: bool) -> int:
    origem, prs = prs_mesclados(raiz, dias, fonte)
    r = {"fonte": origem, **comparar_entregas(raiz, prs, tuple(extras))}
    if como_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        imprimir_comparacao(r, dias)
    return 0


# Comandos sobre os PRs mesclados: (raiz, dias, fonte, marcas, json) → exit code.
SOBRE_PRS = {"prs": _cmd_prs, "comparar": _cmd_comparar}


# --- custo por versão no /avaliar (aula 5 do Tech Leads Club) -----------------------
# "Fiz uma skill e quero ver se ela está boa ou pior que a versão anterior: faço o
# benchmark e olho quantas chamadas de ferramenta ela fez, quanto tempo levou." O /avaliar
# media a qualidade; o custo de cada versão ficava de fora, e uma candidata que empata no
# benchmark gastando o dobro passava. Cada caso roda com `claude -p --output-format json`,
# uma subpasta por versão; aqui sai a mediana por caso de cada versão e a diferença para a
# baseline. Em tokens, nunca em dinheiro (ADR-0044/0048/0050).

def _json_ou_nada(texto: str):
    try:
        return json.loads(texto)
    except ValueError:
        return None


def _objetos(texto: str):
    """O JSON inteiro (`--output-format json`) ou cada linha, da última para a primeira
    (`stream-json`, em que o `result` é o último evento)."""
    inteiro = _json_ou_nada(texto)
    if inteiro is not None:
        yield inteiro
        return
    for linha in reversed(texto.splitlines()):
        objeto = _json_ou_nada(linha)
        if objeto is not None:
            yield objeto


def _resultado(arq: Path) -> dict | None:
    """O evento `result` do arquivo do caso, só se trouxer `usage`."""
    try:
        texto = arq.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    r = next((o for o in _objetos(texto) if isinstance(o, dict) and o.get("type") == "result"), None)
    return r if r and isinstance(r.get("usage"), dict) else None


def _inteiro(d: dict, chave: str) -> int:
    v = d.get(chave)
    return v if isinstance(v, int) and not isinstance(v, bool) else 0


def custo_do_caso(arq: Path) -> dict | None:
    """Tokens, turnos e duração do evento `result`; None sem `usage` (não medido)."""
    r = _resultado(arq)
    if r is None:
        return None
    uso, ms = r["usage"], r.get("duration_ms")
    return {"novos": sum(_inteiro(uso, k) for k in ("input_tokens", "cache_creation_input_tokens",
                                                     "output_tokens")),
            "cache_lido": _inteiro(uso, "cache_read_input_tokens"),
            "turnos": r.get("num_turns") if isinstance(r.get("num_turns"), int) else None,
            "duracao_s": round(ms / 1000, 1) if isinstance(ms, (int, float)) else None,
            "erro": bool(r.get("is_error")) or r.get("subtype", "success") != "success"}


def _mediana_de(casos: list[dict], campo: str) -> float | None:
    valores = sorted(c[campo] for c in casos if c[campo] is not None)
    if not valores:
        return None
    meio = len(valores) // 2
    return float(valores[meio]) if len(valores) % 2 else (valores[meio - 1] + valores[meio]) / 2


def custo_da_versao(pasta: Path) -> dict:
    arquivos = sorted(a for a in pasta.iterdir() if a.suffix in (".json", ".jsonl"))
    casos = [c for c in map(custo_do_caso, arquivos) if c is not None]
    return {"casos": len(arquivos), "medidos": len(casos),
            "com_erro": sum(c["erro"] for c in casos),
            **{campo: _mediana_de(casos, campo)
               for campo in ("novos", "cache_lido", "turnos", "duracao_s")}}


def _delta_pct(v: float | None, base: float | None) -> float | None:
    return round(100 * (v - base) / base, 1) if v is not None and base else None


def custo_por_versao(pasta: Path, baseline: str | None = None) -> dict:
    nomes = sorted(d.name for d in pasta.iterdir() if d.is_dir()) if pasta.is_dir() else []
    if not nomes:
        return {"erro": f"{pasta}: nenhuma subpasta de versão (ex.: {pasta}/baseline/<caso>.json)"}
    base = baseline or ("baseline" if "baseline" in nomes else nomes[0])
    if base not in nomes:
        return {"erro": f"baseline '{base}' não está em {pasta} ({', '.join(nomes)})"}
    versoes = {n: custo_da_versao(pasta / n) for n in nomes}
    for n in nomes:
        if n != base:                                      # a baseline não varia contra si
            versoes[n].update(variacao_contra(versoes[n], versoes[base]))
    return {"pasta": str(pasta), "baseline": base, "versoes": versoes}


def variacao_contra(v: dict, b: dict) -> dict:
    turnos = (v["turnos"] - b["turnos"]) if None not in (v["turnos"], b["turnos"]) else None
    return {"delta_novos_pct": _delta_pct(v["novos"], b["novos"]),
            "delta_duracao_pct": _delta_pct(v["duracao_s"], b["duracao_s"]),
            "delta_turnos": turnos}


def acima_do_teto(r: dict, teto: float | None) -> list[str]:
    """Versões que gastam mais tokens novos por caso que a baseline + teto (em %)."""
    if teto is None or r.get("erro"):
        return []
    return [n for n, v in r["versoes"].items() if (v.get("delta_novos_pct") or 0) > teto]


def _num(x: float | None, sufixo: str = "") -> str:
    return "não medido" if x is None else f"{formatar(int(x))}{sufixo}"


def _variacao(x: float | None, sufixo: str = "%") -> str:
    return "" if x is None else f" ({x:+g}{sufixo})"


def imprimir_custo_eval(r: dict, teto: float | None) -> None:
    print(f"💰 Custo por versão — {r['pasta']} (baseline: {r['baseline']}; mediana por caso)\n")
    for nome, v in r["versoes"].items():
        print(f"   {nome:<14} {v['medidos']}/{v['casos']} caso(s) medidos"
              + (f", {v['com_erro']} com erro" if v["com_erro"] else ""))
        print(f"      tokens novos {_num(v['novos'])}{_variacao(v.get('delta_novos_pct'))} · "
              f"cache lido {_num(v['cache_lido'])} · turnos {_num(v['turnos'])}"
              f"{_variacao(v.get('delta_turnos'), '')} · duração {_num(v['duracao_s'], ' s')}"
              f"{_variacao(v.get('delta_duracao_pct'))}")
    for nome in acima_do_teto(r, teto):
        print(f"\n   ⚠️  {nome} gasta mais que a baseline + {teto:g}% de tokens novos por caso")


def _cmd_custo_eval(comando: str, raiz: Path, dias, args: list[str], como_json: bool) -> int:
    alvo = next((a for a in args[1:] if not a.startswith("--")), None)
    baseline, teto = _valor_de(args, "--baseline"), _valor_de(args, "--teto")
    try:
        teto_pct = float(teto) if teto is not None else None
    except ValueError:
        print("erro: --teto é um percentual, ex.: --teto 20", file=sys.stderr)
        return 1
    r = custo_por_versao(raiz / alvo if alvo else raiz / "?", baseline)
    if r.get("erro"):
        print(f"erro: {r['erro']}", file=sys.stderr)
        return 1
    r["pasta"] = alvo                                       # como foi pedido, sem o caminho da máquina
    r["acima_do_teto"] = acima_do_teto(r, teto_pct)
    print(json.dumps(r, ensure_ascii=False, indent=2)) if como_json else imprimir_custo_eval(r, teto_pct)
    return 1 if r["acima_do_teto"] else 0


def _valor_de(args: list[str], nome: str) -> str | None:
    i = args.index(nome) if nome in args else -1
    return args[i + 1] if 0 <= i < len(args) - 1 else None


def _rodar_sobre_prs(comando: str, raiz: Path, dias, args: list[str], como_json: bool) -> int:
    opcoes = _opcoes_de_pr(args)
    if isinstance(opcoes, str):
        print(opcoes, file=sys.stderr)
        return 1
    return SOBRE_PRS[comando](raiz, dias, *opcoes, como_json)


# Comandos que não leem a trajetória: (comando, raiz, dias, args, json) → exit code.
SEM_TRAJETORIA = {"prs": _rodar_sobre_prs, "comparar": _rodar_sobre_prs,
                  "custo-eval": _cmd_custo_eval}


# --- apresentação ------------------------------------------------------------------

def alertas(m: dict) -> list[str]:
    """O que o resumo destaca com ⚠️: o que deixou de ser medido ou de ser guardado."""
    saida = []
    if m["falhas_do_guardrail"]:
        saida.append(f"Guardrail falhou e deixou passar: {m['falhas_do_guardrail']} vez(es) — "
                     "`tipo: guardrail_erro` na trajetória diz onde (ADR-0046)")
    if m["sessoes_com_producao_sem_gate"]:
        saida.append("Código de produção escrito sem nenhum gate: "
                     f"{m['sessoes_com_producao_sem_gate']} sessão(ões)")
    return saida


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
    if m["recusas_total"]:
        classes = ", ".join(f"{k} ({v})" for k, v in m["recusas_por_classe"].items())
        print(f"  Recusas do guardrail: {m['recusas_total']} em "
              f"{m['sessoes_com_recusa']} sessão(ões) — {classes}")
        if m["recusas_em_modo_aviso"]:
            print(f"     {m['recusas_em_modo_aviso']} em modo aviso. Taxa baixa e estável "
                  "é o sinal de que a regra pode virar bloqueio.")
    print(linha_de_tokens_do_resumo(m))
    print(linha_de_faltas_do_resumo(m))
    for alerta in alertas(m):
        print(f"  ⚠️  {alerta}")
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

    if comando in SEM_TRAJETORIA:
        return SEM_TRAJETORIA[comando](comando, raiz, dias, args, como_json)

    eventos = carregar(raiz, dias)

    if comando == "resumo":
        m = {**metricas(por_sessao(eventos)), **resumo_de_tokens(eventos),
             **faltas_de_fonte(eventos)}
        if como_json:
            print(json.dumps(m, ensure_ascii=False, indent=2))
        else:
            imprimir_resumo(m, dias)
        return 0

    if comando in SIMPLES:
        return SIMPLES[comando](eventos, raiz, dias, como_json)

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
