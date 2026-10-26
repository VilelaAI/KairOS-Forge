"""Testes do `painel.py --caixa` — a caixa de entrada da fábrica (ADR-0044).

Só stdlib. Os ciclos e o quadro são criados pelos próprios `ciclo.py` e `quadro.py`, num
diretório temporário: a caixa lê o mesmo estado que eles escrevem, e é isso que se testa.

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
import ciclo  # noqa: E402
import painel  # noqa: E402
import quadro  # noqa: E402

SPEC = """# SPEC-00{n} — Exemplo

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| EX-01 | Exportar lista | P1 | WHEN clica THEN baixa CSV em ≤ 2 s | Pendente | — |
"""


def chamar(modulo, *args: str) -> int:
    antigo = sys.argv
    sys.argv = [modulo.__name__ + ".py", *args]
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                return int(modulo.main() or 0)
            except SystemExit as e:
                return 1 if e.code else 0
    finally:
        sys.argv = antigo


class Caixa(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-painel-")
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        Path("docs/specs").mkdir(parents=True)
        for n in (1, 2, 3):
            Path(f"docs/specs/SPEC-00{n}-x.md").write_text(SPEC.format(n=n), encoding="utf-8")

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def tipos(self, d: dict) -> dict:
        return {(i["tipo"], i["onde"]) for i in d["itens"]}

    def test_vazia_quando_nada_espera(self) -> None:
        chamar(ciclo, "abrir", "SPEC-001", "--spec-aprovada")
        d = painel.caixa(Path.cwd())
        self.assertEqual(d["itens"], [])
        self.assertEqual(d["github"]["estado"], "nao_consultado")
        self.assertIn("Nada esperando", painel.render_caixa(d))

    def test_junta_gate_spec_alterada_escalado_e_bloqueio(self) -> None:
        chamar(ciclo, "abrir", "SPEC-001")                       # enquadrando
        chamar(ciclo, "registrar", "entendimento_pronto", "SPEC-001")  # → gate 1/3
        chamar(ciclo, "abrir", "SPEC-002", "--spec-aprovada")
        spec2 = Path("docs/specs/SPEC-002-x.md")
        spec2.write_text(spec2.read_text(encoding="utf-8").replace("≤ 2 s", "≤ 5 s"), encoding="utf-8")
        chamar(ciclo, "abrir", "SPEC-003", "--spec-aprovada")
        chamar(ciclo, "escalar", "SPEC-003", "--motivo", "orçamento de validar esgotado")
        chamar(quadro, "abrir", "forge-x")
        chamar(quadro, "adicionar", "forge-x", "--id", "T1", "--titulo", "migration",
               "--dono", "carlos-dba", "--posse", "migrations/**", "--pronto-quando", "roda")
        chamar(quadro, "iniciar", "forge-x", "T1")
        chamar(quadro, "bloquear", "forge-x", "T1", "--motivo", "falta decidir UUID ou bigint")

        d = painel.caixa(Path.cwd())
        self.assertEqual(self.tipos(d), {("gate", "SPEC-001"), ("spec_alterada", "SPEC-002"),
                                         ("escalado", "SPEC-003"), ("bloqueada", "forge-x")})
        escalado = next(i for i in d["itens"] if i["tipo"] == "escalado")
        self.assertIn("orçamento", escalado["o_que"])
        saida = painel.render_caixa(d)
        self.assertIn("gate 1/3", saida)
        self.assertIn("ciclo.py reaprovar SPEC-002", saida)

    def test_github_so_quando_pedido_e_so_pr_da_fabrica(self) -> None:
        issues = [{"number": 9, "title": "Exportar CSV", "url": "u9"}]
        prs = [
            {"number": 1, "title": "feat: da fábrica", "url": "u1", "isDraft": False,
             "commits": [{"authors": [{"name": "P"}], "messageHeadline": "feat: x",
                          "messageBody": "Fabrica: kairos-forge"}]},
            {"number": 2, "title": "feat: à mão", "url": "u2", "isDraft": False,
             "commits": [{"authors": [{"name": "P"}], "messageHeadline": "feat: y",
                          "messageBody": ""}]},
        ]
        respostas = [subprocess.CompletedProcess([], 0, stdout=json.dumps(x), stderr="")
                     for x in (issues, prs)]
        with mock.patch.object(painel.shutil, "which", return_value="/usr/bin/gh"), \
                mock.patch.object(painel.subprocess, "run", side_effect=respostas):
            d = painel.caixa(Path.cwd(), github=True)
        self.assertEqual(d["github"]["estado"], "consultado")
        self.assertEqual(self.tipos(d), {("falta_informacao", "issue #9"),
                                         ("pr_da_fabrica", "PR #1")})


if __name__ == "__main__":
    unittest.main()
