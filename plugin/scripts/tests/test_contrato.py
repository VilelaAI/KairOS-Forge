"""Testes do `contrato.py` — a completude da revisão (contrato 1.1, ADR-0046).

Só stdlib. O módulo é puro: string entra, resultado sai.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import contrato  # noqa: E402


def revisao(**campos) -> str:
    bloco = {"veredicto": "aprovado", "faixa": 1, "criticos": 0,
             "examinado": ["api.py (Helena)", "api.py (Patrícia)"], **campos}
    return f"# Revisão\n\n```kairos-revisao\n{json.dumps(bloco, ensure_ascii=False)}\n```\n"


class CompletudeDaRevisao(unittest.TestCase):
    def test_relatorio_sem_o_campo_continua_valendo(self) -> None:
        r = contrato.ler_revisao(revisao())
        self.assertTrue(r.ok, r.erro)
        self.assertEqual(r.dados["incompletos"], [])

    def test_revisor_que_nao_rodou_nao_aprova(self) -> None:
        for veredicto in ("aprovado", "aprovado_com_ressalvas"):
            r = contrato.ler_revisao(revisao(veredicto=veredicto, incompletos=["Patrícia"]))
            self.assertFalse(r.ok, veredicto)
            self.assertEqual(r.codigo, contrato.SEM_COBERTURA)
            self.assertIn("Patrícia", r.erro)

    def test_incompleta_ja_bloqueada_e_coerente(self) -> None:
        r = contrato.ler_revisao(revisao(veredicto="bloqueado", criticos=1,
                                         incompletos=["Vinícius"]))
        self.assertTrue(r.ok, r.erro)
        self.assertEqual(r.dados["incompletos"], ["Vinícius"])

    def test_incompletos_que_nao_e_lista_e_estrutural(self) -> None:
        r = contrato.ler_revisao(revisao(incompletos="Patrícia"))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)

    def test_coerencia_e_cobertura_continuam_valendo(self) -> None:
        casos = [({"veredicto": "bloqueado"}, contrato.ESTRUTURAL, "criticos=0"),
                 ({"criticos": 1}, contrato.ESTRUTURAL, "não vira ressalva"),
                 ({"examinado": []}, contrato.SEM_COBERTURA, "ausência de busca")]
        for campos, codigo, trecho in casos:
            r = contrato.ler_revisao(revisao(**campos))
            self.assertEqual(r.codigo, codigo, campos)
            self.assertIn(trecho, r.erro)

    def test_esquema_publica_o_campo_e_a_versao(self) -> None:
        c = contrato.contrato_publico()
        self.assertEqual(c["versao"], "1.2")
        self.assertEqual(c["relatorios"]["revisao"]["opcionais"],
                         {"incompletos": "string[]", "achados": "string[]",
                          "anteriores": "object<string,resolvido|nao_resolvido>"})
        self.assertEqual(c["relatorios"]["validacao"]["opcionais"],
                         {"spec": "string", "sem_evidencia": "integer>=0"})


def validacao(**campos) -> str:
    bloco = {"veredicto": "bloqueado", "bloqueios": 2, "verificado": ["EX-01 (npm test)"],
             **campos}
    return f"# Validação\n\n```kairos-validacao\n{json.dumps(bloco, ensure_ascii=False)}\n```\n"


class FaltaDeProva(unittest.TestCase):
    """ADR-0048, do NOT_PROVEN da Alethe: falta de prova não é falha mostrada."""

    def test_sem_o_campo_nada_muda(self) -> None:
        r = contrato.ler_validacao(validacao())
        self.assertTrue(r.ok, r.erro)
        self.assertEqual(r.dados["sem_evidencia"], 0)
        self.assertFalse(r.dados["so_falta_prova"])

    def test_todos_os_bloqueios_sem_evidencia(self) -> None:
        r = contrato.ler_validacao(validacao(sem_evidencia=2))
        self.assertTrue(r.ok, r.erro)
        self.assertTrue(r.dados["so_falta_prova"])

    def test_parte_dos_bloqueios_sem_evidencia_ainda_e_falha(self) -> None:
        r = contrato.ler_validacao(validacao(sem_evidencia=1))
        self.assertTrue(r.ok, r.erro)
        self.assertFalse(r.dados["so_falta_prova"])

    def test_mais_sem_evidencia_que_bloqueios_e_estrutural(self) -> None:
        r = contrato.ler_validacao(validacao(sem_evidencia=3))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)

    def test_spec_vem_do_bloco_ou_fica_nula(self) -> None:
        self.assertEqual(contrato.ler_validacao(validacao(spec=" SPEC-001 ")).dados["spec"],
                         "SPEC-001")
        self.assertIsNone(contrato.ler_validacao(validacao()).dados["spec"])

    def test_aprovado_sem_bloqueio_nao_e_so_falta_de_prova(self) -> None:
        r = contrato.ler_validacao(validacao(veredicto="aprovado", bloqueios=0))
        self.assertTrue(r.ok, r.erro)
        self.assertFalse(r.dados["so_falta_prova"])


class ReRevisao(unittest.TestCase):
    """ADR-0048, do ADDRESSED / NOT ADDRESSED da Alethe."""

    def test_ids_dos_criticos_batem_com_a_contagem(self) -> None:
        ok = contrato.ler_revisao(revisao(veredicto="bloqueado", criticos=2,
                                          achados=["R1", "R2"]))
        self.assertTrue(ok.ok, ok.erro)
        self.assertEqual(ok.dados["achados"], ["R1", "R2"])
        r = contrato.ler_revisao(revisao(veredicto="bloqueado", criticos=2, achados=["R1"]))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)
        r = contrato.ler_revisao(revisao(veredicto="bloqueado", criticos=2,
                                         achados=["R1", "r1"]))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)

    def test_achados_que_nao_e_lista_e_estrutural(self) -> None:
        r = contrato.ler_revisao(revisao(veredicto="bloqueado", criticos=1, achados="R1"))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)
        self.assertIn("achados", r.erro)

    def test_faixa(self) -> None:
        self.assertEqual(contrato.ler_revisao(revisao(faixa="2")).dados["faixa"], 2)
        for faixa in (4, "três", None):
            r = contrato.ler_revisao(revisao(faixa=faixa))
            self.assertEqual(r.codigo, contrato.ESTRUTURAL, faixa)
            self.assertIn("faixa", r.erro)

    def test_anterior_nao_resolvido_nao_aprova(self) -> None:
        r = contrato.ler_revisao(revisao(anteriores={"R1": "não resolvido"}))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)
        self.assertIn("R1", r.erro)

    def test_estado_anterior_invalido_e_estrutural(self) -> None:
        r = contrato.ler_revisao(revisao(anteriores={"R1": "talvez"}))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)
        r = contrato.ler_revisao(revisao(anteriores=["R1"]))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)

    def test_prestar_contas(self) -> None:
        limpo = contrato.ler_revisao(revisao(anteriores={"R1": "resolvido", "r2": "Resolvido"}))
        self.assertTrue(limpo.ok, limpo.erro)
        self.assertIsNone(contrato.prestar_contas([], limpo.dados))
        self.assertIsNone(contrato.prestar_contas(["R1", "R2"], limpo.dados))
        erro = contrato.prestar_contas(["R1", "R2", "R3"], limpo.dados)
        self.assertIn("R3", erro)
        aberto = contrato.ler_revisao(revisao(veredicto="bloqueado", criticos=1, achados=["R1"],
                                              anteriores={"R1": "nao_resolvido"}))
        self.assertIn("R1", contrato.prestar_contas(["R1"], aberto.dados))

    def test_pendentes_depois_junta_novos_e_nao_resolvidos(self) -> None:
        r = contrato.ler_revisao(revisao(veredicto="bloqueado", criticos=2, achados=["R1", "R4"],
                                         anteriores={"R1": "nao_resolvido", "R2": "resolvido"}))
        self.assertTrue(r.ok, r.erro)
        self.assertEqual(contrato.pendentes_depois(["R1", "R2", "R3"], r.dados),
                         ["R1", "R3", "R4"])


if __name__ == "__main__":
    unittest.main()
