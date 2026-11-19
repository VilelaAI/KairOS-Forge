"""Investigar antes de corrigir (ADR-0060): o laço que reproduz, a ficha e a marca de depuração.

Tudo num git de verdade: a base tem o defeito (média de lista vazia divide por zero), a
branch traz a correção e o teste de regressão no arquivo de teste que já existia.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import prova  # noqa: E402

QUEM = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "commit.gpgsign",
        "GIT_CONFIG_VALUE_0": "false"}
MARCA = "forge-" + "depura-a4f2"   # montada aqui: o próprio teste não é log esquecido
COM_DEFEITO = "def media(xs):\n    return sum(xs) / len(xs)\n"
CORRIGIDO = "def media(xs):\n    if not xs:\n        return 0\n    return sum(xs) / len(xs)\n"
TESTE_BASE = ("import unittest\nfrom conta import media\n\n\nclass T(unittest.TestCase):\n"
              "    def test_media(self):\n        self.assertEqual(media([2, 4]), 3)\n")
REGRESSAO = TESTE_BASE + "\n    def test_vazia(self):\n        self.assertEqual(media([]), 0)\n"
LACO = f"{sys.executable} -B -m unittest test_conta"
FICHA = """# INV — a média do relatório quebra com o mês sem vendas

- **Sintoma:** o relatório de janeiro sai com ZeroDivisionError
- **Reprodução:** `{laco}`
- **Sintoma na saída:** `ZeroDivisionError`

## Hipóteses

| # | Hipótese | Se fosse ela, veríamos | Como testei | Resultado |
|---|---|---|---|---|
| 1 | o CSV de janeiro vem vazio | a leitura sem linhas | contei as linhas | descartada |
| 2 | a média não trata a lista vazia | erro com `[]` | `media([])` | confirmada |

## Causa

`conta.py:2` divide pelo tamanho da lista sem tratar a lista vazia.

## Prova

Com a guarda o laço passa; sem ela, volta o ZeroDivisionError.

## Trava

