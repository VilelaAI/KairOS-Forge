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
from unittest import mock
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

    def test_piso_nao_obedece_a_modos(self) -> None:
        # Com a classe `comando` rebaixada para aviso, o resto das regras de comando avisa
        # e deixa passar — o piso continua bloqueando (ADR-0042: sem `modos`).
        (self.raiz / ".agents").mkdir(exist_ok=True)
        (self.raiz / ".agents" / "guardrails.json").write_text(
            '{"modos": {"comando": "aviso"}}', encoding="utf-8")
        self.assertEqual(self.cmd("chmod 777 build")[0], 1)
        self.assertEqual(self.cmd("sudo reboot")[0], 2)
        self.assertEqual(self.cmd('rm -rf "$DIR"')[0], 2)
        self.assertEqual(self.cmd("rm -rf /opt/outro-projeto")[0], 2)


class HooksDoGit(Sandbox):
    """ADR-0046: o hook do git é gate do projeto — desligá-lo é escrever o próprio medidor."""

    def test_formas_de_pular_os_hooks_bloqueiam(self) -> None:
        for comando in ('git commit --no-verify -m "wip"',
                        "git push --no-verify origin feat",
                        'git commit -n -m "wip"',
                        'git commit -anm "wip"',
                        'git -c core.hooksPath=/dev/null commit -m "x"',
                        'git -c CORE.HOOKSPATH=/dev/null commit -m "x"',
                        "git config core.hooksPath /tmp/vazio",
                        'HUSKY=0 git commit -m "x"',
                        'SKIP=flake8 git commit -m "x"',
                        'cd app && LEFTHOOK=0 git push',
                        "bash -c 'git commit --no-verify -m x'"):
            codigo, _, err = self.cmd(comando)
            self.assertEqual(codigo, 2, comando)
            self.assertIn("pula os hooks do git", err)

    def test_mensagem_que_cita_a_flag_e_valor_colado_passam(self) -> None:
        for comando in ('git commit -m "docs: explica por que --no-verify é bloqueado"',
                        "git commit -m 'evite git commit -n'",
                        "git commit -F - <<'EOF'\nfix: nada de --no-verify\n\nHUSKY=0 git x\nEOF",
                        "git commit -uno -m x",
                        "git commit -cmain",
                        "git commit --amend --no-edit",
                        "git push -n origin feat",          # em push, -n é --dry-run
                        "git config --get core.hooksPath",
                        'npx husky && git commit -m "x"',
                        "SKIP=1 npm test"):
            self.assertEqual(self.cmd(comando)[0], 0, comando)

    def test_heredoc_nao_esconde_o_comando_seguinte(self) -> None:
        comando = "cat > nota.txt <<'EOF'\ntexto\nEOF\ngit commit --no-verify -m x"
        self.assertEqual(self.cmd(comando)[0], 2)

    def test_e_piso_nao_obedece_a_modos(self) -> None:
        (self.raiz / ".agents").mkdir(exist_ok=True)
        (self.raiz / ".agents" / "guardrails.json").write_text(
            '{"modos": {"comando": "aviso"}}', encoding="utf-8")
        self.assertEqual(self.cmd("git commit --no-verify -m x")[0], 2)


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


class PrDuranteCiclo(Sandbox):
    """Com dois ciclos abertos, o `gh pr create` é julgado pelo ciclo da branch atual —
    não pelo primeiro em ordem de nome."""

    def setUp(self) -> None:
        super().setUp()
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                        "--allow-empty", "-m", "base"], check=True)
        (self.raiz / ".agents" / "ciclo").mkdir(parents=True)

    def ciclo(self, spec: str, estado: str, branch: str | None) -> None:
        d = {"spec": spec, "estado": estado, "rodadas": {"validar": 0, "revisar": 0},
             "orcamento": {"validar": 2, "revisar": 2}}
        if branch:
            d["branch"] = branch
        (self.raiz / ".agents" / "ciclo" / f"{spec}.json").write_text(json.dumps(d), encoding="utf-8")

    def na_branch(self, nome: str) -> None:
        subprocess.run(["git", "checkout", "-q", "-B", nome], check=True)

    def test_pr_do_ciclo_pronto_passa_com_outro_ciclo_parado(self) -> None:
        self.ciclo("SPEC-001", "aguardando_aprovacao", "feat/spec-001")
        self.ciclo("SPEC-002", "pronto_para_pr", "feat/spec-002")
        self.na_branch("feat/spec-002")
        self.assertEqual(self.cmd("gh pr create --fill")[0], 0)

    def test_pr_do_ciclo_fora_de_estado_bloqueia(self) -> None:
        self.ciclo("SPEC-001", "aguardando_aprovacao", "feat/spec-001")
        self.ciclo("SPEC-002", "pronto_para_pr", "feat/spec-002")
        self.na_branch("feat/spec-001")
        codigo, _, err = self.cmd("gh pr create --fill")
        self.assertEqual(codigo, 2)
        self.assertIn("SPEC-001", err)

    def test_branch_sem_ciclo_nao_escapa(self) -> None:
        # Trocar de branch para abrir o PR não contorna o estado de um ciclo aberto.
        self.ciclo("SPEC-001", "validando", "feat/spec-001")
        self.ciclo("SPEC-002", "pronto_para_pr", "feat/spec-002")
        self.na_branch("atalho")
        self.assertEqual(self.cmd("gh pr create --fill")[0], 2)

    def test_ciclo_antigo_sem_branch(self) -> None:
        self.na_branch("feat/x")
        self.ciclo("SPEC-001", "validando", None)
        self.assertEqual(self.cmd("gh pr create --fill")[0], 2)
        self.ciclo("SPEC-001", "pronto_para_pr", None)
        self.assertEqual(self.cmd("gh pr create --fill")[0], 0)


