"""Validação do nome de arquivo que o usuário pede para baixar."""
from __future__ import annotations


def nome_valido(nome: str) -> bool:
    """Recusa nome vazio e nome que sobe de pasta (`..`)."""
    return bool(nome) and ".." not in nome.split("/")
