"""Testes do `tucano.py` — a fábrica como time do Tucano (ADR-0047).

Só stdlib. O importador do Tucano é TypeScript e não roda aqui: o que se testa é que o
arquivo gerado obedece às regras que o `importTeam` dele aplica (src/core/team.ts) e
que o `instalar` deixa o projeto com o que as skills citam.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import tucano  # noqa: E402


class TimeGerado(unittest.TestCase):
    def setUp(self) -> None:
        self.time = tucano.montar_time("loja")

    def test_o_bloco_e_o_que_o_importador_le_e_e_valido(self) -> None:
        texto = tucano.markdown(self.time)
        self.assertEqual(tucano.ler_bloco(texto), self.time)  # nenhum ``` corta o bloco antes
        self.assertEqual(tucano.validar(self.time), [])
        self.assertTrue(texto.startswith(f"<!-- {tucano.MARCA_GERADO}"))
        self.assertIn("- **Patrícia** (@patricia) · QA · gpt-5.6-terra", texto)

    def test_quem_constroi_no_claude_e_quem_revisa_no_codex(self) -> None:
        motor = {a["handle"]: tucano.MODELOS[a["model"]] for a in self.time["agents"]}
        self.assertEqual({motor["lucas"], motor["marina"]}, {"claude"})
        self.assertEqual({motor["helena"], motor["patricia"]}, {"codex"})

    def test_instrucao_tem_o_preambulo_e_a_persona(self) -> None:
        por = {a["handle"]: a["instructions"] for a in self.time["agents"]}
        self.assertIn("Lucas (Backend) da fábrica KairOS-Forge", por["lucas"])
        self.assertIn("Defensivo. Valida input.", por["lucas"])
        self.assertIn("consultivo", por["patricia"])     # allow-list sem Write/Edit
        self.assertNotIn("consultivo", por["lucas"])

    def test_skill_traz_as_references_e_o_caminho_do_projeto(self) -> None:
        entregar = next(k for k in self.time["skills"] if k["name"] == "entregar")
        self.assertIn("# Referência: references/escalacao.md", entregar["body"])
        self.assertIn(".kairos-forge/scripts/ciclo.py", entregar["body"])
        self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", entregar["body"])
        self.assertEqual(entregar["agents"], ["laura"])

    def test_canal_e_rotina_apontam_para_o_projeto(self) -> None:
        self.assertEqual(self.time["channels"][0]["name"], "loja")
        self.assertEqual(self.time["routines"][0]["where"], "#loja")

    def test_opencode_so_com_modelo(self) -> None:
        sem = {a["handle"]: a["model"] for a in tucano.montar_time()["agents"]}
        com = {a["handle"]: a["model"] for a in
               tucano.montar_time(opencode_modelo="anthropic/claude-sonnet-4-5")["agents"]}
        self.assertEqual(sem["ricardo"], "sonnet")
        self.assertEqual(com["ricardo"], "opencode:anthropic/claude-sonnet-4-5")
        self.assertEqual(com["lucas"], "sonnet")


class Validar(unittest.TestCase):
    """Cada regra do importador que deixaria passar meio time sem avisar."""

    def setUp(self) -> None:
        self.time = copy.deepcopy(tucano.montar_time("loja"))

    def problemas(self) -> str:
        return "\n".join(tucano.validar(self.time))

    def test_modelo_desconhecido_viraria_sonnet(self) -> None:
        self.time["agents"][0]["model"] = "gpt-6"
        self.assertIn("viraria sonnet", self.problemas())
        self.time["agents"][0]["model"] = "opencode:"
        self.assertIn("viraria sonnet", self.problemas())
        self.time["agents"][0]["model"] = "pi:qwen3"
        self.assertEqual(self.problemas(), "")

    def test_handle_fora_do_regex_ou_repetido(self) -> None:
        self.time["agents"][1]["handle"] = "patrícia"
        self.assertIn("handle inválido", self.problemas())
        self.time["agents"][1]["handle"] = "laura"
        self.assertIn("handle inválido ou repetido: 'laura'", self.problemas())

    def test_cor_e_esforco(self) -> None:
        self.time["agents"][0]["color"] = "orange"
        self.assertIn("cor ou esforço", self.problemas())
        self.time["agents"][0]["color"] = "violet"
        self.time["agents"][0]["effort"] = "max"
        self.assertIn("cor ou esforço", self.problemas())

    def test_skill_de_quem_nao_esta_no_time_grande_ou_com_caminho_do_plugin(self) -> None:
        k = self.time["skills"][0]
        k["agents"] = ["vinicius"]
        self.assertIn("agente que não está no time", self.problemas())
        k["agents"] = ["laura"]
        k["body"] = "x" * (tucano.TETO_RESULTADO + 1)
        self.assertIn("o ler_skill corta", self.problemas())
        k["body"] = "rode ${CLAUDE_PLUGIN_ROOT}/scripts/ciclo.py"
        self.assertIn("não reescrito", self.problemas())

    def test_canal_e_rotina(self) -> None:
        self.time["channels"][0]["members"].append("vinicius")
        self.assertIn("membro que não está no time", self.problemas())
        self.time["channels"][0]["members"].pop()
        r = self.time["routines"][0]
        r["where"] = "#outro"
        self.assertIn("agente ou canal inexistente", self.problemas())
        r["where"] = "dm"
        self.assertEqual(self.problemas(), "")
        r["schedule"] = {"days": [7], "time": "08:37"}
        self.assertIn("agenda inválida", self.problemas())
        r["schedule"] = {"days": [1], "time": "24:00"}
        self.assertIn("agenda inválida", self.problemas())

    def test_bloco_ausente_quebrado_ou_de_outra_versao(self) -> None:
        self.assertIsNone(tucano.ler_bloco("# sem bloco"))
        self.assertIsNone(tucano.ler_bloco("```json tucano-team\n{quebrado\n```"))
        self.assertTrue(tucano.validar(tucano.ler_bloco('```json tucano-team\n{"version": 2}\n```')))
        self.assertTrue(tucano.validar(None))


class Instalar(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-tucano-")
        self.projeto = Path(self._tmp.name) / "Meu Projeto"
        self.projeto.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def instalar(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            codigo = tucano.main(["instalar", "--projeto", str(self.projeto), *args])
        return codigo, out.getvalue()

    def test_copia_o_que_as_skills_citam_e_grava_o_time(self) -> None:
        codigo, saida = self.instalar("--opencode-modelo", "openai/gpt-5")
        self.assertEqual(codigo, 0)
        pasta = self.projeto / ".kairos-forge"
        for nome in ("ciclo.py", "prova.py", "qualidade.py", "guardrail.py"):
            self.assertTrue((pasta / "scripts" / nome).is_file(), nome)
        self.assertTrue((pasta / "templates" / "anti-drift.md").is_file())
        time = tucano.ler_bloco((pasta / "time-tucano.md").read_text(encoding="utf-8"))
        self.assertEqual(time["channels"][0]["name"], "meu-projeto")
        self.assertIn("claude, codex, opencode", saida)
        self.assertEqual(self.instalar()[0], 0)                  # de novo, sem erro

    def test_dry_run_nao_escreve(self) -> None:
        codigo, saida = self.instalar("--dry-run", "--canal", "loja")
        self.assertEqual(codigo, 0)
        self.assertIn("#loja", saida)
        self.assertFalse((self.projeto / ".kairos-forge").exists())

    def test_canal_de_pasta_sem_letra_cai_no_padrao(self) -> None:
        self.assertEqual(tucano.canal_de(Path("/tmp/Ágora 2")), "gora-2")
        self.assertEqual(tucano.canal_de(Path("/tmp/çã")), tucano.CANAL_PADRAO)

    def test_modelo_do_opencode_em_branco_recusa_e_nao_escreve(self) -> None:
        # Viraria `sonnet` calado na importação: melhor recusar aqui.
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            codigo = tucano.instalar(self.projeto, "loja", "   ", False)
        self.assertEqual(codigo, 1)
        self.assertIn("@ricardo: modelo 'opencode:   ' viraria sonnet", err.getvalue())
        self.assertFalse((self.projeto / ".kairos-forge").exists())


class Gerar(unittest.TestCase):
    def test_gerar_escreve_o_arquivo_versionado(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            destino = tucano.gerar(Path(d))
            self.assertEqual(destino, Path(d) / tucano.ARQUIVO_GERADO)
            self.assertEqual(tucano.validar(tucano.ler_bloco(destino.read_text(encoding="utf-8"))), [])

    def test_gerar_recusa_time_invalido(self) -> None:
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(tucano, "validar", return_value=["@x: modelo"]):
            with self.assertRaisesRegex(ValueError, "@x: modelo"):
                tucano.gerar(Path(d))
            self.assertFalse((Path(d) / tucano.ARQUIVO_GERADO).exists())

    def test_o_arquivo_do_repositorio_esta_em_dia(self) -> None:
        # O sync regenera; se alguém mudar uma persona sem rodar o sync, este teste acusa.
        versionado = (RAIZ.parent / tucano.ARQUIVO_GERADO).read_text(encoding="utf-8")
        self.assertEqual(versionado, tucano.markdown(tucano.montar_time()))

    def test_cli_gerar(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(tucano.main(["gerar"]), 0)
        self.assertIn(tucano.ARQUIVO_GERADO, out.getvalue())


if __name__ == "__main__":
    unittest.main()
