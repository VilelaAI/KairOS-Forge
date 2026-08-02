#!/usr/bin/env python3
"""diagnostico.py — evidência determinística de nível 1 para o /kairos-forge:diagnosticar.

Coleta o que dá para **medir** num repositório sem executar a aplicação: churn,
concentração de autoria, proporção de teste, inventário de dependências, densidade
de marcadores de dívida e distribuição de tamanho de arquivo.

Por que existe: um diagnóstico onde todo número é impressão do modelo não é
diagnóstico, é opinião com casa decimal. Este script produz a camada que o
relatório pode citar como `medido` — o resto da escada de evidência (nível 2 com
ambiente executável, nível 3 com telemetria de produção) depende de acesso que um
plugin não tem e que a skill declara honestamente quando falta.

O que ele NÃO faz, de propósito:

  · não pontua nem prioriza — isso é julgamento, e é da skill (Rafael consolida);
  · não infere causa ("N+1 aqui") — inferência precisa ser rotulada como tal;
  · não roda a aplicação, não abre porta, não instala nada.

Uso:
    diagnostico.py coletar [CAMINHO] [--dias 90] [--json]

Só stdlib.
"""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

# --- o que conta como código-fonte ------------------------------------------------
EXT_FONTE = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs", ".java",
    ".kt", ".kts", ".rb", ".php", ".cs", ".swift", ".scala", ".ex", ".exs",
    ".vue", ".svelte", ".c", ".h", ".cpp", ".hpp", ".m", ".mm", ".sql",
}
IGNORAR = re.compile(
    r"(^|/)(\.git|node_modules|vendor|dist|build|target|bin|obj|\.venv|venv"
    r"|__pycache__|\.next|\.nuxt|coverage|migrations?/versions)(/|$)"
)
EH_TESTE = re.compile(
    r"(^|/)(tests?|specs?|__tests__|e2e|cypress|playwright)(/|$)|\.(test|spec)\.|_test\.|test_"
)
MARCADORES = re.compile(r"\b(TODO|FIXME|HACK|XXX|WORKAROUND|GAMBIARRA)\b")

MANIFESTOS = {
    "package.json": "npm/node",
    "requirements.txt": "pip",
    "pyproject.toml": "python",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "Gemfile": "ruby",
    "composer.json": "php",
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
}

LIMITE_ARQUIVO_GRANDE = 500  # linhas — acima disso vira candidato a decomposição
TOP = 10


def git(raiz: Path, *args: str) -> str:
    """Git sem shell. Devolve string vazia em qualquer falha — repo sem git é caso válido."""
    try:
        r = subprocess.run(["git", "-C", str(raiz), *args],
                           capture_output=True, text=True, timeout=60)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def tem_git(raiz: Path) -> bool:
    return bool(git(raiz, "rev-parse", "--git-dir").strip())


def fontes(raiz: Path) -> list[Path]:
    saida = []
    for p in raiz.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in EXT_FONTE:
            continue
        rel = str(p.relative_to(raiz)).replace("\\", "/")
        if IGNORAR.search(rel):
            continue
        saida.append(p)
    return saida


def linhas(p: Path) -> int:
    try:
        return sum(1 for _ in p.open("r", encoding="utf-8", errors="ignore"))
    except Exception:
        return 0


# --- métricas ----------------------------------------------------------------------

