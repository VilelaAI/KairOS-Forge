"""Prova pré-patch (ADR-0039): o teste novo que nem carrega na base só prova quando o que
falta é o que o diff acrescenta.

O teste de um símbolo novo falha na base com ImportError porque o símbolo ainda não existe:
é prova, o comportamento não existia. A dependência que não está instalada, o teste com erro
de sintaxe, o auxiliar de teste ou o `conftest.py` que ficaram para trás também não carregam,
e nada disso vem do diff: é `erro_na_base`, não `falhou_na_base`.

As saídas de exemplo foram copiadas de pytest 9.2, vitest 3.2.4, jest 29.7 e go 1.24, com o
caminho do worktree trocado por `{wt}`. O resto roda num git de verdade, com Python e, quando
houver, Go.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import io
import json
import os
import shutil
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
CALC = "def soma(a, b):\n    return a + b\n"
APOIO = "def um():\n    return 1\n"


def teste(cabeca: str, corpo: str = "self.assertTrue(True)") -> str:
    return (f"import unittest\n{cabeca}\n\n\nclass T(unittest.TestCase):\n"
            f"    def test_a(self):\n        {corpo}\n")


class Repo(unittest.TestCase):
    """Base com `app/calc.py` e `tests/apoio.py`; a branch `feat` traz o diff."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-pre-patch-")
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name).resolve()
        self.git("init", "-q", "-b", "main")
        self.escrever({"app/__init__.py": "", "app/calc.py": CALC, "tests/__init__.py": "",
                       "tests/apoio.py": APOIO})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.git("checkout", "-q", "-b", "feat")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.raiz, env={**os.environ, **QUEM},
                              check=True, capture_output=True, text=True).stdout

    def escrever(self, arquivos: dict[str, str]) -> None:
        for rel, texto in arquivos.items():
            (self.raiz / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.raiz / rel).write_text(texto, encoding="utf-8")

    def pre_patch(self, comando: str | None = None, pytest: bool = False) -> dict:
        # Sem pytest, o comando deduzido é o unittest: o mesmo aqui e no CI, que não tem pytest.
        with mock.patch.object(prova, "_tem_modulo", return_value=pytest):
            r = prova.pre_patch(self.raiz, "main", comando, 60)
        self.assertNotIn("erro", r)
        self.assertEqual(self.git("worktree", "list").count("\n"), 1)   # o descartável sumiu
        return r

    def item(self, r: dict, arquivo: str) -> dict:
        return next(t for t in r["testes"] if t["arquivo"] == arquivo)


class OQueFaltaEDoDiff(Repo):
    """O que o diff acrescenta e a base não tem: o teste não carrega lá, e isso é prova."""

    def test_modulo_novo_do_diff(self) -> None:
        self.escrever({"app/novo.py": "def dobro(x):\n    return 2 * x\n",
                       "tests/test_novo.py": teste("from app.novo import dobro",
                                                   "self.assertEqual(dobro(2), 4)")})
        t = self.item(self.pre_patch(), "tests/test_novo.py")
        self.assertEqual(t["veredicto"], "falhou_na_base")
        self.assertIn("app.novo", t["motivo"])

    def test_nome_novo_num_modulo_que_ja_existia(self) -> None:
        self.escrever({"app/calc.py": CALC + "\n\ndef dobro(x):\n    return 2 * x\n",
                       "tests/test_dobro.py": teste("from app.calc import dobro",
                                                    "self.assertEqual(dobro(2), 4)")})
        t = self.item(self.pre_patch(), "tests/test_dobro.py")
        self.assertEqual(t["veredicto"], "falhou_na_base")
        self.assertIn("dobro", t["motivo"])

    def test_submodulo_novo_importado_pelo_pacote(self) -> None:
        # `from app import extenso`: o nome que falta é o módulo novo, que não cita a si mesmo.
        self.escrever({"app/extenso.py": "def escrever(n):\n    return 'dois'\n",
                       "tests/test_extenso.py": teste("from app import extenso",
                                                      "self.assertEqual(extenso.escrever(2), 'dois')")})
        self.assertEqual(self.item(self.pre_patch(), "tests/test_extenso.py")["veredicto"],
                         "falhou_na_base")

    def test_comportamento_que_a_base_nao_tem_continua_falha_comum(self) -> None:
        self.escrever({"app/calc.py": "def soma(a, b):\n    return (a or 0) + (b or 0)\n",
                       "tests/test_nulo.py": teste("from app.calc import soma",
                                                   "self.assertEqual(soma(None, 2), 2)")})
        t = self.item(self.pre_patch(), "tests/test_nulo.py")
        self.assertEqual(t["veredicto"], "falhou_na_base")
        self.assertEqual(t["motivo"], "exit 1 na base")


class OQueFaltaNaoEDoDiff(Repo):
    """O teste não carrega na base por razão que o diff não explica: não prova a mudança."""

    def test_dependencia_que_nao_esta_instalada(self) -> None:
        self.escrever({"tests/test_dep.py": teste("import pacote_que_ninguem_instalou")})
        t = self.item(self.pre_patch(), "tests/test_dep.py")
        self.assertEqual(t["veredicto"], "erro_na_base")
        self.assertIn("pacote_que_ninguem_instalou", t["motivo"])
        self.assertIn("não prova a mudança", t["motivo"])

    def test_nome_que_o_diff_nao_acrescenta(self) -> None:
        self.escrever({"app/calc.py": CALC + "\n\ndef dobro(x):\n    return 2 * x\n",
                       "tests/test_mult.py": teste("from app.calc import multiplica")})
        self.assertEqual(self.item(self.pre_patch(), "tests/test_mult.py")["veredicto"],
                         "erro_na_base")

    def test_erro_de_sintaxe_no_teste(self) -> None:
        self.escrever({"app/calc.py": CALC + "\n\ndef dobro(x):\n    return 2 * x\n",
                       "tests/test_quebrado.py": teste("from app.calc import dobro",
                                                       "x = (")})
        t = self.item(self.pre_patch(), "tests/test_quebrado.py")
        self.assertEqual(t["veredicto"], "erro_na_base")
        self.assertIn("tests/test_quebrado.py", t["motivo"])


