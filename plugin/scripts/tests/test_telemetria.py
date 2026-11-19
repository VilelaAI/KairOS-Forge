"""Testes do `telemetria.py prs` — a autonomia de PR medida pelo git (ADR-0044).

Só stdlib. Cada teste monta um repositório git temporário com merges de verdade, porque
o número sai do histórico; a leitura do `gh` é testada com a resposta dele simulada.

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
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import telemetria  # noqa: E402

FABRICA = "\n\nFabrica: kairos-forge"
CLAUDE = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"


def git(*args: str, autor: str = "Pessoa") -> None:
    subprocess.run(["git", "-c", f"user.name={autor}", "-c", "user.email=a@b", *args],
                   check=True, capture_output=True)


class Repo(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-telemetria-")
        self._cwd = os.getcwd()
        self.raiz = Path(self._tmp.name).resolve()
        os.chdir(self.raiz)
        git("init", "-q", "-b", "main", ".")
        git("commit", "-q", "--allow-empty", "-m", "base")

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def pr(self, numero: int, branch: str, commits: list[tuple[str, str]]) -> None:
        """Abre `branch`, faz os commits (autor, mensagem) e mescla com commit de merge."""
        git("checkout", "-q", "-b", branch)
        for i, (autor, mensagem) in enumerate(commits):
            Path(f"{branch.replace('/', '-')}-{i}.txt").write_text(mensagem, encoding="utf-8")
            git("add", ".")
            git("commit", "-q", "-m", mensagem, autor=autor)
        git("checkout", "-q", "main")
        git("merge", "-q", "--no-ff", branch, "-m",
            f"Merge pull request #{numero} from org/{branch}")

    def medir(self, *extras: str) -> dict:
        import re
        _, prs = telemetria.prs_mesclados(self.raiz, None, "git")
        return telemetria.autonomia_de_prs(prs, tuple(re.compile(e, re.I | re.M) for e in extras))


class AutonomiaDePr(Repo):
    def test_so_pr_sem_commit_humano_conta_como_autonomo(self) -> None:
        self.pr(1, "forge/a", [("Pessoa", "feat: a" + FABRICA), ("Pessoa", "test: a" + FABRICA)])
        self.pr(2, "feat/b", [("Pessoa", "feat: b" + CLAUDE), ("Pessoa", "fix: ajuste à mão")])
        self.pr(3, "feat/c", [("Pessoa", "feat: c feito à mão")])
        r = self.medir()
        self.assertEqual((r["mesclados"], r["da_fabrica"], r["autonomos"]), (3, 2, 1))
        self.assertEqual(r["taxa"], 50.0)
        por_numero = {l["numero"]: l for l in r["prs"]}
        self.assertTrue(por_numero[1]["autonomo"])
        self.assertEqual((por_numero[2]["agente"], por_numero[2]["humano"]), (1, 1))
        self.assertFalse(por_numero[3]["da_fabrica"])
        self.assertEqual(por_numero[1]["branch"], "forge/a")

    def test_sem_pr_da_fabrica_e_nao_medido(self) -> None:
        self.pr(1, "feat/a", [("Pessoa", "feat: tudo à mão")])
        r = self.medir()
        self.assertEqual(r["da_fabrica"], 0)
        self.assertIsNone(r["taxa"])

    def test_autor_kairos_forge_e_marca_extra(self) -> None:
        self.pr(1, "forge/corrige-x", [("kairos-forge", "fix(ci): corrige")])
        self.pr(2, "feat/codex", [("Pessoa", "feat: x\n\nCodex-Session: 123")])
        self.assertEqual(self.medir()["autonomos"], 1)
        self.assertEqual(self.medir(r"^codex-session:")["autonomos"], 2)

    def test_cli_json(self) -> None:
        self.pr(7, "forge/a", [("Pessoa", "feat: a" + FABRICA)])
        out = io.StringIO()
        antigo = sys.argv
        sys.argv = ["telemetria.py", "prs", "--fonte", "git", "--json"]
        try:
            with contextlib.redirect_stdout(out):
                codigo = telemetria.main()
        finally:
            sys.argv = antigo
        self.assertEqual(codigo, 0)
        r = json.loads(out.getvalue())
        self.assertEqual((r["fonte"], r["taxa"]), ("git", 100.0))


class LeituraDoGh(unittest.TestCase):
    def test_normaliza_a_resposta_do_gh(self) -> None:
        resposta = [{
            "number": 42, "title": "feat: exporta CSV", "headRefName": "feat/csv",
            "mergedAt": "2026-10-20T12:00:00Z", "mergeCommit": {"oid": "abc"},
            "closingIssuesReferences": [{"number": 9}],
            "commits": [
                {"oid": "1", "authors": [{"name": "Pessoa", "login": "p"}],
                 "messageHeadline": "feat: exporta", "messageBody": "Fabrica: kairos-forge"},
                {"oid": "2", "authors": [{"name": "Pessoa", "login": "p"}],
                 "messageHeadline": "fix: ajuste", "messageBody": ""},
            ],
        }]
        falso = subprocess.CompletedProcess([], 0, stdout=json.dumps(resposta), stderr="")
        with mock.patch.object(telemetria.shutil, "which", return_value="/usr/bin/gh"), \
                mock.patch.object(telemetria.subprocess, "run", return_value=falso):
            fonte, prs = telemetria.prs_mesclados(Path("."), None)
        self.assertEqual(fonte, "gh")
        self.assertEqual((prs[0]["numero"], prs[0]["entrega"], prs[0]["issues"]), (42, "abc", [9]))
        r = telemetria.autonomia_de_prs(prs)
        self.assertEqual((r["da_fabrica"], r["autonomos"]), (1, 0))

    def test_gh_falhando_cai_para_o_git(self) -> None:
        falso = subprocess.CompletedProcess([], 1, stdout="", stderr="no remotes")
        with mock.patch.object(telemetria.shutil, "which", return_value="/usr/bin/gh"), \
                mock.patch.object(telemetria.subprocess, "run", side_effect=[falso]), \
                mock.patch.object(telemetria, "_prs_do_git", return_value=[]) as do_git:
            fonte, _ = telemetria.prs_mesclados(Path("."), 30)
        self.assertEqual(fonte, "git")
        do_git.assert_called_once()


class FalhasDoGuardrail(unittest.TestCase):
    def test_resumo_conta_o_guardrail_que_falhou_aberto(self) -> None:
        eventos = [{"sessao": "a", "tipo": "guardrail_erro", "modo": "comando"},
                   {"sessao": "b", "tipo": "guardrail_erro", "modo": "escrita"},
                   {"sessao": "b", "tipo": "recusa", "classe": "regua", "modo": "aviso"}]
        m = telemetria.metricas(telemetria.por_sessao(eventos))
        self.assertEqual((m["falhas_do_guardrail"], m["recusas_total"]), (2, 1))
        self.assertIn("Guardrail falhou e deixou passar: 2 vez(es)", telemetria.alertas(m)[0])

    def test_sem_falha_nem_producao_sem_gate_nao_ha_alerta(self) -> None:
        m = {"falhas_do_guardrail": 0, "sessoes_com_producao_sem_gate": 2}
        self.assertEqual(telemetria.alertas(m),
                         ["Código de produção escrito sem nenhum gate: 2 sessão(ões)"])
        self.assertEqual(telemetria.alertas({"falhas_do_guardrail": 0,
                                             "sessoes_com_producao_sem_gate": 0}), [])



def resultado(entrada: int, saida: int, turnos: int, ms: int, erro: bool = False) -> dict:
    return {"type": "result", "subtype": "error_during_execution" if erro else "success",
            "is_error": erro, "duration_ms": ms, "num_turns": turnos, "result": "ok",
            "total_cost_usd": 9.99,
            "usage": {"input_tokens": entrada, "cache_creation_input_tokens": 100,
                      "cache_read_input_tokens": 5000, "output_tokens": saida}}


class CustoPorVersao(unittest.TestCase):
    """`telemetria.py custo-eval`: o custo de cada versão no /avaliar, em tokens."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-custo-")
        self.raiz = Path(self._tmp.name)
        self.pasta = self.raiz / "evals" / "x" / "execucoes"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def caso(self, versao: str, nome: str, texto: str) -> None:
        p = self.pasta / versao / nome
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")

    def montar(self) -> None:
        self.caso("baseline", "c1.json", json.dumps(resultado(1000, 500, 4, 30000)))
        self.caso("baseline", "c2.json", json.dumps(resultado(1200, 600, 6, 40000), indent=2))
        self.caso("candidata", "c1.jsonl", "\n".join([
            json.dumps({"type": "system", "subtype": "init"}),
            json.dumps({"type": "assistant", "message": {"usage": {"input_tokens": 1}}}),
            json.dumps(resultado(2000, 500, 7, 45000))]))
        self.caso("candidata", "c2.json", json.dumps(resultado(2400, 600, 9, 60000, erro=True)))
        self.caso("candidata", "c3.json", json.dumps({"type": "result", "result": "sem usage"}))
        self.caso("candidata", "c4.json", "não é json")
        self.caso("candidata", "notas.txt", "ignorado")

    def test_mediana_por_caso_variacao_contra_a_baseline_e_o_que_nao_e_medido(self) -> None:
        self.montar()
        r = telemetria.custo_por_versao(self.pasta)
        b, c = r["versoes"]["baseline"], r["versoes"]["candidata"]
        self.assertEqual(r["baseline"], "baseline")
        self.assertEqual((b["casos"], b["medidos"], b["novos"], b["turnos"], b["duracao_s"]),
                         (2, 2, 1750.0, 5.0, 35.0))           # mediana de 1600 e 1900
        self.assertNotIn("delta_novos_pct", b)
        self.assertEqual((c["casos"], c["medidos"], c["com_erro"]), (4, 2, 1))
        self.assertEqual((c["novos"], c["delta_novos_pct"], c["delta_turnos"], c["delta_duracao_pct"]),
                         (2850.0, 62.9, 3.0, 50.0))         # o caso com erro também gastou
        self.assertEqual(c["cache_lido"], 5000.0)           # à parte, como no resto da fábrica
        self.assertEqual(telemetria.acima_do_teto(r, 50), ["candidata"])
        self.assertEqual(telemetria.acima_do_teto(r, 70), [])
        self.assertEqual(telemetria.acima_do_teto(r, 62.9), [])        # no teto ainda passa
        self.assertEqual(telemetria.acima_do_teto(r, None), [])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            telemetria.imprimir_custo_eval({**r, "pasta": "evals/x/execucoes"}, 50)
        texto = out.getvalue()
        self.assertIn("baseline: baseline; mediana por caso", texto)
        self.assertIn("2/4 caso(s) medidos, 1 com erro", texto)
        self.assertIn("tokens novos 2.850 (+62.9%) · cache lido 5.000 · turnos 8 (+3) · duração 52 s (+50%)", texto)
        self.assertIn("⚠️  candidata gasta mais que a baseline + 50%", texto)
        self.assertNotIn("dólar", texto.lower())
        self.assertNotIn("9.99", json.dumps(r))             # custo em tokens, nunca em dinheiro

    def test_baseline_escolhida_versao_sem_caso_medido_e_erros(self) -> None:
        self.montar()
        self.caso("vazia", "c1.json", "{}")
        self.caso("vazia", "c2.json", json.dumps({"type": "assistant", "usage": {"input_tokens": 5}}))
        self.caso("vazia", "c3.json", json.dumps({"type": "result", "usage": "texto"}))
        limite = {**resultado(10, 10, 99, 1000), "subtype": "error_max_turns"}   # erro só no subtype
        self.caso("no-limite", "c1.json", json.dumps(limite))
        estranho = {**resultado(0, 0, 1, 1000),
                    "usage": {"input_tokens": "muito", "output_tokens": True,
                              "cache_creation_input_tokens": 3}}            # só inteiro conta
        self.caso("estranha", "c1.json", json.dumps(estranho))
        r = telemetria.custo_por_versao(self.pasta, "candidata")
        self.assertEqual(r["baseline"], "candidata")
        self.assertEqual(r["versoes"]["baseline"]["delta_novos_pct"], -38.6)
        self.assertEqual(r["versoes"]["vazia"]["novos"], None)
        self.assertIsNone(r["versoes"]["vazia"]["delta_novos_pct"])
        self.assertEqual((r["versoes"]["vazia"]["casos"], r["versoes"]["vazia"]["medidos"]), (3, 0))
        self.assertEqual(r["versoes"]["no-limite"]["com_erro"], 1)
        self.assertEqual(r["versoes"]["estranha"]["novos"], 3.0)
        self.assertEqual(telemetria._valor_de(["--teto", "5"], "--teto"), "5")
        self.assertIn("não medido", telemetria._num(None))
        self.assertIn("nenhuma subpasta", telemetria.custo_por_versao(self.raiz / "nada")["erro"])
        self.assertIn("não está", telemetria.custo_por_versao(self.pasta, "outra")["erro"])
        so_arquivos = self.raiz / "plana"
        so_arquivos.mkdir()
        (so_arquivos / "c.json").write_text("{}", encoding="utf-8")
        self.assertIn("nenhuma subpasta", telemetria.custo_por_versao(so_arquivos)["erro"])
        primeira = telemetria.custo_por_versao(self.raiz / "evals" / "x" / "execucoes", None)
        self.assertEqual(primeira["baseline"], "baseline")

    def test_sem_a_pasta_baseline_a_baseline_e_dita_nunca_adivinhada(self) -> None:
        """Sem `baseline/`, a primeira subpasta em ordem alfabética virava a régua sem
        aviso, e o --teto media contra a versão errada. Sem ela, a baseline vem do
        --baseline; sem os dois, o comando recusa e diz as subpastas (emenda ao ADR-0025)."""
        self.montar()
        (self.pasta / "baseline").rename(self.pasta / "a-antiga")
        r = telemetria.custo_por_versao(self.pasta)
        self.assertNotIn("baseline", r)
        self.assertIn("--baseline", r["erro"])
        self.assertIn("a-antiga, candidata", r["erro"])
        self.assertEqual(telemetria.custo_por_versao(self.pasta, "a-antiga")["baseline"], "a-antiga")
        antes, argv = os.getcwd(), sys.argv
        os.chdir(self.raiz)
        try:
            for args, esperado in ((["custo-eval", "evals/x/execucoes"], 1),
                                   (["custo-eval", "evals/x/execucoes", "--teto", "80"], 1),
                                   (["custo-eval", "evals/x/execucoes", "--baseline", "a-antiga",
                                     "--teto", "80"], 0)):
                sys.argv = ["telemetria.py", *args]
                with contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()) as err:
                    self.assertEqual(telemetria.main(), esperado, args)
                if esperado:
                    self.assertIn("--baseline", err.getvalue())
        finally:
            os.chdir(antes)
            sys.argv = argv

    def test_versao_sem_caso_medido_e_nao_medido_e_reprova_o_teto(self) -> None:
        """Sem caso medido não há variação, e sem variação não dá para provar que a versão
        ficou abaixo da baseline + teto: "não medido", nunca 0 (ADR-0050, emenda ao ADR-0025)."""
        self.montar()
        self.caso("vazia", "c1.json", json.dumps({"type": "result", "result": "sem usage"}))
        antes, argv = os.getcwd(), sys.argv
        os.chdir(self.raiz)
        try:
            for args, esperado in ((["custo-eval", "evals/x/execucoes"], 0),
                                   (["custo-eval", "evals/x/execucoes", "--teto", "80"], 1)):
                sys.argv = ["telemetria.py", *args]
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(telemetria.main(), esperado, args)
            sys.argv = ["telemetria.py", "custo-eval", "evals/x/execucoes", "--teto", "80", "--json"]
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(telemetria.main(), 1)
            dados = json.loads(out.getvalue())
            self.assertEqual((dados["acima_do_teto"], dados["nao_medido_no_teto"]), ([], ["vazia"]))
        finally:
            os.chdir(antes)
            sys.argv = argv
        r = telemetria.custo_por_versao(self.pasta)
        self.assertIsNone(r["versoes"]["vazia"]["delta_novos_pct"])
        self.assertEqual(telemetria.acima_do_teto(r, 80), [])           # não está acima: não se sabe
        self.assertEqual(telemetria.acima_do_teto(r, -10), ["candidata"])   # o não medido não vira 0
        self.assertEqual(telemetria.nao_medido_no_teto(r, 80), ["vazia"])
        self.assertEqual(telemetria.nao_medido_no_teto(r, None), [])     # sem teto, sem gate
        with contextlib.redirect_stdout(io.StringIO()) as out:
            telemetria.imprimir_custo_eval({**r, "pasta": "evals/x/execucoes"}, 80)
        self.assertIn("vazia: não medido — nenhum caso medido; não dá para provar que ficou "
                      "dentro da baseline + 80%", out.getvalue())

    def test_baseline_sem_caso_medido_nenhuma_versao_passa_no_teto(self) -> None:
        self.caso("baseline", "c1.json", "não é json")
        self.caso("candidata", "c1.json", json.dumps(resultado(1000, 500, 4, 30000)))
        antes, argv = os.getcwd(), sys.argv
        os.chdir(self.raiz)
        try:
            sys.argv = ["telemetria.py", "custo-eval", "evals/x/execucoes", "--teto", "1000"]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(telemetria.main(), 1)
        finally:
            os.chdir(antes)
            sys.argv = argv
        r = telemetria.custo_por_versao(self.pasta)
        self.assertEqual(telemetria.acima_do_teto(r, 1000) + telemetria.nao_medido_no_teto(r, 1000),
                         ["candidata"])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            telemetria.imprimir_custo_eval({**r, "pasta": "evals/x/execucoes"}, 1000)
        self.assertIn("candidata: não medido — a baseline não tem caso medido", out.getvalue())

    def test_cli_sai_1_acima_do_teto_e_com_erro(self) -> None:
        self.montar()
        antes, argv = os.getcwd(), sys.argv
        os.chdir(self.raiz)
        try:
            for args, esperado in ((["custo-eval", "evals/x/execucoes"], 0),
                                   (["custo-eval", "evals/x/execucoes", "--teto", "80", "--json"], 0),
                                   (["custo-eval", "evals/x/execucoes", "--teto"], 0),   # sem valor: sem teto
                                   (["custo-eval", "evals/x/execucoes", "--teto", "20"], 1),
                                   (["custo-eval", "evals/x/execucoes", "--teto", "muito"], 1),
                                   (["custo-eval", "evals/x/execucoes", "--baseline", "outra"], 1),
                                   (["custo-eval"], 1)):
                sys.argv = ["telemetria.py", *args]
                with contextlib.redirect_stdout(io.StringIO()) as out, \
                        contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(telemetria.main(), esperado, args)
            (self.raiz / "evals" / "x" / "execucoes").rename(self.raiz / "evals" / "x" / "execuções")
            sys.argv = ["telemetria.py", "custo-eval", "evals/x/execuções", "--json"]
            with contextlib.redirect_stdout(io.StringIO()) as out:
                telemetria.main()
            self.assertIn('"pasta": "evals/x/execuções"', out.getvalue())   # sem \\u escapado
            dados = json.loads(out.getvalue())
            self.assertEqual(dados["acima_do_teto"], [])
        finally:
            os.chdir(antes)
            sys.argv = argv


