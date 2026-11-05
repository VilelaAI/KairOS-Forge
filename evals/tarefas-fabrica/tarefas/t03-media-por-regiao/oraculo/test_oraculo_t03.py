import unittest

from vendas.regiao import media_por_regiao


class Oraculo(unittest.TestCase):
    def test_invalida_nao_entra_na_soma_nem_na_contagem(self) -> None:
        vendas = [{"regiao": "Sul", "valor": "10"}, {"regiao": "Sul", "valor": ""},
                  {"regiao": "Sul", "valor": "abc"}, {"regiao": "Sul", "valor": "20"}]
        self.assertEqual(media_por_regiao(vendas), {"Sul": 15.0})

    def test_regiao_so_com_invalidas_nao_aparece(self) -> None:
        vendas = [{"regiao": "Norte", "valor": ""}, {"regiao": "Sul", "valor": "5"}]
        self.assertEqual(media_por_regiao(vendas), {"Sul": 5.0})

    def test_arredonda_em_duas_casas(self) -> None:
        vendas = [{"regiao": "Sul", "valor": "1"}, {"regiao": "Sul", "valor": "1"},
                  {"regiao": "Sul", "valor": "2"}]
        self.assertEqual(media_por_regiao(vendas), {"Sul": 1.33})


if __name__ == "__main__":
    unittest.main()
