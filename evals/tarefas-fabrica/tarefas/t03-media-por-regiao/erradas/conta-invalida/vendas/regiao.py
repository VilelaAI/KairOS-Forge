"""Agregações por região — correção ingênua: tira a linha inválida da soma, mas não da contagem."""
from __future__ import annotations


def media_por_regiao(vendas: list[dict[str, str]]) -> dict[str, float]:
    somas: dict[str, float] = {}
    contagem: dict[str, int] = {}
    for venda in vendas:
        regiao = venda["regiao"]
        contagem[regiao] = contagem.get(regiao, 0) + 1
        try:
            somas[regiao] = somas.get(regiao, 0.0) + float(venda["valor"])
        except ValueError:
            somas.setdefault(regiao, 0.0)
    return {r: round(somas[r] / contagem[r], 2) for r in somas}
