"""Relatório de vendas a partir de um CSV (data, regiao, produto, valor)."""
from __future__ import annotations

import csv
import sys

from vendas.valores import para_reais


def ler_vendas(caminho: str) -> list[dict[str, str]]:
    with open(caminho, newline="", encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def total(vendas: list[dict[str, str]]) -> float:
    soma = 0.0
    for venda in vendas:
        valor = venda["valor"].strip()
        soma += para_reais(valor) if "," in valor else float(valor)
    return soma


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    vendas = ler_vendas(argv[0] if argv else "dados/vendas.csv")
    print(f"Vendas: {len(vendas)}")
    print(f"Total: R$ {total(vendas):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
