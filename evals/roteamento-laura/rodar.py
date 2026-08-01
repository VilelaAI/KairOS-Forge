#!/usr/bin/env python3
"""rodar.py — executa o eval de roteamento da Laura headless (ADR-0025).

Até a v0.18 este gold set existia e era apurado **à mão**, em sessão, pela Alice.
A fábrica pregava "set the bar at the eval, not the demo" e media o próprio eval
por impressão — o CI só verificava que os ids citados existiam em `agents/`.

Este script fecha o dogfooding: apresenta cada `pedido` à Laura via `claude -p`,
registra qual agente ela acionaria, compara com o `esperado` e falha abaixo do
limiar. Acerto = a Laura acionar **qualquer um** dos ids aceitáveis (casos com
mais de um id são fronteiras onde múltiplas respostas são defensáveis).

Uso:
    python3 evals/roteamento-laura/rodar.py                    # tudo, limiar 90%
    python3 evals/roteamento-laura/rodar.py --amostra 15       # subconjunto barato
    python3 evals/roteamento-laura/rodar.py --limiar 85 --json

Sem o CLI `claude` disponível, sai com 0 e diz que pulou — CI sem chave não
quebra o build por ausência de credencial (isso seria falso vermelho, e falso
vermelho treina o time a ignorar o vermelho).

Só stdlib.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
GOLD = AQUI / "gold.jsonl"
LIMIAR_PADRAO = 90.0
TIMEOUT = 120

INSTRUCAO = (
    "Você é Laura, Tech Lead da fábrica kairos-forge, que tem estes agentes:\n"
    "{catalogo}\n\n"
    "Pedido do usuário: \"{pedido}\"\n\n"
    "Responda APENAS com o id do agente que você acionaria. Um id, nada mais."
)


def catalogo() -> tuple[str, list[str]]:
    """Lista `id — description curta` para a Laura escolher, derivada de agents/."""
    linhas, ids = [], []
    for p in sorted((RAIZ / "agents").glob("*.md")):
        texto = p.read_text(encoding="utf-8")
        m = re.search(r"^description:\s*(.+)$", texto, re.M)
        desc = (m.group(1) if m else "")[:110]
        linhas.append(f"- {p.stem}: {desc}")
        ids.append(p.stem)
    return "\n".join(linhas), ids


def casos() -> list[dict]:
    saida = []
    for i, linha in enumerate(GOLD.read_text(encoding="utf-8").splitlines(), 1):
        if linha.strip():
            try:
                saida.append(json.loads(linha))
            except json.JSONDecodeError as e:
                sys.exit(f"gold.jsonl linha {i}: JSON inválido — {e}")
    return saida


def extrair_id(resposta: str, ids: list[str]) -> str | None:
    """Tolerante com formato, rigoroso com conteúdo: aceita o id em qualquer lugar."""
    limpo = resposta.strip().strip("`\"' .\n")
    if limpo in ids:
        return limpo
    achados = [i for i in ids if re.search(rf"\b{re.escape(i)}\b", resposta)]
    if len(achados) == 1:
        return achados[0]
    # Mais de um id citado: a resposta não escolheu — conta como erro, não como acerto.
    return achados[0] if len(achados) == 1 else None


def perguntar(pedido: str, cat: str) -> str:
    r = subprocess.run(
        ["claude", "-p", INSTRUCAO.format(catalogo=cat, pedido=pedido)],
        capture_output=True, text=True, timeout=TIMEOUT,
    )
    return r.stdout.strip()


def main() -> int:
    args = sys.argv[1:]
    como_json = "--json" in args
    args = [a for a in args if a != "--json"]

    def opcao(nome, conv, default):
        if nome in args:
            i = args.index(nome)
            try:
                return conv(args[i + 1])
            except (IndexError, ValueError):
                sys.exit(f"erro: {nome} precisa de um valor")
        return default

    limiar = opcao("--limiar", float, LIMIAR_PADRAO)
    amostra = opcao("--amostra", int, None)

    if not shutil.which("claude"):
        print("⏭️  eval de roteamento pulado — CLI `claude` não disponível.\n"
              "   A parte determinística (ids do gold set existem em agents/) roda "
              "no `release.py check`.")
        return 0

    cat, ids = catalogo()
    lista = casos()[:amostra] if amostra else casos()

    acertos, erros = 0, []
    for n, caso in enumerate(lista, 1):
        pedido, esperado = caso["pedido"], caso["esperado"]
        try:
            bruto = perguntar(pedido, cat)
        except subprocess.TimeoutExpired:
            erros.append({"pedido": pedido, "esperado": esperado, "obtido": "<timeout>"})
            continue
        obtido = extrair_id(bruto, ids)
        if obtido in esperado:
            acertos += 1
        else:
            erros.append({"pedido": pedido, "esperado": esperado,
                          "obtido": obtido or bruto[:60]})
        if not como_json:
            print(f"  [{n}/{len(lista)}] {'✓' if obtido in esperado else '✗'} {pedido[:60]}")

    total = len(lista)
    acuracia = round(100 * acertos / total, 1) if total else 0.0
    passou = acuracia >= limiar

    if como_json:
        print(json.dumps({"total": total, "acertos": acertos, "acuracia": acuracia,
                          "limiar": limiar, "passou": passou, "erros": erros},
                         ensure_ascii=False, indent=2))
    else:
        print(f"\n{'✅' if passou else '❌'} Roteamento da Laura: {acuracia}% "
              f"({acertos}/{total}) · limiar {limiar}%")
        if erros:
            print("\nErros — cada um é ou uma fronteira legítima ou uma description "
                  "que precisa ficar mais nítida:")
            for e in erros:
                print(f"  ✗ {e['pedido'][:70]}\n     esperado: {e['esperado']} · "
                      f"obtido: {e['obtido']}")
        if not passou:
            print("\nAbaixo do limiar: a mudança que causou a queda volta. "
                  "NUNCA ajuste o gold set só para o número passar (Goodhart).")
    return 0 if passou else 1


if __name__ == "__main__":
    sys.exit(main())
