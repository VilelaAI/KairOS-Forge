import contextlib
import io
import json
import os
import tempfile
import unittest

from vendas import relatorio


class Oraculo(unittest.TestCase):
    def test_json_so_com_validas_em_ordem_de_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destino = os.path.join(tmp, "saida.json")
            with contextlib.redirect_stdout(io.StringIO()):
                relatorio.main(["dados/vendas.csv", "--json", destino])
            linhas = json.load(open(destino, encoding="utf-8"))
        self.assertEqual(len(linhas), 8)
        self.assertEqual([l["data"] for l in linhas], sorted(l["data"] for l in linhas))
        self.assertTrue(all(isinstance(l["valor"], (int, float)) for l in linhas))
        self.assertEqual(set(linhas[0]), {"data", "regiao", "produto", "valor"})
        self.assertAlmostEqual(sum(l["valor"] for l in linhas), 14600.5)

    def test_sem_json_nada_muda(self) -> None:
        csv = os.path.abspath("dados/vendas.csv")
        antes = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                saida = io.StringIO()
                with contextlib.redirect_stdout(saida):
                    relatorio.main([csv])
                criados = os.listdir(tmp)
            finally:
                os.chdir(antes)
        self.assertIn("Ignoradas: 2", saida.getvalue())
        self.assertEqual(criados, [])


if __name__ == "__main__":
    unittest.main()
