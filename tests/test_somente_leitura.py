"""Scripts que só leem não podem escrever — hash da árvore antes e depois (ADR-0039).

`painel.py` é "renderização, nunca estado"; `telemetria.py resumo`, `grafo.py validar` e
`diagnostico.py coletar` são medição. A frase está no CLAUDE.md; aqui ela vira teste.
"""
from __future__ import annotations

import json
import unittest

from tests.apoio import Repositorio, assinatura_da_arvore, escrever, fence, rodar


def projeto_minimo(raiz):
    escrever(raiz, "docs/specs/SPEC-001-login.md",
             "# SPEC-001\n\n| ID | Requisito | Prioridade | Status | Verificação |\n"
             "|---|---|---|---|---|\n| EXP-01 | login | P1 | Concluído | verificado: npm test (06/09) |\n")
    escrever(raiz, "docs/specs/validacoes/VALIDACAO-SPEC-001-2026-09-06.md",
             fence("kairos-validacao", {"veredicto": "aprovado", "bloqueios": 0, "verificado": ["EXP-01"]}))
    escrever(raiz, ".agents/execucoes/2026-09.jsonl",
             json.dumps({"t": "2026-09-06T10:00:00+00:00", "sessao": "s1", "tipo": "prompt",
                         "skill": "validar", "chars": 20}) + "\n" +
             json.dumps({"t": "2026-09-06T10:01:00+00:00", "sessao": "s1", "tipo": "comando",
                         "cmd": "npm test", "gate": "teste", "ok": True}) + "\n")
    escrever(raiz, "src/app.py", "print('x')\n")
    escrever(raiz, ".agents/grafo/entidades.jsonl",
             json.dumps({"id": "login", "tipo": "componente", "nome": "Login", "fonte": "docs/specs/SPEC-001-login.md"}) + "\n")
    escrever(raiz, ".agents/grafo/relacoes.jsonl", "")
    rodar("ciclo.py", "abrir", "SPEC-001", "--spec-aprovada", cwd=raiz)
    rodar("quadro.py", "abrir", "forge-x", "--spec", "SPEC-001", cwd=raiz)


class TestSomenteLeitura(unittest.TestCase):
    def test_leitores_nao_mudam_a_arvore(self):
        comandos = [
            ("painel.py", []), ("painel.py", ["SPEC-001"]), ("painel.py", ["--json"]),
            ("telemetria.py", ["resumo"]), ("telemetria.py", ["sessoes"]),
            ("telemetria.py", ["corroborar", "npm test", "--json"]),
            ("grafo.py", ["validar"]), ("grafo.py", ["diagnosticar"]),
            ("diagnostico.py", ["coletar", ".", "--json"]),
            ("ciclo.py", ["estado", "SPEC-001", "--json"]), ("ciclo.py", ["listar"]),
            ("quadro.py", ["estado", "forge-x", "--json"]), ("quadro.py", ["ledger", "forge-x"]),
            ("quadro.py", ["listar"]), ("contrato.py", ["esquema"]),
            ("guardrail.py", ["verificar", "."]),
        ]
        with Repositorio() as raiz:
            projeto_minimo(raiz)
            antes = assinatura_da_arvore(raiz)
            for script, args in comandos:
                with self.subTest(script=script, args=args):
                    r = rodar(script, *args, cwd=raiz)
                    self.assertIn(r.returncode, (0, 1), f"{script} {args}: {r.stderr[-300:]}")
                    self.assertEqual(assinatura_da_arvore(raiz), antes,
                                     f"{script} {args} escreveu na árvore")

    def test_painel_html_escreve_so_o_arquivo_pedido(self):
        with Repositorio() as raiz:
            projeto_minimo(raiz)
            antes = assinatura_da_arvore(raiz)
            r = rodar("painel.py", "--html", "painel.html", cwd=raiz)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((raiz / "painel.html").is_file())
            (raiz / "painel.html").unlink()
            self.assertEqual(assinatura_da_arvore(raiz), antes)


if __name__ == "__main__":
    unittest.main()
