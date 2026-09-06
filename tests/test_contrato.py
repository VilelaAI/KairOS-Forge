"""contrato.py — módulo puro: string entra, resultado sai, nunca lança (ADR-0032/0040)."""
from __future__ import annotations

import json
import sys
import unittest

from tests.apoio import RAIZ, fence

sys.path.insert(0, str(RAIZ / "scripts"))
import contrato  # noqa: E402


class TestExtracao(unittest.TestCase):
    def test_ultimo_bloco_fechado_vence(self):
        texto = fence("kairos-validacao", {"veredicto": "bloqueado", "bloqueios": 9}) + \
                fence("kairos-validacao", {"veredicto": "aprovado", "bloqueios": 0,
                                           "verificado": ["EXP-01"]})
        r = contrato.ler_validacao(texto)
        self.assertTrue(r.ok, r.erro)
        self.assertEqual(r.dados["veredicto"], "aprovado")

    def test_bloco_nao_fechado_nao_conta(self):
        texto = "# x\n```kairos-validacao\n{\"veredicto\": \"aprovado\", \"bloqueios\": 0}\n"
        r = contrato.ler_validacao(texto)
        self.assertFalse(r.ok)
        self.assertEqual(r.codigo, contrato.AUSENTE)

    def test_tolera_crlf_e_indentacao(self):
        texto = ("# x\r\n   ```kairos-revisao\r\n" +
                 json.dumps({"veredicto": "aprovado", "faixa": 1, "criticos": 0,
                             "examinado": ["src/a.py"]}) + "\r\n   ```\r\n")
        self.assertTrue(contrato.ler_revisao(texto).ok)

    def test_fence_errada_nao_e_aceita(self):
        texto = fence("kairos-revisao", {"veredicto": "aprovado", "faixa": 1, "criticos": 0,
                                         "examinado": ["a"]})
        self.assertEqual(contrato.ler_validacao(texto).codigo, contrato.AUSENTE)

    def test_nunca_lanca(self):
        for entrada in ("", None, "```kairos-validacao\n{nao json\n```", "x" * 10000):
            r = contrato.ler_validacao(entrada)  # type: ignore[arg-type]
            self.assertFalse(r.ok)


class TestCoerenciaECobertura(unittest.TestCase):
    def test_bloqueado_com_zero_bloqueios_e_incoerente(self):
        r = contrato.ler_validacao(fence("kairos-validacao",
                                         {"veredicto": "bloqueado", "bloqueios": 0}))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)

    def test_aprovado_com_bloqueios_e_incoerente(self):
        r = contrato.ler_validacao(fence("kairos-validacao",
                                         {"veredicto": "aprovado", "bloqueios": 2,
                                          "verificado": ["x"]}))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)

    def test_limpo_sem_lista_do_que_foi_olhado_e_sem_cobertura(self):
        r = contrato.ler_validacao(fence("kairos-validacao",
                                         {"veredicto": "aprovado", "bloqueios": 0,
                                          "verificado": []}))
        self.assertEqual(r.codigo, contrato.SEM_COBERTURA)
        r = contrato.ler_revisao(fence("kairos-revisao",
                                       {"veredicto": "aprovado", "faixa": 2, "criticos": 0}))
        self.assertEqual(r.codigo, contrato.SEM_COBERTURA)

    def test_bloqueado_nao_exige_cobertura(self):
        r = contrato.ler_validacao(fence("kairos-validacao",
                                         {"veredicto": "bloqueado", "bloqueios": 3}))
        self.assertTrue(r.ok)
        self.assertEqual(r.dados["bloqueios"], 3)

    def test_critica_exige_dois_criticos_distintos(self):
        base = {"veredicto": "aprovado", "achados": 0, "examinado": ["objetivo"]}
        um = contrato.ler_critica(fence("kairos-critica", {**base, "criticado_por": ["Helena"]}))
        self.assertEqual(um.codigo, contrato.ESTRUTURAL)
        repetido = contrato.ler_critica(fence("kairos-critica",
                                              {**base, "criticado_por": ["helena", "Helena"]}))
        self.assertEqual(repetido.codigo, contrato.ESTRUTURAL)
        dois = contrato.ler_critica(fence("kairos-critica",
                                          {**base, "criticado_por": ["Helena", "Patrícia"]}))
        self.assertTrue(dois.ok, dois.erro)

    def test_faixa_invalida_na_revisao(self):
        r = contrato.ler_revisao(fence("kairos-revisao", {"veredicto": "aprovado", "faixa": 4,
                                                          "criticos": 0, "examinado": ["a"]}))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)

    def test_lista_absurda_e_recusada(self):
        r = contrato.ler_validacao(fence("kairos-validacao",
                                         {"veredicto": "aprovado", "bloqueios": 0,
                                          "verificado": ["x"] * (contrato.MAX_ITENS + 1)}))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)


class TestGateQueNaoRodou(unittest.TestCase):
    """ADR-0040: `executado: false` separa status do gate de veredicto sobre o trabalho."""

    def test_nao_executado_com_motivo_e_aceito_sem_contagem(self):
        for leitor, nome, campo in ((contrato.ler_validacao, "kairos-validacao", "bloqueios"),
                                    (contrato.ler_revisao, "kairos-revisao", "criticos"),
                                    (contrato.ler_critica, "kairos-critica", "achados")):
            with self.subTest(nome=nome):
                r = leitor(fence(nome, {"executado": False, "veredicto": "nao_executado",
                                        "motivo": "npm test: dependência nativa não compila"}))
                self.assertTrue(r.ok, r.erro)
                self.assertEqual(r.dados["veredicto"], "nao_executado")
                self.assertIsNone(r.dados[campo])
                self.assertFalse(r.dados["executado"])

    def test_nao_executado_sem_motivo_e_recusado(self):
        r = contrato.ler_validacao(fence("kairos-validacao",
                                         {"executado": False, "veredicto": "nao_executado"}))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)

    def test_executado_false_com_veredicto_de_trabalho_e_incoerente(self):
        r = contrato.ler_validacao(fence("kairos-validacao",
                                         {"executado": False, "veredicto": "bloqueado",
                                          "bloqueios": 2, "motivo": "x"}))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)

    def test_nao_executado_sem_a_flag_e_incoerente(self):
        r = contrato.ler_validacao(fence("kairos-validacao",
                                         {"veredicto": "nao_executado", "bloqueios": 0}))
        self.assertEqual(r.codigo, contrato.ESTRUTURAL)

    def test_relatorio_normal_declara_executado_true(self):
        r = contrato.ler_validacao(fence("kairos-validacao",
                                         {"veredicto": "aprovado", "bloqueios": 0,
                                          "verificado": ["EXP-01"]}))
        self.assertTrue(r.dados["executado"])


class TestEsquemaPublico(unittest.TestCase):
    def test_esquema_declara_o_que_o_codigo_faz(self):
        e = contrato.contrato_publico()
        self.assertEqual(e["versao"], contrato.CONTRATO_VERSAO)
        self.assertEqual(e["veredicto_sem_gate"], contrato.NAO_EXECUTADO)
        for nome, rel in e["relatorios"].items():
            with self.subTest(nome=nome):
                self.assertIn("executado", rel["opcionais"])
                self.assertIn("motivo", rel["opcionais"])
        fences = {rel["fence"] for rel in e["relatorios"].values()}
        self.assertEqual(len(fences), 3, "as três fences precisam ser distintas")


if __name__ == "__main__":
    unittest.main()
