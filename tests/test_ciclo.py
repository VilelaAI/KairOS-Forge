"""ciclo.py — a máquina de estados do arco, testada como CLI (ADR-0029/0032/0034/0040)."""
from __future__ import annotations

import json
import os
import sys
import unittest
from unittest import mock

from tests.apoio import RAIZ, Repositorio, escrever, fence, rodar

CICLO = ".agents/ciclo/SPEC-001.json"


def estado(raiz):
    r = rodar("ciclo.py", "estado", "SPEC-001", "--json", cwd=raiz)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def relatorio_validacao(raiz, dados, dia="2026-09-06"):
    escrever(raiz, f"docs/specs/validacoes/VALIDACAO-SPEC-001-{dia}.md",
             fence("kairos-validacao", dados))


class TestAbrirEEstado(unittest.TestCase):
    def test_abrir_publica_o_contrato(self):
        with Repositorio() as raiz:
            r = rodar("ciclo.py", "abrir", "SPEC-001", cwd=raiz)
            self.assertEqual(r.returncode, 0, r.stderr)
            e = estado(raiz)
            self.assertEqual(e["estado"], "enquadrando")
            self.assertFalse(e["terminal"])
            self.assertFalse(e["aguardando_humano"])
            self.assertIsNone(e["gate"])
            self.assertEqual(e["resultados_validos"], ["entendimento_pronto"])
            for campo in ("contrato", "orcamento", "rodadas", "rodadas_totais", "teto",
                          "marca", "historico", "proximo_passo"):
                self.assertIn(campo, e)

    def test_spec_aprovada_comeca_em_construindo(self):
        with Repositorio() as raiz:
            rodar("ciclo.py", "abrir", "SPEC-001", "--spec-aprovada", cwd=raiz)
            self.assertEqual(estado(raiz)["estado"], "construindo")

    def test_abrir_duas_vezes_e_recusado(self):
        with Repositorio() as raiz:
            rodar("ciclo.py", "abrir", "SPEC-001", cwd=raiz)
            antes = (raiz / CICLO).read_bytes()
            r = rodar("ciclo.py", "abrir", "SPEC-001", cwd=raiz)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual((raiz / CICLO).read_bytes(), antes)

    def test_contrato_publica_o_grafo_inteiro(self):
        with Repositorio() as raiz:
            r = rodar("ciclo.py", "contrato", cwd=raiz)
            c = json.loads(r.stdout)
            self.assertEqual(c["nome"], "kairos-forge/ciclo")
            self.assertIn("corrigindo_revisao", c["transicoes"])
            self.assertEqual(c["transicoes"]["corrigindo_revisao"], {"pronto": "validando"})
            self.assertEqual(set(c["gates"]), {"criticar", "validar", "revisar"})


