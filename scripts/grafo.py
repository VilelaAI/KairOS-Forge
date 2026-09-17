#!/usr/bin/env python3
"""grafo.py — parte determinística do grafo de conhecimento (skill mapear-conhecimento).

O pipeline do grafo segue o princípio: modelo só onde há julgamento (extrair,
resolver, sintetizar, responder); lógica determinística pro resto. Este script
é o "resto":

    validar        contrato dos JSONL (arestas órfãs, aliases ambíguos) — usável como gate
    diagnosticar   nós, arestas, componentes conexos, densidade, compressão, hubs
    subgrafo       serializa vizinhança k-hop de uma entidade como triplas
    amostrar       nó aleatório com arestas e perfil, pra amostra humana
    codigo         camada de CÓDIGO (ADR-0041): arestas importa/herda/instancia
                   extraídas por AST/regex — sem modelo — para codigo.jsonl
    contexto       vizinhança de 1 salto de um ARQUIVO na camada de código: quem
                   importa, o que importa, quem herda — mais as entidades de
                   conhecimento que citam o arquivo como fonte

Uso:
    python3 scripts/grafo.py validar [--dir .agents/grafo]
    python3 scripts/grafo.py diagnosticar [--dir .agents/grafo]
    python3 scripts/grafo.py subgrafo "API de relatórios" [--saltos 2] [--dir .agents/grafo]
    python3 scripts/grafo.py amostrar [--dir .agents/grafo]
    python3 scripts/grafo.py codigo [--raiz .] [--dir .agents/grafo]
    python3 scripts/grafo.py contexto src/api/relatorios.py [--saltos 1] [--json]

Por que uma camada de código separada: o grafo de conhecimento é extraído de documentos
pelo modelo (precisão > recall, com julgamento). Dependência entre arquivos não precisa
de julgamento — o import está no texto — e é o que o modelo mais erra ao navegar: o
paper *The Navigation Paradox* (2026) mostra que grafo de imports ganha 23 pontos sobre
busca textual nas tarefas em que o arquivo certo não compartilha vocabulário com a
pergunta. `codigo.jsonl` é regenerável a qualquer momento e nunca passa pelo modelo.

Somente stdlib. Leitura apenas, com uma exceção declarada: `codigo` escreve
`codigo.jsonl` e `codigo.meta.json` no diretório do grafo — e só eles.
"""
from collections import Counter, defaultdict, deque
from pathlib import Path
import argparse
import ast
import json
import os
import random
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone

CAMPOS_ENTIDADE = {"nome", "tipo", "descricao", "fontes"}
CAMPOS_RELACAO = {"origem", "predicado", "destino", "fonte"}
CAMPOS_ALIAS = {"alias", "canonico"}


def ler_jsonl(path: Path, campos: set, erros: list) -> list:
    """Lê um JSONL validando presença dos campos obrigatórios por linha."""
    registros = []
    if not path.exists():
        return registros
    for n, linha in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        linha = linha.strip()
        if not linha:
            continue
        try:
            reg = json.loads(linha)
        except json.JSONDecodeError as exc:
            erros.append(f"{path.name}:{n}: JSON inválido ({exc})")
            continue
        faltando = campos - set(reg)
        if faltando:
            erros.append(f"{path.name}:{n}: campos ausentes: {', '.join(sorted(faltando))}")
            continue
        registros.append(reg)
    return registros


