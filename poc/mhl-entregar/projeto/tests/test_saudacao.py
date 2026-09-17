import unittest

from saudacao import saudar


class TestSaudacao(unittest.TestCase):
    def test_saudacao_caminho_feliz(self):
        self.assertEqual(saudar("Ana"), "Bom dia, Ana!")

    def test_saudacao_nome_vazio_levanta_erro(self):
        with self.assertRaises(ValueError):
            saudar("   ")


if __name__ == "__main__":
    unittest.main()