def churn(raiz: Path, dias: int) -> dict:
    """Arquivos mais alterados na janela. Onde o código muda é onde o risco mora.

    O top é de **código**: manifest e documentação mudam por versionamento e
    rotina, e afogariam o sinal que interessa. O churn de não-código continua
    contado à parte — volume alto ali é sinal próprio (config instável), só não
    é o mesmo sinal.
    """
    saida = git(raiz, "log", f"--since={dias} days ago", "--pretty=format:", "--name-only")
    if not saida.strip():
        return {"disponivel": False, "motivo": "sem histórico git na janela", "top": []}
    c = Counter(
        l.strip() for l in saida.splitlines()
        if l.strip() and not IGNORAR.search(l.strip())
    )
    codigo = Counter({a: n for a, n in c.items() if Path(a).suffix.lower() in EXT_FONTE})
    outros = Counter({a: n for a, n in c.items() if a not in codigo})
    return {
        "disponivel": True,
        "arquivos_tocados": len(c),
        "arquivos_codigo_tocados": len(codigo),
        "top": [{"arquivo": a, "alteracoes": n} for a, n in codigo.most_common(TOP)],
        "top_nao_codigo": [{"arquivo": a, "alteracoes": n} for a, n in outros.most_common(3)],
    }


def autoria(raiz: Path, arquivos: list[str], dias: int) -> dict:
    """Concentração de conhecimento nos hotspots — o bus factor onde ele importa."""
    if not arquivos:
        return {"disponivel": False, "motivo": "sem hotspots para analisar", "itens": []}
    itens = []
    for arq in arquivos:
        saida = git(raiz, "log", f"--since={dias} days ago", "--pretty=format:%an", "--", arq)
        autores = [a.strip() for a in saida.splitlines() if a.strip()]
        distintos = sorted(set(autores))
        itens.append({
            "arquivo": arq,
            "autores_distintos": len(distintos),
            "autor_unico": distintos[0] if len(distintos) == 1 else None,
        })
    solo = [i for i in itens if i["autores_distintos"] == 1]
    return {
        "disponivel": True,
        "itens": itens,
        "hotspots_com_autor_unico": len(solo),
        "total_hotspots": len(itens),
    }


def cobertura_estrutural(arquivos: list[Path], raiz: Path) -> dict:
    """Proporção arquivo-de-teste : arquivo-de-fonte.

    NÃO é cobertura de linha — é presença estrutural de teste. A distinção importa:
    um projeto pode ter proporção boa e cobertura ruim. O relatório deve dizer isso.
    """
    teste = prod = 0
    for p in arquivos:
        rel = str(p.relative_to(raiz)).replace("\\", "/")
        if EH_TESTE.search(rel):
            teste += 1
        else:
            prod += 1
    razao = round(teste / prod, 2) if prod else None
    return {
        "arquivos_de_teste": teste,
        "arquivos_de_producao": prod,
        "razao_teste_producao": razao,
        "nota": "presença estrutural de teste, não cobertura de linha",
    }


def dependencias(raiz: Path) -> dict:
    achados = []
    for nome, eco in MANIFESTOS.items():
        for p in raiz.rglob(nome):
            rel = str(p.relative_to(raiz)).replace("\\", "/")
            if IGNORAR.search(rel):
                continue
            achados.append({"manifesto": rel, "ecossistema": eco, **_contar_deps(p, nome)})
    return {"disponivel": bool(achados), "manifestos": achados}


def _contar_deps(p: Path, nome: str) -> dict:
    try:
        texto = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"total": None, "sem_versao_fixa": None}
    try:
        if nome == "package.json":
            d = json.loads(texto)
            deps = {**(d.get("dependencies") or {}), **(d.get("devDependencies") or {})}
            frouxas = [k for k, v in deps.items() if isinstance(v, str) and v[:1] in "^~*>"]
            return {"total": len(deps), "sem_versao_fixa": len(frouxas)}
        if nome == "requirements.txt":
            linhas_ = [l.strip() for l in texto.splitlines()
                       if l.strip() and not l.strip().startswith("#")]
            frouxas = [l for l in linhas_ if "==" not in l]
            return {"total": len(linhas_), "sem_versao_fixa": len(frouxas)}
        if nome == "go.mod":
            return {"total": len(re.findall(r"^\s+\S+ v\d", texto, re.M)), "sem_versao_fixa": 0}
        if nome == "pyproject.toml":
            bloco = re.search(r"^dependencies\s*=\s*\[(.*?)\]", texto, re.S | re.M)
            itens = re.findall(r'["\']([^"\']+)["\']', bloco.group(1)) if bloco else []
            frouxas = [i for i in itens if "==" not in i]
            return {"total": len(itens), "sem_versao_fixa": len(frouxas)}
        if nome == "Cargo.toml":
            bloco = re.search(r"\[dependencies\](.*?)(\n\[|\Z)", texto, re.S)
            n = len(re.findall(r"^\s*\w[\w-]*\s*=", bloco.group(1), re.M)) if bloco else 0
            return {"total": n, "sem_versao_fixa": None}
    except Exception:
        pass
    return {"total": None, "sem_versao_fixa": None}