class TestTransicoes(unittest.TestCase):
    def test_resultado_invalido_nao_muda_o_estado(self):
        with Repositorio() as raiz:
            rodar("ciclo.py", "abrir", "SPEC-001", cwd=raiz)
            antes = (raiz / CICLO).read_bytes()
            r = rodar("ciclo.py", "registrar", "aprovada", cwd=raiz)
            self.assertEqual(r.returncode, 1)
            self.assertIn("não é válido", r.stderr)
            self.assertEqual((raiz / CICLO).read_bytes(), antes)

    def test_gates_humanos_sao_marcados_como_tal(self):
        with Repositorio() as raiz:
            rodar("ciclo.py", "abrir", "SPEC-001", cwd=raiz)
            rodar("ciclo.py", "registrar", "entendimento_pronto", cwd=raiz)
            e = estado(raiz)
            self.assertEqual(e["estado"], "aguardando_entendimento")
            self.assertTrue(e["aguardando_humano"])
            self.assertEqual(e["resultados_validos"], ["ajustar", "confirmado"])

    def test_correcao_de_revisao_reabre_a_validacao(self):
        with Repositorio() as raiz:
            rodar("ciclo.py", "abrir", "SPEC-001", "--spec-aprovada", cwd=raiz)
            rodar("ciclo.py", "registrar", "pronto", cwd=raiz)          # validando
            relatorio_validacao(raiz, {"veredicto": "aprovado", "bloqueios": 0,
                                       "verificado": ["EXP-01"]})
            rodar("ciclo.py", "registrar", "aprovado", cwd=raiz)        # revisando
            escrever(raiz, "docs/specs/revisoes/REVISAO-SPEC-001-2026-09-06.md",
                     fence("kairos-revisao", {"veredicto": "bloqueado", "faixa": 1,
                                              "criticos": 2}))
            r = rodar("ciclo.py", "registrar", "critico", cwd=raiz)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(estado(raiz)["estado"], "corrigindo_revisao")
            rodar("ciclo.py", "registrar", "pronto", cwd=raiz)
            self.assertEqual(estado(raiz)["estado"], "validando",
                             "corrigindo_revisao só sai para validando (ADR-0029)")

    def test_estado_terminal_nao_aceita_registro(self):
        with Repositorio() as raiz:
            rodar("ciclo.py", "abrir", "SPEC-001", cwd=raiz)
            rodar("ciclo.py", "encerrar", "--motivo", "teste", cwd=raiz)
            e = estado(raiz)
            self.assertTrue(e["terminal"])
            r = rodar("ciclo.py", "registrar", "entendimento_pronto", cwd=raiz)
            self.assertEqual(r.returncode, 1)


class TestVeredictoVemDoArtefato(unittest.TestCase):
    """handoff-02: relatório bloqueado em disco, `registrar aprovado` é recusado."""

    def _em_validando(self, raiz):
        rodar("ciclo.py", "abrir", "SPEC-001", "--spec-aprovada", cwd=raiz)
        rodar("ciclo.py", "registrar", "pronto", cwd=raiz)
        self.assertEqual(estado(raiz)["estado"], "validando")

    def test_aprovado_sem_relatorio_e_recusado(self):
        with Repositorio() as raiz:
            self._em_validando(raiz)
            antes = (raiz / CICLO).read_bytes()
            r = rodar("ciclo.py", "registrar", "aprovado", cwd=raiz)
            self.assertEqual(r.returncode, 1)
            self.assertIn("não encontrei relatório", r.stderr)
            self.assertEqual((raiz / CICLO).read_bytes(), antes)

    def test_aprovado_contra_relatorio_bloqueado_e_recusado(self):
        with Repositorio() as raiz:
            self._em_validando(raiz)
            relatorio_validacao(raiz, {"veredicto": "bloqueado", "bloqueios": 2})
            antes = (raiz / CICLO).read_bytes()
            r = rodar("ciclo.py", "registrar", "aprovado", cwd=raiz)
            self.assertEqual(r.returncode, 1)
            self.assertIn("BLOQUEADO", r.stderr)
            self.assertEqual((raiz / CICLO).read_bytes(), antes)

    def test_gate_que_nao_rodou_nao_avanca_nem_queima_rodada(self):
        """ADR-0040: `executado: false` não é achado sobre o trabalho."""
        with Repositorio() as raiz:
            self._em_validando(raiz)
            relatorio_validacao(raiz, {"executado": False, "veredicto": "nao_executado",
                                       "motivo": "banco de teste fora do ar"})
            antes = (raiz / CICLO).read_bytes()
            for resultado in ("aprovado", "bloqueado", "aprovado_com_ressalvas"):
                with self.subTest(resultado=resultado):
                    r = rodar("ciclo.py", "registrar", resultado, cwd=raiz)
                    self.assertEqual(r.returncode, 1)
                    self.assertIn("NÃO RODOU", r.stderr)
                    self.assertEqual((raiz / CICLO).read_bytes(), antes)
            self.assertEqual(estado(raiz)["rodadas"]["validar"], 0)