GERADOR = ("def validar(codigo):\n    return True\n\n\ndef gerar():\n    return 'x = ('\n\n\n"
           "def mensagem():\n    return ''\n")
GERADOR_CORRIGIDO = ("import ast\n\n\ndef validar(codigo):\n    ast.parse(codigo)\n    return True\n\n\n"
                     "def gerar():\n    return 'x = ()'\n\n\n"
                     "def mensagem():\n    return \"instale: No module named 'pandas'\"\n")


class FalhaComumQueCitaUmaFalta(Repo):
    """O teste carregou e falhou na asserção, e a mensagem só cita o texto de uma falta: a base
    não tem o comportamento, e isso é prova, com o unittest e com o pytest."""

    def runners(self) -> list[bool]:
        return [False] + ([True] if prova._tem_modulo("pytest") else [])

    def veredictos(self, rel: str, cabeca: str, corpo: str) -> None:
        self.escrever({"app/gerador.py": GERADOR})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "gerador na base")
        self.git("branch", "-f", "main")
        self.escrever({"app/gerador.py": GERADOR_CORRIGIDO, rel: teste(cabeca, corpo)})
        for pytest in self.runners():
            with self.subTest(pytest=pytest):
                t = self.item(self.pre_patch(pytest=pytest), rel)
                self.assertEqual((t["veredicto"], t["motivo"]), ("falhou_na_base", "exit 1 na base"))

    def test_teste_que_espera_syntaxerror(self) -> None:
        self.veredictos("tests/test_valida.py", "from app.gerador import validar",
                        "with self.assertRaises(SyntaxError):\n            validar('x = (')")

    def test_codigo_gerado_que_nao_compila_na_base(self) -> None:
        self.veredictos("tests/test_gera.py", "import ast\nfrom app.gerador import gerar",
                        "ast.parse(gerar())")

    def test_mensagem_que_cita_o_modulo_que_falta(self) -> None:
        self.veredictos("tests/test_msg.py", "from app.gerador import mensagem",
                        "self.assertIn(\"No module named 'pandas'\", mensagem())")


class SuporteDeTesteVaiJunto(Repo):
    """O auxiliar e o `conftest.py` do diff vão para a base antes de rodar qualquer teste."""

    def test_auxiliar_novo_que_vem_depois_na_ordem(self) -> None:
        # `tests/zz_apoio.py` vem depois de `tests/test_a.py`: copiado um a um, não estaria lá.
        self.escrever({"tests/zz_apoio.py": "def quatro():\n    return 4\n",
                       "tests/test_a.py": teste("from app.calc import soma\n"
                                                "from tests.zz_apoio import quatro",
                                                "self.assertEqual(soma(2, 2), quatro())")})
        t = self.item(self.pre_patch(), "tests/test_a.py")
        self.assertEqual(t["veredicto"], "passou_na_base")   # o teste não prova nada do diff

    def test_auxiliar_que_ja_existia_e_mudou(self) -> None:
        self.escrever({"tests/apoio.py": APOIO + "\n\ndef dois():\n    return 2\n",
                       "tests/test_b.py": teste("from app.calc import soma\n"
                                                "from tests.apoio import dois",
                                                "self.assertEqual(soma(1, 1), dois())")})
        self.assertEqual(self.item(self.pre_patch(), "tests/test_b.py")["veredicto"],
                         "passou_na_base")

    def test_conftest_novo_e_mudado_entram_no_que_vai_para_a_base(self) -> None:
        self.escrever({"tests/conftest.py": "X = 1\n"})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "conftest na base")
        self.git("branch", "-f", "main")
        self.escrever({"conftest.py": "Y = 2\n", "tests/conftest.py": "X = 2\n",
                       "tests/test_c.py": teste(""), "app/novo.py": "Z = 3\n",
                       "calc/novo_test.go": "package calc\n"})
        ponto = prova.ponto_de_partida(self.raiz, "main")
        # o `_test.go` fica de fora: entra na base só na vez dele
        self.assertEqual(prova.suporte_do_diff(self.raiz, ponto),
                         ["conftest.py", "tests/conftest.py", "tests/test_c.py"])

    @unittest.skipUnless(prova._tem_modulo("pytest"), "sem pytest neste Python")
    def test_fixture_do_conftest_novo_no_pytest(self) -> None:
        self.escrever({"conftest.py": "import pytest\n\n\n@pytest.fixture\ndef dois():\n"
                                      "    return 2\n",
                       "tests/test_fx.py": "from app.calc import soma\n\n\n"
                                           "def test_a(dois):\n    assert soma(dois, 2) == 4\n"})
        self.assertEqual(self.item(self.pre_patch(pytest=True), "tests/test_fx.py")["veredicto"],
                         "passou_na_base")


