import unittest

from vendas.servidor import servir_relatorio


class Download(unittest.TestCase):
    def test_baixa_o_relatorio(self) -> None:
        self.assertIn(b"exemplo", servir_relatorio("exemplo.txt"))

    def test_recusa_quem_sobe_de_pasta(self) -> None:
        for nome in ("../dados/vendas.csv", "a/../../segredo", "..", ""):
            with self.subTest(nome=nome), self.assertRaises(ValueError):
                servir_relatorio(nome)


if __name__ == "__main__":
    unittest.main()
