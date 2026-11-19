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

E a correção passa a ter causa (ADR-0060): o `reproduzir` roda o laço que mostra o problema
na base do diff, com os testes do diff copiados, e na árvore de trabalho; só vale
`reproduz_e_corrige`, a falha na base com o sintoma e a passagem agora. Com `--antes`, roda
só aqui, para conferir que o laço mostra o problema antes do conserto. O `investigacao` lê
a ficha em `docs/investigacoes/` (sintoma, laço, hipóteses, causa, prova e trava), roda a
reprodução dela e sai 2 com três hipóteses descartadas e nenhuma confirmada: pare e
pergunte. O `marcas` acha a linha nova com a marca de depuração (`forge-depura-<id>`).

E a fonte fica salva (ADR-0060): o `fontes` confere cada `docs/pesquisa/*.md` (data, resposta,
cada fato com fonte, versão e data, nenhum segredo) e toda citação a `docs/pesquisa/` que
aponta para arquivo que não existe; com o id de uma SPEC, lista as pesquisas que ela cita e
as que mudaram depois da aprovação. Sem rede: confere a forma, não a verdade da fonte.

E a revisão separa o que é do PR do que já existia (ADR-0059): o `origem` lê o relatório
do `/revisar` e confere cada `arquivo:linha` citado contra o diff. O achado que bloqueia
(🔴, 🟠) em linha que o diff não tocou precisa dizer como o PR o afeta (`· o PR depende:` ou
`· o PR piora:`); sem isso, é problema antigo e vai para `## Fora deste PR`, que não bloqueia.
E a observação de `## Fora deste PR` numa linha que o PR escreveu é do PR. Sai 1 quando um
dos dois aparece: a revisão não bloqueia o PR pelo que ele não fez, nem esconde o que ele fez.

## Uso

    prova.py pre-patch        [--base REF] [--comando "TEMPLATE"] [--tempo-limite S] [--json]
    prova.py testes-alterados [--base REF] [--json]
    prova.py atalhos          [--base REF] [--json]
    prova.py decisoes SPEC-NNN [--base REF] [--desde DATA] [--github] [--json]
    prova.py origem   REVISAO.md [--base REF] [--json]
    prova.py reproduzir --comando "LAÇO" [--sintoma REGEX] [--antes] [--base REF]
                              [--tempo-limite S] [--json]
    prova.py marcas           [--base REF] [--json]
    prova.py investigacao docs/investigacoes/INV-<slug>.md [--base REF] [--json]
    prova.py fontes   [SPEC-NNN] [--raiz DIR] [--idade-max DIAS] [--json]
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
    erro_na_base     ⚠️  o teste nem carrega na base, por algo que o diff não acrescenta
    nao_executado    ⚠️  sem comando conhecido, sem coleta, ou estourou o tempo

Exit 1 se houver `passou_na_base`; 0 caso contrário. `testes-alterados` sai 1 se houver
sinal de afrouxamento — usável em CI e pre-commit, mas o veredicto é de quem valida.

## Como o pre-patch roda

Cria um worktree descartável na base do diff, copia para dentro o lado de teste do diff
(os testes e os `conftest.py` novos ou mudados, antes de rodar qualquer um; no Go, que
compila o pacote junto, cada `_test.go` novo entra na sua vez) e roda o gate de cada teste
novo lá — o worktree é removido ao final. `node_modules`, `.venv`, `venv` e
`vendor` da raiz são ligados por symlink no worktree quando existem, para que "faltou
dependência" não se disfarce de "falhou na base".

O teste que nem carrega na base (import, sintaxe, coleta do pytest, suíte do jest ou do
vitest, `[setup failed]` do Go) só é `falhou_na_base` quando o que falta é o que o diff
acrescenta em código de produção: o módulo novo, o nome novo num módulo que já existia, o
pacote Go novo. O teste de um símbolo novo não carrega na base porque o símbolo ainda não
existia — é prova. A dependência que não está instalada, o erro de sintaxe no teste, o
auxiliar de fora do diff e a fixture de um plugin ausente saem `erro_na_base`. A falha comum
(asserção, exceção, tipo errado do Go, e a asserção que só cita `SyntaxError` ou `No module
named`, ou o `JSON.parse` do que a base devolve) continua `falhou_na_base` — o script lê exit
code, não intenção: o serviço externo fora do ar é um limite declarado.

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
from collections.abc import Callable
from contextlib import contextmanager
from datetime import date, datetime, timezone
from functools import cache
from pathlib import Path
from typing import NamedTuple

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
    # Caminho com acento sem aspas nem escape, e saída que não é UTF-8 sem derrubar a leitura.
    return subprocess.run(["git", "-c", "core.quotePath=false", "-C", str(raiz), *args],
                          capture_output=True, encoding="utf-8", errors="replace",
                          timeout=timeout)


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


def eh_suporte_de_teste(rel: str) -> bool:
    """Teste, ou o que o pytest carrega para ele (`conftest.py`): o lado de teste do diff."""
    return eh_teste(rel) or Path(rel).name == "conftest.py"


def suporte_do_diff(raiz: Path, ponto: str) -> list[str]:
    """Teste e suporte de teste novos ou mudados no diff. Vão todos para a base antes de rodar
    qualquer teste: o auxiliar ou o `conftest.py` que ficasse para trás faria o teste não
    carregar lá, e isso pareceria falha na base. Menos o `_test.go`: o Go compila o pacote
    inteiro, e o teste novo herdaria a falha de compilação de outro teste do mesmo pacote;
    o novo entra na base na sua vez, e o mudado não entra."""
    nomes = [c for s, c in _diff_sem_renomear(raiz, ponto)
             if s in ("A", "M") and eh_suporte_de_teste(c)]
    nomes += [c for c in nao_rastreados(raiz) if eh_suporte_de_teste(c)]
    return sorted(c for c in dict.fromkeys(nomes) if not c.endswith("_test.go"))


# --- o que não carregou na base ----------------------------------------------------
# O teste que nem carrega na base (import, sintaxe, coleta) sai diferente de 0 como o que
# falha na asserção, e só às vezes é prova. O teste de um símbolo novo não carrega porque o
# símbolo ainda não existe: é prova, o comportamento não existia. A dependência que não está
# instalada, o teste com erro de sintaxe e o auxiliar de fora do diff também não carregam, e
# nada disso vem do diff. A regra é o que o diff acrescenta em código de produção: a falta que
# ele explica é prova; a que ele não explica sai `erro_na_base`.

# (tipo, língua, regex); a primeira que casa na linha vale. `alvo` é o que falta, `de` é onde.
# No Python, a linha é a da exceção (`ModuleNotFoundError: No module named`, `SyntaxError:` no
# começo da linha): a asserção que só cita esse texto (`assertRaises(SyntaxError)`, a mensagem
# que menciona o módulo) é falha comum, e o teste carregou.
FALTAS = (
    ("nome", "js", re.compile(r"The requested module '(?P<de>[^']+)' does not provide an export "
                              r"named '(?P<alvo>[\w$]+)'")),
    ("modulo", "py", re.compile(r"(?:ModuleNotFoundError|ImportError): No module named "
                                r"'(?P<alvo>[\w.]+)'")),
    ("nome", "py", re.compile(r"ImportError: cannot import name '(?P<alvo>\w+)'(?: from (?:partially "
                              r"initialized module )?'(?P<de>[\w.]+)')?")),
    ("nome", "py", re.compile(r"AttributeError: (?:partially initialized )?module '(?P<de>[\w.]+)' "
                              r"has no attribute '(?P<alvo>\w+)'")),
    ("fixture", "py", re.compile(r"fixture '(?P<alvo>\w+)' not found")),
    ("modulo", "js", re.compile(r"Cannot find (?:module|package) '(?P<alvo>[^']+)'")),
    ("modulo", "js", re.compile(r'Failed to resolve import "(?P<alvo>[^"]+)"')),
    ("modulo", "js", re.compile(r"Failed to load url (?P<alvo>\S+) \(resolved id")),
    ("modulo", "go", re.compile(r"no required module provides package (?P<alvo>[^\s;]+)")),
    ("modulo", "go", re.compile(r"cannot find module providing package (?P<alvo>[^\s:;]+)")),
    ("modulo", "go", re.compile(r'cannot find package "(?P<alvo>[^"]+)"')),
    ("modulo", "go", re.compile(r"package (?P<alvo>\S+) is not in (?:std|GOROOT)")),
    ("nome", "go", re.compile(r"\.go:\d+:\d+: undefined: (?:\w+\.)?(?P<alvo>\w+)")),
    ("nome", "go", re.compile(r"has no field or method (?P<alvo>\w+)")),
    ("sintaxe", "py", re.compile(r"^\s*(?:E\s+)?(?:SyntaxError|IndentationError|TabError):")),
)
ARQUIVO_PY = re.compile(r'File "(?P<arquivo>[^"]+)", line \d+')
# O arquivo de teste não carregou, sem causa que as linhas acima reconheçam: pytest, unittest,
# jest, vitest e `go test` (o `[build failed]` fica de fora: tipo errado é falha comum, como o
# TypeError do Python).
CARGA = re.compile(r"ERROR collecting|errors? during collection|Failed to import test module"
                   r"|ImportError while loading conftest|Test suite failed to run|Failed Suites"
                   r"|\[setup failed\]")
