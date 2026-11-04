"""Testes do `prova.py selado` — o alarme de vazamento do conjunto selado (ADR-0043).

Só stdlib. Cada teste monta um repositório mínimo num diretório temporário: o que o
alarme olha é o texto do repositório, não o git.

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
import prova  # noqa: E402

PEDIDO = "A fila está entregando a mesma mensagem duas vezes"


class Repo(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-prova-")
        self.raiz = Path(self._tmp.name).resolve()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def escrever(self, rel: str, texto: str) -> None:
        p = self.raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")

    def casos(self, rel: str, *casos: dict) -> None:
        self.escrever(rel, "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in casos))


class Selado(Repo):
    def test_sem_selado_nao_ha_o_que_proteger(self) -> None:
        self.escrever("skills/x/SKILL.md", PEDIDO)
        r = prova.selado(self.raiz)
        self.assertEqual(r["selados"], [])
        self.assertEqual(r["vazamentos"], [])

    def test_copia_com_quebra_de_linha_e_pontuacao_e_pega(self) -> None:
        self.casos("evals/rota/selado.jsonl",
                   {"id": "r-01", "pedido": PEDIDO, "esperado": ["murilo-eventos"]})
        self.escrever("agents/laura.md",
                      'Exemplo: "a FILA está\nentregando a mesma mensagem, duas vezes" → murilo\n')
        r = prova.selado(self.raiz)
        self.assertEqual(len(r["vazamentos"]), 1)
        self.assertEqual(r["vazamentos"][0]["id"], "r-01")
        self.assertEqual(r["vazamentos"][0]["onde"], ["agents/laura.md"])

    def test_fronteira_de_palavra(self) -> None:
        self.casos("evals/rota/selado.jsonl", {"pedido": PEDIDO})
        self.escrever("contextos/x.md", "Na fila está entregando a mesma mensagem duas vezesx")
        self.assertEqual(prova.selado(self.raiz)["vazamentos"], [])

    def test_trecho_curto_nao_compara_e_conta_como_curto(self) -> None:
        self.casos("evals/rota/selado.jsonl",
                   {"id": "curto-01", "pedido": "Otimizar a query lenta", "esperado": ["carlos"]})
        self.escrever("skills/x/SKILL.md", "Otimizar a query lenta é com o carlos")
        r = prova.selado(self.raiz)
        self.assertEqual(r["vazamentos"], [])
        self.assertEqual(r["selados"][0]["curtos"], 1)

    def test_id_nao_e_trecho(self) -> None:
        cid = "um id comprido com bem mais de seis palavras aqui"
        self.casos("evals/rota/selado.jsonl", {"id": cid, "pedido": "curto"})
        self.escrever("docs/x.md", cid)
        self.assertEqual(prova.selado(self.raiz)["vazamentos"], [])

    def test_repetido_no_visivel(self) -> None:
        self.casos("evals/rota/selado.jsonl", {"id": "s-01", "pedido": PEDIDO})
        self.casos("evals/rota/gold.jsonl", {"id": "v-07", "pedido": PEDIDO + "?"})
        r = prova.selado(self.raiz)
        self.assertEqual(len(r["no_visivel"]), 1)
        self.assertEqual(r["no_visivel"][0]["visivel"], "evals/rota/gold.jsonl")

    def test_trecho_nao_casa_atravessando_dois_casos_do_visivel(self) -> None:
        self.casos("evals/rota/selado.jsonl", {"pedido": PEDIDO})
        self.casos("evals/rota/gold.jsonl",
                   {"pedido": "A fila está entregando"}, {"pedido": "a mesma mensagem duas vezes"})
        self.assertEqual(prova.selado(self.raiz)["no_visivel"], [])

    def test_relatorio_do_eval_e_trajetoria_nao_contam(self) -> None:
        self.casos("evals/rota/selado.jsonl", {"pedido": PEDIDO})
        self.escrever("evals/rota/RELATORIO-2026-10-19.md", f"Falhou: {PEDIDO}")
        self.escrever(".agents/execucoes/2026-10-19.jsonl", json.dumps({"prompt": PEDIDO}))
        self.escrever("node_modules/pacote/README.md", PEDIDO)
        self.assertEqual(prova.selado(self.raiz)["vazamentos"], [])

    def test_linha_ilegivel_e_declarada(self) -> None:
        self.escrever("evals/rota/selado.jsonl", "isto não é json\n")
        r = prova.selado(self.raiz)
        self.assertEqual(len(r["ilegiveis"]), 1)
        self.assertEqual(r["ilegiveis"][0]["linha"], 1)

    def test_cli_sai_1_com_vazamento_e_0_sem(self) -> None:
        self.casos("evals/rota/selado.jsonl", {"pedido": PEDIDO})
        script = str(RAIZ / "prova.py")

        def rodar() -> int:
            return subprocess.run([sys.executable, script, "selado", "--raiz", str(self.raiz)],
                                  capture_output=True, text=True).returncode

        self.assertEqual(rodar(), 0)
        self.escrever("skills/x/SKILL.md", PEDIDO)
        self.assertEqual(rodar(), 1)


def git(raiz: Path, *args: str, autor: str = "Pessoa") -> str:
    r = subprocess.run(["git", "-C", str(raiz), "-c", f"user.name={autor}", "-c",
                        "user.email=a@b", *args], check=True, capture_output=True, text=True)
    return r.stdout.strip()


TESTE_QUE_PROVA = ('import pathlib, sys\n'
                   'sys.exit(0 if pathlib.Path("src/valor.txt").read_text().strip() == "2" else 1)\n')
TESTE_QUE_SEMPRE_PASSA = "import sys\nsys.exit(0)\n"
FABRICA = "\n\nFabrica: kairos-forge"


class ColherDoHistorico(Repo):
    """Entrega da fábrica mesclada com teste no diff vira caso candidato (ADR-0044)."""

    def setUp(self) -> None:
        super().setUp()
        git(self.raiz, "init", "-q", "-b", "main", ".")
        self.escrever("src/valor.txt", "1\n")
        git(self.raiz, "add", ".")
        git(self.raiz, "commit", "-q", "-m", "base")

    def entrega(self, numero: int, branch: str, arquivos: dict, mensagem: str) -> None:
        git(self.raiz, "checkout", "-q", "-b", branch)
        for rel, texto in arquivos.items():
            self.escrever(rel, texto)
        git(self.raiz, "add", ".")
        git(self.raiz, "commit", "-q", "-m", mensagem)
        git(self.raiz, "checkout", "-q", "main")
        git(self.raiz, "merge", "-q", "--no-ff", branch, "-m",
            f"Merge pull request #{numero} from org/{branch}")
        git(self.raiz, "reset", "-q", "--hard")

    def historico(self) -> None:
        self.entrega(1, "forge/a", {"src/valor.txt": "2\n", "tests/test_valor.py": TESTE_QUE_PROVA},
                     "feat: valor 2" + FABRICA)
        self.entrega(2, "forge/b", {"docs/x.md": "doc\n"}, "docs: só texto" + FABRICA)
        self.entrega(3, "feat/c", {"tests/test_c.py": TESTE_QUE_SEMPRE_PASSA}, "test: à mão")
        self.entrega(4, "forge/d", {"tests/test_d.py": TESTE_QUE_SEMPRE_PASSA}, "test: d" + FABRICA)

    def test_colhe_so_entrega_da_fabrica_com_teste(self) -> None:
        self.historico()
        r = prova.colher(self.raiz, None, None, False, None, 60, "git")
        self.assertEqual({c["id"] for c in r["novos"]}, {"pr-1", "pr-4"})
        self.assertIn({"id": "pr-2", "motivo": "entrega sem teste criado ou alterado — sem gabarito"},
                      r["pulados"])
        caso = next(c for c in r["novos"] if c["id"] == "pr-1")
        self.assertEqual(caso["testes"], ["tests/test_valor.py"])
        self.assertEqual(caso["estrategia"], "merge")
        self.assertTrue(caso["revisar_pedido"])  # sem gh, o pedido é o título do merge
        linhas = (self.raiz / "evals/entregas/candidatos.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(linhas), 2)
        de_novo = prova.colher(self.raiz, None, None, False, None, 60, "git")
        self.assertEqual(de_novo["novos"], [])
        self.assertEqual({c["motivo"] for c in de_novo["pulados"]} - {"entrega sem teste criado ou alterado — sem gabarito"},
                         {"já colhido"})

    def test_validar_so_deixa_o_oraculo_que_separa(self) -> None:
        self.historico()
        r = prova.colher(self.raiz, None, "evals/entregas/validados.jsonl", True,
                         f"{sys.executable} {{arquivo}}", 60, "git")
        self.assertEqual([c["id"] for c in r["novos"]], ["pr-1"])
        self.assertEqual(r["novos"][0]["oraculo"], "valido")
        self.assertIn({"id": "pr-4", "motivo": "oráculo passa_na_base"}, r["pulados"])
        self.assertEqual(git(self.raiz, "worktree", "list").count("\n"), 0)  # worktrees removidos

    def test_base_do_squash_e_do_rebase(self) -> None:
        inicio = git(self.raiz, "rev-parse", "HEAD")
        self.escrever("a.txt", "a\n")
        git(self.raiz, "add", ".")
        git(self.raiz, "commit", "-q", "-m", "feat: primeiro")
        self.escrever("b.txt", "b\n")
        git(self.raiz, "add", ".")
        git(self.raiz, "commit", "-q", "-m", "feat: segundo")
        topo = git(self.raiz, "rev-parse", "HEAD")
        commits = [{"mensagem": "feat: primeiro"}, {"mensagem": "feat: segundo"}]
        base, estrategia = prova.base_da_entrega(self.raiz, {"entrega": topo, "commits": commits})
        self.assertEqual((base, estrategia), (inicio, "rebase"))
        squash = [{"mensagem": "wip"}, {"mensagem": "ajuste"}]
        base, estrategia = prova.base_da_entrega(self.raiz, {"entrega": topo, "commits": squash})
        self.assertEqual(estrategia, "squash")
        self.assertEqual(base, git(self.raiz, "rev-parse", "HEAD~1"))


if __name__ == "__main__":
    unittest.main()


class Atalhos(Repo):
    """`prova.py atalhos` — candidatos com nome nas linhas que o diff acrescenta em código."""

    def setUp(self) -> None:
        super().setUp()
        git(self.raiz, "init", "-q", "-b", "main", ".")
        self.escrever("src/cliente.py", "import requests\n\n\ndef buscar(url):\n    return requests.get(url)\n")
        git(self.raiz, "add", ".")
        git(self.raiz, "commit", "-q", "-m", "base")
        git(self.raiz, "checkout", "-q", "-b", "feat")

    def categorias(self) -> dict[str, str]:
        r = prova.atalhos(self.raiz, "main")
        self.assertNotIn("erro", r)
        return {f"{c['arquivo']}:{c['linha']}": c["categoria"] for c in r["candidatos"]}

    def test_cada_categoria_com_arquivo_e_linha_do_diff(self) -> None:
        self.escrever("src/cliente.py",
                      "import requests\n\n\ndef buscar(url):\n"
                      "    try:\n"
                      "        return requests.get(url, verify=False)\n"
                      "    except Exception:\n"
                      "        pass\n")
        git(self.raiz, "commit", "-qam", "atalhos commitados")
        self.escrever("web/tela.tsx",
                      "const x = dado as any;\n"
                      "el.innerHTML = texto;\n"
                      "<div dangerouslySetInnerHTML={{ __html: h }} />\n"
                      "if (a.innerHTML == b) {}\n")
        self.escrever("tests/test_fila.py", "import time\n\ntime.sleep(2)\n")
        self.escrever("web/api.ts", "try {\n  enviar();\n} catch (e) {\n}\n")
        self.assertEqual(self.categorias(), {
            "web/api.ts:3": "erro-engolido",
            "src/cliente.py:6": "tls-desligado",
            "src/cliente.py:7": "erro-engolido",
            "web/tela.tsx:1": "tipo-burlado",
            "web/tela.tsx:2": "html-sem-escape",
            "web/tela.tsx:3": "html-sem-escape",
            "tests/test_fila.py:3": "sleep-como-sincronia",
        })

    def test_teste_e_marcado_e_nao_commitado_entra(self) -> None:
        self.escrever("src/cliente.py", "import requests\n\n\ndef buscar(url):\n"
                                        "    return requests.get(url)  # ok\n"
                                        "promise.catch(() => {})\n")
        r = prova.atalhos(self.raiz, "main")
        self.assertEqual([(c["linha"], c["categoria"]) for c in r["candidatos"]], [(6, "erro-engolido")])
        self.escrever("tests/test_x.py", "time.sleep(1)\n")
        teste = [c for c in prova.atalhos(self.raiz, "main")["candidatos"] if c["arquivo"] == "tests/test_x.py"]
        self.assertTrue(teste and teste[0]["teste"])

    def test_documentacao_linha_removida_e_codigo_legitimo_nao_contam(self) -> None:
        self.escrever("docs/guia.md", "Nunca use `verify=False` nem `as any`.\n")
        self.escrever("src/cliente.py", "import requests\n\n\ndef buscar(url):\n"
                                        "    try:\n"
                                        "        return requests.get(url, verify=True)\n"
                                        "    except ValueError:\n"
                                        "        raise\n"
                                        "except_handler = 1\n")
        git(self.raiz, "add", ".")
        git(self.raiz, "commit", "-qm", "doc e código")
        git(self.raiz, "checkout", "-q", "main")
        self.escrever("src/velho.py", "x = requests.get(u, verify=False)\n")
        git(self.raiz, "add", ".")
        git(self.raiz, "commit", "-qm", "atalho que já estava na base")
        git(self.raiz, "checkout", "-q", "feat")
        self.assertEqual(self.categorias(), {})

    def test_linha_acrescentada_que_comeca_com_mais_mais_nao_vira_cabecalho(self) -> None:
        self.escrever("src/contador.js", "let i = 0;\n")
        git(self.raiz, "add", ".")
        git(self.raiz, "commit", "-qm", "contador")
        self.escrever("src/contador.js", "let i = 0;\n++ b/fake\nconst y = z as any;\n")
        self.assertEqual(self.categorias(), {"src/contador.js:3": "tipo-burlado"})

    def test_cli_sai_zero_com_candidato_e_um_sem_base(self) -> None:
        self.escrever("src/cliente.py", "x = requests.get(u, verify=False)\n")
        antes = os.getcwd()
        os.chdir(self.raiz)
        try:
            for argv, esperado in ((["atalhos", "--base", "main"], 0),
                                   (["atalhos", "--base", "nao-existe"], 1)):
                sys.argv = ["prova.py", *argv]
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(prova.main(), esperado, argv)
            self.assertIn("sem base", out.getvalue())
        finally:
            os.chdir(antes)