`test_conta.py::test_vazia` falha na base e passa agora.
"""


class Repo(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-investigar-")
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self.git("init", "-q", "-b", "main")
        self.escrever({"conta.py": COM_DEFEITO, "test_conta.py": TESTE_BASE})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.git("checkout", "-q", "-b", "fix/media")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.raiz, env={**os.environ, **QUEM},
                              check=True, capture_output=True, text=True).stdout

    def escrever(self, arquivos: dict[str, str]) -> None:
        for rel, texto in arquivos.items():
            (self.raiz / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.raiz / rel).write_text(texto, encoding="utf-8")

    def corrigir(self, codigo: str = CORRIGIDO) -> None:
        self.escrever({"conta.py": codigo, "test_conta.py": REGRESSAO})

    def reproduzir(self, sintoma: str | None = "ZeroDivisionError", **kw) -> dict:
        return prova.reproduzir(self.raiz, "main", kw.pop("comando", LACO), sintoma,
                                kw.pop("tempo", 60), **kw)


class OLacoNosDoisLados(Repo):
    def test_falha_na_base_com_o_sintoma_e_passa_agora(self) -> None:
        self.corrigir()
        r = self.reproduzir()
        self.assertEqual(r["veredicto"], "reproduz_e_corrige")
        self.assertEqual(r["copiados"], ["test_conta.py"])   # o teste mudado, não só o novo
        self.assertTrue(any("ZeroDivisionError" in l for l in r["antes"]))

    def test_o_laco_que_passa_na_base_nao_reproduz(self) -> None:
        self.corrigir()
        r = self.reproduzir(comando=f"{sys.executable} -c 'import conta'")
        self.assertEqual(r["veredicto"], "nao_reproduz")

    def test_outro_erro_na_base_e_sintoma_diferente(self) -> None:
        self.corrigir()
        self.assertEqual(self.reproduzir("KeyError")["veredicto"], "sintoma_diferente")

    def test_sem_sintoma_qualquer_falha_reproduz(self) -> None:
        self.corrigir()
        self.assertEqual(self.reproduzir(None)["veredicto"], "reproduz_e_corrige")

    def test_a_correcao_que_nao_corrige(self) -> None:
        self.corrigir(COM_DEFEITO)
        self.assertEqual(self.reproduzir()["veredicto"], "nao_corrige")

    def test_o_laco_que_estoura_o_tempo(self) -> None:
        self.corrigir()
        r = self.reproduzir(comando=f"{sys.executable} -c 'import time; time.sleep(5)'", tempo=1)
        self.assertEqual(r["veredicto"], "nao_executado")

    def test_estourar_o_tempo_so_depois(self) -> None:
        self.assertEqual(prova.veredicto_da_reproducao("falhou", "nao_executado"),
                         "nao_executado")

    def test_nenhum_worktree_sobra(self) -> None:
        self.corrigir()
        self.reproduzir()
        self.assertEqual(len(self.git("worktree", "list").splitlines()), 1)

    def test_a_pasta_que_ja_sumiu_nao_derruba_a_limpeza(self) -> None:
        """A limpeza do worktree descartável é de melhor esforço: a pasta temporária que já
        sumiu quando ela roda não vira exceção para quem chamou, e o worktree não sobra."""
        import shutil
        with prova.arvore_na_base(self.raiz, "main") as worktree:
            self.assertIsNotNone(worktree)
            shutil.rmtree(worktree.parent)
        self.assertEqual(len(self.git("worktree", "list").splitlines()), 1)

    def test_o_teste_novo_em_pasta_que_a_base_nao_tem(self) -> None:
        """O teste novo numa pasta de dois níveis que a base não tem também vai para a base:
        as pastas que faltam são criadas, e o laço mostra o defeito lá."""
        self.escrever({"conta.py": CORRIGIDO, "testes/regressao/test_vazia.py": REGRESSAO})
        r = self.reproduzir(comando=f"{sys.executable} -B -m unittest discover -s testes/regressao")
        self.assertEqual(r["copiados"], ["testes/regressao/test_vazia.py"])
        self.assertEqual(r["veredicto"], "reproduz_e_corrige")

    def test_antes_do_conserto_so_aqui(self) -> None:
        self.escrever({"test_conta.py": REGRESSAO})
        r = self.reproduzir(antes=True)
        self.assertEqual(r["veredicto"], "reproduz")
        self.assertNotIn("base", r)
        self.corrigir()
        self.assertEqual(self.reproduzir(antes=True)["veredicto"], "nao_reproduz")
        self.assertEqual(self.reproduzir("KeyError", antes=True)["veredicto"], "nao_reproduz")

    def test_erros_de_uso(self) -> None:
        self.assertIn("diga o laço", self.reproduzir(comando=None)["erro"])
        self.assertIn("regex válida", self.reproduzir("(")["erro"])
        r = prova.reproduzir(self.raiz, "nao-existe", LACO, None, 60)
        self.assertIn("(nao-existe)", r["erro"])

    def test_sem_worktree_e_erro(self) -> None:
        with prova.arvore_na_base(self.raiz, "nao-e-um-commit") as worktree:
            self.assertIsNone(worktree)

        @contextmanager
        def sem_worktree(*_):
            yield None
        with mock.patch.object(prova, "arvore_na_base", sem_worktree):
            r = prova.reproduzir(self.raiz, "main", LACO, None, 60)
        self.assertIn("worktree", r["erro"])

    def test_o_que_nao_copia_fica_de_fora(self) -> None:
        self.assertEqual(prova._copiar(self.raiz, self.raiz / "x", ["nao-existe.py"]), [])


class OQueARevisaoAchou(Repo):
    """Os furos que a revisão adversarial achou no laço (ADR-0060), um teste para cada."""

    def test_apagar_o_teste_que_falha_nao_e_conserto(self) -> None:
        self.escrever({"test_vazia.py": "import unittest\nfrom conta import media\n\n\n"
                                        "class T(unittest.TestCase):\n    def test_v(self):\n"
                                        "        self.assertEqual(media([]), 0)\n"})
        self.git("add", "-A")
        self.git("commit", "-qm", "teste que falha")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "fix/media")
        self.git("checkout", "-q", "fix/media")
        laco = f"{sys.executable} -B -m unittest discover -p 'test_*.py'"
        self.git("rm", "-q", "test_vazia.py")
        self.assertEqual(self.reproduzir(comando=laco)["veredicto"], "nao_reproduz")
        self.git("reset", "-q", "--hard")
        self.git("mv", "test_vazia.py", "test_media_extra.py")
        (self.raiz / "test_media_extra.py").write_text("x = 1\n", encoding="utf-8")
        self.assertEqual(self.reproduzir(comando=laco)["veredicto"], "nao_reproduz")

    @unittest.skipUnless(sys.platform.startswith("linux"),
                         "só o Linux guarda nome de arquivo fora do UTF-8")
    def test_apagar_teste_de_nome_fora_do_utf8_nao_derruba(self) -> None:
        """O teste apagado com nome fora do UTF-8 (Latin-1, de um Windows antigo) não derruba a
        reprodução: o git o devolve com caractere trocado, e o que não se acha para tirar da
        base não vira exceção."""
        velho = os.fsdecode(b"test_relat\xf3rio.py")
        (self.raiz / velho).write_text("import unittest\n\n\nclass T(unittest.TestCase):\n"
                                       "    def test_v(self):\n        pass\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "teste velho")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "fix/media")
        self.git("checkout", "-q", "fix/media")
        self.git("rm", "-q", velho)
        self.corrigir()
        self.assertEqual(self.reproduzir()["veredicto"], "reproduz_e_corrige")

    def test_o_laco_que_nao_existe_na_base_nao_e_reproducao(self) -> None:
        self.corrigir()
        r = self.reproduzir(None, comando="./nao-existe.sh")   # 127: o comando não existe ali
        self.assertEqual(r["veredicto"], "nao_executado")

    def test_saida_que_nao_e_utf8_nao_derruba(self) -> None:
        self.corrigir()
        laco = f"{sys.executable} -c 'import sys; sys.stdout.buffer.write(bytes([0xf3])); sys.exit(1)'"
        self.assertEqual(self.reproduzir(None, comando=laco, antes=True)["veredicto"], "reproduz")

    def test_o_tempo_estourado_mata_o_grupo(self) -> None:
        import time
        inicio = time.monotonic()
        r = prova._rodar("sleep 30; true", self.raiz, 1)
        self.assertIsNone(r["exit"])
        self.assertLess(time.monotonic() - inicio, 10)

    def test_marca_de_id_curto_prefixo_do_diff_e_acento(self) -> None:
        self.escrever({"curta.py": f"print('[{MARCA[:-4]}7]')\n",
                       "relatório.py": f"# {MARCA}\n",
                       ".agents/execucoes/s.jsonl": f'{{"cmd": "sed /{MARCA}/d"}}\n'})
        self.git("config", "diff.mnemonicPrefix", "true")
        self.git("config", "diff.noprefix", "true")
        achadas = sorted(m["arquivo"] for m in prova.marcas(self.raiz, "main")["marcas"])
        self.assertEqual(achadas, ["curta.py", "relatório.py"])


class AMarcaDeDepuracao(Repo):
    def test_a_marca_que_sobrou_no_codigo(self) -> None:
        self.escrever({"conta.py": CORRIGIDO + f"print('[{MARCA}]', 1)\n",
                       "novo.py": f"# {MARCA} aqui\n",
                       "INV.md": f"marca usada: {MARCA}\n"})
        r = prova.marcas(self.raiz, "main")
        self.assertEqual(sorted((m["arquivo"], m["linha"]) for m in r["marcas"]),
                         [("conta.py", 5), ("novo.py", 1)])

    def test_a_linha_removida_nao_conta(self) -> None:
        self.escrever({"conta.py": COM_DEFEITO + f"# {MARCA}\n"})
        self.git("commit", "-qam", "com a marca")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "fix/media")
        self.git("checkout", "-q", "fix/media")
        self.escrever({"conta.py": COM_DEFEITO})
        self.assertEqual(prova.marcas(self.raiz, "main")["marcas"], [])

    def test_sem_base(self) -> None:
        self.assertIn("(nao-existe)", prova.marcas(self.raiz, "nao-existe")["erro"])

    def test_o_que_o_gitattributes_marca_como_de_fora(self) -> None:
        self.escrever({".gitattributes": "fixtures/** linguist-vendored=true\n"
                                         "espelho/** linguist-generated=true\n",
                       "fixtures/errada.py": f"print('[{MARCA}]')\n",
                       "espelho/conta.py": f"print('[{MARCA}]')\n",
                       "conta.py": CORRIGIDO + f"print('[{MARCA}]')\n"})
        self.assertEqual([m["arquivo"] for m in prova.marcas(self.raiz, "main")["marcas"]],
                         ["conta.py"])


class AFicha(Repo):
    def ficha(self, texto: str = FICHA) -> dict:
        self.escrever({"docs/investigacoes/INV-media.md": texto.format(laco=LACO)})
        return prova.investigacao(self.raiz, "main",
                                  str(self.raiz / "docs/investigacoes/INV-media.md"), 60)

    def test_a_ficha_pronta(self) -> None:
        self.corrigir()
        r = self.ficha()
        self.assertEqual((r["veredicto"], r["problemas"]), ("pronta", []))
        self.assertEqual((r["confirmadas"], r["descartadas"], r["abertas"]), (1, 1, 0))
        self.assertEqual(r["reproducao"]["veredicto"], "reproduz_e_corrige")

    def test_sem_causa_e_sem_correcao(self) -> None:
        r = self.ficha(FICHA.replace("`conta.py:2` divide pelo tamanho da lista sem tratar a "
                                     "lista vazia.", "<a causa>"))
        self.assertEqual(r["veredicto"], "incompleta")
        self.assertTrue(any("`## Causa`" in p for p in r["problemas"]))
        self.assertTrue(any("`nao_reproduz`" in p for p in r["problemas"]))

    def test_tres_descartadas_e_nenhuma_confirmada(self) -> None:
        linhas = "".join(f"| {i} | h{i} | x | y | descartada |\n" for i in (3, 4))
        texto = FICHA.replace("| confirmada |", "| descartada |").replace(
            "\n## Causa", linhas + "\n## Causa")
        r = self.ficha(texto)
        self.assertEqual((r["veredicto"], r["descartadas"]), ("pare_e_pergunte", 4))
        self.assertNotIn("reproducao", r)

    def test_duas_descartadas_ainda_nao_param(self) -> None:
        self.corrigir()
        r = self.ficha(FICHA.replace("| confirmada |", "| descartada |"))
        self.assertEqual(r["veredicto"], "incompleta")
        self.assertIn("nenhuma hipótese confirmada", r["problemas"])

    def test_a_marca_que_sobrou_reprova(self) -> None:
        self.corrigir(CORRIGIDO + f"# [{MARCA}]\n")
        r = self.ficha()
        self.assertEqual(r["veredicto"], "incompleta")
        self.assertEqual(len(r["marcas"]), 1)

    def test_sem_reproducao_nao_roda(self) -> None:
        r = self.ficha(FICHA.replace("- **Reprodução:** `{laco}`\n", ""))
        self.assertEqual(r["reproducao"], {"veredicto": "nao_executado"})
        self.assertIn("sem **Reprodução:** com o comando entre crases", r["problemas"])

    def test_erro_da_reproducao_entra_nos_problemas(self) -> None:
        self.corrigir()
        r = self.ficha(FICHA.replace("`ZeroDivisionError`", "`(`"))
        self.assertTrue(any("regex válida" in p for p in r["problemas"]))

    def test_ficha_que_nao_existe(self) -> None:
        self.assertIn("não li a ficha", prova.investigacao(self.raiz, "main", "nada.md", 60)["erro"])
        self.assertIn("diga qual ficha", prova.investigacao(self.raiz, "main", None, 60)["erro"])


class OLeitorDaFicha(unittest.TestCase):
    def test_campos_secoes_e_hipoteses(self) -> None:
        f = prova.ler_ficha(FICHA.format(laco="make teste"))
        self.assertEqual((f["comando"], f["sintoma"]), ("make teste", "ZeroDivisionError"))
        self.assertEqual(f["problemas"], [])

    def test_ficha_vazia(self) -> None:
        f = prova.ler_ficha("# INV\n")
        self.assertEqual(len(f["problemas"]), 7)
        self.assertIsNone(f["comando"])

    def test_titulo_dentro_de_bloco_de_codigo_nao_abre_secao(self) -> None:
        texto = "## Causa\n\n```\n## Prova\n```\nfim\n"
        self.assertEqual(set(prova.secoes_md(texto)), {"causa"})

    def test_resultado_da_hipotese(self) -> None:
        self.assertEqual([prova.resultado_da_hipotese(c) for c in
                          ("Descartada", "confirmada (liga e desliga)", "em teste", "",
                           "**confirmada**", "✅ confirmada", "~~descartada~~")],
                         ["descartada", "confirmada", "aberta", "aberta",
                          "confirmada", "confirmada", "descartada"])

    def test_tabela_pela_posicao_e_o_modelo_sem_preencher(self) -> None:
        tabela = "| A | B |\n|:-:|---|\n| 1 | x |\n|  | y |\n| - | z |\n"
        self.assertEqual(prova.linhas_da_tabela(tabela), [["1", "x"], ["", "y"], ["-", "z"]])
        modelo = FICHA.replace("| 1 | o CSV de janeiro vem vazio |", "| 1 | <causa possível> |") \
                      .replace("| 2 | a média não trata a lista vazia |", "| 2 | <causa possível> |")
        f = prova.ler_ficha(modelo.format(laco="x"))
        self.assertEqual((f["confirmadas"], f["descartadas"]), (0, 0))
        self.assertIn("sem a tabela de `## Hipóteses`", f["problemas"])

    def test_linha_de_uma_celula_so_fica_de_fora_sem_derrubar(self) -> None:
        """A linha começada e não escrita (`| 3 |`, uma célula só) não é hipótese nem derruba a leitura."""
        texto = FICHA.replace("| confirmada |\n", "| confirmada |\n| 3 |\n", 1)
        self.assertEqual(prova.linhas_da_tabela(prova.secoes_md(texto)["hipóteses"])[-1], ["3"])
        f = prova.ler_ficha(texto.format(laco="make teste"))
        self.assertEqual((f["descartadas"], f["confirmadas"], f["abertas"]), (1, 1, 0))
        self.assertEqual(f["problemas"], [])

    def test_preenchido(self) -> None:
        self.assertFalse(prova._preenchido("<a causa>"))
        self.assertFalse(prova._preenchido("curta", 20))
        self.assertTrue(prova._preenchido("x" * 20, 20))
        self.assertFalse(prova._preenchido(None))


class AImpressao(Repo):
    def imprimir(self, funcao, r: dict) -> str:
        saida = io.StringIO()
        with redirect_stdout(saida):
            funcao(r)
        return saida.getvalue()

    def test_reproducao(self) -> None:
        self.corrigir()
        saida = self.imprimir(prova.imprimir_reproduzir, self.reproduzir())
        self.assertIn("falha na base e passa agora", saida)
        self.assertIn("testes do diff copiados para a base: test_conta.py", saida)
        self.assertIn("antes  │", saida)
        saida = self.imprimir(prova.imprimir_reproduzir, self.reproduzir(None, antes=True))
        self.assertIn("antes do conserto", saida)
        self.assertIn("sem --sintoma: qualquer saída diferente de 0 conta", saida)
        self.assertIn("🚫", self.imprimir(prova.imprimir_reproduzir, {"erro": "x"}))

    def test_marcas_e_ficha(self) -> None:
        self.escrever({"novo.py": f"# {MARCA}\n"})
        saida = self.imprimir(prova.imprimir_marcas, prova.marcas(self.raiz, "main"))
        self.assertIn("novo.py:1", saida)
        self.assertIn("sai antes de dizer que terminou", saida)
        self.assertIn("🚫", self.imprimir(prova.imprimir_marcas, {"erro": "x"}))
        r = {"ficha": "INV.md", "confirmadas": 0, "descartadas": 3, "abertas": 0,
             "veredicto": "pare_e_pergunte"}
        self.assertIn("não avança sem informação nova", self.imprimir(prova.imprimir_investigacao, r))
        r = {**r, "veredicto": "incompleta", "problemas": ["sem causa"],
             "reproducao": {"veredicto": "nao_corrige"}}
        saida = self.imprimir(prova.imprimir_investigacao, r)
        self.assertIn("✗ sem causa", saida)
        self.assertIn("ainda falha depois da correção", saida)
        self.assertIn("🚫", self.imprimir(prova.imprimir_investigacao, {"erro": "x"}))


class PeloComando(Repo):
    def rodar(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", str(RAIZ / "prova.py"), *args],
                              cwd=self.raiz, capture_output=True, text=True,
                              env={**os.environ, **QUEM}, timeout=120)

    def test_saidas(self) -> None:
        self.corrigir()
        r = self.rodar("reproduzir", "--comando", LACO, "--sintoma", "ZeroDivisionError",
                       "--base", "main")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = self.rodar("reproduzir", "--comando", LACO, "--antes", "--json")
        self.assertEqual((r.returncode, json.loads(r.stdout)["veredicto"]), (1, "nao_reproduz"))
        self.escrever({"docs/investigacoes/INV-media.md": FICHA.format(laco=LACO)})
        r = self.rodar("investigacao", "docs/investigacoes/INV-media.md", "--base", "main")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("ficha pronta", r.stdout)
        self.assertEqual(self.rodar("marcas", "--base", "main").returncode, 0)
        self.escrever({"novo.py": f"# {MARCA}\n"})
        self.assertEqual(self.rodar("marcas", "--base", "main").returncode, 1)

    def test_pare_e_pergunte_sai_2(self) -> None:
        linhas = "".join(f"| {i} | h | x | y | descartada |\n" for i in (1, 2, 3))
        self.escrever({"INV.md": "# INV\n\n## Hipóteses\n\n| # | H | V | T | R |\n|---|---|---|---|---|\n"
                       + linhas})
        r = self.rodar("investigacao", "INV.md", "--base", "main")
        self.assertEqual(r.returncode, 2, r.stdout)


if __name__ == "__main__":
    unittest.main()
