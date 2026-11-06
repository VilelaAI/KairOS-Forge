"""Testes do runner do eval de ponta a ponta — sem modelo, sem chave, sem custo.

Rode: python3 -m unittest discover -s evals/tarefas-fabrica -p 'test_*.py'
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rodar  # noqa: E402


def calado(funcao, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        codigo = funcao(*args)
    return codigo, out.getvalue()


def stream(*eventos: dict) -> list[str]:
    return [json.dumps(e) for e in eventos]


RESULTADO = {"type": "result", "subtype": "success", "num_turns": 7, "duration_ms": 12500,
             "result": "Qual a moeda de cada cliente e qual fonte de câmbio devo usar?",
             "usage": {"input_tokens": 120, "cache_creation_input_tokens": 3000,
                       "cache_read_input_tokens": 50000, "output_tokens": 800}}


class TarefasReais(unittest.TestCase):
    def test_todas_distinguem_base_solucao_e_erradas(self) -> None:
        codigo, saida = calado(rodar.main, ["validar"])
        self.assertEqual(codigo, 0, saida)
        n = len(rodar.carregar_tarefas())
        self.assertGreaterEqual(n, 11)              # nenhuma tarefa some em silêncio
        self.assertIn(f"{n} de {n}", saida)

    def test_todas_bem_formadas(self) -> None:
        for t in rodar.carregar_tarefas():
            self.assertEqual(rodar.problemas_da_tarefa(t), [], t["id"])


class LerStream(unittest.TestCase):
    def test_rota_skills_tokens_e_resposta(self) -> None:
        s = rodar.ler_stream(stream(
            {"type": "system", "subtype": "init"},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Skill", "input": {"skill": "kairos-forge:revisar"}},
                {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "helena-security"}},
                {"type": "tool_use", "name": "Task", "input": {"subagent_type": "patricia-qa"}},
                {"type": "text", "text": "ok"}]}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "python3 -m unittest"}}]}},
            RESULTADO) + ["linha que não é json", "[1, 2]"])
        self.assertEqual(s["rota"], ["helena-security", "patricia-qa"])
        self.assertEqual(s["skills"], ["kairos-forge:revisar"])
        self.assertEqual(s["ferramentas"], {"Skill": 1, "Agent": 1, "Task": 1, "Bash": 1})
        self.assertEqual(rodar.novos(s["tokens"]), 3920)
        self.assertEqual((s["turnos"], s["duracao_s"], s["erro"]), (7, 12.5, None))
        self.assertIn("câmbio", s["resposta"])

    def test_sessao_sem_result_e_erro(self) -> None:
        self.assertEqual(rodar.ler_stream([])["erro"], "sessão sem evento result")

    def test_result_com_erro(self) -> None:
        s = rodar.ler_stream(stream({**RESULTADO, "subtype": "error_max_turns", "is_error": True}))
        self.assertEqual(s["erro"], "error_max_turns")


class Checagens(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        (self.ws / "vendas").mkdir()
        (self.ws / "vendas" / "a.py").write_text("x = 1\n", encoding="utf-8")
        rodar.git(self.ws, "init", "-q", "-b", "main")
        rodar.git(self.ws, "add", "-A")
        rodar.git(self.ws, "commit", "-qm", "base")
        self.ref = rodar.git(self.ws, "rev-parse", "HEAD").stdout.strip()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def checar(self, c: dict, resposta: str = "") -> bool:
        return rodar.checar(c, self.ws, self.ref, resposta)[0]

    def test_intocado_pega_mudanca_commit_e_arquivo_novo(self) -> None:
        c = {"tipo": "intocado", "caminhos": ["vendas/"]}
        self.assertTrue(self.checar(c))
        self.assertEqual(rodar.checar(c, self.ws, self.ref, ""), (True, "intocado"))
        (self.ws / "vendas" / "novo.py").write_text("y = 2\n", encoding="utf-8")
        self.assertEqual(rodar.checar(c, self.ws, self.ref, ""), (False, "mudou: ['vendas/novo.py']"))
        rodar.git(self.ws, "add", "-A")
        rodar.git(self.ws, "commit", "-qm", "muda")
        self.assertFalse(self.checar(c))

    def test_contrato_com_campos_e_minimos(self) -> None:
        pasta = self.ws / "docs" / "specs" / "criticas"
        pasta.mkdir(parents=True)
        (pasta / "CRITICA-SPEC-001-2026-11-03.md").write_text(
            '```kairos-critica\n{"veredicto": "bloqueado", "achados": 1, "criticado_por": '
            '["Joana", "Patrícia"], "examinado": ["requisitos"]}\n```\n', encoding="utf-8")
        base = {"tipo": "contrato", "glob": "docs/specs/criticas/CRITICA-*.md", "leitor": "criticar"}
        self.assertTrue(self.checar(base))
        self.assertTrue(self.checar({**base, "campos": {"veredicto": "bloqueado"}}))
        self.assertFalse(self.checar({**base, "campos": {"veredicto": "aprovado"}}))
        self.assertFalse(self.checar({**base, "minimos": {"achados": 2}}))
        self.assertEqual(rodar.checar({**base, "campos": {"veredicto": "aprovado"}}, self.ws, self.ref, ""),
                         (False, "CRITICA-SPEC-001-2026-11-03.md · difere: ['veredicto']"))
        self.assertEqual(rodar.checar(base, self.ws, self.ref, ""), (True, "CRITICA-SPEC-001-2026-11-03.md"))
        self.assertFalse(self.checar({**base, "glob": "docs/nada/*.md"}))

    def test_contrato_invalido_reprova(self) -> None:
        pasta = self.ws / "docs" / "specs" / "revisoes"
        pasta.mkdir(parents=True)
        (pasta / "REVISAO-x.md").write_text('```kairos-revisao\n{"veredicto": "aprovado"}\n```\n',
                                            encoding="utf-8")
        self.assertFalse(self.checar({"tipo": "contrato", "glob": "docs/specs/revisoes/*.md",
                                      "leitor": "revisar"}))

    def test_arquivo_exige_todas_as_regex_no_mesmo_arquivo(self) -> None:
        (self.ws / "r1.md").write_text("servidor.py\n", encoding="utf-8")
        (self.ws / "r2.md").write_text("path traversal\n", encoding="utf-8")
        c = {"tipo": "arquivo", "glob": "r*.md", "regex": ["servidor\\.py", "travers"]}
        self.assertFalse(self.checar(c))
        (self.ws / "r3.md").write_text("servidor.py tem path TRAVERSAL\n", encoding="utf-8")
        self.assertTrue(self.checar(c))

    def test_ciclo_e_resposta(self) -> None:
        self.assertFalse(self.checar({"tipo": "ciclo", "estados": ["pronto_para_pr"]}))
        (self.ws / ".agents" / "ciclo").mkdir(parents=True)
        (self.ws / ".agents" / "ciclo" / "SPEC-001.json").write_text('{"estado": "pronto_para_pr"}',
                                                                     encoding="utf-8")
        self.assertTrue(self.checar({"tipo": "ciclo", "estados": ["pronto_para_pr"]}))
        c = {"tipo": "resposta", "regex": ["\\?", "câmbio"]}
        self.assertTrue(self.checar(c, "Qual fonte de câmbio?"))
        self.assertFalse(self.checar(c, "Converti tudo para dólar."))


class Bloqueios(unittest.TestCase):
    """A checagem que separa quem acha o defeito de quem bloqueia por qualquer coisa."""

    RELATORIO = textwrap.dedent("""\
        # Revisão pré-PR — feature/x

        ## 🔴 Crítico (qualquer revisor) → bloqueia merge
        - [Helena] R1 · vendas/nomes.py:7 — caminho absoluto passa pelo validador.
        - [Helena] R2 · vendas/compactar.py:14 — subprocess · descartado: lista sem shell, com `--`.

        ## 🟡 Médio
        - [Patrícia] vendas/compactar.py — falta teste do gzip.

        | # | Onde | Achado | Severidade |
        |---|---|---|---|
        | 1 | REG-02 | critério de um sentido só | 🔴 |
        | 2 | REG-04 | bem especificado | 🔵 |

        ```kairos-revisao
        {"veredicto": "bloqueado", "examinado": ["vendas/compactar.py (Helena)", "REG-04"]}
        ```
        """)

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        (self.ws / "REVISAO-x.md").write_text(self.RELATORIO, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def checar(self, **c) -> tuple[bool, str]:
        return rodar.checar({"tipo": "bloqueios", "glob": "REVISAO-*.md", **c}, self.ws, "", "")

    def test_so_as_linhas_que_bloqueiam_contam(self) -> None:
        linhas = rodar.linhas_que_bloqueiam(self.RELATORIO)
        self.assertEqual(len(linhas), 2)
        self.assertIn("nomes.py", linhas[0])
        self.assertIn("REG-02", linhas[1])

    def test_achado_antes_de_qualquer_titulo_so_conta_com_o_vermelho(self) -> None:
        self.assertEqual(rodar.linhas_que_bloqueiam("- [Helena] nota sem severidade\n"), [])
        self.assertEqual(rodar.linhas_que_bloqueiam("- [Helena] 🔴 R1 · a.py\n"), ["- [Helena] 🔴 R1 · a.py"])

    def test_exige_e_proibido(self) -> None:
        self.assertEqual(self.checar(exige=["nomes\\.py", "absolut", "REG-02"],
                                     proibido=["compactar", "REG-04", "subprocess"]),
                         (True, "2 bloqueio(s), todos no lugar"))
        ok, detalhe = self.checar(exige=["servidor\\.py"])
        self.assertFalse(ok)
        self.assertIn("não bloqueou: ['servidor\\\\.py']", detalhe)
        ok, detalhe = self.checar(proibido=["caminho absoluto"])
        self.assertFalse(ok)
        self.assertIn("bloqueou à toa", detalhe)

    def test_sem_relatorio_reprova(self) -> None:
        ok, detalhe = rodar.checar({"tipo": "bloqueios", "glob": "nada/*.md"}, self.ws, "", "")
        self.assertEqual((ok, detalhe), (False, "nenhum nada/*.md"))

    def test_toda_checagem_declarada_tem_quem_a_faca(self) -> None:
        self.assertEqual(set(rodar.CHECAGENS), set(rodar.CHECADORES))
        self.assertEqual(rodar.checar({"tipo": "outra"}, self.ws, "", ""),
                         (False, "checagem desconhecida: outra"))

    def test_campos_aceita_uma_lista_de_valores(self) -> None:
        self.assertTrue(rodar._bate("aprovado", ["aprovado", "aprovado_com_ressalvas"]))
        self.assertFalse(rodar._bate("bloqueado", ["aprovado", "aprovado_com_ressalvas"]))
        self.assertTrue(rodar._bate("bloqueado", "bloqueado"))
        self.assertFalse(rodar._bate(["bloqueado"], "bloqueado"))


class Mudanca(unittest.TestCase):
    def test_branch_e_mensagem_vem_da_tarefa(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as pasta:
            (Path(pasta) / "mudanca").mkdir()
            (Path(pasta) / "mudanca" / "novo.txt").write_text("x", encoding="utf-8")
            for mudanca, branch, mensagem in (
                    (True, "feature/download", "feat: download dos relatórios"),
                    ({"branch": "feature/media", "mensagem": "feat: média"}, "feature/media", "feat: média")):
                ws = Path(tmp) / branch.replace("/", "-")
                ws.mkdir()
                rodar.preparar({"pasta": Path(pasta), "mudanca": mudanca}, ws)
                self.assertEqual(rodar.git(ws, "branch", "--show-current").stdout.strip(), branch)
                self.assertEqual(rodar.git(ws, "log", "-1", "--format=%s").stdout.strip(), mensagem)


class SolucaoErrada(unittest.TestCase):
    def test_oraculo_frouxo_e_denunciado(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            comum = raiz / "_comum"
            (comum / "m").mkdir(parents=True)
            (comum / "m" / "__init__.py").write_text("", encoding="utf-8")
            (comum / "m" / "f.py").write_text("def dobro(x):\n    return x\n", encoding="utf-8")
            pasta = raiz / "t99-dobro"
            for rel, texto in {
                "solucao/m/f.py": "def dobro(x):\n    return 2 * x\n",
                "erradas/soma/m/f.py": "def dobro(x):\n    return x + 2\n",
                "oraculo/test_o.py": textwrap.dedent("""
                    import unittest
                    from m.f import dobro
                    class O(unittest.TestCase):
                        def test(self):
                            self.assertEqual(dobro(2), 4)   # frouxo: x + 2 também dá 4
                    """),
            }.items():
                (pasta / rel).parent.mkdir(parents=True, exist_ok=True)
                (pasta / rel).write_text(texto, encoding="utf-8")
            t = {"id": "t99-dobro", "tipo": "corrigir", "prompt": "dobra", "oraculo": True,
                 "checagens": [], "pasta": pasta}
            with mock.patch.object(rodar, "COMUM", comum):
                self.assertEqual(rodar.erradas_que_passam(t), ["soma"])
                (pasta / "oraculo" / "test_o.py").write_text(textwrap.dedent("""
                    import unittest
                    from m.f import dobro
                    class O(unittest.TestCase):
                        def test(self):
                            self.assertEqual(dobro(2), 4)
                            self.assertEqual(dobro(5), 10)
                    """), encoding="utf-8")
                self.assertEqual(rodar.erradas_que_passam(t), [])


FALSO_CLAUDE = """#!/usr/bin/env python3
import json, sys
print(json.dumps({"type": "assistant", "message": {"content": [
    {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "laura-tech-lead"}}]}}))
