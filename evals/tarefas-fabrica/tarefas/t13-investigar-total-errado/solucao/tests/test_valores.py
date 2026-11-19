import unittest

from vendas.valores import para_reais


class ParaReais(unittest.TestCase):
    def test_ponto_decimal_nao_vira_milhar(self) -> None:
        self.assertEqual(para_reais("300.00"), 300.0)
        self.assertEqual(para_reais("2500.00"), 2500.0)

    def test_formato_brasileiro_continua(self) -> None:
        self.assertEqual(para_reais("4.500,50"), 4500.5)


if __name__ == "__main__":
    unittest.main()
