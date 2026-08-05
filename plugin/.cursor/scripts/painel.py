#!/usr/bin/env python3
"""painel.py — o quadro vivo da fábrica, renderizado do estado canônico (ADR-0013/0032).

A fábrica sempre soube onde estava; ela só não mostrava. O estado do arco vive em
`.agents/ciclo/`, a trajetória em `.agents/execucoes/`, o progresso dos requisitos na
coluna Status/Verificação da SPEC, e o veredicto nos blocos de contrato dos relatórios.
Quatro fontes, todas canônicas, nenhuma com cara de painel — e por isso o usuário
precisava rodar quatro comandos e juntar de cabeça.

Este script junta. **Só isso.**

## A regra que define este arquivo

**O painel é renderização, nunca estado.** Ele lê e desenha; não escreve em lugar
nenhum além do arquivo de saída que você pediu, e não guarda nada entre execuções.
Um "quadro" que persiste vira a planilha paralela que o ADR-0013 recusou: dois lugares
dizendo o progresso, divergindo na primeira vez que alguém esquece de atualizar um.

Consequência prática: se o número aqui está errado, o bug está na fonte, não no painel.
Não conserte aqui.

Uso:
    painel.py                          # tudo que existe, no terminal
    painel.py SPEC-001                 # só uma SPEC
    painel.py --html painel.html       # página autocontida (sem rede, sem CDN)
    painel.py --json                   # para outra ferramenta consumir
    painel.py --dias 7                 # janela da trajetória (default 14)

Só stdlib.
"""
from __future__ import annotations

import html as _html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from contrato import ler_critica, ler_revisao, ler_validacao
except Exception:
    ler_critica = ler_revisao = ler_validacao = None  # type: ignore[assignment]
try:
    from telemetria import carregar, metricas, por_sessao
except Exception:
    carregar = metricas = por_sessao = None  # type: ignore[assignment]

DIAS_PADRAO = 14
LINHA_TABELA = re.compile(r"^\s*\|(?!\s*-)(.+)\|\s*$")

# Peso de cada estado no progresso da SPEC — mesma régua do `/especificar`:
# "Em progresso" conta 0.5 porque meio caminho andado não é zero nem um.
PESO = {"concluído": 1.0, "concluido": 1.0, "em progresso": 0.5, "pendente": 0.0}

ICONE_ESTADO = {"escalado": "⏸️", "encerrado": "✅", "pronto_para_pr": "🎯"}


# --- leitura das fontes canônicas ----------------------------------------------------

def _celulas(linha: str) -> list[str]:
    m = LINHA_TABELA.match(linha)
    return [c.strip() for c in m.group(1).split("|")] if m else []


def ler_spec(caminho: Path) -> dict | None:
    """Requisitos da SPEC pela coluna Status/Verificação. None se não for uma SPEC."""
    try:
        texto = caminho.read_text(encoding="utf-8")
    except Exception:
        return None
    reqs = []
    for linha in texto.splitlines():
        cels = _celulas(linha)
        if len(cels) < 5:
            continue
        estado = next((c for c in cels if c.lower() in PESO), None)
        if estado is None:
            continue
        verificacao = next((c for c in cels if c.lower().startswith(("verificado:",
                                                                     "em progresso:"))), "")
        reqs.append({
            "id": cels[0],
            "titulo": cels[1] if len(cels) > 1 else "",
            "prioridade": next((c for c in cels if re.fullmatch(r"P[123]", c)), "—"),
            "estado": estado.lower(),
            "verificado": verificacao.lower().startswith("verificado:"),
        })
    if not reqs:
        return None

    # "Concluído" sem `verificado:` **não conta como pronto** — é a regra do ADR-0013
    # aplicada ao próprio painel: o card anda porque o agente construiu e provou, não
    # porque alguém escreveu "Concluído". Sem prova, vale o mesmo que "em progresso":
    # nem zero (o código existe) nem um (ninguém verificou).
    sem_prova = [r for r in reqs if r["estado"].startswith("conclu") and not r["verificado"]]
    feito = sum(0.5 if r in sem_prova else PESO.get(r["estado"], 0.0) for r in reqs)
    return {
        "arquivo": str(caminho),
        "id": re.sub(r"^(SPEC-\d+).*", r"\1", caminho.stem) or caminho.stem,
        "requisitos": reqs,
        "total": len(reqs),
        "progresso": round(100 * feito / len(reqs)),
        "p1_abertos": [r["id"] for r in reqs
                       if r["prioridade"] == "P1" and not r["estado"].startswith("conclu")],
        "sem_prova": [r["id"] for r in sem_prova],
    }


