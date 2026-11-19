"""Fonte primária salva (ADR-0060): a forma de cada `docs/pesquisa/*.md` e as citações.

O `fontes` não busca nada na rede: confere a forma (data, resposta, fato com fonte, versão e
data, nenhum segredo) e que toda citação a `docs/pesquisa/` aponta para arquivo que existe.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import prova  # noqa: E402

QUEM = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "commit.gpgsign",
        "GIT_CONFIG_VALUE_0": "false"}
HOJE = date(2026, 11, 19)
TOKEN = "ghp_" + "c" * 36
PESQUISA = """# A biblioteca de CSV aceita separador por ponto e vírgula?

- **Data da pesquisa:** 2026-11-10
- **Para:** SPEC-007

**Resposta:** Sim, desde a 2.1, pelo parâmetro `delimiter`.

## Fatos

| # | Fato | Fonte | Versão | Data da fonte |
|---|---|---|---|---|
| 1 | O leitor aceita o parâmetro `delimiter`. | [doc oficial](https://exemplo.org/csv#delimiter) | 2.1.0 | 2026-03 |
| 2 | O padrão continua sendo a vírgula. | `vendas/leitor.py:12` | sem versão | 2026-11-10 |

## Inferências

- Pelos fatos 1 e 2, basta passar o separador na leitura.

## Em aberto

- Nada.
"""


class Pasta(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-fontes-")
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self.escrever({"vendas/leitor.py": "x = 1\n"})

    def escrever(self, arquivos: dict[str, str]) -> None:
        for rel, texto in arquivos.items():
            (self.raiz / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.raiz / rel).write_text(texto, encoding="utf-8")

    def conferir(self, texto: str = PESQUISA, **kw) -> dict:
        self.escrever({"docs/pesquisa/csv.md": texto})
        return prova.fontes(self.raiz, kw.get("spec"), kw.get("idade", 180), HOJE)

    def problemas(self, texto: str) -> list[str]:
        return self.conferir(texto)["pesquisas"][0]["problemas"]


class AForma(Pasta):
    def test_a_pesquisa_completa(self) -> None:
        r = self.conferir()
        self.assertEqual(r["pesquisas"], [{"arquivo": "docs/pesquisa/csv.md", "data": "2026-11-10",
                                           "problemas": [], "avisos": []}])
        self.assertEqual(r["citacoes_quebradas"], [])

    def test_fato_sem_fonte_ou_com_caminho_que_nao_existe(self) -> None:
        for fonte in ("doc oficial", "`vendas/sumiu.py:3`", "docs"):
            with self.subTest(fonte):
                texto = PESQUISA.replace("[doc oficial](https://exemplo.org/csv#delimiter)", fonte)
                self.assertEqual(self.problemas(texto),
                                 ["fato 1: sem fonte: um link ou um caminho do repositório que exista"])

    def test_versao_e_data_da_fonte(self) -> None:
        texto = PESQUISA.replace("| 2.1.0 | 2026-03 |", "|  | março |")
        self.assertEqual(self.problemas(texto), [
            "fato 1: sem versão (escreva `sem versão` quando a fonte não tem)",
            "fato 1: data da fonte fora de AAAA-MM-DD ou AAAA-MM, ou no futuro"])
        for data in ("2026-13-45", "2099-01", "2026-02-30"):
            with self.subTest(data):
                self.assertEqual(self.problemas(PESQUISA.replace("| 2026-03 |", f"| {data} |")),
                                 ["fato 1: data da fonte fora de AAAA-MM-DD ou AAAA-MM, ou no futuro"])

    def test_fato_com_a_data_de_hoje_vale(self) -> None:
        """A fonte publicada hoje não está no futuro: só o dia seguinte reprova."""
        self.assertEqual(self.problemas(PESQUISA.replace("| 2026-03 |", "| 2026-11-19 |")), [])
        self.assertEqual(self.problemas(PESQUISA.replace("| 2026-03 |", "| 2026-11-20 |")),
                         ["fato 1: data da fonte fora de AAAA-MM-DD ou AAAA-MM, ou no futuro"])

    def test_o_hoje_pedido_manda_na_data_da_fonte(self) -> None:
        """A data da fonte é julgada contra o `hoje` que se pede, não contra o relógio; sem
        `hoje`, vale o relógio (aqui parado em 2026-03-31, para o teste não depender do dia)."""
        self.escrever({"docs/pesquisa/csv.md": PESQUISA.replace("2026-11-10\n-", "2026-03-31\n-")})
        r = prova.fontes(self.raiz, None, 180, date(2026, 3, 31))
        self.assertEqual(r["pesquisas"][0]["problemas"],
                         ["fato 2: data da fonte fora de AAAA-MM-DD ou AAAA-MM, ou no futuro"])

        class Relogio(date):
            @classmethod
            def today(cls) -> date:
                return date(2026, 3, 31)

        fato = ["1", "fato", "https://exemplo.org", "1.0", "2026-11-10"]
        with unittest.mock.patch.object(prova, "date", Relogio):
            self.assertEqual(prova.problemas_do_fato(fato, self.raiz),
                             ["fato 1: data da fonte fora de AAAA-MM-DD ou AAAA-MM, ou no futuro"])
            self.assertEqual(prova.problemas_do_fato(fato, self.raiz, date(2026, 11, 19)), [])

    def test_copia_avulsa_sem_o_segredos_py_confere_a_forma(self) -> None:
        """O `prova.py` copiado sozinho, sem o `segredos.py` ao lado, ainda confere a forma das
        pesquisas: sem a regra, nenhum segredo é procurado, e o comando não quebra."""
        avulso = Path(tempfile.mkdtemp(prefix="kairos-forge-prova-avulso-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(avulso, ignore_errors=True))
        (avulso / "prova.py").write_text((RAIZ / "prova.py").read_text(encoding="utf-8"), encoding="utf-8")
        self.escrever({"docs/pesquisa/csv.md": PESQUISA,
                       "docs/pesquisa/ruim.md": PESQUISA.replace("| 2.1.0 |", "|  |")})
        r = subprocess.run([sys.executable, "-I", "-B", str(avulso / "prova.py"), "fontes", "--json",
                            "--raiz", str(self.raiz)], cwd=self.raiz, capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stderr), (1, ""))
        self.assertEqual({p["arquivo"]: p["problemas"] for p in json.loads(r.stdout)["pesquisas"]},
                         {"docs/pesquisa/csv.md": [],
                          "docs/pesquisa/ruim.md": ["fato 1: sem versão (escreva `sem versão` "
                                                    "quando a fonte não tem)"]})

    def test_linha_curta_e_fato_vazio(self) -> None:
        texto = PESQUISA.replace("| 1 | O leitor aceita o parâmetro `delimiter`. |", "| 1 |  |")
        self.assertEqual(self.problemas(texto), ["fato 1: sem o fato"])
        texto = PESQUISA.replace("| sem versão | 2026-11-10 |", "")
        self.assertEqual(self.problemas(texto),
                         ["fato 2: a linha precisa de fato, fonte, versão e data da fonte"])

    def test_cabecalho_da_pesquisa(self) -> None:
        texto = (PESQUISA.replace("# A biblioteca", "A biblioteca")
                 .replace("2026-11-10\n- **Para", "ontem\n- **Para")
                 .replace("**Resposta:** Sim, desde a 2.1, pelo parâmetro `delimiter`.", "**Resposta:**"))
        self.assertEqual(self.problemas(texto), ["sem título `# <pergunta>`",
                                                 "sem **Data da pesquisa:** AAAA-MM-DD",
                                                 "sem **Resposta:**"])

    def test_data_no_futuro(self) -> None:
        self.assertEqual(self.problemas(PESQUISA.replace("2026-11-10\n-", "2026-12-01\n-")),
                         ["data da pesquisa no futuro"])
        self.assertEqual(self.problemas(PESQUISA.replace("2026-11-10\n-", "2026-11-19\n-")), [])

    def test_sem_fatos(self) -> None:
        texto = PESQUISA.split("## Fatos")[0] + "## Fatos\n\n## Em aberto\n\n- Nada.\n"
        self.assertEqual(self.problemas(texto), ["`## Fatos` sem nenhuma linha"])

    def test_nao_encontrada(self) -> None:
        cabeca = PESQUISA.split("**Resposta:**")[0] + "**Resposta:** não encontrada.\n"
        self.assertEqual(self.problemas(cabeca + "\n## Em aberto\n\n- A doc da 2.x saiu do ar.\n"), [])
        self.assertEqual(self.problemas(cabeca), ['resposta "não encontrada" sem `## Em aberto`'])

    def test_o_marcador_do_modelo_nao_preenche(self) -> None:
        cabeca = PESQUISA.split("**Resposta:**")[0] + "**Resposta:** não encontrada.\n"
        self.assertEqual(self.problemas(cabeca + "\n## Em aberto\n\n- <o que não deu para confirmar>\n"),
                         ['resposta "não encontrada" sem `## Em aberto`'])
        self.assertEqual(self.problemas(PESQUISA.replace(
            "**Resposta:** Sim, desde a 2.1, pelo parâmetro `delimiter`.", "**Resposta:** <uma frase>")),
            ["sem **Resposta:**"])

    def test_nao_encontrada_de_passagem_nao_dispensa_os_fatos(self) -> None:
        texto = (PESQUISA.split("## Fatos")[0].replace(
            "Sim, desde a 2.1", "Sim; a opção antiga foi não encontrada na 3.0, mas a 2.1")
            + "## Fatos\n\n## Em aberto\n\n- Nada.\n")
        self.assertEqual(self.problemas(texto), ["`## Fatos` sem nenhuma linha"])
        self.assertEqual(self.problemas(texto.replace("**Resposta:** Sim;", "**Resposta:** Não encontrada;")), [])

    def test_o_fato_do_modelo_e_a_fonte_fora_do_repositorio(self) -> None:
        modelo = PESQUISA.replace("| 1 | O leitor aceita o parâmetro `delimiter`. | [doc oficial](https://exemplo.org/csv#delimiter) | 2.1.0 |",
                                  "| 1 | <o fato> | [<título>](https://…) | <v4.2.0 ou sem versão> |")
        self.assertEqual(self.problemas(modelo), ["fato 1: sem o fato",
                                                  "fato 1: sem fonte: um link ou um caminho do repositório que exista",
                                                  "fato 1: sem versão (escreva `sem versão` quando a fonte não tem)"])
        fora = PESQUISA.replace("`vendas/leitor.py:12`", "`../../../../../../../etc/passwd`")
        self.assertEqual(self.problemas(fora),
                         ["fato 2: sem fonte: um link ou um caminho do repositório que exista"])
        sem_numero = PESQUISA.replace("| 2 | O padrão", "|  | O padrão").replace("| 2026-11-10 |\n\n## Inf", "| ontem |\n\n## Inf")
        self.assertIn("fato ?: data da fonte fora de AAAA-MM-DD ou AAAA-MM, ou no futuro", self.problemas(sem_numero))

    def test_arquivo_ilegivel_vira_problema(self) -> None:
        (self.raiz / "docs/pesquisa/pasta.md").mkdir(parents=True)
        r = self.conferir()
        self.assertIn({"arquivo": "docs/pesquisa/pasta.md", "data": "",
                       "problemas": ["ilegível: IsADirectoryError"], "avisos": []}, r["pesquisas"])

    def test_segredo_no_texto(self) -> None:
        texto = PESQUISA.replace("- Nada.", f"- O exemplo da doc usa `{TOKEN}`.")
        self.assertEqual(self.problemas(texto),
                         ["segredo no texto: rode `guardrail.py ocultar <arquivo>`"])

    def test_pesquisa_velha_e_aviso(self) -> None:
        p = self.conferir(idade=5)["pesquisas"][0]
        self.assertEqual((p["problemas"], p["avisos"]),
                         ([], ["mais de 5 dias: confira se a fonte mudou"]))
        self.assertEqual(self.conferir(idade=9)["pesquisas"][0]["avisos"], [])

    def test_readme_da_pasta_e_ignorado(self) -> None:
        self.escrever({"docs/pesquisa/README.md": "# índice\n"})
        self.assertEqual([p["arquivo"] for p in self.conferir()["pesquisas"]], ["docs/pesquisa/csv.md"])

    def test_sem_pasta_nada_a_conferir(self) -> None:
        r = prova.fontes(self.raiz, None, 180, HOJE)
        self.assertEqual((r["pesquisas"], r["citacoes_quebradas"], r["spec"]), ([], [], None))


class AsCitacoes(Pasta):
    def test_citacao_quebrada_em_qualquer_md(self) -> None:
        self.escrever({"docs/adr/0001-x.md": "Ver docs/pesquisa/csv.md e docs/pesquisa/sumiu.md.\n",
                       "contextos/stack.md": "\n(docs/pesquisa/outra/velha.md)\n",
                       "docs/pesquisa/indice.txt": "docs/pesquisa/nao-conta.md\n",
                       "node_modules/x/README.md": "docs/pesquisa/dependencia.md\n",
                       ".agents/execucoes/s.md": "docs/pesquisa/trajetoria.md\n",
                       "modelo.md": "docs/pesquisa/<assunto>.md\n"})
        r = self.conferir()
        self.assertEqual(r["citacoes_quebradas"], [
            {"arquivo": "contextos/stack.md", "linha": 2, "alvo": "docs/pesquisa/outra/velha.md"},
            {"arquivo": "docs/adr/0001-x.md", "linha": 1, "alvo": "docs/pesquisa/sumiu.md"}])

    def test_citacao_de_outro_repositorio_ou_subprojeto_nao_conta(self) -> None:
        self.escrever({"README.md": "https://github.com/outro/projeto/blob/main/docs/pesquisa/x.md\n"
                                    "pacotes/api/docs/pesquisa/y.md\n"})
        self.assertEqual(self.conferir()["citacoes_quebradas"], [])

    def test_md_ilegivel_e_pulado(self) -> None:
        (self.raiz / "binario.md").write_bytes(b"\xff\xfe docs/pesquisa/x.md")
        self.assertEqual(self.conferir()["citacoes_quebradas"], [])


class NaSpec(Pasta):
    def setUp(self) -> None:
        super().setUp()
        self.git("init", "-q", "-b", "main")
        self.escrever({"docs/pesquisa/csv.md": PESQUISA,
                       "docs/specs/SPEC-007-csv.md": "# SPEC-007\n\nSe apoia em docs/pesquisa/csv.md e "
                                                     "docs/pesquisa/csv.md de novo.\n"})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "spec aprovada", "--date", "2026-11-10T10:00:00Z",
                 env={"GIT_COMMITTER_DATE": "2026-11-10T10:00:00Z"})

    def git(self, *args: str, env: dict | None = None) -> str:
        return subprocess.run(["git", *args], cwd=self.raiz, check=True, capture_output=True,
                              text=True, env={**os.environ, **QUEM, **(env or {})}).stdout

    def test_a_pesquisa_que_nao_mudou(self) -> None:
        spec = prova.fontes(self.raiz, "SPEC-007", 180, HOJE)["spec"]
        self.assertEqual(spec["citadas"], [{"pesquisa": "docs/pesquisa/csv.md", "existe": True,
                                            "mudou_depois": False}])
        self.assertEqual(spec["fonte_da_aprovacao"], "último commit da SPEC")

    def test_a_pesquisa_que_mudou_depois_da_aprovacao(self) -> None:
        self.escrever({"docs/pesquisa/csv.md": PESQUISA.replace("Nada.", "O 3.0 muda o padrão.")})
        self.assertTrue(prova.fontes(self.raiz, "SPEC-007", 180, HOJE)["spec"]["citadas"][0]["mudou_depois"])
        self.git("commit", "-qam", "pesquisa revista", env={"GIT_COMMITTER_DATE": "2026-11-15T10:00:00Z"})
        self.assertTrue(prova.fontes(self.raiz, "SPEC-007", 180, HOJE)["spec"]["citadas"][0]["mudou_depois"])

    def test_rebase_depois_do_selo_nao_conta_como_mudanca(self) -> None:
        (self.raiz / ".agents/ciclo").mkdir(parents=True)
        (self.raiz / ".agents/ciclo/SPEC-007.json").write_text('{"spec_selada_em": "2026-11-12T10:00:00+00:00"}',
                                                             encoding="utf-8")
        self.git("commit", "-q", "--amend", "--no-edit", env={"GIT_COMMITTER_DATE": "2026-11-15T10:00:00Z"})
        self.assertFalse(prova.fontes(self.raiz, "SPEC-007", 180, HOJE)["spec"]["citadas"][0]["mudou_depois"])

    def test_spec_que_nao_existe_e_sem_aprovacao(self) -> None:
        self.assertEqual(prova.fontes(self.raiz, "SPEC-099", 180, HOJE)["spec"],
                         {"spec": "SPEC-099", "erro": "SPEC não encontrada em docs/specs/"})
        self.assertIsNone(prova._mudou_depois(self.raiz, "docs/pesquisa/csv.md", None))
        # Instante que não se lê: qualquer commit desde ele conta, sem quebrar.
        self.assertIsInstance(prova._mudou_depois(self.raiz, "docs/pesquisa/csv.md", "x"), bool)

    def test_selo_ilegivel_conta_qualquer_commit_ou_mudanca(self) -> None:
        """Selo que não se lê como instante: a pesquisa com commit ou com mudança pendente conta
        como mudada depois da aprovação (confere-se à toa, não se deixa passar); a que nunca
        existiu, não."""
        (self.raiz / ".agents/ciclo").mkdir(parents=True)
        (self.raiz / ".agents/ciclo/SPEC-007.json").write_text('{"spec_selada_em": "ontem"}',
                                                             encoding="utf-8")
        spec = prova.fontes(self.raiz, "SPEC-007", 180, HOJE)["spec"]
        self.assertEqual((spec["aprovacao"], spec["citadas"][0]["mudou_depois"]), ("ontem", True))
        self.escrever({"docs/pesquisa/nova.md": PESQUISA})
        self.assertTrue(prova._mudou_depois(self.raiz, "docs/pesquisa/nova.md", "ontem"))
        self.assertFalse(prova._mudou_depois(self.raiz, "docs/pesquisa/sumiu.md", "ontem"))


class AImpressaoEOComando(NaSpec):
    def imprimir(self, r: dict) -> str:
        saida = io.StringIO()
        with redirect_stdout(saida):
            prova.imprimir_fontes(r)
        return saida.getvalue()

    def test_impressao(self) -> None:
        self.escrever({"docs/adr/0001.md": "docs/pesquisa/sumiu.md\n",
                       "docs/pesquisa/velha.md": PESQUISA.replace("2026-11-10\n-", "2020-01-01\n-")
                       .replace("| 2.1.0 |", "|  |")})
        saida = self.imprimir(prova.fontes(self.raiz, "SPEC-007", 180, HOJE))
        self.assertIn("2 pesquisa(s) em docs/pesquisa/", saida)
        self.assertIn("✅ docs/pesquisa/csv.md (2026-11-10)", saida)
        self.assertIn("❌ docs/pesquisa/velha.md (2020-01-01)", saida)
        self.assertIn("· mais de 180 dias", saida)
        self.assertIn("❌ docs/adr/0001.md:1 cita docs/pesquisa/sumiu.md, que não existe", saida)
        self.assertIn("SPEC-007 cita 1 pesquisa(s)", saida)
        self.assertNotIn("nada a conferir", saida)
        self.escrever({"docs/pesquisa/csv.md": PESQUISA.replace("Nada.", "Mudou.")})
        self.assertIn("mudou depois da aprovação",
                      self.imprimir(prova.fontes(self.raiz, "SPEC-007", 180, HOJE)))
        self.assertIn("🚫 SPEC-099", self.imprimir(prova.fontes(self.raiz, "SPEC-099", 180, HOJE)))
        vazio = Path(tempfile.mkdtemp(prefix="kairos-forge-fontes-vazio-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(vazio, ignore_errors=True))
        self.assertIn("nada a conferir", self.imprimir(prova.fontes(vazio, None, 180, HOJE)))
        self.assertIn("⚠️  docs/pesquisa/csv.md",
                      self.imprimir(prova.fontes(self.raiz, None, 1, HOJE)))

    def test_nada_a_conferir_so_sem_pesquisa_e_sem_citacao_quebrada(self) -> None:
        """Basta uma pesquisa ou uma citação quebrada para o relatório não dizer "nada a conferir"."""
        so_pesquisa = prova.fontes(self.raiz, None, 180, HOJE)
        self.assertEqual((len(so_pesquisa["pesquisas"]), so_pesquisa["citacoes_quebradas"]), (1, []))
        self.assertNotIn("nada a conferir", self.imprimir(so_pesquisa))
        vazio = Path(tempfile.mkdtemp(prefix="kairos-forge-fontes-so-citacao-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(vazio, ignore_errors=True))
        (vazio / "docs/adr").mkdir(parents=True)
        (vazio / "docs/adr/0001.md").write_text("docs/pesquisa/sumiu.md\n", encoding="utf-8")
        so_citacao = prova.fontes(vazio, None, 180, HOJE)
        self.assertEqual((so_citacao["pesquisas"], len(so_citacao["citacoes_quebradas"])), ([], 1))
        self.assertNotIn("nada a conferir", self.imprimir(so_citacao))

    def rodar(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", str(RAIZ / "prova.py"), "fontes", *args],
                              cwd=self.raiz, capture_output=True, text=True)

    def test_comando(self) -> None:
        r = self.rodar("SPEC-007", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(r.stdout)["spec"]["citadas"][0]["pesquisa"], "docs/pesquisa/csv.md")
        self.assertEqual(self.rodar("--raiz", str(self.raiz)).returncode, 0)
        self.assertEqual(self.rodar("--idade-max", "x").returncode, 1)
        self.assertEqual(self.rodar("SPEC-099").returncode, 1)   # SPEC que não existe não passa calada
        self.assertEqual(self.rodar("spec-007").returncode, 0)    # o id em minúscula acha a SPEC
        self.escrever({"docs/adr/0001.md": "docs/pesquisa/sumiu.md\n"})
        self.assertEqual(self.rodar().returncode, 1)
        self.escrever({"docs/adr/0001.md": "nada\n", "docs/pesquisa/ruim.md": "# x\n"})
        self.assertEqual(self.rodar().returncode, 1)

    def test_sem_raiz_numa_subpasta_confere_a_raiz_do_repositorio(self) -> None:
        """Sem `--raiz`, o comando rodado numa subpasta confere a raiz do git, não a subpasta."""
        r = subprocess.run([sys.executable, "-B", str(RAIZ / "prova.py"), "fontes", "--json"],
                           cwd=self.raiz / "vendas", capture_output=True, text=True)
        saida = json.loads(r.stdout)
        self.assertEqual((Path(saida["raiz"]).resolve(), [p["arquivo"] for p in saida["pesquisas"]]),
                         (self.raiz.resolve(), ["docs/pesquisa/csv.md"]), r.stderr)


class OMainNoProcesso(unittest.TestCase):
    """Os comandos fora do diff (`fontes`, `selado`, `colher`) pelo `main`, no mesmo processo."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-main-")
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self._cwd = os.getcwd()
        os.chdir(self.raiz)
        self.addCleanup(os.chdir, self._cwd)

    def main(self, *args: str) -> tuple[int, str]:
        saida, erro = io.StringIO(), io.StringIO()
        with redirect_stdout(saida), unittest.mock.patch.object(sys, "argv", ["prova.py", *args]), \
                unittest.mock.patch.object(sys, "stderr", erro):
            codigo = prova.main()
        return codigo, saida.getvalue() + erro.getvalue()

    def test_fontes(self) -> None:
        self.assertEqual(self.main("fontes", "--raiz", str(self.raiz)), (0, f"📚 Fontes salvas — 0 pesquisa(s) em docs/pesquisa/\n   nada a conferir\n"))
        codigo, texto = self.main("fontes", "--json", "--raiz", str(self.raiz))
        self.assertEqual((codigo, json.loads(texto)["pesquisas"]), (0, []))
        self.assertEqual(self.main("fontes", "--idade-max", "x")[0], 1)
        self.assertEqual(self.main("fontes", "SPEC-001", "--raiz", str(self.raiz))[0], 1)

    def test_json_sai_com_o_acento_legivel(self) -> None:
        """O `--json` sai em UTF-8: o PT-BR do relatório não vira escape unicode para quem lê."""
        codigo, texto = self.main("fontes", "SPEC-001", "--json", "--raiz", str(self.raiz))
        self.assertEqual((codigo, json.loads(texto)["spec"]["erro"]),
                         (1, "SPEC não encontrada em docs/specs/"))
        self.assertIn('"erro": "SPEC não encontrada em docs/specs/"', texto)

    def test_fora_do_git_sem_raiz_confere_a_pasta_atual(self) -> None:
        """Fora de um repositório git e sem `--raiz`, `fontes` e `selado` leem a pasta de onde rodam."""
        (self.raiz / "docs/pesquisa").mkdir(parents=True)
        (self.raiz / "docs/pesquisa/csv.md").write_text(PESQUISA, encoding="utf-8")
        _, texto = self.main("fontes", "--json")
        self.assertEqual([p["arquivo"] for p in json.loads(texto)["pesquisas"]], ["docs/pesquisa/csv.md"])
        self.assertEqual(self.main("selado")[0], 0)

    def test_selado(self) -> None:
        self.assertEqual(self.main("selado", "--raiz", str(self.raiz))[0], 0)
        self.assertIn('"selados": []', self.main("selado", "--json", "--raiz", str(self.raiz))[1])

    def test_colher_e_os_erros_de_argumento(self) -> None:
        self.assertIn("fora de um repositório git", self.main("colher")[1])
        subprocess.run(["git", "init", "-q"], cwd=self.raiz, check=True)
        self.assertEqual(self.main("colher", "--dias", "x")[0], 1)
        self.assertIn("--fonte é gh ou git", self.main("colher", "--fonte", "svn")[1])
        self.assertEqual(self.main("colher", "--fonte", "git", "--saida", str(self.raiz / "c.jsonl"))[0], 0)
        self.assertEqual(self.main("colher", "--json", "--fonte", "git",
                                   "--saida", str(self.raiz / "c.jsonl"))[0], 0)
        self.assertEqual(self.main("pre-patch", "--tempo-limite", "x")[0], 1)
        codigo, texto = self.main("nada")
        self.assertEqual((codigo, texto.splitlines()[0]), (1, prova.__doc__.strip().splitlines()[0]))

    def test_colher_que_nao_colhe_sai_1(self) -> None:
        """Fora do git ou com `--fonte` inválida o `colher` sai 1: `sys.exit(None)` diria sucesso ao shell."""
        codigo, texto = self.main("colher")
        self.assertEqual((codigo, "fora de um repositório git" in texto), (1, True))
        subprocess.run(["git", "init", "-q"], cwd=self.raiz, check=True)
        codigo, texto = self.main("colher", "--fonte", "svn")
        self.assertEqual((codigo, "--fonte é gh ou git" in texto), (1, True))


if __name__ == "__main__":
    unittest.main()