class Grafo:
    def __init__(self, diretorio: Path):
        self.dir = diretorio
        self.erros: list = []
        self.entidades = ler_jsonl(diretorio / "entidades.jsonl", CAMPOS_ENTIDADE, self.erros)
        self.relacoes = ler_jsonl(diretorio / "relacoes.jsonl", CAMPOS_RELACAO, self.erros)
        self.aliases = ler_jsonl(diretorio / "aliases.jsonl", CAMPOS_ALIAS, self.erros)
        self.nomes = {e["nome"] for e in self.entidades}
        self.mapa_alias: dict = {}
        for a in self.aliases:
            existente = self.mapa_alias.get(a["alias"])
            if existente and existente != a["canonico"]:
                self.erros.append(
                    f"aliases.jsonl: alias ambíguo '{a['alias']}' → '{existente}' e '{a['canonico']}'"
                )
            self.mapa_alias[a["alias"]] = a["canonico"]

    def resolver(self, nome: str) -> str:
        return self.mapa_alias.get(nome, nome)

    def validar_estrutura(self) -> list:
        erros = list(self.erros)
        for a in self.aliases:
            if a["canonico"] not in self.nomes:
                erros.append(f"aliases.jsonl: canônico inexistente '{a['canonico']}' (alias '{a['alias']}')")
        for i, r in enumerate(self.relacoes, 1):
            for ponta in ("origem", "destino"):
                nome = self.resolver(r[ponta])
                if nome not in self.nomes:
                    erros.append(
                        f"relacoes.jsonl: aresta órfã — {ponta} '{r[ponta]}' não resolve "
                        f"para entidade (relação {i}: {r['origem']} --[{r['predicado']}]--> {r['destino']})"
                    )
            if not r.get("fonte"):
                erros.append(f"relacoes.jsonl: relação {i} sem fonte")
        vistos = Counter(e["nome"] for e in self.entidades)
        for nome, qtd in vistos.items():
            if qtd > 1:
                erros.append(f"entidades.jsonl: entidade duplicada '{nome}' ({qtd}x)")
        return erros

    def vizinhos(self) -> dict:
        adj = defaultdict(set)
        for r in self.relacoes:
            o, d = self.resolver(r["origem"]), self.resolver(r["destino"])
            adj[o].add(d)
            adj[d].add(o)
        return adj

    def componentes(self) -> list:
        adj = self.vizinhos()
        visitados, comps = set(), []
        for no in sorted(self.nomes):
            if no in visitados:
                continue
            fila, comp = deque([no]), set()
            while fila:
                atual = fila.popleft()
                if atual in comp:
                    continue
                comp.add(atual)
                fila.extend(adj[atual] - comp)
            visitados |= comp
            comps.append(comp)
        return sorted(comps, key=len, reverse=True)

    def graus(self) -> Counter:
        graus = Counter()
        for r in self.relacoes:
            graus[self.resolver(r["origem"])] += 1
            graus[self.resolver(r["destino"])] += 1
        return graus


def slug(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "-" for c in base.lower()).strip("-")


def cmd_validar(g: Grafo) -> int:
    erros = g.validar_estrutura()
    if erros:
        print(f"❌ {len(erros)} erro(s) de contrato em {g.dir}:")
        for e in erros:
            print(f"  - {e}")
        return 1
    print(f"✅ Contrato ok: {len(g.entidades)} entidades, {len(g.relacoes)} relações, {len(g.aliases)} aliases.")
    return 0


def cmd_diagnosticar(g: Grafo) -> int:
    n_nos, n_arestas = len(g.entidades), len(g.relacoes)
    if n_nos == 0:
        print("Grafo vazio — rode /kairos-forge:mapear-conhecimento construir.")
        return 1
    comps = g.componentes()
    graus = g.graus()
    formas = len(g.nomes) + len(g.aliases)
    compressao = formas / n_nos if n_nos else 0.0
    densidade = n_arestas / n_nos if n_nos else 0.0
    por_tipo = Counter(e["tipo"] for e in g.entidades)

    print(f"# Diagnóstico do grafo — {g.dir}")
    print(f"Nós: {n_nos} | Arestas: {n_arestas} | Aliases: {len(g.aliases)}")
    print(f"Densidade (arestas/nós): {densidade:.2f}  [saudável: ~1.0–2.0]")
    print(f"Taxa de compressão (formas/canônicos): {compressao:.2f}  [>2.0 = muita variação de nome]")
    print(f"Componentes conexos: {len(comps)} (maior: {len(comps[0])} nós)"
          f"{'  ⚠️ ilhas — investigar resolução' if len(comps) > 1 else '  ✅'}")
    if len(comps) > 1:
        for c in comps[1:6]:
            print(f"  ilha: {', '.join(sorted(c)[:5])}{'…' if len(c) > 5 else ''}")
    print("Top 5 hubs por grau:")
    for nome, grau in graus.most_common(5):
        marca = " (perfil recomendado)" if grau >= 3 and not (g.dir / "perfis" / f"{slug(nome)}.md").exists() else ""
        print(f"  {grau:>3}  {nome}{marca}")
    print("Entidades por tipo: " + ", ".join(f"{t}={q}" for t, q in por_tipo.most_common()))
    erros = g.validar_estrutura()
    if erros:
        print(f"⚠️ Contrato com {len(erros)} erro(s) — rode o subcomando validar para a lista.")
        return 1
    return 0