ROTULOS = (("critica", "Crítica"), ("validacao", "Validação"), ("revisao", "Revisão"))


def _achados(r: dict) -> int:
    """Contagem de achados, qualquer que seja o nome do campo no contrato."""
    for campo in ("achados", "bloqueios", "criticos"):
        if campo in r:
            return r[campo]
    return 0


def _cobertura(r: dict) -> list:
    return r.get("verificado") or r.get("examinado") or []


def coluna_de(r: dict) -> str:
    """Coluna do quadro. 'Pronto' exige `verificado:` — o resto é 'Em progresso'."""
    if r["estado"].startswith("conclu"):
        return "Pronto" if r["verificado"] else "Em progresso"
    return "Em progresso" if r["estado"] == "em progresso" else "A fazer"


def ler_ciclos(raiz: Path) -> list[dict]:
    pasta = raiz / ".agents" / "ciclo"
    if not pasta.is_dir():
        return []
    saida = []
    for p in sorted(pasta.glob("*.json")):
        try:
            saida.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return saida


def ler_relatorios(raiz: Path, spec: str) -> dict:
    """Último veredicto de cada gate, lido do bloco de contrato (ADR-0032)."""
    alvo = re.sub(r"[^A-Za-z0-9_-]", "-", spec)
    saida = {}
    for chave, pasta, prefixo, leitor in (
        ("critica", "docs/specs/criticas", "CRITICA", ler_critica),
        ("validacao", "docs/specs/validacoes", "VALIDACAO", ler_validacao),
        ("revisao", "docs/specs/revisoes", "REVISAO", ler_revisao),
    ):
        d = raiz / pasta
        if not d.is_dir() or leitor is None:
            continue
        cands = sorted(d.glob(f"{prefixo}-{alvo}-*.md"), key=lambda x: x.name, reverse=True)
        if not cands:
            continue
        r = leitor(cands[0].read_text(encoding="utf-8"))
        saida[chave] = ({"arquivo": cands[0].name, **r.dados} if r.ok
                        else {"arquivo": cands[0].name, "erro": r.codigo})
    return saida


def coletar(raiz: Path, alvo: str | None, dias: int) -> dict:
    specs = []
    pasta = raiz / "docs" / "specs"
    if pasta.is_dir():
        for p in sorted(pasta.glob("*.md")):
            s = ler_spec(p)
            if s and (alvo is None or alvo.lower() in s["id"].lower()):
                s["relatorios"] = ler_relatorios(raiz, s["id"])
                specs.append(s)

    ciclos = [c for c in ler_ciclos(raiz)
              if alvo is None or alvo.lower() in str(c.get("spec", "")).lower()]

    tele = {}
    if carregar is not None:
        try:
            eventos = carregar(raiz, dias)
            if eventos:
                tele = metricas(por_sessao(eventos))
        except Exception:
            tele = {}

    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raiz": str(raiz),
        "janela_dias": dias,
        "specs": specs,
        "ciclos": ciclos,
        "telemetria": tele,
    }


# --- render: terminal -----------------------------------------------------------------

def barra(pct: int, largura: int = 20) -> str:
    cheio = round(pct * largura / 100)
    return "█" * cheio + "░" * (largura - cheio)


