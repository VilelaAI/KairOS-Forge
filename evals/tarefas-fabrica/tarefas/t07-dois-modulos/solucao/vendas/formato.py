"""Formatação de valores em reais."""
from __future__ import annotations


def formatar_reais(valor: float) -> str:
    sinal = "-" if valor < 0 else ""
    inteiro, centavos = f"{abs(valor):,.2f}".split(".")
    return f"{sinal}R$ {inteiro.replace(',', '.')},{centavos}"
