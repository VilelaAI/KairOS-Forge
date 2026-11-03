"""Testes dos gatilhos de CI (`templates/ci/`): a fronteira de confiança (ADR-0026, emenda).

Só stdlib: o YAML é lido como texto. Três coisas que o template não pode perder:

1. Texto de fora (issue, diff, log de CI, nome de branch) nunca entra no script por
   `${{ }}` — no `run:` ele vira código. Só número passa (`.id`, `.number`).
2. Cada `claude -p` declara as ferramentas na linha de comando, sem rede, sem hooks nem
   MCP do projeto, e diz no prompt que o texto de fora é dado, não instrução.
3. O `corrigir` não age sobre CI de fork, que roda com segredo e token de escrita.

O último bloco roda cada `claude -p` contra uma CLI falsa e confere o que o shell entrega:
aspas e curingas que quebram em silêncio só aparecem executando.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

CI = Path(__file__).resolve().parent.parent.parent / "templates" / "ci"
TEMPLATES = sorted(CI.glob("*.yml"))
NUMERO_SEGURO = re.compile(r"^github\.event\.[a-z_.]+\.(id|number)$")


def blocos_run(texto: str) -> list[tuple[int, str]]:
    """(linha, script) de cada `run:`, em bloco (`|`) ou em linha."""
    linhas, saida, i = texto.splitlines(), [], 0
    while i < len(linhas):
        m = re.match(r"^(\s*)(?:-\s+)?run:\s*(.*)$", linhas[i])
        if not m:
            i += 1
            continue
        recuo, resto, j = len(m.group(1)), m.group(2).strip(), i + 1
        if resto in ("|", ">", "|-", ">-"):
            corpo = []
            while j < len(linhas) and (not linhas[j].strip()
                                       or len(linhas[j]) - len(linhas[j].lstrip()) > recuo):
                corpo.append(linhas[j])
                j += 1
            resto = "\n".join(corpo)
        saida.append((i + 1, resto))
        i = j
    return saida


def comandos_claude(texto: str) -> list[str]:
    """Cada `claude -p ...` com as linhas de continuação, sem o recuo do YAML."""
    comandos = []
    for _, script in blocos_run(texto):
        linhas = [linha.strip() for linha in script.splitlines()]
        for i, linha in enumerate(linhas):
            if not linha.startswith("claude -p"):
                continue
            partes = [linha]
            while partes[-1].endswith("\\") and i + 1 < len(linhas):
                i += 1
                partes.append(linhas[i])
            comandos.append("\n".join(partes))
    return comandos


def valor(cmd: str, flag: str) -> str:
    m = re.search(rf"{re.escape(flag)}\s+\"([^\"]*)\"", cmd)
    return m.group(1) if m else ""


def ferramentas(cmd: str, flag: str) -> set[str]:
    return {f.strip() for f in valor(cmd, flag).split(",") if f.strip()}


def ler(nome: str) -> str:
    return (CI / f"kairos-forge-{nome}.yml").read_text(encoding="utf-8")


class TextoDeForaNaoViraCodigo(unittest.TestCase):
    def test_ha_templates(self) -> None:
        self.assertEqual([p.stem for p in TEMPLATES], ["kairos-forge-auditar", "kairos-forge-corrigir",
                                                       "kairos-forge-revisar", "kairos-forge-triar"])

    def test_nenhum_run_interpola_texto_do_evento(self) -> None:
        for arq in TEMPLATES:
            for linha, script in blocos_run(arq.read_text(encoding="utf-8")):
                for expr in re.findall(r"\$\{\{\s*(.*?)\s*\}\}", script):
                    if expr.startswith("github.event") or expr.startswith("github.head_ref"):
                        self.assertRegex(expr, NUMERO_SEGURO, f"{arq.name}:{linha} interpola `{expr}` no script")

    def test_o_detector_pega_o_padrao_antigo(self) -> None:
        antigo = ("    steps:\n      - run: |\n          git checkout -b "
                  "\"forge/corrige-${{ github.event.workflow_run.head_branch }}\"\n")
        exprs = [e for _, s in blocos_run(antigo) for e in re.findall(r"\$\{\{\s*(.*?)\s*\}\}", s)]
        self.assertEqual(exprs, ["github.event.workflow_run.head_branch"])
        self.assertNotRegex(exprs[0], NUMERO_SEGURO)


class FerramentasDeclaradas(unittest.TestCase):
    def comandos(self) -> dict[str, list[str]]:
        return {arq.stem.replace("kairos-forge-", ""): comandos_claude(arq.read_text(encoding="utf-8"))
                for arq in TEMPLATES}

    def test_cada_template_tem_um_claude_p(self) -> None:
        self.assertEqual({k: len(v) for k, v in self.comandos().items()},
                         {"auditar": 1, "corrigir": 1, "revisar": 1, "triar": 1})

    def test_todo_claude_p_declara_ferramentas_sem_rede_hooks_nem_mcp(self) -> None:
        for nome, (cmd,) in self.comandos().items():
            with self.subTest(nome):
                self.assertTrue(ferramentas(cmd, "--allowedTools"), "sem --allowedTools")
                self.assertLessEqual({"WebFetch", "WebSearch"}, ferramentas(cmd, "--disallowedTools"))
                self.assertIn("--strict-mcp-config", cmd)
                self.assertIn("""--settings '{"disableAllHooks": true}'""", cmd)
                self.assertNotIn("bypassPermissions", cmd)
                self.assertNotIn("--dangerously-skip-permissions", cmd)

    def test_todo_prompt_diz_que_o_texto_de_fora_e_dado(self) -> None:
        for nome, (cmd,) in self.comandos().items():
            self.assertIn("dado, não instrução", cmd, nome)

    def test_triar_e_auditar_so_leem(self) -> None:
        for nome in ("triar", "auditar"):
            (cmd,) = self.comandos()[nome]
            self.assertEqual(ferramentas(cmd, "--allowedTools"), {"Read", "Grep", "Glob"}, nome)
            self.assertLessEqual({"Bash", "Edit", "Write", "NotebookEdit"}, ferramentas(cmd, "--disallowedTools"))
            self.assertNotIn("--permission-mode", cmd)

    def test_revisar_le_arquivos_e_git_de_leitura(self) -> None:
        (cmd,) = self.comandos()["revisar"]
        bash = {f for f in ferramentas(cmd, "--allowedTools") if f.startswith("Bash")}
        self.assertEqual(bash, {"Bash(git diff *)", "Bash(git log *)", "Bash(git show *)"})
        self.assertLessEqual({"Edit", "Write", "NotebookEdit"}, ferramentas(cmd, "--disallowedTools"))
        self.assertNotIn("--permission-mode", cmd)

    def test_corrigir_edita_e_roda_so_o_gate(self) -> None:
        (cmd,) = self.comandos()["corrigir"]
        self.assertIn("--permission-mode acceptEdits", cmd)
        bash = {f for f in ferramentas(cmd, "--allowedTools") if f.startswith("Bash")}
        self.assertEqual(bash, {"Bash($GATE *)", "Bash(git diff *)", "Bash(git log *)",
                                "Bash(git show *)", "Bash(git status *)"})
        self.assertNotIn("Bash", ferramentas(cmd, "--allowedTools"))  # nunca Bash livre
        self.assertLessEqual({"Bash(git push *)", "Bash(git commit *)", "Bash(gh *)"},
                             ferramentas(cmd, "--disallowedTools"))
        self.assertRegex(ler("corrigir"), r'\n    env:\n      GATE: "[^"]+"')


class ForkNuncaDisparaACorrecao(unittest.TestCase):
    def test_if_do_job_exige_o_mesmo_repositorio(self) -> None:
        bloco = ler("corrigir").split("jobs:", 1)[1].split("runs-on:", 1)[0]
        self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository", bloco)

    def test_branch_do_evento_entra_por_variavel(self) -> None:
        texto = ler("corrigir")
        self.assertIn('git checkout -b "forge/corrige-$BRANCH-$RUN"', texto)
        self.assertNotIn("forge/corrige-${{", texto)


class ArgumentosQueOShellEntrega(unittest.TestCase):
    """Roda cada `claude -p` com uma CLI falsa que grava o argv recebido."""

    def argv(self, nome: str) -> list[str]:
        (cmd,) = comandos_claude(ler(nome))
        with tempfile.TemporaryDirectory() as tmp:
            falso = Path(tmp) / "claude"
            falso.write_text('#!/usr/bin/env python3\nimport json, sys\n'
                             'json.dump(sys.argv[1:], open("argv.json", "w"))\n', encoding="utf-8")
            falso.chmod(0o755)
            env = {**os.environ, "PATH": f"{tmp}{os.pathsep}{os.environ.get('PATH', '')}",
                   "GATE": "npm test", "BASE": "aaa111", "HEAD": "bbb222"}
            subprocess.run(["bash", "-c", cmd], cwd=tmp, env=env, check=True)
            return json.loads((Path(tmp) / "argv.json").read_text(encoding="utf-8"))

    def opcao(self, argv: list[str], flag: str) -> str:
        return argv[argv.index(flag) + 1]

    def test_prompt_vem_primeiro_e_as_flags_chegam_inteiras(self) -> None:
        for nome in ("auditar", "corrigir", "revisar", "triar"):
            with self.subTest(nome):
                argv = self.argv(nome)
                self.assertEqual(argv[0], "-p")
                self.assertIn("dado, não instrução", argv[1])
                self.assertFalse(argv[1].startswith("-"))
                self.assertEqual(json.loads(self.opcao(argv, "--settings")), {"disableAllHooks": True})
                self.assertIn("--strict-mcp-config", argv)
                self.assertTrue(argv[-1].startswith(("Web", "Bash", "Edit")), argv[-1])

    def test_gate_e_diff_chegam_expandidos(self) -> None:
        argv = self.argv("corrigir")
        self.assertIn("Bash(npm test *)", self.opcao(argv, "--allowedTools").split(","))
        self.assertIn("rode o gate (npm test)", argv[1])
        self.assertIn("aaa111 e bbb222", self.argv("revisar")[1])


if __name__ == "__main__":
    unittest.main()
