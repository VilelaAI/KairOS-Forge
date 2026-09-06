"""hooks/hooks.json — os comandos dos hooks EXECUTADOS com payload sintético (ADR-0039).

Grepar o JSON passa mesmo quando um script define uma função que nunca chama. Por isso
cada hook roda de verdade, com o mesmo stdin que o Claude Code mandaria.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest

from tests.apoio import RAIZ, Repositorio, ambiente, escrever, eventos, payload

HOOKS = json.loads((RAIZ / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
EVENTOS_CONHECIDOS = {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
                      "Stop", "SubagentStart", "SubagentStop", "Notification",
                      "PreCompact", "SessionEnd"}


def comandos(evento, matcher_contem=None):
    for bloco in HOOKS.get(evento, []):
        if matcher_contem and matcher_contem not in bloco.get("matcher", "*"):
            continue
        for h in bloco["hooks"]:
            yield bloco.get("matcher", "*"), h["command"]


def executar(cmd, raiz, stdin, extra_env=None):
    env = ambiente(extra_env)
    return subprocess.run(["bash", "-c", cmd], cwd=str(raiz), input=stdin,
                          capture_output=True, text=True, env=env, timeout=60)


class TestForma(unittest.TestCase):
    def test_so_eventos_que_o_claude_code_conhece(self):
        self.assertTrue(set(HOOKS) <= EVENTOS_CONHECIDOS, set(HOOKS) - EVENTOS_CONHECIDOS)

    def test_todo_script_citado_existe(self):
        for evento in HOOKS:
            for _, cmd in comandos(evento):
                for rel in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s\"']+)", cmd):
                    with self.subTest(evento=evento, script=rel):
                        self.assertNotIn("..", rel)
                        self.assertTrue((RAIZ / rel).is_file(), rel)

    def test_guardrails_previos_cobrem_bash_escrita_e_leitura(self):
        matchers = {m for m, c in comandos("PreToolUse") if "guardrail.py" in c}
        for ferramenta in ("Bash", "Write", "Edit", "Read", "Grep"):
            self.assertTrue(any(ferramenta in m for m in matchers), ferramenta)

    def test_telemetria_ve_delegacao_e_subagentes(self):
        matchers = {m for m, c in comandos("PostToolUse") if "execucao.py\" ferramenta" in c}
        self.assertTrue(any("Agent" in m and "Skill" in m for m in matchers),
                        "ramo `delegacao` sem matcher é código morto")
        self.assertTrue(any("subagente_inicio" in c for _, c in comandos("SubagentStart")))
        self.assertTrue(any("subagente_fim" in c for _, c in comandos("SubagentStop")))


class TestExecucaoDosHooks(unittest.TestCase):
    def _unico(self, evento, contem):
        achados = [c for _, c in comandos(evento) if contem in c]
        self.assertEqual(len(achados), 1, f"{evento}/{contem}: {achados}")
        return achados[0]

    def test_pre_tool_use_bash_bloqueia_destrutivo(self):
        cmd = self._unico("PreToolUse", "guardrail.py\" comando")
        with Repositorio() as raiz:
            r = executar(cmd, raiz, payload("Bash", raiz, command="rm -rf /"))
            self.assertEqual(r.returncode, 2, r.stderr)
            r = executar(cmd, raiz, payload("Bash", raiz, command="ls"))
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_pre_tool_use_read_bloqueia_segredo(self):
        cmd = self._unico("PreToolUse", "guardrail.py\" leitura")
        with Repositorio() as raiz:
            escrever(raiz, ".env", "A=1\n")
            r = executar(cmd, raiz, payload("Read", raiz, file_path=str(raiz / ".env")))
            self.assertEqual(r.returncode, 2, r.stderr)

    def test_hooks_de_telemetria_nao_falam_no_stdout(self):
        """Invariante 2 do execucao.py: em SessionStart/UserPromptSubmit o stdout vira contexto."""
        with Repositorio() as raiz:
            for evento, contem in (("SessionStart", "execucao.py"), ("UserPromptSubmit", "execucao.py"),
                                   ("Stop", "execucao.py"), ("SubagentStart", "execucao.py"),
                                   ("SubagentStop", "execucao.py")):
                for _, cmd in comandos(evento):
                    if contem not in cmd:
                        continue
                    with self.subTest(evento=evento):
                        base = json.loads(payload("Bash", raiz, command="x"))
                        base.update({"hook_event_name": evento, "prompt": "/kairos-forge:validar x",
                                     "agent_id": "ag-1", "agent_type": "lucas-backend"})
                        r = executar(cmd, raiz, json.dumps(base))
                        self.assertEqual(r.returncode, 0)
                        self.assertEqual(r.stdout, "")
            tipos = [e["tipo"] for e in eventos(raiz)]
            for tipo in ("sessao_inicio", "prompt", "subagente_inicio", "subagente_fim", "sessao_fim"):
                self.assertIn(tipo, tipos)

    def test_lembrete_de_dod_avisa_uma_vez_por_sessao(self):
        """ADR-0038: primeiro arquivo de produção fala; o segundo, não."""
        cmd = self._unico("PostToolUse", "primeiro arquivo de produção")
        with Repositorio() as raiz, tempfile.TemporaryDirectory() as tmp:
            env = {"TMPDIR": tmp}
            p = payload("Write", raiz, sessao="s-dod", file_path=str(raiz / "src/app.py"))
            r1 = executar(cmd, raiz, p, env)
            self.assertIn("kairos-forge", r1.stdout)
            r2 = executar(cmd, raiz, p, env)
            self.assertEqual(r2.stdout, "")
            teste = payload("Write", raiz, sessao="s-outra", file_path=str(raiz / "tests/test_x.py"))
            self.assertEqual(executar(cmd, raiz, teste, env).stdout, "", "arquivo de teste não avisa")

    def test_banner_de_session_start_cabe_no_orcamento(self):
        banner = [c for _, c in comandos("SessionStart") if c.startswith("echo")][0]
        self.assertLess(len(banner), 600)
        self.assertIn("kairos-forge", banner)


if __name__ == "__main__":
    unittest.main()
