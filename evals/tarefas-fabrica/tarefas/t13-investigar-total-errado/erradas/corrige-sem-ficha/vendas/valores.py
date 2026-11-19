"""Conversão dos valores que o ERP exporta."""
from __future__ import annotations


def para_reais(texto: str) -> float:
    """O ERP exporta no formato brasileiro (1.234,56) e, desde outubro, parte das linhas com
    ponto decimal (1234.56). Com vírgula, o ponto separa o milhar; sem vírgula, é o decimal."""
    texto = texto.strip()
    if "," in texto:
        return float(texto.replace(".", "").replace(",", "."))
    return float(texto)
