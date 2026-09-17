"""Testes do `guardrail.py` — o piso do ADR-0042 e o gate de parada.

Só stdlib. Cada teste roda num repositório git temporário, porque as regras olham
para o cwd (destruição fora do projeto) e para `.agents/execucoes/` (parada).

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
import guardrail  # noqa: E402


def hook(modo: str, payload: dict) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    guardrail._EDITOR["cursor"] = False
    guardrail._EDITOR["evento"] = ""
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        codigo = guardrail.MODOS[modo](guardrail.normalizar_payload(payload))
    return codigo, out.getvalue(), err.getvalue()


class Sandbox(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-guardrail-")
        self._cwd = os.getcwd()
        self.raiz = Path(self._tmp.name).resolve()
        os.chdir(self.raiz)
        subprocess.run(["git", "init", "-q", "."], check=True)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def cmd(self, comando: str) -> tuple[int, str, str]:
        return hook("comando", {"session_id": "s1", "cwd": str(self.raiz),
                                "tool_input": {"command": comando}})


class LeituraDeSegredo(Sandbox):
    def test_cat_env_bloqueia_e_grep_passa(self) -> None:
        self.assertEqual(self.cmd("cat .env")[0], 2)
        self.assertEqual(self.cmd("head -n 3 .env.production")[0], 2)
        self.assertEqual(self.cmd("cat ~/.ssh/id_rsa")[0], 2)
        self.assertEqual(self.cmd("base64 certs/servidor.pem")[0], 2)
        self.assertEqual(self.cmd("grep -c DATABASE_URL .env")[0], 0)
        self.assertEqual(self.cmd("ls -la ~/.ssh")[0], 0)
        self.assertEqual(self.cmd("cat .env.example")[0], 0)
        self.assertEqual(self.cmd("cat README.md")[0], 0)

    def test_metadados_da_nuvem(self) -> None:
        self.assertEqual(self.cmd("curl -s http://169.254.169.254/latest/meta-data/")[0], 2)

    def test_tool_read_em_segredo(self) -> None:
        for arq, esperado in ((".env", 2), (".env.local", 2), ("chaves/app.pem", 2),
                              (".env.example", 0), ("src/main.py", 0)):
            codigo, _, _ = hook("leitura", {"cwd": str(self.raiz),
                                            "tool_input": {"file_path": str(self.raiz / arq)}})
            self.assertEqual(codigo, esperado, arq)


class DestruicaoNoPiso(Sandbox):
    def test_rm_com_variavel_e_bloqueado(self) -> None:
        self.assertEqual(self.cmd('rm -rf "$DIR"')[0], 2)
        self.assertEqual(self.cmd("rm -rf $(pwd)/build")[0], 2)
        self.assertEqual(self.cmd("rm -rf build dist")[0], 0)

    def test_rm_fora_do_projeto(self) -> None:
        self.assertEqual(self.cmd("rm -rf /opt/outro-projeto")[0], 2)
        antigo = guardrail.TEMP
        guardrail.TEMP = ()  # o sandbox do teste vive em /tmp; sem isto o vizinho seria "temp"
        try:
            self.assertEqual(self.cmd("rm -rf ../vizinho")[0], 2)
            self.assertEqual(self.cmd("rm -rf ~/projetos/outro")[0], 2)
        finally:
            guardrail.TEMP = antigo
        self.assertEqual(self.cmd(f"rm -rf {self.raiz}/node_modules")[0], 0)
        self.assertEqual(self.cmd("rm -rf /tmp/qualquer-coisa")[0], 0)
        self.assertEqual(self.cmd("rm -rf node_modules")[0], 0)

    def test_controle_da_maquina(self) -> None:
        self.assertEqual(self.cmd("sudo reboot")[0], 2)
        self.assertEqual(self.cmd("shutdown -h now")[0], 2)
        self.assertEqual(self.cmd("echo reboot-log.txt")[0], 0)


class FiacaoDosHooks(Sandbox):
    def escrita(self, rel: str, entrada: dict) -> int:
        return hook("escrita", {"cwd": str(self.raiz),
                                "tool_input": {"file_path": str(self.raiz / rel), **entrada}})[0]

    def test_hooks_json_do_cursor_e_sagrado(self) -> None:
        self.assertEqual(self.escrita(".cursor/hooks.json", {"content": "{}"}), 2)

    def test_settings_do_claude_so_bloqueia_o_bloco_hooks(self) -> None:
        (self.raiz / ".claude").mkdir()
        atual = {"permissions": {"allow": ["Bash(npm test)"]},
                 "hooks": {"Stop": [{"hooks": [{"command": "python3 guardrail.py parada"}]}]}}
        (self.raiz / ".claude" / "settings.json").write_text(json.dumps(atual), encoding="utf-8")
        so_permissao = dict(atual, permissions={"allow": ["Bash(npm test)", "Bash(npm run lint)"]})
        self.assertEqual(self.escrita(".claude/settings.json", {"content": json.dumps(so_permissao)}), 0)
        sem_hooks = {"permissions": atual["permissions"]}
        self.assertEqual(self.escrita(".claude/settings.json", {"content": json.dumps(sem_hooks)}), 2)
        self.assertEqual(self.escrita(".claude/settings.json",
                                      {"old_string": '"Bash(npm test)"', "new_string": '"Bash(npm ci)"'}), 0)
        self.assertEqual(self.escrita(".claude/settings.json",
                                      {"old_string": '"hooks": {', "new_string": '"hooks_off": {'}), 2)


class GateDeParada(Sandbox):
    def gravar(self, eventos: list[dict]) -> None:
        pasta = self.raiz / ".agents" / "execucoes"
        pasta.mkdir(parents=True, exist_ok=True)
        with (pasta / "2026-09.jsonl").open("a", encoding="utf-8") as fh:
            for ev in eventos:
                fh.write(json.dumps({"t": "2026-09-17T00:00:00+00:00", "sessao": "s1", **ev}) + "\n")

    def parada(self, extra: dict | None = None) -> tuple[int, str, str]:
        return hook("parada", {"session_id": "s1", "cwd": str(self.raiz), **(extra or {})})

    def test_sem_escrita_de_producao_nao_dispara(self) -> None:
        self.gravar([{"tipo": "escrita", "arquivo": "docs/x.md", "producao": False}])
        self.assertEqual(self.parada()[0], 0)

    def test_producao_sem_gate_avisa_por_default_e_bloqueia_em_bloqueio(self) -> None:
        self.gravar([{"tipo": "escrita", "arquivo": "src/a.py", "producao": True}])
        codigo, _, err = self.parada()
        self.assertEqual(codigo, 1)  # `parada` nasce em aviso
        self.assertIn("src/a.py", err)
        (self.raiz / ".agents" / "guardrails.json").write_text('{"modos": {"parada": "bloqueio"}}', encoding="utf-8")
        self.assertEqual(self.parada()[0], 2)

    def test_gate_verde_depois_da_escrita_libera(self) -> None:
        self.gravar([{"tipo": "escrita", "arquivo": "src/a.py", "producao": True},
                     {"tipo": "comando", "cmd": "pytest -q", "gate": "teste", "ok": True}])
        self.assertEqual(self.parada()[0], 0)

    def test_escrita_depois_do_gate_volta_a_pender(self) -> None:
        self.gravar([{"tipo": "comando", "cmd": "pytest -q", "gate": "teste", "ok": True},
                     {"tipo": "escrita", "arquivo": "src/b.py", "producao": True}])
        (self.raiz / ".agents" / "guardrails.json").write_text('{"modos": {"parada": "bloqueio"}}', encoding="utf-8")
        codigo, _, err = self.parada()
        self.assertEqual(codigo, 2)
        self.assertIn("src/b.py", err)

    def test_nunca_dispara_duas_vezes(self) -> None:
        self.gravar([{"tipo": "escrita", "arquivo": "src/a.py", "producao": True}])
        (self.raiz / ".agents" / "guardrails.json").write_text('{"modos": {"parada": "bloqueio"}}', encoding="utf-8")
        self.assertEqual(self.parada({"stop_hook_active": True})[0], 0)
        self.assertEqual(self.parada({"loop_count": 1})[0], 0)


class AdaptadorCursor(Sandbox):
    def test_shell_do_cursor_responde_em_json(self) -> None:
        codigo, out, _ = hook("comando", {"conversation_id": "c1", "hook_event_name": "beforeShellExecution",
                                          "workspace_roots": [str(self.raiz)], "command": "cat .env", "cwd": str(self.raiz)})
        self.assertEqual(codigo, 0)
        resp = json.loads(out)
        self.assertEqual(resp["permission"], "deny")
        self.assertIn("segredo", resp["agent_message"])

    def test_leitura_do_cursor(self) -> None:
        codigo, out, _ = hook("leitura", {"conversation_id": "c1", "hook_event_name": "beforeReadFile",
                                          "workspace_roots": [str(self.raiz)], "file_path": str(self.raiz / ".env")})
        self.assertEqual(json.loads(out)["permission"], "deny")

    def test_parada_do_cursor_vira_followup(self) -> None:
        pasta = self.raiz / ".agents" / "execucoes"; pasta.mkdir(parents=True)
        (pasta / "2026-09.jsonl").write_text(json.dumps({"t": "x", "sessao": "c1", "tipo": "escrita",
                                                          "arquivo": "src/a.py", "producao": True}) + "\n")
        (self.raiz / ".agents" / "guardrails.json").write_text('{"modos": {"parada": "bloqueio"}}', encoding="utf-8")
        codigo, out, _ = hook("parada", {"conversation_id": "c1", "hook_event_name": "stop",
                                         "workspace_roots": [str(self.raiz)], "status": "completed", "loop_count": 0})
        self.assertEqual(codigo, 0)
        self.assertIn("src/a.py", json.loads(out)["followup_message"])


if __name__ == "__main__":
    unittest.main()
