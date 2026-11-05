import unittest

from vendas.servidor import servir_relatorio


class Oraculo(unittest.TestCase):
    def test_download_normal(self) -> None:
        self.assertIn(b"exemplo", servir_relatorio("exemplo.txt"))

    def test_sair_da_pasta_levanta_value_error(self) -> None:
        for nome in ("../dados/vendas.csv", "../../etc/passwd", "/etc/passwd"):
            with self.assertRaises(ValueError, msg=nome):
                servir_relatorio(nome)


if __name__ == "__main__":
    unittest.main()
