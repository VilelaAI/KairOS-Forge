"""Testes da alegação sem prova (ADR-0058).

A resposta que afirma gate verde ("os testes passam", "o build passou", "tudo verde") é
conferida contra a trajetória no `Stop`. Volta uma vez ao modelo quando o registro a
desmente: nenhum gate daquele tipo depois da última escrita, o último vermelho, ou ainda
rodando em background. E, quando a pessoa pergunta se falta algo, o modelo recebe a
conferência item a item (modo `conferir`, no `UserPromptSubmit`).

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
import execucao  # noqa: E402
import guardrail  # noqa: E402
from tests.test_guardrail import Sandbox, hook  # noqa: E402


class Deteccao(unittest.TestCase):
    def test_o_que_e_afirmacao_de_gate_verde(self) -> None:
        for texto, tipos in (
                ("Pronto, os testes passam.", ["teste"]),
                ("Feito: 12 testes passando (pytest).", ["teste"]),
                ("Rodei a suíte e está tudo verde.", ["teste", None]),
                ("All tests pass now.", ["teste"]),
                ("O lint está limpo.", ["lint"]),
                ("mypy sem erros.", ["tipos"]),
                ("O build passou e o lint está limpo.", ["lint", "build"]),
                ("Compila sem erros.", ["build"]),
                ("Tudo verde por aqui.", [None])):
            with self.subTest(texto):
                self.assertEqual([t for t, _ in guardrail.alegacoes(texto)], tipos)

    def test_o_que_nao_e(self) -> None:
        for texto in ("Os testes não passam ainda.", "Os testes passam?", "Quer que eu rode os testes?",
                      "O CI passou e os testes passam no GitHub Actions.", "Antes os testes passavam.",
                      "Rodei `pytest -q` e deu `3 passed`.", "```\n5 passed\n```\nPronto.",
                      "Se os testes passarem, subo.", "Os testes devem passar.", "Nem o build passou.",
                      "Corrigi o login.", ""):
            with self.subTest(texto):
                self.assertEqual(guardrail.alegacoes(texto), [])

    def test_a_frase_vem_inteira_e_curta(self) -> None:
        [(_, frase)] = guardrail.alegacoes("Mexi em três arquivos.\nOs testes passam agora.")
        self.assertEqual(frase, "Os testes passam agora.")
        [(_, longa)] = guardrail.alegacoes("Os testes passam " + "e mais " * 60 + ".")
        self.assertEqual(len(longa), 160)


def escrita(arquivo: str = "src/a.py") -> dict:
    return {"tipo": "escrita", "arquivo": arquivo, "producao": True}


def gate(cmd: str, ok: bool | None, tarefa: str | None = None) -> dict:
    ev = {"tipo": "comando", "cmd": cmd, "gate": execucao.classificar_gate(cmd), "ok": ok}
    return {**ev, "tarefa": tarefa} if tarefa else ev


class Prova(unittest.TestCase):
    def falta(self, eventos: list[dict], tipo: str | None = "teste", em_curso: set[str] | None = None,
              sem_gate: list[str] | None = None) -> str | None:
        return guardrail.falta_prova(eventos, tipo, em_curso or set(), sem_gate or [])

    def test_sem_gate_nenhum(self) -> None:
        self.assertEqual(self.falta([]), "nenhum rodou nesta sessão")
        self.assertEqual(self.falta([escrita()]), "nenhum rodou depois da última escrita")
        self.assertEqual(self.falta([gate("pytest -q", True), escrita()]),
                         "nenhum rodou depois da última escrita")

    def test_verde_depois_da_escrita_sustenta(self) -> None:
        self.assertIsNone(self.falta([escrita(), gate("pytest -q", True)]))
        self.assertIsNone(self.falta([gate("python3 -m unittest discover", True)]))   # sem escrita

    def test_o_ultimo_vermelho_desmente(self) -> None:
        falta = self.falta([escrita(), gate("pytest -q", True), gate("pytest -q -k login", False)])
        self.assertEqual(falta, "o último rodou vermelho: `pytest -q -k login`")

    def test_o_gate_de_outro_tipo_nao_prova(self) -> None:
        self.assertEqual(self.falta([escrita(), gate("ruff check .", True)]),
                         "nenhum rodou depois da última escrita")
        self.assertIsNone(self.falta([escrita(), gate("ruff check .", True)], "lint"))

    def test_tudo_verde_pede_o_ultimo_de_cada_tipo_verde(self) -> None:
        self.assertIsNone(self.falta([escrita(), gate("pytest -q", True), gate("ruff check .", True)], None))
        self.assertIn("vermelho", self.falta([escrita(), gate("pytest -q", True),
                                              gate("ruff check .", False)], None))

    def test_sem_como_afirmar_nao_desmente(self) -> None:
        self.assertIsNone(self.falta([escrita(), gate("pytest -q", None)]))

    def test_ainda_rodando_em_background(self) -> None:
        self.assertEqual(self.falta([escrita(), gate("pytest -q", None, "t1")], em_curso={"t1"}),
                         "ainda roda em background: `pytest -q`")

    def test_escrita_em_pasta_sem_gate_nao_move_a_referencia(self) -> None:
        eventos = [escrita(), gate("pytest -q", True), escrita("experiments/poc.py")]
        self.assertIsNone(self.falta(eventos, sem_gate=["experiments/**"]))
        self.assertEqual(self.falta(eventos), "nenhum rodou depois da última escrita")


class NaParada(Sandbox):
    def gravar(self, *eventos: dict) -> None:
        pasta = self.raiz / ".agents" / "execucoes"
        pasta.mkdir(parents=True, exist_ok=True)
        with (pasta / "2026-11.jsonl").open("a", encoding="utf-8") as fh:
            for ev in eventos:
                fh.write(json.dumps({"t": "2026-11-18T00:00:00+00:00", "sessao": "s1", **ev}) + "\n")

    def config(self, cfg: dict) -> None:
        (self.raiz / ".agents").mkdir(exist_ok=True)
        (self.raiz / ".agents" / "guardrails.json").write_text(json.dumps(cfg), encoding="utf-8")

    def parada(self, resposta: str | None, **extra) -> tuple[int, str, str]:
        payload = {"session_id": "s1", "cwd": str(self.raiz), "stop_hook_active": False, **extra}
        if resposta is not None:
            payload["last_assistant_message"] = resposta
        return hook("parada", payload)

    def recusas(self) -> list[dict]:
        pasta = self.raiz / ".agents" / "execucoes"
        return [e for p in pasta.glob("*.jsonl") for e in map(json.loads, p.read_text().splitlines())
                if e.get("tipo") == "recusa"]

    def test_afirmou_sem_rodar_volta_ao_modelo(self) -> None:
        self.gravar(escrita())
        codigo, out, motivo = self.parada("Pronto, os testes passam.")
        self.assertEqual((codigo, out), (2, ""))
        self.assertIn("alegação sem prova — a resposta diz “Pronto, os testes passam.”", motivo)
        self.assertIn("nenhum rodou depois da última escrita", motivo)
        self.assertIn("diga isso em vez de afirmar que passa", motivo)
        [recusa] = self.recusas()
        self.assertEqual((recusa["classe"], recusa["modo"], recusa["alvo"]),
                         ("alegacao", "bloqueio", "Pronto, os testes passam."))

    def test_afirmou_com_prova_passa_quieto(self) -> None:
        self.gravar(escrita(), gate("pytest -q", True))
        self.assertEqual(self.parada("Pronto, os testes passam."), (0, "", ""))
        self.assertEqual(self.recusas(), [])

    def test_em_aviso_fala_com_a_pessoa(self) -> None:
        self.gravar(escrita(), gate("pytest -q", False))
        self.config({"modos": {"alegacao": "aviso"}})
        codigo, _, aviso = self.parada("Os testes passam.")
        self.assertEqual(codigo, guardrail.AVISOU)
        self.assertIn("o agente afirmou “Os testes passam.” sem prova na trajetória: o último rodou "
                      "vermelho: `pytest -q`", aviso)
        self.assertIn("Peça que rode o gate", aviso)

    def test_nunca_duas_vezes_na_mesma_parada(self) -> None:
        self.gravar(escrita())
        self.assertEqual(self.parada("Os testes passam.", stop_hook_active=True), (0, "", ""))

    def test_sem_afirmacao_a_parada_segue_como_antes(self) -> None:
        self.gravar(escrita())
        codigo, _, aviso = self.parada("Mudei o arquivo; quer que eu rode os testes?")
        self.assertEqual(codigo, guardrail.AVISOU)                # o aviso da parada, não a alegação
        self.assertIn("o agente encerrou sem gate verde", aviso)
        self.assertEqual([r["classe"] for r in self.recusas()], ["parada"])

    def test_o_verde_em_background_sustenta(self) -> None:
        self.gravar(escrita(), gate("pytest -q", None, "t1"))
        transcript = self.raiz / "t.jsonl"
        transcript.write_text(json.dumps({
            "type": "user", "origin": {"kind": "task-notification"},
            "message": {"content": "<task-notification><task-id>t1</task-id><status>completed</status>"
                                   "<summary>Background command \"t\" completed (exit code 0)</summary>"
                                   "</task-notification>"}}) + "\n", encoding="utf-8")
        self.assertEqual(self.parada("Os testes passam.", transcript_path=str(transcript),
                                     background_tasks=[]), (0, "", ""))

    def test_sem_o_campo_le_a_ultima_resposta_do_transcript(self) -> None:
        self.gravar(escrita())
        transcript = self.raiz / "t.jsonl"
        linhas = [{"type": "assistant", "message": {"content": [{"type": "text", "text": "Os testes passam."}]}},
                  {"type": "assistant", "isSidechain": True, "message": {"content": [{"type": "text", "text": "x"}]}},
                  "{quebrado"]
        transcript.write_text("".join((l if isinstance(l, str) else json.dumps(l)) + "\n" for l in linhas),
                              encoding="utf-8")
        self.assertEqual(self.parada(None, transcript_path=str(transcript))[0], 2)
        self.assertEqual(guardrail.ultima_resposta({"transcript_path": str(self.raiz / "nada.jsonl")}), "")
        so_pessoa = self.raiz / "so-pessoa.jsonl"                 # transcript sem resposta do modelo
        so_pessoa.write_text(json.dumps({"type": "user", "message": {"content": "oi"}}) + "\n", encoding="utf-8")
        self.assertEqual(guardrail.ultima_resposta({"transcript_path": str(so_pessoa)}), "")
        self.assertEqual(guardrail.ultima_resposta({}), "")

    def test_no_cursor_vira_followup(self) -> None:
        self.gravar({**escrita(), "sessao": "c1"})
        codigo, out, _ = hook("parada", {"conversation_id": "c1", "hook_event_name": "stop",
                                         "workspace_roots": [str(self.raiz)], "loop_count": 0,
                                         "last_assistant_message": "Os testes passam."})
        self.assertEqual(codigo, 0)
        self.assertIn("alegação sem prova", json.loads(out)["followup_message"])

    def test_pelo_processo(self) -> None:
        self.gravar(escrita())
        payload = {"session_id": "s1", "cwd": str(self.raiz), "hook_event_name": "Stop",
                   "stop_hook_active": False, "last_assistant_message": "Feito, o build passou."}
        r = subprocess.run([sys.executable, "-B", str(RAIZ / "guardrail.py"), "parada"], input=json.dumps(payload),
                           capture_output=True, text=True, cwd=self.raiz)
        self.assertEqual((r.returncode, r.stdout), (2, ""))
        self.assertIn("Gate: build.", r.stderr)


class Conferir(unittest.TestCase):
    def conferir(self, prompt: str, **extra) -> tuple[int, str, str]:
        return hook("conferir", {"prompt": prompt, "hook_event_name": "UserPromptSubmit", **extra})

    def test_quando_a_pessoa_pergunta_se_falta_algo(self) -> None:
        for prompt in ("terminou? faltou algo?", "tá pronto?", "veja se ficou faltando alguma coisa",
                       "confere aí", "is it done?"):
            with self.subTest(prompt):
                codigo, out, _ = self.conferir(prompt)
                saida = json.loads(out)["hookSpecificOutput"]
                self.assertEqual((codigo, saida["hookEventName"]), (0, "UserPromptSubmit"))
                self.assertIn("o que chegou no meio do trabalho", saida["additionalContext"])

    def test_o_resto_passa_calado(self) -> None:
        for prompt in ("cria uma tela de login", "o que falta para o login funcionar", "pronto"):
            with self.subTest(prompt):
                self.assertEqual(self.conferir(prompt), (0, "", ""))

    def test_no_cursor_nao_responde(self) -> None:
        codigo, out, _ = hook("conferir", {"conversation_id": "c1", "hook_event_name": "beforeSubmitPrompt",
                                           "prompt": "faltou algo?"})
        self.assertEqual((codigo, out), (0, ""))

    def test_esta_ligado_no_user_prompt_submit(self) -> None:
        ligados = json.loads((RAIZ.parent / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        comandos = [h["command"] for g in ligados["hooks"]["UserPromptSubmit"] for h in g["hooks"]]
        self.assertTrue(any(c.endswith('guardrail.py" conferir') for c in comandos), comandos)


class GatesDeTeste(unittest.TestCase):
    def test_os_corredores_que_faltavam(self) -> None:
        for cmd in ("python3 -m unittest discover -s scripts/tests -t scripts", "tox -e py312",
                    "nox -s testes", "node --test", "deno test"):
            with self.subTest(cmd):
                self.assertEqual(execucao.classificar_gate(cmd), "teste")
        self.assertIsNone(execucao.classificar_gate("echo toxico"))


if __name__ == "__main__":
    unittest.main()