def cmd_subgrafo(g: Grafo, semente: str, saltos: int) -> int:
    centro = g.resolver(semente)
    if centro not in g.nomes:
        candidatos = [n for n in sorted(g.nomes) if semente.lower() in n.lower()]
        print(f"Entidade '{semente}' não encontrada no grafo.")
        if candidatos:
            print("Parecidas: " + "; ".join(candidatos[:8]))
        return 1
    adj = g.vizinhos()
    nos, fronteira = {centro}, {centro}
    for _ in range(saltos):
        proxima = set()
        for n in fronteira:
            proxima |= adj[n]
        fronteira = proxima - nos
        nos |= fronteira
    linhas = sorted(
        f"({g.resolver(r['origem'])}) --[{r['predicado']}]--> ({g.resolver(r['destino'])}) [fonte: {r['fonte']}]"
        for r in g.relacoes
        if g.resolver(r["origem"]) in nos and g.resolver(r["destino"]) in nos
    )
    print(f"# Subgrafo de '{centro}' ({saltos} salto(s)): {len(nos)} nós, {len(linhas)} arestas")
    for linha in dict.fromkeys(linhas):
        print(linha)
    return 0


def cmd_mermaid(g: Grafo, semente: str, saltos: int) -> int:
    """Exporta o subgrafo da semente como flowchart Mermaid (colável em SPEC/RFC/ADR)."""
    centro = g.resolver(semente)
    if centro not in g.nomes:
        candidatos = [n for n in sorted(g.nomes) if semente.lower() in n.lower()]
        print(f"Entidade '{semente}' não encontrada no grafo.")
        if candidatos:
            print("Parecidas: " + "; ".join(candidatos[:8]))
        return 1
    adj = g.vizinhos()
    nos, fronteira = {centro}, {centro}
    for _ in range(saltos):
        proxima = set()
        for n in fronteira:
            proxima |= adj[n]
        fronteira = proxima - nos
        nos |= fronteira
    arestas = dict.fromkeys(
        (g.resolver(r["origem"]), r["predicado"], g.resolver(r["destino"]))
        for r in g.relacoes
        if g.resolver(r["origem"]) in nos and g.resolver(r["destino"]) in nos
    )
    if len(arestas) > 60:
        print(f"Subgrafo com {len(arestas)} arestas — vira espaguete renderizado. "
              f"Reduza --saltos ou escolha semente mais específica.")
        return 1
    ids = {nome: f"n{i}" for i, nome in enumerate(sorted(nos))}
    print("```mermaid")
    print("flowchart LR")
    print(f'    {ids[centro]}["{centro}"]:::centro')
    for nome in sorted(nos - {centro}):
        print(f'    {ids[nome]}["{nome}"]')
    for origem, predicado, destino in arestas:
        print(f"    {ids[origem]} -->|{predicado}| {ids[destino]}")
    print("    classDef centro stroke-width:3px")
    print("```")
    print(f"\n%% Subgrafo de '{centro}' ({saltos} salto(s)): {len(nos)} nós, "
          f"{len(arestas)} arestas — gerado por grafo.py, fonte da verdade é o grafo.")
    return 0


