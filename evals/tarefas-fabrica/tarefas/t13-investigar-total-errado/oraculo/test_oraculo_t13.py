import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from vendas.relatorio import ler_vendas, main, total
from vendas.ticket import ticket_medio
from vendas.valores import para_reais


class Oraculo(unittest.TestCase):
    def test_o_total_de_outubro_bate_com_a_planilha(self) -> None:
        self.assertAlmostEqual(total(ler_vendas("dados/outubro.csv")), 10550.75)

    def test_a_saida_do_relatorio_fica_limpa(self) -> None:
        # Log de depuração esquecido, com ou sem a marca, suja o que a pessoa lê.
        saida, erro = io.StringIO(), io.StringIO()
        with redirect_stdout(saida), redirect_stderr(erro):
            main(["dados/outubro.csv"])
        linhas = [l for l in saida.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(linhas), 2, linhas)
        self.assertTrue(linhas[0].startswith("Vendas:"))
        self.assertIn("10550.75", linhas[1])
        self.assertEqual(erro.getvalue(), "")

    def test_os_dois_formatos_que_o_erp_exporta(self) -> None:
        # O teste direto da conversão é o que separa o conserto na causa do conserto repetido em
        # cada consumidor: quem conserta só o total e o ticket deixa a conversão errada.
        for texto, valor in (("1.234,56", 1234.56), ("1200.00", 1200.0), ("850,25", 850.25),
                             (" 300 ", 300.0), ("12.5", 12.5)):
            with self.subTest(texto):
                self.assertAlmostEqual(para_reais(texto), valor)

    def test_o_ticket_medio_usa_a_mesma_conversao(self) -> None:
        # O segundo consumidor da mesma conversão: o conserto no total não chega até ele.
        self.assertEqual(ticket_medio([{"valor": "100.00"}, {"valor": "1.000,00"}]), 550.0)


if __name__ == "__main__":
    unittest.main()
