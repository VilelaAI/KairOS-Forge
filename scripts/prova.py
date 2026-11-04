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

A mesma pergunta vale para o eval (ADR-0043): só o conjunto selado aprova, e um selado
que foi copiado para o texto que o sistema avaliado lê aprova quem já leu a resposta.

  3. Eval que já viu o gabarito — caso de `evals/<slug>/selado.jsonl` presente, ao pé
     da letra, em prompt, skill, persona, `contextos/`, teste ou doc do repositório, ou
     repetido no `gold.jsonl` visível do mesmo eval.

E o histórico vira prova (ADR-0044): cada entrega da fábrica já mesclada, com teste no
diff, é um caso pronto — o pedido, o commit de antes e os testes como gabarito. O
`colher` junta esses casos em `evals/entregas/candidatos.jsonl`; com `--validar`, só
entra o caso cujo teste falha na base e passa na entrega, porque teste que passa na
base não separa quem resolveu de quem não resolveu.

E a revisão ganha candidatos com nome: o `atalhos` lista, nas linhas que o diff
acrescenta em código, os desvios que o `guardrail.py` não pegava — TLS desligado, erro
engolido, tipo burlado, HTML sem escape e `sleep` como sincronização. Adaptado do
`scan_bypasses.py` da skill the-judge (Felipe Rodrigues, CC-BY-4.0). Cada linha é
candidata, nunca achado: `except: pass` numa limpeza e `sleep` num backoff são
legítimos. Quem julga é o revisor, por isso o `atalhos` sai com 0 sempre que leu o diff.

E a validação ganha o que a SPEC não sabe: o `decisoes` lista o que se decidiu depois da
aprovação — ADR, linha no `decisoes/log.md`, convenção em `contextos/`, lição em
`.agents/memory/`, o `DESIGN.md` — na branch depois do selo da SPEC e na base fora da
branch, e liga cada decisão à entrega pelo que se lê sem modelo: o id da SPEC, um id de
requisito, a issue de origem ou um arquivo do diff. Com `--github`, os comentários da
issue de origem depois da aprovação também entram. Ligar não é julgar: quem diz se a
entrega segue ou contradiz a decisão é o `/validar`, por isso sai 0 sempre que leu.

## Uso

    prova.py pre-patch        [--base REF] [--comando "TEMPLATE"] [--tempo-limite S] [--json]
    prova.py testes-alterados [--base REF] [--json]
    prova.py atalhos          [--base REF] [--json]
    prova.py decisoes SPEC-NNN [--base REF] [--desde DATA] [--github] [--json]
    prova.py selado           [--raiz DIR] [--json]
    prova.py colher           [--dias N] [--saida ARQ] [--validar] [--comando "TEMPLATE"]
                              [--fonte gh|git] [--json]

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
`falhou_na_base` — o script lê exit code, não intenção.

## Como o selado é comparado

Cada string de cada caso selado (menos o `id`) vira um trecho normalizado: minúsculas,
só palavras, espaço único. Trecho com menos de seis palavras não é comparado — nome de
agente e rótulo curto aparecem na instrução por coincidência — e sai contado como
"curto", nunca como "limpo". O trecho é procurado, com fronteira de palavra, em todo
arquivo de texto do repositório, menos `evals/` (onde o eval mora, com os relatórios),
`.agents/execucoes/` (a trajetória de quem rodou o eval) e diretórios de dependência.
O `gold.jsonl` irmão é lido à parte: caso selado repetido no visível também é vazamento.

É um alarme, não a defesa (a ideia vem do `assert_no_grader_verdicts` do Harness²): se
ele dispara, ache o caminho por onde o caso chegou à instrução, em vez de afrouxar a
regra. Pega cópia; paráfrase passa — a divergência visível × selado do relatório do
`/kairos-forge:avaliar` é quem mede o ajuste que não deixa rastro literal. Sem
`selado.jsonl` no repositório, o script diz que não há o que proteger e sai 0. Só stdlib.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from execucao import pasta_do_projeto
except Exception:                     # cópia avulsa do script, sem o execucao.py ao lado
    def pasta_do_projeto(raiz, nome: str) -> Path:
        return Path(raiz) / ".agents" / nome


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


# --- conjunto selado (ADR-0043) ----------------------------------------------------
MIN_PALAVRAS_SELADO = 6
LIMITE_BYTES_SELADO = 1_000_000
DIRS_IGNORADOS_SELADO = {
    ".git", "node_modules", ".venv", "venv", "vendor", "dist", "build", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
}
PREFIXOS_IGNORADOS_SELADO = ("evals/", ".agents/execucoes/")


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


# --- atalhos no diff (do the-judge) -------------------------------------------------
# Só as categorias que ainda não tinham dono: supressão inline é da classe `regua` do
# `guardrail.py`, e teste pulado é do `testes-alterados`.

