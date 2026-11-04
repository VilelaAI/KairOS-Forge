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