def cmd_amostrar(g: Grafo) -> int:
    if not g.entidades:
        print("Grafo vazio — nada a amostrar.")
        return 1
    ent = random.choice(g.entidades)
    nome = ent["nome"]
    print(f"# Amostra humana — {nome} ({ent['tipo']})")
    print(f"Descrição: {ent['descricao']}")
    print(f"Fontes: {', '.join(ent.get('fontes', []))}")
    perfil = g.dir / "perfis" / f"{slug(nome)}.md"
    print(f"Perfil: {perfil if perfil.exists() else '(sem perfil)'}")
    print("Arestas:")
    achou = False
    for r in g.relacoes:
        if nome in (g.resolver(r["origem"]), g.resolver(r["destino"])):
            achou = True
            print(f"  ({g.resolver(r['origem'])}) --[{r['predicado']}]--> ({g.resolver(r['destino'])}) [fonte: {r['fonte']}]")
    if not achou:
        print("  (nó isolado — candidato a revisão)")
    print("\nCheque 2-3 arestas contra os documentos-fonte. Se alguma não se explicar,")
    print("a compreensão do grafo ficou pra trás do conteúdo — registre em GRAFO.md.")
    return 0


# --- camada de código (ADR-0041) -------------------------------------------------------

IGNORAR_DIRS = {".git", "node_modules", ".venv", "venv", "vendor", "dist", "build",
                ".worktrees", "__pycache__", ".agents", ".cursor", ".codex", ".opencode",
                "coverage", ".next", ".turbo", ".cache", "target", ".tox", ".mypy_cache"}
EXT_PY = {".py"}
EXT_JS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
EXT_GO = {".go"}
PREDICADOS_CODIGO = ("importa", "herda", "instancia")

RE_JS_IMPORT = re.compile(
    r"""(?:^|\n)\s*(?:import|export)\s+(?P<bind>[^'"\n;]*?)\s*from\s*['"](?P<spec>[^'"]+)['"]"""
    r"""|(?:^|\n)\s*import\s*['"](?P<spec2>[^'"]+)['"]"""
    r"""|require\(\s*['"](?P<spec3>[^'"]+)['"]\s*\)"""
    r"""|import\(\s*['"](?P<spec4>[^'"]+)['"]\s*\)""")
RE_JS_EXTENDS = re.compile(r"\bclass\s+\w+\s+extends\s+([A-Za-z_$][\w$]*)")
RE_JS_NEW = re.compile(r"\bnew\s+([A-Za-z_$][\w$]*)\s*[(<]")
RE_GO_IMPORT = re.compile(r'"([^"]+)"')


def arquivos_de_codigo(raiz: Path) -> list[str]:
    """Arquivos rastreados pelo git (respeita .gitignore); sem git, os.walk com exclusões."""
    exts = EXT_PY | EXT_JS | EXT_GO
    try:
        r = subprocess.run(["git", "-C", str(raiz), "ls-files", "-z"], capture_output=True,
                           text=True, timeout=60)
        if r.returncode == 0:
            nomes = [n for n in r.stdout.split("\0") if n]
            return sorted(n for n in nomes if Path(n).suffix in exts
                          and not (set(Path(n).parts[:-1]) & IGNORAR_DIRS))
    except (OSError, subprocess.SubprocessError):
        pass
    achados = []
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if d not in IGNORAR_DIRS]
        for f in filenames:
            if Path(f).suffix in exts:
                achados.append(str((Path(dirpath) / f).relative_to(raiz)).replace("\\", "/"))
    return sorted(achados)


def _normalizar(caminho: Path) -> str:
    return os.path.normpath(str(caminho)).replace("\\", "/").lstrip("./") or "."


def _resolver_python(rel: str, modulo: str | None, nivel: int, nomes: list[str],
                     conjunto: set[str], raizes: list[str]) -> list[str]:
    """Candidatos de arquivo para um import Python; devolve os que existem no projeto."""
    partes = modulo.split(".") if modulo else []
    bases: list[Path]
    if nivel > 0:
        pacote = Path(rel).parent
        for _ in range(nivel - 1):
            pacote = pacote.parent
        bases = [pacote]
    else:
        bases = [Path(r) for r in raizes]
    achados = []
    for base in bases:
        alvo = base.joinpath(*partes) if partes else base
        candidatos = []
        # `from a.b import c` — c pode ser submódulo; `import a.b` — a/b.py ou a/b/__init__.py
        for nome in nomes or [None]:
            if nome:
                candidatos += [alvo / f"{nome}.py", alvo / nome / "__init__.py"]
        if partes:
            candidatos += [alvo.with_suffix(".py"), alvo / "__init__.py"]
        for c in candidatos:
            n = _normalizar(c)
            if n in conjunto and n != rel and n not in achados:
                achados.append(n)
    return achados


