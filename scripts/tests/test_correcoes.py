"""Testes do `telemetria.py prs --correcoes` — o que as pessoas mudaram nos PRs da fábrica
(emenda ao ADR-0044), o insumo do /evoluir.

Num git de verdade, com merges datados: o commit humano dentro do PR da fábrica, a correção
e o revert humanos depois do merge (pelos critérios do `comparar`), a correção da própria
fábrica que não conta, e o PR de pessoa que fica de fora. A leitura do `gh`, para o commit
que não está no clone, é testada com a resposta dele simulada.

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
PESSOA = "Maria Humana"
AGENTE = "Claude"
AGORA = datetime(2026, 10, 20, tzinfo=timezone.utc)


class CorrecoesNumGitDeVerdade(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-correcoes-")
        self.raiz = Path(self._tmp.name).resolve()
        self.g("init", "-q", "-b", "main", ".")
        self.g("commit", "-q", "--allow-empty", "-m", "base")
        # PR 1 da fábrica, com um commit de pessoa dentro (e um binário)
        self.pr(1, [(AGENTE, "feat: a" + FABRICA, {"src/a.py": "a = 1\n"}),
                    (PESSOA, "fix: ajusta a", {"src/a.py": "a = 2\n", "tests/test_a.py": "ok\n",
                                               "img/x.bin": b"\x00\x01\x02"})], dia=1)
        # PR 2 da fábrica, corrigido por uma pessoa na main; a fábrica corrige depois e não conta
        self.pr(2, [(AGENTE, "feat: b" + FABRICA, {"src/b.py": "b = 1\n"})], dia=2)
        self.commit_na_main(PESSOA, "fix: corrige b", {"src/b.py": "b = 2\n", "docs/x.md": "x\n"}, dia=4)
        self.commit_na_main(AGENTE, "fix: b de novo" + FABRICA, {"src/b.py": "b = 3\n"}, dia=5)
        # PR 3 da fábrica, revertido por uma pessoa
        self.merge3 = self.pr(3, [(AGENTE, "feat: c" + FABRICA, {"src/c.py": "c = 1\n"})], dia=3)
        self.g("revert", "-m", "1", "--no-edit", self.merge3, dia=6, autor=PESSOA)
        # PR 4 da fábrica; a fábrica corrige no PR 5, e uma pessoa no PR 6 (que pega o 4 e o 5)
        self.pr(4, [(AGENTE, "feat: d" + FABRICA, {"src/d.py": "d = 1\n"})], dia=7)
        self.pr(5, [(AGENTE, "fix: corrige d" + FABRICA, {"src/d.py": "d = 2\n"})], dia=8)
        self.pr(6, [(PESSOA, "fix: d mais", {"src/d.py": "d = 3\n"})], dia=9)
        # PR 7 de pessoa, corrigido por pessoa: não é da fábrica, fica de fora
        self.pr(7, [(PESSOA, "feat: h", {"src/h.py": "h = 1\n"})], dia=10)
        self.commit_na_main(PESSOA, "fix: corrige h", {"src/h.py": "h = 2\n"}, dia=11)
        # PR 8 da fábrica, que ninguém tocou
        self.pr(8, [(AGENTE, "feat: e" + FABRICA, {"src/e.py": "e = 1\n"})], dia=12)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # --- o git de teste --------------------------------------------------------------

    def g(self, *args: str, dia: int = 0, autor: str = PESSOA) -> str:
        data = f"2026-10-{1 + dia:02d}T10:00:00+00:00"
        env = {**os.environ, "GIT_AUTHOR_DATE": data, "GIT_COMMITTER_DATE": data}
        r = subprocess.run(["git", "-C", str(self.raiz), "-c", f"user.name={autor}", "-c",
                            "user.email=a@b", *args], check=True, capture_output=True,
                           text=True, env=env)
        return r.stdout.strip()

    def escrever(self, arquivos: dict) -> None:
        for rel, conteudo in arquivos.items():
            p = self.raiz / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(conteudo) if isinstance(conteudo, bytes) else p.write_text(conteudo, encoding="utf-8")

    def pr(self, numero: int, commits: list[tuple[str, str, dict]], dia: int) -> str:
        branch = f"b{numero}"
        self.g("checkout", "-q", "-b", branch)
        for autor, mensagem, arquivos in commits:
            self.escrever(arquivos)
            self.g("add", ".")
            self.g("commit", "-q", "-m", mensagem, dia=dia, autor=autor)
        self.g("checkout", "-q", "main")
        titulo = commits[-1][1].split("\n", 1)[0]
        self.g("merge", "-q", "--no-ff", branch, "-m",
               f"Merge pull request #{numero} from org/{branch}\n\n{titulo}", dia=dia)
        return self.g("rev-parse", "HEAD")

    def commit_na_main(self, autor: str, mensagem: str, arquivos: dict, dia: int) -> None:
        self.escrever(arquivos)
        self.g("add", ".")
        self.g("commit", "-q", "-m", mensagem, dia=dia, autor=autor)

    def correcoes(self) -> dict:
        _, prs = telemetria.prs_mesclados(self.raiz, None, "git")
        return telemetria.correcoes_humanas(self.raiz, prs, agora=AGORA)

    def por_numero(self, r: dict) -> dict:
        return {i["numero"]: i for i in r["prs"]}

    # --- o que sai -------------------------------------------------------------------

    def test_conta_os_prs_da_fabrica_e_os_que_uma_pessoa_mudou(self) -> None:
        r = self.correcoes()
        self.assertEqual(r["da_fabrica"], 6)                          # 1, 2, 3, 4, 5 e 8
        self.assertEqual([i["numero"] for i in r["prs"]], [5, 4, 3, 2, 1])   # do mais recente, como o `prs`
        self.assertEqual((r["com_mudanca"], r["antes_do_merge"], r["depois_do_merge"]), (5, 1, 4))

    def test_o_commit_de_pessoa_dentro_do_pr_vem_com_os_arquivos_e_as_linhas(self) -> None:
        pr1 = self.por_numero(self.correcoes())[1]
        self.assertEqual(pr1["depois"], [])
        [m] = pr1["antes"]
        self.assertEqual((m["assunto"], m["tipo"]), ("fix: ajusta a", "fix"))
        self.assertEqual(m["arquivos"], [{"arquivo": "img/x.bin", "mais": None, "menos": None},
                                         {"arquivo": "src/a.py", "mais": 1, "menos": 1},
                                         {"arquivo": "tests/test_a.py", "mais": 1, "menos": 0}])

    def test_a_correcao_de_pessoa_na_main_conta_so_os_arquivos_do_pr(self) -> None:
        pr2 = self.por_numero(self.correcoes())[2]
        [m] = pr2["depois"]                                    # a correção da fábrica não conta
        self.assertEqual((m["sinal"], m["assunto"], m["tipo"]), ("corrigido", "fix: corrige b", "fix"))
        self.assertEqual([a["arquivo"] for a in m["arquivos"]], ["src/b.py"])   # docs/x.md fora

    def test_o_revert_de_pessoa(self) -> None:
        [m] = self.por_numero(self.correcoes())[3]["depois"]
        self.assertEqual((m["sinal"], m["tipo"]), ("revertido", "revert"))
        self.assertEqual([a["arquivo"] for a in m["arquivos"]], ["src/c.py"])

    def test_o_pr_que_corrige_decide_se_foi_pessoa_ou_fabrica(self) -> None:
        r = self.por_numero(self.correcoes())
        for numero in (4, 5):                              # o PR 6 (pessoa) mexe no d dos dois
            [m] = r[numero]["depois"]
            self.assertEqual((m["sinal"], m["assunto"]), ("corrigido", "fix: d mais"))
        self.assertNotIn(7, r)                                     # PR de pessoa fica de fora
        self.assertNotIn(8, r)                                     # PR que ninguém tocou

    def test_agrega_por_arquivo_e_por_tipo_sem_o_nome_de_quem_mudou(self) -> None:
        r = self.correcoes()
        self.assertEqual(r["por_arquivo"][0], {"arquivo": "src/d.py", "prs": 2, "commits": 2})
        self.assertEqual({a["arquivo"] for a in r["por_arquivo"][1:]},
                         {"img/x.bin", "src/a.py", "src/b.py", "src/c.py", "tests/test_a.py"})
        self.assertEqual(r["por_tipo"], {"fix": 4, "revert": 1})
        self.assertEqual(r["nao_lidos"], 0)
        self.assertEqual(r["janela_aberta"], 3)                    # 4, 5 e 8: menos de 14 dias
        self.assertNotIn(PESSOA, json.dumps(r, ensure_ascii=False))

    def test_o_texto_diz_onde_o_que_e_como_ver_o_diff(self) -> None:
        r = {"fonte": "git", **self.correcoes()}
        with contextlib.redirect_stdout(io.StringIO()) as out:
            telemetria.imprimir_correcoes(r, 30)
        texto = out.getvalue()
        self.assertIn("últimos 30 dias (fonte: git)", texto)
        self.assertIn("squash e rebase não aparecem", texto)
        self.assertIn("PRs da fábrica: 6 · com mudança de uma pessoa: 5 (antes do merge: 1 · depois: 4)", texto)
        self.assertIn("3 mesclado(s) há menos de 14 dias", texto)
        self.assertIn("src/d.py — 2 PR(s), 2 commit(s)", texto)
        self.assertIn("Tipo de mudança: fix 4 · revert 1", texto)
        self.assertIn("fix: ajusta a — img/x.bin, src/a.py (+1 −1), tests/test_a.py (+1 −0)", texto)
        self.assertIn("depois (revertido)", texto)
        self.assertIn("git show <sha>", texto)
        self.assertNotIn(PESSOA, texto)

    def test_pela_linha_de_comando(self) -> None:
        r = subprocess.run([sys.executable, "-B", str(RAIZ / "telemetria.py"), "prs", "--correcoes",
                            "--fonte", "git", "--json"], cwd=self.raiz, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        dados = json.loads(r.stdout)
        self.assertEqual((dados["fonte"], dados["da_fabrica"], dados["com_mudanca"]), ("git", 6, 5))
        sem = subprocess.run([sys.executable, "-B", str(RAIZ / "telemetria.py"), "prs", "--fonte", "git"],
                             cwd=self.raiz, capture_output=True, text=True)
        self.assertIn("Autonomia de PR", sem.stdout)                # sem a flag, o `prs` de sempre


class SemNadaParaLer(unittest.TestCase):
    def test_sem_pr_da_fabrica_e_sem_mudanca(self) -> None:
        for r, esperado in (({"da_fabrica": 0, "prs": []}, "nada a ler"),
                            ({"da_fabrica": 2, "com_mudanca": 0, "antes_do_merge": 0,
                              "depois_do_merge": 0, "janela_aberta": 0, "prs": []},
                             "Nenhuma pessoa mudou os PRs da fábrica")):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                telemetria.imprimir_correcoes({"fonte": "gh", **r}, None)
            self.assertIn(esperado, out.getvalue())
            self.assertIn("todo o histórico", out.getvalue())
            self.assertNotIn("squash", out.getvalue())


class CommitForaDoClone(unittest.TestCase):
    """Fonte `gh` e squash: o branch do PR foi apagado e o commit não está no clone."""

    OID = "f" * 40

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-correcoes-gh-")
        self.raiz = Path(self._tmp.name)
        self.prs = [{"numero": 9, "titulo": "feat: z", "branch": "z", "mesclado_em": None,
                     "entrega": None, "issues": [], "commits": [
                         {"oid": "a" * 40, "autor": "x", "mensagem": "feat: z" + FABRICA},
                         {"oid": self.OID, "autor": PESSOA, "mensagem": "test: cobre z\n\ncorpo"},
                         {"oid": "b" * 40, "autor": PESSOA, "mensagem": "Merge branch 'main' into z"}]}]

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_o_gh_traz_os_arquivos_e_o_merge_da_base_fica_de_fora(self) -> None:
        resposta = [{"arquivo": "src/z.py", "mais": 3, "menos": 1}, "lixo", {"arquivo": ""}]
        with mock.patch.object(telemetria, "gh_json", return_value=resposta) as gh:
            r = telemetria.correcoes_humanas(self.raiz, self.prs, gh=True)
        [m] = r["prs"][0]["antes"]
        self.assertEqual((m["assunto"], m["tipo"]), ("test: cobre z", "test"))
        self.assertEqual(m["arquivos"], [{"arquivo": "src/z.py", "mais": 3, "menos": 1}])
        argumentos = gh.call_args.args
        self.assertEqual(argumentos[1:3], ("api", f"repos/{{owner}}/{{repo}}/commits/{self.OID}"))

    def test_sem_gh_os_arquivos_ficam_nao_lidos_em_vez_de_vazios(self) -> None:
        with mock.patch.object(telemetria, "gh_json") as gh:
            r = telemetria.correcoes_humanas(self.raiz, self.prs, gh=False)
        gh.assert_not_called()
        self.assertIsNone(r["prs"][0]["antes"][0]["arquivos"])
        self.assertEqual(r["nao_lidos"], 1)
        with mock.patch.object(telemetria, "gh_json", return_value=None):
            self.assertEqual(telemetria.correcoes_humanas(self.raiz, self.prs, gh=True)["nao_lidos"], 1)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            telemetria.imprimir_correcoes({"fonte": "gh", **r}, 30)
        self.assertIn("arquivos não lidos", out.getvalue())
        self.assertIn("1 commit(s) sem arquivos", out.getvalue())


class TipoDoCommit(unittest.TestCase):
    def test_prefixo_revert_correcao_e_outro(self) -> None:
        for assunto, tipo in (("feat(api)!: x", "feat"), ("fix: y", "fix"), ("Test: z", "test"),
                              ('Revert "feat: a"', "revert"), ("revert: volta", "revert"),
                              ("corrige o login", "fix"), ("Atualiza o README", "outro"), ("", "outro")):
            self.assertEqual(telemetria.tipo_do_commit(assunto), tipo, assunto)

    def test_arquivos_da_mudanca(self) -> None:
        muitos = {"arquivos": [{"arquivo": f"f{i}", "mais": 1, "menos": 0} for i in range(6)]}
        self.assertEqual(telemetria._arquivos_da_mudanca(muitos),
                         "f0 (+1 −0), f1 (+1 −0), f2 (+1 −0), f3 (+1 −0) e mais 2")
        self.assertEqual(telemetria._arquivos_da_mudanca({"arquivos": []}), "nenhum arquivo")


if __name__ == "__main__":
    unittest.main()