EXT_LINGUA = {"py": {".py"}, "go": {".go"},
              "js": {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts"}}


def _relativo(caminho: str, worktree: Path | None) -> str:
    """O caminho dentro do worktree da base, como o diff o chama; os outros ficam como vieram."""
    for raiz in ({worktree, worktree.resolve()} if worktree else ()):
        try:
            return Path(caminho).relative_to(raiz).as_posix()
        except ValueError:
            continue
    return caminho


def _arquivo_do_projeto(caminho: str | None) -> bool:
    """O arquivo que o worktree tem; `<unknown>` e o caminho absoluto que sobrou são código
    montado em tempo de teste (`ast.parse`, `JSON.parse`): falha comum."""
    return bool(caminho) and not caminho.startswith("<") and not Path(caminho).is_absolute()


def _falta_na_linha(linha: str, ultimo_arquivo: str | None) -> dict | None:
    """A falta da primeira linha de `FALTAS` que casa; None sem nenhuma, ou quando o erro de
    sintaxe não é de um arquivo do projeto."""
    for tipo, lingua, rx in FALTAS:
        m = rx.search(linha)
        if not m:
            continue
        campos = m.groupdict()
        alvo = ultimo_arquivo if tipo == "sintaxe" else campos.get("alvo")
        if tipo == "sintaxe" and not _arquivo_do_projeto(alvo):
            return None
        return {"tipo": tipo, "lingua": lingua, "alvo": alvo, "de": campos.get("de")}
    return None


def faltas_na_carga(saida: str, worktree: Path | None) -> list[dict]:
    """O que a base não conseguiu carregar, lido da saída do runner, uma vez cada."""
    faltas, ultimo_arquivo = {}, None
    for linha in saida.splitlines():
        arquivo = ARQUIVO_PY.search(linha)
        if arquivo:
            ultimo_arquivo = _relativo(arquivo.group("arquivo"), worktree)
        falta = _falta_na_linha(linha, ultimo_arquivo)
        if falta:
            faltas.setdefault(tuple(falta.values()), falta)
    if not faltas and CARGA.search(saida):
        return [{"tipo": "carga", "lingua": None, "alvo": None, "de": None}]
    return list(faltas.values())


def _sem_extensao(rel: str) -> str:
    suf = Path(rel).suffix
    return rel[: -len(suf)] if suf in EXT_LINGUA["js"] | EXT_LINGUA["py"] | {".json"} else rel


def _termina_em(caminho: str, fim: str) -> bool:
    return caminho == fim or caminho.endswith("/" + fim)


def _modulo_py(rel: str, nome: str) -> bool:
    """`rel` é o módulo `nome` (`a/b.py`, `src/a/b.py`) ou está dentro do pacote dele."""
    p = nome.replace(".", "/")
    return rel.endswith(".py") and (_termina_em(_sem_extensao(rel), p) or f"/{p}/" in f"/{rel}")


def _modulo_js(rel: str, spec: str, worktree: Path | None) -> bool:
    """`spec` (relativo, absoluto no worktree ou com alias `@/`) aponta para `rel`."""
    p = re.sub(r"^(?:\.{1,2}/)+|^[@~#]/", "", _relativo(spec, worktree))
    if not p or p.startswith("/"):
        return False
    nomes = {rel, _sem_extensao(rel)}
    if Path(_sem_extensao(rel)).name == "index":
        nomes.add(Path(rel).parent.as_posix())
    return any(_termina_em(n, alvo) for n in nomes for alvo in {p, _sem_extensao(p)})


def _pacote_go(raiz: Path, rel: str) -> str | None:
    """O import path do pacote de `rel`, pelo `go.mod` mais próximo."""
    pasta = Path(rel).parent
    for acima in (pasta, *pasta.parents):
        try:
            texto = (raiz / acima / "go.mod").read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.search(r"^module\s+(\S+)", texto, re.M)
        if not m:
            return None
        resto = pasta.relative_to(acima).as_posix()
        return m.group(1) if resto == "." else f"{m.group(1)}/{resto}"
    return None


def _modulo_acrescentado(alvo: str, lingua: str, da_lingua: list[str], raiz: Path,
                         worktree: Path | None) -> bool:
    if lingua == "py":
        return any(_modulo_py(f, alvo) for f in da_lingua)
    if lingua == "js":
        return any(_modulo_js(f, alvo, worktree) for f in da_lingua)
    return any(_pacote_go(raiz, f) == alvo for f in da_lingua)


def _fixture_definida(alvo: str, da_lingua: list[str], acrescentado: dict[str, list[str]]) -> bool:
    # A fixture é suporte de teste: a palavra citada em produção não a explica (a do plugin
    # que não está instalado, como `settings`, é palavra comum); só a que o diff define lá.
    define = re.compile(rf"^\s*(?:async\s+)?def\s+{re.escape(alvo)}\s*\("
                        rf"|\bname\s*=\s*['\"]{re.escape(alvo)}['\"]")
    return any(define.search(linha) for f in da_lingua for linha in acrescentado[f])


def _nome_acrescentado(alvo: str, lingua: str, de: str | None, da_lingua: list[str],
                       acrescentado: dict[str, list[str]]) -> bool:
    if lingua == "py" and de:
        if any(_modulo_py(f, f"{de}.{alvo}") for f in da_lingua):
            return True                       # `from app import novo`, o submódulo novo
        da_lingua = [f for f in da_lingua if _modulo_py(f, de)]
    palavra = re.compile(rf"(?<![\w$]){re.escape(alvo)}(?![\w$])")
    return any(palavra.search(linha) for f in da_lingua for linha in acrescentado[f])


def explicada(falta: dict, acrescentado: dict[str, list[str]], raiz: Path,
              worktree: Path | None) -> bool:
    """A falta é o que o diff acrescenta em código de produção (não em teste nem no suporte)."""
    tipo, lingua, alvo, de = falta["tipo"], falta["lingua"], falta["alvo"], falta["de"]
    if not alvo:
        return False
    codigo = [f for f in acrescentado if not eh_suporte_de_teste(f)]
    if tipo == "sintaxe":
        return alvo in codigo
    da_lingua = [f for f in codigo if Path(f).suffix in EXT_LINGUA[lingua]]
    if tipo == "modulo":
        return _modulo_acrescentado(alvo, lingua, da_lingua, raiz, worktree)
    if tipo == "fixture":
        return _fixture_definida(alvo, da_lingua, acrescentado)
    return _nome_acrescentado(alvo, lingua, de, da_lingua, acrescentado)


def _o_que_falta(falta: dict) -> str:
    tipo, alvo, de = falta["tipo"], falta["alvo"], falta["de"]
    if tipo == "modulo":
        return f"falta o módulo `{alvo}`"
    if tipo == "nome":
        return f"falta o nome `{alvo}`" + (f" em `{de}`" if de else "")
    if tipo == "fixture":
        return f"falta a fixture `{alvo}`"
    if tipo == "sintaxe":
        return f"erro de sintaxe em `{alvo}`" if alvo else "erro de sintaxe"
    return "o arquivo de teste não carregou"


def veredicto_da_falha(saida: str, codigo: int, acrescentado, raiz: Path,
                       worktree: Path | None) -> tuple[str, str]:
    """(veredicto, motivo) do teste que saiu diferente de 0 na base. `acrescentado` é chamada só
    quando há o que explicar e devolve {arquivo do diff: linhas que ele acrescenta}."""
    faltas = faltas_na_carga(saida, worktree)
    if not faltas:
        return "falhou_na_base", f"exit {codigo} na base"
    arquivos = acrescentado()
    soltas = [f for f in faltas if not explicada(f, arquivos, raiz, worktree)]
    if soltas:
        pronome = "a" if soltas[0]["tipo"] == "fixture" else "o"
        return "erro_na_base", (f"não carregou na base: {_o_que_falta(soltas[0])}, e o diff não "
                                f"{pronome} acrescenta — não prova a mudança")
    return "falhou_na_base", (f"exit {codigo} na base: "
                              + "; ".join(_o_que_falta(f) for f in faltas) + ", que o diff acrescenta")


# O pytest que não carrega um `conftest.py` não roda nenhum teste da árvore dele. O conftest
# do diff que importa código novo não carrega na base, e todo teste novo dali falharia lá, até
# o que não usa nada do diff: prova falsa. Nesse caso o teste roda de novo com os conftests da
# base. Se passar, não prova a mudança; se faltar uma fixture que o conftest do diff define, o
# teste depende dela e, por ela, do código novo.
CONFTEST_QUEBRADO = re.compile(r"Error while loading conftest\b")
FIXTURE_AUSENTE = re.compile(r"fixture '(\w+)' not found")


def _rodar_na_base(cmd: str, cwd: str, worktree: Path, tempo_limite: int) -> tuple[int, str] | None:
    """(código de saída, saída) do gate no worktree da base; None se estourou o tempo."""
    try:
        p = subprocess.run(cmd, shell=True, cwd=str(worktree / cwd), capture_output=True,
                           text=True, timeout=tempo_limite)
    except subprocess.TimeoutExpired:
        return None
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _conftests_da_base(worktree: Path, ponto: str, conftests: list[str]) -> None:
    """O `conftest.py` mudado volta à versão da base, e o novo sai."""
    for rel in conftests:
        if git(worktree, "cat-file", "-e", f"{ponto}:{rel}").returncode == 0:
            git(worktree, "checkout", ponto, "--", rel)
        else:
            (worktree / rel).unlink(missing_ok=True)


def sem_o_conftest_do_diff(raiz: Path, worktree: Path, ponto: str, conftests: list[str],
                           par: tuple[str, str], tempo_limite: int,
                           acrescentado) -> tuple[str, str] | None:
    """O veredicto do teste rodado de novo sem os conftests do diff; None quando a nova rodada
    não diz nada (estourou, nada coletado) e vale o veredicto da primeira."""
    _conftests_da_base(worktree, ponto, conftests)
    try:
        rodada = _rodar_na_base(*par, worktree, tempo_limite)
    finally:
        _copiar(raiz, worktree, conftests)   # o próximo teste roda com o diff inteiro
    if rodada is None or rodada[0] == 5 or SEM_COLETA.search(rodada[1]):
        return None
    codigo, saida = rodada
    if codigo == 0:
        return "passou_na_base", ("passa sem a mudança quando o conftest.py do diff sai da base "
                                  "— não prova a mudança")
    definidas = "\n".join((raiz / c).read_text(encoding="utf-8", errors="replace")
                          for c in conftests if (raiz / c).is_file())
    for nome in FIXTURE_AUSENTE.findall(saida):
        if re.search(rf"^\s*def {re.escape(nome)}\(", definidas, re.M):
            return "falhou_na_base", (f"usa a fixture `{nome}` do conftest.py do diff, que não "
                                      f"carrega sem a mudança")
    return veredicto_da_falha(saida, codigo, acrescentado, raiz, worktree)


def acrescentado_no_diff(raiz: Path, ponto: str) -> dict[str, list[str]]:
    """Arquivo que o diff acrescenta ou muda → as linhas que ele acrescenta."""
    arquivos = {c: [] for s, c in diff_nomes(raiz, ponto) if s != "D"}
    arquivos.update({c: [] for c in nao_rastreados(raiz)})
    for rel, _, linha in linhas_acrescentadas(raiz, ponto):
        if rel in arquivos:
            arquivos[rel].append(linha)
    return arquivos


class WorktreeDaBase(NamedTuple):
    """O worktree da base com o lado de teste do diff, onde cada teste novo é julgado."""
    raiz: Path
    worktree: Path
    ponto: str
    tempo_limite: int
    conftests: list[str]
    acrescentado: Callable[[], dict[str, list[str]]]   # lido do diff só quando há falta


def _de_novo_sem_o_conftest(wt: WorktreeDaBase, par: tuple[str, str], saida: str,
                            julgado: tuple[str, str]) -> tuple[str, str] | None:
    """O veredicto da segunda rodada, quando a prova da primeira pode ser só o conftest do diff
    que não carrega na base; None quando a primeira vale."""
    if julgado[0] != "falhou_na_base" or not wt.conftests or not CONFTEST_QUEBRADO.search(saida):
        return None
    return sem_o_conftest_do_diff(wt.raiz, wt.worktree, wt.ponto, wt.conftests, par,
                                  wt.tempo_limite, wt.acrescentado)


def veredicto_da_rodada(wt: WorktreeDaBase, par: tuple[str, str], codigo: int,
                        saida: str) -> dict:
    """Os campos do item que a saída do teste na base decide."""
    if SEM_COLETA.search(saida) or codigo == 5:  # 5 = pytest sem coleta
        return {"motivo": "nenhum teste coletado no worktree da base"}
    if codigo == 0:
        return {"veredicto": "passou_na_base", "motivo": "passa sem a mudança — não prova a mudança"}
    ultimas = [l for l in saida.strip().splitlines() if l.strip()][-3:]
    if codigo in (126, 127):   # o executor nem rodou: comando inexistente ou sem permissão
        return {"motivo": (f"exit {codigo} na base: o comando do teste nem rodou — "
                           "confira o ambiente ou passe --comando"),
                "ultimas_linhas": ultimas}
    julgado = veredicto_da_falha(saida, codigo, wt.acrescentado, wt.raiz, wt.worktree)
    veredicto, motivo = _de_novo_sem_o_conftest(wt, par, saida, julgado) or julgado
    return {"veredicto": veredicto, "motivo": motivo, "ultimas_linhas": ultimas}


def julgar_teste(wt: WorktreeDaBase, rel: str, copiado: bool, template: str | None) -> dict:
    """Um teste novo rodado na base: o comando, a saída lida e o veredicto."""
    item = {"arquivo": rel, "veredicto": "nao_executado", "motivo": "", "comando": ""}
    if not copiado:
        item["motivo"] = "não copiei o teste para o worktree"
        return item
    par = comando_para(wt.raiz, rel, template)
    if par is None:
        item["motivo"] = "ecossistema sem comando conhecido — passe --comando"
        return item
    item["comando"] = par[0]
    rodada = _rodar_na_base(*par, wt.worktree, wt.tempo_limite)
    if rodada is None:
        item["motivo"] = f"estourou {wt.tempo_limite}s"
        return item
    item.update(veredicto_da_rodada(wt, par, *rodada))
    return item


def julgar_na_base(raiz: Path, worktree: Path, ponto: str, novos: list[str],
                   template: str | None, tempo_limite: int) -> list[dict]:
    """Cada teste novo julgado no worktree da base, com o suporte de teste do diff já lá."""
    copiados = set(_copiar(raiz, worktree, suporte_do_diff(raiz, ponto)))
    wt = WorktreeDaBase(raiz, worktree, ponto, tempo_limite,
                        conftests=sorted(c for c in copiados if Path(c).name == "conftest.py"),
                        acrescentado=cache(lambda: acrescentado_no_diff(raiz, ponto)))
    testes = []
    for rel in novos:
        if rel not in copiados:   # o `_test.go` novo, na sua vez
            copiados.update(_copiar(raiz, worktree, [rel]))
        testes.append(julgar_teste(wt, rel, rel in copiados, template))
    return testes


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
        resultado["testes"] = julgar_na_base(raiz, worktree, ponto, novos, template, tempo_limite)
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
TRECHO_COMPLETO = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
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
    for linha in git(raiz, "diff", "-U0", "--no-color", "--src-prefix=a/", "--dst-prefix=b/",
                     *refs).stdout.splitlines():
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


# --- o que é do PR e o que já existia (ADR-0059) ----------------------------------
# A ideia vem da corno-revisa (corno-skills, sem licença declarada: a ideia, não o texto):
# o problema que o PR introduziu ou piorou pede ajuste; o que já existia fica anotado para
# outra tarefa, sem bloquear. A conferência é pela linha citada contra o diff, sem modelo.

SECAO_MD = re.compile(r"^##\s+(.+?)\s*$")
LOCAL_CITADO = re.compile(r"([\w./@+-]+\.[A-Za-z0-9]+):(\d+)(?:[-–](\d+))?")
JUSTIFICADO = re.compile(r"·\s*o PR (depende|piora)\b", re.I)
DESCARTADO = re.compile(r"·\s*descartado:", re.I)
FOLGA = 3   # o achado que bloqueia pode citar a linha ao lado da que o diff mexeu


def _secao_da_revisao(titulo: str) -> str | None:
    """`bloqueia` para 🔴 e 🟠, `fora` para "Fora deste PR"; o resto não é conferido."""
    if "fora deste pr" in titulo.casefold():
        return "fora"
    return "bloqueia" if titulo.startswith(("🔴", "🟠")) else None


def achados_da_revisao(texto: str) -> list[dict]:
    """Cada achado das seções que importam, com o local citado. Bloco de código e achado
    descartado (ADR-0039) ficam de fora."""
    achados, secao, em_bloco = [], None, False
    for linha in texto.splitlines():
        if linha.lstrip().startswith("```"):
            em_bloco = not em_bloco
            continue
        titulo = None if em_bloco else SECAO_MD.match(linha)
        if titulo:
            secao = _secao_da_revisao(titulo.group(1))
        elif secao and not em_bloco and linha.lstrip().startswith("- ") and not DESCARTADO.search(linha):
            achados.append(_achado(secao, linha))
    return achados


def _achado(secao: str, linha: str) -> dict:
    local = LOCAL_CITADO.search(linha)
    inicio = int(local.group(2)) if local else None
    return {"secao": secao, "texto": linha.strip()[2:].strip()[:200],
            "arquivo": local.group(1) if local else None, "inicio": inicio,
            "fim": int(local.group(3) or inicio) if local else None,
            "justificado": bool(JUSTIFICADO.search(linha))}


def trechos_do_diff(raiz: Path, ponto: str) -> dict[str, list[tuple[int, int]]]:
    """arquivo → [(primeira, última)] das linhas que o diff escreveu, na versão nova. Linha
    apagada conta como o ponto onde estava; arquivo novo e não rastreado, inteiro."""
    trechos: dict[str, list[tuple[int, int]]] = {}
    arquivo, anterior = None, ""
    for linha in git(raiz, "diff", "-U0", "--no-color", "--src-prefix=a/", "--dst-prefix=b/",
                     ponto).stdout.splitlines():
        if linha.startswith("+++ ") and anterior.startswith("--- "):
            m = CABECALHO.match(linha)
            arquivo = m.group(1) if m else None
        m = TRECHO_COMPLETO.match(linha)
        if m and arquivo:
            inicio, qtd = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
            trechos.setdefault(arquivo, []).append((inicio, inicio + max(qtd, 1) - 1))
        anterior = linha
    for rel in nao_rastreados(raiz):
        trechos.setdefault(rel, []).append((1, 10 ** 9))
    return trechos


def _no_diff(achado: dict, trechos: dict, folga: int) -> bool:
    return any(a - folga <= achado["fim"] and achado["inicio"] <= b + folga
               for a, b in trechos.get(achado["arquivo"], []))


def _ler_md(caminho: str | None, faltou: str, nome: str) -> tuple[str | None, str | None]:
    """(texto, erro)."""
    if not caminho:
        return None, faltou
    try:
        return Path(caminho).read_text(encoding="utf-8"), None
    except (OSError, UnicodeDecodeError):
        return None, f"não li {nome} {caminho}"


def classificar_origem(achados: list[dict], trechos: dict) -> dict:
    """O que bloqueia precisa ser do PR, ou dizer como o PR o afeta; o que é de fora não pode
    estar numa linha que o PR escreveu (aí a comparação é exata, sem folga)."""
    com_local = [a for a in achados if a["arquivo"]]
    return {"conferidos": len(com_local), "sem_local": [a for a in achados if not a["arquivo"]],
            "fora_sem_dizer": [a for a in com_local if a["secao"] == "bloqueia"
                               and not a["justificado"] and not _no_diff(a, trechos, FOLGA)],
            "do_pr_como_observacao": [a for a in com_local if a["secao"] == "fora"
                                      and _no_diff(a, trechos, 0)]}


def origem(raiz: Path, base: str | None, relatorio: str | None) -> dict:
    texto, erro = _ler_md(relatorio, "diga qual relatório conferir: prova.py origem REVISAO.md",
                          "o relatório")
    if erro:
        return {"erro": erro}
    base = base or base_padrao(raiz)
    ponto = ponto_de_partida(raiz, base) if base else None
    if not ponto:
        return {"erro": f"sem base para o diff ({base or 'nenhuma ref'}) — passe --base"}
    return {"base": base, "ponto": ponto[:12], "relatorio": relatorio,
            **classificar_origem(achados_da_revisao(texto), trechos_do_diff(raiz, ponto))}


# --- investigar antes de corrigir (ADR-0060) ----------------------------------------
# A ideia vem da corno-investiga (corno-skills, sem licença declarada: a ideia, não o
# texto). Correção sem causa é chute: o sintoma some e a causa fica. A fábrica pede o
# laço que mostra o problema, a causa escrita antes do conserto e a prova de que o mesmo
# laço falha na base e passa depois. O `reproduzir` roda o laço nos dois lados, o
# `investigacao` confere a ficha, e o `marcas` acha o log de depuração que sobrou.

MARCA_DEPURACAO = re.compile(r"forge-depura-[0-9a-z]+", re.I)
SEM_MARCA = {".md", ".mdx", ".rst"}   # a ficha e a documentação citam a marca de propósito
CAMPO_MD = re.compile(r"^\s*[-*]?\s*\*\*([^*:]+):\*\*\s*(.*?)\s*$")
ENTRE_CRASES = re.compile(r"`([^`]+)`")
MIN_CAUSA = 20          # a mesma régua da premissa do `ciclo.py`
PARAR_DEPOIS_DE = 3     # hipóteses descartadas sem nenhuma confirmada: pare e pergunte
SAIDA_DA_FICHA = {"pronta": 0, "pare_e_pergunte": 2}


def _rodar(cmd: str, cwd: Path, tempo_limite: int) -> dict:
    """O laço num grupo de processos próprio: no tempo estourado, o grupo inteiro morre."""
    p = subprocess.Popen(cmd, shell=True, cwd=str(cwd), stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, start_new_session=True)
    try:
        saida, _ = p.communicate(timeout=tempo_limite)
    except subprocess.TimeoutExpired:
        _matar_grupo(p)
        return {"exit": None, "saida": f"estourou {tempo_limite}s"}
    return {"exit": p.returncode, "saida": saida.decode("utf-8", errors="replace")}


def _matar_grupo(p: subprocess.Popen) -> None:
    try:
        os.killpg(p.pid, 9)
    except OSError:
        pass   # o grupo já acabou
    p.communicate()


def _final(saida: str) -> list[str]:
    return [l[:160] for l in saida.strip().splitlines() if l.strip()][-4:]


def _estado_do_laco(r: dict, sintoma: re.Pattern | None) -> str:
    """Uma rodada do laço: `falhou` (com o sintoma, se houver), `sintoma_diferente`,
    `passou` ou `nao_executado`. O laço mostra o problema saindo diferente de 0."""
    if r["exit"] is None or r["exit"] in (126, 127):   # estourou, ou o laço nem existe ali
        return "nao_executado"
    if r["exit"] == 0:
        return "passou"
    return "falhou" if sintoma is None or sintoma.search(r["saida"]) else "sintoma_diferente"


def veredicto_da_reproducao(antes: str, depois: str | None) -> str:
    if antes in ("nao_executado", "sintoma_diferente"):
        return antes
    if antes == "passou":
        return "nao_reproduz"
    if depois is None:
        return "reproduz"
    return {"passou": "reproduz_e_corrige", "nao_executado": "nao_executado"}.get(
        depois, "nao_corrige")


def _diff_sem_renomear(raiz: Path, ponto: str) -> list[tuple[str, str]]:
    """(status, caminho), com renomeação como `D` da origem e `A` do destino."""
    r = git(raiz, "diff", "--name-status", "--no-renames", ponto)
    return [(l.split("\t")[0][:1], l.split("\t")[-1]) for l in r.stdout.splitlines() if "\t" in l]


def testes_do_diff(raiz: Path, ponto: str) -> list[str]:
    """Teste novo ou mudado no diff: a regressão costuma entrar num arquivo que já existe."""
    nomes = [c for s, c in _diff_sem_renomear(raiz, ponto) if s in ("A", "M") and eh_teste(c)]
    nomes += [c for c in nao_rastreados(raiz) if eh_teste(c)]
    return sorted(dict.fromkeys(nomes))


def testes_que_sairam(raiz: Path, ponto: str) -> list[str]:
    """Teste que existia na base e não existe agora (apagado ou renomeado): sai da base também,
    senão apagar o teste que falha pareceria conserto."""
    return sorted(c for s, c in _diff_sem_renomear(raiz, ponto) if s == "D" and eh_teste(c))


@contextmanager
def arvore_na_base(raiz: Path, ponto: str):
    """Worktree descartável no ponto de partida; None quando o git não o cria."""
    tmp = Path(tempfile.mkdtemp(prefix="kairos-forge-reproduz-"))
    worktree = tmp / "base"
    try:
        r = git(raiz, "worktree", "add", "--detach", str(worktree), ponto, timeout=120)
        yield worktree if r.returncode == 0 else None
    finally:
        git(raiz, "worktree", "remove", "--force", str(worktree), timeout=60)
        git(raiz, "worktree", "prune")
        shutil.rmtree(tmp, ignore_errors=True)


def _copiar(raiz: Path, destino: Path, arquivos: list[str]) -> list[str]:
    copiados = []
    for rel in arquivos:
        try:
            (destino / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(raiz / rel, destino / rel)
            copiados.append(rel)
        except OSError:
            # Quem não copia fica fora de `copiados`, que vai no resultado: a falta aparece ali,
            # e o laço na base diz o resto (`sintoma_diferente` ou `nao_reproduz`).
            pass
    return copiados


def _sintoma(sintoma: str | None) -> tuple[re.Pattern | None, str | None]:
    try:
        return (re.compile(sintoma) if sintoma else None), None
    except re.error as e:
        return None, f"o sintoma não é uma regex válida: {e}"


def base_e_ponto(raiz: Path, base: str | None) -> tuple[str | None, str | None, str | None]:
    """(base, ponto, erro): a base pedida ou a padrão, e o merge-base dela com o HEAD."""
    base = base or base_padrao(raiz)
    ponto = ponto_de_partida(raiz, base) if base else None
    erro = None if ponto else f"sem base para o diff ({base or 'nenhuma ref'}) — passe --base"
    return base, ponto, erro


def _so_aqui(raiz: Path, comando: str, rx: re.Pattern | None, tempo_limite: int) -> dict:
    aqui = _rodar(comando, raiz, tempo_limite)
    return {"veredicto": veredicto_da_reproducao(_estado_do_laco(aqui, rx), None),
            "antes": _final(aqui["saida"])}


def _na_base(raiz: Path, ponto: str, comando: str, tempo_limite: int) -> tuple[dict | None, list[str]]:
    """A rodada do laço no worktree da base, com os testes do diff copiados para lá."""
    with arvore_na_base(raiz, ponto) as worktree:
        if worktree is None:
            return None, []
        ligar_dependencias(raiz, worktree)
        copiados = _copiar(raiz, worktree, testes_do_diff(raiz, ponto))
        for rel in testes_que_sairam(raiz, ponto):
            (worktree / rel).unlink(missing_ok=True)
        return _rodar(comando, worktree, tempo_limite), copiados


def reproduzir(raiz: Path, base: str | None, comando: str | None, sintoma: str | None,
               tempo_limite: int, antes: bool = False) -> dict:
    """Roda o laço na base do diff (com os testes do diff copiados) e na árvore de trabalho.
    Com `antes`, só aqui: é a conferência de que o laço mostra o problema antes do conserto."""
    rx, erro = _sintoma(sintoma)
    if erro or not comando:
        return {"erro": erro or 'diga o laço: --comando "o que mostra o problema"'}
    r = {"comando": comando, "sintoma": sintoma}
    if antes:
        return {**r, **_so_aqui(raiz, comando, rx, tempo_limite)}
    base, ponto, erro = base_e_ponto(raiz, base)
    if erro:
        return {"erro": erro}
    na_base, copiados = _na_base(raiz, ponto, comando, tempo_limite)
    if na_base is None:
        return {"erro": "não consegui criar o worktree na base"}
    depois = _rodar(comando, raiz, tempo_limite)
    return {**r, "base": base, "ponto": ponto[:12], "copiados": copiados,
            "veredicto": veredicto_da_reproducao(_estado_do_laco(na_base, rx),
                                                 _estado_do_laco(depois, rx)),
            "antes": _final(na_base["saida"]), "depois": _final(depois["saida"])}


def gerados(raiz: Path, rels: list[str]) -> set[str]:
    """Arquivos marcados `linguist-generated` ou `linguist-vendored` no `.gitattributes`:
    cópia espelhada, código gerado, biblioteca de terceiro, fixture escrito errado de
    propósito. Ninguém os edita à mão aqui."""
    marcados: set[str] = set()
    for i in range(0, len(rels), 200):
        r = git(raiz, "check-attr", "linguist-generated", "linguist-vendored", "--",
                *rels[i:i + 200], timeout=60)
        for linha in r.stdout.splitlines():
            atributo, _, valor = linha.rpartition(": ")
            if valor.strip() in ("true", "set"):
                marcados.add(atributo.rsplit(": ", 1)[0])
    return marcados


def marcas(raiz: Path, base: str | None) -> dict:
    """Linha nova com a marca de depuração: log que era para sair antes de terminar. O que
    o `.gitattributes` marca como gerado ou de terceiro fica de fora."""
    base, ponto, erro = base_e_ponto(raiz, base)
    if erro:
        return {"erro": erro, "marcas": []}
    com_marca = [(rel, n, linha) for rel, n, linha in linhas_acrescentadas(raiz, ponto)
                 if Path(rel).suffix.lower() not in SEM_MARCA
                 and not rel.startswith(".agents/execucoes/") and MARCA_DEPURACAO.search(linha)]
    fora = gerados(raiz, sorted({rel for rel, _, _ in com_marca}))
    return {"base": base, "ponto": ponto[:12],
            "marcas": [{"arquivo": rel, "linha": n, "trecho": linha.strip()[:160]}
                       for rel, n, linha in com_marca if rel not in fora]}


def secoes_md(texto: str) -> dict[str, str]:
    """Título de `## ` (minúsculo) → corpo. Título dentro de bloco de código não abre seção."""
    secoes: dict[str, str] = {}
    atual, em_bloco = None, False
    for linha in texto.splitlines():
        if linha.lstrip().startswith("```"):
            em_bloco = not em_bloco
        m = None if em_bloco else SECAO_MD.match(linha)
        if m:
            atual = m.group(1).strip().casefold()
            secoes[atual] = ""
        elif atual is not None:
            secoes[atual] += linha + "\n"
    return secoes


def campos_md(texto: str) -> dict[str, str]:
    """`**Nome:** valor` (com ou sem marcador de lista) → {nome minúsculo: valor}."""
    campos: dict[str, str] = {}
    for linha in texto.splitlines():
        m = CAMPO_MD.match(linha)
        if m:
            campos.setdefault(m.group(1).strip().casefold(), m.group(2).strip())
    return campos


CELULA_SEPARADORA = re.compile(r"^:?-+:?$")


def linhas_da_tabela(corpo: str) -> list[list[str]]:
    """As linhas de dados de uma tabela: sem o cabeçalho (a linha antes do separador) e sem o
    separador. Célula vazia na primeira coluna não tira a linha da conta."""
    linhas: list[list[str]] = []
    for linha in corpo.splitlines():
        if not linha.strip().startswith("|"):
            continue
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        if all(CELULA_SEPARADORA.match(c) for c in celulas):
            if linhas:
                linhas.pop()    # a linha de cima era o cabeçalho
            continue
        linhas.append(celulas)
    return linhas


MARCADOR_DO_MODELO = re.compile(r"^\s*(?:[-*]\s+)?<[^>]*>\.?\s*$")


def _preenchido(texto: str | None, minimo: int = 1) -> bool:
    """Texto de verdade: sem as linhas que são só o `<…>` do modelo, com ou sem marcador."""
    t = "\n".join(l for l in (texto or "").splitlines() if not MARCADOR_DO_MODELO.match(l)).strip()
    return len(t) >= minimo


def resultado_da_hipotese(celula: str) -> str:
    c = re.sub(r"^[^\w<]+", "", celula).casefold()   # `**confirmada**`, `✅ confirmada`
    return "descartada" if c.startswith("descart") else (
        "confirmada" if c.startswith("confirm") else "aberta")


def ler_ficha(texto: str) -> dict:
    campos, secoes = campos_md(texto), secoes_md(texto)
    comando = ENTRE_CRASES.search(campos.get("reprodução", ""))
    sintoma = ENTRE_CRASES.search(campos.get("sintoma na saída", ""))
    hip = [resultado_da_hipotese(c[-1]) for c in linhas_da_tabela(secoes.get("hipóteses", ""))
           if len(c) > 1 and _preenchido(c[1])]   # a linha do modelo, `<causa possível>`, não conta
    return {"comando": comando.group(1) if comando else None,
            "sintoma": sintoma.group(1) if sintoma else None,
            "descartadas": hip.count("descartada"), "confirmadas": hip.count("confirmada"),
            "abertas": hip.count("aberta"),
            "problemas": [msg for ok, msg in (
                (_preenchido(campos.get("sintoma")), "sem **Sintoma:** (o que a pessoa viu)"),
                (comando, "sem **Reprodução:** com o comando entre crases"),
                (sintoma, "sem **Sintoma na saída:** com a regex entre crases"),
                (hip, "sem a tabela de `## Hipóteses`"),
                (not hip or "confirmada" in hip, "nenhuma hipótese confirmada"),
                (_preenchido(secoes.get("causa"), MIN_CAUSA),
                 f"`## Causa` vazia ou com menos de {MIN_CAUSA} caracteres"),
                (_preenchido(secoes.get("prova")), "`## Prova` vazia: o que liga e desliga o bug"),
                (_preenchido(secoes.get("trava")),
                 "`## Trava` vazia: o teste que impede o problema de voltar, ou por que não há"),
            ) if not ok]}


def investigacao(raiz: Path, base: str | None, ficha: str | None, tempo_limite: int) -> dict:
    texto, erro = _ler_md(ficha, "diga qual ficha conferir: prova.py investigacao "
                                 "docs/investigacoes/INV-<slug>.md", "a ficha")
    if erro:
        return {"erro": erro}
    lida = ler_ficha(texto)
    r = {"ficha": ficha, **lida}
    if lida["confirmadas"] == 0 and lida["descartadas"] >= PARAR_DEPOIS_DE:
        return {**r, "veredicto": "pare_e_pergunte"}
    repro = (reproduzir(raiz, base, lida["comando"], lida["sintoma"], tempo_limite)
             if lida["comando"] else {"veredicto": "nao_executado"})
    sobra = marcas(raiz, base)["marcas"]
    problemas = lida["problemas"] + [msg for ok, msg in (
        (not repro.get("erro"), repro.get("erro")),
        (repro.get("erro") or repro["veredicto"] == "reproduz_e_corrige",
         f"a reprodução deu `{repro.get('veredicto')}`, não `reproduz_e_corrige`"),
        (not sobra, f"{len(sobra)} linha(s) nova(s) com a marca de depuração"),
    ) if not ok]
    return {**r, "reproducao": repro, "marcas": sobra, "problemas": problemas,
            "veredicto": "incompleta" if problemas else "pronta"}


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


# --- fonte primária salva (ADR-0060) ------------------------------------------------
# A ideia vem da corno-pesquisa (corno-skills, sem licença declarada: a ideia, não o
# texto). O que a fábrica afirma sobre biblioteca, API ou versão vale o que vale a fonte,
# e a fonte consultada numa conversa some com ela. A pesquisa fica em
# `docs/pesquisa/<assunto>.md`, com data, resposta e cada fato com link, versão e data; e
# quem decide a partir dela cita o caminho. O `fontes` confere a forma dos arquivos e as
# citações, sem rede: a verdade da fonte é do revisor, a forma é do código.

PASTA_PESQUISA = "docs/pesquisa"
CITACAO_PESQUISA = re.compile(r"(?<![\w/.:-])docs/pesquisa/[\w./-]+?\.md\b")
LINK = re.compile(r"https?://[^\s)>\]]+")
CAMINHO_NA_FONTE = re.compile(r"([\w.-]+/[\w./-]*[\w-]|[\w-]+\.[A-Za-z0-9]+)(?::\d+(?:-\d+)?)?")
DATA_DA_FONTE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
MARCADOR_NA_CELULA = re.compile(r"<[^>]+>")
TITULO_H1 = re.compile(r"^#\s+\S", re.M)
NAO_ENCONTRADA = re.compile(r"^\W*n[ãa]o encontrad", re.I)   # a resposta é essa, não a cita
IDADE_MAX_PADRAO = 180
try:
    from segredos import ocultar_segredos
except Exception:                     # cópia avulsa do script, sem o segredos.py ao lado
    def ocultar_segredos(texto: str) -> tuple[str, list[str]]:
        return texto, []


def _data(texto: str | None) -> date | None:
    try:
        return date.fromisoformat((texto or "").strip("` ")[:10])
    except ValueError:
        return None


def _fonte_existe(raiz: Path, fonte: str) -> bool:
    """Um link, ou um caminho do repositório que exista (com `:linha` ou não)."""
    if LINK.search(fonte):
        return True
    dentro = raiz.resolve()
    return any((raiz / m.group(1)).resolve().is_relative_to(dentro) and (raiz / m.group(1)).exists()
               for m in CAMINHO_NA_FONTE.finditer(fonte))


def _data_da_fonte(texto: str, hoje: date) -> bool:
    """AAAA-MM-DD ou AAAA-MM de verdade, e não no futuro."""
    t = texto.strip("` ")
    # O `_data` lê os dez primeiros caracteres: AAAA-MM-DD fica como está, AAAA-MM vale pelo dia 1.
    dia = _data(f"{t}-01") if DATA_DA_FONTE.fullmatch(t) else None
    return dia is not None and dia <= hoje


def problemas_do_fato(celulas: list[str], raiz: Path, hoje: date | None = None) -> list[str]:
    n = celulas[0] or "?"
    if len(celulas) < 5:
        return [f"fato {n}: a linha precisa de fato, fonte, versão e data da fonte"]
    _, fato, fonte, versao, quando = celulas[:5]
    return [f"fato {n}: {msg}" for ok, msg in (
        (_preenchido(fato), "sem o fato"),
        (_fonte_existe(raiz, fonte) and not MARCADOR_NA_CELULA.search(fonte),
         "sem fonte: um link ou um caminho do repositório que exista"),
        (_preenchido(versao), "sem versão (escreva `sem versão` quando a fonte não tem)"),
        (_data_da_fonte(quando, hoje or date.today()),
         "data da fonte fora de AAAA-MM-DD ou AAAA-MM, ou no futuro"),
    ) if not ok]


def problemas_da_pesquisa(texto: str, raiz: Path, hoje: date) -> tuple[list[str], date | None]:
    campos, secoes = campos_md(texto), secoes_md(texto)
    data = _data(campos.get("data da pesquisa"))
    resposta = campos.get("resposta")
    fatos = linhas_da_tabela(secoes.get("fatos", ""))
    nao_achou = bool(NAO_ENCONTRADA.match(resposta or ""))
    problemas = [msg for ok, msg in (
        (TITULO_H1.search(texto), "sem título `# <pergunta>`"),
        (data, "sem **Data da pesquisa:** AAAA-MM-DD"),
        (not data or data <= hoje, "data da pesquisa no futuro"),
        (_preenchido(resposta), "sem **Resposta:**"),
        (fatos or nao_achou, "`## Fatos` sem nenhuma linha"),
        (not nao_achou or _preenchido(secoes.get("em aberto")),
         'resposta "não encontrada" sem `## Em aberto`'),
        (not ocultar_segredos(texto)[1], "segredo no texto: rode `guardrail.py ocultar <arquivo>`"),
    ) if not ok]
    for celulas in fatos:
        problemas += problemas_do_fato(celulas, raiz, hoje)
    return problemas, data


def _mds(raiz: Path) -> list[str]:
    """Os `.md` do repositório pelo git (respeita o `.gitignore` e não entra em worktree
    aninhado, como os `.worktrees/` do `/mobilizar`); fora de git, pela árvore."""
    r = git(raiz, "ls-files", "-co", "--exclude-standard", "-z", "--", "*.md")
    if r.returncode == 0:
        return sorted(x for x in r.stdout.split("\0") if x)
    rels = []
    for pasta, subpastas, nomes in os.walk(raiz):
        subpastas[:] = sorted(d for d in subpastas if d not in DIRS_IGNORADOS_SELADO)
        rels += [(Path(pasta) / n).relative_to(raiz).as_posix() for n in nomes if n.endswith(".md")]
    return sorted(rels)


def superficie_md(raiz: Path) -> list[tuple[str, str]]:
    """(rel, texto) de todo `.md` do repositório, menos dependência, `.git` e trajetória."""
    achados = []
    for rel in _mds(raiz):
        if rel.startswith(".agents/execucoes/"):
            continue
        try:
            achados.append((rel, (raiz / rel).read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            continue
    return achados


def citacoes_quebradas(raiz: Path) -> list[dict]:
    return [{"arquivo": rel, "linha": n, "alvo": alvo}
            for rel, texto in superficie_md(raiz)
            for n, linha in enumerate(texto.splitlines(), 1)
            for alvo in CITACAO_PESQUISA.findall(linha) if not (raiz / alvo).is_file()]


def _mudou_depois(raiz: Path, rel: str, quando: str | None) -> bool | None:
    if not quando:
        return None
    limite = instante(quando)
    # A data de autor: o rebase depois do selo muda a de commit, não a de quem escreveu.
    datas = git(raiz, "log", "--format=%aI", "--", rel).stdout.split()
    pendente = git(raiz, "status", "--porcelain", "--", rel).stdout.strip()
    if limite is None:
        return bool(pendente or datas)
    # O `--since` inclui o próprio commit da aprovação, que traz a versão aprovada.
    return bool(pendente) or any((instante(d) or limite) > limite for d in datas)


def fontes_da_spec(raiz: Path, spec: str) -> dict:
    """As pesquisas que a SPEC cita, e se alguma mudou depois da aprovação."""
    arquivo = arquivo_da_spec(raiz, spec)
    if arquivo is None:
        return {"spec": spec, "erro": "SPEC não encontrada em docs/specs/"}
    quando, fonte = momento_da_aprovacao(raiz, spec, arquivo)
    citadas = sorted(set(CITACAO_PESQUISA.findall(arquivo.read_text(encoding="utf-8"))))
    return {"spec": spec, "aprovacao": quando, "fonte_da_aprovacao": fonte,
            "citadas": [{"pesquisa": rel, "existe": (raiz / rel).is_file(),
                         "mudou_depois": _mudou_depois(raiz, rel, quando)} for rel in citadas]}


def _pesquisa(arq: Path, raiz: Path, hoje: date, idade_max: int) -> dict:
    rel = arq.relative_to(raiz).as_posix()
    try:
        texto = arq.read_text(encoding="utf-8", errors="replace")
    except OSError as e:   # link quebrado, pasta com nome .md, sem permissão
        return {"arquivo": rel, "data": "", "problemas": [f"ilegível: {type(e).__name__}"],
                "avisos": []}
    problemas, data = problemas_da_pesquisa(texto, raiz, hoje)
    velha = data is not None and (hoje - data).days > idade_max
    return {"arquivo": rel, "data": str(data or ""), "problemas": problemas,
            "avisos": [f"mais de {idade_max} dias: confira se a fonte mudou"] if velha else []}


def fontes(raiz: Path, spec: str | None, idade_max: int, hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    pasta = raiz / PASTA_PESQUISA
    arquivos = sorted(p for p in pasta.rglob("*.md") if p.name != "README.md") \
        if pasta.is_dir() else []
    pesquisas = [_pesquisa(arq, raiz, hoje, idade_max) for arq in arquivos]
    return {"raiz": str(raiz), "pesquisas": pesquisas,
            "citacoes_quebradas": citacoes_quebradas(raiz),
            "spec": fontes_da_spec(raiz, spec) if spec else None, "idade_max": idade_max}


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
    "erro_na_base": "⚠️  erro na base",
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
    _imprimir_resumo_pre_patch(r["testes"])


def _imprimir_resumo_pre_patch(testes: list[dict]) -> None:
    sem_carga = [t for t in testes if t["veredicto"] == "erro_na_base"]
    if sem_carga:
        print(f"\n   {len(sem_carga)} teste(s) novo(s) não carregaram na base por algo que o diff "
              "não acrescenta\n   (dependência, sintaxe, auxiliar): não provam a mudança. "
              "Corrija o ambiente ou o teste e rode de novo.")
    ruins = [t for t in testes if t["veredicto"] == "passou_na_base"]
    if ruins:
        print(f"\n   {len(ruins)} teste(s) novo(s) passam sem a mudança. Ou o teste não exercita "
              "o que o patch fez,\n   ou é regressão de comportamento que a base já tinha — "
              "nos dois casos a justificativa vai no relatório de validação.")
    else:
        print("\n   Nenhum teste novo passa na base sem a mudança.")


FORA_DO_LUGAR = {
    "fora_sem_dizer": (
        "bloqueia numa linha que o PR não tocou, sem dizer como o PR o afeta:",
        "Se já existia antes, vai para `## Fora deste PR` (não bloqueia). Se o PR depende dele "
        "ou o piora, marque `· o PR depende: <como>` ou `· o PR piora: <como>`."),
    "do_pr_como_observacao": (
        "observação numa linha que o PR escreveu:",
        "É do PR: volta para a seção da gravidade dele."),
}


def imprimir_origem(r: dict) -> None:
    if r.get("erro"):
        print(f"🚫 {r['erro']}")
        return
    print(f"🧭 Origem dos achados — {r['relatorio']} contra {r['base']} ({r['ponto']})")
    sem = f", {len(r['sem_local'])} sem `arquivo:linha` (não conferido)" if r["sem_local"] else ""
    print(f"   {r['conferidos']} achado(s) com local conferido(s){sem}")
    for chave, (titulo, dica) in FORA_DO_LUGAR.items():
        if r[chave]:
            print(f"\n   ✗ {titulo}")
            for a in r[chave]:
                print(f"     · {a['texto'][:140]}")
            print(f"     {dica}")
    if not any(r[chave] for chave in FORA_DO_LUGAR):
        print("   ✅ o que bloqueia é do PR, e o que é de fora não bloqueia")


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


REPRODUCAO = {
    "reproduz": "✅ o laço mostra o problema",
    "reproduz_e_corrige": "✅ falha na base e passa agora",
    "nao_reproduz": "❌ o laço passa: não mostra o problema",
    "sintoma_diferente": "❌ o laço falha, mas não com o sintoma: é outro erro",
    "nao_corrige": "❌ o laço ainda falha depois da correção",
    "nao_executado": "⚠️  o laço não rodou até o fim (tempo estourado, ou o comando não existe ali)",
}


def imprimir_reproduzir(r: dict) -> None:
    if r.get("erro"):
        print(f"🚫 {r['erro']}")
        return
    onde = f" — base {r['base']} ({r['ponto']})" if r.get("base") else " — antes do conserto"
    print(f"🔁 Reprodução{onde}\n   laço: {r['comando']}")
    print(f"   sintoma: {r['sintoma']}" if r.get("sintoma") else
          "   sem --sintoma: qualquer saída diferente de 0 conta como o problema")
    if r.get("copiados"):
        print(f"   testes do diff copiados para a base: {', '.join(r['copiados'])}")
    print(f"   {REPRODUCAO[r['veredicto']]}")
    for lado in ("antes", "depois"):
        for linha in r.get(lado, []):
            print(f"      {lado:6} │ {linha[:110]}")


def imprimir_marcas(r: dict) -> None:
    if r.get("erro"):
        print(f"🚫 {r['erro']}")
        return
    print(f"🧹 Marca de depuração no diff contra {r['base']} ({r['ponto']}): {len(r['marcas'])}")
    for m in r["marcas"]:
        print(f"   {m['arquivo']}:{m['linha']}\t{m['trecho'][:100]}")
    if r["marcas"]:
        print("   Log de depuração sai antes de dizer que terminou.")


FICHA = {
    "pronta": "✅ ficha pronta: a causa está escrita e o laço falha na base e passa agora",
    "pare_e_pergunte": (f"✋ {PARAR_DEPOIS_DE} hipóteses ou mais caíram e nenhuma se sustentou:"
                        " a investigação não avança sem informação nova; leve à pessoa o laço e"
                        " as hipóteses que caíram"),
    "incompleta": "❌ ficha incompleta",
}


def imprimir_investigacao(r: dict) -> None:
    if r.get("erro"):
        print(f"🚫 {r['erro']}")
        return
    print(f"🔎 Investigação — {r['ficha']}")
    print(f"   hipóteses: {r['confirmadas']} confirmada(s), {r['descartadas']} descartada(s),"
          f" {r['abertas']} aberta(s)")
    if r.get("reproducao", {}).get("veredicto"):
        print(f"   reprodução: {REPRODUCAO[r['reproducao']['veredicto']]}")
    print(f"   {FICHA[r['veredicto']]}")
    for problema in r.get("problemas", []):
        print(f"     ✗ {problema}")


def _imprimir_pesquisa(p: dict) -> None:
    marca = "❌" if p["problemas"] else ("⚠️ " if p["avisos"] else "✅")
    print(f"   {marca} {p['arquivo']} ({p['data'] or 'sem data'})")
    for item in p["problemas"] + p["avisos"]:
        print(f"      · {item}")


def imprimir_fontes(r: dict) -> None:
    pesquisas, quebradas = r["pesquisas"], r["citacoes_quebradas"]
    print(f"📚 Fontes salvas — {len(pesquisas)} pesquisa(s) em {PASTA_PESQUISA}/")
    for p in pesquisas:
        _imprimir_pesquisa(p)
    for c in quebradas:
        print(f"   ❌ {c['arquivo']}:{c['linha']} cita {c['alvo']}, que não existe")
    if r.get("spec"):
        _imprimir_fontes_da_spec(r["spec"])
    if not pesquisas and not quebradas:
        print("   nada a conferir")


def _imprimir_fontes_da_spec(spec: dict) -> None:
    if spec.get("erro"):
        print(f"   🚫 {spec['spec']}: {spec['erro']}")
        return
    print(f"   {spec['spec']} cita {len(spec['citadas'])} pesquisa(s); aprovação: "
          f"{spec['aprovacao'] or 'não encontrada'}")
    for c in spec["citadas"]:
        mudou = {True: " — mudou depois da aprovação", False: "", None: ""}[c["mudou_depois"]]
        print(f"      {'✅' if c['existe'] else '❌'} {c['pesquisa']}{mudou}")


def _mostrar(r: dict, como_json: bool, imprimir) -> None:
    if como_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        imprimir(r)


def _raiz_pedida(opcao) -> Path:
    alvo = opcao("--raiz")
    return Path(alvo).resolve() if alvo else (raiz_git() or Path.cwd())


def _cli_colher(args: list[str], opcao, como_json: bool, template: str | None, tempo: int) -> int:
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
    _mostrar(r, como_json, imprimir_colher)
    return 0


def _cli_fontes(args: list[str], opcao, como_json: bool, *_) -> int:
    try:
        idade = int(opcao("--idade-max") or IDADE_MAX_PADRAO)
    except ValueError:
        print("erro: --idade-max precisa de um número de dias", file=sys.stderr)
        return 1
    spec = next((a.upper() for a in args[1:] if ID_SPEC.match(a)), None)
    r = fontes(_raiz_pedida(opcao), spec, idade)
    _mostrar(r, como_json, imprimir_fontes)
    quebrado = r["citacoes_quebradas"] or any(p["problemas"] for p in r["pesquisas"])
    return 1 if quebrado or (r["spec"] or {}).get("erro") else 0


def _cli_selado(args: list[str], opcao, como_json: bool, *_) -> int:
    r = selado(_raiz_pedida(opcao))
    _mostrar(r, como_json, imprimir_selado)
    return 1 if (r["vazamentos"] or r["no_visivel"] or r["ilegiveis"]) else 0


# Os comandos que não medem o diff: cada um com a sua leitura dos argumentos.
FORA_DO_DIFF = {"colher": _cli_colher, "fontes": _cli_fontes, "selado": _cli_selado}


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] not in (*SOBRE_O_DIFF, *FORA_DO_DIFF):
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
    if comando in FORA_DO_DIFF:
        return FORA_DO_DIFF[comando](args, opcao, como_json, template, tempo)

    raiz = raiz_git()
    if raiz is None:
        print("🚫 fora de um repositório git — sem diff não há prova", file=sys.stderr)
        return 1
    calcular, imprimir, reprova = SOBRE_O_DIFF[comando]
    r = calcular(raiz, base, template, tempo, args)
    _mostrar(r, como_json, imprimir)
    return 1 if r.get("erro") else int(reprova(r))


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
    "origem": (lambda raiz, base, _t, _s, args: origem(raiz, base, next(
                   (a for a in args[1:] if a.endswith(".md")), None)),
               lambda r: imprimir_origem(r),
               lambda r: any(r[chave] for chave in FORA_DO_LUGAR)),
    "reproduzir": (lambda raiz, base, comando, tempo, args: reproduzir(
                       raiz, base, comando, _valor(args, "--sintoma"), tempo, "--antes" in args),
                   lambda r: imprimir_reproduzir(r),
                   lambda r: r["veredicto"] not in ("reproduz", "reproduz_e_corrige")),
    "marcas": (lambda raiz, base, *_: marcas(raiz, base),
               lambda r: imprimir_marcas(r),
               lambda r: bool(r["marcas"])),
    "investigacao": (lambda raiz, base, _t, tempo, args: investigacao(
                         raiz, base, next((a for a in args[1:] if a.endswith(".md")), None), tempo),
                     lambda r: imprimir_investigacao(r),
                     lambda r: SAIDA_DA_FICHA.get(r["veredicto"], 1)),
}


def _valor(args: list[str], nome: str) -> str | None:
    i = args.index(nome) if nome in args else -1
    return args[i + 1] if 0 <= i < len(args) - 1 else None


if __name__ == "__main__":
    sys.exit(main())
