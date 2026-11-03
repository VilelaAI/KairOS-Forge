import unittest

from vendas.regiao import media_por_regiao


class Media(unittest.TestCase):
    def test_media_simples(self) -> None:
        vendas = [{"regiao": "Sul", "valor": "10"}, {"regiao": "Sul", "valor": "20"}]
        self.assertEqual(media_por_regiao(vendas), {"Sul": 15.0})


if __name__ == "__main__":
    unittest.main()