def marcadores(arquivos: list[Path], raiz: Path) -> dict:
    """Densidade de dívida declarada pelo próprio time — sinal barato e honesto."""
    total_marc = total_linhas = 0
    por_arquivo: Counter = Counter()
    for p in arquivos:
        try:
            texto = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        n = len(MARCADORES.findall(texto))
        total_linhas += texto.count("\n") + 1
        if n:
            por_arquivo[str(p.relative_to(raiz)).replace("\\", "/")] = n
            total_marc += n
    densidade = round(1000 * total_marc / total_linhas, 2) if total_linhas else 0.0
    return {
        "total": total_marc,
        "por_mil_linhas": densidade,
        "top": [{"arquivo": a, "marcadores": n} for a, n in por_arquivo.most_common(TOP)],
    }


def tamanho(arquivos: list[Path], raiz: Path) -> dict:
    pares = [(str(p.relative_to(raiz)).replace("\\", "/"), linhas(p)) for p in arquivos]
    pares = [(a, n) for a, n in pares if n > 0]
    if not pares:
        return {"disponivel": False, "grandes": []}
    valores = sorted(n for _, n in pares)
    grandes = sorted((p for p in pares if p[1] >= LIMITE_ARQUIVO_GRANDE),
                     key=lambda x: -x[1])[:TOP]
    return {
        "disponivel": True,
        "arquivos": len(pares),
        "linhas_totais": sum(valores),
        "mediana": statistics.median(valores),
        "p90": valores[int(0.9 * (len(valores) - 1))],
        "maximo": valores[-1],
        "limite_grande": LIMITE_ARQUIVO_GRANDE,
        "grandes": [{"arquivo": a, "linhas": n} for a, n in grandes],
    }


def atividade(raiz: Path, dias: int) -> dict:
    saida = git(raiz, "log", f"--since={dias} days ago", "--pretty=format:%ad", "--date=short")
    if not saida.strip():
        return {"disponivel": False}
    datas = [l.strip() for l in saida.splitlines() if l.strip()]
    ultimo = git(raiz, "log", "-1", "--pretty=format:%ad", "--date=short").strip()
    autores = git(raiz, "log", f"--since={dias} days ago", "--pretty=format:%an")
    return {
        "disponivel": True,
        "commits_na_janela": len(datas),
        "commits_por_semana": round(len(datas) / max(1, dias / 7), 1),
        "dias_com_commit": len(set(datas)),
        "autores_distintos": len({a.strip() for a in autores.splitlines() if a.strip()}),
        "ultimo_commit": ultimo,
    }


# --- montagem ----------------------------------------------------------------------

def coletar(raiz: Path, dias: int) -> dict:
    arquivos = fontes(raiz)
    ch = churn(raiz, dias) if tem_git(raiz) else {"disponivel": False, "motivo": "não é repositório git", "top": []}
    hot = [i["arquivo"] for i in ch.get("top", [])]
    return {
        "raiz": str(raiz),
        "janela_dias": dias,
        "nivel_evidencia": 1,
        "nivel_descricao": "somente repositório — sem execução da aplicação nem telemetria de produção",
        "git": tem_git(raiz),
        "atividade": atividade(raiz, dias) if tem_git(raiz) else {"disponivel": False},
        "churn": ch,
        "autoria": autoria(raiz, hot, dias) if tem_git(raiz) else {"disponivel": False, "itens": []},
        "teste": cobertura_estrutural(arquivos, raiz),
        "dependencias": dependencias(raiz),
        "marcadores": marcadores(arquivos, raiz),
        "tamanho": tamanho(arquivos, raiz),
    }


