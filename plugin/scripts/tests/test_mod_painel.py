"""Testes do encaixe do mod do painel do arco no plugin (ADR-0051).

Só stdlib. O comportamento do mod é testado pelo kit do Claude Code
(`claude plugin test .`, em `tests/painel.test.tsx`); aqui fica o que tem de valer em
qualquer máquina, com ou sem o Claude Code instalado:

1. O manifesto não ganha chave que CLI antigo recusa. O Claude Code 2.0.77 recusa o
   `plugin.json` inteiro por uma chave que não conhece ("Unrecognized key: types") — e
   com ele iriam os guardrails da fábrica. A chave `modules` do `hooks.json` ele ignora
   (testado no 2.0.77, no 2.1.207 e no 2.1.286).
2. O módulo nomeado no `hooks.json` existe, na raiz e na cópia distribuída.
3. O mod é só leitura, no código: nenhuma chamada que escreve, aprova, recusa, manda
   prompt ou roda outra coisa que não o `painel.py`.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
HOOKS = RAIZ / "hooks"

# As chaves de `plugin.json` que o manifesto da fábrica usa hoje, todas aceitas pelo
# 2.0.77. Chave nova aqui só depois de carregar o plugin num CLI antigo.
CHAVES_DO_MANIFESTO = {"name", "version", "description", "author", "homepage",
                       "repository", "license", "keywords"}

# O que um mod poderia chamar e este não chama: escrever, aprovar ou recusar, mandar
# prompt, rodar comando ou agente, mudar settings ou ambiente, chamar modelo.
PROIBIDO = re.compile(
    r"\$\.(fs\.(write|remove|rm|mkdir|rename|copy)|tool\.(call|check|register)"
    r"|prompt\.(submit|fill|paint)|session\.append|agent\.(spawn|register)"
    r"|command\.run|settings|env\.set|model\.|store\.set|network|audio)"
    r"|on\(\s*['\"](tool\.check|prompt\.submit|session\.append|classic\.)"
    r"|\bdeny\b|\bdecision\b")


def codigo(caminho: Path) -> str:
    """O fonte sem os comentários de linha, que podem citar o que o código não faz."""
    return "\n".join(re.sub(r"(^|\s)//.*$", "", linha) for linha in
                     caminho.read_text(encoding="utf-8").splitlines())


class Encaixe(unittest.TestCase):
    def test_manifesto_so_com_chaves_que_cli_antigo_aceita(self) -> None:
        for base in (RAIZ, RAIZ / "plugin"):
            with self.subTest(str(base)):
                manifesto = json.loads((base / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
                self.assertLessEqual(set(manifesto), CHAVES_DO_MANIFESTO)

    def test_modulo_do_hooks_json_existe_na_raiz_e_na_copia(self) -> None:
        for base in (RAIZ, RAIZ / "plugin"):
            with self.subTest(str(base)):
                hooks = json.loads((base / "hooks/hooks.json").read_text(encoding="utf-8"))
                self.assertLessEqual(set(hooks), {"hooks", "modules", "description"})
                self.assertEqual(hooks["modules"], ["./painel.tsx"])
                for nome in ("painel.tsx", "vista.ts"):
                    self.assertTrue((base / "hooks" / nome).is_file(), nome)
                self.assertTrue((base / "types/index.d.ts").is_file())

    def test_o_mod_e_so_leitura(self) -> None:
        fontes = sorted([*HOOKS.glob("*.ts"), *HOOKS.glob("*.tsx")])
        self.assertTrue(fontes)
        for fonte in fontes:
            with self.subTest(fonte.name):
                self.assertEqual(PROIBIDO.findall(codigo(fonte)), [])

    def test_so_roda_o_painel_e_sem_escrever_arquivo(self) -> None:
        mod = codigo(HOOKS / "painel.tsx")
        runs = re.findall(r"\$\.process\.(run|spawn)\((.*)", mod)
        self.assertEqual(len(runs), 1)
        self.assertIn("/scripts/painel.py`", runs[0][1])
        self.assertNotIn("--html", mod)          # o único modo do painel.py que escreve

    def test_gancho_em_tool_call_deixa_passar_ate_quando_falha(self) -> None:
        mod = codigo(HOOKS / "painel.tsx")
        ganchos = len(re.findall(r"on\('tool\.call'", mod))
        self.assertGreater(ganchos, 0)
        self.assertEqual(mod.count(".catch(($, e, next) => next(e))"), ganchos)
        self.assertEqual(len(re.findall(r"await next\(e\)", mod)), ganchos + 1)  # + turn.complete


if __name__ == "__main__":
    unittest.main()
