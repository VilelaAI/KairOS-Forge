"""Testes da construção fora do checkout principal (emenda ao ADR-0024).

Só stdlib, num git de verdade com um worktree ligado. Três coisas:

1. O estado do ciclo e do quadro mora no checkout principal, também quando o script roda
   num worktree: o arco aberto lá aparece para a caixa, o painel, a telemetria e o
   guardrail, e o teammate em worktree acha o quadro no `vincular`.
2. Os caminhos sagrados valem pelo caminho relativo ao checkout principal: de dentro do
   worktree, escrever na trajetória ou no estado por caminho absoluto não passa.
3. A classe `checkout` avisa quando código de produção é escrito no checkout principal
   enquanto um ciclo aberto constrói no branch dele.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import contextlib
import importlib.util
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
import guardrail  # noqa: E402
from tests.test_guardrail import o_que_se_le  # noqa: E402
import painel  # noqa: E402
import quadro  # noqa: E402
import telemetria  # noqa: E402

SPEC = """# SPEC-00{n} — Exemplo

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| EX-01 | Exportar | P1 | WHEN clica THEN baixa em ≤ 2 s | Pendente | — |
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


def escrever(payload_cwd: Path, alvo: Path, sessao: str = "s1") -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    guardrail._EDITOR["cursor"] = False
    guardrail._EDITOR["evento"] = ""
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        codigo = guardrail.MODOS["escrita"](guardrail.normalizar_payload({
            "session_id": sessao, "cwd": str(payload_cwd),
            "tool_input": {"file_path": str(alvo), "content": "x = 1\n"}}))
    return codigo, o_que_se_le(codigo, out.getvalue(), err.getvalue())


