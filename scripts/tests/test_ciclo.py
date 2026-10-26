"""Testes do `ciclo.py` — os contratos de que um runner externo depende (ADR-0034).

Só stdlib. Cada teste roda num diretório temporário com `docs/specs/` e `.agents/ciclo/`
próprios, porque o `ciclo.py` trabalha relativo ao cwd — igual ao runner real.

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
import ciclo  # noqa: E402

SPEC = """# SPEC-001 — Exemplo

## Requisitos rastreáveis

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| EX-01 | Exportar lista | P1 | WHEN clica THEN baixa CSV em ≤ 2 s | Pendente | — |
"""

VALIDACAO_OK = """# Validação — SPEC-001

**Veredicto:** aprovado

```kairos-validacao
{"spec": "SPEC-001", "veredicto": "aprovado", "bloqueios": 0, "verificado": ["EX-01 (npm test)"]}
```
"""


def rodar(*args: str) -> tuple[int, str, str]:
    """Chama o `main()` do ciclo.py como a CLI faria; devolve (exit, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    antigo = sys.argv
    sys.argv = ["ciclo.py", *args]
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                codigo = ciclo.main()
            except SystemExit as e:  # `resolver` usa sys.exit em erro
                codigo = 1 if e.code else 0
                if isinstance(e.code, str):
                    err.write(e.code)
    finally:
        sys.argv = antigo
    return int(codigo or 0), out.getvalue(), err.getvalue()


def estado(spec: str = "SPEC-001") -> dict:
    codigo, out, _ = rodar("estado", spec, "--json")
    assert codigo == 0, out
    return json.loads(out)


class Sandbox(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-ciclo-")
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        Path("docs/specs/validacoes").mkdir(parents=True)
        Path("docs/specs/SPEC-001-exemplo.md").write_text(SPEC, encoding="utf-8")

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()


class RegistrarIdempotente(Sandbox):
    """Semântica at-least-once do runner: repetir `registrar` nunca avança dois estados."""

    def test_repetir_resultado_nao_avanca_duas_vezes(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        self.assertEqual(estado()["estado"], "construindo")
        self.assertEqual(rodar("registrar", "pronto", "SPEC-001")[0], 0)
        self.assertEqual(estado()["estado"], "validando")
        codigo, _, err = rodar("registrar", "pronto", "SPEC-001")  # o runner repete
        self.assertEqual(codigo, 1)
        self.assertIn("não é válido", err)
        self.assertEqual(estado()["estado"], "validando")
        self.assertEqual([h["resultado"] for h in estado()["historico"]], ["abrir", "pronto"])

    def test_repetir_em_terminal_e_recusado(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("registrar", "pronto", "SPEC-001")
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(VALIDACAO_OK, encoding="utf-8")
        rodar("registrar", "aprovado", "SPEC-001")
        Path("docs/specs/revisoes").mkdir()
        Path("docs/specs/revisoes/REVISAO-SPEC-001-2026-01-01.md").write_text(
            '# Revisão\n\n**Veredicto:** aprovado\n\n```kairos-revisao\n'
            '{"veredicto": "aprovado", "faixa": 1, "criticos": 0, "examinado": ["x.py (Helena)"]}\n```\n',
            encoding="utf-8")
        rodar("registrar", "limpo", "SPEC-001")
        self.assertEqual(rodar("registrar", "pr_aberto", "SPEC-001")[0], 0)
        e = estado()
        self.assertTrue(e["terminal"])
        codigo, _, err = rodar("registrar", "pr_aberto", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("terminal", err)
        self.assertEqual(estado()["estado"], "encerrado")

    def test_estado_com_spec_explicita_funciona_em_ciclo_encerrado(self) -> None:
        """Achado da POC: sem a SPEC, `estado` falha em ciclo fechado; com ela, responde."""
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("encerrar", "SPEC-001", "--motivo", "teste")
        self.assertTrue(estado()["terminal"])
        codigo, _, _ = rodar("estado", "--json")  # sem SPEC
        self.assertEqual(codigo, 1)


class DigestDaSpec(Sandbox):
    def test_status_e_verificacao_nao_contam(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        self.assertIs(estado()["spec_alterada"], False)
        p = Path("docs/specs/SPEC-001-exemplo.md")
        p.write_text(p.read_text(encoding="utf-8").replace(
            "| Pendente | — |", "| Concluído | verificado: npm test (01/01) |"), encoding="utf-8")
        self.assertIs(estado()["spec_alterada"], False)

    def test_criterio_alterado_recusa_verde_ate_reaprovar(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("registrar", "pronto", "SPEC-001")
        p = Path("docs/specs/SPEC-001-exemplo.md")
        p.write_text(p.read_text(encoding="utf-8").replace("≤ 2 s", "≤ 10 s"), encoding="utf-8")
        self.assertIs(estado()["spec_alterada"], True)
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(VALIDACAO_OK, encoding="utf-8")
        codigo, _, err = rodar("registrar", "aprovado", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("mudou depois da aprovação", err)
        self.assertEqual(rodar("reaprovar", "SPEC-001")[0], 0)
        self.assertIs(estado()["spec_alterada"], False)
        self.assertEqual(rodar("registrar", "aprovado", "SPEC-001")[0], 0)
        self.assertEqual(estado()["estado"], "revisando")

    def test_reaprovar_antes_da_aprovacao_e_recusado(self) -> None:
        """Achado da POC: selar em `enquadrando`/`desenhando` sela um digest que não é contrato."""
        rodar("abrir", "SPEC-001")  # sem --spec-aprovada → enquadrando, sem selo
        self.assertIsNone(estado()["spec_alterada"])
        codigo, _, err = rodar("reaprovar", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("ainda não foi aprovada", err)
        self.assertNotIn("reaprovar", [h["resultado"] for h in estado()["historico"]])

    def test_sem_spec_no_disco_digest_e_null(self) -> None:
        rodar("abrir", "SPEC-999", "--spec-aprovada")
        self.assertIsNone(estado("SPEC-999")["spec_alterada"])


class RelatorioComBlocoInvalido(Sandbox):
    """A prosa é o formato antigo, sem bloco — não a saída de emergência de um bloco que
    o parser recusou. Senão o "limpo sem lista do que foi olhado" (ADR-0032) passa pela
    linha `**Veredicto:**`."""

    def validando_com(self, relatorio: str) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("registrar", "pronto", "SPEC-001")
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(
            relatorio, encoding="utf-8")

    def test_sem_cobertura_nao_aprova(self) -> None:
        self.validando_com(
            "# Validação\n\n**Veredicto:** aprovado\n\n```kairos-validacao\n"
            '{"spec": "SPEC-001", "veredicto": "aprovado", "bloqueios": 0, "verificado": []}\n```\n')
        codigo, _, err = rodar("registrar", "aprovado", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("sem_cobertura", err)
        self.assertEqual(estado()["estado"], "validando")

    def test_bloco_malformado_nao_aprova(self) -> None:
        self.validando_com(
            "# Validação\n\n**Veredicto:** aprovado\n\n```kairos-validacao\n{veredicto: aprovado\n```\n")
        codigo, _, err = rodar("registrar", "aprovado", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("json_invalido", err)
        self.assertEqual(estado()["estado"], "validando")

    def test_prosa_sem_bloco_continua_aceita(self) -> None:
        self.validando_com("# Validação\n\n**Veredicto:** aprovado\n")
        self.assertEqual(rodar("registrar", "aprovado", "SPEC-001")[0], 0)
        self.assertEqual(estado()["estado"], "revisando")
        self.assertEqual(estado()["historico"][-1]["fonte"], "prosa")

    def test_resultado_negativo_com_bloco_invalido_e_aceito(self) -> None:
        # Registrar o negativo é o lado conservador: a rodada só queima ficha.
        self.validando_com(
            "# Validação\n\n**Veredicto:** bloqueado\n\n```kairos-validacao\n{quebrado\n```\n")
        codigo, _, err = rodar("registrar", "bloqueado", "SPEC-001")
        self.assertEqual(codigo, 0)
        self.assertEqual(estado()["estado"], "corrigindo_validacao")
        self.assertEqual(estado()["historico"][-1]["fonte"], "invalido")
        self.assertIn("json_invalido", err)


class BranchDoCiclo(Sandbox):
    """O guardrail julga o `gh pr create` pela branch do ciclo — o `abrir` grava qual é."""

    def test_abrir_grava_a_branch(self) -> None:
        for args in (["init", "-q", "."],
                     ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                      "--allow-empty", "-m", "base"],
                     ["checkout", "-q", "-b", "feat/spec-001"]):
            subprocess.run(["git", *args], check=True, capture_output=True)
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        self.assertEqual(estado()["branch"], "feat/spec-001")

    def test_fora_de_um_repositorio_git_a_branch_e_nula(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        self.assertIsNone(estado()["branch"])


if __name__ == "__main__":
    unittest.main()
