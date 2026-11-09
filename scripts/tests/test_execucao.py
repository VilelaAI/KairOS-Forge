"""Testes da escrita registrada pelo `execucao.py`: o que conta como produção do projeto.

Só stdlib. Origem: numa sessão do `/entregar`, o gate de parada (ADR-0042) avisou "parada
sem prova" por causa do script de medição que o Claude Code escreveu no scratchpad, fora
do projeto. Escrita fora do checkout não é produção do projeto.

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

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import execucao  # noqa: E402
import guardrail  # noqa: E402
from tests.test_guardrail import o_que_se_le  # noqa: E402


def escrita(arquivo: str, cwd: Path, ferramenta: str = "Write") -> dict:
    return {"session_id": "s1", "cwd": str(cwd), "tool_name": ferramenta,
            "tool_input": {"file_path": arquivo, "content": "x = 1\n"}}


class Sandbox(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-execucao-")
        self.raiz = Path(self._tmp.name).resolve() / "projeto"
        self.raiz.mkdir()
        (self.raiz / ".git").mkdir()
        self._fora = tempfile.TemporaryDirectory(prefix="kairos-forge-scratchpad-")
        self.scratchpad = Path(self._fora.name).resolve()

    def tearDown(self) -> None:
        self._tmp.cleanup()
        self._fora.cleanup()


class ProducaoDoProjeto(Sandbox):
    def test_codigo_dentro_do_projeto_e_producao(self) -> None:
        ev = execucao.ev_ferramenta(escrita(str(self.raiz / "src" / "a.py"), self.raiz))
        self.assertEqual(ev["arquivo"], "src/a.py")
        self.assertTrue(ev["producao"])

    def test_caminho_relativo_dentro_do_projeto_e_producao(self) -> None:
        antes = os.getcwd()
        os.chdir(self.raiz)
        try:
            ev = execucao.ev_ferramenta(escrita("src/a.py", self.raiz, "Edit"))
        finally:
            os.chdir(antes)
        self.assertTrue(ev["producao"])

    def test_codigo_no_scratchpad_fora_do_projeto_nao_e_producao(self) -> None:
        alvo = self.scratchpad / "medicao" / "medir.py"
        ev = execucao.ev_ferramenta(escrita(str(alvo), self.raiz))
        self.assertFalse(ev["producao"])
        self.assertEqual(ev["arquivo"], str(alvo))  # fica legível de onde veio

    def test_irmao_do_projeto_nao_e_producao(self) -> None:
        irmao = self.raiz.parent / "outro" / "b.py"
        self.assertFalse(execucao.ev_ferramenta(escrita(str(irmao), self.raiz))["producao"])

    def test_teste_dentro_do_projeto_continua_fora(self) -> None:
        ev = execucao.ev_ferramenta(escrita(str(self.raiz / "tests" / "test_a.py"), self.raiz))
        self.assertFalse(ev["producao"])

    def test_sessao_numa_subpasta_conta_o_checkout_inteiro(self) -> None:
        sub = self.raiz / "servico"
        sub.mkdir()
        ev = execucao.ev_ferramenta(escrita(str(self.raiz / "lib" / "c.py"), sub))
        self.assertTrue(ev["producao"])

    def test_sem_git_a_raiz_e_o_proprio_cwd(self) -> None:
        sem_git = self.scratchpad / "solto"
        sem_git.mkdir()
        self.assertEqual(execucao.raiz_do_checkout(str(sem_git)), sem_git)
        self.assertTrue(execucao.ev_ferramenta(escrita(str(sem_git / "d.py"), sem_git))["producao"])

    def test_worktree_ligado_tem_raiz_propria(self) -> None:
        (self.raiz / "wt").mkdir()
        (self.raiz / "wt" / ".git").write_text("gitdir: ../.git/worktrees/wt\n", encoding="utf-8")
        self.assertEqual(execucao.raiz_do_checkout(str(self.raiz / "wt")), self.raiz / "wt")


class GateDeParadaDePontaAPonta(Sandbox):
    """O sintoma relatado: o hook grava a escrita e o `Stop` decide se avisa."""

    def ferramenta(self, payload: dict) -> None:
        antigo = sys.stdin
        sys.stdin = io.StringIO(json.dumps(payload))
        sys.argv, argv = ["execucao.py", "ferramenta"], sys.argv
        try:
            self.assertEqual(execucao.main(), 0)
        finally:
            sys.stdin, sys.argv = antigo, argv

    def parada(self) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        guardrail._EDITOR["cursor"] = False
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            codigo = guardrail.checar_parada({"session_id": "s1", "cwd": str(self.raiz)})
        return codigo, o_que_se_le(codigo, out.getvalue(), err.getvalue())

    def test_script_no_scratchpad_nao_dispara_o_aviso(self) -> None:
        self.ferramenta(escrita(str(self.scratchpad / "medicao" / "medir.py"), self.raiz))
        self.assertEqual(self.parada(), (0, ""))

    def test_producao_no_projeto_ainda_dispara(self) -> None:
        self.ferramenta(escrita(str(self.raiz / "vendas" / "relatorio.py"), self.raiz))
        codigo, err = self.parada()
        self.assertEqual(codigo, 1)  # `parada` nasce em aviso
        self.assertIn("vendas/relatorio.py", err)


class GitDeVerdade(unittest.TestCase):
    """`raiz_do_checkout` lê o `.git` sem rodar git; confere contra um repositório real."""

    def test_bate_com_o_toplevel_do_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp).resolve()
            subprocess.run(["git", "init", "-q", str(raiz)], check=True)
            (raiz / "a" / "b").mkdir(parents=True)
            topo = subprocess.run(["git", "-C", str(raiz / "a" / "b"), "rev-parse", "--show-toplevel"],
                                  check=True, capture_output=True, text=True).stdout.strip()
            self.assertEqual(execucao.raiz_do_checkout(str(raiz / "a" / "b")), Path(topo).resolve())


if __name__ == "__main__":
    unittest.main()
