import unittest

from vendas.relatorio import ler_vendas, total
from vendas.ticket import ticket_medio
from vendas.valores import para_reais


class Oraculo(unittest.TestCase):
    def test_o_total_de_outubro_bate_com_a_planilha(self) -> None:
        self.assertAlmostEqual(total(ler_vendas("dados/outubro.csv")), 10550.75)

    def test_os_dois_formatos_que_o_erp_exporta(self) -> None:
        for texto, valor in (("1.234,56", 1234.56), ("1200.00", 1200.0), ("850,25", 850.25),
                             (" 300 ", 300.0), ("12.5", 12.5)):
            with self.subTest(texto):
                self.assertAlmostEqual(para_reais(texto), valor)

    def test_o_ticket_medio_usa_a_mesma_conversao(self) -> None:
        # O segundo consumidor da mesma conversão: corrigir só o total não basta.
        self.assertEqual(ticket_medio([{"valor": "100.00"}, {"valor": "1.000,00"}]), 550.0)


if __name__ == "__main__":
    unittest.main()