# Um pytest mínimo para o CI, que não tem pytest: carrega os `conftest.py` da raiz até a pasta
# do teste, resolve as fixtures pelo nome e imprime o que o pytest imprime quando um conftest
# não carrega (`ImportError while loading conftest`, com a linha `E   ModuleNotFoundError`).
FALSO_PYTEST = """import inspect, sys, types
from pathlib import Path
pytest = types.ModuleType("pytest"); pytest.fixture = lambda f: f; sys.modules["pytest"] = pytest
raiz, arquivo = Path.cwd().resolve(), Path(sys.argv[1]).resolve()
sys.path.insert(0, str(raiz))
fixtures = {}
for pasta in [raiz, *[p for p in reversed(arquivo.parents) if raiz in p.parents]]:
    conftest = pasta / "conftest.py"
    if conftest.is_file():
        ns = {}
        try:
            exec(compile(conftest.read_text(), str(conftest), "exec"), ns)
        except Exception as e:
            print(f"ImportError while loading conftest '{conftest}'.")
            print(f"E   {type(e).__name__}: {e}")
            sys.exit(4)
        fixtures.update({k: v for k, v in ns.items() if inspect.isfunction(v)})
ns = {}
exec(compile(arquivo.read_text(), str(arquivo), "exec"), ns)
falhou = False
for nome, f in ns.items():
    if not (nome.startswith("test_") and inspect.isfunction(f)):
        continue
    faltam = [p for p in inspect.signature(f).parameters if p not in fixtures]
    if faltam:
        print(f"E       fixture '{faltam[0]}' not found"); falhou = True; continue
    try:
        f(*[fixtures[p]() for p in inspect.signature(f).parameters])
    except AssertionError:
        print(f"FAILED {nome}"); falhou = True
sys.exit(1 if falhou else 0)
"""


class ConftestQueNaoCarregaNaBase(Repo):
    """O conftest do diff que importa código novo não carrega na base. O teste novo que não
    depende dele não pode virar prova só por isso; o que usa a fixture dele, sim."""

    def setUp(self) -> None:
        super().setUp()
        pasta = tempfile.TemporaryDirectory(prefix="kairos-forge-falso-pytest-")
        self.addCleanup(pasta.cleanup)
        self.falso = Path(pasta.name) / "falso_pytest.py"
        self.falso.write_text(FALSO_PYTEST, encoding="utf-8")

    def julgar(self, arquivos: dict[str, str], teste: str) -> dict:
        self.escrever(arquivos)
        return self.item(self.pre_patch(f"{sys.executable} {self.falso} {{arquivo}}"), teste)

    def test_teste_que_nao_usa_o_conftest_mudado_nao_prova(self) -> None:
        self.escrever({"tests/conftest.py": "X = 1\n"})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "conftest na base")
        self.git("branch", "-f", "main")
        t = self.julgar({"app/novo.py": "def tres():\n    return 3\n",
                         "tests/conftest.py": "from app.novo import tres\nX = 1\n",
                         "tests/test_soma.py": "from app.calc import soma\n\n\n"
                                               "def test_soma():\n    assert soma(1, 1) == 2\n"},
                        "tests/test_soma.py")
        self.assertEqual(t["veredicto"], "passou_na_base", t["motivo"])
        self.assertIn("conftest.py do diff sai da base", t["motivo"])
        # O conftest volta inteiro para o teste seguinte: o worktree não fica sem ele.
        self.assertEqual((self.raiz / "tests/conftest.py").read_text(encoding="utf-8"),
                         "from app.novo import tres\nX = 1\n")

    def test_teste_que_usa_a_fixture_do_conftest_novo_prova(self) -> None:
        t = self.julgar({"app/novo.py": "def tres():\n    return 3\n",
                         "conftest.py": "import pytest\nfrom app.novo import tres\n\n\n"
                                        "@pytest.fixture\ndef valor():\n    return tres()\n",
                         "tests/test_valor.py": "def test_valor(valor):\n    assert valor == 3\n"},
                        "tests/test_valor.py")
        self.assertEqual(t["veredicto"], "falhou_na_base", t["motivo"])
        self.assertIn("usa a fixture `valor` do conftest.py do diff", t["motivo"])

    def test_conftest_que_quebra_por_biblioteca_ausente_nao_prova(self) -> None:
        t = self.julgar({"conftest.py": "import biblioteca_que_nao_esta_instalada\n",
                         "tests/test_soma.py": "from app.calc import soma\n\n\n"
                                               "def test_soma():\n    assert soma(1, 1) == 2\n"},
                        "tests/test_soma.py")
        self.assertEqual(t["veredicto"], "erro_na_base", t["motivo"])

    def test_segunda_rodada_que_nao_coleta_nada_nao_decide(self) -> None:
        """A coleta depende do conftest do diff: sem ele, o runner sai 5 sem dizer nada. A
        segunda rodada não diz nada sobre o teste, e vale o veredicto da primeira."""
        runner = self.falso.with_name("coleta_pelo_conftest.py")
        runner.write_text("import sys\nfrom pathlib import Path\n"
                          "if Path('conftest.py').is_file():\n"
                          "    print(\"ImportError while loading conftest 'conftest.py'.\")\n"
                          "    print(\"E   ModuleNotFoundError: No module named 'app.novo'\")\n"
                          "    sys.exit(4)\n"
                          "sys.exit(5)\n", encoding="utf-8")
        self.escrever({"app/novo.py": "def tres():\n    return 3\n",
                       "conftest.py": "from app.novo import tres\n",
                       "tests/test_tres.py": "def test_tres():\n    assert True\n"})
        t = self.item(self.pre_patch(f"{sys.executable} {runner} {{arquivo}}"),
                      "tests/test_tres.py")
        self.assertEqual((t["veredicto"], t["motivo"]),
                         ("falhou_na_base",
                          "exit 4 na base: falta o módulo `app.novo`, que o diff acrescenta"))

    def test_sem_o_conftest_o_teste_que_ainda_nao_carrega_por_outra_falta_nao_prova(self) -> None:
        """A segunda rodada decide: sem o conftest do diff, o teste não carrega na base por uma
        dependência que o diff não acrescenta, e a falta do conftest não vira prova."""
        t = self.julgar({"app/novo.py": "def tres():\n    return 3\n",
                         "conftest.py": "from app.novo import tres\n",
                         "tests/test_dep.py": "import pacote_que_ninguem_instalou\n\n\n"
                                              "def test_dep():\n    assert True\n"},
                        "tests/test_dep.py")
        self.assertEqual(t["veredicto"], "erro_na_base", t["motivo"])
        self.assertIn("falta o módulo `pacote_que_ninguem_instalou`", t["motivo"])

    def test_conftest_que_carrega_nao_faz_rodar_de_novo(self) -> None:
        """Sem `Error while loading conftest`, a primeira rodada decide, como antes."""
        t = self.julgar({"app/novo.py": "def tres():\n    return 3\n",
                         "conftest.py": "X = 1\n",
                         "tests/test_tres.py": "from app.novo import tres\n\n\n"
                                               "def test_tres():\n    assert tres() == 3\n"},
                        "tests/test_tres.py")
        self.assertEqual(t["veredicto"], "falhou_na_base", t["motivo"])
        self.assertNotIn("conftest.py do diff", t["motivo"])

    @unittest.skipUnless(prova._tem_modulo("pytest"), "sem pytest neste Python")
    def test_com_o_pytest_de_verdade(self) -> None:
        self.escrever({"tests/conftest.py": "X = 1\n"})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "conftest na base")
        self.git("branch", "-f", "main")
        self.escrever({"app/novo.py": "def tres():\n    return 3\n",
                       "tests/conftest.py": "from app.novo import tres\nX = 1\n",
                       "tests/test_soma.py": "from app.calc import soma\n\n\n"
                                             "def test_soma():\n    assert soma(1, 1) == 2\n"})
        t = self.item(self.pre_patch(pytest=True), "tests/test_soma.py")
        self.assertEqual(t["veredicto"], "passou_na_base", t["motivo"])


