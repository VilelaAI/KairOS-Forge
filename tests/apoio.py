"""Apoio compartilhado da suíte (ADR-0039).

Princípios, copiados de quem já pagou o preço de não os ter:

- **Script como CLI, em repositório temporário.** O contrato testado é argv + código de
  saída + stdout + efeito no disco — o mesmo que o hook, o CI e o kairos-symphony veem.
  Nenhum teste importa o script para chamar função interna, salvo para injetar falha.
- **Só stdlib.** Um teste que se pula por falta de dependência é um teste que silenciosamente
  parou de rodar.
- **Falha antes de escrever.** Todo caso negativo confere que o estado em disco ficou
  byte a byte igual.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"


def ambiente(extra: dict | None = None) -> dict:
    env = dict(os.environ)
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "CLAUDE_PLUGIN_ROOT": str(RAIZ),
        "LC_ALL": "C.UTF-8",
    })
    env.pop("CLAUDE_SESSION_ID", None)
    if extra:
        env.update(extra)
    return env


def rodar(script: str, *args: str, cwd: Path, stdin: str | None = None,
          env: dict | None = None, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=str(cwd), input=stdin, capture_output=True, text=True,
        env=ambiente(env), timeout=timeout,
    )


def git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                       env=ambiente(), timeout=30)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falhou: {r.stderr}")
    return r.stdout.strip()


class Repositorio:
    """Diretório temporário com `git init` e um commit inicial. Use como context manager."""

    def __init__(self, com_git: bool = True):
        self.com_git = com_git
        self.dir: Path | None = None

    def __enter__(self) -> Path:
        self.dir = Path(tempfile.mkdtemp(prefix="forge-tmp-")).resolve()
        if self.com_git:
            git(self.dir, "init", "-q", "-b", "main")
            git(self.dir, "config", "user.email", "teste@exemplo.local")
            git(self.dir, "config", "user.name", "Teste")
            (self.dir / "README.md").write_text("# projeto de teste\n", encoding="utf-8")
            git(self.dir, "add", "README.md")
            git(self.dir, "commit", "-q", "-m", "inicial")
        return self.dir

    def __exit__(self, *exc) -> None:
        if self.dir is not None:
            shutil.rmtree(self.dir, ignore_errors=True)


def payload(tool: str, cwd: Path, sessao: str = "sessao-teste", **tool_input) -> str:
    return json.dumps({
        "session_id": sessao,
        "cwd": str(cwd),
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
    })


def fence(nome: str, dados: dict, preambulo: str = "# Relatório\n\nTexto.\n") -> str:
    return f"{preambulo}\n```{nome}\n{json.dumps(dados, ensure_ascii=False)}\n```\n"


def escrever(raiz: Path, rel: str, conteudo: str) -> Path:
    p = raiz / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(conteudo, encoding="utf-8")
    return p


def eventos(raiz: Path) -> list[dict]:
    pasta = raiz / ".agents" / "execucoes"
    if not pasta.is_dir():
        return []
    saida = []
    for arq in sorted(pasta.glob("*.jsonl")):
        for linha in arq.read_text(encoding="utf-8").splitlines():
            if linha.strip():
                saida.append(json.loads(linha))
    return saida


def assinatura_da_arvore(raiz: Path) -> str:
    """Hash recursivo de nomes + conteúdo. Ignora .git e __pycache__."""
    h = hashlib.sha256()
    for p in sorted(raiz.rglob("*")):
        rel = p.relative_to(raiz)
        if ".git" in rel.parts or "__pycache__" in rel.parts:
            continue
        h.update(str(rel).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()