print(json.dumps(%s))
"""


class RodadaComClaudeFalso(unittest.TestCase):
    def test_grava_resultado_trace_e_rodada(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            falso = Path(tmp) / "claude-falso"
            falso.write_text(FALSO_CLAUDE % json.dumps(RESULTADO), encoding="utf-8")
            falso.chmod(falso.stat().st_mode | stat.S_IEXEC)
            with mock.patch.object(rodar, "RESULTADOS", Path(tmp) / "resultados"):
                codigo, saida = calado(rodar.main, [
                    "rodar", "--variante", "teste", "--reps", "1", "--tarefas", "t06",
                    "--claude", str(falso)])
                self.assertEqual(codigo, 0, saida)
                linha = json.loads((Path(tmp) / "resultados/teste/resultados.jsonl").read_text())
                rodada = json.loads((Path(tmp) / "resultados/teste/rodada.json").read_text())
                self.assertTrue((Path(tmp) / "resultados/teste/traces/t06-perguntar-moeda_rep0.jsonl").is_file())
                # Repetir a mesma variante é recusado: mais reps viram outra variante.
                self.assertEqual(calado(rodar.main, ["rodar", "--variante", "teste", "--tarefas", "t06",
                                                     "--claude", str(falso)])[0], 1)
        self.assertTrue(linha["aprovado"], linha)
        self.assertEqual(linha["rota"], ["laura-tech-lead"])
        self.assertEqual(rodar.novos(linha["tokens"]), 3920)
        self.assertEqual(rodada["tarefas"], ["t06-perguntar-moeda"])

    def test_sem_claude_nao_roda(self) -> None:
        codigo, _ = calado(rodar.main, ["rodar", "--variante", "x", "--claude", "nao-existe-claude"])
        self.assertEqual(codigo, 1)


def linha(tarefa: str, rep: int, aprovado: bool, rota: list[str], saida: int = 100) -> str:
    return json.dumps({"tarefa": tarefa, "rep": rep, "aprovado": aprovado, "rota": rota,
                       "tokens": {"entrada": 0, "cache_escrita": 0, "cache_leitura": 10, "saida": saida},
                       "duracao_s": 10.0, "erro": None})


T1, T2 = "t01-csv-sujo", "t02-entregar-exportar-json"


class Comparar(unittest.TestCase):
    def test_piorou_melhorou_e_rota(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(rodar, "RESULTADOS", Path(tmp)):
            for variante, linhas in {
                "base": [linha(T1, 0, True, []), linha(T1, 1, True, []),
                         linha(T2, 0, False, ["helena-security"]), linha(T2, 1, False, ["helena-security"])],
                "v1": [linha(T1, 0, True, []), linha(T1, 1, False, []),
                       linha(T2, 0, True, []), linha(T2, 1, False, [])],
            }.items():
                (Path(tmp) / variante).mkdir()
                (Path(tmp) / variante / "resultados.jsonl").write_text("\n".join(linhas) + "\n")
            r = rodar.comparar(rodar.carregar_resultados("base"), rodar.carregar_resultados("v1"))
            self.assertEqual((r["piorou"], r["melhorou"], r["rota_mudou"]), ([T1], [T2], [T2]))
            codigo, saida = calado(rodar.main, ["comparar", "base", "v1"])
            self.assertEqual(codigo, 0)
            self.assertIn(f"Piorou: {T1}", saida)
            codigo, saida = calado(rodar.main, ["estimar", "base", "--reps", "3", "--tarefas", "t01"])
            self.assertIn("300 tokens novos", saida)


if __name__ == "__main__":
    unittest.main()
