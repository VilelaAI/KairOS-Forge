"""Relatório de vendas a partir de um CSV (data, regiao, produto, valor)."""
from __future__ import annotations

import csv
import sys


def ler_vendas(caminho: str) -> list[dict[str, str]]:
    with open(caminho, newline="", encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def total(vendas: list[dict[str, str]]) -> float:
    return sum(float(venda["valor"]) for venda in vendas)


def maior(vendas: list[dict[str, str]]) -> float:
    """O maior valor entre as vendas; 0.0 quando não há nenhuma."""
    return max((float(venda["valor"]) for venda in vendas), default=0.0)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    vendas = ler_vendas(argv[0] if argv else "dados/vendas.csv")
    print(f"Vendas: {len(vendas)}")
    print(f"Total: R$ {total(vendas):.2f}")
    print(f"Maior venda: R$ {maior(vendas):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
