"""Testes do encaixe dos mods no plugin: o painel do arco (ADR-0051) e a pausa da faixa 3
na execução (ADR-0052).

Só stdlib. O comportamento dos mods é testado pelo kit do Claude Code
(`claude plugin test .`, em `tests/`); aqui fica o que tem de valer em qualquer máquina,
com ou sem o Claude Code instalado:

1. O manifesto não ganha chave que CLI antigo recusa. O Claude Code 2.0.77 recusa o
   `plugin.json` inteiro por uma chave que não conhece ("Unrecognized key: types") — e
   com ele iriam os guardrails da fábrica. A chave `modules` do `hooks.json` ele ignora
   (testado no 2.0.77, no 2.1.207 e no 2.1.286).
2. O módulo nomeado no `hooks.json` existe, na raiz e na cópia distribuída.
3. Os mods só apertam, no código:
   - o painel não escreve, não aprova nem recusa, não manda prompt e só roda o
     `painel.py`;
   - a pausa só pergunta: o único veredito que ela dá é `ask`, a recusa de baixo passa
     intacta e ela só roda o `guardrail.py faixa3`;
   - nenhum dos dois devolve `allow`.

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

# O que um mod poderia chamar e estes não chamam: escrever, mandar prompt, rodar comando
# ou agente, mudar settings ou ambiente, chamar modelo.
PROIBIDO = re.compile(
    r"\$\.(fs\.(write|remove|rm|mkdir|rename|copy)|tool\.(call|check|register)"
    r"|prompt\.(submit|fill|paint)|session\.append|agent\.(spawn|register)"
    r"|command\.run|settings|env\.set|model\.|store\.set|network|audio)"
    r"|on\(\s*['\"](prompt\.submit|session\.append|classic\.)")
# Decidir sobre uma chamada é da pausa, e só no sentido de apertar.
DECIDE = re.compile(r"on\(\s*['\"]tool\.check|\bdecision\b|\bdeny\b")


def codigo(caminho: Path) -> str:
    """O fonte sem os comentários de linha, que podem citar o que o código não faz."""
    return "\n".join(re.sub(r"(^|\s)//.*$", "", linha) for linha in
                     caminho.read_text(encoding="utf-8").splitlines())


def fontes() -> list[Path]:
    return sorted([*HOOKS.glob("*.ts"), *HOOKS.glob("*.tsx")])


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
                self.assertEqual(hooks["modules"], ["./mod.ts"])
                for nome in ("mod.ts", "painel.tsx", "vista.ts", "pausa.ts"):
                    self.assertTrue((base / "hooks" / nome).is_file(), nome)
                self.assertTrue((base / "types/index.d.ts").is_file())

    def test_a_entrada_liga_os_dois_mods(self) -> None:
        entrada = codigo(HOOKS / "mod.ts")
        self.assertIn("registrarPainel(on)", entrada)
        self.assertIn("registrarPausa(on)", entrada)

    def test_nenhum_mod_escreve_nem_manda_prompt(self) -> None:
        self.assertTrue(fontes())
        for fonte in fontes():
            with self.subTest(fonte.name):
                self.assertEqual(PROIBIDO.findall(codigo(fonte)), [])

    def test_so_a_pausa_decide_e_so_pergunta(self) -> None:
        for fonte in fontes():
            with self.subTest(fonte.name):
                texto = codigo(fonte)
                self.assertNotIn("'allow'", texto)           # nenhum mod libera nada
                if fonte.name != "pausa.ts":
                    self.assertEqual(DECIDE.findall(texto), [])
        pausa = codigo(HOOKS / "pausa.ts")
        self.assertEqual(re.findall(r"decision: '(\w+)'", pausa), ["ask"])
        self.assertIn("if (abaixo.decision === 'deny' || e.isReadOnly) return abaixo", pausa)
        self.assertEqual(pausa.count(".catch(($, e, next) => next(e))"), 1)

    def test_cada_mod_so_roda_o_seu_script(self) -> None:
        for nome, script in (("painel.tsx", "/scripts/painel.py`"),
                             ("pausa.ts", "/scripts/guardrail.py`, 'faixa3'")):
            with self.subTest(nome):
                texto = codigo(HOOKS / nome)
                runs = re.findall(r"\$\.process\.(run|spawn)\((.*)", texto)
                self.assertEqual(len(runs), 1)
                self.assertIn(script, runs[0][1])
        self.assertNotIn("--html", codigo(HOOKS / "painel.tsx"))   # o modo do painel.py que escreve

    def test_gancho_em_tool_call_deixa_passar_ate_quando_falha(self) -> None:
        mod = codigo(HOOKS / "painel.tsx")
        ganchos = len(re.findall(r"on\('tool\.call'", mod))
        self.assertGreater(ganchos, 0)
        self.assertEqual(mod.count(".catch(($, e, next) => next(e))"), ganchos)
        self.assertEqual(len(re.findall(r"await next\(e\)", mod)), ganchos + 1)  # + turn.complete


if __name__ == "__main__":
    unittest.main()