def render_terminal(d: dict) -> str:
    L = [f"📋 Quadro da fábrica — {d['gerado_em'][:16].replace('T', ' ')} UTC", ""]

    if not d["specs"] and not d["ciclos"]:
        L.append("Nada para mostrar: sem SPEC em docs/specs/ e sem ciclo em .agents/ciclo/.")
        L.append("Comece com /kairos-forge:especificar ou /kairos-forge:entregar.")
        return "\n".join(L)

    ciclo_por_spec = {c.get("spec"): c for c in d["ciclos"]}

    for s in d["specs"]:
        c = ciclo_por_spec.pop(s["id"], None)
        cab = f"  {s['id']} — {barra(s['progresso'])} {s['progresso']}%  ({s['total']} req)"
        if c:
            e = c.get("estado", "?")
            cab += f"   {ICONE_ESTADO.get(e, '🙋' if e.startswith('aguardando_') else '🔁')} {e}"
        L.append(cab)

        colunas = {"A fazer": [], "Em progresso": [], "Pronto": []}
        for r in s["requisitos"]:
            colunas[coluna_de(r)].append(r["id"] + ("" if r["verificado"]
                                                    or not r["estado"].startswith("conclu")
                                                    else " ⚠️"))
        L.append("     " + " | ".join(f"{k}: {', '.join(v) or '—'}" for k, v in colunas.items()))

        if s["sem_prova"]:
            L.append(f"     ⚠️  'Concluído' sem `verificado:` → {', '.join(s['sem_prova'])}"
                     " — não conta como pronto aqui, e a /validar trata como sem evidência")
        for chave, rot in ROTULOS:
            r = s["relatorios"].get(chave)
            if not r:
                continue
            if "erro" in r:
                L.append(f"     🛑 {rot}: contrato inválido [{r['erro']}] em {r['arquivo']}")
            else:
                n, cob = _achados(r), len(_cobertura(r))
                extra = f" · faixa {r['faixa']}" if r.get("faixa") else ""
                if r.get("criticado_por"):
                    extra += f" · {len(set(c.lower() for c in r['criticado_por']))} críticos"
                L.append(f"     {'✅' if not n else '❌'} {rot}: {r['veredicto']}"
                         f" ({n} achado(s){extra}) · {cob} item(ns) de cobertura")
        if c:
            L.append("     " + _placar_ciclo(c))
        L.append("")

    for c in ciclo_por_spec.values():  # ciclo sem SPEC correspondente em docs/specs/
        e = c.get("estado", "?")
        L.append(f"  {c.get('spec', '?')} — {ICONE_ESTADO.get(e, '🙋' if e.startswith('aguardando_') else '🔁')} {e}  (sem SPEC no disco)")
        L.append("     " + _placar_ciclo(c) + "\n")

    t = d["telemetria"]
    if t:
        L.append(f"  Trajetória ({d['janela_dias']}d): {t.get('ciclos', 0)} ciclo(s) · "
                 f"autonomia {t.get('autonomia_pct', 0)}% · "
                 f"gate verde de primeira {t.get('verdes_de_primeira_pct', 0)}% · "
                 f"{t.get('sessoes_com_producao_sem_gate', 0)} sessão(ões) com produção sem gate")
        if t.get("recusas_total"):
            L.append(f"  Recusas de guardrail: {t['recusas_total']} "
                     f"({', '.join(f'{k}={v}' for k, v in (t.get('recusas_por_classe') or {}).items())})")
    else:
        L.append("  Trajetória: sem telemetria neste projeto (ADR-0021) — o painel mostra "
                 "só o que está no disco.")

    return "\n".join(L)


def _placar_ciclo(c: dict) -> str:
    orc, rod = c.get("orcamento", {}), c.get("rodadas", {})
    tot, teto = c.get("rodadas_totais", {}), c.get("teto", {})
    marca = c.get("marca") or {}
    partes = []
    for g in ("validar", "revisar"):
        p = f"{g} {rod.get(g, 0)}/{orc.get(g, '?')}"
        if tot.get(g) is not None and teto.get(g) is not None:
            p += f" (tot {tot[g]}/{teto[g]})"
        if marca.get(g) is not None:
            p += f" · marca {marca[g]}"
        partes.append(p)
    linha = "Fichas: " + " · ".join(partes)
    if c.get("motivo_escalacao"):
        linha += f"\n     ⏸️  {c['motivo_escalacao']}"
    return linha


# --- render: HTML autocontido ----------------------------------------------------------
# Sem CDN, sem fonte remota, sem script externo: o painel precisa abrir numa máquina
# sem rede, que é justamente onde alguém está depurando um ciclo que travou.

