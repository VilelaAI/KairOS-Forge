#!/usr/bin/env python3
"""grafo.py — parte determinística do grafo de conhecimento (skill mapear-conhecimento).

O pipeline do grafo segue o princípio: modelo só onde há julgamento (extrair,
resolver, sintetizar, responder); lógica determinística pro resto. Este script
é o "resto":

    validar        contrato dos JSONL (arestas órfãs, aliases ambíguos) — usável como gate
    diagnosticar   nós, arestas, componentes conexos, densidade, compressão, hubs
    subgrafo       serializa vizinhança k-hop de uma entidade como triplas
    amostrar       nó aleatório com arestas e perfil, pra amostra humana

Uso:
    python3 scripts/grafo.py validar [--dir .agents/grafo]
    python3 scripts/grafo.py diagnosticar [--dir .agents/grafo]
    python3 scripts/grafo.py subgrafo "API de relatórios" [--saltos 2] [--dir .agents/grafo]
    python3 scripts/grafo.py amostrar [--dir .agents/grafo]

Somente stdlib. Não modifica nenhum arquivo — leitura apenas.
"""
from collections import Counter, defaultdict, deque
from pathlib import Path
import argparse
import json
import random
import sys
import unicodedata

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Parte determinística do grafo de conhecimento.")
    parser.add_argument("comando", choices=["validar", "diagnosticar", "subgrafo", "amostrar", "mermaid"])
    parser.add_argument("entidade", nargs="?", help="entidade-semente (para subgrafo e mermaid)")
    parser.add_argument("--saltos", type=int, default=2, help="raio do subgrafo (default 2)")
    parser.add_argument("--dir", default=".agents/grafo", help="diretório do grafo (default .agents/grafo)")
    args = parser.parse_args()

    diretorio = Path(args.dir)
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