class VerificarNoCI(Sandbox):
    def rodar(self) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            codigo = guardrail.verificar(self.raiz)
        return codigo, out.getvalue()

    def test_env_example_passa_e_env_reprova(self) -> None:
        # As mesmas exceções do hook de escrita: `.env.example` existe para ser versionado.
        (self.raiz / ".env.example").write_text("API_KEY=\n", encoding="utf-8")
        (self.raiz / "certs").mkdir()
        (self.raiz / "certs" / "README.md").write_text("onde ficam as chaves\n", encoding="utf-8")
        self.assertEqual(self.rodar()[0], 0)
        (self.raiz / ".env").write_text("API_KEY=x\n", encoding="utf-8")
        codigo, saida = self.rodar()
        self.assertEqual(codigo, 1)
        self.assertIn(".env:", saida)
        self.assertNotIn(".env.example", saida)


class FalhaAberta(Sandbox):
    """ADR-0046: guardrail quebrado deixa passar — mas não em silêncio."""

    def rastro(self) -> list[dict]:
        pasta = self.raiz / ".agents" / "execucoes"
        return [json.loads(l) for p in pasta.glob("*.jsonl")
                for l in p.read_text(encoding="utf-8").splitlines()]

    def test_payload_quebrado_passa_mas_fica_na_trajetoria(self) -> None:
        r = subprocess.run([sys.executable, str(RAIZ / "guardrail.py"), "comando"],
                           input="{quebrado", capture_output=True, text=True, cwd=self.raiz)
        self.assertEqual(r.returncode, 0)
        self.assertIn("falhou e deixou passar", r.stderr)
        evento, = self.rastro()
        self.assertEqual((evento["tipo"], evento["modo"]), ("guardrail_erro", "comando"))
        self.assertIn("JSONDecodeError", evento["erro"])

    def test_bug_numa_regra_usa_o_cwd_do_payload(self) -> None:
        # O hook pode rodar com o processo noutro diretório: vale o projeto do payload.
        os.chdir(self._cwd)
        with contextlib.redirect_stderr(io.StringIO()):
            codigo = guardrail.falhar_aberto("escrita", {"cwd": str(self.raiz)},
                                             KeyError("tool_input"))
        self.assertEqual(codigo, 0)
        self.assertEqual(self.rastro()[0]["erro"], "KeyError: 'tool_input'")


class ComCommit(Sandbox):
    """Sandbox com base commitada e `$TMPDIR` próprio para as marcas de "uma vez por sessão"."""

    def setUp(self) -> None:
        super().setUp()
        # O "avisa uma vez por sessão" marca em $TMPDIR; fora do sandbox, a marca da
        # rodada anterior da suíte faria o primeiro aviso desta sair calado.
        tmp = self.raiz / ".tmp"
        tmp.mkdir()
        self._env = mock.patch.dict(os.environ, {"TMPDIR": str(tmp)})
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()
        super().tearDown()

    def commitar(self, arquivos: dict[str, str]) -> None:
        for rel, texto in arquivos.items():
            (self.raiz / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.raiz / rel).write_text(texto, encoding="utf-8")
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm",
                        "base"], check=True)

    def escrita(self, rel: str, entrada: dict, sessao: str = "") -> tuple[int, str]:
        codigo, _, err = hook("escrita", {
            "session_id": sessao or self.id(), "cwd": str(self.raiz),
            "tool_input": {"file_path": str(self.raiz / rel), **entrada}})
        return codigo, err

    def config(self, texto: str) -> None:
        (self.raiz / ".agents").mkdir(exist_ok=True)
        (self.raiz / ".agents" / "guardrails.json").write_text(texto, encoding="utf-8")

    def rastro(self) -> list[dict]:
        return [json.loads(l) for p in (self.raiz / ".agents" / "execucoes").glob("*.jsonl")
                for l in p.read_text(encoding="utf-8").splitlines()]



