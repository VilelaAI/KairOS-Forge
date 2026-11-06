"""Download dos relatórios gerados em relatorios/."""
from __future__ import annotations

from pathlib import Path

from vendas.nomes import nome_valido

BASE = Path("relatorios")


def servir_relatorio(nome: str) -> bytes:
    if not nome_valido(nome):
        raise ValueError(f"nome de relatório inválido: {nome!r}")
    return (BASE / nome).read_bytes()
