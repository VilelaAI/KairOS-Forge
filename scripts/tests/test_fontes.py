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
            "fato 1: data da fonte fora de AAAA-MM-DD ou AAAA-MM"])

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

    def test_spec_que_nao_existe_e_sem_aprovacao(self) -> None:
        self.assertEqual(prova.fontes(self.raiz, "SPEC-099", 180, HOJE)["spec"],
                         {"spec": "SPEC-099", "erro": "SPEC não encontrada em docs/specs/"})
        self.assertIsNone(prova._mudou_depois(self.raiz, "docs/pesquisa/csv.md", None))
        # Instante que não se lê: qualquer commit desde ele conta, sem quebrar.
        self.assertIsInstance(prova._mudou_depois(self.raiz, "docs/pesquisa/csv.md", "x"), bool)


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
        self.escrever({"docs/adr/0001.md": "docs/pesquisa/sumiu.md\n"})
        self.assertEqual(self.rodar().returncode, 1)
        self.escrever({"docs/adr/0001.md": "nada\n", "docs/pesquisa/ruim.md": "# x\n"})
        self.assertEqual(self.rodar().returncode, 1)


if __name__ == "__main__":
    unittest.main()
