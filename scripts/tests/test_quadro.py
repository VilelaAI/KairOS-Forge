"""Testes do `quadro.py` — a posse exercida, conferida no git (ADR-0048).

Cada teste roda num repositório git de verdade, num diretório temporário, porque o
`quadro.py` trabalha relativo ao cwd e a conferência lê o `git status` e o HEAD.

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
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import quadro  # noqa: E402


def rodar(*args: str) -> tuple[int, str]:
    """Chama o `main()` do quadro.py como a CLI faria; devolve (exit, stdout)."""
    out = io.StringIO()
    antigo = sys.argv
    sys.argv = ["quadro.py", *args]
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try:
                codigo = quadro.main()
            except SystemExit as e:
                codigo = 1 if e.code else 0
    finally:
        sys.argv = antigo
    return int(codigo or 0), out.getvalue()


def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True)


class ComRepositorio(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.antes = os.getcwd()
        os.chdir(self.tmp.name)
        git("init", "-q", "-b", "main")
        git("config", "user.email", "teste@exemplo")
        git("config", "user.name", "Teste")
        git("config", "commit.gpgsign", "false")
        Path("src").mkdir()
        Path("src/app.py").write_text("x = 1\n", encoding="utf-8")
        Path("README.md").write_text("# exemplo\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-qm", "base")
        self.assertEqual(rodar("abrir", "q")[0], 0)

    def tearDown(self) -> None:
        os.chdir(self.antes)
        self.tmp.cleanup()

    def adicionar(self, tid: str, *extra: str) -> int:
        return rodar("adicionar", "q", "--id", tid, "--titulo", tid, "--dono", "lucas",
                     "--pronto-quando", "teste passa", *extra)[0]

    def concluir(self, tid: str, *extra: str) -> tuple[int, str]:
        return rodar("concluir", "q", tid, "--evidencia", "feito", "--gate-ok", *extra)

    def tarefa(self, tid: str) -> dict:
        return json.loads(Path(".agents/quadro/q.json").read_text(encoding="utf-8"))["tasks"][tid]


class PosseExercida(ComRepositorio):
    def test_mudanca_dentro_da_posse_conclui_e_registra_a_conferencia(self) -> None:
        self.adicionar("T1", "--posse", "src/**")
        rodar("iniciar", "q", "T1")
        Path("src/app.py").write_text("x = 2\n", encoding="utf-8")
        Path("src/novo.py").write_text("y = 1\n", encoding="utf-8")
        codigo, saida = self.concluir("T1")
        self.assertEqual(codigo, 0, saida)
        exercida = self.tarefa("T1")["posse_exercida"]
        self.assertTrue(exercida["conferida"])
        self.assertEqual(exercida["mudados"], 2)
        self.assertEqual(exercida["fora"], [])

    def test_arquivo_fora_da_posse_recusa_e_a_tarefa_segue_em_voo(self) -> None:
        self.adicionar("T1", "--posse", "src/**")
        rodar("iniciar", "q", "T1")
        Path("README.md").write_text("# mexido\n", encoding="utf-8")
        codigo, saida = self.concluir("T1")
        self.assertEqual(codigo, 1)
        self.assertIn("README.md", saida)
        self.assertEqual(self.tarefa("T1")["estado"], "em_progresso")

    def test_fora_da_posse_com_motivo_conclui_e_fica_registrado(self) -> None:
        self.adicionar("T1", "--posse", "src/**")
        rodar("iniciar", "q", "T1")
        Path("README.md").write_text("# mexido\n", encoding="utf-8")
        codigo, _ = self.concluir("T1", "--fora-da-posse", "instrução de uso nova")
        self.assertEqual(codigo, 0)
        exercida = self.tarefa("T1")["posse_exercida"]
        self.assertEqual(exercida["fora"], ["README.md"])
        self.assertEqual(exercida["motivo"], "instrução de uso nova")

    def test_motivo_em_branco_nao_libera(self) -> None:
        self.adicionar("T1", "--posse", "src/**")
        rodar("iniciar", "q", "T1")
        Path("README.md").write_text("# mexido\n", encoding="utf-8")
        self.assertEqual(self.concluir("T1", "--fora-da-posse", "  ")[0], 1)

    def test_tarefa_de_leitura_que_escreveu_e_recusada(self) -> None:
        self.adicionar("T1", "--leitura")
        rodar("iniciar", "q", "T1")
        Path("src/app.py").write_text("x = 99\n", encoding="utf-8")
        codigo, saida = self.concluir("T1")
        self.assertEqual(codigo, 1)
        self.assertIn("tarefa de leitura", saida)

    def test_tarefa_de_leitura_que_so_leu_conclui(self) -> None:
        self.adicionar("T1", "--leitura")
        rodar("iniciar", "q", "T1")
        self.assertEqual(self.concluir("T1")[0], 0)

    def test_mudanca_que_entrou_em_commit_tambem_conta(self) -> None:
        self.adicionar("T1", "--posse", "src/**")
        rodar("iniciar", "q", "T1")
        Path("README.md").write_text("# commitado\n", encoding="utf-8")
        git("commit", "-qam", "mexe no README")
        codigo, saida = self.concluir("T1")
        self.assertEqual(codigo, 1)
        self.assertIn("README.md", saida)

    def test_arquivo_ja_sujo_e_intocado_nao_conta(self) -> None:
        Path("README.md").write_text("# sujo antes\n", encoding="utf-8")
        self.adicionar("T1", "--posse", "src/**")
        rodar("iniciar", "q", "T1")
        self.assertEqual(self.concluir("T1")[0], 0)

    def test_arquivo_ja_sujo_e_mexido_de_novo_conta(self) -> None:
        Path("README.md").write_text("# sujo antes\n", encoding="utf-8")
        self.adicionar("T1", "--posse", "src/**")
        rodar("iniciar", "q", "T1")
        Path("README.md").write_text("# sujo depois\n", encoding="utf-8")
        self.assertEqual(self.concluir("T1")[0], 1)

    def test_escrita_de_tarefa_que_trabalhava_junto_nao_e_atribuida(self) -> None:
        self.adicionar("T1", "--posse", "src/**")
        self.adicionar("T2", "--posse", "docs/**")
        rodar("iniciar", "q", "T1")
        rodar("iniciar", "q", "T2")
        Path("docs").mkdir()
        Path("docs/guia.md").write_text("guia\n", encoding="utf-8")
        self.assertEqual(self.concluir("T2")[0], 0)   # T2 conclui antes de T1
        self.assertEqual(self.concluir("T1")[0], 0)   # e o arquivo dela não cai em T1

    def test_escrita_de_tarefa_concluida_antes_do_iniciar_e_atribuida(self) -> None:
        self.adicionar("T2", "--posse", "docs/**")
        rodar("iniciar", "q", "T2")
        self.assertEqual(self.concluir("T2")[0], 0)
        self.adicionar("T1", "--posse", "src/**")
        rodar("iniciar", "q", "T1")
        Path("docs").mkdir()
        Path("docs/depois.md").write_text("tarde\n", encoding="utf-8")
        self.assertEqual(self.concluir("T1")[0], 1)

    def test_a_foto_e_apagada_depois_de_concluir(self) -> None:
        self.adicionar("T1", "--posse", "src/**")
        rodar("iniciar", "q", "T1")
        self.assertTrue(quadro.caminho_da_foto("q", "T1").is_file())
        self.concluir("T1")
        self.assertFalse(quadro.caminho_da_foto("q", "T1").exists())


class Adicionar(ComRepositorio):
    def test_leitura_e_posse_juntas_sao_recusadas(self) -> None:
        self.assertEqual(self.adicionar("T1", "--leitura", "--posse", "src/**"), 1)

    def test_sem_posse_e_sem_leitura_e_recusada(self) -> None:
        self.assertEqual(self.adicionar("T1"), 1)

    def test_tarefa_de_leitura_nao_disputa_posse_com_ninguem(self) -> None:
        self.adicionar("T1", "--posse", "**")
        self.adicionar("T2", "--leitura")
        codigo, saida = rodar("prontas", "q", "--json")
        self.assertEqual(json.loads(saida)["prontas"], ["T1", "T2"])


class Foto(unittest.TestCase):
    """As bordas da foto do checkout: tamanho do arquivo, sujeira demais e repo sem commit."""

    def test_impressao_troca_o_sha_por_tamanho_acima_do_limite(self) -> None:
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(quadro, "LIMITE_IMPRESSAO", 4):
            no_limite, acima = Path(tmp, "a"), Path(tmp, "b")
            no_limite.write_bytes(b"1234")
            acima.write_bytes(b"12345")
            self.assertEqual(len(quadro.impressao(no_limite)), 64)        # sha256
            self.assertTrue(quadro.impressao(acima).startswith("tamanho:5:"))
            self.assertEqual(quadro.impressao(Path(tmp)), "dir")
            self.assertEqual(quadro.impressao(Path(tmp, "nao-existe")), "ausente")

    def test_sujeira_acima_do_limite_nao_tira_foto(self) -> None:
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(quadro, "LIMITE_FOTO", 2):
            dois = b" M a.txt\0?? b.txt\0"
            self.assertEqual(sorted(quadro.arquivos_do_status(dois, Path(tmp))), ["a.txt", "b.txt"])
            self.assertIsNone(quadro.arquivos_do_status(dois + b"?? c.txt\0", Path(tmp)))

    def test_renomeacao_pula_a_origem_e_o_quadro_fica_fora(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bruto = b"R  novo.py\0velho.py\0?? .agents/quadro/q.json\0 M src/x.py\0"
            self.assertEqual(sorted(quadro.arquivos_do_status(bruto, Path(tmp))),
                             ["novo.py", "src/x.py"])

    def test_repositorio_sem_commit_tem_head_nulo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True, capture_output=True)
            Path(tmp, "a.txt").write_text("a\n", encoding="utf-8")
            foto = quadro.foto_do_checkout(Path(tmp))
            self.assertIsNone(foto["head"])
            self.assertEqual(list(foto["arquivos"]), ["a.txt"])


class Mensagens(ComRepositorio):
    def test_concluir_diz_o_que_liberou_e_quando_acabou(self) -> None:
        self.adicionar("T1", "--posse", "src/**")
        self.adicionar("T2", "--posse", "docs/**", "--depende", "T1")
        self.adicionar("T3", "--posse", "lib/**")
        rodar("iniciar", "q", "T1")
        rodar("iniciar", "q", "T3")
        _, saida = self.concluir("T3")
        self.assertIn("nada liberado ainda", saida)
        _, saida = self.concluir("T1")
        self.assertIn("liberou: T2", saida)
        rodar("iniciar", "q", "T2")
        _, saida = self.concluir("T2")
        self.assertIn("quadro completo", saida)


class Iniciar(ComRepositorio):
    def test_recusas(self) -> None:
        self.adicionar("T1", "--posse", "src/**")
        self.adicionar("T2", "--posse", "src/**", "--depende", "T1")
        self.assertEqual(rodar("iniciar", "q", "T9")[0], 1)            # não existe
        codigo, saida = rodar("iniciar", "q", "T2")                     # espera T1
        self.assertEqual(codigo, 1)
        self.assertIn("espera T1", saida)
        self.assertEqual(rodar("iniciar", "q", "T1")[0], 0)
        self.assertEqual(rodar("iniciar", "q", "T1")[0], 1)             # já em progresso
        self.concluir("T1")
        self.assertEqual(rodar("iniciar", "q", "T1")[0], 1)             # já concluída

    def test_nova_onda_so_quando_nada_esta_em_voo(self) -> None:
        self.adicionar("T1", "--posse", "src/**")
        self.adicionar("T2", "--posse", "docs/**")
        rodar("iniciar", "q", "T1")
        rodar("iniciar", "q", "T2")
        self.assertEqual((self.tarefa("T1")["onda"], self.tarefa("T2")["onda"]), (1, 1))

    def test_checkout_de_um_worktree(self) -> None:
        self.adicionar("T1", "--posse", "src/**")
        with tempfile.TemporaryDirectory() as fora:      # fora do repo, e limpo no fim
            wt = Path(fora) / "wt"
            git("worktree", "add", "-q", str(wt), "-b", "wt")
            rodar("iniciar", "q", "T1", "--checkout", str(wt))
            (wt / "README.md").write_text("# no worktree\n", encoding="utf-8")
            codigo, saida = self.concluir("T1")
            git("worktree", "remove", "--force", str(wt))
        self.assertEqual(codigo, 1)
        self.assertIn("README.md", saida)


class Vincular(ComRepositorio):
    def test_tarefa_existente(self) -> None:
        self.adicionar("T1", "--posse", "src/**")
        self.assertEqual(rodar("vincular", "q", "T1")[0], 0)

    def test_tarefa_inexistente(self) -> None:
        self.assertEqual(rodar("vincular", "q", "T9")[0], 1)


class ForaDoGit(unittest.TestCase):
    def test_sem_git_conclui_sem_conferir_e_avisa(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            antes = os.getcwd()
            os.chdir(tmp)
            try:
                rodar("abrir", "q")
                rodar("adicionar", "q", "--id", "T1", "--titulo", "t", "--dono", "lucas",
                      "--posse", "src/**", "--pronto-quando", "ok")
                _, saida = rodar("iniciar", "q", "T1")
                self.assertIn("sem foto", saida)
                codigo, saida = rodar("concluir", "q", "T1", "--evidencia", "e", "--gate-ok")
                self.assertEqual(codigo, 0)
                self.assertIn("não conferida", saida)
            finally:
                os.chdir(antes)


class RegexDaPosse(unittest.TestCase):
    def casa(self, rel: str, padrao: str) -> bool:
        return quadro.cabe_na_posse(rel, [padrao])

    def test_dois_asteriscos_atravessam_pastas(self) -> None:
        self.assertTrue(self.casa("src/a/b/c.py", "src/**"))
        self.assertFalse(self.casa("srcx/a.py", "src/**"))

    def test_um_asterisco_nao_atravessa_pasta(self) -> None:
        self.assertTrue(self.casa("src/a.py", "src/*.py"))
        self.assertFalse(self.casa("src/a/b.py", "src/*.py"))

    def test_padrao_de_nome_em_qualquer_profundidade_inclusive_a_raiz(self) -> None:
        self.assertTrue(self.casa("a.test.ts", "**/*.test.*"))
        self.assertTrue(self.casa("x/y/a.test.ts", "**/*.test.*"))
        self.assertFalse(self.casa("x/y/a.ts", "**/*.test.*"))

    def test_pasta_nomeada_cobre_o_conteudo(self) -> None:
        self.assertTrue(self.casa("docs/specs/SPEC-001.md", "docs/specs"))
        self.assertTrue(self.casa("docs/specs/SPEC-001.md", "./docs/specs/"))
        self.assertFalse(self.casa("docs/specsx.md", "docs/specs"))

    def test_classe_negada(self) -> None:
        self.assertTrue(self.casa("b.py", "[!a]*.py"))
        self.assertFalse(self.casa("a.py", "[!a]*.py"))


class Contrato(unittest.TestCase):
    def test_versao_e_regra_da_posse_exercida(self) -> None:
        decl = quadro.contrato_publico()
        self.assertEqual(decl["versao"], "1.2")
        self.assertTrue(any("--fora-da-posse" in r for r in decl["regras"]))


if __name__ == "__main__":
    unittest.main()
