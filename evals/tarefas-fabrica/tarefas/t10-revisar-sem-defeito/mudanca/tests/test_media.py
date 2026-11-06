import contextlib
import io
import unittest

from vendas.relatorio import main, media


class Media(unittest.TestCase):
    def test_media_das_validas(self) -> None:
        vendas = [{"valor": "100.00"}, {"valor": "50.50"}]
        self.assertAlmostEqual(media(vendas), 75.25)

    def test_linha_invalida_nao_entra_na_conta(self) -> None:
        self.assertAlmostEqual(media([{"valor": "100.00"}, {"valor": "abc"}, {"valor": ""}]), 100.0)

    def test_sem_venda_valida_e_zero(self) -> None:
        self.assertEqual(media([]), 0.0)
        self.assertEqual(media([{"valor": "abc"}]), 0.0)

    def test_o_relatorio_mostra_a_media(self) -> None:
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            self.assertEqual(main(["dados/vendas.csv"]), 0)
        self.assertRegex(saida.getvalue(), r"Média: R\$ \d+\.\d{2}")


if __name__ == "__main__":
    unittest.main()