def gravado(cmd: str, ok: bool | None = True) -> dict:
    return {"t": "x", "sessao": "s", "tipo": "comando", "cmd": cmd, "ok": ok, "gate": "teste"}


class CorroborarSoOQueRodou(unittest.TestCase):
    """`telemetria.py corroborar`: o gate citado no `verificado:` rodou? (ADR-0021).

    Só corrobora a execução que roda o comando alegado: o alegado inteiro, palavra por
    palavra, e o comando acaba ali. A comparação por trecho de texto, nos dois sentidos,
    deixava um comando mais amplo ou mais estreito confirmar a alegação."""

    def veredicto(self, alegado: str, *execucoes: dict) -> str:
        return telemetria.corroborar(list(execucoes), alegado)["veredicto"]

    def test_comando_mais_curto_que_o_alegado_nao_corrobora(self) -> None:
        for rodou in ("pytest", "cd scripts", "test", "python3 -m unittest"):
            self.assertEqual(self.veredicto("cd scripts && python3 -m unittest tests.test_x",
                                            gravado(rodou)), "nao_corroborado", rodou)

    def test_comando_mais_estreito_que_o_alegado_nao_corrobora(self) -> None:
        for rodou in ("pytest tests/test_x.py -k um_so", "pytest tests/test_x.py::test_um",
                      "pytest tests/test_x.py --lf", "npm test -- --grep um_so"):
            alegado = "npm test" if rodou.startswith("npm") else "pytest tests/test_x.py"
            self.assertEqual(self.veredicto(alegado, gravado(rodou)), "nao_corroborado", rodou)

    def test_palavra_pela_metade_nao_corrobora(self) -> None:
        self.assertEqual(self.veredicto("pytest tests/test_x", gravado("pytest tests/test_x_outro.py")),
                         "nao_corroborado")
        self.assertEqual(self.veredicto("pytest -k foo", gravado("pytest -k foobar")), "nao_corroborado")
        self.assertEqual(self.veredicto("make test", gravado("cmake test")), "nao_corroborado")
        self.assertEqual(self.veredicto("pytest tests/", gravado('git commit -m "verificado: pytest tests/"')),
                         "nao_corroborado")                 # citar o comando não é rodá-lo

    def test_o_estreito_que_passou_nao_esconde_o_alegado_que_falhou(self) -> None:
        self.assertEqual(self.veredicto("pytest tests/",
                                        gravado("pytest tests/ -k um_so", True),
                                        gravado("pytest tests/", False)), "corroborado_com_falha")

    def test_o_que_prepara_e_o_que_vem_depois_do_comando_nao_atrapalham(self) -> None:
        for rodou in ("cd scripts && python3 -m unittest tests.test_x",
                      "CD scripts &&   python3 -m unittest   tests.test_x",
                      "timeout 60 python3 -m unittest tests.test_x 2>&1 | tail -5",
                      "python3 -m unittest tests.test_x > saida.txt; echo fim",
                      "python3 -m unittest tests.test_x 2> /dev/null || true",
                      "python3 -m unittest tests.test_x&& echo ok",
                      "python3 -m unittest tests.test_x &> log.txt",
                      "(cd scripts && python3 -m unittest tests.test_x)",
                      "python3 -m unittest tests.test_x"):
            self.assertEqual(self.veredicto("python3 -m unittest tests.test_x", gravado(rodou)),
                             "corroborado", rodou)
        self.assertEqual(self.veredicto("cd scripts && python3 -m unittest tests.test_x",
                                        gravado("cd scripts && python3 -m unittest tests.test_x")),
                         "corroborado")

    def test_cada_linha_e_um_comando_e_o_que_nao_roda_nao_conta(self) -> None:
        """O shell roda cada linha como um comando, e a linha continuada com `\\` é uma só.
        O texto entre aspas, o corpo de heredoc e o comentário não rodam: citar o comando
        neles não é rodá-lo."""
        for rodou in ("cd scripts\npython3 -m unittest tests.test_x\necho fim",
                      'python3 -m unittest tests.test_x\necho "saiu $?"',
                      "python3 -m unittest \\\n  tests.test_x",
                      "python3 -m unittest tests.test_x  # a suíte do módulo",
                      "cat <<EOF > f.txt\nnotas\nEOF\npython3 -m unittest tests.test_x"):
            self.assertEqual(self.veredicto("python3 -m unittest tests.test_x", gravado(rodou)),
                             "corroborado", rodou)
        for citou in ('git commit -m "feat: x\n\nverificado: pytest tests/\n\nfim"',
                      "git commit -m \"$(cat <<'EOF'\nfeat: x\n\nverificado: pytest tests/\nEOF\n)\"",
                      "cat > notas.md <<EOF\nverificado: pytest tests/\nEOF\necho ok",
                      "cat > notas.md <<-'FIM'\n\tpytest tests/\n\tFIM",
                      "# pytest tests/",
                      "# pytest tests/\necho pulei",
                      "echo ok # pytest tests/"):
            self.assertEqual(self.veredicto("pytest tests/", gravado(citou)), "nao_corroborado", citou)
        self.assertEqual(self.veredicto("pytest tests/", gravado("pytest tests/ <<< entrada")),
                         "corroborado")                   # `<<<` é here-string, não heredoc

    def test_alegado_vazio_nao_corrobora_nada(self) -> None:
        for alegado in ("", "   "):
            self.assertEqual(self.veredicto(alegado, gravado("pytest")), "nao_corroborado")

    def test_a_cli_sai_1_quando_so_o_mais_amplo_rodou(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kairos-forge-corroborar-") as tmp:
            pasta = Path(tmp) / ".agents" / "execucoes"
            pasta.mkdir(parents=True)
            agora = datetime.now(timezone.utc).isoformat()
            (pasta / "s.jsonl").write_text(json.dumps({**gravado("pytest"), "t": agora}) + "\n",
                                           encoding="utf-8")
            antes, argv = os.getcwd(), sys.argv
            os.chdir(tmp)
            try:
                for alegado, esperado in (("pytest tests/test_x.py", 1), ("pytest", 0)):
                    sys.argv = ["telemetria.py", "corroborar", alegado, "--json"]
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(telemetria.main(), esperado, alegado)
            finally:
                os.chdir(antes)
                sys.argv = argv


if __name__ == "__main__":
    unittest.main()


class SinaisDoPr(unittest.TestCase):
    """As bordas de `sinais_do_pr` sem montar um repositório: o histórico é uma lista."""

    def c(self, letra: str, dia: int, assunto: str, corpo: str = "") -> dict:
        return {"oid": letra * 40, "quando": datetime(2026, 10, dia, tzinfo=timezone.utc),
                "assunto": assunto, "corpo": corpo, "arquivos": ["src/x.py"]}

    def pr(self, numero: int, letra: str, dia: int) -> dict:
        return {"numero": numero, "titulo": "feat: exportar", "entrega": letra * 40,
                "mesclado_em": f"2026-10-{dia:02d}T00:00:00+00:00", "commits": []}

    def test_revert_so_pelo_sha_e_relancamento_com_o_mesmo_titulo(self) -> None:
        historico = [self.c("a", 1, "feat: exportar (#5)"),
                     self.c("b", 2, "Revert parcial", "This reverts commit aaaaaaaa."),
                     self.c("c", 3, 'Revert "feat: exportar"'),
                     self.c("d", 5, "feat: exportar (#9)")]
        self.assertTrue(telemetria.sinais_do_pr(self.pr(5, "a", 1), historico)["revertido"]
                        .startswith("bbbbbbbbb"))
        # o #9 relança o mesmo título depois do revert antigo: não foi revertido
        self.assertIsNone(telemetria.sinais_do_pr(self.pr(9, "d", 5), historico)["revertido"])
        # reverter um commit de dentro do PR também é reverter o PR
        com_commit = {**self.pr(9, "d", 5), "titulo": "feat: outro", "commits": [{"oid": "e" * 40}]}
        historico.append(self.c("f", 6, "Revert um pedaço", "This reverts commit eeeeeeee."))
        self.assertTrue(telemetria.sinais_do_pr(com_commit, historico)["revertido"]
                        .startswith("fffffffff"))

    def test_pr_sem_data_nao_tem_sinal_e_a_janela_fecha_no_dia_14(self) -> None:
        sem_data = {**self.pr(5, "a", 1), "mesclado_em": None}
        self.assertEqual(telemetria.sinais_do_pr(sem_data, [self.c("b", 2, "fix: x")]),
                         {"revertido": None, "corrigido": None})
        pr = self.pr(5, "a", 1)
        self.assertTrue(telemetria.janela_fechada(pr, datetime(2026, 10, 15, tzinfo=timezone.utc)))
        self.assertFalse(telemetria.janela_fechada(pr, datetime(2026, 10, 14, 23, tzinfo=timezone.utc)))

    def test_git_ausente_e_historico_vazio(self) -> None:
        with mock.patch.object(telemetria.subprocess, "run", side_effect=OSError):
            self.assertEqual(telemetria.historico_principal(Path(".")), [])


class EntregaDaFabricaComparadaComAHumana(unittest.TestCase):
    """`telemetria.py comparar`: PRs revertidos e corrigidos depois, fábrica × pessoas."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-comparar-")
        self.raiz = Path(self._tmp.name).resolve()
        self.g("init", "-q", "-b", "main", ".")
        self.g("commit", "-q", "--allow-empty", "-m", "base", dia=0)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def g(self, *args: str, dia: int = 0, autor: str = "Pessoa") -> str:
        data = f"2026-10-{1 + dia:02d}T10:00:00+00:00"
        env = {**os.environ, "GIT_AUTHOR_DATE": data, "GIT_COMMITTER_DATE": data}
        r = subprocess.run(["git", "-C", str(self.raiz), "-c", f"user.name={autor}", "-c",
                            "user.email=a@b", *args], check=True, capture_output=True,
                           text=True, env=env)
        return r.stdout.strip()

    def escrever(self, rel: str, texto: str) -> None:
        p = self.raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")

    def pr(self, numero: int, arquivos: list[str], dia: int, fabrica: bool) -> str:
        branch = f"b{numero}"
        self.g("checkout", "-q", "-b", branch)
        for rel in arquivos:
            self.escrever(rel, f"# pr {numero}\n")
        self.g("add", ".")
        self.g("commit", "-q", "-m", f"feat: pr {numero}" + (FABRICA if fabrica else ""), dia=dia)
        self.g("checkout", "-q", "main")
        self.g("merge", "-q", "--no-ff", branch, "-m",
               f"Merge pull request #{numero} from org/{branch}\n\nfeat: pr {numero}", dia=dia)
        return self.g("rev-parse", "HEAD")

    def commit_na_main(self, mensagem: str, arquivos: list[str], dia: int) -> None:
        for rel in arquivos:
            self.escrever(rel, f"# {mensagem} {dia}\n")
        self.g("add", ".")
        self.g("commit", "-q", "-m", mensagem, dia=dia)

    def comparar(self, agora: datetime = datetime(2026, 12, 1, tzinfo=timezone.utc)) -> dict:
        _, prs = telemetria.prs_mesclados(self.raiz, None, "git")
        return telemetria.comparar_entregas(self.raiz, prs, agora=agora)

    def test_revertido_e_corrigido_nos_dois_grupos_com_janela_e_teste_fora(self) -> None:
        for n in range(1, 6):
            arqs = [f"src/f{n}.py"] + ([f"tests/test_f{n}.py"] if n == 4 else [])
            merge = self.pr(n, arqs, dia=n, fabrica=True)
            if n == 2:
                self.g("revert", "-m", "1", "--no-edit", merge, dia=n + 1)     # revertido
        for n in range(6, 11):
            self.pr(n, [f"src/h{n}.py"], dia=n, fabrica=False)
        self.commit_na_main("fix: corrige h7", ["src/h7.py"], dia=10)          # corrigido (3 dias)
        self.commit_na_main("fix: tarde demais", ["src/f3.py"], dia=25)        # fora dos 14 dias
        self.commit_na_main("fix: só o teste", ["tests/test_f4.py"], dia=12)   # teste não conta
        self.commit_na_main("feat: f5 cresce", ["src/f5.py"], dia=13)         # não é correção
        r = self.comparar()
        f, h = r["fabrica"], r["humano"]
        self.assertEqual((f["prs"], f["revertidos"], f["corrigidos"], f["taxa_voltaram"]), (5, 1, 0, 20.0))
        self.assertEqual((h["prs"], h["revertidos"], h["corrigidos"], h["taxa_voltaram"]), (5, 0, 1, 20.0))
        self.assertEqual([i["numero"] for i in f["voltaram_lista"]], [2])
        self.assertEqual([i["numero"] for i in h["voltaram_lista"]], [7])
        self.assertTrue(r["comparavel"])
        self.assertEqual(r["diferenca_pp"], 0.0)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            telemetria.imprimir_comparacao({"fonte": "git", **r}, 90)
        texto = out.getvalue()
        self.assertIn("últimos 90 dias", texto)
        self.assertIn("volta tanto quanto a das pessoas", texto)
        self.assertIn("[fábrica] #2 feat: pr 2 — revertido:", texto)
        self.assertIn("[humano] #7 feat: pr 7 — corrigido:", texto)
        self.assertEqual(telemetria._frase_da_diferenca({**r, "diferenca_pp": 12.5}),
                         "A entrega da fábrica volta 12.5 p.p. acima da das pessoas.")
        self.assertIn("abaixo", telemetria._frase_da_diferenca({**r, "diferenca_pp": -3.0}))

    def test_amostra_pequena_nao_vira_taxa_nem_veredicto(self) -> None:
        for n in range(1, 6):
            self.pr(n, [f"src/f{n}.py"], dia=n, fabrica=True)
        for n in range(6, 9):
            self.pr(n, [f"src/h{n}.py"], dia=n, fabrica=False)
        r = self.comparar()
        self.assertIsNone(r["humano"]["taxa_voltaram"])
        self.assertFalse(r["comparavel"])
        self.assertIsNone(r["diferenca_pp"])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            telemetria.imprimir_comparacao({"fonte": "git", **r}, None)
        self.assertIn("amostra pequena", out.getvalue())
        self.assertIn("Não comparável", out.getvalue())

    def test_pr_com_a_janela_aberta_fica_em_observacao_e_fora_da_conta(self) -> None:
        for n in range(1, 6):
            self.pr(n, [f"src/f{n}.py"], dia=n, fabrica=True)
        self.pr(6, [f"src/f6.py"], dia=20, fabrica=True)       # 2026-10-21
        self.pr(7, [f"src/h7.py"], dia=21, fabrica=False)      # 2026-10-22
        r = self.comparar(agora=datetime(2026, 10, 30, tzinfo=timezone.utc))
        self.assertEqual(r["em_observacao"], {"fabrica": 1, "humano": 1})
        self.assertEqual((r["fabrica"]["prs"], r["humano"]["prs"]), (5, 0))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            telemetria.imprimir_comparacao({"fonte": "git", **r}, None)
        self.assertIn("em observação", out.getvalue())
        self.assertEqual(self.comparar()["em_observacao"], {"fabrica": 0, "humano": 0})

    def test_correcao_e_revert_que_chegam_por_merge_commit_contam(self) -> None:
        for n in range(1, 6):
            self.pr(n, [f"src/f{n}.py"], dia=n, fabrica=True)
        for n, titulo in ((20, "fix: f1 aceitava vazio"), (21, 'Revert "feat: pr 3"')):
            self.g("checkout", "-q", "-b", f"b{n}")
            self.escrever(f"src/f{1 if n == 20 else 3}.py", f"# {n}\n")
            self.g("commit", "-qam", "x", dia=7)
            self.g("checkout", "-q", "main")
            self.g("merge", "-q", "--no-ff", f"b{n}", "-m",
                   f"Merge pull request #{n} from org/b{n}\n\n{titulo}", dia=7)
        r = self.comparar()
        f = r["fabrica"]
        self.assertEqual((f["prs"], f["corrigidos"], f["revertidos"]), (5, 1, 1))
        self.assertEqual(sorted(i["numero"] for i in f["voltaram_lista"]), [1, 3])
        self.assertEqual(r["humano"]["prs"], 2)          # o fix e o revert são PRs de pessoa

    def test_revert_pelo_titulo_do_squash_e_pelo_numero(self) -> None:
        pr = {"numero": 12, "titulo": "feat: exportar CSV", "entrega": "a" * 40, "commits": []}
        def c(assunto: str, corpo: str = "") -> dict:
            return {"assunto": assunto, "corpo": corpo}
        self.assertTrue(telemetria.reverte(c('Revert "feat: exportar CSV (#12)" (#15)'), pr, ["a" * 40]))
        self.assertTrue(telemetria.reverte(c('Revert "feat: exportar CSV"'), pr, ["a" * 40]))
        self.assertTrue(telemetria.reverte(c("Revert x", "This reverts commit aaaaaaa."), pr, ["a" * 40]))
        self.assertFalse(telemetria.reverte(c('Revert "feat: outro (#120)"'), pr, ["a" * 40]))
        self.assertFalse(telemetria.reverte(c("fix: exportar CSV #12"), pr, ["a" * 40]))

    def test_cli_compara_e_recusa_marca_invalida(self) -> None:
        self.pr(1, ["src/f1.py"], dia=1, fabrica=True)
        antes, argv = os.getcwd(), sys.argv
        os.chdir(self.raiz)
        try:
            for args, esperado in ((["comparar", "--fonte", "git", "--json"], 0),
                                   (["comparar", "--fonte", "git"], 0),
                                   (["comparar", "--marca", "("], 1),
                                   (["prs", "--fonte"], 1)):
                sys.argv = ["telemetria.py", *args]
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(telemetria.main(), esperado, args)
        finally:
            os.chdir(antes)
            sys.argv = argv