class Leitor(Repo):
    """O `erro_na_base` chega ao leitor: rótulo, JSON e saída 0 (não é teste que passa)."""

    def rodar(self, *args: str) -> tuple[int, str]:
        anterior = Path.cwd()
        os.chdir(self.raiz)
        self.addCleanup(os.chdir, anterior)
        saida = io.StringIO()
        with mock.patch.object(sys, "argv", ["prova.py", "pre-patch", "--base", "main", *args]), \
                mock.patch.object(prova, "_tem_modulo", return_value=False), redirect_stdout(saida):
            codigo = prova.main()
        return codigo, saida.getvalue()

    def test_texto_json_e_saida(self) -> None:
        self.escrever({"tests/test_dep.py": teste("import pacote_que_ninguem_instalou")})
        codigo, texto = self.rodar()
        self.assertEqual(codigo, 0)
        self.assertIn("erro na base", texto)
        self.assertIn("não carregaram na base", texto)
        codigo, texto = self.rodar("--json")
        self.assertEqual(json.loads(texto)["testes"][0]["veredicto"], "erro_na_base")
        self.escrever({"tests/test_vazio.py": teste("")})
        self.assertEqual(self.rodar()[0], 1)   # o que passa na base continua saindo 1


class SemChegarAoTeste(Repo):
    """O que para antes de o teste rodar na base diz o porquê, e o teste fica `nao_executado`."""

    def test_sem_ref_de_base(self) -> None:
        with mock.patch.object(prova, "base_padrao", return_value=None):
            r = prova.pre_patch(self.raiz, None, None, 60)
        self.assertEqual(r, {"erro": "nenhuma ref de base encontrada — passe --base", "testes": []})

    def test_sem_merge_base(self) -> None:
        r = prova.pre_patch(self.raiz, "ref-que-nao-existe", None, 60)
        self.assertEqual(r, {"erro": "sem merge-base entre ref-que-nao-existe e HEAD", "testes": []})

    def test_diff_sem_teste_novo(self) -> None:
        self.escrever({"app/calc.py": CALC + "\n\ndef dobro(x):\n    return 2 * x\n"})
        r = self.pre_patch()
        self.assertEqual((r["testes"], r["ligadas"], r["aviso"]),
                         ([], [], "nenhum teste novo no diff — nada a provar aqui"))

    def test_worktree_que_nao_se_cria(self) -> None:
        pasta = tempfile.TemporaryDirectory(prefix="kairos-forge-sem-worktree-")
        self.addCleanup(pasta.cleanup)
        ocupada = Path(pasta.name) / "tmp"
        (ocupada / "base").mkdir(parents=True)
        (ocupada / "base" / "ocupado").write_text("x", encoding="utf-8")
        self.escrever({"tests/test_n.py": teste("from app.calc import soma")})
        with mock.patch.object(prova.tempfile, "mkdtemp", return_value=str(ocupada)):
            r = prova.pre_patch(self.raiz, "main", None, 60)
        self.assertTrue(r["erro"].startswith("não consegui criar worktree na base: "), r)
        self.assertEqual(r["testes"], [])
        self.assertFalse(ocupada.exists())   # a pasta descartável sai mesmo assim

    def test_teste_que_nao_copia(self) -> None:
        self.escrever({"tests/test_n.py": teste("from app.calc import soma")})
        with mock.patch.object(prova, "_copiar", return_value=[]):
            r = self.pre_patch()
        self.assertEqual(r["testes"], [{"arquivo": "tests/test_n.py", "veredicto": "nao_executado",
                                        "motivo": "não copiei o teste para o worktree",
                                        "comando": ""}])

    def test_ecossistema_sem_comando(self) -> None:
        self.escrever({"spec/calculo_spec.rb": "describe 'x' do\nend\n"})
        self.assertEqual(self.item(self.pre_patch(), "spec/calculo_spec.rb"),
                         {"arquivo": "spec/calculo_spec.rb", "veredicto": "nao_executado",
                          "motivo": "ecossistema sem comando conhecido — passe --comando",
                          "comando": ""})

    def test_tempo_estourado(self) -> None:
        self.escrever({"tests/test_lento.py": teste("")})
        comando = f"exec {sys.executable} -c 'import time; time.sleep(10)' {{arquivo}}"
        r = prova.pre_patch(self.raiz, "main", comando, 1)
        self.assertEqual(self.git("worktree", "list").count("\n"), 1)
        self.assertEqual(self.item(r, "tests/test_lento.py"),
                         {"arquivo": "tests/test_lento.py", "veredicto": "nao_executado",
                          "motivo": "estourou 1s", "comando": comando.replace("{arquivo}",
                                                                              "tests/test_lento.py")})

    def test_campos_do_item_na_ordem_do_json(self) -> None:
        self.escrever({"app/novo.py": "def dobro(x):\n    return 2 * x\n",
                       "tests/test_novo.py": teste("from app.novo import dobro"),
                       "tests/test_vazio.py": teste("")})
        r = self.pre_patch()
        self.assertEqual(list(self.item(r, "tests/test_novo.py")),
                         ["arquivo", "veredicto", "motivo", "comando", "ultimas_linhas"])
        self.assertEqual(list(self.item(r, "tests/test_vazio.py")),
                         ["arquivo", "veredicto", "motivo", "comando"])
        self.assertEqual(list(r), ["base", "ponto", "testes", "ligadas"])