def extrair_python(raiz: Path, rel: str, conjunto: set[str]) -> tuple[list[dict], int]:
    try:
        arvore = ast.parse((raiz / rel).read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError, OSError):
        return [], 0
    raizes = ["."]
    if (raiz / "src").is_dir():
        raizes.append("src")
    pai = Path(rel).parent
    while str(pai) not in (".", ""):
        raizes.append(str(pai))
        pai = pai.parent
    arestas, externos = [], 0
    nome_para_arquivo: dict[str, str] = {}
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for a in no.names:
                alvos = _resolver_python(rel, a.name, 0, [], conjunto, raizes)
                if alvos:
                    arestas.append((alvos[0], "importa", no.lineno))
                    nome_para_arquivo[(a.asname or a.name).split(".")[0]] = alvos[0]
                else:
                    externos += 1
        elif isinstance(no, ast.ImportFrom):
            nomes = [a.name for a in no.names if a.name != "*"]
            alvos = _resolver_python(rel, no.module, no.level, nomes, conjunto, raizes)
            if alvos:
                for alvo in alvos:
                    arestas.append((alvo, "importa", no.lineno))
                # símbolo importado → arquivo do módulo (o primeiro candidato de módulo)
                modulo_arq = _resolver_python(rel, no.module, no.level, [], conjunto, raizes)
                for a in no.names:
                    destino = None
                    sub = _resolver_python(rel, no.module, no.level, [a.name], conjunto, raizes)
                    if sub:
                        destino = sub[0]
                    elif modulo_arq:
                        destino = modulo_arq[0]
                    if destino:
                        nome_para_arquivo[a.asname or a.name] = destino
            elif no.module or no.level:
                externos += 1
    for no in ast.walk(arvore):
        if isinstance(no, ast.ClassDef):
            for base in no.bases:
                raiz_nome = base.id if isinstance(base, ast.Name) else (
                    base.value.id if isinstance(base, ast.Attribute)
                    and isinstance(base.value, ast.Name) else None)
                if raiz_nome in nome_para_arquivo:
                    arestas.append((nome_para_arquivo[raiz_nome], "herda", no.lineno))
        elif isinstance(no, ast.Call):
            f = no.func
            nome = f.id if isinstance(f, ast.Name) else (
                f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                else None)
            if nome in nome_para_arquivo and nome[:1].isupper():
                arestas.append((nome_para_arquivo[nome], "instancia", no.lineno))
    return [{"origem": rel, "predicado": p, "destino": d, "fonte": f"{rel}:{ln}"}
            for d, p, ln in arestas], externos


def _resolver_js(rel: str, spec: str, conjunto: set[str], aliases: dict[str, str]) -> str | None:
    if spec.startswith("."):
        base = Path(rel).parent / spec
    else:
        prefixo = next((a for a in aliases if spec == a.rstrip("/") or spec.startswith(a)), None)
        if prefixo is None:
            return None
        base = Path(aliases[prefixo]) / spec[len(prefixo):]
    candidatos = [base] + [base.with_suffix(base.suffix + e) if base.suffix not in EXT_JS
                           else base for e in sorted(EXT_JS)]
    candidatos += [base / f"index{e}" for e in sorted(EXT_JS)]
    for c in candidatos:
        n = _normalizar(c)
        if n in conjunto and n != rel:
            return n
    return None


def _aliases_js(raiz: Path) -> dict[str, str]:
    """Aliases de caminho comuns: `@/` e `~/` → src/ (ou raiz), lidos do tsconfig se houver."""
    aliases = {}
    for nome in ("tsconfig.json", "jsconfig.json"):
        p = raiz / nome
        if not p.is_file():
            continue
        try:
            texto = re.sub(r"//[^\n]*|/\*.*?\*/", "", p.read_text(encoding="utf-8"), flags=re.S)
            cfg = json.loads(texto)
            opts = cfg.get("compilerOptions", {}) or {}
            base = opts.get("baseUrl", ".")
            for chave, alvos in (opts.get("paths") or {}).items():
                if chave.endswith("/*") and alvos:
                    aliases[chave[:-1]] = _normalizar(Path(base) / alvos[0].rstrip("*"))
        except Exception:
            continue
    for atalho in ("@/", "~/"):
        if atalho not in aliases:
            aliases[atalho] = "src" if (raiz / "src").is_dir() else "."
    return aliases