def imprimir(d: dict) -> None:
    print(f"📋 Diagnóstico — evidência de nível {d['nivel_evidencia']} ({d['janela_dias']}d)")
    print(f"   {d['nivel_descricao']}\n")

    a = d["atividade"]
    if a.get("disponivel"):
        print(f"  Atividade:      {a['commits_na_janela']} commits "
              f"({a['commits_por_semana']}/semana) · {a['autores_distintos']} autor(es) · "
              f"último em {a['ultimo_commit']}")
    else:
        print("  Atividade:      — (sem histórico git)")

    t = d["tamanho"]
    if t.get("disponivel"):
        print(f"  Código:         {t['arquivos']} arquivos · {t['linhas_totais']} linhas · "
              f"mediana {t['mediana']:.0f} · p90 {t['p90']} · máx {t['maximo']}")
        if t["grandes"]:
            print(f"                  {len(t['grandes'])} arquivo(s) ≥ {t['limite_grande']} linhas — "
                  f"maior: {t['grandes'][0]['arquivo']} ({t['grandes'][0]['linhas']})")

    te = d["teste"]
    r = te["razao_teste_producao"]
    print(f"  Teste:          {te['arquivos_de_teste']} de teste / {te['arquivos_de_producao']} de produção"
          f" · razão {r if r is not None else '—'}  ({te['nota']})")

    m = d["marcadores"]
    print(f"  Dívida marcada: {m['total']} marcadores · {m['por_mil_linhas']} por mil linhas")

    ch = d["churn"]
    if ch.get("disponivel"):
        print(f"\n  Hotspots de código ({len(ch['top'])} de "
              f"{ch.get('arquivos_codigo_tocados', 0)} arquivos de código tocados, "
              f"{ch['arquivos_tocados']} no total):")
        au = {i["arquivo"]: i for i in d["autoria"].get("itens", [])}
        for i in ch["top"]:
            info = au.get(i["arquivo"], {})
            solo = info.get("autor_unico")
            marca = f"  ⚠️  autor único: {solo}" if solo else ""
            print(f"    {i['alteracoes']:>3}×  {i['arquivo']}{marca}")
        solos = d["autoria"].get("hotspots_com_autor_unico", 0)
        if solos:
            print(f"\n  ⚠️  {solos} de {d['autoria']['total_hotspots']} hotspots têm autor único "
                  "na janela — concentração de conhecimento")

    dep = d["dependencias"]
    if dep.get("disponivel"):
        print("\n  Dependências:")
        for man in dep["manifestos"]:
            tot = man["total"] if man["total"] is not None else "?"
            fr = man["sem_versao_fixa"]
            extra = f" · {fr} sem versão fixa" if fr else ""
            print(f"    {man['manifesto']} ({man['ecossistema']}): {tot}{extra}")

    print("\n  Estes números são MEDIDOS. Causa e prioridade são julgamento — "
          "veja /kairos-forge:diagnosticar.")


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] != "coletar":
        print(__doc__.strip())
        return 1
    args = args[1:]

    como_json = "--json" in args
    args = [a for a in args if a != "--json"]

    dias = 90
    if "--dias" in args:
        i = args.index("--dias")
        try:
            dias = int(args[i + 1])
        except (IndexError, ValueError):
            print("erro: --dias precisa de um número", file=sys.stderr)
            return 1
        args = args[:i] + args[i + 2:]

    raiz = Path(args[0]).resolve() if args else Path.cwd()
    if not raiz.is_dir():
        print(f"erro: {raiz} não é um diretório", file=sys.stderr)
        return 1

    d = coletar(raiz, dias)
    print(json.dumps(d, ensure_ascii=False, indent=2)) if como_json else imprimir(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