ATALHOS = (
    ("tls-desligado", re.compile(
        r"rejectUnauthorized\s*:\s*false|verify\s*=\s*False\b|InsecureSkipVerify\s*:\s*true"
        r"|NODE_TLS_REJECT_UNAUTHORIZED|CURLOPT_SSL_VERIFYPEER\s*,\s*(false|0)\b")),
    ("erro-engolido", re.compile(
        r"^\s*except(\s+[\w.(), ]+?(\s+as\s+\w+)?)?\s*:\s*(pass|\.\.\.)\s*$"
        r"|catch\s*(\([^)]*\))?\s*\{\s*\}|\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*\{\s*\}\s*\)")),
    ("tipo-burlado", re.compile(r"\bas\s+any\b|\bas\s+unknown\s+as\b")),
    ("html-sem-escape", re.compile(
        r"dangerouslySetInnerHTML|bypassSecurityTrust\w*|\bv-html\b|\bmark_safe\s*\("
        r"|\.innerHTML\s*=(?!=)")),
    ("sleep-como-sincronia", re.compile(
        r"\btime\.sleep\s*\(|\bThread\.sleep\s*\(|\bawait\s+(sleep|delay)\s*\(")),
)
EXT_CODIGO = {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".go",
              ".rb", ".java", ".kt", ".rs", ".php", ".cs", ".swift", ".scala", ".vue",
              ".svelte"}
CABECALHO = re.compile(r"^\+\+\+ b/(.+)$")
TRECHO = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


ABRE_EXCECAO = re.compile(r"^\s*except\b[^:]*:\s*$|catch\s*(\([^)]*\))?\s*\{\s*$")
CORPO_VAZIO = re.compile(r"^\s*(pass|\.\.\.|\})\s*$")


def categoria_de(linha: str) -> str | None:
    return next((nome for nome, rx in ATALHOS if rx.search(linha)), None)


def engolido_em_duas_linhas(anterior: tuple | None, rel: str, n: int, linha: str) -> bool:
    """`except X:` numa linha e `pass` na seguinte — a forma em que o Python é escrito."""
    return (anterior is not None and anterior[0] == rel and anterior[1] == n - 1
            and bool(ABRE_EXCECAO.search(anterior[2])) and bool(CORPO_VAZIO.match(linha)))


def linhas_acrescentadas(raiz: Path, ponto: str):
    """(arquivo, número da linha, texto) de cada linha nova, commitada ou não."""
    yield from _linhas_do_diff(raiz, ponto)
    yield from _linhas_nao_rastreadas(raiz)


def _linhas_do_diff(raiz: Path, *refs: str):
    arquivo, numero, anterior = None, 0, ""
    for linha in git(raiz, "diff", "-U0", "--no-color", *refs).stdout.splitlines():
        trecho = TRECHO.match(linha)
        if linha.startswith("+++ ") and anterior.startswith("--- "):
            m = CABECALHO.match(linha)
            arquivo = m.group(1) if m else None      # `+++ /dev/null`: arquivo apagado
        elif trecho:
            numero = int(trecho.group(1))
        elif linha.startswith("+") and arquivo:
            yield arquivo, numero, linha[1:]
            numero += 1
        anterior = linha