class TextoDoPrePatch(unittest.TestCase):
    """O texto que a pessoa lê, de cada forma de resultado."""

    def texto(self, r: dict) -> str:
        saida = io.StringIO()
        with redirect_stdout(saida):
            prova.imprimir_pre_patch(r)
        return saida.getvalue()

    def test_erro(self) -> None:
        self.assertEqual(self.texto({"erro": "sem merge-base", "testes": []}),
                         "🚫 prova pré-patch: sem merge-base\n")

    def test_aviso_para_antes_dos_testes(self) -> None:
        r = {"base": "main", "ponto": "abc123", "testes": [], "ligadas": ["node_modules"],
             "aviso": "nenhum teste novo no diff — nada a provar aqui"}
        self.assertEqual(self.texto(r), "🧪 Prova pré-patch — base main (abc123)\n"
                                        "   nenhum teste novo no diff — nada a provar aqui\n")

    def test_dependencias_ligadas_e_linhas_cortadas(self) -> None:
        r = {"base": "main", "ponto": "abc123", "ligadas": ["node_modules", ".venv"],
             "testes": [{"arquivo": "tests/test_a.py", "veredicto": "falhou_na_base",
                         "motivo": "exit 1 na base", "comando": "x",
                         "ultimas_linhas": ["A" * 120]}]}
        self.assertEqual(self.texto(r), (
            "🧪 Prova pré-patch — base main (abc123)\n"
            "   dependências ligadas no worktree: node_modules, .venv\n"
            "   ✅ falhou na base  tests/test_a.py\n"
            "      exit 1 na base\n"
            f"      │ {'A' * 110}\n"
            "\n   Nenhum teste novo passa na base sem a mudança.\n"))

    def test_erro_na_base_e_passou_na_base_juntos(self) -> None:
        r = {"base": "main", "ponto": "abc123", "ligadas": [],
             "testes": [{"arquivo": "tests/test_a.py", "veredicto": "erro_na_base",
                         "motivo": "m", "comando": "x"},
                        {"arquivo": "tests/test_b.py", "veredicto": "passou_na_base",
                         "motivo": "m", "comando": "x"}]}
        texto = self.texto(r)
        self.assertIn("1 teste(s) novo(s) não carregaram na base", texto)
        self.assertIn("1 teste(s) novo(s) passam sem a mudança", texto)
        self.assertNotIn("Nenhum teste novo passa", texto)


# --- a saída de cada runner, sem rodar nada ------------------------------------------

WT = Path("/tmp/kairos-forge-prova-x/base")

