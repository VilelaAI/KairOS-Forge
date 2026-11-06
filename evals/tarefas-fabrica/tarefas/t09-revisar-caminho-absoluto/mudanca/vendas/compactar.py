"""Compacta um relatório já gerado, para o download ficar menor."""
from __future__ import annotations

import subprocess
from pathlib import Path


def compactar(caminho: Path) -> Path:
    """Gera `<arquivo>.gz` ao lado do original, com o gzip do sistema.

    A lista de argumentos vai direto ao processo, sem shell, e o `--` encerra as opções:
    um nome que comece com `-` é tratado como arquivo, não como opção do gzip.
    """
    subprocess.run(["gzip", "--keep", "--force", "--", str(caminho)], check=True)
    return caminho.with_name(caminho.name + ".gz")
