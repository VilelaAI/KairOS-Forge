"""Testes do `prova.py origem` (ADR-0059): o que é do PR e o que já existia.

O relatório do `/revisar` é conferido contra o diff, num git de verdade. O achado que bloqueia
(🔴, 🟠) numa linha que o PR não tocou precisa dizer como o PR o afeta; senão, é problema
antigo e vai para `## Fora deste PR`. E a observação numa linha que o PR escreveu é do PR.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import prova  # noqa: E402

QUEM = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "commit.gpgsign",
        "GIT_CONFIG_VALUE_0": "false"}
EXPORTAR = 'import os\n\ndef exportar(nome):\n    return open(os.path.join("saida", nome), "w")\n'
ANTES = "def total(xs):\n    return sum(xs)\n\n\ndef media(xs):\n    return 0\n"
DEPOIS = ("def total(xs):\n    return sum(xs)\n\n\ndef media(xs):\n"
          "    validas = [x for x in xs if x > 0]\n    return sum(validas) / len(validas)\n")


class ComRepositorio(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-origem-")
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self.git("init", "-q", "-b", "main")
        self.escrever({"vendas/exportar.py": EXPORTAR, "vendas/relatorio.py": ANTES,
                       "vendas/fim.py": "a = 1\nb = 2\nc = 3\nd = 4\n"})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.git("checkout", "-q", "-b", "feature/media")
        self.escrever({"vendas/relatorio.py": DEPOIS, "vendas/fim.py": "a = 1\nd = 4\n"})
        self.git("commit", "-q", "-am", "media")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.raiz, env={**os.environ, **QUEM}, check=True,
                              capture_output=True, text=True).stdout

    def escrever(self, arquivos: dict[str, str]) -> None:
        for rel, texto in arquivos.items():
            (self.raiz / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.raiz / rel).write_text(texto, encoding="utf-8")

    def conferir(self, relatorio: str) -> dict:
        arq = self.raiz / "REVISAO.md"
        arq.write_text(relatorio, encoding="utf-8")
        return prova.origem(self.raiz, "main", str(arq))

    def textos(self, r: dict, chave: str) -> list[str]:
        return [a["texto"] for a in r[chave]]


class OQueBloqueiaPrecisaSerDoPR(ComRepositorio):
    def test_o_antigo_que_bloqueia_sem_dizer_como_o_pr_o_afeta(self) -> None:
        r = self.conferir("## 🔴 Crítico\n- [Helena] R1 · vendas/exportar.py:4 — caminho sem normalizar.\n")
        self.assertEqual(self.textos(r, "fora_sem_dizer"),
                         ["[Helena] R1 · vendas/exportar.py:4 — caminho sem normalizar."])

    def test_o_alto_tambem(self) -> None:
        r = self.conferir("## 🟠 Alto\n- [Helena] vendas/exportar.py:3 — sem teste.\n")
        self.assertEqual(len(r["fora_sem_dizer"]), 1)

    def test_o_do_pr_passa(self) -> None:
        r = self.conferir("## 🔴 Crítico\n- [Patrícia] R1 · vendas/relatorio.py:7 — divide por zero.\n"
                          "## 🟠 Alto\n- [Patrícia] `vendas/relatorio.py:6-7` — sem teste.\n")
        self.assertEqual((r["fora_sem_dizer"], r["conferidos"]), ([], 2))

    def test_a_linha_ao_lado_da_mexida_passa(self) -> None:
        r = self.conferir("## 🔴 Crítico\n- R1 · vendas/relatorio.py:4 — a assinatura não trata None.\n")
        self.assertEqual(r["fora_sem_dizer"], [])
        r = self.conferir("## 🔴 Crítico\n- R1 · vendas/relatorio.py:3 — no limite da folga.\n")
        self.assertEqual(r["fora_sem_dizer"], [])
        r = self.conferir("## 🔴 Crítico\n- R1 · vendas/relatorio.py:2 — longe da mudança.\n")
        self.assertEqual(len(r["fora_sem_dizer"]), 1)

    def test_a_linha_removida_que_parece_cabecalho_nao_perde_o_arquivo(self) -> None:
        """Comentário SQL removido sai no diff como `--- …`; o trecho seguinte continua do
        mesmo arquivo."""
        sql = "".join(f"select {i};\n" for i in range(1, 10))
        self.git("checkout", "-q", "main")
        self.escrever({"vendas/consulta.sql": "-- antigo\n" + sql})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "sql")
        self.git("checkout", "-q", "feature/media")
        self.git("merge", "-q", "--no-edit", "main")
        self.escrever({"vendas/consulta.sql": sql.replace("select 9;", "select 99;")})
        r = self.conferir("## 🔴 Crítico\n- R1 · vendas/consulta.sql:9 — trocou o 9.\n")
        self.assertEqual(r["fora_sem_dizer"], [])

    def test_a_linha_apagada_conta_onde_estava(self) -> None:
        r = self.conferir("## 🔴 Crítico\n- R1 · vendas/fim.py:2 — tirou o `c` que o fluxo usa.\n")
        self.assertEqual(r["fora_sem_dizer"], [])

    def test_quem_depende_ou_piora_fica_marcado(self) -> None:
        for marca in ("· o PR depende: a média nova chama isto", "· o PR piora: passa a vir da URL",
                      "· O PR Depende: idem"):
            with self.subTest(marca):
                r = self.conferir(f"## 🔴 Crítico\n- R1 · vendas/exportar.py:4 — sem normalizar {marca}.\n")
                self.assertEqual(r["fora_sem_dizer"], [])

    def test_o_arquivo_novo_e_o_nao_rastreado_inteiros(self) -> None:
        self.escrever({"vendas/novo.py": "x = 1\n" * 50})
        r = self.conferir("## 🔴 Crítico\n- R1 · vendas/novo.py:40 — x sem uso.\n")
        self.assertEqual(r["fora_sem_dizer"], [])

    def test_o_que_nao_bloqueia_e_o_descartado_nao_sao_conferidos(self) -> None:
        r = self.conferir("## 🟡 Médio\n- vendas/exportar.py:4 — nome ruim.\n"
                          "## 🔵 Baixo\n- vendas/exportar.py:1 — import solto.\n"
                          "## 🔴 Crítico\n- R1 · vendas/exportar.py:4 — antigo · descartado: já existia\n")
        self.assertEqual((r["fora_sem_dizer"], r["conferidos"]), ([], 0))

    def test_sem_local_fica_como_nao_conferido(self) -> None:
        r = self.conferir("## 🔴 Crítico\n- [Helena] R1 · api/upload — sem limite de tamanho.\n")
        self.assertEqual((r["fora_sem_dizer"], len(r["sem_local"])), ([], 1))


class AObservacaoNaoEscondeOQueEDoPR(ComRepositorio):
    def test_a_observacao_numa_linha_que_o_pr_escreveu(self) -> None:
        r = self.conferir("## Fora deste PR (já existia; não bloqueia)\n"
                          "- [Patrícia] vendas/relatorio.py:7 — divide por zero.\n")
        self.assertEqual(self.textos(r, "do_pr_como_observacao"),
                         ["[Patrícia] vendas/relatorio.py:7 — divide por zero."])

    def test_a_observacao_do_que_ja_existia_passa(self) -> None:
        r = self.conferir("## Fora deste PR\n- [Helena] vendas/exportar.py:4 — sem normalizar. Outra tarefa.\n"
                          "- [Helena] vendas/relatorio.py:2 — total sem tipo.\n")
        self.assertEqual(r["do_pr_como_observacao"], [])

    def test_a_observacao_ao_lado_da_mudanca_nao_e_acusada(self) -> None:
        r = self.conferir("## Fora deste PR\n- vendas/relatorio.py:4 — a assinatura já era assim.\n")
        self.assertEqual(r["do_pr_como_observacao"], [])

    def test_a_observacao_logo_depois_da_linha_apagada_nao_e_acusada(self) -> None:
        """O `fim.py` perdeu duas linhas depois da 1: o trecho é a 1, e a 2 é a antiga `d = 4`."""
        r = self.conferir("## Fora deste PR\n- vendas/fim.py:2 — `d` sem uso.\n")
        self.assertEqual(r["do_pr_como_observacao"], [])
        r = self.conferir("## Fora deste PR\n- vendas/fim.py:1 — onde o PR apagou.\n")
        self.assertEqual(len(r["do_pr_como_observacao"]), 1)


class OLeitorDoRelatorio(unittest.TestCase):
    def test_secoes_bloco_de_codigo_e_campos(self) -> None:
        texto = ("# Revisão\n## 🔴 Crítico (qualquer revisor) → bloqueia merge\n"
                 "- [Helena] R1 · `api/users.ts:42-44` — SQL injection.\n"
                 "```kairos-revisao\n## 🔴 dentro do bloco\n- api/x.ts:1 — não é achado\n```\n"
                 "## ✅ O que está bom\n- api/y.ts:3 — fica de fora\n"
                 "## Fora deste PR\n- lib/z.py:9 — antigo\n")
        self.assertEqual(prova.achados_da_revisao(texto), [
            {"secao": "bloqueia", "texto": "[Helena] R1 · `api/users.ts:42-44` — SQL injection.",
             "arquivo": "api/users.ts", "inicio": 42, "fim": 44, "justificado": False},
            {"secao": "fora", "texto": "lib/z.py:9 — antigo", "arquivo": "lib/z.py", "inicio": 9,
             "fim": 9, "justificado": False}])


class PeloComando(ComRepositorio):
    def rodar(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", str(RAIZ / "prova.py"), "origem", *args],
                              cwd=self.raiz, capture_output=True, text=True, env={**os.environ, **QUEM})

    def test_sai_1_com_achado_fora_do_lugar_e_0_sem(self) -> None:
        (self.raiz / "ruim.md").write_text("## 🔴 Crítico\n- R1 · vendas/exportar.py:4 — antigo.\n")
        (self.raiz / "certo.md").write_text("## Fora deste PR\n- vendas/exportar.py:4 — antigo.\n")
        r = self.rodar("ruim.md", "--base", "main")
        self.assertEqual(r.returncode, 1)
        self.assertIn("bloqueia numa linha que o PR não tocou", r.stdout)
        r = self.rodar("certo.md", "--base", "main")
        self.assertEqual(r.returncode, 0)
        self.assertIn("✅ o que bloqueia é do PR", r.stdout)

    def test_json_e_erros_numa_linha(self) -> None:
        (self.raiz / "certo.md").write_text("## Fora deste PR\n- vendas/exportar.py:4 — antigo.\n")
        r = self.rodar("certo.md", "--base", "main", "--json")
        self.assertEqual(json.loads(r.stdout)["conferidos"], 1)
        for args, erro in ((("--base", "main"), "diga qual relatório"),
                           (("nada.md", "--base", "main"), "não li o relatório"),
                           (("certo.md", "--base", "nao-existe"), "sem base para o diff")):
            with self.subTest(args):
                r = self.rodar(*args)
                self.assertEqual(r.returncode, 1)
                self.assertIn(erro, r.stdout)


class AImpressao(ComRepositorio):
    """A mesma saída do comando, lida no processo: cada lista com o título e a dica dela."""

    def imprimir(self, relatorio: str) -> str:
        saida = io.StringIO()
        with redirect_stdout(saida):
            prova.imprimir_origem(self.conferir(relatorio))
        return saida.getvalue()

    def test_cada_erro_com_o_titulo_e_a_dica_dele(self) -> None:
        saida = self.imprimir("## 🔴 Crítico\n- R1 · vendas/exportar.py:4 — antigo.\n"
                              "## Fora deste PR\n- vendas/relatorio.py:7 — divide por zero.\n"
                              "## 🟡 Sugestões\n- sem local.\n")
        self.assertIn("REVISAO.md contra main", saida)
        self.assertIn("2 achado(s) com local conferido(s)\n", saida)   # o 🟡 não entra na conta
        fora, dentro = saida.index("não tocou"), saida.index("o PR escreveu")
        self.assertLess(fora, saida.index("R1 · vendas/exportar.py:4"))
        self.assertLess(saida.index("`## Fora deste PR`"), dentro)
        self.assertLess(dentro, saida.index("vendas/relatorio.py:7 — divide"))
        self.assertIn("volta para a seção da gravidade dele", saida)
        self.assertNotIn("✅", saida)

    def test_so_um_dos_erros(self) -> None:
        saida = self.imprimir("## Fora deste PR\n- vendas/relatorio.py:7 — divide por zero.\n")
        self.assertNotIn("não tocou", saida)
        self.assertIn("o PR escreveu", saida)
        self.assertNotIn("✅", saida)

    def test_sem_erro_e_com_achado_sem_local(self) -> None:
        saida = self.imprimir("## 🔴 Crítico\n- R1 · vendas/relatorio.py:7 — divide por zero.\n"
                              "## 🟠 Alto\n- A1 · sem local.\n")
        self.assertIn("1 achado(s) com local conferido(s), 1 sem `arquivo:linha`", saida)
        self.assertIn("✅ o que bloqueia é do PR", saida)
        self.assertNotIn("✗", saida)

    def test_o_texto_longo_e_cortado(self) -> None:
        saida = self.imprimir("## 🔴 Crítico\n- R1 · vendas/exportar.py:4 — " + "x" * 300 + "\n")
        self.assertIn("x" * 100, saida)
        self.assertNotIn("x" * 150, saida)

    def test_os_erros_no_processo(self) -> None:
        for relatorio, erro in ((None, "🚫 diga qual relatório conferir"),
                                (str(self.raiz / "nada.md"), "🚫 não li o relatório"),
                                (str(self.raiz / "vendas"), "🚫 não li o relatório")):
            with self.subTest(relatorio):
                r = prova.origem(self.raiz, "main", relatorio)
                self.assertEqual(set(r), {"erro"})
                saida = io.StringIO()
                with redirect_stdout(saida):
                    prova.imprimir_origem(r)
                self.assertTrue(saida.getvalue().startswith(erro), saida.getvalue())
        (self.raiz / "latin.md").write_bytes("## 🔴\n- ç".encode("utf-16"))
        self.assertIn("não li", prova.origem(self.raiz, "main", str(self.raiz / "latin.md"))["erro"])
        arq = self.raiz / "REVISAO.md"
        arq.write_text("## Fora deste PR\n", encoding="utf-8")
        self.assertIn("(nao-existe)", prova.origem(self.raiz, "nao-existe", str(arq))["erro"])

    def test_sem_base_usa_a_padrao(self) -> None:
        arq = self.raiz / "REVISAO.md"
        arq.write_text("## 🔴 Crítico\n- R1 · vendas/exportar.py:4 — antigo.\n", encoding="utf-8")
        with mock.patch.object(prova, "base_padrao", return_value="main") as padrao:
            r = prova.origem(self.raiz, None, str(arq))
        padrao.assert_called_once_with(self.raiz)
        self.assertEqual((r["base"], len(r["fora_sem_dizer"])), ("main", 1))
        with mock.patch.object(prova, "base_padrao", return_value=None):
            self.assertIn("(nenhuma ref)", prova.origem(self.raiz, None, str(arq))["erro"])


class NoGatilhoDeCI(ComRepositorio):
    """Os passos do `kairos-forge-revisar.yml` rodados de verdade, com um `gh` falso."""

    def passos(self) -> tuple[str, str]:
        from tests.test_ci import blocos_run, ler
        blocos = [s for _, s in blocos_run(ler("revisar"))]
        (conferir,) = [b for b in blocos if "prova.py origem" in b]
        (comentar,) = [b for b in blocos if "gh pr comment" in b]
        return tuple(b.replace("/tmp/forge/scripts", str(RAIZ)) for b in (conferir, comentar))

    def publicar(self, revisao: str) -> str:
        conferir, comentar = self.passos()
        (self.raiz / "revisao.md").write_text(revisao, encoding="utf-8")
        bin_ = self.raiz / ".bin"
        bin_.mkdir()
        (bin_ / "gh").write_text('#!/bin/sh\nwhile [ "$1" != "--body-file" ]; do shift; done\n'
                                 'cp "$2" "$PUBLICADO"\n', encoding="utf-8")
        (bin_ / "gh").chmod(0o755)
        env = {**os.environ, **QUEM, "PATH": f"{bin_}{os.pathsep}{os.environ.get('PATH', '')}",
               "BASE": self.git("rev-parse", "main").strip(), "PR": "7",
               "PUBLICADO": str(self.raiz / "publicado.md")}
        for script in (conferir, comentar):
            subprocess.run(["bash", "-e", "-c", script], cwd=self.raiz, env=env, check=True,
                           capture_output=True, text=True)
        return (self.raiz / "publicado.md").read_text(encoding="utf-8")

    def test_o_achado_fora_do_lugar_aparece_no_comentario(self) -> None:
        publicado = self.publicar("## 🔴 Crítico\n- [Helena] R1 · vendas/exportar.py:4 — antigo.\n")
        self.assertIn("### Conferência da origem dos achados", publicado)
        self.assertIn("bloqueia numa linha que o PR não tocou", publicado)

    def test_a_revisao_certa_sai_sem_a_conferencia(self) -> None:
        publicado = self.publicar("## Fora deste PR\n- [Helena] vendas/exportar.py:4 — antigo.\n")
        self.assertIn("vendas/exportar.py:4", publicado)
        self.assertNotIn("Conferência da origem", publicado)


if __name__ == "__main__":
    unittest.main()
