import unittest

from vendas.servidor import servir_relatorio


class Download(unittest.TestCase):
    def test_baixa_o_relatorio(self) -> None:
        self.assertIn(b"exemplo", servir_relatorio("exemplo.txt"))


if __name__ == "__main__":
    unittest.main()
