"""execucao.py / telemetria.py — a trajetória: o que entra, o que nunca entra (ADR-0021/0030/0039)."""
from __future__ import annotations

import json
import sys
import unittest

from tests.apoio import RAIZ, Repositorio, eventos, rodar

SEGREDO = "sk-ant-api03-FAKE" + "x" * 48   # FAKE: o check de segredos exige o marcador


def hook(acao, raiz, **campos):
    base = {"session_id": "sessao-t", "cwd": str(raiz)}
    base.update(campos)
    r = rodar("execucao.py", acao, cwd=raiz, stdin=json.dumps(base))
    assert r.returncode == 0 and r.stdout == "", (r.returncode, r.stdout, r.stderr)
    return r


def bruto(raiz) -> str:
    return "".join(p.read_text(encoding="utf-8")
                   for p in (raiz / ".agents/execucoes").glob("*.jsonl"))


class TestOQueNuncaEntra(unittest.TestCase):
    def test_prompt_entra_como_contagem_e_skill_nunca_como_texto(self):
        with Repositorio() as raiz:
            hook("prompt", raiz, prompt=f"/kairos-forge:validar SPEC-001 senha=hunter2 {SEGREDO}")
            ev = eventos(raiz)[-1]
            self.assertEqual(ev["tipo"], "prompt")
            self.assertEqual(ev["skill"], "validar")
            self.assertGreater(ev["chars"], 10)
            self.assertNotIn("hunter2", bruto(raiz))
            self.assertNotIn(SEGREDO, bruto(raiz))
            self.assertNotIn("prompt", ev)

    def test_comando_e_redigido(self):
        with Repositorio() as raiz:
            hook("ferramenta", raiz, tool_name="Bash",
                 tool_input={"command": f"curl -H 'Authorization: Bearer {SEGREDO}' --password abc123x x"},
                 tool_response={"exit_code": 0})
            ev = eventos(raiz)[-1]
            self.assertEqual(ev["tipo"], "comando")
            self.assertNotIn(SEGREDO, bruto(raiz))
            self.assertNotIn("abc123x", bruto(raiz))
            self.assertIn("«redigido»", ev["cmd"])

    def test_delegacao_registra_o_alvo_e_nunca_o_prompt(self):
        with Repositorio() as raiz:
            hook("ferramenta", raiz, tool_name="Agent",
                 tool_input={"subagent_type": "lucas-backend", "description": "implementa X",
                             "prompt": "TEXTO-QUE-NAO-PODE-VAZAR"})
            ev = eventos(raiz)[-1]
            self.assertEqual((ev["tipo"], ev["alvo"]), ("delegacao", "lucas-backend"))
            self.assertNotIn("TEXTO-QUE-NAO-PODE-VAZAR", bruto(raiz))
            hook("ferramenta", raiz, tool_name="Skill", tool_input={"skill": "kairos-forge:validar"})
            self.assertEqual(eventos(raiz)[-1]["alvo"], "kairos-forge:validar")

    def test_caminho_fora_do_projeto_nao_expoe_a_maquina(self):
        with Repositorio() as raiz:
            hook("ferramenta", raiz, tool_name="Write",
                 tool_input={"file_path": "/home/alguem/segredos/pasta/arquivo.py"})
            ev = eventos(raiz)[-1]
            self.assertTrue(ev["arquivo"].startswith("…/"), ev["arquivo"])
            self.assertNotIn("/home/alguem", bruto(raiz))

    def test_sanear_derruba_chaves_proibidas_por_nome(self):
        sys.path.insert(0, str(RAIZ / "scripts"))
        import execucao  # noqa: E402
        saida = execucao.sanear({"tipo": "x", "prompt": "a", "model": "opus", "API_KEY": "k",
                                 "descricao": "d", "cmd": "ok"})
        self.assertEqual(set(saida), {"tipo", "cmd"})


class TestSubagentes(unittest.TestCase):
    def test_duracao_por_instancia_nao_por_tipo(self):
        """Dois teammates da mesma persona em paralelo não trocam de duração."""
        with Repositorio() as raiz:
            hook("subagente_inicio", raiz, agent_id="a-1", agent_type="lucas-backend")
            hook("subagente_inicio", raiz, agent_id="a-2", agent_type="lucas-backend")
            hook("subagente_fim", raiz, agent_id="a-1", agent_type="lucas-backend")
            fim = eventos(raiz)[-1]
            self.assertEqual((fim["tipo"], fim["agente_id"]), ("subagente_fim", "a-1"))
            self.assertIn("duracao_s", fim)
            self.assertGreaterEqual(fim["duracao_s"], 0)
            r = rodar("telemetria.py", "resumo", "--json", cwd=raiz)
            m = json.loads(r.stdout)
            self.assertEqual(m["subagentes_lancados"], 2)


class TestSubagenteEmSessaoLonga(unittest.TestCase):
    def test_inicio_antes_de_500_eventos_ainda_conta(self):
        with Repositorio() as raiz:
            hook("subagente_inicio", raiz, agent_id="longo", agent_type="ricardo-testes")
            for _ in range(500):
                hook("ferramenta", raiz, tool_name="Write", tool_input={"file_path": "src/a.py"})
            hook("subagente_fim", raiz, agent_id="longo", agent_type="ricardo-testes")
            self.assertIn("duracao_s", eventos(raiz)[-1])


class TestPatinacaoECorroboracao(unittest.TestCase):
    def _falha(self, raiz, cmd):
        hook("ferramenta", raiz, tool_name="Bash", tool_input={"command": cmd},
             tool_response={"exit_code": 1, "stdout": "1 failed"})

    def test_terceira_falha_identica_dispara_o_alerta_uma_vez(self):
        """repetida-01: após a 3ª falha idêntica a trajetória registra a patinação."""
        with Repositorio() as raiz:
            alertas = []
            for _ in range(4):
                self._falha(raiz, "npm test -- x")
                r = rodar("execucao.py", "alerta", cwd=raiz,
                          stdin=json.dumps({"session_id": "sessao-t", "cwd": str(raiz)}))
                alertas.append(r.stdout)
            self.assertEqual([bool(a) for a in alertas], [False, False, True, False],
                             "dispara exatamente quando o padrão fecha, não a cada turno")
            self.assertIn("3 vezes", alertas[2])

    def test_verificado_sem_execucao_nao_corrobora(self):
        """conclusao-02: `verificado: npm test -- x` sem o comando ter rodado."""
        with Repositorio() as raiz:
            r = rodar("telemetria.py", "corroborar", "npm test -- x", "--json", cwd=raiz)
            self.assertEqual(json.loads(r.stdout)["veredicto"], "nao_corroborado")
            hook("ferramenta", raiz, tool_name="Bash", tool_input={"command": "npm test -- x"},
                 tool_response={"exit_code": 0, "stdout": "3 passed"})
            r = rodar("telemetria.py", "corroborar", "npm test -- x", "--json", cwd=raiz)
            self.assertEqual(json.loads(r.stdout)["veredicto"], "corroborado")


class TestInvariantes(unittest.TestCase):
    def test_nunca_falha_a_sessao(self):
        with Repositorio() as raiz:
            for stdin in ("", "{nao json", '{"tool_input": 5}', "[]"):
                for acao in ("inicio", "prompt", "ferramenta", "subagente_fim", "fim", "alerta", "x"):
                    r = rodar("execucao.py", acao, cwd=raiz, stdin=stdin)
                    self.assertEqual((r.returncode, r.stdout), (0, ""), (acao, stdin, r.stderr))


if __name__ == "__main__":
    unittest.main()
