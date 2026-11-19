#!/usr/bin/env python3
"""pronto.py — o `## Pronto quando` de cada skill (ADR-0060). Sem I/O.

Cada skill da fábrica diz o que precisa estar provado para ela dar o trabalho por
terminado. A ideia vem do corno-skills (sem licença declarada: a ideia, não o texto).
Sem a seção, "terminei" é o que o modelo achar; com ela, é uma lista que se confere.

A forma é cobrada aqui, num lugar só:

- o título `## Pronto quando`, uma vez, fora de bloco de código;
- de 3 a 7 itens de lista, cada um numa linha de até 280 caracteres;
- cada item com o comando ou o artefato que o prova entre crases, ou terminando em
  `(gate humano)` quando quem decide é a pessoa;
- o script citado existe, e o primeiro argumento dele, quando é um subcomando ou uma
  flag, aparece no código do script.

Quem usa: o `release.py check` (a forma, em toda skill) e o `guardrail.py conferir` (os
itens das skills usadas na sessão, quando a pessoa pergunta se falta algo). Confere a
forma, não a verdade: se o item descreve o que a skill de fato exige é o revisor que diz.
"""
from __future__ import annotations

import re

TITULO = re.compile(r"^##\s+Pronto quando\s*$")
OUTRO_TITULO = re.compile(r"^#{1,2}\s+\S")
ITEM = re.compile(r"^-\s+(.+?)\s*$")
CRASES = re.compile(r"`([^`]+)`")
SCRIPT_CITADO = re.compile(r"\b([a-z][\w-]*\.py)(?:\s+(-{0,2}[a-z][\w-]*))?")
GATE_HUMANO = "(gate humano)"
MIN_ITENS, MAX_ITENS, MAX_CHARS_ITEM = 3, 7, 280


def _fora_de_bloco(texto: str):
    """(número, linha) de cada linha fora de bloco de código cercado."""
    em_bloco = False
    for n, linha in enumerate(texto.splitlines(), 1):
        if linha.lstrip().startswith("```"):
            em_bloco = not em_bloco
            continue
        if not em_bloco:
            yield n, linha


def secoes(texto: str) -> list[list[str]]:
    """O corpo de cada `## Pronto quando` do texto (normalmente um só)."""
    achadas: list[list[str]] = []
    atual: list[str] | None = None
    for _, linha in _fora_de_bloco(texto):
        if TITULO.match(linha):
            atual = []
            achadas.append(atual)
        elif OUTRO_TITULO.match(linha):
            atual = None
        elif atual is not None:
            atual.append(linha)
    return achadas


def itens(texto: str) -> list[str] | None:
    """Os itens da seção, ou None quando a skill não a tem."""
    achadas = secoes(texto)
    if not achadas:
        return None
    return [m.group(1) for linha in achadas[0] if (m := ITEM.match(linha))]


def _problemas_do_item(i: int, item: str, scripts: dict[str, str]) -> list[str]:
    problemas = []
    if len(item) > MAX_CHARS_ITEM:
        problemas.append(f"item {i}: {len(item)} caracteres, limite {MAX_CHARS_ITEM}")
    spans = CRASES.findall(item)
    if not spans and not item.rstrip(" .;").endswith(GATE_HUMANO):
        problemas.append(f"item {i}: sem o comando ou o artefato entre crases, e sem "
                         f"`{GATE_HUMANO}` no fim")
    for span in spans:
        for m in SCRIPT_CITADO.finditer(span):
            script, argumento = m.group(1), m.group(2)
            if script not in scripts:
                problemas.append(f"item {i}: cita `{script}`, que não existe em scripts/")
            elif argumento and f'"{argumento}"' not in scripts[script]:
                problemas.append(f"item {i}: `{script} {argumento}` — `{argumento}` não "
                                 f"aparece no {script}")
    return problemas


def problemas(texto: str, scripts: dict[str, str]) -> list[str]:
    """O que falta na seção. `scripts` é nome → código dos scripts da fábrica."""
    achadas = secoes(texto)
    if not achadas:
        return ["sem a seção `## Pronto quando`"]
    lista = [p for p in [f"`## Pronto quando` aparece {len(achadas)} vezes"] if len(achadas) > 1]
    corpo = [l for l in achadas[0] if l.strip()]
    soltas = [l for l in corpo if not ITEM.match(l)]
    if soltas:
        lista.append(f"linha fora da lista: {soltas[0].strip()[:60]}")
    todos = itens(texto) or []
    if not MIN_ITENS <= len(todos) <= MAX_ITENS:
        lista.append(f"{len(todos)} itens; são de {MIN_ITENS} a {MAX_ITENS}")
    for i, item in enumerate(todos, 1):
        lista += _problemas_do_item(i, item, scripts)
    return lista
