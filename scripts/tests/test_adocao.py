"""O guia de adoção por peça (`docs/adocao.md`) promete só o que existe.

Só stdlib. Duas coisas:

1. Cada comando do bloco "Sem instalar nada" roda num repositório git que nunca viu a
   fábrica (sem plugin, sem `/onboardar`, sem `.agents/`) e sai 0, sem traceback. É a
   promessa da seção: a peça funciona sozinha.
2. Toda skill, template de CI, script, subcomando, ADR e link que o guia cita existe.
   Guia que manda rodar o que sumiu ensina o time a não confiar no guia.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
GUIA = RAIZ / "docs" / "adocao.md"
NATIVOS = {"plugin"}          # comandos do próprio Claude Code citados no guia, não skills

CALC_BASE = "def soma(a, b):\n    return a + b\n"
CALC_FEAT = CALC_BASE + "\n\ndef dobro(x):\n    if x is None:\n        return 0\n    return soma(x, x)\n"
TESTE_BASE = ("import unittest\nfrom src.calc import soma\n\n\nclass T(unittest.TestCase):\n"
              "    def test_soma(self):\n        self.assertEqual(soma(1, 2), 3)\n")
TESTE_FEAT = TESTE_BASE + ("\n    def test_dobro(self):\n        from src.calc import dobro\n"
                           "        self.assertEqual(dobro(2), 4)\n")


def texto() -> str:
    return GUIA.read_text(encoding="utf-8")


def secao(titulo: str) -> str:
    corpo = texto().split(f"\n## {titulo}\n", 1)[1]
    return corpo.split("\n## ", 1)[0]


def comandos_avulsos() -> list[str]:
    blocos = re.findall(r"```bash\n(.*?)```", secao("Sem instalar nada"), re.S)
    return [linha.strip() for bloco in blocos for linha in bloco.splitlines()
            if linha.strip().startswith("python3 <plugin>/scripts/")]


class ComandosSemInstalarNada(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-adocao-")
        self.repo = Path(self._tmp.name)
        self.git("init", "-q", "-b", "main")
        self.escrever(CALC_BASE, TESTE_BASE)
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.git("checkout", "-qb", "feat")
        self.escrever(CALC_FEAT, TESTE_FEAT)
        self.git("commit", "-qam", "feat")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t",
                        *args], check=True, capture_output=True)

    def escrever(self, calc: str, teste: str) -> None:
        for pasta in ("src", "tests"):
            (self.repo / pasta).mkdir(exist_ok=True)
            (self.repo / pasta / "__init__.py").write_text("", encoding="utf-8")
        (self.repo / "src" / "calc.py").write_text(calc, encoding="utf-8")
        (self.repo / "tests" / "test_calc.py").write_text(teste, encoding="utf-8")

    def test_cada_comando_roda_num_repositorio_sem_a_fabrica(self) -> None:
        comandos = comandos_avulsos()
        self.assertGreaterEqual(len(comandos), 8)          # o leitor do guia achou o bloco
        env = {**os.environ, "GH_PROMPT_DISABLED": "1"}
        for linha in comandos:
            with self.subTest(linha):
                args = [a.replace("<plugin>", str(RAIZ)) for a in shlex.split(linha)]
                r = subprocess.run(args, cwd=self.repo, capture_output=True, text=True,
                                   timeout=120, env=env)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertNotIn("Traceback", r.stderr)
        self.assertFalse((self.repo / "CLAUDE.md").exists())   # ninguém pediu o onboarding


class ReferenciasDoGuia(unittest.TestCase):
    def test_skill_citada_existe(self) -> None:
        nomes = set(re.findall(r"`/([a-z][a-z-]+)[ `]", texto())) - NATIVOS
        # Os comandos que o mod do painel registra (ADR-0051) também são comandos da fábrica.
        do_mod = set(re.findall(r"name: '([a-z-]+)'",
                                (RAIZ / "hooks" / "painel.tsx").read_text(encoding="utf-8")))
        self.assertIn("entregar", nomes)
        self.assertIn("forge-painel", nomes & do_mod)
        for nome in sorted(nomes):
            with self.subTest(nome):
                self.assertTrue((RAIZ / "skills" / nome / "SKILL.md").is_file() or nome in do_mod)

    def test_template_script_e_doc_citados_existem(self) -> None:
        caminhos = set(re.findall(r"(?:templates/ci|docs)/[\w.-]+\.(?:yml|md)", texto()))
        caminhos |= {f"scripts/{s}" for s in re.findall(r"\b(\w+\.py)\b", texto())}
        self.assertIn("scripts/guardrail.py", caminhos)
        for caminho in sorted(caminhos):
            with self.subTest(caminho):
                self.assertTrue((RAIZ / caminho).is_file())

    def test_subcomando_citado_existe_no_script(self) -> None:
        pares = set(re.findall(r"\b(\w+\.py) (-{0,2}[a-z][\w-]*)", texto()))
        self.assertIn(("quadro.py", "ledger"), pares)
        for script, sub in sorted(pares):
            with self.subTest(f"{script} {sub}"):
                self.assertIn(f'"{sub}"', (RAIZ / "scripts" / script).read_text(encoding="utf-8"))

    def test_adr_e_link_citados_existem(self) -> None:
        for numero in sorted(set(re.findall(r"ADR-(\d{4})", texto()))):
            with self.subTest(f"ADR-{numero}"):
                self.assertTrue(list((RAIZ / "docs" / "adr").glob(f"{numero}-*.md")))
        for alvo in re.findall(r"\]\((?!https?:|#)([^)#]+)", texto()):
            with self.subTest(alvo):
                self.assertTrue((RAIZ / "docs" / alvo).exists())


if __name__ == "__main__":
    unittest.main()
