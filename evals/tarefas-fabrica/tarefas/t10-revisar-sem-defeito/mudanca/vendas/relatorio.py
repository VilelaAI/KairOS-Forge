"""Relatório de vendas a partir de um CSV (data, regiao, produto, valor)."""
from __future__ import annotations

import csv
import sys


def ler_vendas(caminho: str) -> list[dict[str, str]]:
    with open(caminho, newline="", encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def valor_de(venda: dict[str, str]) -> float | None:
    """O valor da venda, ou None quando vazio ou não numérico."""
    try:
        return float(venda.get("valor") or "")
    except ValueError:
        return None


def validas(vendas: list[dict[str, str]]) -> list[dict[str, str]]:
    return [v for v in vendas if valor_de(v) is not None]


def total(vendas: list[dict[str, str]]) -> float:
    return sum(valor_de(v) for v in validas(vendas))


def linhas_invalidas(vendas: list[dict[str, str]]) -> int:
    return len(vendas) - len(validas(vendas))


def media(vendas: list[dict[str, str]]) -> float:
    """Média por venda válida; 0.0 quando não há nenhuma (o relatório mostra zero em vez de quebrar)."""
    quantas = len(validas(vendas))
    return total(vendas) / quantas if quantas else 0.0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    vendas = ler_vendas(argv[0] if argv else "dados/vendas.csv")
    print(f"Vendas: {len(vendas)}")
    print(f"Total: R$ {total(vendas):.2f}")
    # TODO(comercial): mostrar também a mediana, quando o time pedir.
    print(f"Média: R$ {media(vendas):.2f}")
    print(f"Ignoradas: {linhas_invalidas(vendas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
