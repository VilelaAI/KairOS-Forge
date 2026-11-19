import unittest

from vendas.relatorio import total


class Total(unittest.TestCase):
    def test_soma_os_valores(self) -> None:
        vendas = [{"regiao": "Sul", "valor": "1.000,00"}, {"regiao": "Sul", "valor": "50,50"}]
        self.assertAlmostEqual(total(vendas), 1050.50)


if __name__ == "__main__":
    unittest.main()