def extrair_js(raiz: Path, rel: str, conjunto: set[str], aliases: dict[str, str]) -> tuple[list[dict], int]:
    try:
        texto = (raiz / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], 0
    arestas, externos = [], 0
    nome_para_arquivo: dict[str, str] = {}
    for m in RE_JS_IMPORT.finditer(texto):
        spec = m.group("spec") or m.group("spec2") or m.group("spec3") or m.group("spec4")
        destino = _resolver_js(rel, spec, conjunto, aliases)
        linha = texto.count("\n", 0, m.start()) + 1
        if destino is None:
            if spec.startswith(".") or any(spec.startswith(a) for a in aliases):
                externos += 1
            continue
        arestas.append((destino, "importa", linha))
        bind = m.group("bind") or ""
        for nome in re.findall(r"[A-Za-z_$][\w$]*", bind.replace("type ", " ")):
            if nome not in ("as", "default", "type"):
                nome_para_arquivo[nome] = destino
    for m in RE_JS_EXTENDS.finditer(texto):
        if m.group(1) in nome_para_arquivo:
            arestas.append((nome_para_arquivo[m.group(1)], "herda",
                            texto.count("\n", 0, m.start()) + 1))
    for m in RE_JS_NEW.finditer(texto):
        if m.group(1) in nome_para_arquivo:
            arestas.append((nome_para_arquivo[m.group(1)], "instancia",
                            texto.count("\n", 0, m.start()) + 1))
    return [{"origem": rel, "predicado": p, "destino": d, "fonte": f"{rel}:{ln}"}
            for d, p, ln in arestas], externos


def _modulo_go(raiz: Path) -> str | None:
    p = raiz / "go.mod"
    if not p.is_file():
        return None
    m = re.search(r"^module\s+(\S+)", p.read_text(encoding="utf-8", errors="replace"), re.M)
    return m.group(1) if m else None


def extrair_go(raiz: Path, rel: str, pacotes: set[str], modulo: str | None) -> tuple[list[dict], int]:
    if not modulo:
        return [], 0
    try:
        texto = (raiz / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], 0
    m = re.search(r"^import\s*(\([^)]*\)|\"[^\"]+\")", texto, re.M | re.S)
    if not m:
        return [], 0
    arestas, externos = [], 0
    pacote_origem = _normalizar(Path(rel).parent)
    for spec in RE_GO_IMPORT.findall(m.group(1)):
        if spec == modulo or spec.startswith(modulo + "/"):
            dir_ = spec[len(modulo):].lstrip("/") or "."
            if dir_ in pacotes and dir_ != pacote_origem:
                linha = texto.count("\n", 0, texto.find(f'"{spec}"')) + 1
                arestas.append({"origem": rel, "predicado": "importa",
                                "destino": dir_ + "/", "fonte": f"{rel}:{linha}"})
            else:
                externos += 1
    return arestas, externos


