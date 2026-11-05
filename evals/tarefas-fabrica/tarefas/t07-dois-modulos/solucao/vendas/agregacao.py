"""Totais por região."""
from __future__ import annotations


def por_regiao(vendas: list[dict[str, str]]) -> dict[str, float]:
    saida: dict[str, float] = {}
    for venda in vendas:
        try:
            valor = float(venda.get("valor") or "")
        except ValueError:
            continue
        saida[venda["regiao"]] = saida.get(venda["regiao"], 0.0) + valor
    return saida