CSS = """
:root{--bg:#0f1115;--card:#171a21;--txt:#e6e8ee;--dim:#8b93a7;--ok:#3fb950;--no:#f85149;
--warn:#d29922;--bar:#2d3340;--ac:#58a6ff}
@media(prefers-color-scheme:light){:root{--bg:#f6f7f9;--card:#fff;--txt:#1c2128;
--dim:#57606a;--bar:#e6e8ec}}
*{box-sizing:border-box}body{margin:0;padding:2rem 1rem;background:var(--bg);color:var(--txt);
font:15px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}
main{max-width:60rem;margin:0 auto}h1{font-size:1.1rem;margin:0 0 .25rem}
.sub{color:var(--dim);font-size:.8rem;margin-bottom:1.5rem}
.c{background:var(--card);border-radius:10px;padding:1rem 1.15rem;margin-bottom:1rem;
border:1px solid color-mix(in srgb,var(--txt) 10%,transparent)}
.h{display:flex;flex-wrap:wrap;gap:.6rem;align-items:baseline;margin-bottom:.6rem}
.h b{font-size:1rem}.tag{font-size:.72rem;padding:.1rem .5rem;border-radius:99px;
background:var(--bar);color:var(--dim)}
.bar{height:7px;border-radius:4px;background:var(--bar);overflow:hidden;margin:.5rem 0}
.bar i{display:block;height:100%;background:var(--ac)}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));gap:.6rem;
margin:.7rem 0}
.col{background:color-mix(in srgb,var(--bar) 45%,transparent);border-radius:7px;padding:.5rem .6rem}
.col b{display:block;font-size:.7rem;color:var(--dim);text-transform:uppercase;
letter-spacing:.04em;margin-bottom:.3rem}
.chip{display:inline-block;font-size:.75rem;padding:.05rem .4rem;margin:.1rem .15rem .1rem 0;
border-radius:4px;background:var(--bar)}
.ok{color:var(--ok)}.no{color:var(--no)}.warn{color:var(--warn)}.dim{color:var(--dim)}
.l{font-size:.82rem;margin:.25rem 0}
table{width:100%;border-collapse:collapse;font-size:.8rem;margin-top:.4rem}
td{padding:.2rem .4rem;border-top:1px solid var(--bar)}td:first-child{color:var(--dim)}
footer{color:var(--dim);font-size:.75rem;text-align:center;margin-top:2rem}
"""


def _e(x) -> str:
    return _html.escape(str(x))


def _chips(itens, extra="") -> str:
    if not itens:
        return '<span class="dim">—</span>'
    return "".join(f'<span class="chip {extra}">{_e(i)}</span>' for i in itens)


