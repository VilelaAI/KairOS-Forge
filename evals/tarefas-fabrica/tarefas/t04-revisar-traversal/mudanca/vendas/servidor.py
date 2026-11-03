"""Download dos relatórios gerados em relatorios/."""
from __future__ import annotations

from pathlib import Path

BASE = Path("relatorios")


def servir_relatorio(nome: str) -> bytes:
    return (BASE / nome).read_bytes()
