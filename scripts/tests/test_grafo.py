"""`grafo.py validar` como gate (ADR-0009): o que ele aprova tem de existir e ter proveniência.

- sem grafo de conhecimento (pasta vazia, só a camada de código ou `entidades.jsonl` sem
  nenhuma entidade), o `validar` diz que não há grafo e não sai 0 — o `/auditar` dá pontos
  pelo exit 0, e um grafo que não existe não pode valer como "contrato ok";
- entidade com `fontes` vazio (ou só com texto em branco) reprova: proveniência por linha é
  o que o ADR-0009 promete, e a relação sem fonte já reprovava;
- o grafo com entidades e relações com fonte continua passando.

Só stdlib. Cada teste monta o diretório do grafo numa pasta temporária.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import grafo  # noqa: E402

API = {"nome": "API de relatórios", "tipo": "COMPONENTE", "descricao": "Gera relatórios",
       "fontes": ["docs/specs/SPEC-001.md"]}
BANCO = {"nome": "PostgreSQL", "tipo": "TECNOLOGIA", "descricao": "Banco",
         "fontes": ["docs/adr/0002-banco.md"]}
ARESTA = {"origem": "API de relatórios", "predicado": "depende de", "destino": "PostgreSQL",
          "fonte": "docs/adr/0002-banco.md"}


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-grafo-")
        self.dir = Path(self._tmp.name) / "grafo"
        self.dir.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def gravar(self, nome: str, registros: list[dict]) -> None:
        (self.dir / nome).write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in registros), encoding="utf-8")

    def validar(self) -> tuple[int, str]:
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["grafo.py", "validar", "--dir", str(self.dir)]), \
                redirect_stdout(out):
            codigo = grafo.main()
        return codigo, out.getvalue()


class SemGrafo(Base):
    def test_pasta_vazia_nao_e_grafo_valido(self) -> None:
        codigo, saida = self.validar()
        self.assertNotEqual(codigo, 0)
        self.assertIn("sem grafo de conhecimento", saida.lower())
        self.assertNotIn("Contrato ok", saida)

    def test_so_a_camada_de_codigo_nao_e_grafo_de_conhecimento(self) -> None:
        # `grafo.py codigo` cria a pasta com `codigo.jsonl`; isso não é o grafo do ADR-0009.
        self.gravar("codigo.jsonl", [{"origem": "a.py", "predicado": "importa",
                                      "destino": "b.py"}])
        codigo, saida = self.validar()
        self.assertNotEqual(codigo, 0)
        self.assertIn("sem grafo de conhecimento", saida.lower())

    def test_entidades_jsonl_sem_entidade_nao_passa(self) -> None:
        (self.dir / "entidades.jsonl").write_text("\n", encoding="utf-8")
        (self.dir / "relacoes.jsonl").write_text("", encoding="utf-8")
        codigo, saida = self.validar()
        self.assertNotEqual(codigo, 0)
        self.assertIn("sem grafo de conhecimento", saida.lower())

    def test_diretorio_inexistente_continua_nao_passando(self) -> None:
        self.dir.rmdir()
        codigo, saida = self.validar()
        self.assertNotEqual(codigo, 0)
        self.assertIn("não existe", saida)

    def test_relacao_sem_entidades_e_erro_de_contrato_e_nao_ausencia(self) -> None:
        self.gravar("relacoes.jsonl", [ARESTA])
        codigo, saida = self.validar()
        self.assertEqual(codigo, 1)
        self.assertIn("aresta órfã", saida)


class Proveniencia(Base):
    def test_grafo_com_fontes_passa(self) -> None:
        self.gravar("entidades.jsonl", [API, BANCO])
        self.gravar("relacoes.jsonl", [ARESTA])
        codigo, saida = self.validar()
        self.assertEqual(codigo, 0, saida)
        self.assertIn("Contrato ok: 2 entidades, 1 relações", saida)

    def test_entidade_com_fontes_vazio_reprova(self) -> None:
        self.gravar("entidades.jsonl", [API, {**BANCO, "fontes": []}])
        self.gravar("relacoes.jsonl", [ARESTA])
        codigo, saida = self.validar()
        self.assertEqual(codigo, 1)
        self.assertIn("'PostgreSQL' sem fontes", saida)
        self.assertNotIn("'API de relatórios' sem fontes", saida)

    def test_fontes_so_com_texto_em_branco_ou_nulo_reprova(self) -> None:
        for fontes in ([""], ["   "], None, ""):
            with self.subTest(fontes=fontes):
                self.gravar("entidades.jsonl", [{**API, "fontes": fontes}])
                codigo, saida = self.validar()
                self.assertEqual(codigo, 1)
                self.assertIn("'API de relatórios' sem fontes", saida)

    def test_fonte_unica_como_texto_vale(self) -> None:
        # O contrato mostra lista; um caminho solto também é proveniência, e não reprova.
        self.gravar("entidades.jsonl", [{**API, "fontes": "docs/specs/SPEC-001.md"}])
        self.assertEqual(self.validar()[0], 0)

    def test_fonte_unica_como_texto_e_lida_inteira_no_contexto_e_na_amostra(self) -> None:
        # O que o `validar` aprova o resto do script lê: o caminho solto não vira letra a letra.
        self.gravar("entidades.jsonl", [{**API, "fontes": "src/api.py"}])
        self.gravar("codigo.jsonl", [{"origem": "src/api.py", "predicado": "importa",
                                      "destino": "src/db.py", "fonte": "src/api.py:1"}])
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["grafo.py", "contexto", "src/api.py", "--json",
                                             "--dir", str(self.dir)]), redirect_stdout(out):
            self.assertEqual(grafo.main(), 0)
        self.assertEqual(json.loads(out.getvalue())["entidades_de_conhecimento"],
                         ["API de relatórios"])
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["grafo.py", "amostrar", "--dir", str(self.dir)]), \
                redirect_stdout(out):
            grafo.main()
        self.assertIn("Fontes: src/api.py\n", out.getvalue())

    def test_relacao_com_fonte_em_branco_reprova(self) -> None:
        self.gravar("entidades.jsonl", [API, BANCO])
        self.gravar("relacoes.jsonl", [{**ARESTA, "fonte": "  "}])
        codigo, saida = self.validar()
        self.assertEqual(codigo, 1)
        self.assertIn("relação 1 sem fonte", saida)


if __name__ == "__main__":
    unittest.main()
