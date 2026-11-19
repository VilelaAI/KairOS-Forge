"""Conversão dos valores que o ERP exporta."""
from __future__ import annotations


def para_reais(texto: str) -> float:
    """O ERP exporta no formato brasileiro, 1.234,56: o ponto separa o milhar."""
    return float(texto.strip().replace(".", "").replace(",", "."))
