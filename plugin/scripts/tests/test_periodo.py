"""Testes da comparação de período do /relatar (`telemetria.py periodo`, emenda ao ADR-0050).

Só stdlib, num git de verdade com merges datados dos dois lados da fronteira e uma
trajetória com sessões nos dois períodos. Três coisas:

1. A conta é do script: carrega 2N dias e reparte. A sessão conta no período em que
   começou, mesmo que termine no seguinte; o PR, no período em que foi mesclado; o que
   passa de 2N fica fora.
2. Cada número é o mesmo do comando de origem (`prs`, `resumo`, `tokens`), e a variação
   sai calculada: contagem em unidades, taxa em pontos percentuais, com a conta ao lado e
   "amostra pequena" abaixo de 5.
3. Sem trajetória, processo e custo saem "não medido", nunca 0; PRs saem do git sempre.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import telemetria  # noqa: E402

FABRICA = "\n\nFabrica: kairos-forge"


def ha(dias: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()


def evento(sessao: str, dias: float, tipo: str, **campos) -> dict:
    return {"t": ha(dias), "sessao": sessao, "tipo": tipo, **campos}


TRAJETORIA = [
    # agora: a1 autônoma, com gate verde de primeira e tokens
    evento("a1", 2, "prompt", skill="entregar"),
    evento("a1", 2, "comando", gate="validar", cmd="pytest", ok=True),
    evento("a1", 2, "escrita", producao=True),
    evento("a1", 2, "sessao_fim", tokens={"entrada": 1000, "saida": 500, "cache_leitura": 50000}),
    # agora: a2 com três prompts, gate que falhou e voltou, e uma recusa
    evento("a2", 1, "prompt", skill="revisar"),
    evento("a2", 1, "prompt"),
    evento("a2", 1, "prompt"),
    evento("a2", 1, "comando", gate="validar", cmd="pytest", ok=False),
    evento("a2", 1, "comando", gate="validar", cmd="pytest", ok=True),
    evento("a2", 1, "recusa", classe="teste", modo="aviso"),
    evento("a2", 1, "sessao_fim", tokens={"entrada": 2000, "saida": 1000, "cache_leitura": 10000}),
    # antes: b1 começa há 10 dias e termina há 6, dentro do período atual: conta antes
    evento("b1", 10, "prompt", skill="entregar"),
    evento("b1", 10, "escrita", producao=True),
    evento("b1", 6, "sessao_fim", tokens={"entrada": 500, "saida": 500}),
    # fora dos 14 dias
    evento("velha", 20, "prompt", skill="entregar"),
]


class ComRepositorio(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-periodo-")
        self.raiz = Path(self._tmp.name).resolve()
        self.g("init", "-q", "-b", "main", ".")
        self.g("commit", "-q", "--allow-empty", "-m", "base", dias=30)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def g(self, *args: str, dias: float = 0) -> None:
        data = ha(dias)
        env = {**os.environ, "GIT_AUTHOR_DATE": data, "GIT_COMMITTER_DATE": data}
        subprocess.run(["git", "-C", str(self.raiz), "-c", "user.name=Pessoa", "-c",
                        "user.email=a@b", *args], check=True, capture_output=True, env=env)

    def pr(self, numero: int, dias: float, mensagens: list[str]) -> None:
        self.g("checkout", "-q", "-b", f"b{numero}", dias=dias)
        for i, mensagem in enumerate(mensagens):
            (self.raiz / f"f{numero}_{i}.py").write_text(f"x = {i}\n", encoding="utf-8")
            self.g("add", ".", dias=dias)
            self.g("commit", "-q", "-m", mensagem, dias=dias)
        self.g("checkout", "-q", "main", dias=dias)
        self.g("merge", "-q", "--no-ff", f"b{numero}", "-m",
               f"Merge pull request #{numero} from org/b{numero}", dias=dias)

    def trajetoria(self) -> None:
        pasta = self.raiz / ".agents" / "execucoes"
        pasta.mkdir(parents=True)
        (pasta / "trajetoria.jsonl").write_text(
            "".join(json.dumps(e) + "\n" for e in TRAJETORIA), encoding="utf-8")

    def linhas(self, r: dict) -> dict:
        return {l["rotulo"]: l for l in r["linhas"]}

    def rodar(self, *args: str) -> str:
        texto, antes = io.StringIO(), os.getcwd()
        try:
            os.chdir(self.raiz)
            with mock.patch.object(sys, "argv", ["telemetria.py", "periodo", *args]), \
                    contextlib.redirect_stdout(texto):
                self.assertEqual(telemetria.main(), 0)
        finally:
            os.chdir(antes)
        return texto.getvalue()


class EstePeriodoEOAnterior(ComRepositorio):
    def setUp(self) -> None:
        super().setUp()
        # Em ordem de data, como numa história real: o `git log --since` para no primeiro
        # commit mais velho que o limite.
        self.pr(4, 20, ["feat: d" + FABRICA])                      # fora dos 14 dias
        self.pr(3, 9, ["feat: c"])                                 # antes, só humano
        self.pr(2, 3, ["feat: b" + FABRICA, "fix: ajuste à mão"])  # agora, com commit humano
        self.pr(1, 2, ["feat: a" + FABRICA])                       # agora, só da fábrica
        self.trajetoria()

    def test_cada_numero_no_periodo_certo_com_a_variacao_calculada(self) -> None:
        r = telemetria.comparar_periodos(self.raiz, 7, "git")
        self.assertEqual(r["fonte_prs"], "git")
        l = self.linhas(r)
        def par(rotulo: str) -> tuple:
            return l[rotulo]["agora"], l[rotulo]["antes"], l[rotulo]["variacao"]
        self.assertEqual(par("PRs mesclados"), (2, 1, 1))
        self.assertEqual(par("com código da fábrica"), (2, 0, 2))
        self.assertEqual(par("sem commit humano"), (1, 0, 1))
        self.assertEqual(par("autonomia de PR"), (50.0, None, None))       # antes: nenhum da fábrica
        self.assertEqual(par("sessões"), (2, 1, 1))                        # b1 conta antes
        self.assertEqual(par("autonomia de ciclo"), (50.0, 100.0, -50.0))
        self.assertTrue(l["autonomia de ciclo"]["amostra_pequena"])
        self.assertEqual(l["autonomia de ciclo"]["agora_conta"], "1/2")
        self.assertEqual(par("gates verdes de primeira"), (50.0, None, None))
        self.assertEqual(par("rodadas de correção"), (1, 0, 1))
        self.assertEqual(par("recusas do guardrail"), (1, 0, 1))
        self.assertEqual(par("sessões com produção sem gate"), (0, 1, -1))
        self.assertEqual(par("tokens novos"), (4500, 1000, 3500))
        self.assertEqual(par("cache lido"), (60000, 0, 60000))

    def test_prs_batem_com_o_prs_e_cada_sessao_conta_uma_vez(self) -> None:
        l = self.linhas(telemetria.comparar_periodos(self.raiz, 7, "git"))
        _, prs = telemetria.prs_mesclados(self.raiz, 7, "git")
        self.assertEqual(l["PRs mesclados"]["agora"], telemetria.autonomia_de_prs(prs)["mesclados"])
        dois_periodos = telemetria.carregar(self.raiz, 14)
        def soma(rotulo: str) -> int:
            return l[rotulo]["agora"] + l[rotulo]["antes"]
        self.assertEqual(soma("sessões"), len(telemetria.por_sessao(dois_periodos)))
        self.assertEqual(soma("tokens novos"),
                         telemetria.resumo_de_tokens(dois_periodos)["tokens_novos"])
        # o `resumo --dias 7` corta por evento: b1, que começou antes, entra nele
        self.assertEqual(len(telemetria.por_sessao(telemetria.carregar(self.raiz, 7))), 3)

    def test_pela_cli(self) -> None:
        saida = self.rodar("--dias", "7", "--fonte", "git")
        self.assertIn("📅 Este período × o anterior — 7 dias", saida)
        self.assertIn("Fonte git: só merges com commit de merge", saida)
        self.assertIn("Entregue — telemetria.py prs, fonte git", saida)
        self.assertIn("Processo — telemetria.py resumo", saida)
        linha = next(x for x in saida.splitlines() if "autonomia de ciclo" in x)
        self.assertIn("50,0% (1/2)", linha)
        self.assertIn("100,0% (1/1)", linha)
        self.assertIn("−50,0 p.p. · amostra pequena", linha)
        self.assertIn("tokens novos                              4.500            1.000   +3.500",
                      saida)
        self.assertIn("cache lido                               60 mil                0   +60 mil",
                      saida)
        self.assertRegex(saida, r"sessões com produção sem gate\s+0\s+1\s+−1")
        self.assertRegex(saida, r"PRs mesclados\s+2\s+1\s+\+1")
        self.assertRegex(saida, r"autonomia de PR\s+50,0% \(1/2\)\s+—\s+—")
        bruto = self.rodar("--fonte", "git", "--json")
        self.assertEqual(json.loads(bruto)["dias"], 7)
        self.assertIn('"sessões"', bruto)                        # JSON legível, com acento

    def test_as_datas_das_duas_janelas(self) -> None:
        r = telemetria.comparar_periodos(self.raiz, 7, "git")
        hoje = datetime.now(timezone.utc).date()
        self.assertEqual((r["agora_de"], r["agora_ate"], r["antes_de"], r["antes_ate"]),
                         tuple(str(hoje - timedelta(days=d)) for d in (7, 0, 14, 7)))


class SemTrajetoria(ComRepositorio):
    def test_processo_e_custo_nao_medidos_e_prs_do_git(self) -> None:
        self.pr(1, 1, ["feat: a"])
        r = telemetria.comparar_periodos(self.raiz, 7, "git")
        l = self.linhas(r)
        self.assertEqual((l["PRs mesclados"]["agora"], l["PRs mesclados"]["variacao"]), (1, 1))
        for rotulo in ("sessões", "rodadas de correção", "tokens novos", "cache lido"):
            with self.subTest(rotulo):
                self.assertFalse(l[rotulo]["medido"])
                self.assertIsNone(l[rotulo]["variacao"])
        saida = self.rodar("--fonte", "git")
        self.assertRegex(saida, r"sessões\s+não medido\s+não medido\s+—")
        self.assertRegex(saida, r"tokens novos\s+não medido\s+não medido\s+—")
        self.assertRegex(saida, r"com código da fábrica\s+0\s+0\s+0\n")   # zero sem sinal

    def test_trajetoria_sem_leitura_de_tokens_mede_o_processo_e_nao_o_custo(self) -> None:
        pasta = self.raiz / ".agents" / "execucoes"
        pasta.mkdir(parents=True)
        sem_tokens = [e for e in TRAJETORIA if e["tipo"] != "sessao_fim"]   # como no Codex
        (pasta / "t.jsonl").write_text("".join(json.dumps(e) + "\n" for e in sem_tokens),
                                       encoding="utf-8")
        l = self.linhas(telemetria.comparar_periodos(self.raiz, 7, "git"))
        self.assertTrue(l["sessões"]["medido"])
        self.assertEqual(l["sessões"]["agora"], 2)
        self.assertFalse(l["tokens novos"]["medido"])


class ImpressaoDosPrs(unittest.TestCase):
    """O `prs` e o `periodo` dão o mesmo aviso quando a fonte é o git."""

    def imprimir(self, r: dict, dias: int | None) -> str:
        texto = io.StringIO()
        with contextlib.redirect_stdout(texto):
            telemetria.imprimir_prs(r, dias)
        return texto.getvalue()

    def test_fonte_git_sem_pr_da_fabrica(self) -> None:
        saida = self.imprimir({"fonte": "git", "mesclados": 3, "da_fabrica": 0}, None)
        self.assertIn("todo o histórico (fonte: git)", saida)
        self.assertIn(telemetria.AVISO_FONTE_GIT, saida)
        self.assertIn("3 PR(s) mesclado(s), nenhum com commit da fábrica", saida)

    def test_fonte_gh_lista_so_os_da_fabrica(self) -> None:
        def pr(numero, branch, fabrica, autonomo, titulo):
            return {"numero": numero, "branch": branch, "da_fabrica": fabrica,
                    "autonomo": autonomo, "agente": 1, "humano": 0 if autonomo else 1,
                    "titulo": titulo}
        saida = self.imprimir({"fonte": "gh", "mesclados": 4, "da_fabrica": 3, "autonomos": 1,
                               "taxa": 33.3, "prs": [pr(7, "b7", True, True, "sete"),
                                                     pr(8, "b8", False, False, "oito"),
                                                     pr(None, "b9", True, False, "nove"),
                                                     pr(None, "", True, False, "dez")]}, 7)
        self.assertIn("últimos 7 dias (fonte: gh)", saida)
        self.assertNotIn("Fonte git", saida)
        self.assertIn("Autonomia de PR: 33.3%  (1/3)", saida)
        self.assertIn("✅ #7", saida)
        self.assertNotIn("oito", saida)
        self.assertIn("·  b9", saida)
        self.assertIn("·  merge", saida)


class AmostraPequena(unittest.TestCase):
    def test_cinco_ja_nao_e_amostra_pequena(self) -> None:
        def lado(n: int) -> dict:
            return {"ciclos_autonomos": 1, "ciclos": n, "sessoes_totais": n}
        def linha(agora: int, antes: int) -> dict:
            return telemetria._linha_do_periodo("Processo", "autonomia de ciclo", "ciclos_autonomos",
                                                "ciclos", {"agora": lado(agora), "antes": lado(antes)})
        self.assertFalse(linha(5, 7)["amostra_pequena"])
        self.assertTrue(linha(4, 7)["amostra_pequena"])
        self.assertTrue(linha(9, 4)["amostra_pequena"])


class Fronteira(unittest.TestCase):
    def test_o_instante_do_corte_e_do_periodo_atual(self) -> None:
        meio = datetime(2026, 11, 1, tzinfo=timezone.utc)
        self.assertIs(telemetria._no_periodo("2026-11-01T00:00:00+00:00", meio), True)
        self.assertIs(telemetria._no_periodo("2026-10-31T23:59:59Z", meio), False)
        self.assertIsNone(telemetria._no_periodo("2026-11-02T00:00:00", meio))   # sem fuso
        self.assertIsNone(telemetria._no_periodo(None, meio))


if __name__ == "__main__":
    unittest.main()
