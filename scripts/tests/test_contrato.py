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
        self.assertEqual(c["versao"], "1.1")
        self.assertEqual(c["relatorios"]["revisao"]["opcionais"], {"incompletos": "string[]"})


if __name__ == "__main__":
    unittest.main()
