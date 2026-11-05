"""Agregações por região."""
from __future__ import annotations


def media_por_regiao(vendas: list[dict[str, str]]) -> dict[str, float]:
    somas: dict[str, float] = {}
    contagem: dict[str, int] = {}
    for venda in vendas:
        regiao = venda["regiao"]
        somas[regiao] = somas.get(regiao, 0.0) + float(venda["valor"])
        contagem[regiao] = contagem.get(regiao, 0) + 1
    return {r: round(somas[r] / contagem[r], 2) for r in somas}