class ComWorktree(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-checkout-")
        base = Path(self._tmp.name).resolve()
        self.principal, self.wt = base / "repo", base / "wt"
        self.principal.mkdir()
        self._cwd = os.getcwd()
        for n in (1, 2):
            p = self.principal / f"docs/specs/SPEC-00{n}-x.md"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(SPEC.format(n=n), encoding="utf-8")
        self.git(self.principal, "init", "-q", "-b", "main")
        self.git(self.principal, "add", ".")
        self.git(self.principal, "commit", "-qm", "base")
        self.git(self.principal, "worktree", "add", "-q", str(self.wt), "-b", "forge/SPEC-001")
        self._env = mock.patch.dict(os.environ, {"TMPDIR": str(base)})   # "uma vez por sessão"
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def git(self, onde: Path, *args: str) -> None:
        subprocess.run(["git", "-C", str(onde), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       check=True, capture_output=True)

    def em(self, onde: Path, modulo, *args: str) -> int:
        os.chdir(onde)
        return chamar(modulo, *args)


class EstadoNoCheckoutPrincipal(ComWorktree):
    def test_ciclo_aberto_no_worktree_mora_no_principal_e_todos_o_veem(self) -> None:
        self.assertEqual(self.em(self.wt, ciclo, "abrir", "SPEC-001", "--spec-aprovada"), 0)
        estado = self.principal / ".agents" / "ciclo" / "SPEC-001.json"
        self.assertTrue(estado.is_file())
        self.assertFalse((self.wt / ".agents" / "ciclo").exists())
        self.assertEqual(json.loads(estado.read_text(encoding="utf-8"))["branch"], "forge/SPEC-001")
        self.assertIsNotNone(json.loads(estado.read_text(encoding="utf-8"))["spec_digest"])
        self.assertEqual(self.em(self.wt, ciclo, "estado", "SPEC-001"), 0)   # e o próprio worktree acha
        os.chdir(self.principal)
        self.assertEqual([c["spec"] for c in painel.ler_ciclos(Path.cwd())], ["SPEC-001"])
        self.assertEqual([c["spec"] for c in telemetria.ler_ciclos(self.principal)], ["SPEC-001"])
        self.assertEqual([c["spec"] for c in guardrail.ciclos_abertos(self.wt)], ["SPEC-001"])
        self.assertEqual(self.em(self.principal, ciclo, "listar"), 0)

    def test_teammate_no_worktree_acha_o_quadro_no_vincular(self) -> None:
        self.assertEqual(self.em(self.principal, quadro, "abrir", "forge-x"), 0)
        self.assertEqual(self.em(self.principal, quadro, "adicionar", "forge-x", "--id", "T1",
                                 "--titulo", "exportar", "--dono", "vinicius-backend",
                                 "--posse", "src/**", "--pronto-quando", "teste passa"), 0)
        self.assertEqual(self.em(self.wt, quadro, "vincular", "forge-x", "T1"), 0)
        self.assertEqual(self.em(self.wt, quadro, "listar"), 0)
        self.assertFalse((self.wt / ".agents" / "quadro").exists())
        os.chdir(self.principal)
        self.assertEqual([q["slug"] for q in painel.ler_quadros(Path.cwd())], ["forge-x"])

    def test_telemetria_no_worktree_le_a_trajetoria_do_principal(self) -> None:
        pasta = self.principal / ".agents" / "execucoes"
        pasta.mkdir(parents=True)
        (pasta / "2026-11.jsonl").write_text(json.dumps(
            {"t": "2026-11-04T10:00:00+00:00", "sessao": "s1", "tipo": "prompt"}) + "\n",
            encoding="utf-8")
        self.assertEqual(len(telemetria.carregar(self.wt, None)), 1)


class SagradosPeloCheckoutPrincipal(ComWorktree):
    def test_do_worktree_nao_escreve_trajetoria_nem_estado_por_caminho_absoluto(self) -> None:
        os.chdir(self.wt)
        for alvo in (self.principal / ".agents" / "execucoes" / "2026-11.jsonl",
                     self.principal / ".agents" / "ciclo" / "SPEC-001.json",
                     self.principal / ".agents" / "quadro" / "forge-x.json"):
            with self.subTest(alvo.name):
                codigo, err = escrever(self.wt, alvo)
                self.assertEqual(codigo, 2)
                self.assertIn("escrita bloqueada", err)
        self.assertEqual(escrever(self.wt, self.wt / "src" / "app.py")[0], 0)


class ConstrucaoNoCheckoutPrincipal(ComWorktree):
    def construindo_no_principal(self) -> None:
        self.git(self.principal, "checkout", "-q", "-b", "feat/SPEC-002")
        self.assertEqual(self.em(self.principal, ciclo, "abrir", "SPEC-002", "--spec-aprovada"), 0)

    def test_avisa_uma_vez_e_so_no_checkout_principal_com_o_ciclo_construindo(self) -> None:
        self.construindo_no_principal()
        codigo, err = escrever(self.principal, self.principal / "src" / "app.py")
        self.assertEqual(codigo, 1)                                       # aviso, não bloqueio
        self.assertIn("o ciclo SPEC-002 está construindo aqui", err)
        self.assertIn("git worktree add .worktrees/<SPEC> -b forge/<SPEC>", err)
        self.assertEqual(escrever(self.principal, self.principal / "src" / "outro.py")[0], 0)
        self.assertEqual(escrever(self.principal, self.principal / "tests" / "test_app.py", "s2")[0], 0)
        self.assertEqual(escrever(self.principal, self.principal / "docs" / "nota.md", "s3")[0], 0)
        self.assertEqual(escrever(self.wt, self.wt / "src" / "app.py", "s4")[0], 0)   # worktree: é o lugar
        rastro = [json.loads(l) for p in (self.principal / ".agents" / "execucoes").glob("*.jsonl")
                  for l in p.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["classe"] for r in rastro if r.get("tipo") == "recusa"], ["checkout"] * 2)

    def test_sem_ciclo_construindo_fica_quieto_e_a_config_endurece(self) -> None:
        self.git(self.principal, "checkout", "-q", "-b", "feat/SPEC-002")
        self.assertEqual(self.em(self.principal, ciclo, "abrir", "SPEC-002"), 0)   # enquadrando
        self.assertEqual(escrever(self.principal, self.principal / "src" / "app.py")[0], 0)
        cfg = self.principal / ".agents" / "guardrails.json"
        cfg.write_text(json.dumps({"checkout_principal": "sempre"}), encoding="utf-8")
        codigo, err = escrever(self.principal, self.principal / "src" / "app.py", "s5")
        self.assertEqual(codigo, 1)
        self.assertIn("a regra do projeto pede worktree", err)
        cfg.write_text(json.dumps({"checkout_principal": "sempre", "modos": {"checkout": "bloqueio"}}),
                       encoding="utf-8")
        self.assertEqual(escrever(self.principal, self.principal / "src" / "app.py", "s5")[0], 2)
        cfg.write_text(json.dumps({"checkout_principal": "sempre", "liberados": ["src/**"]}),
                       encoding="utf-8")
        self.assertEqual(escrever(self.principal, self.principal / "src" / "app.py", "s6")[0], 0)

    def test_ciclo_construindo_noutro_branch_nao_e_deste_checkout(self) -> None:
        self.assertEqual(self.em(self.wt, ciclo, "abrir", "SPEC-001", "--spec-aprovada"), 0)
        self.assertEqual(escrever(self.principal, self.principal / "src" / "app.py")[0], 0)
        self.assertIsNone(guardrail.checkout_principal(Path(self._tmp.name) / "fora" / "x.py"))


class CopiaAvulsaSemExecucao(unittest.TestCase):
    """Script copiado sozinho, sem o execucao.py ao lado: o estado volta a ser relativo ao
    diretório atual, como era antes da emenda, e a classe `checkout` não dispara."""

    def carregar(self, nome: str):
        spec = importlib.util.spec_from_file_location(f"_avulso_{nome}", RAIZ / f"{nome}.py")
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo

    def test_cada_script_cai_no_caminho_de_sempre(self) -> None:
        with mock.patch.dict(sys.modules, {"execucao": None}):
            self.assertEqual(self.carregar("ciclo").pasta_do_estado(), Path(".agents/ciclo"))
            self.assertEqual(self.carregar("quadro").pasta_do_estado(), Path(".agents/quadro"))
            for nome in ("painel", "telemetria", "prova"):
                with self.subTest(nome):
                    self.assertEqual(self.carregar(nome).pasta_do_projeto("/p", "ciclo"),
                                     Path("/p/.agents/ciclo"))
            self.assertIs(guardrail._eh_producao("src/app.py"), False)
        self.assertIs(guardrail._eh_producao("src/app.py"), True)


if __name__ == "__main__":
    unittest.main()
