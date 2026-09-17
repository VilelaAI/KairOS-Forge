#!/usr/bin/env python3
"""prova.py — prova negativa dos testes de um diff (ADR-0039).

Código ficou barato; prova, não. A fábrica já cobra `verificado:` na SPEC e corrobora o
comando na trajetória (ADR-0021), mas as duas checagens aceitam um teste que **passa** —
e um teste que passa também sem a mudança não prova a mudança. Este script fecha as duas
formas silenciosas de gate verde sem prova:

  1. Teste novo que não testa nada — o teste escrito junto com o patch é rodado contra
     o código de ANTES do patch. Se passa ali, não prova o que o patch fez.
  2. Teste existente afrouxado — asserção removida, caso pulado (`skip`), caso apagado
     ou arquivo de teste deletado no mesmo diff. Suite verde que o agente afrouxou não
     é evidência; é o medidor sendo reescrito (o mesmo Goodhart do `guardrail.py`).

Nenhum dos dois é veredicto sozinho: refactor legítimo muda teste, e um teste de
regressão de bug já corrigido passa na base por definição. O que o script faz é
transformar o silêncio em achado com nome, para o `/kairos-forge:validar` cobrar a
justificativa — e o `/kairos-forge:revisar` ler antes de aprovar.

## Uso

    prova.py pre-patch        [--base REF] [--comando "TEMPLATE"] [--tempo-limite S] [--json]
    prova.py testes-alterados [--base REF] [--json]

`--base` é a ref contra a qual o diff é medido (default: `origin/HEAD`, depois
`origin/main`, `origin/master`, `main`, `master` — o primeiro que existir). O diff
inclui o que ainda não foi commitado.

`--comando` é o template do gate por arquivo, com `{arquivo}` no lugar do caminho
(ex.: `--comando "python3 -m pytest -q {arquivo}"`). Sem ele, o script deduz por
extensão: pytest (ou unittest) para `.py`, vitest/jest pelo `package.json` para
JS/TS, `go test` para `_test.go`. Ecossistema que ele não reconhece sai como
`nao_executado` — declarado, nunca inventado.

## Veredictos do `pre-patch`, por teste novo

    falhou_na_base   ✅ o teste depende da mudança — prova algo
    passou_na_base   ❌ o teste passa sem a mudança — não prova a mudança
    nao_executado    ⚠️  sem comando conhecido, sem coleta, ou estourou o tempo

Exit 1 se houver `passou_na_base`; 0 caso contrário. `testes-alterados` sai 1 se houver
sinal de afrouxamento — usável em CI e pre-commit, mas o veredicto é de quem valida.

## Como o pre-patch roda

Cria um worktree descartável na base do diff, copia só os testes novos para dentro e
roda o gate lá — o worktree é removido ao final. `node_modules`, `.venv`, `venv` e
`vendor` da raiz são ligados por symlink no worktree quando existem, para que "faltou
dependência" não se disfarce de "falhou na base". Limite declarado: teste que falha na
base por motivo alheio ao patch (fixture ausente, serviço externo) conta como
`falhou_na_base` — o script lê exit code, não intenção. Só stdlib.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

# --- o que é arquivo de teste ------------------------------------------------------
# Mesma família de padrões do lembrete de DoD do hooks.json e do `execucao.py`, mais
# estrita no nome: `test|spec` no meio de um nome qualquer (`contest.py`) não casa.
PADRAO_TESTE = re.compile(
    r"(^|/)(tests?|__tests__|specs?|testing)/"
    r"|(^|/)test_[^/]+\.py$"
    r"|_test\.py$"
    r"|_test\.go$"
    r"|_spec\.rb$"
    r"|\.(test|spec)\.(js|jsx|ts|tsx|mjs|cjs)$"
    r"|Tests?\.(java|kt|cs|swift)$"
    r"|_test\.(exs|rs)$"
)

# Sinais de afrouxamento no diff de um teste existente. Linhas REMOVIDAS que casem com
# `ASSERCAO` ou `CASO`, e linhas ADICIONADAS que casem com `PULO`.
ASSERCAO = re.compile(
    r"\b(assert\w*|expect|should|require\.\w+|t\.(Error|Fatal|Fail)\w*|assert_eq!|assert!|XCTAssert\w*)\b"
)
CASO = re.compile(
    r"^\s*(def test_\w+|async def test_\w+|func Test\w+|it\(|test\(|it\.each|test\.each"
    r"|describe\(|context\(|#\[test\]|@Test\b|\[Fact\]|\[Theory\])"
)
PULO = re.compile(
    r"(@pytest\.mark\.skip|pytest\.skip\(|@unittest\.skip|\.skip\(|\bxit\(|\bxdescribe\(|\bxtest\("
    r"|\bfit\(|\bfdescribe\(|\.only\(|t\.Skip\(|#\[ignore\]|@Ignore\b|\[Skip\]|\bskip:\s*true)"
)

# Padrões na saída que dizem "não coletei nada" mesmo com exit ≠ 0 — não é falha.
SEM_COLETA = re.compile(
    r"(?i)(no tests? (found|collected|ran)|collected 0 items|no test files found"
    r"|\[no test files\]|Ran 0 tests|NO TESTS RAN)"
)


def eh_teste(rel: str) -> bool:
    return bool(PADRAO_TESTE.search(rel.replace("\\", "/")))


# --- git ---------------------------------------------------------------------------

def git(raiz: Path, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(raiz), *args], capture_output=True,
                          text=True, timeout=timeout)


def raiz_git(inicio: Path | None = None) -> Path | None:
    r = git(inicio or Path.cwd(), "rev-parse", "--show-toplevel")
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def base_padrao(raiz: Path) -> str | None:
    """A ref contra a qual o diff é medido, na ordem em que a maioria dos repos tem."""
    r = git(raiz, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    candidatas = ([r.stdout.strip()] if r.returncode == 0 and r.stdout.strip() else []) + [
        "origin/main", "origin/master", "main", "master"]
    for ref in candidatas:
        if git(raiz, "rev-parse", "--verify", "--quiet", ref).returncode == 0:
            return ref
    return None


def ponto_de_partida(raiz: Path, base: str) -> str | None:
    """merge-base entre a base e o HEAD — o 'antes do patch' de uma branch de feature."""
    r = git(raiz, "merge-base", base, "HEAD")
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def diff_nomes(raiz: Path, ponto: str) -> list[tuple[str, str]]:
    """(status, caminho) do diff árvore-de-trabalho vs ponto, incluindo não-commitado.

    Renomeação vira M do destino: o conteúdo é o que importa para afrouxamento.
    """
    r = git(raiz, "diff", "--name-status", "-M", ponto)
    pares = []
    for linha in r.stdout.splitlines():
        partes = linha.split("\t")
        if len(partes) < 2:
            continue
        status = partes[0][:1]
        caminho = partes[-1]
        if status == "R":
            status = "M"
        pares.append((status, caminho))
    return pares


def nao_rastreados(raiz: Path) -> list[str]:
    r = git(raiz, "ls-files", "--others", "--exclude-standard")
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


# --- 1. teste pré-patch ------------------------------------------------------------

def testes_novos(raiz: Path, ponto: str) -> list[str]:
    novos = [c for s, c in diff_nomes(raiz, ponto) if s == "A" and eh_teste(c)]
    novos += [c for c in nao_rastreados(raiz) if eh_teste(c)]
    return sorted(dict.fromkeys(novos))


def _tem_dependencia_js(raiz: Path, nome: str) -> bool:
    pkg = raiz / "package.json"
    if not pkg.is_file():
        return False
    try:
        d = json.loads(pkg.read_text(encoding="utf-8"))
    except Exception:
        return False
    for chave in ("devDependencies", "dependencies"):
        if nome in (d.get(chave) or {}):
            return True
    return False


def _tem_modulo(nome: str) -> bool:
    r = subprocess.run([sys.executable, "-c", f"import {nome}"], capture_output=True)
    return r.returncode == 0


def comando_para(raiz: Path, arquivo: str, template: str | None) -> tuple[str, str] | None:
    """(comando, cwd relativo) para rodar UM arquivo de teste — ou None se não sabe."""
    if template:
        return template.replace("{arquivo}", arquivo), "."
    suf = Path(arquivo).suffix
    if suf == ".py":
        if _tem_modulo("pytest"):
            return f"{sys.executable} -m pytest -q -p no:cacheprovider {arquivo}", "."
        modulo = arquivo[:-3].replace("/", ".")
        return f"{sys.executable} -m unittest {modulo}", "."
    if suf in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
        if _tem_dependencia_js(raiz, "vitest"):
            return f"npx vitest run {arquivo}", "."
        if _tem_dependencia_js(raiz, "jest"):
            return f"npx jest --ci {arquivo}", "."
        return None
    if arquivo.endswith("_test.go"):
        pacote = str(Path(arquivo).parent)
        return ("go test ." if pacote == "." else f"go test ./{pacote}/"), "."
    return None


def ligar_dependencias(raiz: Path, worktree: Path) -> list[str]:
    """Symlinks das pastas de dependência — dependência ausente não é falha na base."""
    ligadas = []
    for nome in ("node_modules", ".venv", "venv", "vendor"):
        origem = raiz / nome
        destino = worktree / nome
        if origem.is_dir() and not destino.exists():
            try:
                os.symlink(origem, destino, target_is_directory=True)
                ligadas.append(nome)
            except OSError:
                pass
    return ligadas


def pre_patch(raiz: Path, base: str | None, template: str | None,
              tempo_limite: int) -> dict:
    base = base or base_padrao(raiz)
    if not base:
        return {"erro": "nenhuma ref de base encontrada — passe --base", "testes": []}
    ponto = ponto_de_partida(raiz, base)
    if not ponto:
        return {"erro": f"sem merge-base entre {base} e HEAD", "testes": []}

    novos = testes_novos(raiz, ponto)
    resultado = {"base": base, "ponto": ponto[:12], "testes": [], "ligadas": []}
    if not novos:
        resultado["aviso"] = "nenhum teste novo no diff — nada a provar aqui"
        return resultado

    tmp = Path(tempfile.mkdtemp(prefix="kairos-forge-prova-"))
    worktree = tmp / "base"
    try:
        r = git(raiz, "worktree", "add", "--detach", str(worktree), ponto, timeout=120)
        if r.returncode != 0:
            return {"erro": f"não consegui criar worktree na base: {r.stderr.strip()[:200]}",
                    "testes": []}
        resultado["ligadas"] = ligar_dependencias(raiz, worktree)
        for rel in novos:
            item = {"arquivo": rel, "veredicto": "nao_executado", "motivo": "", "comando": ""}
            resultado["testes"].append(item)
            origem = raiz / rel
            destino = worktree / rel
            try:
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origem, destino)
            except OSError as e:
                item["motivo"] = f"não copiei o teste para o worktree: {e}"
                continue
            par = comando_para(raiz, rel, template)
            if par is None:
                item["motivo"] = "ecossistema sem comando conhecido — passe --comando"
                continue
            cmd, cwd = par
            item["comando"] = cmd
            try:
                p = subprocess.run(cmd, shell=True, cwd=str(worktree / cwd),
                                   capture_output=True, text=True, timeout=tempo_limite)
            except subprocess.TimeoutExpired:
                item["motivo"] = f"estourou {tempo_limite}s"
                continue
            saida = (p.stdout or "") + (p.stderr or "")
            if SEM_COLETA.search(saida) or p.returncode == 5:  # 5 = pytest sem coleta
                item["motivo"] = "nenhum teste coletado no worktree da base"
                continue
            if p.returncode == 0:
                item["veredicto"] = "passou_na_base"
                item["motivo"] = "passa sem a mudança — não prova a mudança"
            else:
                item["veredicto"] = "falhou_na_base"
                item["motivo"] = f"exit {p.returncode} na base"
                item["ultimas_linhas"] = [l for l in saida.strip().splitlines() if l.strip()][-3:]
    finally:
        git(raiz, "worktree", "remove", "--force", str(worktree), timeout=60)
        git(raiz, "worktree", "prune")
        shutil.rmtree(tmp, ignore_errors=True)
    return resultado


# --- 2. testes existentes alterados -----------------------------------------------

def sinais_de_afrouxamento(raiz: Path, ponto: str, rel: str) -> dict:
    r = git(raiz, "diff", "-U0", ponto, "--", rel)
    removidas = adicionadas = 0
    assercoes_removidas: list[str] = []
    casos_removidos: list[str] = []
    pulos_adicionados: list[str] = []
    for linha in r.stdout.splitlines():
        if linha.startswith("---") or linha.startswith("+++"):
            continue
        if linha.startswith("-"):
            removidas += 1
            corpo = linha[1:]
            if CASO.match(corpo):
                casos_removidos.append(corpo.strip()[:80])
            elif ASSERCAO.search(corpo):
                assercoes_removidas.append(corpo.strip()[:80])
        elif linha.startswith("+"):
            adicionadas += 1
            corpo = linha[1:]
            if PULO.search(corpo):
                pulos_adicionados.append(corpo.strip()[:80])
    return {
        "arquivo": rel, "status": "M",
        "linhas_removidas": removidas, "linhas_adicionadas": adicionadas,
        "assercoes_removidas": assercoes_removidas,
        "casos_removidos": casos_removidos,
        "pulos_adicionados": pulos_adicionados,
        "sinal": bool(assercoes_removidas or casos_removidos or pulos_adicionados),
    }


def testes_alterados(raiz: Path, base: str | None) -> dict:
    base = base or base_padrao(raiz)
    if not base:
        return {"erro": "nenhuma ref de base encontrada — passe --base", "testes": []}
    ponto = ponto_de_partida(raiz, base)
    if not ponto:
        return {"erro": f"sem merge-base entre {base} e HEAD", "testes": []}
    itens = []
    for status, rel in diff_nomes(raiz, ponto):
        if not eh_teste(rel):
            continue
        if status == "D":
            itens.append({"arquivo": rel, "status": "D", "sinal": True,
                          "linhas_removidas": 0, "linhas_adicionadas": 0,
                          "assercoes_removidas": [], "casos_removidos": [],
                          "pulos_adicionados": []})
        elif status == "M":
            itens.append(sinais_de_afrouxamento(raiz, ponto, rel))
    return {"base": base, "ponto": ponto[:12], "testes": itens,
            "com_sinal": sum(1 for i in itens if i["sinal"])}


# --- apresentação ------------------------------------------------------------------

ROTULO = {
    "falhou_na_base": "✅ falhou na base",
    "passou_na_base": "❌ PASSOU na base",
    "nao_executado": "⚠️  não executado",
}


def imprimir_pre_patch(r: dict) -> None:
    if r.get("erro"):
        print(f"🚫 prova pré-patch: {r['erro']}")
        return
    print(f"🧪 Prova pré-patch — base {r['base']} ({r['ponto']})")
    if r.get("aviso"):
        print(f"   {r['aviso']}")
        return
    if r.get("ligadas"):
        print(f"   dependências ligadas no worktree: {', '.join(r['ligadas'])}")
    for t in r["testes"]:
        print(f"   {ROTULO[t['veredicto']]}  {t['arquivo']}")
        print(f"      {t['motivo']}")
        for l in t.get("ultimas_linhas", []):
            print(f"      │ {l[:110]}")
    ruins = [t for t in r["testes"] if t["veredicto"] == "passou_na_base"]
    if ruins:
        print(f"\n   {len(ruins)} teste(s) novo(s) passam sem a mudança. Ou o teste não exercita "
              "o que o patch fez,\n   ou é regressão de comportamento que a base já tinha — "
              "nos dois casos a justificativa vai no relatório de validação.")
    else:
        print("\n   Nenhum teste novo passa na base sem a mudança.")


def imprimir_testes_alterados(r: dict) -> None:
    if r.get("erro"):
        print(f"🚫 testes alterados: {r['erro']}")
        return
    print(f"🔍 Testes existentes no diff — base {r['base']} ({r['ponto']})")
    if not r["testes"]:
        print("   nenhum teste existente modificado ou removido.")
        return
    for t in r["testes"]:
        marca = "❌" if t["sinal"] else "·"
        if t["status"] == "D":
            print(f"   {marca} {t['arquivo']}  — ARQUIVO DE TESTE REMOVIDO")
            continue
        print(f"   {marca} {t['arquivo']}  (+{t['linhas_adicionadas']} −{t['linhas_removidas']})")
        for rot, lista in (("asserção removida", t["assercoes_removidas"]),
                           ("caso removido", t["casos_removidos"]),
                           ("pulo adicionado", t["pulos_adicionados"])):
            for l in lista[:4]:
                print(f"      {rot}: {l}")
            if len(lista) > 4:
                print(f"      … e mais {len(lista) - 4} ({rot})")
    if r["com_sinal"]:
        print(f"\n   {r['com_sinal']} arquivo(s) com sinal de afrouxamento. Refactor legítimo "
              "também muda teste —\n   a diferença é a justificativa escrita, que o "
              "/kairos-forge:validar cobra por arquivo.")
    else:
        print("\n   Teste existente mudou sem sinal de afrouxamento.")


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] not in ("pre-patch", "testes-alterados"):
        print(__doc__.strip())
        return 1
    comando = args[0]
    como_json = "--json" in args
    args = [a for a in args if a != "--json"]

    def opcao(nome: str) -> str | None:
        if nome in args:
            i = args.index(nome)
            if i + 1 < len(args):
                return args[i + 1]
        return None

    base = opcao("--base")
    template = opcao("--comando")
    try:
        tempo = int(opcao("--tempo-limite") or 300)
    except ValueError:
        print("erro: --tempo-limite precisa de um número de segundos", file=sys.stderr)
        return 1

    raiz = raiz_git()
    if raiz is None:
        print("🚫 fora de um repositório git — sem diff não há prova", file=sys.stderr)
        return 1

    if comando == "pre-patch":
        r = pre_patch(raiz, base, template, tempo)
        if como_json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            imprimir_pre_patch(r)
        if r.get("erro"):
            return 1
        return 1 if any(t["veredicto"] == "passou_na_base" for t in r["testes"]) else 0

    r = testes_alterados(raiz, base)
    if como_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        imprimir_testes_alterados(r)
    if r.get("erro"):
        return 1
    return 1 if r.get("com_sinal") else 0


if __name__ == "__main__":
    sys.exit(main())
