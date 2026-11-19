import contextlib
import io
import unittest

from vendas.relatorio import main, maior


class Maior(unittest.TestCase):
    def test_o_maior_valor(self) -> None:
        self.assertEqual(maior([{"valor": "10"}, {"valor": "32.50"}, {"valor": "7"}]), 32.5)

    def test_sem_vendas_e_zero(self) -> None:
        self.assertEqual(maior([]), 0.0)

    def test_o_relatorio_mostra_a_maior(self) -> None:
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            main(["dados/vendas.csv"])
        self.assertIn("Maior venda: R$", saida.getvalue())


if __name__ == "__main__":
    unittest.main()
