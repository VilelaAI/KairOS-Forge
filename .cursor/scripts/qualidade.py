#!/usr/bin/env python3
"""qualidade.py — os gates de "deixar certo" sobre o diff (ADR-0045).

Primeiro fazer funcionar, depois deixar certo. A fábrica já prova a primeira metade:
o gate roda, o `prova.py` mostra que o teste novo falha sem a mudança, o `/validar`
confere a SPEC. A segunda metade ficava no olho de quem revisa — e o olho cansa
justamente no diff grande. Inspirado no ub-mode de Robert C. Martin e nas três
ferramentas que ele usa como gate (crapper, dryer, mutator — 0BSD; aqui as ideias e
a fórmula, com código próprio, só stdlib), este script mede três coisas, sempre nas
funções que o diff tocou, nunca no legado que ninguém pediu para mexer:

  1. `crap` — complexidade ciclomática × cobertura, por função tocada:

         CRAP = CC² × (1 − cobertura)³ + CC

     No limite (padrão 10) ou acima, a função é complexa demais para os testes que
     tem: quebre em funções menores, teste o que falta, ou as duas coisas. Sem
     relatório de cobertura o CRAP não existe — mas CRAP ≥ CC sempre, então função com
     CC no limite já reprova sem cobertura nenhuma; as outras saem `indeterminado`,
     nunca inventadas.

     Função que já estava no limite ou acima na base é legado: o diff que a toca sem
     subir a complexidade sai `legado_acima` — listado, sem reprovar. É uma catraca, como
     a do `/otimizar`: tocar código ruim não obriga a reescrevê-lo, mas proíbe piorá-lo.

  2. `duplicacao` — similaridade estrutural (Jaccard de impressões) entre cada função
     tocada e as demais funções da mesma linguagem. Nome de variável e literal não
     contam; chamada, operador e forma da árvore contam. No limite (padrão 0,8) ou
     acima, é uma decisão morando em dois lugares.

  3. `mutacao` — muda um operador por vez nas linhas tocadas (`==`→`!=`, `<`→`<=`,
     `and`→`or`, `True`→`False`, `+`→`-`, `return x`→`return None`) e roda a suíte num
     worktree descartável. Mutante que sobrevive é teste que não percebe o comportamento
     mudar: se a suíte passa com a função devolvendo nada, ela não testa a função.

Nenhum dos três decide sozinho. Mutante equivalente existe, duplicação às vezes é
coincidência de forma, e cobertura velha mente. O script transforma o silêncio em
achado com nome; quem julga a justificativa é o `/kairos-forge:validar`.

## Uso

    qualidade.py crap        [--base REF] [--cobertura ARQ] [--limite 10] [--json]
    qualidade.py duplicacao  [--base REF] [--limite 0.8] [--min-linhas 4] [--json]
    qualidade.py mutacao     [--base REF] [--comando "CMD"] [--max 25]
                             [--tempo-limite S] [--teto S] [--json]

`--base` funciona como no `prova.py`: o diff é medido contra o merge-base com a base
(default `origin/HEAD`, depois `origin/main`, `origin/master`, `main`, `master`) e
inclui o que ainda não foi commitado.

`--cobertura` aponta o relatório. Sem ele, o script procura, nesta ordem:
`coverage.json` (coverage.py), `coverage/lcov.info`, `lcov.info`, `coverage.lcov`,
`coverage.xml`, `cobertura.xml`, `coverage/cobertura-coverage.xml`, `coverage.out`,
`cover.out`. Relatório mais antigo que o código tocado sai com aviso: cobertura de
ontem não cobre o código de hoje.

`--comando` é a suíte que a mutação roda (ex.: `--comando "python3 -m pytest -q"`).
Sem ele: pytest (ou unittest) para Python, vitest/jest/`npm test` pelo
`package.json`, `go test ./...` para Go. A suíte tem de passar antes da primeira
mutação — base vermelha não julga mutante nenhum.

Arquivo marcado `linguist-generated` ou `linguist-vendored` no `.gitattributes` fica
de fora das três medidas: cópia espelhada e código de terceiro não se editam aqui.

## Linguagens

Python é lido pela árvore sintática (`ast`): conta `if`, `elif`, `for`, `while`,
`except`, cada `case`, cada filtro de compreensão, cada expressão condicional e cada
`and`/`or` — as mesmas decisões do crapper. JS/TS e Go são lidos por varredura de
texto, com comentário e string apagados antes: conta `if`, `for`, `while`, `case`,
`catch`, `&&`, `||` (e `??`, `?.` e ternário no JS/TS). É heurística declarada: código
que a varredura não entende sai em `nao_analisados`, nunca com número inventado.

Função aninhada não é unidade própria: as decisões dela contam para a que a contém.

## Saída

Exit 1 quando há achado (`acima_do_limite`, par duplicado, mutante sobrevivente) ou
quando a medida não pôde ser feita (sem base, base vermelha, sem comando). 0 caso
contrário. `--json` dá a forma estável para o `/validar` e para o CI.

Só stdlib.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prova  # noqa: E402  — git, base, diff e worktree vivem num lugar só

LINGUAGEM_POR_SUFIXO = {
    ".py": "python",
    ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js", ".ts": "js", ".tsx": "js",
    ".go": "go",
}
PASTAS_IGNORADAS = {"node_modules", "vendor", ".venv", "venv", "dist", "build", "target",
                    ".git", "__pycache__", "coverage", ".metrics"}
TETO_ARQUIVOS = 4000
TETO_BYTES = 400_000

RELATORIOS_DE_COBERTURA = [
    "coverage.json", "coverage/lcov.info", "lcov.info", "coverage.lcov", "coverage.xml",
    "cobertura.xml", "coverage/cobertura-coverage.xml", "coverage.out", "cover.out",
]


# --- arquivos e linhas do diff -----------------------------------------------------

def linguagem_de(rel: str) -> str | None:
    return LINGUAGEM_POR_SUFIXO.get(Path(rel).suffix)


def eh_producao(rel: str) -> bool:
    partes = Path(rel.replace("\\", "/")).parts
    return (not any(p in PASTAS_IGNORADAS for p in partes[:-1])
            and linguagem_de(rel) is not None and not prova.eh_teste(rel))


def gerados(raiz: Path, rels: list[str]) -> set[str]:
    """Arquivos marcados `linguist-generated` ou `linguist-vendored` no `.gitattributes`.

    É o jeito padrão de dizer "não fui escrito à mão aqui": cópia espelhada, código
    gerado, biblioteca de terceiro. Medir qualidade do que ninguém edita é ruído.
    """
    marcados: set[str] = set()
    for i in range(0, len(rels), 200):
        r = prova.git(raiz, "check-attr", "linguist-generated", "linguist-vendored", "--",
                      *rels[i:i + 200], timeout=60)
        for linha in r.stdout.splitlines():
            atributo, _, valor = linha.rpartition(": ")
            if valor.strip() in ("true", "set"):
                marcados.add(atributo.rsplit(": ", 1)[0])
    return marcados


def ler_hunks(diff: str) -> dict[str, set[int]]:
    """{arquivo de produção: linhas novas} a partir de um `git diff -U0`."""
    alteradas: dict[str, set[int]] = {}
    atual = None
    for linha in diff.splitlines():
        if linha.startswith("+++ "):
            alvo = linha[4:].strip()
            atual = alvo[2:] if alvo.startswith("b/") and eh_producao(alvo[2:]) else None
        elif linha.startswith("@@") and atual:
            m = re.search(r"\+(\d+)(?:,(\d+))?", linha)
            ini, qtd = int(m.group(1)), int(m.group(2) or 1)
            alteradas.setdefault(atual, set()).update(range(ini, ini + qtd))
    return alteradas


def contar_linhas(p: Path) -> int:
    try:
        return p.read_text(encoding="utf-8", errors="replace").count("\n") + 1
    except OSError:
        return 0


def linhas_alteradas(raiz: Path, ponto: str) -> dict[str, set[int]]:
    """{arquivo de produção: linhas novas ou alteradas}, incluindo não-commitado."""
    diff = prova.git(raiz, "diff", "-U0", "--no-color", "-M", ponto, timeout=60).stdout
    alteradas = ler_hunks(diff)
    for rel in filter(eh_producao, prova.nao_rastreados(raiz)):
        alteradas[rel] = set(range(1, contar_linhas(raiz / rel) + 1))
    fora = gerados(raiz, sorted(alteradas))
    return {k: v for k, v in alteradas.items() if v and k not in fora and (raiz / k).is_file()}


def arquivos_de_producao(raiz: Path, linguagem: str) -> list[str]:
    listados = prova.git(raiz, "ls-files", timeout=60).stdout.splitlines()
    rels = [rel for rel in dict.fromkeys(listados + prova.nao_rastreados(raiz))
            if eh_producao(rel) and linguagem_de(rel) == linguagem]
    fora = gerados(raiz, rels)
    cabem = [rel for rel in sorted(rels) if rel not in fora and _cabe(raiz / rel)]
    return cabem[:TETO_ARQUIVOS]


def _cabe(p: Path) -> bool:
    return p.is_file() and p.stat().st_size <= TETO_BYTES


def preparar_diff(raiz: Path, base: str | None) -> tuple[dict, str | None]:
    base = base or prova.base_padrao(raiz)
    if not base:
        return {"erro": "nenhuma ref de base encontrada — passe --base"}, None
    ponto = prova.ponto_de_partida(raiz, base)
    if not ponto:
        return {"erro": f"sem merge-base entre {base} e HEAD"}, None
    return {"base": base, "ponto": ponto[:12]}, ponto


# --- texto sem comentário nem string -----------------------------------------------

def _fim_do_comentario(texto: str, i: int, linguagem: str) -> int | None:
    """Onde termina o comentário que começa em `i` — ou None se não começa um ali."""
    if linguagem == "python":
        inicio_de_linha = texto[i] == "#"
    else:
        inicio_de_linha = texto.startswith("//", i)
        if texto.startswith("/*", i):
            fim = texto.find("*/", i + 2)
            return len(texto) if fim == -1 else fim + 2
    if not inicio_de_linha:
        return None
    fim = texto.find("\n", i)
    return len(texto) if fim == -1 else fim


def _regras_da_string(texto: str, i: int, linguagem: str) -> tuple[str, bool, bool]:
    """(o que fecha, a barra escapa?, a quebra de linha encerra?) da string em `i`."""
    c = texto[i]
    if linguagem == "python" and texto.startswith(c * 3, i):
        return c * 3, True, False
    if c == "`":  # template do JS escapa; string crua do Go, não
        return c, linguagem != "go", False
    return c, True, True


def _fim_da_string(texto: str, i: int, linguagem: str) -> tuple[int, int]:
    """(início do miolo, posição da aspa que fecha) da string que começa em `i`."""
    fecha, escapa, quebra_encerra = _regras_da_string(texto, i, linguagem)
    j = i + len(fecha)
    while j < len(texto) and not texto.startswith(fecha, j):
        if escapa and texto[j] == "\\":
            j += 1
        elif quebra_encerra and texto[j] == "\n":
            break
        j += 1
    return i + len(fecha), j


def limpar(texto: str, linguagem: str) -> str:
    """Mesmo comprimento e mesmas quebras de linha; comentário e miolo de string viram
    espaço (as aspas ficam). Operador dentro de string não é operador."""
    saida = list(texto)

    def apagar(a: int, b: int) -> None:
        for k in range(a, min(b, len(texto))):
            if saida[k] != "\n":
                saida[k] = " "

    i = 0
    while i < len(texto):
        fim = _fim_do_comentario(texto, i, linguagem)
        if fim is not None:
            apagar(i, fim)
            i = fim
        elif texto[i] in "'\"`":
            miolo, fecha = _fim_da_string(texto, i, linguagem)
            apagar(miolo, fecha)
            i = fecha + (miolo - i)
        else:
            i += 1
    return "".join(saida)


# --- funções: extração e complexidade ----------------------------------------------

class Funcao:
    __slots__ = ("arquivo", "nome", "inicio", "fim", "complexidade", "impressoes")

    def __init__(self, arquivo: str, nome: str, inicio: int, fim: int,
                 complexidade: int, impressoes: set[str]):
        self.arquivo, self.nome = arquivo, nome
        self.inicio, self.fim = inicio, fim
        self.complexidade, self.impressoes = complexidade, impressoes

    @property
    def linhas(self) -> int:
        return self.fim - self.inicio + 1

    def toca(self, linhas: set[int]) -> bool:
        return any(self.inicio <= l <= self.fim for l in linhas)


DECISOES_PYTHON = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp,
                   *((ast.match_case,) if hasattr(ast, "match_case") else ()))


def _decisoes_do_no(n: ast.AST) -> int:
    if isinstance(n, DECISOES_PYTHON):
        return 1
    if isinstance(n, ast.BoolOp):
        return len(n.values) - 1
    if isinstance(n, ast.comprehension):
        return len(n.ifs)
    return 0


def complexidade_python(no: ast.AST) -> int:
    return 1 + sum(_decisoes_do_no(n) for n in ast.walk(no))


IGNORADOS_NA_FORMA = (ast.expr_context, ast.operator, ast.cmpop, ast.boolop, ast.unaryop)


def _rotulo(no: ast.AST) -> str:
    """Tipo do nó, operador e nome chamado. Nome local, atributo e literal ficam de fora."""
    rotulo = type(no).__name__
    if isinstance(no, ast.Call):
        f = no.func
        rotulo += f"[{getattr(f, 'id', None) or getattr(f, 'attr', '')}]"
    if hasattr(no, "op"):
        rotulo += f"<{type(no.op).__name__}>"
    if isinstance(no, ast.Compare):
        rotulo += "<" + ",".join(type(o).__name__ for o in no.ops) + ">"
    return rotulo


def forma_python(no: ast.AST, impressoes: set[str]) -> str:
    """Forma normalizada da subárvore; guarda a impressão de cada subárvore com filhos."""
    if isinstance(no, ast.Name):
        return "N"
    if isinstance(no, ast.Constant):
        return "C"
    filhos = [forma_python(f, impressoes) for f in ast.iter_child_nodes(no)
              if not isinstance(f, IGNORADOS_NA_FORMA)]
    if not filhos:
        return _rotulo(no)
    forma = f"{_rotulo(no)}({','.join(filhos)})"
    impressoes.add(hashlib.sha1(forma.encode()).hexdigest()[:16])
    return forma


def _sem_docstring(corpo: list[ast.stmt]) -> list[ast.stmt]:
    primeiro = corpo[0] if corpo else None
    eh_doc = (isinstance(primeiro, ast.Expr) and isinstance(primeiro.value, ast.Constant)
              and isinstance(primeiro.value.value, str))
    return corpo[1:] if eh_doc else corpo


def _funcao_python(rel: str, no: ast.AST, prefixo: str) -> Funcao:
    impressoes: set[str] = set()
    for instrucao in _sem_docstring(list(no.body)):
        forma_python(instrucao, impressoes)
    inicio = min([no.lineno] + [d.lineno for d in no.decorator_list])
    return Funcao(rel, prefixo + no.name, inicio, no.end_lineno or no.lineno,
                  complexidade_python(no), impressoes)


def _visitar_python(rel: str, no: ast.AST, prefixo: str, saida: list[Funcao]) -> None:
    for filho in ast.iter_child_nodes(no):
        if isinstance(filho, (ast.FunctionDef, ast.AsyncFunctionDef)):
            saida.append(_funcao_python(rel, filho, prefixo))
        elif isinstance(filho, ast.ClassDef):
            _visitar_python(rel, filho, f"{prefixo}{filho.name}.", saida)
        else:
            _visitar_python(rel, filho, prefixo, saida)


def funcoes_python(rel: str, texto: str) -> list[Funcao] | None:
    try:
        arvore = ast.parse(texto)
    except (SyntaxError, ValueError):
        return None
    saida: list[Funcao] = []
    _visitar_python(rel, arvore, "", saida)
    return saida


PALAVRAS_RESERVADAS = {
    "if", "for", "while", "switch", "catch", "function", "return", "else", "do", "try",
    "new", "typeof", "await", "yield", "case", "default", "break", "continue", "throw",
    "const", "let", "var", "class", "import", "export", "from", "of", "in", "instanceof",
    "true", "false", "null", "undefined", "this", "super", "async", "static", "get", "set",
    "func", "go", "defer", "select", "range", "type", "struct", "interface", "map",
    "chan", "package", "nil", "fallthrough", "goto",
}

INICIO_JS = [
    re.compile(r"\b(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*(?:<[^>{}]*>)?\s*\("),
    re.compile(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:async\s*)?"
               r"(?:function\b[^(]*\(|\([^()]*(?:\([^()]*\)[^()]*)*\)\s*(?::[^=>{]+)?=>\s*\{|"
               r"[A-Za-z_$][\w$]*\s*=>\s*\{)"),
    re.compile(r"^[ \t]*(?:(?:public|private|protected|static|async|override|readonly)\s+)*"
               r"(?:get\s+|set\s+)?\*?\s*([A-Za-z_$][\w$]*)\s*(?:<[^>{}]*>)?\s*\([^;{}]*\)"
               r"\s*(?::\s*[^;{}=]+)?\s*\{", re.M),
]
INICIO_GO = re.compile(r"^func\s*(?:\(\s*\w*\s*\*?\s*([A-Za-z_]\w*)[^)]*\)\s*)?"
                       r"([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*\(", re.M)

DECISOES = {
    "js": re.compile(r"\b(?:if|for|while|case|catch)\b|&&|\|\||\?\?|\?\.|\?(?![:.])"),
    "go": re.compile(r"\b(?:if|for|case)\b|&&|\|\|"),
}
TOKEN = re.compile(r"[A-Za-z_$][\w$]*|\d[\w.]*|'[^'\n]*'|\"[^\"\n]*\"|`[^`]*`|"
                   r"===|!==|==|!=|<=|>=|&&|\|\||\?\?|=>|\+\+|--|[-+*/%<>=!&|^~?:.,;(){}\[\]]")


def _fecha(limpo: str, abre: int, par: str = "{}") -> int | None:
    profundidade = 0
    for k in range(abre, len(limpo)):
        profundidade += {par[0]: 1, par[1]: -1}.get(limpo[k], 0)
        if profundidade == 0:
            return k
    return None


def _abre_do_corpo(limpo: str, m: re.Match, linguagem: str) -> int:
    """A chave que abre o corpo: depois dos parâmetros, não dentro deles. No Go, a do fim
    de linha — `interface{}` no parâmetro ou no retorno não é o corpo (o gofmt garante)."""
    fim = m.end() - 1
    if limpo[fim] == "(":
        fim = _fecha(limpo, fim, "()") or fim
    if linguagem == "go":
        m_corpo = re.compile(r"\{[ \t]*\n").search(limpo, fim)
        return m_corpo.start() if m_corpo else -1
    return limpo.find("{", fim)


def _normalizar_token(lista: list[str], i: int) -> str:
    t = lista[i]
    if t[0] in "'\"`" or t[0].isdigit():
        return "C"
    if not re.match(r"[A-Za-z_$]", t):
        return t
    chamada = i + 1 < len(lista) and lista[i + 1] == "("
    return t if (t in PALAVRAS_RESERVADAS or chamada) else "N"


def impressoes_tokens(trecho: str, k: int = 4) -> set[str]:
    lista = TOKEN.findall(trecho)
    tokens = [_normalizar_token(lista, i) for i in range(len(lista))]
    return {hashlib.sha1(" ".join(tokens[i:i + k]).encode()).hexdigest()[:16]
            for i in range(max(0, len(tokens) - k + 1))}


def _nome_do_inicio(m: re.Match, linguagem: str) -> str | None:
    if linguagem == "go":
        receptor, nome = m.group(1), m.group(2)
        return f"{receptor}.{nome}" if receptor else nome
    nome = m.group(1)
    return None if nome in PALAVRAS_RESERVADAS else nome


def _candidatas(limpo: str, linguagem: str) -> list[tuple[int, int, str]]:
    """(início, chave que fecha, nome) de cada função que algum padrão reconhece."""
    candidatas = []
    for padrao in (INICIO_JS if linguagem == "js" else [INICIO_GO]):
        for m in padrao.finditer(limpo):
            nome = _nome_do_inicio(m, linguagem)
            abre = _abre_do_corpo(limpo, m, linguagem)
            fecha = _fecha(limpo, abre) if nome and abre >= 0 else None
            if fecha is not None:
                candidatas.append((m.start(), fecha, nome))
    return sorted(candidatas, key=lambda c: (c[0], -c[1]))


def _externas(candidatas: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    """Só as de fora: aninhada (ou a mesma achada por outro padrão) conta para a que a contém."""
    externas: list[tuple[int, int, str]] = []
    for c in candidatas:
        if not externas or c[0] > externas[-1][1]:
            externas.append(c)
    return externas


def funcoes_texto(rel: str, texto: str, linguagem: str) -> list[Funcao]:
    limpo = limpar(texto, linguagem)
    saida = []
    for ini, fim, nome in _externas(_candidatas(limpo, linguagem)):
        corpo = limpo[ini:fim + 1]
        corpo = corpo[corpo.find("{"):]
        saida.append(Funcao(rel, nome, limpo.count("\n", 0, ini) + 1,
                            limpo.count("\n", 0, fim) + 1,
                            1 + len(DECISOES[linguagem].findall(corpo)),
                            impressoes_tokens(corpo)))
    return saida


def funcoes_do_texto(rel: str, texto: str) -> list[Funcao] | None:
    linguagem = linguagem_de(rel)
    if linguagem == "python":
        return funcoes_python(rel, texto)
    return funcoes_texto(rel, texto, linguagem)


def funcoes_de(raiz: Path, rel: str) -> list[Funcao] | None:
    try:
        texto = (raiz / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return funcoes_do_texto(rel, texto)


def complexidade_na_base(raiz: Path, ponto: str, rel: str) -> dict[str, int]:
    """{nome: CC} das funções do arquivo como estava no ponto de partida do diff."""
    r = prova.git(raiz, "show", f"{ponto}:{rel}", timeout=30)
    fs = funcoes_do_texto(rel, r.stdout) if r.returncode == 0 else None
    return {f.nome: f.complexidade for f in fs or []}


# --- cobertura -------------------------------------------------------------------

class Cobertura:
    """{arquivo: (linhas cobertas, linhas instrumentadas)}, com o caminho normalizado."""

    def __init__(self, raiz: Path):
        self.raiz, self.mapa = raiz, {}

    def somar(self, caminho: str, linha: int, coberta: bool) -> None:
        cob, inst = self.mapa.setdefault(self._rel(caminho), (set(), set()))
        inst.add(linha)
        if coberta:
            cob.add(linha)

    def _rel(self, caminho: str) -> str:
        c = caminho.replace("\\", "/")
        if not os.path.isabs(c):
            return c
        try:
            return Path(c).resolve().relative_to(self.raiz).as_posix()
        except ValueError:
            return c

    def do_arquivo(self, rel: str) -> tuple[set[int], set[int]]:
        if rel in self.mapa:
            return self.mapa[rel]
        for chave, valor in self.mapa.items():
            if chave.endswith("/" + rel) or rel.endswith("/" + chave):
                return valor
        return set(), set()  # o relatório não menciona: 0% (mesma regra do crapper)


def _ler_json(cob: Cobertura, texto: str) -> None:
    for rel, d in (json.loads(texto).get("files") or {}).items():
        for linha in d.get("executed_lines", []):
            cob.somar(rel, linha, True)
        for linha in d.get("missing_lines", []):
            cob.somar(rel, linha, False)


def _ler_xml(cob: Cobertura, texto: str) -> None:
    for classe in ET.fromstring(texto).iter("class"):
        for linha in classe.iter("line"):
            cob.somar(classe.get("filename", ""), int(linha.get("number", 0)),
                      int(linha.get("hits", 0)) > 0)


def _modulo_go(raiz: Path) -> str:
    gomod = raiz / "go.mod"
    m = re.search(r"^module\s+(\S+)", gomod.read_text(encoding="utf-8"), re.M) \
        if gomod.is_file() else None
    return m.group(1) + "/" if m else ""


def _ler_go(cob: Cobertura, texto: str) -> None:
    modulo = _modulo_go(cob.raiz)
    for linha in texto.splitlines()[1:]:
        m = re.match(r"(.+):(\d+)\.\d+,(\d+)\.\d+ \d+ (\d+)$", linha.strip())
        if not m:
            continue
        rel = m.group(1)[len(modulo):] if modulo and m.group(1).startswith(modulo) else m.group(1)
        for n in range(int(m.group(2)), int(m.group(3)) + 1):
            cob.somar(rel, n, int(m.group(4)) > 0)


def _ler_lcov(cob: Cobertura, texto: str) -> None:
    rel = None
    for linha in texto.splitlines():
        if linha.startswith("SF:"):
            rel = linha[3:].strip()
        elif linha.startswith("DA:") and rel:
            numero, _, hits = linha[3:].partition(",")
            if numero.isdigit():
                cob.somar(rel, int(numero), hits.split(",")[0].strip() not in ("0", ""))


def formato_da_cobertura(nome: str, texto: str) -> str:
    if nome.endswith(".json"):
        return "coverage.py json"
    if texto.lstrip().startswith("<"):
        return "cobertura xml"
    return "go coverprofile" if texto.startswith("mode:") else "lcov"


LEITORES = {"coverage.py json": _ler_json, "cobertura xml": _ler_xml,
            "go coverprofile": _ler_go, "lcov": _ler_lcov}


def ler_cobertura(raiz: Path, arquivo: Path) -> tuple[Cobertura, str]:
    texto = arquivo.read_text(encoding="utf-8", errors="replace")
    formato = formato_da_cobertura(arquivo.name, texto)
    cob = Cobertura(raiz)
    LEITORES[formato](cob, texto)
    return cob, formato


def localizar_cobertura(raiz: Path, explicito: str | None) -> Path | None:
    candidatos = [explicito] if explicito else RELATORIOS_DE_COBERTURA
    for c in candidatos:
        p = Path(c) if os.path.isabs(c) else raiz / c
        if p.is_file():
            return p
    return None


def crap(cc: int, cobertura: float) -> float:
    return round(cc ** 2 * (1 - cobertura) ** 3 + cc, 1)


def _carregar_cobertura(raiz: Path, explicito: str | None, alteradas: dict,
                        r: dict) -> Cobertura | None:
    info = r["cobertura"]
    relatorio = localizar_cobertura(raiz, explicito)
    if relatorio is None:
        info["aviso"] = f"relatório {explicito} não encontrado" if explicito else None
        return None
    try:
        cob, info["formato"] = ler_cobertura(raiz, relatorio)
    except (OSError, ValueError, ET.ParseError) as e:
        info["aviso"] = f"não consegui ler {relatorio.name}: {e}"
        return None
    info["arquivo"] = (relatorio.relative_to(raiz).as_posix()
                       if relatorio.is_relative_to(raiz) else str(relatorio))
    mais_novo = max(((raiz / a).stat().st_mtime for a in alteradas), default=0)
    if mais_novo > relatorio.stat().st_mtime:
        info["aviso"] = ("relatório de cobertura mais antigo que o código tocado — "
                         "rode a suíte com cobertura de novo")
    return cob


def _veredicto(item: dict, limite: float) -> dict:
    """Reprova pela regra cheia; a catraca só alivia quem ainda reprovaria e não piorou."""
    normal = _veredicto_pela_regra(item, limite)
    cc, base = item["complexidade"], item["cc_base"]
    legado = base is not None and base >= limite and cc <= base
    if normal["veredicto"] == "acima_do_limite" and legado:
        return {"veredicto": "legado_acima",
                "motivo": f"já tinha CC {base} na base e não piorou — a catraca não deixa subir"}
    return normal


def _veredicto_pela_regra(item: dict, limite: float) -> dict:
    cc = item["complexidade"]
    if item["crap"] is not None:
        return {"veredicto": "acima_do_limite" if item["crap"] >= limite else "ok"}
    if cc >= limite:
        return {"veredicto": "acima_do_limite",
                "motivo": "sem cobertura, mas CRAP ≥ CC e a CC já está no limite"}
    return {"veredicto": "indeterminado",
            "motivo": "sem relatório de cobertura — CRAP não calculado"}


def avaliar_funcao(f: Funcao, cob: Cobertura | None, limite: float,
                   cc_base: int | None = None) -> dict:
    item = {"arquivo": f.arquivo, "funcao": f.nome, "linha": f.inicio, "fim": f.fim,
            "complexidade": f.complexidade, "cc_base": cc_base, "cobertura": None,
            "crap": None}
    if cob is not None:
        cobertas, instrumentadas = cob.do_arquivo(f.arquivo)
        vao = set(range(f.inicio, f.fim + 1))
        medidas = instrumentadas & vao
        fracao = len(cobertas & vao) / len(medidas) if medidas else 0.0
        item["cobertura"], item["crap"] = round(fracao * 100, 1), crap(f.complexidade, fracao)
    item.update(_veredicto(item, limite))
    return item


def analisar_crap(raiz: Path, base: str | None, cobertura: str | None,
                  limite: float) -> dict:
    r, ponto = preparar_diff(raiz, base)
    if ponto is None:
        return r
    r.update({"limite": limite, "funcoes": [], "nao_analisados": [],
              "cobertura": {"arquivo": None, "formato": None, "aviso": None}})
    alteradas = linhas_alteradas(raiz, ponto)
    cob = _carregar_cobertura(raiz, cobertura, alteradas, r)
    for rel in sorted(alteradas):
        funcoes = funcoes_de(raiz, rel)
        if funcoes is None:
            r["nao_analisados"].append({"arquivo": rel, "motivo": "não consegui ler a estrutura"})
            continue
        na_base = complexidade_na_base(raiz, ponto, rel)
        r["funcoes"] += [avaliar_funcao(f, cob, limite, na_base.get(f.nome)) for f in funcoes
                         if f.toca(alteradas[rel])]
    r["funcoes"].sort(key=lambda i: (-(i["crap"] or i["complexidade"]), i["arquivo"], i["linha"]))
    return r


# --- duplicação ------------------------------------------------------------------

def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _unidades(raiz: Path, linguagem: str, alteradas: dict, min_linhas: int,
              r: dict) -> list[Funcao]:
    todas: list[Funcao] = []
    for rel in arquivos_de_producao(raiz, linguagem):
        fs = funcoes_de(raiz, rel)
        if fs is None and rel in alteradas:
            r["nao_analisados"].append({"arquivo": rel, "motivo": "não consegui ler a estrutura"})
        todas.extend(f for f in fs or [] if f.linhas >= min_linhas and f.impressoes)
    return todas


def _tocada(f: Funcao, alteradas: dict) -> bool:
    return f.arquivo in alteradas and f.toca(alteradas[f.arquivo])


def _par(f: Funcao, g: Funcao, nota: float, alteradas: dict) -> dict:
    return {"nota": round(nota, 3),
            "tocada": {"arquivo": f.arquivo, "funcao": f.nome, "linha": f.inicio},
            "outra": {"arquivo": g.arquivo, "funcao": g.nome, "linha": g.inicio,
                      "tocada": _tocada(g, alteradas)}}


def pares_duplicados(tocadas: list[Funcao], todas: list[Funcao], limite: float,
                     alteradas: dict) -> list[dict]:
    pares, vistos = [], set()
    for f in tocadas:
        for g in todas:
            chave = frozenset([(f.arquivo, f.inicio), (g.arquivo, g.inicio)])
            if g is f or chave in vistos:
                continue
            vistos.add(chave)
            nota = jaccard(f.impressoes, g.impressoes)
            if nota >= limite:
                pares.append(_par(f, g, nota, alteradas))
    return pares


def analisar_duplicacao(raiz: Path, base: str | None, limite: float,
                        min_linhas: int) -> dict:
    r, ponto = preparar_diff(raiz, base)
    if ponto is None:
        return r
    r.update({"limite": limite, "min_linhas": min_linhas, "pares": [], "tocadas": 0,
              "comparadas": 0, "nao_analisados": []})
    alteradas = linhas_alteradas(raiz, ponto)
    for linguagem in sorted({linguagem_de(rel) for rel in alteradas}):
        todas = _unidades(raiz, linguagem, alteradas, min_linhas, r)
        tocadas = [f for f in todas if _tocada(f, alteradas)]
        r["tocadas"] += len(tocadas)
        r["comparadas"] += len(todas)
        r["pares"] += pares_duplicados(tocadas, todas, limite, alteradas)
    r["pares"].sort(key=lambda p: (-p["nota"], p["tocada"]["arquivo"], p["tocada"]["linha"]))
    return r


# --- mutação: sítios -------------------------------------------------------------

RELACIONAIS = [("==", "!="), ("!=", "=="), ("<=", "<"), (">=", ">"), ("<", "<="), (">", ">=")]
ARITMETICOS = [("+", "-"), ("-", "+")]
OPERADORES = {
    "python": RELACIONAIS + ARITMETICOS + [("and", "or"), ("or", "and"),
                                           ("True", "False"), ("False", "True")],
    "js": [("===", "!=="), ("!==", "===")] + RELACIONAIS + ARITMETICOS +
          [("&&", "||"), ("||", "&&"), ("true", "false"), ("false", "true")],
    "go": RELACIONAIS + ARITMETICOS + [("&&", "||"), ("||", "&&"),
                                       ("true", "false"), ("false", "true")],
}
LINHA_SEM_MUTACAO = re.compile(r"\s*(?:def|class|import|from|@)\b")


def padrao_operador(op: str) -> re.Pattern:
    if op[0].isalpha():
        return re.compile(rf"(?<![\w.]){re.escape(op)}(?!\w)")
    # Operador simbólico só cercado de espaço: evita `->`, `=>`, genérico `Array<T>`,
    # `+=`, `++`, sinal de número negativo e o meio de um operador maior.
    return re.compile(rf"(?<=\s){re.escape(op)}(?=\s)")


def _sitios_da_linha(rel: str, n: int, linha_limpa: str, linguagem: str) -> list[dict]:
    if linguagem == "python" and LINHA_SEM_MUTACAO.match(linha_limpa):
        return []
    return [{"arquivo": rel, "linha": n, "coluna": m.start(), "original": de,
             "mutado": para, "tipo": "operador"}
            for de, para in OPERADORES[linguagem]
            for m in padrao_operador(de).finditer(linha_limpa)]


def sitios_de_mutacao(raiz: Path, rel: str, linhas: set[int]) -> list[dict]:
    linguagem = linguagem_de(rel)
    try:
        texto = (raiz / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    limpo = limpar(texto, linguagem).split("\n")
    sitios = [s for n in sorted(linhas) if n <= len(limpo)
              for s in _sitios_da_linha(rel, n, limpo[n - 1], linguagem)]
    sitios += RETORNOS.get(linguagem, lambda *_: [])(rel, texto, limpo, linhas)
    unicos = {}
    for s in sitios:  # um sítio por posição
        unicos.setdefault((s["linha"], s["coluna"]), s)
    return [unicos[k] for k in sorted(unicos)]


def coluna_de(linha: str, deslocamento_em_bytes: int) -> int:
    """Coluna em caracteres a partir do deslocamento em bytes UTF-8 que o `ast` devolve."""
    return len(linha.encode("utf-8")[:deslocamento_em_bytes].decode("utf-8", errors="ignore"))


def _retorno_mutavel(no: ast.AST, linhas: set[int]) -> bool:
    return (isinstance(no, ast.Return) and no.value is not None and no.lineno in linhas
            and no.lineno == no.end_lineno
            and not (isinstance(no.value, ast.Constant) and no.value.value is None))


def retornos_python(rel: str, texto: str, limpo: list[str], linhas: set[int]) -> list[dict]:
    """`return x` → `return None`: se a suíte passa com a função devolvendo nada, ela não
    testa o que a função devolve. Só retorno de uma linha, para o mutante compilar."""
    try:
        arvore = ast.parse(texto)
    except (SyntaxError, ValueError):
        return []
    originais = texto.split("\n")
    saida = []
    for no in filter(lambda n: _retorno_mutavel(n, linhas), ast.walk(arvore)):
        linha = originais[no.lineno - 1]
        col, fim = coluna_de(linha, no.col_offset), coluna_de(linha, no.end_col_offset)
        saida.append({"arquivo": rel, "linha": no.lineno, "coluna": col,
                      "original": linha[col:fim], "mutado": "return None", "tipo": "retorno"})
    return saida


RETORNO_JS = re.compile(r"(\s*)return\s+([^;]+);\s*$")


def _expressao_fechada(expr: str) -> bool:
    return all(expr.count(a) == expr.count(b) for a, b in ("()", "[]", "{}"))


def retornos_js(rel: str, texto: str, limpo: list[str], linhas: set[int]) -> list[dict]:
    """O mesmo para JS/TS com `return undefined`. Go fica de fora: o tipo não deixa."""
    originais = texto.split("\n")
    saida = []
    for n, linha in enumerate(limpo, 1):
        m = RETORNO_JS.match(linha) if n in linhas else None
        if not m or m.group(2).strip() in ("undefined", "null") or \
                not _expressao_fechada(m.group(2)):
            continue
        col = len(m.group(1))
        saida.append({"arquivo": rel, "linha": n, "coluna": col,
                      "original": originais[n - 1][col:m.end(2)].rstrip(),
                      "mutado": "return undefined", "tipo": "retorno"})
    return saida


RETORNOS = {"python": retornos_python, "js": retornos_js}


def _espalhar(itens: list[dict], quantos: int) -> list[dict]:
    if len(itens) <= quantos:
        return list(itens)
    passo = len(itens) / quantos
    return [itens[int(i * passo)] for i in range(quantos)]


def escolher(sitios: list[dict], maximo: int) -> list[dict]:
    """Até metade das vagas para retornos, o resto para operadores espalhados pelo diff;
    vaga que um lado não usa passa para o outro. Determinístico, sem sorteio."""
    retornos = [s for s in sitios if s["tipo"] == "retorno"]
    operadores = [s for s in sitios if s["tipo"] == "operador"]
    vagas_operadores = min(len(operadores), maximo - min(len(retornos), maximo // 2))
    vagas_retornos = min(len(retornos), maximo - vagas_operadores)
    escolhidos = _espalhar(retornos, vagas_retornos) + _espalhar(operadores, vagas_operadores)
    return sorted(escolhidos, key=lambda s: (s["arquivo"], s["linha"], s["coluna"]))


# --- mutação: execução -----------------------------------------------------------

def _comando_js(raiz: Path) -> str | None:
    for nome, cmd in (("vitest", "npx vitest run"), ("jest", "npx jest --ci")):
        if prova._tem_dependencia_js(raiz, nome):
            return cmd
    try:
        scripts = json.loads((raiz / "package.json").read_text(encoding="utf-8")).get("scripts")
    except (OSError, ValueError):
        return None
    return "npm test --silent" if (scripts or {}).get("test") else None


def _comando_python(_raiz: Path) -> str:
    if prova._tem_modulo("pytest"):
        return f"{sys.executable} -m pytest -q -x -p no:cacheprovider"
    return f"{sys.executable} -m unittest discover -q"


COMANDOS = {"python": _comando_python, "js": _comando_js, "go": lambda _r: "go test ./..."}


def comando_da_suite(raiz: Path, linguagens: set[str]) -> str | None:
    """Deduz a suíte quando há uma linguagem só; diff misto pede `--comando`."""
    if len(linguagens) != 1:
        return None
    return COMANDOS[next(iter(linguagens))](raiz)


def aplicar_mutacao(texto: str, sitio: dict) -> str | None:
    linhas = texto.split("\n")
    i, col, original = sitio["linha"] - 1, sitio["coluna"], sitio["original"]
    if i >= len(linhas) or linhas[i][col:col + len(original)] != original:
        return None
    linhas[i] = linhas[i][:col] + sitio["mutado"] + linhas[i][col + len(original):]
    return "\n".join(linhas)


def _matar_grupo(p: subprocess.Popen) -> None:
    try:
        os.killpg(p.pid, 9)
    except OSError:
        p.kill()
    p.wait()


def rodar(cmd: str, cwd: Path, tempo: float) -> tuple[str, float, list[str]]:
    """(passou|falhou|tempo, segundos, últimas linhas). Estourou o tempo, o grupo de
    processos inteiro morre: com `shell=True`, matar só o shell deixa a suíte órfã."""
    inicio = time.monotonic()
    ambiente = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as saida:
        p = subprocess.Popen(cmd, shell=True, cwd=str(cwd), stdout=saida,
                             stderr=subprocess.STDOUT, env=ambiente, start_new_session=True)
        try:
            estado = "passou" if p.wait(timeout=tempo) == 0 else "falhou"
        except subprocess.TimeoutExpired:
            _matar_grupo(p)
            estado = "tempo"
        saida.seek(0)
        ultimas = [l for l in saida.read().strip().splitlines() if l.strip()][-3:]
    return estado, time.monotonic() - inicio, ultimas


def montar_worktree(raiz: Path, destino: Path) -> str | None:
    """Worktree no HEAD com o não-commitado aplicado — o código de agora, não o de ontem."""
    r = prova.git(raiz, "worktree", "add", "--detach", str(destino), "HEAD", timeout=120)
    if r.returncode != 0:
        return f"não consegui criar worktree: {r.stderr.strip()[:200]}"
    remendo = prova.git(raiz, "diff", "HEAD", "--binary", timeout=60).stdout
    p = subprocess.run(["git", "-C", str(destino), "apply", "--whitespace=nowarn", "-"],
                       input=remendo, capture_output=True, text=True, timeout=60) \
        if remendo.strip() else None
    if p is not None and p.returncode != 0:
        return f"não consegui aplicar o diff não-commitado: {p.stderr.strip()[:200]}"
    for rel in prova.nao_rastreados(raiz):
        (destino / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(raiz / rel, destino / rel)
    prova.ligar_dependencias(raiz, destino)
    return None


def julgar(sitio: dict, arvore: Path, comando: str, tempo: float) -> dict:
    """Aplica UM mutante, roda a suíte, desfaz. Falhou ou estourou o tempo: morto."""
    item = dict(sitio)
    alvo = arvore / sitio["arquivo"]
    original = alvo.read_text(encoding="utf-8")
    mutado = aplicar_mutacao(original, sitio)
    if mutado is None:
        return {**item, "resultado": "nao_executado",
                "motivo": "o texto do sítio não confere no worktree"}
    try:
        alvo.write_text(mutado, encoding="utf-8")
        estado, _, _ = rodar(comando, arvore, tempo)
    finally:
        alvo.write_text(original, encoding="utf-8")
    item["resultado"] = "sobreviveu" if estado == "passou" else "morto"
    if estado == "tempo":
        item["motivo"] = "estourou o tempo — conta como morto"
    return item


def placar(mutantes: list[dict]) -> dict:
    p = {"mortos": 0, "sobreviventes": 0, "nao_executados": 0, "pontuacao": None}
    chave = {"morto": "mortos", "sobreviveu": "sobreviventes"}
    for m in mutantes:
        p[chave.get(m["resultado"], "nao_executados")] += 1
    julgados = p["mortos"] + p["sobreviventes"]
    p["pontuacao"] = round(p["mortos"] / julgados, 3) if julgados else None
    return p


def _funcao_do_sitio(funcoes: dict, s: dict) -> str | None:
    return next((f.nome for f in funcoes.get(s["arquivo"], [])
                 if f.inicio <= s["linha"] <= f.fim), None)


def executar_mutantes(r: dict, escolhidos: list[dict], arvore: Path, funcoes: dict,
                      limites: tuple[int, int]) -> None:
    """Linha de base verde primeiro; depois um mutante por vez, até o teto da rodada."""
    tempo_limite, teto = limites
    inicio = time.monotonic()
    estado, duracao, ultimas = rodar(r["comando"], arvore, tempo_limite)
    r["base_segundos"] = round(duracao, 1)
    if estado != "passou":
        motivo = "estourou o tempo" if estado == "tempo" else "base vermelha"
        r["erro"] = (f"a suíte não passa sem mutação nenhuma ({motivo}) — mutante só se "
                     "julga contra suíte verde")
        r["ultimas_linhas"] = ultimas
        return
    por_mutante = min(tempo_limite, max(30.0, duracao * 3))
    for s in escolhidos:
        s = {**s, "funcao": _funcao_do_sitio(funcoes, s)}
        estourou = time.monotonic() - inicio > teto
        r["mutantes"].append({**s, "resultado": "nao_executado",
                              "motivo": f"teto de {teto}s da rodada atingido"} if estourou
                             else julgar(s, arvore, r["comando"], por_mutante))


def analisar_mutacao(raiz: Path, base: str | None, comando: str | None, maximo: int,
                     tempo_limite: int, teto: int) -> dict:
    r, ponto = preparar_diff(raiz, base)
    if ponto is None:
        return r
    alteradas = linhas_alteradas(raiz, ponto)
    sitios = [s for rel in sorted(alteradas) for s in sitios_de_mutacao(raiz, rel, alteradas[rel])]
    escolhidos = escolher(sitios, maximo)
    r.update({"sitios": len(sitios), "mutantes": [], "placar": placar([]),
              "comando": comando or comando_da_suite(
                  raiz, {linguagem_de(s["arquivo"]) for s in escolhidos})})
    if not escolhidos:
        r["aviso"] = "nenhum sítio de mutação nas linhas tocadas — nada a mutar"
        return r
    if not r["comando"]:
        r["erro"] = "não sei rodar a suíte deste projeto — passe --comando"
        return r
    funcoes = {rel: funcoes_de(raiz, rel) or [] for rel in alteradas}
    tmp = Path(tempfile.mkdtemp(prefix="kairos-forge-mutacao-"))
    try:
        r["erro"] = montar_worktree(raiz, tmp / "arvore")
        if not r["erro"]:
            executar_mutantes(r, escolhidos, tmp / "arvore", funcoes, (tempo_limite, teto))
    finally:
        prova.git(raiz, "worktree", "remove", "--force", str(tmp / "arvore"), timeout=60)
        prova.git(raiz, "worktree", "prune")
        shutil.rmtree(tmp, ignore_errors=True)
    if not r["erro"]:
        del r["erro"]
    r["placar"] = placar(r["mutantes"])
    return r


# --- impressão -------------------------------------------------------------------

ICONES = {"ok": "✅", "acima_do_limite": "❌", "indeterminado": "⚠️ ", "legado_acima": "🟡",
          "morto": "✅", "sobreviveu": "❌", "nao_executado": "⚠️ "}


def _cabecalho(r: dict, titulo: str) -> None:
    print(f"{titulo} — diff contra {r.get('base')} (desde {r.get('ponto')})")


def _avisos(r: dict) -> None:
    for n in r.get("nao_analisados", []):
        print(f"   ⚠️  {n['arquivo']}: {n['motivo']}")


def _linha_crap(f: dict) -> str:
    valor = f"CRAP {f['crap']}" if f["crap"] is not None else "CRAP —"
    cobertura = f"{f['cobertura']}%" if f["cobertura"] is not None else "—"
    base = f", na base {f['cc_base']}" if f.get("cc_base") not in (None, f["complexidade"]) else ""
    return (f"   {ICONES[f['veredicto']]} {f['arquivo']}:{f['linha']} {f['funcao']} — "
            f"{valor} (CC {f['complexidade']}{base}, cobertura {cobertura})")


def imprimir_crap(r: dict) -> None:
    _cabecalho(r, "📐 CRAP por função tocada")
    cob = r["cobertura"]
    print(f"   cobertura: {cob['arquivo'] or 'nenhum relatório'}"
          + (f" ({cob['formato']})" if cob["formato"] else ""))
    if cob["aviso"]:
        print(f"   ⚠️  {cob['aviso']}")
    for f in r["funcoes"]:
        print(_linha_crap(f))
    _avisos(r)
    acima = sum(f["veredicto"] == "acima_do_limite" for f in r["funcoes"])
    legado = sum(f["veredicto"] == "legado_acima" for f in r["funcoes"])
    print(f"\n   {len(r['funcoes'])} funções tocadas, {acima} no limite {r['limite']:g} "
          f"ou acima" + (f", {legado} de legado que não piorou" if legado else ""))


def imprimir_duplicacao(r: dict) -> None:
    _cabecalho(r, "🧬 Duplicação estrutural das funções tocadas")
    print(f"   {r['tocadas']} tocadas, comparadas com {r['comparadas']} "
          f"(≥ {r['min_linhas']} linhas, limite {r['limite']:g})")
    for p in r["pares"]:
        t, o = p["tocada"], p["outra"]
        print(f"   ❌ {p['nota']:.2f}  {t['arquivo']}:{t['linha']} {t['funcao']}  ≈  "
              f"{o['arquivo']}:{o['linha']} {o['funcao']}")
    _avisos(r)
    print("" if r["pares"] else "   nenhum par no limite ou acima")


def _linha_mutante(m: dict) -> str:
    onde = f"{m['arquivo']}:{m['linha']}" + (f" {m['funcao']}" if m.get("funcao") else "")
    motivo = f" — {m['motivo']}" if m.get("motivo") else ""
    return f"   {ICONES[m['resultado']]} {onde}: `{m['original']}` → `{m['mutado']}`{motivo}"


def imprimir_mutacao(r: dict) -> None:
    _cabecalho(r, "🧪 Mutação nas linhas tocadas")
    base = f" ({r['base_segundos']}s sem mutação)" if "base_segundos" in r else ""
    print(f"   suíte: {r.get('comando') or '—'}{base}")
    if r.get("aviso"):
        print(f"   {r['aviso']}")
    for m in r["mutantes"]:
        print(_linha_mutante(m))
    p = r["placar"]
    nota = f"{p['pontuacao']:.0%}" if p["pontuacao"] is not None else "—"
    print(f"\n   {p['mortos']} mortos, {p['sobreviventes']} sobreviventes, "
          f"{p['nao_executados']} não executados — pontuação {nota} "
          f"({len(r['mutantes'])} de {r.get('sitios', 0)} sítios)")


# --- CLI -------------------------------------------------------------------------

def opcao(args: list[str], nome: str, tipo=str, padrao=None):
    if nome not in args or args.index(nome) + 1 >= len(args):
        return padrao
    valor = args[args.index(nome) + 1]
    try:
        return tipo(valor)
    except ValueError:
        sys.exit(f"erro: {nome} recebeu '{valor}', que não é um número")


def _crap_cli(raiz: Path, base, args) -> tuple[dict, bool]:
    r = analisar_crap(raiz, base, opcao(args, "--cobertura"), opcao(args, "--limite", float, 10.0))
    return r, any(f["veredicto"] == "acima_do_limite" for f in r.get("funcoes", []))


def _duplicacao_cli(raiz: Path, base, args) -> tuple[dict, bool]:
    r = analisar_duplicacao(raiz, base, opcao(args, "--limite", float, 0.8),
                            opcao(args, "--min-linhas", int, 4))
    return r, bool(r.get("pares"))


def _mutacao_cli(raiz: Path, base, args) -> tuple[dict, bool]:
    r = analisar_mutacao(raiz, base, opcao(args, "--comando"), opcao(args, "--max", int, 25),
                         opcao(args, "--tempo-limite", int, 300), opcao(args, "--teto", int, 900))
    return r, bool(r.get("placar", {}).get("sobreviventes"))


SUBCOMANDOS = {"crap": (_crap_cli, imprimir_crap),
               "duplicacao": (_duplicacao_cli, imprimir_duplicacao),
               "mutacao": (_mutacao_cli, imprimir_mutacao)}


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] not in SUBCOMANDOS:
        print(__doc__.strip())
        return 1
    analisar, imprimir = SUBCOMANDOS[args[0]]
    raiz = prova.raiz_git()
    if raiz is None:
        print("🚫 fora de um repositório git — sem diff não há o que medir", file=sys.stderr)
        return 1
    r, falhou = analisar(raiz, opcao(args, "--base"), args)
    if "--json" in args:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif r.get("erro"):
        print(f"🚫 {r['erro']}", *r.get("ultimas_linhas", []), sep="\n   ", file=sys.stderr)
    else:
        imprimir(r)
    return 1 if (r.get("erro") or falhou) else 0


if __name__ == "__main__":
    sys.exit(main())
