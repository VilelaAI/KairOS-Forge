"""Testes do `sync-multi-cli.py` — o sync inteiro, numa cópia do repositório.

Só stdlib. O módulo é carregado do arquivo de verdade (para a cobertura contar) e os
caminhos dele apontam para uma cópia temporária de `agents/`, `skills/`, `templates/` e
`scripts/`: o repositório não é tocado.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import shutil
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
REPO = SCRIPTS.parent


def carregar_sync():
    spec = importlib.util.spec_from_file_location("sync_multi_cli", SCRIPTS / "sync-multi-cli.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class SyncNumaCopia(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-sync-")
        self.raiz = Path(self._tmp.name)
        for d in ("agents", "skills", "templates", "scripts"):
            shutil.copytree(REPO / d, self.raiz / d,
                            ignore=shutil.ignore_patterns("__pycache__", "tests"))
        (self.raiz / ".claude-plugin").mkdir()
        shutil.copy2(REPO / ".claude-plugin" / "plugin.json", self.raiz / ".claude-plugin")
        self.sync = carregar_sync()
        r = self.raiz
        for nome, caminho in {"ROOT": r, "AGENTS_SRC": r / "agents", "SKILLS_SRC": r / "skills",
                              "CODEX_DIR": r / ".agents", "CURSOR_DIR": r / ".cursor",
                              "PLUGIN_JSON": r / ".claude-plugin" / "plugin.json",
                              "MANIFESTO_ATIVOS": r / ".claude-plugin" / "ativos.manifest.json"}.items():
            setattr(self.sync, nome, caminho)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_regenera_todos_os_alvos_inclusive_o_time_do_tucano(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(self.sync.sincronizar_tudo(), 0)
        for rel in (".agents/laura-tech-lead/AGENT.md", ".codex/agents/laura-tech-lead.toml",
                    ".opencode/agent/laura-tech-lead.md", ".cursor/scripts/ciclo.py",
                    ".claude-plugin/ativos.manifest.json", ".tucano/kairos-forge-entrega.md"):
            self.assertTrue((self.raiz / rel).is_file(), rel)
        # A cópia gera o mesmo time que o repositório versiona: o sync é determinístico.
        self.assertEqual((self.raiz / ".tucano/kairos-forge-entrega.md").read_text(encoding="utf-8"),
                         (REPO / ".tucano/kairos-forge-entrega.md").read_text(encoding="utf-8"))
        self.assertIn("importe no Tucano", out.getvalue())

    def test_sem_agents_nao_sincroniza(self) -> None:
        shutil.rmtree(self.raiz / "agents")
        with contextlib.redirect_stderr(io.StringIO()) as err, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.sync.sincronizar_tudo(), 1)
        self.assertIn("agents/ não encontrado", err.getvalue())
        self.assertFalse((self.raiz / ".tucano").exists())


if __name__ == "__main__":
    unittest.main()