def cmd_codigo(raiz: Path, diretorio: Path) -> int:
    arquivos = arquivos_de_codigo(raiz)
    if not arquivos:
        print(f"nenhum arquivo .py/.js/.ts/.go em {raiz} — nada a extrair")
        return 1
    conjunto = set(arquivos)
    pacotes_go = {_normalizar(Path(a).parent) for a in arquivos if Path(a).suffix in EXT_GO}
    modulo_go = _modulo_go(raiz)
    aliases_js = _aliases_js(raiz)
    arestas: list[dict] = []
    externos = 0
    por_linguagem = Counter()
    for rel in arquivos:
        suf = Path(rel).suffix
        if suf in EXT_PY:
            por_linguagem["python"] += 1
            novas, ext = extrair_python(raiz, rel, conjunto)
        elif suf in EXT_JS:
            por_linguagem["js/ts"] += 1
            novas, ext = extrair_js(raiz, rel, conjunto, aliases_js)
        else:
            por_linguagem["go"] += 1
            novas, ext = extrair_go(raiz, rel, pacotes_go, modulo_go)
        externos += ext
        vistos = set()
        for a in novas:  # uma aresta por (origem, predicado, destino); a fonte é a 1ª ocorrência
            chave = (a["origem"], a["predicado"], a["destino"])
            if chave not in vistos:
                vistos.add(chave)
                arestas.append(a)

    diretorio.mkdir(parents=True, exist_ok=True)
    with (diretorio / "codigo.jsonl").open("w", encoding="utf-8") as fh:
        for a in arestas:
            fh.write(json.dumps(a, ensure_ascii=False) + "\n")
    entrada = Counter(a["destino"] for a in arestas if a["predicado"] == "importa")
    por_predicado = Counter(a["predicado"] for a in arestas)
    meta = {
        "construido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raiz": str(raiz), "arquivos": len(arquivos), "por_linguagem": dict(por_linguagem),
        "arestas": len(arestas), "por_predicado": dict(por_predicado),
        "imports_nao_resolvidos": externos,
        "hubs": [{"arquivo": k, "importado_por": v} for k, v in entrada.most_common(10)],
        "versao_esquema_codigo": 1,
    }
    (diretorio / "codigo.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"🧩 Camada de código — {len(arquivos)} arquivos "
          f"({', '.join(f'{k} {v}' for k, v in por_linguagem.items())}) → {len(arestas)} arestas")
    print("   " + " · ".join(f"{p}: {por_predicado.get(p, 0)}" for p in PREDICADOS_CODIGO)
          + f" · imports não resolvidos (stdlib, externos ou fora da raiz): {externos}")
    sem_aresta = len(conjunto - {a["origem"] for a in arestas} - {a["destino"] for a in arestas})
    print(f"   arquivos sem nenhuma aresta: {sem_aresta}")
    if entrada:
        print("   mais importados:")
        for k, v in entrada.most_common(8):
            print(f"     {v:>4}  {k}")
    print(f"   gravado em {diretorio / 'codigo.jsonl'} (+ codigo.meta.json)")
    return 0


def carregar_codigo(diretorio: Path) -> list[dict]:
    erros: list = []
    return ler_jsonl(diretorio / "codigo.jsonl", CAMPOS_RELACAO, erros)


