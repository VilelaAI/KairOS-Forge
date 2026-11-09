"""Testes do aviso que chega à pessoa (emenda ao ADR-0042).

O guardrail em `aviso` saía com exit 1 e o texto no stderr, e o Claude Code mostrava isso
como "Stop hook error: Failed with non-blocking status code" — o guardrail parecia quebrado
justamente quando funcionava. Agora o aviso sai como `systemMessage` com exit 0 ("Stop says:
…", conferido no Claude Code 2.1.319 e no 2.0.77), e o texto da parada em `aviso` fala com
quem o lê: a pessoa. A pasta que o projeto declara sem teste (`sem_gate`) sai da conta, e a
linha do gate vermelho mostra o começo e o fim do comando.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import guardrail  # noqa: E402
from tests.test_guardrail import Sandbox, hook  # noqa: E402

LONGO = ("bash -c 'cd /Users/pessoa/workspace/projeto-com-nome-comprido/experiments/sop-test"
         "/orchestrator-hosting && python -m pytest -q tests/unit'")


class ComTrajetoria(Sandbox):
    def setUp(self) -> None:
        super().setUp()
        # O "avisa uma vez por sessão" marca em $TMPDIR: cada teste com o seu, para a marca
        # de uma rodada anterior não calar o aviso desta.
        self._tmpdir = tempfile.TemporaryDirectory(prefix="kairos-forge-aviso-tmp-")
        self.addCleanup(self._tmpdir.cleanup)

    def gravar(self, *eventos: dict, sessao: str = "s1") -> None:
        pasta = self.raiz / ".agents" / "execucoes"
        pasta.mkdir(parents=True, exist_ok=True)
        with (pasta / "2026-11.jsonl").open("a", encoding="utf-8") as fh:
            for ev in eventos:
                fh.write(json.dumps({"t": "2026-11-09T00:00:00+00:00", "sessao": sessao, **ev}) + "\n")

    def escrita(self, arquivo: str) -> dict:
        return {"tipo": "escrita", "arquivo": arquivo, "producao": True}

    def config(self, cfg: dict) -> None:
        (self.raiz / ".agents").mkdir(exist_ok=True)
        (self.raiz / ".agents" / "guardrails.json").write_text(json.dumps(cfg), encoding="utf-8")

    def parada(self) -> tuple[int, str, str]:
        return hook("parada", {"session_id": "s1", "cwd": str(self.raiz)})

    def processo(self, modo: str, payload: dict | str) -> subprocess.CompletedProcess[str]:
        entrada = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.run([sys.executable, "-B", str(RAIZ / "guardrail.py"), modo], input=entrada,
                              capture_output=True, text=True, cwd=self.raiz,
                              env={**os.environ, "TMPDIR": self._tmpdir.name})

    def recusas(self) -> list[dict]:
        pasta = self.raiz / ".agents" / "execucoes"
        return [e for p in pasta.glob("*.jsonl") for e in map(json.loads, p.read_text().splitlines())
                if e.get("tipo") == "recusa"]


class OAvisoChegaAPessoa(ComTrajetoria):
    """Na fronteira do processo, que é o que o Claude Code lê."""

    def test_parada_em_aviso_sai_zero_com_uma_linha_system_message(self) -> None:
        self.gravar(self.escrita("src/a.py"))
        r = self.processo("parada", {"session_id": "s1", "cwd": str(self.raiz)})
        self.assertEqual((r.returncode, r.stderr), (0, ""))
        [linha] = r.stdout.splitlines()
        aviso = json.loads(linha)["systemMessage"]
        self.assertIn("o agente encerrou sem gate verde depois de escrever 1 arquivo(s)", aviso)
        self.assertIn("· src/a.py", aviso)
        self.assertTrue(aviso.endswith("Esta regra está em observação — hoje ela avisa, não bloqueia."))

    def test_parada_em_bloqueio_vai_ao_modelo_pelo_stderr(self) -> None:
        self.gravar(self.escrita("src/a.py"))
        self.config({"modos": {"parada": "bloqueio"}})
        r = self.processo("parada", {"session_id": "s1", "cwd": str(self.raiz)})
        self.assertEqual((r.returncode, r.stdout), (2, ""))
        self.assertIn("🛑 kairos-forge (guardrail): parada sem prova", r.stderr)

    def test_as_outras_classes_em_aviso_usam_o_mesmo_canal(self) -> None:
        (self.raiz / "tests").mkdir()
        (self.raiz / "tests" / "test_app.py").write_text("def test_a():\n    assert 1 == 1\n")
        subprocess.run(["git", "add", "-A"], cwd=self.raiz, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "a"],
                       cwd=self.raiz, check=True)
        r = self.processo("escrita", {"session_id": "s1", "cwd": str(self.raiz), "tool_name": "Edit",
                                      "tool_input": {"file_path": str(self.raiz / "tests" / "test_app.py"),
                                                     "old_string": "1 == 1", "new_string": "1 == 2"}})
        self.assertEqual((r.returncode, r.stderr), (0, ""))
        self.assertIn("teste existente", json.loads(r.stdout)["systemMessage"])

    def test_sem_nada_a_dizer_nada_sai(self) -> None:
        r = self.processo("parada", {"session_id": "s1", "cwd": str(self.raiz)})
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def test_falha_do_guardrail_chega_a_pessoa_menos_nos_modos_do_mod(self) -> None:
        r = self.processo("parada", "{quebrado")
        self.assertEqual((r.returncode, r.stderr), (0, ""))
        self.assertIn("o guardrail (parada) falhou e deixou passar", json.loads(r.stdout)["systemMessage"])
        # O mod lê o stdout de `faixa3` e `saida`: ali uma linha a mais quebraria a resposta.
        for modo in sorted(guardrail.MODOS_DO_MOD):
            with self.subTest(modo):
                r = self.processo(modo, "{quebrado")
                self.assertEqual((r.returncode, r.stdout), (0, ""))
                self.assertIn(f"o guardrail ({modo}) falhou e deixou passar", r.stderr)

    def test_no_cursor_a_resposta_segue_no_dialeto_dele(self) -> None:
        self.gravar(self.escrita("src/a.py"), sessao="c1")
        r = self.processo("parada", {"conversation_id": "c1", "hook_event_name": "stop",
                                     "workspace_roots": [str(self.raiz)], "loop_count": 0})
        self.assertEqual((r.returncode, r.stdout.strip(), r.stderr), (0, "{}", ""))


class OTextoDaParada(ComTrajetoria):
    def test_em_aviso_fala_com_a_pessoa(self) -> None:
        self.gravar(self.escrita("src/a.py"))
        codigo, _, aviso = self.parada()
        self.assertEqual(codigo, guardrail.AVISOU)
        self.assertIn("peça que rode o teste ou o lint do projeto em primeiro plano", aviso)
        self.assertIn("o teste rodado em background não conta", aviso)
        self.assertIn('`{"sem_gate": ["experiments/**"]}`', aviso)
        self.assertNotIn("encerre de novo", aviso)          # instrução para o modelo
        self.assertNotIn("diga ao usuário", aviso)

    def test_em_aviso_nomeia_o_gate_declarado(self) -> None:
        (self.raiz / "contextos").mkdir()
        (self.raiz / "contextos" / "testes.md").write_text(
            "# Gates\n\n- `pytest -q`\n- `ruff check .`\n- `mypy src`\n", encoding="utf-8")
        self.gravar(self.escrita("src/a.py"))
        aviso = self.parada()[2]
        self.assertIn("peça que rode `pytest -q` ou `ruff check .` (de `contextos/testes.md`)", aviso)
        self.assertNotIn("mypy", aviso)

    def test_em_bloqueio_fala_com_o_modelo(self) -> None:
        self.gravar(self.escrita("src/a.py"))
        self.config({"modos": {"parada": "bloqueio"}})
        codigo, _, motivo = self.parada()
        self.assertEqual(codigo, 2)
        self.assertIn("Em primeiro plano: o gate rodado em background não conta.", motivo)
        self.assertIn("Depois, encerre de novo.", motivo)
        self.assertNotIn("peça que rode", motivo)

    def test_o_gate_vermelho_mostra_o_comeco_e_o_fim_do_comando(self) -> None:
        self.gravar(self.escrita("src/a.py"),
                    {"tipo": "comando", "cmd": LONGO, "gate": "teste", "ok": False})
        aviso = self.parada()[2]
        [linha] = [l for l in aviso.splitlines() if l.startswith("Últimos gates")]
        self.assertIn("teste: `bash -c 'cd /Users/pessoa/w", linha)
        self.assertIn(" … ", linha)
        self.assertIn("python -m pytest -q tests/unit'`", linha)   # o que diz qual teste rodou

    def test_lista_longa_mostra_oito_e_diz_quantos_faltam(self) -> None:
        self.gravar(*[self.escrita(f"src/m{i}.py") for i in range(10)])
        aviso = self.parada()[2]
        self.assertIn("escrever 10 arquivo(s)", aviso)
        self.assertIn("· src/m7.py\n  · … e mais 2", aviso)
        self.assertNotIn("src/m8.py", aviso)

    def test_encurtar_no_meio(self) -> None:
        self.assertEqual(guardrail.encurtar_no_meio("pytest -q"), "pytest -q")
        curto = guardrail.encurtar_no_meio(LONGO)
        self.assertEqual(len(curto), 90)
        self.assertTrue(curto.startswith(LONGO[:30]) and curto.endswith(LONGO[-57:]))


class PastaSemGate(ComTrajetoria):
    """A ausência declarada que o ADR-0042 aceita: a pasta sai da conta, o resto continua."""

    def test_a_pasta_declarada_sai_da_lista_e_o_resto_fica(self) -> None:
        self.gravar(self.escrita("experiments/sop/harness.py"), self.escrita("src/b.py"))
        self.config({"sem_gate": ["experiments/**"]})
        aviso = self.parada()[2]
        self.assertIn("· src/b.py", aviso)
        self.assertNotIn("experiments/", aviso.split("Para fechar")[0])
        self.assertIn("escrever 1 arquivo(s)", aviso)

    def test_tudo_declarado_nao_avisa_nem_registra(self) -> None:
        self.gravar(self.escrita("experiments/a.py"), self.escrita("tools/gerar.py"))
        self.config({"sem_gate": ["experiments/**", "tools/*.py"]})
        self.assertEqual(self.parada(), (0, "", ""))
        self.assertEqual(self.recusas(), [])

    def test_vale_tambem_em_bloqueio(self) -> None:
        self.gravar(self.escrita("experiments/a.py"))
        self.config({"sem_gate": ["experiments/**"], "modos": {"parada": "bloqueio"}})
        self.assertEqual(self.parada()[0], 0)

    def test_config_mal_formada_e_ignorada(self) -> None:
        self.gravar(self.escrita("experiments/a.py"))
        for valor in ("experiments/**", [1, "", None], {"experiments/**": True}):
            with self.subTest(valor=valor):
                self.config({"sem_gate": valor})
                codigo, _, aviso = self.parada()
                self.assertEqual(codigo, guardrail.AVISOU)
                self.assertIn("· experiments/a.py", aviso)


if __name__ == "__main__":
    unittest.main()