PYTEST_COLETA = """\
==================================== ERRORS ====================================
_______________________ ERROR collecting tests/test_x.py _______________________
ImportError while importing test module '{wt}/tests/test_x.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.13/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/test_x.py:1: in <module>
    from app.novo import f
E   ModuleNotFoundError: No module named '{modulo}'
=========================== short test summary info ============================
ERROR tests/test_x.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.05s
"""
PYTEST_NOME = """\
_______________________ ERROR collecting tests/test_y.py _______________________
tests/test_y.py:1: in <module>
    from app import g
E   ImportError: cannot import name 'g' from 'app' ({wt}/app/__init__.py)
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
"""
PYTEST_ATRIBUTO = """\
______________________ ERROR collecting tests/test_at.py _______________________
tests/test_at.py:2: in <module>
    X = app.novo_const
E   AttributeError: module 'app' has no attribute 'novo_const'
ERROR tests/test_at.py - AttributeError: module 'app' has no attribute 'novo_...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
"""
PYTEST_SINTAXE = """\
_______________________ ERROR collecting tests/test_z.py _______________________
/usr/lib/python3.13/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "{wt}/{arquivo}", line 4
E       x = (
E           ^
E   SyntaxError: '(' was never closed
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
"""
PYTEST_FIXTURE = """\
___________________________ ERROR at setup of test_a ___________________________
file {wt}/tests/test_f.py, line 1
  def test_a(cliente):
E       fixture 'cliente' not found
ERROR tests/test_f.py::test_a
1 error in 0.00s
"""
PYTEST_EM_TEMPO_DE_TESTE = """\
    def test_a():
>       from app.novo import f
E       ModuleNotFoundError: No module named 'app.novo'

tests/test_r.py:2: ModuleNotFoundError
FAILED tests/test_r.py::test_a - ModuleNotFoundError: No module named 'app.novo'
1 failed in 0.01s
"""
PYTEST_COLETA_SEM_IMPORT = """\
_______________________ ERROR collecting tests/test_n.py _______________________
tests/test_n.py:3: in <module>
    X = calcular()
E   NameError: name 'calcular' is not defined
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
"""
UNITTEST_ASSERCAO = """\
F
======================================================================
FAIL: test_a (tests.test_x.T.test_a)
----------------------------------------------------------------------
AssertionError: 3 != 4
FAILED (failures=1)
"""
VITEST_MODULO = """\
⎯⎯⎯⎯⎯⎯ Failed Suites 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  test/a.test.js [ test/a.test.js ]
Error: Cannot find {tipo} '{spec}' imported from '{wt}/test/a.test.js'
 ❯ test/a.test.js:1:1
Caused by: Error: Failed to load url {spec} (resolved id: {spec}) in {wt}/test/a.test.js. Does the file exist?
"""
VITEST_SINTAXE = """\
⎯⎯⎯⎯⎯⎯ Failed Suites 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  test/d.test.js [ test/d.test.js ]
Error: Failed to parse source for import analysis because the content contains invalid JS syntax.
  Plugin: vite:import-analysis
  File: {wt}/test/d.test.js:1:0
"""
VITEST_TYPEERROR = """\
 FAIL  test/b.test.js > a
TypeError: (0 , dobro) is not a function
 ❯ test/b.test.js:3:29
 Test Files  1 failed (1)
"""
JEST_MODULO = """\
FAIL test/a.test.js
  ● Test suite failed to run

    Cannot find module '{spec}' from 'test/a.test.js'

    > 1 | const {{ novo }} = require("{spec}")
"""
NODE_EXPORT = ("file:///x/test/a.test.mjs:1\nimport {{ dobro }} from '../src/soma.js';\n"
               "         ^^^^^\nSyntaxError: The requested module '../src/soma.js' does not "
               "provide an export named 'dobro'\n")
GO_INDEFINIDO = """\
# exemplo.com/m/calc [exemplo.com/m/calc.test]
calc/novo_test.go:6:5: undefined: Dobro
FAIL	exemplo.com/m/calc [build failed]
FAIL
"""
# Com GOPROXY=off e -mod=mod, o go não procura o pacote e diz outra frase (go 1.24).
GO_SEM_PROXY = """\
calc/novo_test.go:5:2: cannot find module providing package {pacote}: module lookup disabled by GOPROXY=off
FAIL	exemplo.com/m/calc [setup failed]
"""

GO_PACOTE = """\
# exemplo.com/m/calc
calc/novo_test.go:5:2: no required module provides package {pacote}; to add it:
	go get {pacote}
FAIL	exemplo.com/m/calc [setup failed]
FAIL
"""
GO_SINTAXE = """\
# exemplo.com/m/calc
calc/novo_test.go:7:1: expected operand, found '}}'
FAIL	exemplo.com/m/calc [setup failed]
FAIL
"""
GO_ASSERCAO = "--- FAIL: TestNovo (0.00s)\n    novo_test.go:6: conta errada\nFAIL\n"
# A falha comum que cita o texto de uma falta, no formato do jest 29 e do vitest 3: o JSON que a
# base devolve e o teste não consegue ler.
JEST_JSON = """\
FAIL test/json.test.js
  ● gera › devolve JSON

    SyntaxError: Unexpected end of JSON input
        at JSON.parse (<anonymous>)

      3 | test('devolve JSON', () => {{
    > 4 |   expect(JSON.parse(gerar())).toEqual({{ a: 1 }})
        |               ^
      5 | }})

      at Object.parse (test/json.test.js:4:15)
"""
VITEST_JSON = """\
 FAIL  test/json.test.js > devolve JSON
SyntaxError: Unexpected end of JSON input
 ❯ test/json.test.js:4:15
 Test Files  1 failed (1)
"""


class ExecutorQueNaoRoda(Repo):
    """O comando do teste que nem roda na base (exit 127, comando inexistente; 126, sem
    permissão) não diz nada sobre o teste: nem prova, nem erro do teste."""

    def test_comando_inexistente_e_nao_executado(self) -> None:
        self.escrever({"tests/test_n.py": teste("from app.calc import soma")})
        t = self.item(self.pre_patch("comando-de-teste-que-nao-existe {arquivo}"), "tests/test_n.py")
        self.assertEqual(t["veredicto"], "nao_executado", t["motivo"])
        self.assertIn("exit 127 na base: o comando do teste nem rodou", t["motivo"])


class NadaColetadoNaBase(Repo):
    """O runner que não coletou nada na base não diz nada sobre o teste: nem prova quando sai 5
    calado, nem passa sem a mudança quando diz que não rodou nada e sai 0."""

    def test_saida_5_sem_texto_e_texto_de_nada_coletado_com_saida_0(self) -> None:
        self.escrever({"tests/test_n.py": teste("from app.calc import soma")})
        for comando in (f"{sys.executable} -c 'import sys; sys.exit(5)' {{arquivo}}",
                        "echo 'no tests ran in 0.01s' {arquivo}"):
            with self.subTest(comando=comando):
                t = self.item(self.pre_patch(comando), "tests/test_n.py")
                self.assertEqual((t["veredicto"], t["motivo"]),
                                 ("nao_executado", "nenhum teste coletado no worktree da base"))


