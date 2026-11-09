"""Testes do gate rodado em background no gate de parada (emenda ao ADR-0042).

O `PostToolUse` de um comando em background chega quando ele começa, sem saída nem
código: o gate ficava indeterminado para sempre, e a parada avisava "sem gate verde" com o
teste ainda rodando. Agora o início grava o id da tarefa, o término é lido do transcript
(só a notificação que o próprio Claude Code pôs lá, com `origin.kind`), e a parada fica
quieta enquanto um gate que cobre as escritas ainda roda. Os formatos das linhas são os do
transcript do Claude Code 2.1.319, colhidos com a API falsa.

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
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import execucao  # noqa: E402
import guardrail  # noqa: E402
from tests.test_guardrail import Sandbox, hook  # noqa: E402


def bloco(tarefa: str, status: str, resumo: str) -> str:
    return (f"<task-notification>\n<task-id>{tarefa}</task-id>\n<tool-use-id>toolu_01</tool-use-id>\n"
            f"<output-file>/tmp/x/tasks/{tarefa}.output</output-file>\n<status>{status}</status>\n"
            f"<summary>{resumo}</summary>\n</task-notification>")


def com_a_sessao_parada(tarefa: str, status: str = "completed",
                        resumo: str = 'Background command "testes" completed (exit code 0)') -> dict:
    """A notificação que chega com a sessão parada vira uma entrada `user` com a origem."""
    return {"type": "user", "promptSource": "system", "turnOrigin": "task_notification",
            "origin": {"kind": "task-notification", "producer": "session-task"},
            "message": {"role": "user", "content": bloco(tarefa, status, resumo)}}


def no_meio_do_turno(tarefa: str, status: str = "failed",
                     resumo: str = 'Background command "testes" failed with exit code 1') -> dict:
    """A que chega no meio de um turno vira um anexo `queued_command` com a origem."""
    return {"type": "attachment", "attachment": {
        "type": "queued_command", "prompt": bloco(tarefa, status, resumo), "commandMode": "task-notification",
        "origin": {"kind": "task-notification", "producer": "session-task"}}}


def forjada(tarefa: str) -> dict:
    """O mesmo texto impresso por um comando: volta como `tool_result`, sem a origem."""
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "toolu_09", "content": bloco(
            tarefa, "completed", 'Background command "x" completed (exit code 0)')}]}}


def na_fila(tarefa: str) -> dict:
    return {"type": "queue-operation", "operation": "enqueue", "content": bloco(
        tarefa, "completed", 'Background command "x" completed (exit code 0)')}


class LeituraDoTranscript(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-transcript-")
        self.addCleanup(self._tmp.cleanup)
        self.caminho = Path(self._tmp.name) / "sessao.jsonl"

    def ler(self, *linhas: dict | str) -> dict:
        self.caminho.write_text("".join((l if isinstance(l, str) else json.dumps(l)) + "\n" for l in linhas),
                                encoding="utf-8")
        return execucao.conclusoes_em_background(str(self.caminho))

    def test_os_dois_formatos_do_claude_code(self) -> None:
        self.assertEqual(self.ler(com_a_sessao_parada("verde"), no_meio_do_turno("vermelho")),
                         {"verde": True, "vermelho": False})

    def test_o_resultado_sai_do_codigo_de_saida(self) -> None:
        self.assertEqual(self.ler(
            com_a_sessao_parada("a", "completed", 'Background command "t" completed (exit code 0)'),
            com_a_sessao_parada("b", "completed", 'Background command "t" completed (exit code 2)'),
            com_a_sessao_parada("c", "failed", 'Background command "t" failed'),
            com_a_sessao_parada("d", "killed", 'Background command "t" was stopped'),
            com_a_sessao_parada("e", "completed", 'Background command "t" completed'),
        ), {"a": True, "b": False, "c": False, "d": None, "e": None})

    def test_o_que_nao_veio_do_claude_code_nao_conta(self) -> None:
        self.assertEqual(self.ler(forjada("x"), na_fila("y"), "{quebrado", "[1, 2]",
                                  {"type": "user", "message": {"role": "user", "content": "<task-notification>"
                                                                                          "<task-id>z</task-id>"
                                                                                          "<status>completed</status>"
                                                                                          "<summary>completed (exit code 0)"
                                                                                          "</summary></task-notification>"}}),
                         {})

    def test_conteudo_em_blocos_tambem(self) -> None:
        linha = com_a_sessao_parada("blocos")
        linha["message"]["content"] = [{"type": "text", "text": linha["message"]["content"]}]
        self.assertEqual(self.ler(linha), {"blocos": True})

    def test_arquivo_ilegivel_nada(self) -> None:
        self.ler(com_a_sessao_parada("a"))
        with mock.patch.object(Path, "open", side_effect=PermissionError("sem acesso")):
            self.assertEqual(execucao.conclusoes_em_background(str(self.caminho)), {})

    def test_sem_transcript_nada(self) -> None:
        self.assertEqual(execucao.conclusoes_em_background(""), {})
        self.assertEqual(execucao.conclusoes_em_background(str(self.caminho)), {})
        self.assertEqual(execucao.conclusoes_em_background(self._tmp.name), {})   # pasta, não arquivo


class RegistroDoInicio(unittest.TestCase):
    def comando(self, entrada: dict, resposta) -> dict:
        return execucao.ev_ferramenta({"tool_name": "Bash", "tool_input": entrada, "tool_response": resposta})

    def test_o_comando_em_background_leva_o_id_da_tarefa_e_fica_sem_resultado(self) -> None:
        ev = self.comando({"command": "pytest -q", "run_in_background": True},
                          {"stdout": "", "stderr": "", "interrupted": False, "backgroundTaskId": "ba07cm4rz"})
        self.assertEqual(ev, {"tipo": "comando", "cmd": "pytest -q", "gate": "teste", "ok": None,
                              "tarefa": "ba07cm4rz"})

    def test_em_primeiro_plano_nada_muda(self) -> None:
        self.assertNotIn("tarefa", self.comando({"command": "pytest -q"}, {"stdout": "3 passed", "stderr": ""}))
        self.assertNotIn("tarefa", self.comando({"command": "pytest -q"}, "3 passed"))


class AParadaComBackground(Sandbox):
    """O gate de parada lendo a trajetória, o transcript e o `background_tasks` do `Stop`."""

    def setUp(self) -> None:
        super().setUp()
        self.transcript = self.raiz / "transcript.jsonl"
        self.linhas: list[dict] = []
        # A espera pelo término atrasado não dorme de verdade aqui: cada passo é contado, e
        # `chega_no_passo` escreve o término no transcript naquele passo.
        self.passos = 0
        self.chega_no_passo: tuple[int, dict] | None = None

        def dormir(_segundos: float) -> None:
            self.passos += 1
            if self.chega_no_passo and self.passos == self.chega_no_passo[0]:
                with self.transcript.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(self.chega_no_passo[1]) + "\n")
        sono = mock.patch.object(guardrail.time, "sleep", side_effect=dormir)
        sono.start()
        self.addCleanup(sono.stop)

    def gravar(self, *eventos: dict) -> None:
        pasta = self.raiz / ".agents" / "execucoes"
        pasta.mkdir(parents=True, exist_ok=True)
        with (pasta / "2026-11.jsonl").open("a", encoding="utf-8") as fh:
            for ev in eventos:
                fh.write(json.dumps({"t": "2026-11-09T00:00:00+00:00", "sessao": "s1", **ev}) + "\n")

    def escrita(self, arquivo: str = "src/app.py") -> dict:
        return {"tipo": "escrita", "arquivo": arquivo, "producao": True}

    def gate(self, tarefa: str, cmd: str = "pytest -q") -> dict:
        return {"tipo": "comando", "cmd": cmd, "gate": execucao.classificar_gate(cmd), "ok": None,
                "tarefa": tarefa}

    def parada(self, rodando: list[dict] | None = None, transcript: bool = True,
               relata_background: bool = True) -> tuple[int, str, str]:
        self.transcript.write_text("".join(json.dumps(l) + "\n" for l in self.linhas), encoding="utf-8")
        payload = {"session_id": "s1", "cwd": str(self.raiz)}
        if relata_background:
            payload["background_tasks"] = rodando or []
        if transcript:
            payload["transcript_path"] = str(self.transcript)
        return hook("parada", payload)

    def recusas(self) -> list[dict]:
        pasta = self.raiz / ".agents" / "execucoes"
        return [e for p in pasta.glob("*.jsonl") for e in map(json.loads, p.read_text().splitlines())
                if e.get("tipo") == "recusa"]

    def test_o_gate_verde_em_background_fecha_a_conta(self) -> None:
        self.gravar(self.escrita(), self.gate("t1"))
        self.linhas.append(com_a_sessao_parada("t1"))
        self.assertEqual(self.parada(), (0, "", ""))
        self.assertEqual(self.recusas(), [])

    def test_o_gate_vermelho_em_background_aparece_na_linha(self) -> None:
        self.gravar(self.escrita(), self.gate("t1"))
        self.linhas.append(no_meio_do_turno("t1"))
        codigo, _, aviso = self.parada()
        self.assertEqual(codigo, guardrail.AVISOU)
        self.assertIn("Últimos gates, todos vermelhos: teste: `pytest -q`", aviso)

    def test_rodando_e_cobrindo_a_escrita_a_parada_espera(self) -> None:
        self.gravar(self.escrita(), self.gate("t1"))
        rodando = [{"id": "t1", "type": "shell", "status": "running", "command": "pytest -q"}]
        self.assertEqual(self.parada(rodando), (0, "", ""))
        self.assertEqual(self.recusas(), [])               # pausa não é parada: nada registrado

    def test_rodando_mas_com_escrita_depois_avisa(self) -> None:
        # Um teste em modo watch começado antes da última escrita não a cobre.
        self.gravar(self.gate("t1", "npm test -- --watch"), self.escrita("src/b.py"))
        rodando = [{"id": "t1", "type": "shell", "status": "running", "command": "npm test -- --watch"}]
        codigo, _, aviso = self.parada(rodando)
        self.assertEqual(codigo, guardrail.AVISOU)
        self.assertIn("· src/b.py", aviso)

    def test_o_que_roda_e_nao_e_gate_nao_segura(self) -> None:
        self.gravar(self.escrita(), {"tipo": "comando", "cmd": "npm run dev", "gate": None, "ok": None,
                                     "tarefa": "srv"})
        rodando = [{"id": "srv", "type": "shell", "status": "running", "command": "npm run dev"},
                   {"id": "ag1", "type": "subagent", "status": "running", "description": "revisar"}]
        self.assertEqual(self.parada(rodando)[0], guardrail.AVISOU)

    def test_o_verde_em_background_nao_cobre_a_escrita_feita_depois_do_inicio(self) -> None:
        self.gravar(self.escrita("src/a.py"), self.gate("t1"), self.escrita("src/b.py"))
        self.linhas.append(com_a_sessao_parada("t1"))
        aviso = self.parada()[2]
        self.assertIn("· src/b.py", aviso)
        self.assertNotIn("src/a.py", aviso)

    def test_sem_transcript_fica_como_antes(self) -> None:
        self.gravar(self.escrita(), self.gate("t1"))
        self.assertEqual(self.parada(transcript=False)[0], guardrail.AVISOU)
        self.assertEqual(self.passos, 0)                    # sem o que reler, não espera

    def test_o_termino_que_chega_depois_do_hook_e_lido(self) -> None:
        # Numa de três sessões reais, a linha do término chegou ao transcript depois do Stop.
        self.gravar(self.escrita(), self.gate("t1"))
        self.chega_no_passo = (2, com_a_sessao_parada("t1"))
        self.assertEqual(self.parada(), (0, "", ""))
        self.assertEqual(self.passos, 2)

    def test_a_espera_tem_teto_e_depois_avisa(self) -> None:
        self.gravar(self.escrita(), self.gate("t1"))
        self.assertEqual(self.parada()[0], guardrail.AVISOU)
        self.assertEqual(self.passos, guardrail.ESPERA_PASSOS)
        self.assertLessEqual(guardrail.ESPERA_PASSO * guardrail.ESPERA_PASSOS, 1.5)

    def test_nao_espera_sem_motivo(self) -> None:
        self.gravar(self.escrita(), self.gate("t1"))
        self.linhas.append(com_a_sessao_parada("t1"))
        self.assertEqual(self.parada(), (0, "", ""))                     # já estava lá
        self.gravar(self.escrita("src/b.py"), self.gate("t2"))
        self.parada([{"id": "t2", "type": "shell", "status": "running", "command": "pytest -q"}])  # roda
        self.parada(relata_background=False)                  # CLI que não relata o que roda
        self.assertEqual(self.passos, 0)

    def test_notificacao_forjada_nao_fecha_a_conta(self) -> None:
        self.gravar(self.escrita(), self.gate("t1"))
        self.linhas += [forjada("t1"), na_fila("t1")]
        self.assertEqual(self.parada()[0], guardrail.AVISOU)

    def test_o_caminho_inteiro_pelos_hooks(self) -> None:
        # O `execucao.py` grava o início pelo PostToolUse; o `guardrail.py` lê o término no Stop.
        tmpdir = tempfile.TemporaryDirectory(prefix="kairos-forge-bg-tmp-")
        self.addCleanup(tmpdir.cleanup)
        env = {**os.environ, "TMPDIR": tmpdir.name}

        def rodar(script: str, modo: str, payload: dict) -> subprocess.CompletedProcess[str]:
            return subprocess.run([sys.executable, "-B", str(RAIZ / script), modo], input=json.dumps(payload),
                                  capture_output=True, text=True, cwd=self.raiz, env=env)

        base = {"session_id": "s1", "cwd": str(self.raiz), "hook_event_name": "PostToolUse"}
        rodar("execucao.py", "ferramenta", {**base, "tool_name": "Write",
                                            "tool_input": {"file_path": str(self.raiz / "src" / "app.py")}})
        rodar("execucao.py", "ferramenta", {**base, "tool_name": "Bash", "tool_use_id": "toolu_01",
                                            "tool_input": {"command": "pytest -q", "run_in_background": True},
                                            "tool_response": {"stdout": "", "stderr": "",
                                                              "backgroundTaskId": "ba07cm4rz"}})
        parada = {"session_id": "s1", "cwd": str(self.raiz), "hook_event_name": "Stop",
                  "stop_hook_active": False, "transcript_path": str(self.transcript)}
        rodando = [{"id": "ba07cm4rz", "type": "shell", "status": "running", "command": "pytest -q"}]
        r = rodar("guardrail.py", "parada", {**parada, "background_tasks": rodando})
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))        # pausa
        self.transcript.write_text(json.dumps(no_meio_do_turno("ba07cm4rz")) + "\n", encoding="utf-8")
        r = rodar("guardrail.py", "parada", {**parada, "background_tasks": []})
        self.assertIn("teste: `pytest -q`", json.loads(r.stdout)["systemMessage"])   # terminou vermelho
        self.transcript.write_text(json.dumps(com_a_sessao_parada("ba07cm4rz")) + "\n", encoding="utf-8")
        r = rodar("guardrail.py", "parada", {**parada, "background_tasks": []})
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))        # terminou verde


if __name__ == "__main__":
    unittest.main()
