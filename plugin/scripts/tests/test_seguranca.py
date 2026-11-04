"""Testes do `check-agent-security.py`: a identidade da fábrica nos workflows.

Só stdlib. Workflow da fábrica que age com token de pessoa dá ao agente a escrita da
pessoa, e revogar um é revogar o outro (emenda ao ADR-0026).

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

ARQ = Path(__file__).resolve().parent.parent / "check-agent-security.py"
_spec = importlib.util.spec_from_file_location("check_agent_security", ARQ)
seguranca = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seguranca)

FABRICA = "name: kairos-forge — revisar\nenv:\n  GH_TOKEN: ${{ %s }}\n"


class IdentidadeDaFabrica(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-seg-")
        self.raiz = Path(self._tmp.name)
        seguranca.achados.clear()

    def tearDown(self) -> None:
        seguranca.achados.clear()
        self._tmp.cleanup()

    def workflow(self, rel: str, texto: str) -> None:
        p = self.raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")

    def test_token_de_pessoa_em_workflow_da_fabrica_e_achado(self) -> None:
        self.workflow(".github/workflows/kairos-forge-revisar.yml", FABRICA % "secrets.GH_PAT")
        self.workflow(".github/workflows/kairos-forge-triar.yml", FABRICA % "secrets.GH_TOKEN")
        self.workflow("templates/ci/kairos-forge-corrigir.yml", FABRICA % "secrets.MEU_TOKEN_PESSOAL")
        self.assertEqual(seguranca.checar_identidade(self.raiz), 3)
        self.assertEqual([(s, r) for s, r, _ in seguranca.achados], [("MEDIA", "identidade da fábrica")] * 3)
        self.assertIn("secrets.GH_PAT", seguranca.achados[0][2])

    def test_app_token_do_workflow_e_workflow_alheio_passam(self) -> None:
        self.workflow(".github/workflows/kairos-forge-revisar.yml",
                      FABRICA % "steps.app.outputs.token || github.token"
                      + "  K: ${{ secrets.ANTHROPIC_API_KEY }}\n  P: ${{ secrets.FORGE_APP_PRIVATE_KEY }}\n"
                      + "  T: ${{ secrets.GITHUB_TOKEN }}\n  C: ${{ secrets.COMPANY_URL }}\n")
        self.workflow(".github/workflows/deploy.yml", "name: deploy\nenv:\n  T: ${{ secrets.DEPLOY_PAT }}\n")
        self.assertEqual(seguranca.checar_identidade(self.raiz), 1)
        self.assertEqual(seguranca.achados, [])

    def test_apontado_para_o_claude_do_projeto_olha_os_workflows_dele(self) -> None:
        self.workflow(".github/workflows/kairos-forge-auditar.yml", FABRICA % "secrets.PAT")
        (self.raiz / ".claude").mkdir()
        self.assertEqual(seguranca.checar_identidade(self.raiz / ".claude"), 1)
        self.assertEqual(len(seguranca.achados), 1)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(seguranca.main(["x", str(self.raiz / ".claude")]), 0)   # MEDIA não falha o CI
        self.assertIn("1 workflows da fábrica", out.getvalue())


if __name__ == "__main__":
    unittest.main()
