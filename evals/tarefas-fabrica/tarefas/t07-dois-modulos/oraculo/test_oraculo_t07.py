import unittest

from vendas.agregacao import por_regiao
from vendas.formato import formatar_reais


class Oraculo(unittest.TestCase):
    def test_por_regiao_ignora_invalidas(self) -> None:
        vendas = [{"regiao": "Sul", "valor": "10"}, {"regiao": "Sul", "valor": "abc"},
                  {"regiao": "Norte", "valor": ""}, {"regiao": "Sul", "valor": "2.5"}]
        self.assertEqual(por_regiao(vendas), {"Sul": 12.5})

    def test_formatar_reais(self) -> None:
        self.assertEqual(formatar_reais(1234.56), "R$ 1.234,56")
        self.assertEqual(formatar_reais(0), "R$ 0,00")
        self.assertEqual(formatar_reais(1234567.8), "R$ 1.234.567,80")
        self.assertEqual(formatar_reais(-1234.56), "-R$ 1.234,56")


if __name__ == "__main__":
    unittest.main()
