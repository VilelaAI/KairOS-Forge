"""Ticket médio: o valor médio por venda."""
from __future__ import annotations

from vendas.valores import para_reais


def ticket_medio(vendas: list[dict[str, str]]) -> float:
    valores = [para_reais(venda["valor"]) for venda in vendas]
    return round(sum(valores) / len(valores), 2) if valores else 0.0
