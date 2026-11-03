"""Download dos relatórios — correção ingênua: bloqueia `..`, mas não caminho absoluto."""
from __future__ import annotations

from pathlib import Path

BASE = Path("relatorios")


def servir_relatorio(nome: str) -> bytes:
    if ".." in nome:
        raise ValueError(f"fora da pasta de relatórios: {nome}")
    return (BASE / nome).read_bytes()
