"""Testes das tags de versão (emenda ao ADR-0057): `release.py tags` e o workflow que o roda.

Num git de verdade, com um remoto local: cada versão ganha a tag no commit da linha
principal em que entrou, a versão que entrou junto com outra fica sem tag, a tag que já
existe em outro commit não se move, e o ensaio não cria nada. O `release.py` é copiado
para o repositório de teste, porque é a pasta dele que diz onde o git roda.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
RELEASE = RAIZ / "scripts" / "release.py"
WORKFLOW = RAIZ / ".github" / "workflows" / "tags.yml"
QUEM = {"GIT_AUTHOR_NAME": "Pessoa", "GIT_AUTHOR_EMAIL": "pessoa@exemplo.dev",
        "GIT_COMMITTER_NAME": "Pessoa", "GIT_COMMITTER_EMAIL": "pessoa@exemplo.dev"}


class TagsNumGitDeVerdade(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="tags-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.origem = self.tmp / "origem.git"
        self.repo = self.tmp / "repo"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origem)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        (self.repo / "scripts").mkdir()
        shutil.copy2(RELEASE, self.repo / "scripts" / "release.py")
        self.git("remote", "add", "origin", str(self.origem))
        self.c1 = self.versao("0.1.0", "feat: a primeira", "2026-01-10T12:00:00+00:00")
        self.commit("docs: só texto", "2026-01-11T12:00:00+00:00", {"LEIAME.md": "oi"})
        self.c2 = self.versao("0.2.0", "feat: a segunda", "2026-01-12T12:00:00+00:00")
        # Duas versões num branch, mescladas num commit só: na linha principal só a
        # segunda tem commit próprio.
        self.git("checkout", "-q", "-b", "lado")
        self.versao("0.3.0", "feat: a terceira", "2026-01-13T12:00:00+00:00")
        self.versao("0.4.0", "feat: a quarta", "2026-01-14T12:00:00+00:00")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "lado", "-m", "Merge: terceira e quarta",
                 data="2026-01-15T12:00:00+00:00")
        self.c4 = self.cabeca()
        self.commit("chore: manifesto ilegível", "2026-01-16T12:00:00+00:00",
                    {".claude-plugin/plugin.json": '{"version": '})
        self.versao("dev", "chore: versão que não é X.Y.Z", "2026-01-16T13:00:00+00:00")
        self.git("push", "-q", "origin", "main")

    # --- o git de teste --------------------------------------------------------------

    def git(self, *args: str, data: str = "2026-01-01T00:00:00+00:00", cwd: Path | None = None) -> str:
        env = {**os.environ, **QUEM, "GIT_AUTHOR_DATE": data, "GIT_COMMITTER_DATE": data}
        r = subprocess.run(["git", "-C", str(cwd or self.repo), *args], env=env,
                           capture_output=True, text=True, check=True)
        return r.stdout.strip()

    def commit(self, msg: str, data: str, arquivos: dict[str, str]) -> str:
        for rel, texto in arquivos.items():
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / rel).write_text(texto, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg, data=data)
        return self.cabeca()

    def versao(self, versao: str, msg: str, data: str) -> str:
        return self.commit(msg, data, {".claude-plugin/plugin.json": json.dumps({"version": versao})})

    def cabeca(self) -> str:
        return self.git("rev-parse", "HEAD")

    def rodar(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, **QUEM, "PYTHONDONTWRITEBYTECODE": "1"}
        return subprocess.run(["python3", str(self.repo / "scripts" / "release.py"), "tags", *args],
                              env=env, capture_output=True, text=True)

    def no_origem(self) -> dict[str, str]:
        """Tag → commit marcado, como o origin as tem."""
        saida = self.git("for-each-ref", "--format=%(refname:short) %(*objectname) %(objectname)",
                         "refs/tags", cwd=self.origem)
        return {nome: alvos[0] for nome, *alvos in (linha.split() for linha in saida.splitlines())}

    # --- o que o comando faz ---------------------------------------------------------

    def test_o_ensaio_mostra_e_nao_cria_nada(self) -> None:
        r = self.rodar()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, rf"criar\s+v0\.1\.0\s+{self.c1[:9]}")
        self.assertIn("ensaio", r.stdout)
        self.assertEqual(self.git("tag"), "")
        self.assertEqual(self.no_origem(), {})

    def test_cada_versao_ganha_a_tag_no_commit_em_que_entrou(self) -> None:
        r = self.rodar("--publicar")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.no_origem(), {"v0.1.0": self.c1, "v0.2.0": self.c2, "v0.4.0": self.c4})
        self.assertIn("publicadas: v0.1.0, v0.2.0, v0.4.0\n", r.stdout)
        self.assertNotIn("ensaio", r.stdout)                  # publicou: não é ensaio

    def test_a_versao_que_entrou_junto_com_outra_fica_sem_tag(self) -> None:
        self.rodar("--publicar")
        self.assertNotIn("v0.3.0", self.no_origem())
        # O manifesto ilegível e a versão fora de X.Y.Z também não viram tag nem derrubam o comando.
        self.assertNotIn("vdev", self.no_origem())
        self.assertEqual(len(self.no_origem()), 3)

    def test_a_tag_e_anotada_com_a_data_e_o_assunto_do_commit(self) -> None:
        self.rodar("--publicar")
        self.assertEqual(self.git("cat-file", "-t", "refs/tags/v0.2.0", cwd=self.origem), "tag")
        corpo = self.git("cat-file", "-p", "refs/tags/v0.2.0", cwd=self.origem)
        self.assertIn("kairos-forge v0.2.0", corpo)
        self.assertIn("feat: a segunda", corpo)
        epoca = self.git("log", "-1", "--format=%ct", self.c2)
        self.assertRegex(corpo, rf"(?m)^tagger Pessoa <pessoa@exemplo\.dev> {epoca} ")

    def test_rodar_de_novo_nao_cria_nem_publica_nada(self) -> None:
        self.rodar("--publicar")
        antes = self.no_origem()
        r = self.rodar("--publicar")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0 a criar, 3 já existem", r.stdout)
        self.assertNotIn("publicadas:", r.stdout)
        self.assertNotIn("ensaio", r.stdout)
        self.assertEqual(self.no_origem(), antes)

    def test_a_versao_nova_ganha_so_a_tag_dela(self) -> None:
        self.rodar("--publicar")
        c5 = self.versao("0.5.0", "feat: a quinta", "2026-01-17T12:00:00+00:00")
        self.git("push", "-q", "origin", "main")
        r = self.rodar("--publicar")
        self.assertIn("publicadas: v0.5.0\n", r.stdout)
        self.assertEqual(self.no_origem()["v0.5.0"], c5)

    def test_a_tag_que_ja_existe_em_outro_commit_nao_se_move(self) -> None:
        self.git("tag", "v0.2.0", self.c1)
        self.git("push", "-q", "origin", "refs/tags/v0.2.0")
        self.git("tag", "-d", "v0.2.0")
        r = self.rodar("--publicar")
        self.assertEqual(r.returncode, 1)
        self.assertIn("v0.2.0 já existe em outro commit", r.stderr)
        no_origem = self.no_origem()
        self.assertEqual(self.git("rev-parse", "refs/tags/v0.2.0^{commit}", cwd=self.origem), self.c1)
        self.assertEqual((no_origem["v0.1.0"], no_origem["v0.4.0"]), (self.c1, self.c4))  # as outras saem

    def test_o_que_vale_ao_publicar_e_o_origin_e_nao_este_clone(self) -> None:
        # A tag criada aqui e nunca publicada (o que o 403 do proxy deixou neste container).
        self.git("tag", "-a", "v0.1.0", self.c1, "-m", "local")
        self.assertIn("existe     v0.1.0", self.rodar().stdout)
        self.rodar("--publicar")
        self.assertEqual(self.no_origem()["v0.1.0"], self.c1)

    def test_tag_local_em_outro_commit_para_antes_de_publicar(self) -> None:
        self.git("tag", "v0.1.0", self.c2)
        r = self.rodar("--publicar")
        self.assertEqual(r.returncode, 1)
        self.assertIn("v0.1.0 existe neste clone em outro commit", r.stderr)
        self.assertEqual(self.no_origem(), {})

    def test_sem_origin_o_erro_e_uma_linha_e_nao_um_traceback(self) -> None:
        self.git("remote", "remove", "origin")
        r = self.rodar("--publicar")
        self.assertEqual(r.returncode, 1)
        self.assertTrue(r.stderr.startswith("erro: git ls-remote"), r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_argumento_desconhecido_mostra_o_uso(self) -> None:
        r = self.rodar("--force")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("release.py tags [--publicar]", r.stderr)


class Workflow(unittest.TestCase):
    """O que publica as tags: na main, a cada versão, sem nada que mova ou apague tag."""

    def setUp(self) -> None:
        self.texto = WORKFLOW.read_text(encoding="utf-8")
        self.passos = self.texto.split("    steps:\n", 1)[1]

    def test_roda_na_main_quando_a_versao_muda_e_a_mao(self) -> None:
        self.assertRegex(self.texto, r"on:\n  push:\n    branches: \[main\]\n"
                                     r"    paths: \[\"\.claude-plugin/plugin\.json\"\]\n  workflow_dispatch:")
        self.assertNotIn("pull_request", self.texto)

    def test_so_pede_escrita_no_conteudo(self) -> None:
        self.assertIn("permissions:\n  contents: write\n\n", self.texto)
        self.assertEqual(self.texto.count("permissions:"), 1)

    def test_checkout_fixado_com_a_historia_inteira_e_sem_credencial(self) -> None:
        checkout = self.passos[:self.passos.index("\n\n")]
        self.assertRegex(checkout, r"uses: actions/checkout@[0-9a-f]{40} # v\d+\.\d+\.\d+")
        self.assertIn("fetch-depth: 0", checkout)
        self.assertIn("persist-credentials: false", checkout)

    def test_quem_decide_e_o_release_py_sem_nada_que_mova_tag(self) -> None:
        self.assertIn("python3 scripts/release.py tags --publicar", self.passos)
        self.assertIn("gh auth setup-git", self.passos)
        for proibido in ("--force", " -f ", "tag -d", "--delete", "git push", "git tag"):
            self.assertNotIn(proibido, self.passos)

    def test_e_o_mesmo_checkout_dos_gatilhos_de_ci(self) -> None:
        fixado = re.search(r"actions/checkout@([0-9a-f]{40})", self.texto).group(1)
        for template in sorted((RAIZ / "templates" / "ci").glob("*.yml")):
            self.assertIn(f"actions/checkout@{fixado}", template.read_text(encoding="utf-8"), template.name)


if __name__ == "__main__":
    unittest.main()
