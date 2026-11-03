"""Download dos relatórios gerados em relatorios/."""
from __future__ import annotations

from pathlib import Path

BASE = Path("relatorios")


def servir_relatorio(nome: str) -> bytes:
    raiz = BASE.resolve()
    alvo = (raiz / nome).resolve()
    if not alvo.is_relative_to(raiz):
        raise ValueError(f"fora da pasta de relatórios: {nome}")
    return alvo.read_bytes()