def cmd_contexto(diretorio: Path, arquivo: str, saltos: int, como_json: bool) -> int:
    arestas = carregar_codigo(diretorio)
    if not arestas:
        print(f"sem camada de código em {diretorio} — rode `grafo.py codigo` primeiro")
        return 1
    alvo = _normalizar(Path(arquivo))
    nos = {a["origem"] for a in arestas} | {a["destino"] for a in arestas}
    if alvo not in nos:
        parecidos = [n for n in nos if n.endswith("/" + Path(alvo).name) or Path(alvo).name in n][:5]
        print(f"`{alvo}` não está na camada de código." +
              (f" Parecidos: {', '.join(parecidos)}" if parecidos else ""))
        return 1
    saida = defaultdict(list)
    entrada = defaultdict(list)
    for a in arestas:
        saida[a["origem"]].append(a)
        entrada[a["destino"]].append(a)
    # BFS nos dois sentidos até `saltos`
    fronteira, vistos, camadas = {alvo}, {alvo}, []
    for _ in range(saltos):
        proxima = set()
        for n in fronteira:
            proxima |= {a["destino"] for a in saida[n]} | {a["origem"] for a in entrada[n]}
        proxima -= vistos
        if not proxima:
            break
        camadas.append(sorted(proxima))
        vistos |= proxima
        fronteira = proxima
    r = {
        "arquivo": alvo,
        "importado_por": sorted({a["origem"] for a in entrada[alvo] if a["predicado"] == "importa"}),
        "importa": sorted({a["destino"] for a in saida[alvo] if a["predicado"] == "importa"}),
        "herda_de": sorted({a["destino"] for a in saida[alvo] if a["predicado"] == "herda"}),
        "herdado_por": sorted({a["origem"] for a in entrada[alvo] if a["predicado"] == "herda"}),
        "instancia": sorted({a["destino"] for a in saida[alvo] if a["predicado"] == "instancia"}),
        "instanciado_por": sorted({a["origem"] for a in entrada[alvo] if a["predicado"] == "instancia"}),
        "alcance_por_salto": [len(c) for c in camadas],
        "vizinhanca": camadas,
    }
    # ponte com o grafo de conhecimento: entidades que citam o arquivo como fonte
    erros: list = []
    entidades = ler_jsonl(diretorio / "entidades.jsonl", CAMPOS_ENTIDADE, erros)
    r["entidades_de_conhecimento"] = sorted(
        e["nome"] for e in entidades
        if any(alvo == _normalizar(Path(str(f))) or str(f).endswith(alvo) for f in (e.get("fontes") or [])))
    meta_p = diretorio / "codigo.meta.json"
    if meta_p.is_file():
        try:
            r["camada_construida_em"] = json.loads(meta_p.read_text(encoding="utf-8")).get("construido_em")
        except Exception:
            pass
    if como_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    print(f"🧭 Contexto arquitetural — {alvo}"
          + (f"  (camada de {r['camada_construida_em'][:10]})" if r.get("camada_construida_em") else ""))
    for rotulo, chave in (("importado por", "importado_por"), ("importa", "importa"),
                          ("herda de", "herda_de"), ("herdado por", "herdado_por"),
                          ("instancia", "instancia"), ("instanciado por", "instanciado_por")):
        if r[chave]:
            print(f"   {rotulo} ({len(r[chave])}):")
            for n in r[chave][:20]:
                print(f"     · {n}")
            if len(r[chave]) > 20:
                print(f"     … e mais {len(r[chave]) - 20}")
    if saltos > 1 and len(camadas) > 1:
        print(f"   alcance: {' → '.join(str(n) for n in r['alcance_por_salto'])} arquivos por salto")
    if r["entidades_de_conhecimento"]:
        print(f"   no grafo de conhecimento: {', '.join(r['entidades_de_conhecimento'][:8])}")
    if not r["importado_por"]:
        print("   ninguém importa este arquivo: ponto de entrada, script, teste — ou código morto.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Parte determinística do grafo de conhecimento.")
    parser.add_argument("comando", choices=["validar", "diagnosticar", "subgrafo", "amostrar",
                                            "mermaid", "codigo", "contexto"])
    parser.add_argument("entidade", nargs="?",
                        help="entidade-semente (subgrafo/mermaid) ou arquivo (contexto)")
    parser.add_argument("--saltos", type=int, default=None,
                        help="raio (default 2 no subgrafo/mermaid, 1 no contexto)")
    parser.add_argument("--dir", default=".agents/grafo", help="diretório do grafo (default .agents/grafo)")
    parser.add_argument("--raiz", default=".", help="raiz do código a extrair (codigo; default .)")
    parser.add_argument("--json", action="store_true", help="saída em JSON (contexto)")
    args = parser.parse_args()

    diretorio = Path(args.dir)
    if args.comando == "codigo":
        return cmd_codigo(Path(args.raiz).resolve(), diretorio)
    if args.comando == "contexto":
        if not args.entidade:
            print('Informe o arquivo: grafo.py contexto "src/x.py" [--saltos 1]')
            return 2
        return cmd_contexto(diretorio, args.entidade, args.saltos or 1, args.json)
    if args.saltos is None:
        args.saltos = 2
    if not diretorio.exists():
        print(f"Diretório {diretorio} não existe. Rode /kairos-forge:mapear-conhecimento construir "
              f"(ou /kairos-forge:onboardar num projeto novo).")
        return 1
    g = Grafo(diretorio)
    if args.comando == "validar":
        return cmd_validar(g)
    if args.comando == "diagnosticar":
        return cmd_diagnosticar(g)
    if args.comando in ("subgrafo", "mermaid"):
        if not args.entidade:
            print(f"Informe a entidade-semente: grafo.py {args.comando} \"<entidade>\" [--saltos 2]")
            return 2
        if args.comando == "mermaid":
            return cmd_mermaid(g, args.entidade, args.saltos)
        return cmd_subgrafo(g, args.entidade, args.saltos)
    return cmd_amostrar(g)


if __name__ == "__main__":
    sys.exit(main())