class TesteExistente(ComCommit):
    """ADR-0039: teste que já existia é a prova do comportamento anterior."""

    def test_teste_existente_avisa_uma_vez_e_teste_novo_passa(self) -> None:
        self.commitar({"tests/test_app.py": "def test_a():\n    assert f() == 1\n"})
        troca = {"old_string": "== 1", "new_string": "== 2"}
        codigo, err = self.escrita("tests/test_app.py", troca)
        self.assertEqual(codigo, 1)
        self.assertIn("teste existente", err)
        self.assertEqual(self.escrita("tests/test_app.py", troca)[0], 0)
        self.assertEqual(self.escrita("tests/test_novo.py", {"content": "x = 1\n"})[0], 0)
        self.assertEqual([e["classe"] for e in self.rastro()], ["teste", "teste"])

    def test_excecao_casa_em_qualquer_pasta(self) -> None:
        self.config('{"protegidos": ["config/**"]}')
        self.assertEqual(self.escrita("config/.env.example", {"content": "A=\n"})[0], 0)
        self.assertEqual(self.escrita("config/app.yml", {"content": "a: 1\n"})[0], 2)

    def test_teste_em_caminho_protegido_e_bloqueado_nao_so_avisado(self) -> None:
        # O que bloqueia vem antes do que avisa (ADR-0046).
        self.commitar({"tests/test_app.py": "x = 1\n"})
        self.config('{"protegidos": ["tests/**"]}')
        codigo, err = self.escrita("tests/test_app.py", {"content": "x = 2\n"})
        self.assertEqual(codigo, 2)
        self.assertIn("protegido pelo projeto", err)

    def test_bloqueio_e_liberados(self) -> None:
        self.commitar({"tests/test_app.py": "x = 1\n"})
        self.config('{"modos": {"teste": "bloqueio"}}')
        self.assertEqual(self.escrita("tests/test_app.py", {"content": "x = 2\n"})[0], 2)
        self.config('{"modos": {"teste": "bloqueio"}, "liberados": ["tests/**"]}')
        self.assertEqual(self.escrita("tests/test_app.py", {"content": "x = 2\n"})[0], 0)


