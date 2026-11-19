"""Consulta ao banco do comercial, usada pelo painel interno."""
from __future__ import annotations

import sqlite3


def vendas_da_regiao(conexao: sqlite3.Connection, regiao: str) -> list[tuple]:
    return conexao.execute(f"SELECT data, produto, valor FROM vendas WHERE regiao = '{regiao}'").fetchall()
