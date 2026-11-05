#!/usr/bin/env python3
"""rodar.py — eval de tarefa concluída da fábrica, de ponta a ponta (ADR-0049).

Os outros dois evals medem partes: o de roteamento, se a Laura chama o agente certo; o de
comportamento, se a fábrica se comporta quando o mundo diz não. Nenhum mede o que importa
ao comparar arquiteturas: a tarefa ficou pronta? É a pergunta do artigo da Anthropic
sobre dobrar subagentes no loop principal, e do single-agent-loop-kit (Apache 2.0) que o
acompanha: uma dobra só fica se a versão dobrada não for pior na tarefa concluída.

Cada tarefa é um projeto pequeno (`tarefas/_comum` mais a pasta `projeto/` da tarefa), um
pedido, e o que conta como pronto: um oráculo escondido (testes que só entram depois da
rodada) e checagens de processo lidas do disco (relatório com bloco de contrato válido,
estado do ciclo, arquivo intocado, resposta que pergunta). Tudo decidido por código.

Uso:
    rodar.py listar
    rodar.py validar [--tarefas t01,t04]
        Sem modelo e sem custo: cada oráculo e cada checagem tem de reprovar o projeto
        como está e aprovar a solução de referência. Roda no CI.
    rodar.py rodar --variante base [--reps 2] [--tarefas ...] [--modelo M]
                   [--plugin DIR] [--claude BIN] [--permissao bypassPermissions] [--manter]
        Paga: cada tarefa × rep é uma sessão `claude -p` com o plugin carregado de
        `--plugin` (padrão: este repositório) e sem as configurações de quem roda.
        Grava resultados/<variante>/resultados.jsonl, rodada.json e traces/.
    rodar.py comparar <antes> <depois>
    rodar.py estimar <variante medida> [--reps N] [--tarefas ...]

Só stdlib.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

RAIZ_EVAL = Path(__file__).resolve().parent
RAIZ_REPO = RAIZ_EVAL.parents[1]
TAREFAS = RAIZ_EVAL / "tarefas"
RESULTADOS = RAIZ_EVAL / "resultados"
COMUM = TAREFAS / "_comum"

sys.path.insert(0, str(RAIZ_REPO / "scripts"))
import contrato  # noqa: E402

TIPOS = ("corrigir", "construir", "verificar", "perguntar")
CHECAGENS = ("arquivo", "contrato", "ciclo", "intocado", "resposta")
DELEGACAO = ("Agent", "Task")       # ferramentas que abrem subagente no Claude Code


# --- tarefas -------------------------------------------------------------------------

def carregar_tarefas(filtro: str | None = None) -> list[dict]:
    ids = {x.strip() for x in (filtro or "").split(",") if x.strip()}
    saida = []
    for pasta in sorted(p for p in TAREFAS.iterdir() if p.is_dir() and not p.name.startswith("_")):
        if ids and not any(pasta.name == i or pasta.name.startswith(i + "-") for i in ids):
            continue
        t = json.loads((pasta / "tarefa.json").read_text(encoding="utf-8"))
        t["pasta"] = pasta
        saida.append(t)
    return saida


def problemas_da_tarefa(t: dict) -> list[str]:
    """O que impede a tarefa de ser rodada ou avaliada; vazio quando está bem formada."""
    p = []
    if t.get("id") != t["pasta"].name:
        p.append(f"id '{t.get('id')}' difere da pasta '{t['pasta'].name}'")
    if t.get("tipo") not in TIPOS:
        p.append(f"tipo '{t.get('tipo')}' fora de {TIPOS}")
    if not str(t.get("prompt") or "").strip():
        p.append("sem prompt")
    if t.get("oraculo") and not (t["pasta"] / "oraculo").is_dir():
        p.append("oraculo: true sem a pasta oraculo/")
    if not t.get("oraculo") and not t.get("checagens"):
        p.append("sem oráculo e sem checagens: nada decide se ficou pronta")
    p += [f"checagem '{c.get('tipo')}' desconhecida" for c in t.get("checagens", [])
          if c.get("tipo") not in CHECAGENS]
    if not (t["pasta"] / "solucao").is_dir():
        p.append("sem solucao/: o oráculo não tem como provar que distingue")
    return p


# --- o projeto de cada rodada ---------------------------------------------------------

def git(ws: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ws), "-c", "user.name=eval", "-c",
                           "user.email=eval@kairos-forge", "-c", "commit.gpgsign=false", *args],
                          capture_output=True, text=True, check=False)


def sobrepor(origem: Path, destino: Path) -> None:
    if origem.is_dir():
        shutil.copytree(origem, destino, dirs_exist_ok=True)


def preparar(t: dict, ws: Path) -> str:
    """Monta o projeto em `ws` como repositório git e devolve o commit de referência."""
    sobrepor(COMUM, ws)
    sobrepor(t["pasta"] / "projeto", ws)
    git(ws, "init", "-q", "-b", "main")
    git(ws, "add", "-A")
    git(ws, "commit", "-qm", "base")
    if t.get("mudanca"):
        git(ws, "checkout", "-q", "-b", "feature/download")
        sobrepor(t["pasta"] / "mudanca", ws)
        git(ws, "add", "-A")
        git(ws, "commit", "-qm", "feat: download dos relatórios")
    return git(ws, "rev-parse", "HEAD").stdout.strip()


def aplicar_solucao(t: dict, ws: Path) -> str:
    """Sobrepõe a solução de referência; devolve a resposta final dela, se houver."""
    sol = t["pasta"] / "solucao"
    sobrepor(sol, ws)
    resposta = ws / "resposta.txt"
    texto = resposta.read_text(encoding="utf-8") if resposta.is_file() else ""
    resposta.unlink(missing_ok=True)
    return texto


# --- avaliação ------------------------------------------------------------------------

def rodar_oraculo(t: dict, ws: Path) -> tuple[bool, str]:
    destino = ws / ".oraculo"
    shutil.copytree(t["pasta"] / "oraculo", destino, dirs_exist_ok=True)
    try:
        # A pasta do oráculo é a raiz da descoberta; o projeto entra pelo cwd (`-m`).
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", ".oraculo", "-q"],
                           cwd=ws, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return False, "oráculo passou do tempo"
    finally:
        shutil.rmtree(destino, ignore_errors=True)
    linhas = (r.stderr or r.stdout).strip().splitlines()
    return r.returncode == 0, linhas[-1] if linhas else ""


def _arquivos(ws: Path, padrao: str) -> list[Path]:
    return sorted(p for p in ws.glob(padrao) if p.is_file())


def checar(c: dict, ws: Path, ref: str, resposta: str) -> tuple[bool, str]:
    tipo = c["tipo"]
    if tipo == "arquivo":
        for arq in _arquivos(ws, c["glob"]):
            texto = arq.read_text(encoding="utf-8", errors="replace")
            if all(re.search(rx, texto, re.I) for rx in c.get("regex", [])):
                return True, str(arq.relative_to(ws))
        return False, f"nenhum {c['glob']} com {c.get('regex', [])}"
    if tipo == "contrato":
        arqs = _arquivos(ws, c["glob"])
        if not arqs:
            return False, f"nenhum {c['glob']}"
        r = contrato.LEITORES[c["leitor"]](arqs[-1].read_text(encoding="utf-8", errors="replace"))
        if not r.ok:
            return False, f"{arqs[-1].name}: [{r.codigo}] {r.erro}"
        errado = [k for k, v in c.get("campos", {}).items() if r.dados.get(k) != v]
        baixo = [k for k, v in c.get("minimos", {}).items() if (r.dados.get(k) or 0) < v]
        return not (errado or baixo), f"{arqs[-1].name}" + (f" · difere: {errado + baixo}" if errado or baixo else "")
    if tipo == "ciclo":
        estados = []
        for arq in _arquivos(ws, ".agents/ciclo/*.json"):
            try:
                estados.append(json.loads(arq.read_text(encoding="utf-8")).get("estado"))
            except ValueError:
                continue
        ok = any(e in c["estados"] for e in estados)
        return ok, f"estados: {estados or 'nenhum ciclo'}"
    if tipo == "intocado":
        mudados = git(ws, "diff", "--name-only", ref, "--", *c["caminhos"]).stdout.split()
        novos = git(ws, "ls-files", "--others", "--exclude-standard", "--", *c["caminhos"]).stdout.split()
        return not (mudados or novos), f"mudou: {mudados + novos}" if mudados or novos else "intocado"
    if tipo == "resposta":
        faltam = [rx for rx in c["regex"] if not re.search(rx, resposta or "", re.I)]
        return not faltam, f"faltou: {faltam}" if faltam else "ok"
    return False, f"checagem desconhecida: {tipo}"


def avaliar(t: dict, ws: Path, ref: str, resposta: str) -> dict:
    oraculo, detalhe = (rodar_oraculo(t, ws) if t.get("oraculo") else (None, ""))
    checagens = []
    for c in t.get("checagens", []):
        ok, d = checar(c, ws, ref, resposta)
        checagens.append({"tipo": c["tipo"], "ok": ok, "detalhe": d})
    aprovado = oraculo is not False and all(c["ok"] for c in checagens)
    return {"aprovado": aprovado, "oraculo": oraculo, "oraculo_detalhe": detalhe,
            "checagens": checagens}


# --- validar: o oráculo distingue? ----------------------------------------------------

def erradas_que_passam(t: dict) -> list[str]:
    """As soluções erradas conhecidas (`erradas/<nome>/`) que o oráculo deixa passar.

    Distinguir a base da solução de referência não basta: um oráculo frouxo aprova também
    a correção ingênua. Cada pasta em `erradas/` é uma dessas, e tem de ser reprovada.
    """
    passam = []
    for errada in sorted(p for p in (t["pasta"] / "erradas").glob("*") if p.is_dir()):
        with tempfile.TemporaryDirectory(prefix="kairos-eval-") as tmp:
            ws = Path(tmp)
            ref = preparar(t, ws)
            sobrepor(errada, ws)
            if avaliar(t, ws, ref, "")["aprovado"]:
                passam.append(errada.name)
    return passam


def cmd_validar(a) -> int:
    tarefas = carregar_tarefas(a.tarefas)
    falhas = 0
    for t in tarefas:
        problemas = problemas_da_tarefa(t)
        if not problemas:
            with tempfile.TemporaryDirectory(prefix="kairos-eval-") as tmp:
                ws = Path(tmp)
                ref = preparar(t, ws)
                antes = avaliar(t, ws, ref, "")
                resposta = aplicar_solucao(t, ws)
                depois = avaliar(t, ws, ref, resposta)
            if antes["aprovado"]:
                problemas.append("o projeto como está já passa: o oráculo não prova nada")
            if not depois["aprovado"]:
                motivos = [c["detalhe"] for c in depois["checagens"] if not c["ok"]]
                if depois["oraculo"] is False:
                    motivos.insert(0, f"oráculo: {depois['oraculo_detalhe']}")
                problemas.append(f"a solução de referência não passa: {motivos}")
            problemas += [f"a solução errada '{e}' passa: o oráculo não a pega"
                          for e in erradas_que_passam(t)]
        falhas += bool(problemas)
        print(f"{'✅' if not problemas else '❌'} {t['id']:<28} {t['tipo']:<10}"
              + ("" if not problemas else " · " + "; ".join(problemas)))
    print(f"\n{len(tarefas) - falhas} de {len(tarefas)} tarefa(s) distinguem a base da solução, "
          "sem modelo e sem custo.")
    return 1 if falhas else 0


# --- rodar: a sessão headless ---------------------------------------------------------

def ler_stream(linhas: list[str]) -> dict:
    """O que a sessão fez, lido do `--output-format stream-json`: rota, skills, tokens."""
    saida = {"rota": [], "skills": [], "ferramentas": {}, "tokens": None, "turnos": None,
             "duracao_s": None, "resposta": "", "erro": None}
    for linha in linhas:
        try:
            ev = json.loads(linha)
        except ValueError:
            continue
        if not isinstance(ev, dict):
            continue
        if ev.get("type") == "assistant":
            for bloco in (ev.get("message") or {}).get("content") or []:
                if not isinstance(bloco, dict) or bloco.get("type") != "tool_use":
                    continue
                nome, entrada = bloco.get("name", "?"), bloco.get("input") or {}
                saida["ferramentas"][nome] = saida["ferramentas"].get(nome, 0) + 1
                if nome in DELEGACAO:
                    saida["rota"].append(str(entrada.get("subagent_type") or entrada.get("name") or "?"))
                if nome == "Skill":
                    saida["skills"].append(str(entrada.get("skill") or entrada.get("command") or "?"))
        elif ev.get("type") == "result":
            uso = ev.get("usage") or {}
            saida["tokens"] = {"entrada": uso.get("input_tokens", 0),
                               "cache_escrita": uso.get("cache_creation_input_tokens", 0),
                               "cache_leitura": uso.get("cache_read_input_tokens", 0),
                               "saida": uso.get("output_tokens", 0)}
            saida["turnos"] = ev.get("num_turns")
            saida["duracao_s"] = round((ev.get("duration_ms") or 0) / 1000, 1)
            saida["resposta"] = str(ev.get("result") or "")
            if ev.get("is_error") or str(ev.get("subtype", "success")) != "success":
                saida["erro"] = str(ev.get("subtype") or "erro")
    if saida["tokens"] is None and saida["erro"] is None:
        saida["erro"] = "sessão sem evento result"
    return saida


def novos(tokens: dict | None) -> int:
    return sum((tokens or {}).get(k, 0) for k in ("entrada", "cache_escrita", "saida"))


def commit_do_plugin(plugin: Path) -> str:
    r = subprocess.run(["git", "-C", str(plugin), "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True, check=False)
    return r.stdout.strip() or "?"


def uma_rodada(t: dict, rep: int, a, traces: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"kairos-eval-{t['id']}-") as tmp:
        ws = Path(tmp)
        ref = preparar(t, ws)
        cmd = [a.claude, "-p", t["prompt"], "--output-format", "stream-json", "--verbose",
               "--plugin-dir", str(Path(a.plugin).resolve()), "--setting-sources", "",
               "--permission-mode", a.permissao]
        if a.modelo:
            cmd += ["--model", a.modelo]
        erro = None
        try:
            r = subprocess.run(cmd, cwd=ws, capture_output=True, text=True,
                               timeout=t.get("tempo_limite_s", 900))
            bruto = r.stdout
        except subprocess.TimeoutExpired as e:
            bruto = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            erro = "tempo_limite"
        except OSError as e:
            bruto, erro = "", f"não rodou: {e}"
        (traces / f"{t['id']}_rep{rep}.jsonl").write_text(bruto, encoding="utf-8")
        sessao = ler_stream(bruto.splitlines())
        nota = avaliar(t, ws, ref, sessao["resposta"])
        if a.manter:
            shutil.copytree(ws, traces / f"{t['id']}_rep{rep}_projeto", dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(".git"))
    return {"tarefa": t["id"], "rep": rep, **nota, **{k: v for k, v in sessao.items() if k != "resposta"},
            "resposta": sessao["resposta"][:500], "erro": erro or sessao["erro"]}


def cmd_rodar(a) -> int:
    if not shutil.which(a.claude):
        print(f"❌ `{a.claude}` não encontrado. A rodada paga precisa do Claude Code instalado e "
              "autenticado.", file=sys.stderr)
        return 1
    tarefas = carregar_tarefas(a.tarefas)
    ruins = {t["id"]: problemas_da_tarefa(t) for t in tarefas if problemas_da_tarefa(t)}
    if ruins:
        print(f"❌ tarefas malformadas: {ruins}", file=sys.stderr)
        return 1
    pasta = RESULTADOS / a.variante
    if (pasta / "resultados.jsonl").exists():
        print(f"❌ a variante '{a.variante}' já tem resultados. Mais reps de uma variante já "
              "comparada viram outra variante (ex.: base-rerun).", file=sys.stderr)
        return 1
    traces = pasta / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    (pasta / "rodada.json").write_text(json.dumps({
        "variante": a.variante, "inicio": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plugin": str(Path(a.plugin).resolve()), "plugin_commit": commit_do_plugin(Path(a.plugin)),
        "modelo": a.modelo or "padrão do CLI", "reps": a.reps,
        "tarefas": [t["id"] for t in tarefas]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (pasta / "resultados.jsonl").open("a", encoding="utf-8") as fh:
        for t in tarefas:
            for rep in range(a.reps):
                linha = uma_rodada(t, rep, a, traces)
                fh.write(json.dumps(linha, ensure_ascii=False) + "\n")
                fh.flush()
                print(f"{'✅' if linha['aprovado'] else '❌'} {t['id']} rep {rep} · "
                      f"{novos(linha['tokens']):,} tokens novos · rota {linha['rota'] or '—'}"
                      + (f" · erro: {linha['erro']}" if linha["erro"] else ""))
    return 0


# --- comparar e estimar ---------------------------------------------------------------

def carregar_resultados(variante: str) -> dict[str, list[dict]]:
    arq = RESULTADOS / variante / "resultados.jsonl"
    if not arq.is_file():
        raise SystemExit(f"❌ sem resultados para a variante '{variante}' em {arq}")
    por_tarefa: dict[str, list[dict]] = {}
    for linha in arq.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            d = json.loads(linha)
            por_tarefa.setdefault(d["tarefa"], []).append(d)
    return por_tarefa


def resumo(linhas: list[dict]) -> dict:
    n = len(linhas)
    medidos = [l for l in linhas if l.get("tokens")]
    return {"reps": n, "aprovados": sum(bool(l["aprovado"]) for l in linhas),
            "novos": round(sum(novos(l["tokens"]) for l in medidos) / len(medidos)) if medidos else None,
            "cache": round(sum(l["tokens"]["cache_leitura"] for l in medidos) / len(medidos)) if medidos else None,
            "duracao": round(sum(l.get("duracao_s") or 0 for l in linhas) / n, 1) if n else None,
            "rota": sorted({r for l in linhas for r in l.get("rota") or []}),
            "erros": sum(bool(l.get("erro")) for l in linhas)}


def comparar(antes: dict[str, list[dict]], depois: dict[str, list[dict]]) -> dict:
    saida = {"tarefas": {}, "piorou": [], "melhorou": [], "rota_mudou": [], "so_num_lado": []}
    for tid in sorted(set(antes) | set(depois)):
        if tid not in antes or tid not in depois:
            saida["so_num_lado"].append(tid)
            continue
        a, d = resumo(antes[tid]), resumo(depois[tid])
        saida["tarefas"][tid] = {"antes": a, "depois": d}
        taxa_a, taxa_d = a["aprovados"] / a["reps"], d["aprovados"] / d["reps"]
        if taxa_d < taxa_a:
            saida["piorou"].append(tid)
        elif taxa_d > taxa_a:
            saida["melhorou"].append(tid)
        if a["rota"] != d["rota"]:
            saida["rota_mudou"].append(tid)
    return saida


def cmd_comparar(a) -> int:
    r = comparar(carregar_resultados(a.antes), carregar_resultados(a.depois))
    print(f"{'tarefa':<28} {'pronta':>13} {'tokens novos':>23} {'duração (s)':>17}  rota")
    for tid, x in r["tarefas"].items():
        an, de = x["antes"], x["depois"]
        print(f"{tid:<28} {an['aprovados']}/{an['reps']} → {de['aprovados']}/{de['reps']:<5} "
              f"{str(an['novos']):>10} → {str(de['novos']):<10} {str(an['duracao']):>7} → {str(de['duracao']):<7}"
              f"  {','.join(an['rota']) or '—'} → {','.join(de['rota']) or '—'}")
    for rotulo, chave in (("Piorou", "piorou"), ("Melhorou", "melhorou"),
                          ("Rota mudou", "rota_mudou"), ("Só num dos lados", "so_num_lado")):
        if r[chave]:
            print(f"{rotulo}: {', '.join(r[chave])}")
    if r["piorou"]:
        print("A mudança piorou alguma tarefa: abra os traces antes de decidir. Mudança que só "
              "mexeu numa rep pode ser ruído — rode mais reps dos dois lados.")
    return 0


def cmd_estimar(a) -> int:
    medidos = carregar_resultados(a.variante)
    tarefas = [t["id"] for t in carregar_tarefas(a.tarefas)]
    total_novos = total_cache = 0
    sem_medida = []
    for tid in tarefas:
        r = resumo(medidos.get(tid, []))
        if r["novos"] is None:
            sem_medida.append(tid)
            continue
        total_novos += r["novos"] * a.reps
        total_cache += r["cache"] * a.reps
    print(f"{len(tarefas)} tarefa(s) × {a.reps} rep(s) = {len(tarefas) * a.reps} sessão(ões).")
    print(f"Estimativa a partir de '{a.variante}': {total_novos:,} tokens novos e "
          f"{total_cache:,} de cache lido (média por tarefa × reps).")
    if sem_medida:
        print(f"Sem medida para: {', '.join(sem_medida)} — fora da soma.")
    print("Não conta o que subagentes de Agent Teams gastam em sessões próprias, nem o que muda "
          "entre variantes. É uma ordem de grandeza, não uma promessa.")
    return 0


def cmd_listar(a) -> int:
    for t in carregar_tarefas(a.tarefas):
        decide = (["oráculo"] if t.get("oraculo") else []) + [c["tipo"] for c in t.get("checagens", [])]
        print(f"{t['id']:<28} {t['tipo']:<10} {t.get('titulo', '')}  [{', '.join(decide)}]")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rodar.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("listar")
    p.add_argument("--tarefas")
    p.set_defaults(fn=cmd_listar)
    p = sub.add_parser("validar", help="sem modelo: o oráculo distingue base e solução?")
    p.add_argument("--tarefas")
    p.set_defaults(fn=cmd_validar)
    p = sub.add_parser("rodar", help="pago: cada tarefa × rep numa sessão claude -p")
    p.add_argument("--variante", required=True)
    p.add_argument("--reps", type=int, default=2)
    p.add_argument("--tarefas")
    p.add_argument("--modelo")
    p.add_argument("--plugin", default=str(RAIZ_REPO))
    p.add_argument("--claude", default="claude")
    p.add_argument("--permissao", default="bypassPermissions")
    p.add_argument("--manter", action="store_true", help="guarda o projeto final de cada rep")
    p.set_defaults(fn=cmd_rodar)
    p = sub.add_parser("comparar")
    p.add_argument("antes")
    p.add_argument("depois")
    p.set_defaults(fn=cmd_comparar)
    p = sub.add_parser("estimar")
    p.add_argument("variante")
    p.add_argument("--reps", type=int, default=2)
    p.add_argument("--tarefas")
    p.set_defaults(fn=cmd_estimar)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
