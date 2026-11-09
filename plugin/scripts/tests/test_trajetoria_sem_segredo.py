"""Testes da trajetória sem segredo (emenda ao ADR-0056).

O que vai para `.agents/execucoes/` passa pela regra do `segredos.py`, a mesma da saída de
ferramenta: o comando de cada gate que o `execucao.py` grava e tudo o que o `guardrail.py`
grava (recusa, pausa, erro). A regra antiga do `execucao.py` deixava passar `DB_PASSWORD=`,
a senha na URL e as chaves com prefixo, e apagava hash de commit e nome longo de teste, o
que fazia o `corroborar` não achar o gate que rodou.

Os segredos de amostra são montados na hora, para o scanner de segurança não os confundir
com um segredo de verdade.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import execucao  # noqa: E402
import guardrail  # noqa: E402
import segredos  # noqa: E402
import telemetria  # noqa: E402
from tests.test_segredo import OCULTA, PASSA  # noqa: E402

SENHA = "S3nh4" + "Forte99"
GH = "ghp_" + "b" * 36
BEARER = "abcd1234" + "efgh5678ijkl"
LONGO = "test_um_nome_de_teste_bem_comprido_com_mais_de_quarenta_letras"
SHA = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"


def texto_de(amostra) -> str:
    return amostra[0] if isinstance(amostra, tuple) else amostra


class ARegraNova(unittest.TestCase):
    """Os três padrões que o comando trouxe valem também para a saída de ferramenta."""

    def test_bearer_flag_e_usuario_senha_viram_marca(self) -> None:
        for texto, tipo, valor in (
                (f'curl -H "Authorization: Bearer {BEARER}" https://api', "token Bearer", BEARER),
                (f"mysql --password {SENHA} -h db", "valor de flag secreta", SENHA),
                (f"psql --token '{SENHA}'", "valor de flag secreta", SENHA),
                (f"curl -u admin:{SENHA} https://api", "senha em usuário:senha", SENHA)):
            with self.subTest(texto):
                oculto, tipos = segredos.ocultar_segredos(texto)
                self.assertNotIn(valor, oculto)
                self.assertEqual(tipos, [tipo])

    def test_o_que_parece_mas_nao_e_passa(self) -> None:
        for texto in ("Bearer authentication is required", "Bearer ${TOKEN}",
                      "docker login --password-stdin", "git push -u origin main",
                      "docker run -u 1000:1000 img", "gh --token-file ~/.tok",
                      "mysql --password $DB_PASS", f"python -m unittest tests.x.{LONGO}",
                      f"git show {SHA}", "gh auth status", "mkdir -p build"):
            with self.subTest(texto):
                self.assertEqual(segredos.ocultar_segredos(texto), (texto, []))


class ComandoGravadoPeloExecucao(unittest.TestCase):
    def ev(self, comando: str) -> dict:
        return execucao.ev_ferramenta({"tool_name": "Bash", "tool_input": {"command": comando},
                                       "tool_response": {"stdout": "1 passed", "stderr": ""}})

    def test_cada_formato_de_segredo_sai_do_comando(self) -> None:
        for amostra in OCULTA:
            texto = texto_de(amostra)
            with self.subTest(texto[:40]):
                cmd = self.ev(f"echo {texto}")["cmd"]
                self.assertEqual(cmd, f"echo {segredos.ocultar(texto)}"[:execucao.LIMITE_CMD])
                self.assertIn("«segredo ocultado pelo kairos-forge:", cmd)

    def test_o_que_nao_e_segredo_fica_como_veio(self) -> None:
        for comando in [f"echo {texto_de(a)}" for a in PASSA] + [
                f"python -m unittest tests.test_x.Classe.{LONGO}", f"git show {SHA}",
                "gh auth status", "mkdir -p build"]:
            with self.subTest(comando[:50]):
                self.assertEqual(self.ev(comando)["cmd"], comando[:execucao.LIMITE_CMD])

    def test_o_gate_sai_do_comando_e_nao_da_gravacao(self) -> None:
        ev = self.ev(f"DATABASE_URL=postgres://app:{SENHA}@db/x pytest -q")
        self.assertNotIn(SENHA, ev["cmd"])
        self.assertEqual(ev["gate"], execucao.classificar_gate("pytest -q"))
        self.assertTrue(ev["ok"])

    def test_sem_a_regra_o_comando_nao_e_gravado_mas_o_gate_e(self) -> None:
        with mock.patch.object(execucao, "ocultar", None):
            ev = self.ev(f"DB_PASSWORD={SENHA} pytest -q")
        self.assertEqual(ev["cmd"], execucao.NAO_GRAVADO)
        self.assertEqual(ev["gate"], execucao.classificar_gate("pytest -q"))

    def test_pelo_hook_nada_do_segredo_chega_ao_disco(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            for comando in (f"DB_PASSWORD={SENHA} pytest -q", f"git push https://x:{GH}@github.com/o/r",
                            f'curl -H "Authorization: Bearer {BEARER}" https://api'):
                payload = {"hook_event_name": "PostToolUse", "session_id": "s1", "cwd": tmp,
                           "tool_name": "Bash", "tool_input": {"command": comando},
                           "tool_response": {"stdout": "ok", "stderr": ""}}
                subprocess.run([sys.executable, "-B", str(RAIZ / "execucao.py"), "ferramenta"],
                               input=json.dumps(payload), text=True, check=True, cwd=tmp)
            gravado = "".join(p.read_text(encoding="utf-8")
                              for p in Path(tmp, ".agents", "execucoes").glob("*.jsonl"))
            self.assertEqual(gravado.count('"tipo": "comando"'), 3)
            for valor in (SENHA, GH, BEARER):
                self.assertNotIn(valor, gravado)
            self.assertFalse(list(Path(RAIZ).glob("__pycache__/segredos*")))   # nem bytecode


class OQueOGuardrailGrava(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-trajetoria-")
        self.raiz = Path(self._tmp.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.raiz)], check=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def gravado(self) -> list[dict]:
        return [json.loads(l) for p in (self.raiz / ".agents" / "execucoes").glob("*.jsonl")
                for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

    def test_todo_texto_do_evento_passa_pela_regra_e_o_resto_fica(self) -> None:
        guardrail.registrar_evento(self.raiz, {"tipo": "pausa", "alvo": f"PGPASSWORD={SENHA} psql prod",
                                               "regra": f"Bearer {BEARER}", "quantos": 2,
                                               "specs": ["SPEC-001"]})
        [ev] = self.gravado()
        self.assertNotIn(SENHA, json.dumps(ev))
        self.assertNotIn(BEARER, json.dumps(ev))
        self.assertEqual((ev["tipo"], ev["quantos"], ev["specs"]), ("pausa", 2, ["SPEC-001"]))
        self.assertIn("psql prod", ev["alvo"])

    def test_a_recusa_de_comando_pelo_hook(self) -> None:
        cwd = os.getcwd()
        os.chdir(self.raiz)
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                guardrail._EDITOR["cursor"] = False
                codigo = guardrail.MODOS["comando"](guardrail.normalizar_payload(
                    {"cwd": str(self.raiz), "tool_name": "Bash",
                     "tool_input": {"command": f"rm -rf / ; export GITHUB_TOKEN={GH}"}}))
        finally:
            os.chdir(cwd)
        self.assertEqual(codigo, 2)
        [ev] = [e for e in self.gravado() if e["tipo"] == "recusa"]
        self.assertIn("rm -rf /", ev["alvo"])
        self.assertNotIn(GH, ev["alvo"])

    def test_o_erro_do_guardrail_sem_o_segredo_no_disco_e_no_aviso(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            guardrail.falhar_aberto("comando", {"cwd": str(self.raiz)},
                                    ValueError(f"falhou em DB_PASSWORD={SENHA}"))
        [ev] = self.gravado()
        self.assertEqual(ev["tipo"], "guardrail_erro")
        self.assertNotIn(SENHA, ev["erro"])
        aviso = json.loads(out.getvalue())["systemMessage"]
        self.assertIn("falhou em DB_PASSWORD=", aviso)
        self.assertNotIn(SENHA, aviso + err.getvalue())
        self.assertIn("ValueError: falhou em DB_PASSWORD=", ev["erro"])


class CorroborarComAMesmaRegra(unittest.TestCase):
    def eventos(self, *comandos: str) -> list[dict]:
        return [{"t": "x", "sessao": "s", **execucao.ev_ferramenta(
            {"tool_name": "Bash", "tool_input": {"command": c},
             "tool_response": {"stdout": "OK", "stderr": ""}})} for c in comandos]

    def test_o_nome_longo_de_teste_e_achado(self) -> None:
        alegado = f"python -m unittest tests.test_x.Classe.{LONGO}"
        r = telemetria.corroborar(self.eventos(alegado), alegado)
        self.assertEqual(r["veredicto"], "corroborado")

    def test_falha_indeterminado_e_comando_vazio(self) -> None:
        falhou = {"t": "x", "tipo": "comando", "cmd": "pytest -q", "ok": False}
        sem_saida = {**falhou, "ok": None}
        vazio = {"t": "x", "tipo": "comando", "cmd": "", "ok": True}
        self.assertEqual(telemetria.corroborar([vazio, falhou], "pytest -q")["veredicto"],
                         "corroborado_com_falha")
        self.assertEqual(telemetria.corroborar([falhou, sem_saida], "pytest -q")["veredicto"],
                         "corroborado_indeterminado")
        r = telemetria.corroborar([vazio, {"tipo": "escrita", "arquivo": "a.py"}], "pytest -q")
        self.assertEqual((r["veredicto"], r["total"]), ("nao_corroborado", 0))

    def test_o_alegado_com_segredo_bate_com_o_gravado(self) -> None:
        alegado = f"DB_PASSWORD={SENHA} pytest -q"
        r = telemetria.corroborar(self.eventos(alegado), alegado)
        self.assertEqual(r["veredicto"], "corroborado")
        self.assertNotIn(SENHA, json.dumps(r))


class OModuloVaiJunto(unittest.TestCase):
    """Todo módulo local que um script de suporte importa vai para o Cursor e o Tucano junto."""

    def test_os_imports_locais_estao_na_lista_do_sync(self) -> None:
        spec = importlib.util.spec_from_file_location("sync_multi_cli", RAIZ / "sync-multi-cli.py")
        sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sync)
        lista = set(sync.SCRIPTS_DE_SUPORTE)
        locais = {p.stem for p in RAIZ.glob("*.py")}
        for nome in sorted(lista):
            arvore = ast.parse((RAIZ / nome).read_text(encoding="utf-8"))
            importados = {n.module for n in ast.walk(arvore) if isinstance(n, ast.ImportFrom) and n.module} | {
                a.name for n in ast.walk(arvore) if isinstance(n, ast.Import) for a in n.names}
            for modulo in sorted(importados & locais):
                with self.subTest(script=nome, importa=modulo):
                    self.assertIn(f"{modulo}.py", lista)
        self.assertIn("segredos.py", lista)


if __name__ == "__main__":
    unittest.main()