class FaltasNaSaida(unittest.TestCase):
    """A falta lida da saída e explicada, ou não, pelo que o diff acrescenta em produção."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-faltas-")
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        (self.raiz / "go.mod").write_text("module exemplo.com/m\n\ngo 1.21\n", encoding="utf-8")

    def veredicto(self, saida: str, producao: dict[str, list[str]], **campos) -> str:
        texto = saida.format(wt=WT, **campos)
        return prova.veredicto_da_falha(texto, 1, lambda: producao, self.raiz, WT)[0]

    def test_pytest_modulo_na_coleta(self) -> None:
        novo = {"app/novo.py": ["def f():", "    return 1"]}
        self.assertEqual(self.veredicto(PYTEST_COLETA, novo, modulo="app.novo"), "falhou_na_base")
        self.assertEqual(self.veredicto(PYTEST_COLETA, {"src/app/novo/__init__.py": []},
                                        modulo="app.novo"), "falhou_na_base")
        self.assertEqual(self.veredicto(PYTEST_COLETA, novo, modulo="requests"), "erro_na_base")
        # o auxiliar de teste do diff não é o que o diff muda em produção
        self.assertEqual(self.veredicto(PYTEST_COLETA, {"tests/util.py": []},
                                        modulo="tests.util"), "erro_na_base")

    def test_pytest_nome_atributo_e_import_em_tempo_de_teste(self) -> None:
        self.assertEqual(self.veredicto(PYTEST_NOME, {"app/__init__.py": ["from .x import g"]}),
                         "falhou_na_base")
        self.assertEqual(self.veredicto(PYTEST_NOME, {"outro/__init__.py": ["def g(): ..."]}),
                         "erro_na_base")
        self.assertEqual(self.veredicto(PYTEST_ATRIBUTO, {"app/__init__.py": ["novo_const = 3"]}),
                         "falhou_na_base")
        self.assertEqual(self.veredicto(PYTEST_ATRIBUTO, {"app/__init__.py": ["novo = 3"]}),
                         "erro_na_base")
        self.assertEqual(self.veredicto(PYTEST_EM_TEMPO_DE_TESTE, {"app/novo.py": []}),
                         "falhou_na_base")
        self.assertEqual(self.veredicto(PYTEST_EM_TEMPO_DE_TESTE, {}), "erro_na_base")

    def test_pytest_sintaxe_fixture_e_coleta_sem_causa_conhecida(self) -> None:
        self.assertEqual(self.veredicto(PYTEST_SINTAXE, {"app/x.py": []}, arquivo="tests/test_z.py"),
                         "erro_na_base")
        # a base com erro de sintaxe num arquivo que o diff corrige: o diff explica
        self.assertEqual(self.veredicto(PYTEST_SINTAXE, {"app/x.py": []}, arquivo="app/x.py"),
                         "falhou_na_base")
        self.assertEqual(self.veredicto(PYTEST_FIXTURE, {"app/x.py": ["def soma(): ..."]}),
                         "erro_na_base")
        self.assertEqual(self.veredicto(PYTEST_COLETA_SEM_IMPORT, {"app/x.py": ["def calcular()"]}),
                         "erro_na_base")

    def test_coleta_sem_causa_conhecida_diz_que_o_arquivo_nao_carregou(self) -> None:
        """Sem falta que as regras reconheçam, o motivo diz que o arquivo de teste não carregou."""
        saida = PYTEST_COLETA_SEM_IMPORT.format(wt=WT)
        self.assertEqual(prova.veredicto_da_falha(saida, 2, lambda: {}, self.raiz, WT),
                         ("erro_na_base", "não carregou na base: o arquivo de teste não carregou, "
                                          "e o diff não o acrescenta — não prova a mudança"))

    def test_falha_comum_nao_e_falta(self) -> None:
        for saida in (UNITTEST_ASSERCAO, VITEST_TYPEERROR, GO_ASSERCAO, JEST_JSON, VITEST_JSON):
            self.assertEqual(prova.faltas_na_carga(saida, WT), [])
            self.assertEqual(self.veredicto(saida, {}), "falhou_na_base")

    def test_fixture_so_e_explicada_pela_definicao(self) -> None:
        # A fixture de um plugin que não está instalado (`settings` do pytest-django) não vira
        # prova porque o diff cita a palavra em produção; só a fixture que ele define em produção.
        saida = PYTEST_FIXTURE.replace("cliente", "settings")
        self.assertEqual(self.veredicto(saida, {"app/conf.py": ["    settings = carregar()"]}),
                         "erro_na_base")
        motivo = prova.veredicto_da_falha(saida.format(wt=WT), 1, lambda: {}, self.raiz, WT)[1]
        self.assertIn("falta a fixture `settings`, e o diff não a acrescenta", motivo)
        self.assertEqual(self.veredicto(saida, {"app/plugin.py": ["@pytest.fixture",
                                                                  "def settings():"]}),
                         "falhou_na_base")

    def test_vitest_e_jest(self) -> None:
        ts = {"src/novo.ts": ["export function novo() { return 1 }"]}
        self.assertEqual(self.veredicto(VITEST_MODULO, ts, tipo="module", spec="../src/novo.js"),
                         "falhou_na_base")
        self.assertEqual(self.veredicto(VITEST_MODULO, ts, tipo="package", spec="lodash-inexistente"),
                         "erro_na_base")
        self.assertEqual(self.veredicto(VITEST_SINTAXE, ts), "erro_na_base")
        indice = {"src/novo/index.js": ["module.exports = {}"]}
        self.assertEqual(self.veredicto(JEST_MODULO, indice, spec="../src/novo"), "falhou_na_base")
        self.assertEqual(self.veredicto(JEST_MODULO, indice, spec="pacote-que-nao-existe"),
                         "erro_na_base")

    def test_modulo_js_por_caminho_absoluto(self) -> None:
        """O caminho absoluto fora do worktree da base não é o arquivo que o diff acrescenta,
        mesmo terminando como ele; o absoluto dentro do worktree é."""
        ts = {"src/novo.ts": ["export function novo() { return 1 }"]}
        self.assertEqual(self.veredicto(JEST_MODULO, ts, spec="/opt/outro/src/novo"),
                         "erro_na_base")
        self.assertEqual(self.veredicto(JEST_MODULO, ts, spec=f"{WT}/src/novo"), "falhou_na_base")

    def test_export_que_falta_no_esm(self) -> None:
        soma = {"src/soma.js": ["export function dobro(x) { return 2 * x }"]}
        self.assertEqual(self.veredicto(NODE_EXPORT, soma), "falhou_na_base")
        self.assertEqual(self.veredicto(NODE_EXPORT, {"src/soma.js": ["export const x = 1"]}),
                         "erro_na_base")
        self.assertEqual([f["tipo"] for f in prova.faltas_na_carga(NODE_EXPORT, WT)], ["nome"])

    def test_go(self) -> None:
        dobro = {"calc/calc.go": ["func Dobro(x int) int { return 2 * x }"]}
        self.assertEqual(self.veredicto(GO_INDEFINIDO, dobro), "falhou_na_base")
        self.assertEqual(self.veredicto(GO_INDEFINIDO, {"calc/calc.go": ["// nada"]}), "erro_na_base")
        self.assertEqual(self.veredicto(GO_PACOTE, {"novo/novo.go": ["package novo"]},
                                        pacote="exemplo.com/m/novo"), "falhou_na_base")
        # `lib/` do projeto não é o `github.com/fulano/lib` que falta
        self.assertEqual(self.veredicto(GO_PACOTE, {"lib/lib.go": ["package lib"]},
                                        pacote="github.com/fulano/lib"), "erro_na_base")
        self.assertEqual(self.veredicto(GO_SINTAXE, dobro), "erro_na_base")
        # O pacote novo do diff, com o proxy desligado: prova, e o de fora continua sem prova.
        self.assertEqual(self.veredicto(GO_SEM_PROXY, {"novo/novo.go": ["package novo"]},
                                        pacote="exemplo.com/m/novo"), "falhou_na_base")
        self.assertEqual(self.veredicto(GO_SEM_PROXY, {"novo/novo.go": ["package novo"]},
                                        pacote="github.com/fulano/lib"), "erro_na_base")


GO = shutil.which("go")


@unittest.skipUnless(GO, "sem go neste ambiente")
class GoNaBase(Repo):
    """O mesmo caminho com `go test` de verdade, sem rede."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-pre-patch-go-")
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name).resolve()
        cache = Path(self._tmp.name) / ".cache"
        ambiente = mock.patch.dict(os.environ, {"GOPROXY": "off", "GOFLAGS": "-mod=mod",
                                                "GOTOOLCHAIN": "local", "GOWORK": "off",
                                                "GOCACHE": os.environ.get("GOCACHE") or str(cache)})
        ambiente.start()
        self.addCleanup(ambiente.stop)
        self.git("init", "-q", "-b", "main")
        self.escrever({"go.mod": "module exemplo.com/m\n\ngo 1.21\n",
                       "calc/calc.go": "package calc\n\nfunc Soma(a, b int) int { return a + b }\n"})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.git("checkout", "-q", "-b", "feat")

    def test_simbolo_novo_prova_e_pacote_de_fora_nao(self) -> None:
        self.escrever({"calc/calc.go": "package calc\n\nfunc Soma(a, b int) int { return a + b }\n"
                                       "\nfunc Dobro(x int) int { return 2 * x }\n",
                       "calc/dobro_test.go": "package calc\n\nimport \"testing\"\n\n"
                                             "func TestDobro(t *testing.T) {\n"
                                             "\tif Dobro(2) != 4 {\n\t\tt.Fatal(\"x\")\n\t}\n}\n",
                       "fora/fora_test.go": "package fora\n\nimport (\n\t\"testing\"\n\n"
                                            "\t\"github.com/fulano/lib\"\n)\n\n"
                                            "func TestFora(t *testing.T) { _ = lib.X }\n"})
        r = self.pre_patch()
        self.assertEqual(self.item(r, "calc/dobro_test.go")["veredicto"], "falhou_na_base")
        self.assertEqual(self.item(r, "fora/fora_test.go")["veredicto"], "erro_na_base")

    def test_teste_novo_nao_herda_a_compilacao_de_outro_do_mesmo_pacote(self) -> None:
        # O Go compila o pacote junto: `a_test.go` passa sozinho na base, e não pode sair
        # `falhou_na_base` porque `b_test.go`, que vem depois, usa o `Dobro` que o diff traz.
        self.escrever({"calc/calc.go": "package calc\n\nfunc Soma(a, b int) int { return a + b }\n"
                                       "\nfunc Dobro(x int) int { return 2 * x }\n",
                       "calc/a_test.go": "package calc\n\nimport \"testing\"\n\n"
                                         "func TestA(t *testing.T) {\n"
                                         "\tif Soma(2, 2) != 4 {\n\t\tt.Fatal(\"x\")\n\t}\n}\n",
                       "calc/b_test.go": "package calc\n\nimport \"testing\"\n\n"
                                         "func TestB(t *testing.T) {\n"
                                         "\tif Dobro(2) != 4 {\n\t\tt.Fatal(\"x\")\n\t}\n}\n"})
        r = self.pre_patch()
        self.assertEqual(self.item(r, "calc/a_test.go")["veredicto"], "passou_na_base")
        self.assertEqual(self.item(r, "calc/b_test.go")["veredicto"], "falhou_na_base")


if __name__ == "__main__":
    unittest.main()