class Principal(Sandbox):
    """O `main`: uso, `verificar`, modo hook e a falha aberta, no mesmo processo."""

    def main(self, *args: str, entrada: str = "") -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["guardrail.py", *args]), \
                mock.patch.object(sys, "stdin", io.StringIO(entrada)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            codigo = guardrail.main()
        return codigo, out.getvalue(), err.getvalue()

    def test_sem_argumento_ou_modo_desconhecido_mostra_o_uso(self) -> None:
        for args in ((), ("medir",)):
            codigo, out, _ = self.main(*args)
            self.assertEqual(codigo, 1)
            self.assertIn("guardrail.py verificar", out)

    def test_verificar_e_modo_hook(self) -> None:
        self.assertEqual(self.main("verificar", str(self.raiz))[0], 0)
        payload = {"cwd": str(self.raiz), "tool_input": {"command": "git commit --no-verify"}}
        self.assertEqual(self.main("comando", entrada=json.dumps(payload))[0], 2)
        self.assertEqual(self.main("comando", entrada="")[0], 0)

    def test_payload_quebrado_passa_e_avisa(self) -> None:
        codigo, _, err = self.main("comando", entrada="{x")
        self.assertEqual(codigo, 0)
        self.assertIn("falhou e deixou passar", err)


class Regua(ComCommit):
    """ADR-0046: config do gate e supressão inline — baixar a régua em vez de consertar."""

    def test_config_existente_avisa_uma_vez_e_deixa_rastro_sempre(self) -> None:
        self.commitar({".eslintrc.json": '{"rules": {"no-unused-vars": "error"}}\n'})
        troca = {"old_string": '"error"', "new_string": '"off"'}
        codigo, err = self.escrita(".eslintrc.json", troca)
        self.assertEqual(codigo, 1)
        self.assertIn("régua do projeto", err)
        self.assertEqual(self.escrita(".eslintrc.json", troca)[0], 0)  # avisa uma vez
        self.assertEqual([e["classe"] for e in self.rastro()], ["regua", "regua"])

    def test_config_nova_e_setup_e_passa(self) -> None:
        self.commitar({"app.py": "x = 1\n"})
        self.assertEqual(self.escrita("ruff.toml", {"content": "line-length = 100\n"})[0], 0)
        self.assertEqual(self.escrita(".husky/pre-commit", {"content": "npm test\n"})[0], 0)

    def test_hook_do_git_e_ignore_tambem_sao_regua(self) -> None:
        self.commitar({".husky/pre-commit": "npm test\n", ".eslintignore": "dist\n",
                       "eslint.config.base.mjs": "export default []\n"})
        for rel in (".husky/pre-commit", ".eslintignore", "eslint.config.base.mjs"):
            self.assertEqual(self.escrita(rel, {"content": "\n"})[0], 1, rel)

    def test_supressao_nova_em_producao_avisa(self) -> None:
        self.commitar({"app.py": "x = f()\n", "web.ts": "const y = g();\n"})
        self.assertEqual(self.escrita("app.py", {"old_string": "x = f()",
                                                 "new_string": "x = f()  # type: ignore"})[0], 1)
        self.assertEqual(self.escrita("web.ts", {"edits": [
            {"old_string": "const y", "new_string": "// @ts-ignore\nconst y"}]})[0], 1)
        self.assertEqual(self.escrita("novo.py", {"content": "y = 2  # pragma: no cover\n"})[0], 1)

    def test_supressao_em_literal_em_teste_ou_so_movida_passa(self) -> None:
        self.commitar({"app.py": "a()  # noqa\nb()\n"})
        self.assertEqual(self.escrita("app.py", {"old_string": "b()",
                                                 "new_string": 'b("# noqa")'})[0], 0)
        self.assertEqual(self.escrita("app.py", {"old_string": "a()  # noqa\nb()",
                                                 "new_string": "b()\na()  # noqa"})[0], 0)
        self.assertEqual(self.escrita("tests/test_app.py",
                                      {"content": "x = y  # type: ignore\n"})[0], 0)
        self.assertEqual(self.escrita("README.md", {"content": "use `# noqa`\n"})[0], 0)

    def test_modo_bloqueio_e_liberados(self) -> None:
        self.commitar({"tsconfig.json": '{"strict": true}\n'})
        troca = {"old_string": "true", "new_string": "false"}
        self.config('{"modos": {"regua": "bloqueio"}}')
        self.assertEqual(self.escrita("tsconfig.json", troca)[0], 2)
        self.config('{"modos": {"regua": "bloqueio"}, "liberados": ["tsconfig.json"]}')
        self.assertEqual(self.escrita("tsconfig.json", troca)[0], 0)

    def test_ler_diff_marca_novo_e_removido(self) -> None:
        diff = ("diff --git a/.prettierrc b/.prettierrc\n--- a/.prettierrc\n+++ /dev/null\n"
                "@@ -1 +0,0 @@\n-{}\n"
                "diff --git a/n.py b/n.py\n--- /dev/null\n+++ b/n.py\n@@ -0,0 +1 @@\n+x = 1\n")
        d = guardrail.ler_diff(diff)
        self.assertEqual((d[".prettierrc"]["novo"], d[".prettierrc"]["menos"]), (False, ["{}"]))
        self.assertEqual((d["n.py"]["novo"], d["n.py"]["mais"]), (True, ["x = 1"]))

    def test_verificar_avisa_e_endurece_por_modo(self) -> None:
        self.commitar({".prettierrc": "{}\n", "app.js": "f();\n", "ruff.toml": "\n",
                       "outro.py": "x = 1\n"})
        (self.raiz / "outro.py").write_text("x = 2\n", encoding="utf-8")
        (self.raiz / ".prettierrc").unlink()
        (self.raiz / "app.js").write_text("// eslint-disable-next-line\nf();\n", encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(guardrail.verificar(self.raiz), 0)
        self.assertIn(".prettierrc — config da régua alterada ou removida", out.getvalue())
        self.assertIn("app.js — 1 supressão(ões) inline nova(s)", out.getvalue())
        self.assertNotIn("ruff.toml", out.getvalue())
        self.assertNotIn("outro.py", out.getvalue())  # mudou, mas sem supressão nova
        self.config('{"modos": {"regua": "bloqueio"}}')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(guardrail.verificar(self.raiz), 1)

    def test_espelho_gerado_nao_conta_duas_vezes(self) -> None:
        self.commitar({".gitattributes": "espelho/** linguist-generated=true\n",
                       "app.py": "x = 1\n", "espelho/app.py": "x = 1\n"})
        for rel in ("app.py", "espelho/app.py"):
            (self.raiz / rel).write_text("x = 1  # noqa\n", encoding="utf-8")
        self.assertEqual(guardrail.regua_no_diff(self.raiz),
                         ["app.py — 1 supressão(ões) inline nova(s)"])
        with mock.patch.dict(sys.modules, {"qualidade": None}):  # sem o qualidade.py ao lado
            self.assertEqual(len(guardrail.regua_no_diff(self.raiz)), 2)

    def test_sem_prova_ao_lado_o_ponto_e_o_head(self) -> None:
        with mock.patch.dict(sys.modules, {"prova": None}):
            self.assertEqual(guardrail.ponto_da_base(self.raiz), "HEAD")


if __name__ == "__main__":
    unittest.main()
