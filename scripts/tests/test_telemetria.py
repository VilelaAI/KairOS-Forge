"""Testes do `telemetria.py prs` — a autonomia de PR medida pelo git (ADR-0044).

Só stdlib. Cada teste monta um repositório git temporário com merges de verdade, porque
o número sai do histórico; a leitura do `gh` é testada com a resposta dele simulada.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import telemetria  # noqa: E402

FABRICA = "\n\nFabrica: kairos-forge"
CLAUDE = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"


def git(*args: str, autor: str = "Pessoa") -> None:
    subprocess.run(["git", "-c", f"user.name={autor}", "-c", "user.email=a@b", *args],
                   check=True, capture_output=True)


class Repo(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-telemetria-")
        self._cwd = os.getcwd()
        self.raiz = Path(self._tmp.name).resolve()
        os.chdir(self.raiz)
        git("init", "-q", "-b", "main", ".")
        git("commit", "-q", "--allow-empty", "-m", "base")

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def pr(self, numero: int, branch: str, commits: list[tuple[str, str]]) -> None:
        """Abre `branch`, faz os commits (autor, mensagem) e mescla com commit de merge."""
        git("checkout", "-q", "-b", branch)
        for i, (autor, mensagem) in enumerate(commits):
            Path(f"{branch.replace('/', '-')}-{i}.txt").write_text(mensagem, encoding="utf-8")
            git("add", ".")
            git("commit", "-q", "-m", mensagem, autor=autor)
        git("checkout", "-q", "main")
        git("merge", "-q", "--no-ff", branch, "-m",
            f"Merge pull request #{numero} from org/{branch}")

    def medir(self, *extras: str) -> dict:
        import re
        _, prs = telemetria.prs_mesclados(self.raiz, None, "git")
        return telemetria.autonomia_de_prs(prs, tuple(re.compile(e, re.I | re.M) for e in extras))


class AutonomiaDePr(Repo):
    def test_so_pr_sem_commit_humano_conta_como_autonomo(self) -> None:
        self.pr(1, "forge/a", [("Pessoa", "feat: a" + FABRICA), ("Pessoa", "test: a" + FABRICA)])
        self.pr(2, "feat/b", [("Pessoa", "feat: b" + CLAUDE), ("Pessoa", "fix: ajuste à mão")])
        self.pr(3, "feat/c", [("Pessoa", "feat: c feito à mão")])
        r = self.medir()
        self.assertEqual((r["mesclados"], r["da_fabrica"], r["autonomos"]), (3, 2, 1))
        self.assertEqual(r["taxa"], 50.0)
        por_numero = {l["numero"]: l for l in r["prs"]}
        self.assertTrue(por_numero[1]["autonomo"])
        self.assertEqual((por_numero[2]["agente"], por_numero[2]["humano"]), (1, 1))
        self.assertFalse(por_numero[3]["da_fabrica"])
        self.assertEqual(por_numero[1]["branch"], "forge/a")

    def test_sem_pr_da_fabrica_e_nao_medido(self) -> None:
        self.pr(1, "feat/a", [("Pessoa", "feat: tudo à mão")])
        r = self.medir()
        self.assertEqual(r["da_fabrica"], 0)
        self.assertIsNone(r["taxa"])

    def test_autor_kairos_forge_e_marca_extra(self) -> None:
        self.pr(1, "forge/corrige-x", [("kairos-forge", "fix(ci): corrige")])
        self.pr(2, "feat/codex", [("Pessoa", "feat: x\n\nCodex-Session: 123")])
        self.assertEqual(self.medir()["autonomos"], 1)
        self.assertEqual(self.medir(r"^codex-session:")["autonomos"], 2)

    def test_cli_json(self) -> None:
        self.pr(7, "forge/a", [("Pessoa", "feat: a" + FABRICA)])
        out = io.StringIO()
        antigo = sys.argv
        sys.argv = ["telemetria.py", "prs", "--fonte", "git", "--json"]
        try:
            with contextlib.redirect_stdout(out):
                codigo = telemetria.main()
        finally:
            sys.argv = antigo
        self.assertEqual(codigo, 0)
        r = json.loads(out.getvalue())
        self.assertEqual((r["fonte"], r["taxa"]), ("git", 100.0))


class LeituraDoGh(unittest.TestCase):
    def test_normaliza_a_resposta_do_gh(self) -> None:
        resposta = [{
            "number": 42, "title": "feat: exporta CSV", "headRefName": "feat/csv",
            "mergedAt": "2026-10-20T12:00:00Z", "mergeCommit": {"oid": "abc"},
            "closingIssuesReferences": [{"number": 9}],
            "commits": [
                {"oid": "1", "authors": [{"name": "Pessoa", "login": "p"}],
                 "messageHeadline": "feat: exporta", "messageBody": "Fabrica: kairos-forge"},
                {"oid": "2", "authors": [{"name": "Pessoa", "login": "p"}],
                 "messageHeadline": "fix: ajuste", "messageBody": ""},
            ],
        }]
        falso = subprocess.CompletedProcess([], 0, stdout=json.dumps(resposta), stderr="")
        with mock.patch.object(telemetria.shutil, "which", return_value="/usr/bin/gh"), \
                mock.patch.object(telemetria.subprocess, "run", return_value=falso):
            fonte, prs = telemetria.prs_mesclados(Path("."), None)
        self.assertEqual(fonte, "gh")
        self.assertEqual((prs[0]["numero"], prs[0]["entrega"], prs[0]["issues"]), (42, "abc", [9]))
        r = telemetria.autonomia_de_prs(prs)
        self.assertEqual((r["da_fabrica"], r["autonomos"]), (1, 0))

    def test_gh_falhando_cai_para_o_git(self) -> None:
        falso = subprocess.CompletedProcess([], 1, stdout="", stderr="no remotes")
        with mock.patch.object(telemetria.shutil, "which", return_value="/usr/bin/gh"), \
                mock.patch.object(telemetria.subprocess, "run", side_effect=[falso]), \
                mock.patch.object(telemetria, "_prs_do_git", return_value=[]) as do_git:
            fonte, _ = telemetria.prs_mesclados(Path("."), 30)
        self.assertEqual(fonte, "git")
        do_git.assert_called_once()


if __name__ == "__main__":
    unittest.main()