def _linhas_nao_rastreadas(raiz: Path):
    for rel in nao_rastreados(raiz):
        try:
            texto = (raiz / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for i, linha in enumerate(texto.splitlines(), 1):
            yield rel, i, linha


def atalhos(raiz: Path, base: str | None) -> dict:
    base = base or base_padrao(raiz)
    ponto = ponto_de_partida(raiz, base) if base else None
    if not ponto:
        return {"erro": f"sem base para o diff ({base or 'nenhuma ref'}) — passe --base",
                "candidatos": []}
    candidatos, anterior = [], None
    for rel, n, linha in linhas_acrescentadas(raiz, ponto):
        if Path(rel).suffix not in EXT_CODIGO:
            continue
        if engolido_em_duas_linhas(anterior, rel, n, linha):
            cat, n_cand, trecho = "erro-engolido", n - 1, f"{anterior[2].strip()} {linha.strip()}"
        else:
            cat, n_cand, trecho = categoria_de(linha), n, linha.strip()
        if cat:
            candidatos.append({"arquivo": rel, "linha": n_cand, "categoria": cat,
                               "teste": eh_teste(rel), "trecho": trecho[:160]})
        anterior = (rel, n, linha)
    return {"base": base, "ponto": ponto[:12], "candidatos": candidatos}


# --- decisões registradas depois da aprovação da SPEC ------------------------------
# A SPEC é o contrato do dia em que foi aprovada. O que se decidiu depois ela não sabe, e
# a validação contra ela também não: "essa lógica não está alinhada com a última coisa que
# foi decidida" (aula 5 do Tech Leads Club). O cérebro da fábrica é a memória curada e
# versionada, então dá para listar o que entrou nela depois do selo e ligar à entrega.

DECISAO = re.compile(r"^(?:docs/adr/|decisoes/(?!auditorias/|evolucoes/|otimizacoes/|gestao/)"
                     r"|\.agents/memory/|contextos/).*\.md$|^DESIGN\.md$")
ID_SPEC = re.compile(r"^SPEC-\d+$", re.I)
REQUISITO_DA_SPEC = re.compile(r"^\|\s*([A-Z][A-Z0-9]*-\d+)\s*\|", re.M)
ISSUE_DE_ORIGEM = re.compile(r"\*\*Origem:\*\*[^\n]*?#(\d+)")
ENTRADA_DATADA = re.compile(r"^#{1,6}\s+\d{4}-\d{2}-\d{2}\b")
TITULO_MD = re.compile(r"^#{1,6}\s+(.+)$")
ARVORE_VAZIA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
FORA_DA_ENTREGA = (".agents/", "decisoes/", "docs/specs/")   # estado, registro e contrato


def eh_decisao(rel: str) -> bool:
    """ADR, registro de decisão, lição e convenção. Relatório (auditoria, evolução,
    otimização, status) não é decisão, e fica de fora."""
    return bool(DECISAO.match(rel.replace("\\", "/")))


def instante(texto: str | None) -> datetime | None:
    """ISO com ou sem hora; data sozinha é a meia-noite UTC daquele dia."""
    try:
        t = datetime.fromisoformat(str(texto).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def arquivo_da_spec(raiz: Path, spec: str) -> Path | None:
    pasta = raiz / "docs" / "specs"
    achados = sorted([*pasta.glob(f"{spec}-*.md"), *pasta.glob(f"{spec}.md")])
    return achados[0] if achados else None


def momento_da_aprovacao(raiz: Path, spec: str, arquivo: Path | None) -> tuple[str | None, str]:
    """(instante, fonte). O selo do `ciclo.py` é a aprovação; sem ciclo, o último commit da
    SPEC, porque o contrato que a entrega seguiu é o que estava escrito ali."""
    try:
        d = json.loads((pasta_do_projeto(raiz, "ciclo") / f"{spec}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if isinstance(d, dict) and d.get("spec_selada_em"):
        return str(d["spec_selada_em"]), "selo da SPEC no ciclo"
    rel = arquivo.relative_to(raiz).as_posix() if arquivo else None
    quando = git(raiz, "log", "-1", "--format=%cI", "--", rel).stdout.strip() if rel else ""
    return (quando, "último commit da SPEC") if quando else (None, "")


def commit_no_momento(raiz: Path, quando: str) -> str:
    """O último commit da linha da branch até o instante; antes do primeiro, a árvore vazia."""
    r = git(raiz, "rev-list", "-1", "--first-parent", f"--before={quando}", "HEAD")
    return r.stdout.strip() or ARVORE_VAZIA


def entradas(linhas, origem: str) -> list[dict]:
    """Linhas acrescentadas e contíguas de um arquivo viram uma entrada; um título datado
    (`## AAAA-MM-DD`, o formato do `decisoes/log.md`) abre outra."""
    lista: list[dict] = []
    for rel, n, texto in linhas:
        atual = lista[-1] if lista else None
        if not (atual and atual["arquivo"] == rel and atual["ate"] == n - 1
                and not ENTRADA_DATADA.match(texto)):
            atual = {"origem": origem, "arquivo": rel, "linha": n, "ate": n, "texto": []}
            lista.append(atual)
        atual["texto"].append(texto)
        atual["ate"] = n
    return [e for e in lista if any(l.strip() for l in e["texto"])]


def titulo_da_entrada(e: dict) -> str:
    titulos = [m.group(1).strip() for m in map(TITULO_MD.match, e["texto"]) if m]
    return (titulos or [l.strip() for l in e["texto"] if l.strip()])[0][:90]


def alvo_da_entrega(raiz: Path, spec: str, arquivo: Path | None, ponto: str) -> dict:
    """O que liga uma decisão a esta entrega: SPEC, requisitos, issue de origem e arquivos."""
    texto = arquivo.read_text(encoding="utf-8", errors="replace") if arquivo else ""
    issue = ISSUE_DE_ORIGEM.search(texto)
    tocados = {c for _, c in diff_nomes(raiz, ponto)} | set(nao_rastreados(raiz))
    return {"spec": spec, "requisitos": sorted(set(REQUISITO_DA_SPEC.findall(texto))),
            "issue": issue.group(1) if issue else None,
            "arquivos": sorted(a for a in tocados
                               if not eh_decisao(a) and not a.startswith(FORA_DA_ENTREGA))}


def cita(texto: str, termo: str) -> bool:
    """`termo` aparece inteiro: `SPEC-01` não casa em `SPEC-012`, nem `x.py` em `lib/x.py`."""
    return bool(re.search(rf"(?<![\w/.-]){re.escape(termo)}(?![\w-])", texto, re.I))


def vinculos(texto: str, alvo: dict) -> list[str]:
    ids = [alvo["spec"], *alvo["requisitos"]]
    achados = [i for i in ids if cita(texto, i)]
    if alvo["issue"] and re.search(rf"#{alvo['issue']}\b", texto):
        achados.append(f"issue #{alvo['issue']}")
    achados += [a for a in alvo["arquivos"]
                if cita(texto, a) or (len(Path(a).name) >= 6 and cita(texto, Path(a).name))]
    return achados[:6]


def _primeira_linha(texto) -> str:
    return next((l.strip() for l in str(texto or "").splitlines() if l.strip()), "")[:120]


def _issue_do_gh(raiz: Path, issue: str) -> dict | None:
    try:
        r = subprocess.run(["gh", "issue", "view", issue, "--json", "comments"], cwd=raiz,
                           capture_output=True, timeout=60)
        dados = json.loads(r.stdout) if r.returncode == 0 else None   # json lê bytes em UTF-8
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return dados if isinstance(dados, dict) else None


def _comentario(c: dict) -> dict:
    return {"autor": (c.get("author") or {}).get("login") or "?", "quando": c.get("createdAt"),
            "trecho": _primeira_linha(c.get("body"))}


def comentarios_da_issue(raiz: Path, issue: str, desde: str) -> dict:
    """Comentários da issue de origem depois da aprovação. O texto é de fora: é dado."""
    if not shutil.which("gh"):
        return {"numero": issue, "estado": "sem_gh", "itens": []}
    dados = _issue_do_gh(raiz, issue)
    if dados is None:
        return {"numero": issue, "estado": "falhou", "itens": []}
    corte = instante(desde) or datetime.max.replace(tzinfo=timezone.utc)
    itens = [_comentario(c) for c in dados.get("comments") or []
             if (instante(c.get("createdAt")) or corte) > corte]
    return {"numero": issue, "estado": "consultado", "itens": itens}


def momento(raiz: Path, spec: str, arquivo: Path | None, desde: str | None) -> tuple[str | None, str]:
    quando, fonte = (desde, "--desde") if desde else momento_da_aprovacao(raiz, spec, arquivo)
    t = instante(quando)
    return (t.isoformat(timespec="seconds"), fonte) if t else (None, fonte)


def decisoes_acrescentadas(raiz: Path, quando: str, ponto: str | None, base: str | None) -> list[dict]:
    """Na branch, depois do instante (com o que não foi commitado); na base, o que a branch
    ainda não tem."""
    depois = linhas_acrescentadas(raiz, commit_no_momento(raiz, quando))
    na_base = _linhas_do_diff(raiz, ponto, base) if ponto else ()
    return (entradas((l for l in depois if eh_decisao(l[0])), "branch")
            + entradas((l for l in na_base if eh_decisao(l[0])), "base"))


def issue_de_origem(raiz: Path, numero: str | None, quando: str, github: bool) -> dict | None:
    if not numero:
        return None
    if github:
        return comentarios_da_issue(raiz, numero, quando)
    return {"numero": numero, "estado": "nao_consultado", "itens": []}


def decisoes(raiz: Path, base: str | None, spec: str | None, desde: str | None,
             github: bool = False) -> dict:
    if not spec or not ID_SPEC.match(spec):
        return {"erro": "diga qual SPEC: prova.py decisoes SPEC-NNN"}
    spec = spec.upper()
    arquivo = arquivo_da_spec(raiz, spec)
    quando, fonte = momento(raiz, spec, arquivo, desde)
    if quando is None:
        return {"erro": f"sem o momento da aprovação da {spec} (nem selo no ciclo, nem commit "
                        "da SPEC) — passe --desde AAAA-MM-DD"}
    base = base or base_padrao(raiz)
    ponto = ponto_de_partida(raiz, base) if base else None
    alvo = alvo_da_entrega(raiz, spec, arquivo, ponto or "HEAD")
    lista = [{"origem": e["origem"], "arquivo": e["arquivo"], "linha": e["linha"],
              "titulo": titulo_da_entrada(e), "vinculos": vinculos("\n".join(e["texto"]), alvo)}
             for e in decisoes_acrescentadas(raiz, quando, ponto, base)]
    return {"spec": spec, "desde": quando, "fonte": fonte, "base": base,
            "arquivos_da_entrega": len(alvo["arquivos"]), "requisitos": alvo["requisitos"],
            "decisoes": sorted(lista, key=lambda d: not d["vinculos"]),
            "issue": issue_de_origem(raiz, alvo["issue"], quando, github)}


# --- 3. conjunto selado fora da instrução (ADR-0043) ------------------------------

def normalizar(texto: str) -> str:
    return " ".join(re.findall(r"\w+", texto.casefold()))


def textos_do_caso(valor, chave: str = "") -> list[str]:
    """Toda string do caso, em qualquer profundidade — menos o `id`, que é rótulo."""
    if chave == "id":
        return []
    if isinstance(valor, str):
        return [valor]
    if isinstance(valor, dict):
        return [t for k, v in valor.items() for t in textos_do_caso(v, k)]
    if isinstance(valor, list):
        return [t for v in valor for t in textos_do_caso(v)]
    return []


def trechos_do_caso(caso) -> list[str]:
    vistos: list[str] = []
    for texto in textos_do_caso(caso):
        t = normalizar(texto)
        if len(t.split()) >= MIN_PALAVRAS_SELADO and t not in vistos:
            vistos.append(t)
    return vistos


def ler_casos(arq: Path) -> tuple[list[tuple[int, dict]], list[tuple[int, str]]]:
    casos, ilegiveis = [], []
    for i, linha in enumerate(arq.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not linha.strip():
            continue
        try:
            casos.append((i, json.loads(linha)))
        except ValueError as e:
            ilegiveis.append((i, str(e)[:120]))
    return casos, ilegiveis


def superficie(raiz: Path) -> dict[str, str]:
    """rel → texto normalizado de todo arquivo de texto que pode virar instrução."""
    textos: dict[str, str] = {}
    for pasta, subpastas, nomes in os.walk(raiz):
        # Poda antes de descer: `.git` e `node_modules` não são percorridos.
        subpastas[:] = sorted(d for d in subpastas if d not in DIRS_IGNORADOS_SELADO)
        for nome in sorted(nomes):
            p = Path(pasta) / nome
            rel = p.relative_to(raiz).as_posix()
            if not rel.startswith(PREFIXOS_IGNORADOS_SELADO) and p.is_file():
                texto = _texto_de(p)
                if texto is not None:
                    textos[rel] = texto
    return textos


def _texto_de(p: Path) -> str | None:
    """Texto normalizado, entre espaços; None para binário, grande ou ilegível."""
    try:
        if p.stat().st_size > LIMITE_BYTES_SELADO:
            return None
        bruto = p.read_bytes()
    except OSError:
        return None
    if b"\0" in bruto:
        return None
    return f" {normalizar(bruto.decode('utf-8', errors='replace'))} "


def selado(raiz: Path) -> dict:
    arquivos = sorted((raiz / "evals").rglob("selado.jsonl")) if (raiz / "evals").is_dir() else []
    r: dict = {"raiz": str(raiz), "selados": [], "vazamentos": [], "no_visivel": [],
               "ilegiveis": []}
    if not arquivos:
        return r
    textos = superficie(raiz)
    for arq in arquivos:
        rel = arq.relative_to(raiz).as_posix()
        casos, ilegiveis = ler_casos(arq)
        r["ilegiveis"] += [{"selado": rel, "linha": i, "erro": e} for i, e in ilegiveis]
        visivel = arq.with_name("gold.jsonl")
        texto_visivel = ""
        if visivel.is_file():
            # \0 separa os campos: um trecho não casa atravessando dois casos.
            texto_visivel = " " + " \0 ".join(
                normalizar(t) for _, caso in ler_casos(visivel)[0] for t in textos_do_caso(caso)
            ) + " "
        curtos = 0
        for i, caso in casos:
            trechos = trechos_do_caso(caso)
            if not trechos:
                curtos += 1
                continue
            cid = str(caso.get("id", "")) if isinstance(caso, dict) else ""
            for trecho in trechos:
                onde = [f for f, texto in textos.items() if f" {trecho} " in texto]
                if onde:
                    r["vazamentos"].append({"selado": rel, "linha": i, "id": cid,
                                            "trecho": trecho[:80], "onde": onde})
                if f" {trecho} " in texto_visivel:
                    r["no_visivel"].append({"selado": rel, "linha": i, "id": cid,
                                            "trecho": trecho[:80],
                                            "visivel": visivel.relative_to(raiz).as_posix()})
        r["selados"].append({"arquivo": rel, "casos": len(casos), "curtos": curtos})
    return r


# --- 4. colher casos do histórico (ADR-0044) --------------------------------------

SAIDA_COLHER = Path("evals/entregas/candidatos.jsonl")


def base_da_entrega(raiz: Path, pr: dict) -> tuple[str | None, str]:
    """(commit de antes da entrega, estratégia do merge). None se a entrega não está aqui.

    Merge com dois pais: a base é o primeiro. Um pai só é squash ou rebase — o rebase
    se reconhece pelo título da entrega igual ao do último commit do PR, e aí a base
    fica N commits atrás; no squash, um atrás.
    """
    m = pr.get("entrega")
    if not m or git(raiz, "cat-file", "-e", f"{m}^{{commit}}").returncode != 0:
        return None, "ausente"
    pais = git(raiz, "rev-list", "--parents", "-n", "1", m).stdout.split()[1:]
    if not pais:
        return None, "raiz"
    if len(pais) >= 2:
        return pais[0], "merge"
    n = len(pr.get("commits") or [])
    if n > 1:
        titulo = git(raiz, "log", "-1", "--format=%s", m).stdout.strip()
        ultimo = (pr["commits"][-1].get("mensagem") or "").splitlines()
        if ultimo and ultimo[0].strip() == titulo:
            r = git(raiz, "rev-parse", f"{m}~{n}")
            if r.returncode == 0:
                return r.stdout.strip(), "rebase"
    return pais[0], "squash"


def testes_da_entrega(raiz: Path, base: str, entrega: str) -> list[str]:
    """Teste criado ou alterado entre a base e a entrega — o gabarito do caso."""
    saida = []
    for linha in git(raiz, "diff", "--name-status", "--no-renames", base, entrega).stdout.splitlines():
        partes = linha.split("\t")
        if len(partes) == 2 and partes[0] in ("A", "M") and eh_teste(partes[1]):
            saida.append(partes[1])
    return saida


def pedido_de(raiz: Path, pr: dict, usar_gh: bool) -> tuple[str, str]:
    """(pedido, de onde veio). A issue que o PR fecha é o pedido; o corpo do PR, não —
    ele descreve a solução, e caso que já traz a solução no enunciado não mede nada."""
    if usar_gh and pr.get("issues") and shutil.which("gh"):
        partes = []
        for numero in pr["issues"][:3]:
            try:
                r = subprocess.run(["gh", "issue", "view", str(numero), "--json", "title,body"],
                                   cwd=raiz, capture_output=True, text=True, timeout=60)
                d = json.loads(r.stdout) if r.returncode == 0 else {}
            except (OSError, subprocess.SubprocessError, ValueError):
                d = {}
            if d.get("title"):
                partes.append(f"{d['title']}\n\n{(d.get('body') or '').strip()}".strip())
        if partes:
            return "\n\n---\n\n".join(partes), "issue"
    return (pr.get("titulo") or "").strip(), "titulo"


def _rodar_teste(cmd: str, cwd: Path, tempo_limite: int) -> str:
    try:
        p = subprocess.run(cmd, shell=True, cwd=str(cwd), capture_output=True, text=True,
                           timeout=tempo_limite)
    except subprocess.TimeoutExpired:
        return "nao_executado"
    saida = (p.stdout or "") + (p.stderr or "")
    if SEM_COLETA.search(saida) or p.returncode == 5:
        return "nao_executado"
    return "passou" if p.returncode == 0 else "falhou"


def validar_caso(raiz: Path, caso: dict, template: str | None, tempo_limite: int) -> str:
    """`valido` se cada teste falha na base (com o teste da entrega) e passa na entrega.

    É a prova negativa do `pre-patch` aplicada ao passado: o teste que passa na base
    não separa quem resolveu o pedido de quem não resolveu.
    """
    tmp = Path(tempfile.mkdtemp(prefix="kairos-forge-colher-"))
    vistos: dict[str, set] = {"base": set(), "entrega": set()}
    try:
        for lado in ("base", "entrega"):
            arvore = tmp / lado
            if git(raiz, "worktree", "add", "--detach", str(arvore), caso[lado],
                   timeout=120).returncode != 0:
                return "nao_executado"
            ligar_dependencias(raiz, arvore)
            for rel in caso["testes"]:
                if lado == "base":
                    conteudo = git(raiz, "show", f"{caso['entrega']}:{rel}").stdout
                    (arvore / rel).parent.mkdir(parents=True, exist_ok=True)
                    (arvore / rel).write_text(conteudo, encoding="utf-8")
                par = comando_para(raiz, rel, template)
                if par is None:
                    return "nao_executado"
                cmd, cwd = par
                vistos[lado].add(_rodar_teste(cmd, arvore / cwd, tempo_limite))
    finally:
        for lado in ("base", "entrega"):
            git(raiz, "worktree", "remove", "--force", str(tmp / lado), timeout=60)
        git(raiz, "worktree", "prune")
        shutil.rmtree(tmp, ignore_errors=True)
    if "nao_executado" in vistos["base"] | vistos["entrega"]:
        return "nao_executado"
    if "passou" in vistos["base"]:
        return "passa_na_base"
    if "falhou" in vistos["entrega"]:
        return "falha_na_entrega"
    return "valido"


def ids_conhecidos(pasta: Path) -> set[str]:
    """Ids já colhidos, no visível ou no selado — colher de novo não duplica."""
    vistos: set[str] = set()
    for nome in ("candidatos.jsonl", "gold.jsonl", "selado.jsonl"):
        arq = pasta / nome
        if arq.is_file():
            vistos |= {str(c.get("id")) for _, c in ler_casos(arq)[0] if isinstance(c, dict)}
    return vistos


def colher(raiz: Path, dias: int | None, saida: str | None, validar: bool,
           template: str | None, tempo_limite: int, fonte: str | None) -> dict:
    from telemetria import commit_de_agente, prs_mesclados

    origem, prs = prs_mesclados(raiz, dias, fonte)
    destino = raiz / (saida or SAIDA_COLHER)
    conhecidos = ids_conhecidos(destino.parent)
    novos, pulados = [], []
    for pr in prs:
        agentes = [commit_de_agente(c) for c in pr["commits"]]
        if not any(agentes):
            continue  # só o que a fábrica entregou é caso da fábrica
        cid = f"pr-{pr['numero']}" if pr.get("numero") else f"merge-{(pr.get('entrega') or '')[:10]}"
        if cid in conhecidos:
            pulados.append({"id": cid, "motivo": "já colhido"})
            continue
        base, estrategia = base_da_entrega(raiz, pr)
        if not base:
            pulados.append({"id": cid, "motivo": "entrega fora deste clone — rode `git fetch`"})
            continue
        testes = testes_da_entrega(raiz, base, pr["entrega"])
        if not testes:
            pulados.append({"id": cid, "motivo": "entrega sem teste criado ou alterado — sem gabarito"})
            continue
        pedido, fonte_pedido = pedido_de(raiz, pr, origem == "gh")
        caso = {"id": cid, "estado": "candidato", "pedido": pedido,
                "fonte_pedido": fonte_pedido, "revisar_pedido": fonte_pedido != "issue",
                "base": base, "entrega": pr["entrega"], "estrategia": estrategia,
                "testes": testes, "autonomo": all(agentes),
                "mesclado_em": pr.get("mesclado_em"), "colhido_em": date.today().isoformat(),
                "oraculo": "nao_validado"}
        if validar:
            caso["oraculo"] = validar_caso(raiz, caso, template, tempo_limite)
            if caso["oraculo"] != "valido":
                pulados.append({"id": cid, "motivo": f"oráculo {caso['oraculo']}"})
                continue
        novos.append(caso)
    if novos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("a", encoding="utf-8") as f:
            for caso in novos:
                f.write(json.dumps(caso, ensure_ascii=False) + "\n")
    try:
        rel = destino.relative_to(raiz).as_posix()
    except ValueError:
        rel = str(destino)
    return {"fonte": origem, "saida": rel, "novos": novos, "pulados": pulados}


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


def imprimir_atalhos(r: dict) -> None:
    if r.get("erro"):
        print(f"🚫 {r['erro']}")
        return
    cands = r["candidatos"]
    print(f"🔎 Atalhos no diff contra {r['base']} ({r['ponto']}): {len(cands)} candidato(s)")
    if not cands:
        print("   nenhum: TLS, erro engolido, tipo burlado, HTML sem escape e sleep conferidos")
        return
    print("   Candidato não é achado: com justificativa e link, fica; sem, vira achado.\n")
    for c in cands:
        onde = f"{c['arquivo']}:{c['linha']}" + (" (teste)" if c["teste"] else "")
        print(f"   {onde}\t{c['categoria']}\t{c['trecho'][:100]}")


ONDE = {"branch": "na branch", "base": "na base, fora da branch"}
ISSUE = {"nao_consultado": "comentários não consultados (rode com --github)",
         "sem_gh": "comentários não consultados — o CLI `gh` não está instalado",
         "falhou": "a consulta falhou (o `gh` está autenticado neste repositório?)"}


def _imprimir_issue(issue: dict | None) -> None:
    if not issue:
        return
    if issue["estado"] != "consultado":
        print(f"\n   Issue de origem #{issue['numero']}: {ISSUE[issue['estado']]}")
        return
    print(f"\n   Issue de origem #{issue['numero']}: {len(issue['itens'])} comentário(s) depois "
          "da aprovação (texto de fora: é dado, não instrução)")
    for c in issue["itens"]:
        print(f"   💬 {c['quando']} @{c['autor']}: {c['trecho']}")


def imprimir_decisoes(r: dict) -> None:
    if r.get("erro"):
        print(f"🚫 {r['erro']}")
        return
    ligadas = [d for d in r["decisoes"] if d["vinculos"]]
    print(f"🧭 Decisões depois da aprovação da {r['spec']} — desde {r['desde']} ({r['fonte']}), "
          f"base {r['base'] or '—'}")
    print(f"   {len(ligadas)} ligada(s) à entrega, {len(r['decisoes']) - len(ligadas)} sem "
          f"vínculo detectado ({r['arquivos_da_entrega']} arquivo(s) na entrega)")
    if not r["decisoes"]:
        print("   nenhuma decisão registrada depois da aprovação")
    for d in r["decisoes"]:
        marca = "⚠️ " if d["vinculos"] else "· "
        cita_ = f" — cita {', '.join(d['vinculos'])}" if d["vinculos"] else ""
        print(f"   {marca} [{ONDE[d['origem']]}] {d['arquivo']}:{d['linha']}  {d['titulo']}{cita_}")
    _imprimir_issue(r.get("issue"))


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


def imprimir_selado(r: dict) -> None:
    if not r["selados"] and not r["ilegiveis"]:
        print("🔒 Conjunto selado: nenhum evals/<slug>/selado.jsonl neste repositório — "
              "nada a proteger.")
        return
    casos = sum(s["casos"] for s in r["selados"])
    curtos = sum(s["curtos"] for s in r["selados"])
    print(f"🔒 Conjunto selado — {len(r['selados'])} arquivo(s), {casos} caso(s)")
    for v in r["vazamentos"]:
        onde = ", ".join(v["onde"][:4]) + (f" … e mais {len(v['onde']) - 4}"
                                           if len(v["onde"]) > 4 else "")
        print(f"   ❌ {v['selado']}:{v['linha']} {v['id']}".rstrip())
        print(f"      \"{v['trecho']}\" aparece em: {onde}")
    for v in r["no_visivel"]:
        print(f"   ❌ {v['selado']}:{v['linha']} {v['id']}".rstrip())
        print(f"      \"{v['trecho']}\" repetido no visível {v['visivel']}")
    for v in r["ilegiveis"]:
        print(f"   ⚠️  {v['selado']}:{v['linha']} ilegível — {v['erro']}")
    if curtos:
        print(f"   · {curtos} caso(s) sem trecho de {MIN_PALAVRAS_SELADO}+ palavras — "
              "não comparados, não 'limpos'.")
    if r["vazamentos"] or r["no_visivel"]:
        print("\n   Caso selado que o sistema avaliado consegue ler mede leitura, não "
              "comportamento.\n   Ache por onde ele chegou lá, tire de lá e rotacione o "
              "caso: o resultado selado anterior\n   não vale como aprovação.")
    elif r["ilegiveis"]:
        print("\n   Linha ilegível não dá para comparar — conserte o JSON antes de confiar "
              "no selado.")
    else:
        print("\n   Nenhum caso selado copiado para instrução nem repetido no visível.")


def imprimir_colher(r: dict) -> None:
    print(f"🌾 Casos colhidos do histórico — fonte {r['fonte']}, saída {r['saida']}")
    if r["fonte"] == "git":
        print("   Fonte git: só merges com commit de merge, e o pedido é o título do merge.\n"
              "   Com o `gh` autenticado, o pedido vem da issue que o PR fecha.")
    for c in r["novos"]:
        marca = "  (reescreva o pedido)" if c["revisar_pedido"] else ""
        print(f"   + {c['id']:<14} {len(c['testes'])} teste(s) · oráculo {c['oraculo']}{marca}")
    for c in r["pulados"]:
        print(f"   · {c['id']:<14} {c['motivo']}")
    if not r["novos"]:
        print("   Nenhum caso novo.")
        return
    print(f"\n   {len(r['novos'])} candidato(s). Antes de selar: o pedido não pode trazer a solução,\n"
          "   e a divisão visível × selado é da Alice (`/kairos-forge:avaliar`).")


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] not in ("pre-patch", "testes-alterados", "atalhos", "decisoes",
                                   "selado", "colher"):
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

    if comando == "colher":
        raiz = raiz_git()
        if raiz is None:
            print("🚫 fora de um repositório git — sem histórico não há o que colher",
                  file=sys.stderr)
            return 1
        try:
            dias = int(opcao("--dias")) if opcao("--dias") else None
        except ValueError:
            print("erro: --dias precisa de um número", file=sys.stderr)
            return 1
        fonte = opcao("--fonte")
        if fonte not in (None, "gh", "git"):
            print("erro: --fonte é gh ou git", file=sys.stderr)
            return 1
        r = colher(raiz, dias, opcao("--saida"), "--validar" in args, template, tempo, fonte)
        if como_json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            imprimir_colher(r)
        return 0

    if comando == "selado":
        alvo = opcao("--raiz")
        raiz = Path(alvo).resolve() if alvo else (raiz_git() or Path.cwd())
        r = selado(raiz)
        if como_json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            imprimir_selado(r)
        return 1 if (r["vazamentos"] or r["no_visivel"] or r["ilegiveis"]) else 0

    raiz = raiz_git()
    if raiz is None:
        print("🚫 fora de um repositório git — sem diff não há prova", file=sys.stderr)
        return 1
    calcular, imprimir, reprova = SOBRE_O_DIFF[comando]
    r = calcular(raiz, base, template, tempo, args)
    if como_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        imprimir(r)
    return 1 if r.get("erro") or reprova(r) else 0


# Os comandos que medem o diff contra a base: (calcular, imprimir, sai 1 quando).
SOBRE_O_DIFF = {
    "pre-patch": (lambda raiz, base, template, tempo, _: pre_patch(raiz, base, template, tempo),
                  lambda r: imprimir_pre_patch(r),
                  lambda r: any(t["veredicto"] == "passou_na_base" for t in r["testes"])),
    "testes-alterados": (lambda raiz, base, *_: testes_alterados(raiz, base),
                         lambda r: imprimir_testes_alterados(r),
                         lambda r: bool(r.get("com_sinal"))),
    "atalhos": (lambda raiz, base, *_: atalhos(raiz, base),
                lambda r: imprimir_atalhos(r),
                lambda r: False),   # candidato não é achado: quem julga é o revisor
    "decisoes": (lambda raiz, base, _t, _s, args: decisoes(
                     raiz, base, next((a for a in args[1:] if ID_SPEC.match(a)), None),
                     _valor(args, "--desde"), "--github" in args),
                 lambda r: imprimir_decisoes(r),
                 lambda r: False),  # ligar não é julgar: quem diz se a entrega segue é o /validar
}


def _valor(args: list[str], nome: str) -> str | None:
    i = args.index(nome) if nome in args else -1
    return args[i + 1] if 0 <= i < len(args) - 1 else None


if __name__ == "__main__":
    sys.exit(main())