class TestOrcamento(unittest.TestCase):
    """repetida-02: orçamento de 2 e validação que bloqueia sempre → escala na 3ª."""

    def _bloquear(self, raiz, bloqueios, dia):
        escrever(raiz, f"docs/specs/validacoes/VALIDACAO-SPEC-001-{dia}.md",
                 fence("kairos-validacao", {"veredicto": "bloqueado", "bloqueios": bloqueios}))
        r = rodar("ciclo.py", "registrar", "bloqueado", cwd=raiz)
        self.assertEqual(r.returncode, 0, r.stderr)
        return estado(raiz)

    def test_sem_progresso_escala_na_terceira(self):
        with Repositorio() as raiz:
            rodar("ciclo.py", "abrir", "SPEC-001", "--spec-aprovada",
                  "--orcamento-validar", "2", cwd=raiz)
            rodar("ciclo.py", "registrar", "pronto", cwd=raiz)
            e = self._bloquear(raiz, 3, "2026-09-01")
            self.assertEqual((e["estado"], e["rodadas"]["validar"]), ("corrigindo_validacao", 1))
            rodar("ciclo.py", "registrar", "pronto", cwd=raiz)
            e = self._bloquear(raiz, 3, "2026-09-02")
            self.assertEqual((e["estado"], e["rodadas"]["validar"]), ("corrigindo_validacao", 2))
            rodar("ciclo.py", "registrar", "pronto", cwd=raiz)
            e = self._bloquear(raiz, 3, "2026-09-03")
            self.assertEqual(e["estado"], "escalado")
            self.assertTrue(e["terminal"])
            self.assertIn("sem progresso", e["motivo_escalacao"])

    def test_progresso_real_devolve_a_ficha(self):
        """ADR-0032: bloqueios caindo zera as rodadas sem progresso."""
        with Repositorio() as raiz:
            rodar("ciclo.py", "abrir", "SPEC-001", "--spec-aprovada",
                  "--orcamento-validar", "2", cwd=raiz)
            rodar("ciclo.py", "registrar", "pronto", cwd=raiz)
            self._bloquear(raiz, 5, "2026-09-01")
            rodar("ciclo.py", "registrar", "pronto", cwd=raiz)
            e = self._bloquear(raiz, 2, "2026-09-02")
            self.assertEqual(e["rodadas"]["validar"], 0, "ficha devolvida")
            self.assertEqual(e["marca"]["validar"], 2)
            self.assertEqual(e["rodadas_totais"]["validar"], 2)

    def test_teto_absoluto_vale_mesmo_com_progresso(self):
        with Repositorio() as raiz:
            rodar("ciclo.py", "abrir", "SPEC-001", "--spec-aprovada",
                  "--orcamento-validar", "2", "--teto-validar", "3", cwd=raiz)
            rodar("ciclo.py", "registrar", "pronto", cwd=raiz)
            for i, b in enumerate((9, 8, 7), start=1):
                e = self._bloquear(raiz, b, f"2026-09-0{i}")
                if e["estado"] != "escalado":
                    rodar("ciclo.py", "registrar", "pronto", cwd=raiz)
            self.assertEqual(e["estado"], "escalado")
            self.assertIn("teto absoluto", e["motivo_escalacao"])


class TestPublicacaoAtomica(unittest.TestCase):
    """ADR-0040: falha ao publicar deixa o estado anterior íntegro e nenhum .tmp."""

    def test_falha_no_replace_preserva_o_estado(self):
        with Repositorio() as raiz:
            rodar("ciclo.py", "abrir", "SPEC-001", cwd=raiz)
            antes = (raiz / CICLO).read_bytes()
            sys.path.insert(0, str(RAIZ / "scripts"))
            import ciclo  # noqa: E402
            cwd = os.getcwd()
            os.chdir(raiz)
            try:
                with mock.patch.object(ciclo.os, "replace", side_effect=OSError("disco cheio")):
                    with self.assertRaises(OSError):
                        ciclo.registrar("SPEC-001", "entendimento_pronto", None)
            finally:
                os.chdir(cwd)
            self.assertEqual((raiz / CICLO).read_bytes(), antes)
            self.assertEqual(list((raiz / ".agents/ciclo").glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
