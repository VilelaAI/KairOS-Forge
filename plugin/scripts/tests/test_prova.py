"""Testes do `prova.py selado` — o alarme de vazamento do conjunto selado (ADR-0043).

Só stdlib. Cada teste monta um repositório mínimo num diretório temporário: o que o
alarme olha é o texto do repositório, não o git.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import json
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


if __name__ == "__main__":
    unittest.main()