def render_html(d: dict) -> str:
    ciclo_por_spec = {c.get("spec"): c for c in d["ciclos"]}
    corpo = []

    for s in d["specs"]:
        c = ciclo_por_spec.pop(s["id"], None)
        cols = {"A fazer": [], "Em progresso": [], "Pronto": []}
        for r in s["requisitos"]:
            cols[coluna_de(r)].append(r["id"] + ("" if r["verificado"]
                                                 or not r["estado"].startswith("conclu")
                                                 else " ⚠"))

        linhas = []
        if s["sem_prova"]:
            linhas.append('<p class="l warn">⚠ "Concluído" sem <code>verificado:</code> → '
                          f'{_e(", ".join(s["sem_prova"]))} — não conta como pronto aqui, '
                          "e a /validar trata como sem evidência</p>")
        for chave, rot in ROTULOS:
            r = s["relatorios"].get(chave)
            if not r:
                continue
            if "erro" in r:
                linhas.append(f'<p class="l no">🛑 {rot}: contrato inválido '
                              f'[{_e(r["erro"])}] em {_e(r["arquivo"])}</p>')
                continue
            n, cob = _achados(r), len(_cobertura(r))
            faixa = f" · faixa {_e(r['faixa'])}" if r.get("faixa") else ""
            linhas.append(f'<p class="l {"ok" if not n else "no"}">{"✅" if not n else "❌"} '
                          f'{rot}: {_e(r["veredicto"])} ({n} achado(s){faixa}) '
                          f'<span class="dim">· {cob} item(ns) de cobertura</span></p>')
        if c:
            linhas.append(f'<p class="l dim">{_e(_placar_ciclo(c)).replace(chr(10), "<br>")}</p>')

        estado_tag = (f'<span class="tag">{_e(c.get("estado", ""))}</span>' if c else "")
        corpo.append(f"""<section class="c">
  <div class="h"><b>{_e(s['id'])}</b>{estado_tag}
    <span class="tag">{s['total']} requisitos</span>
    <span class="tag">{s['progresso']}%</span>
    {'<span class="tag no">P1 aberto: ' + _e(", ".join(s["p1_abertos"])) + "</span>" if s["p1_abertos"] else ""}
  </div>
  <div class="bar"><i style="width:{s['progresso']}%"></i></div>
  <div class="cols">{''.join(f'<div class="col"><b>{k}</b>{_chips(v)}</div>' for k, v in cols.items())}</div>
  {''.join(linhas)}
</section>""")

    for c in ciclo_por_spec.values():
        corpo.append(f"""<section class="c"><div class="h"><b>{_e(c.get('spec', '?'))}</b>
  <span class="tag">{_e(c.get('estado', '?'))}</span>
  <span class="tag dim">sem SPEC no disco</span></div>
  <p class="l dim">{_e(_placar_ciclo(c)).replace(chr(10), "<br>")}</p></section>""")

    t = d["telemetria"]
    if t:
        pares = [("Ciclos", t.get("ciclos", 0)),
                 ("Autonomia", f"{t.get('autonomia_pct', 0)}%"),
                 ("Intervenções (mediana)", t.get("intervencoes_medianas", "—")),
                 ("Gate verde de primeira", f"{t.get('verdes_de_primeira_pct', 0)}%"
                                            f" ({t.get('verdes_de_primeira', 0)}"
                                            f"/{t.get('gates_distintos', 0)})"),
                 ("Sessões com produção sem gate", t.get("sessoes_com_producao_sem_gate", 0)),
                 ("Recusas de guardrail", t.get("recusas_total", 0))]
        corpo.append('<section class="c"><div class="h"><b>Trajetória</b>'
                     f'<span class="tag">{d["janela_dias"]} dias</span></div><table>'
                     + "".join(f"<tr><td>{_e(k)}</td><td>{_e(v)}</td></tr>" for k, v in pares)
                     + "</table></section>")
    else:
        corpo.append('<section class="c"><p class="l dim">Sem telemetria neste projeto '
                     "(ADR-0021) — o painel mostra só o que está no disco.</p></section>")

    if not corpo:
        corpo.append('<section class="c"><p class="l dim">Nada para mostrar: sem SPEC em '
                     "docs/specs/ e sem ciclo em .agents/ciclo/.</p></section>")

    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quadro da fábrica — kairos-forge</title><style>{CSS}</style></head><body><main>
<h1>📋 Quadro da fábrica</h1>
<p class="sub">{_e(d['raiz'])} · gerado em {_e(d['gerado_em'][:16].replace('T', ' '))} UTC</p>
{''.join(corpo)}
<footer>Renderização do estado canônico — <code>.agents/ciclo/</code>,
<code>.agents/execucoes/</code>, coluna Status/Verificação da SPEC e blocos de contrato
dos relatórios. O painel não guarda estado: se o número está errado, o bug está na fonte.</footer>
</main></body></html>"""


# --- CLI ---------------------------------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]
    como_json = "--json" in args
    args = [a for a in args if a != "--json"]

    saida_html = None
    dias = DIAS_PADRAO
    for flag, conv in (("--html", str), ("--dias", int)):
        if flag in args:
            i = args.index(flag)
            try:
                v = conv(args[i + 1])
            except (IndexError, ValueError):
                sys.exit(f"erro: {flag} precisa de um valor")
            args = args[:i] + args[i + 2:]
            if flag == "--html":
                saida_html = v
            else:
                dias = v

    alvo = args[0] if args else None
    d = coletar(Path.cwd(), alvo, dias)

    if como_json:
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0
    if saida_html:
        Path(saida_html).write_text(render_html(d), encoding="utf-8")
        print(f"✅ painel escrito em {saida_html} "
              f"({len(d['specs'])} SPEC(s), {len(d['ciclos'])} ciclo(s))")
        return 0
    print(render_terminal(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
