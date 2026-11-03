import contextlib
import io
import re
import unittest

from vendas import relatorio

MISTO = [{"valor": "10"}, {"valor": ""}, {"valor": "abc"}, {"valor": "2.5"}]


class Oraculo(unittest.TestCase):
    def test_total_ignora_vazio_e_texto(self) -> None:
        self.assertAlmostEqual(relatorio.total(MISTO), 12.5)

    def test_conta_as_ignoradas(self) -> None:
        self.assertEqual(relatorio.linhas_invalidas(MISTO), 2)
        self.assertEqual(relatorio.linhas_invalidas([{"valor": "1"}]), 0)

    def test_comando_imprime_total_e_ignoradas(self) -> None:
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            codigo = relatorio.main(["dados/vendas.csv"])
        self.assertEqual(codigo or 0, 0)
        self.assertRegex(saida.getvalue(), r"14[.]?600[.,]50")
        self.assertRegex(saida.getvalue(), r"Ignoradas: 2")


if __name__ == "__main__":
    unittest.main()
