"""Testes da medição da linha: a chave sessão ↔ SPEC e o tempo de espera por estado.

Só stdlib. Origem: a aula 5 do Tech Leads Club (Fábricas Agênticas) — o trabalho passa a
maior parte do tempo esperando alguém, e o custo só soma por tarefa com uma chave comum.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import execucao  # noqa: E402
import telemetria  # noqa: E402


def git(raiz: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(raiz), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       check=True, capture_output=True, text=True)
    return r.stdout.strip()


def fim(sessao: str, novos_saida: int, branch: str | None = None, cache: int = 0) -> dict:
    ev = {"t": "2026-11-04T10:00:00+00:00", "sessao": sessao, "tipo": "sessao_fim",
          "tokens": {"entrada": 0, "cache_escrita": 0, "cache_leitura": cache,
                     "saida": novos_saida, "respostas": 1}}
    return {**ev, "branch": branch} if branch else ev


class Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-linha-")
        self.raiz = Path(self._tmp.name).resolve()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def ciclo(self, spec: str, branch: str | None, historico: list[tuple[str, str]],
              estado: str | None = None) -> None:
        pasta = self.raiz / ".agents" / "ciclo"
        pasta.mkdir(parents=True, exist_ok=True)
        hist = [{"t": t, "de": None, "para": para} for para, t in historico]
        (pasta / f"{spec}.json").write_text(json.dumps({
            "spec": spec, "branch": branch, "estado": estado or historico[-1][0],
            "historico": hist}), encoding="utf-8")


class BranchNoHook(Tmp):
    def test_branch_do_checkout_do_worktree_e_destacado(self) -> None:
        git(self.raiz, "init", "-q", "-b", "main", ".")
        git(self.raiz, "commit", "-q", "--allow-empty", "-m", "base")
        git(self.raiz, "checkout", "-q", "-b", "agent/limite-tamanho")
        (self.raiz / "sub").mkdir()
        self.assertEqual(execucao.branch_atual(str(self.raiz / "sub")), "agent/limite-tamanho")
        wt = self.raiz.parent / (self.raiz.name + "-wt")
        git(self.raiz, "worktree", "add", "-q", "-b", "forge/t2", str(wt))
        try:
            self.assertEqual(execucao.branch_atual(str(wt)), "forge/t2")
        finally:
            git(self.raiz, "worktree", "remove", "--force", str(wt))
        git(self.raiz, "checkout", "-q", "--detach")
        self.assertIsNone(execucao.branch_atual(str(self.raiz)))

    def test_sem_cwd_no_payload_nao_le_o_diretorio_do_processo(self) -> None:
        self.assertNotIn("branch", execucao.ev_fim({}))
        self.assertNotIn("branch", execucao.ev_inicio({}))

    def test_fora_de_git_nao_quebra_o_hook(self) -> None:
        self.assertIsNone(execucao.branch_atual(str(self.raiz)))
        self.assertEqual(execucao.ev_inicio({"cwd": str(self.raiz)}),
                         {"tipo": "sessao_inicio", "origem": "?"})

    def test_inicio_e_fim_gravam_o_branch(self) -> None:
        git(self.raiz, "init", "-q", "-b", "feat/SPEC-012-x", ".")
        self.assertEqual(execucao.ev_inicio({"cwd": str(self.raiz)})["branch"], "feat/SPEC-012-x")
        self.assertEqual(execucao.ev_fim({"cwd": str(self.raiz)})["branch"], "feat/SPEC-012-x")

    def test_prompt_guarda_so_o_id_da_spec(self) -> None:
        ev = execucao.ev_prompt({"prompt": "continua a spec-007 e depois SPEC-002; a SPEC-007 é a principal"})
        self.assertEqual(ev["specs"], ["SPEC-002", "SPEC-007"])
        self.assertNotIn("specs", execucao.ev_prompt({"prompt": "sem id aqui"}))


class CustoPorSpec(Tmp):
    def test_chave_pelo_ciclo_pelo_branch_pelo_prompt_e_sem_chave(self) -> None:
        self.ciclo("SPEC-002", "agent/limite-tamanho", [("construindo", "2026-11-04T09:00:00+00:00")])
        eventos = [
            {"sessao": "s1", "tipo": "sessao_inicio", "branch": "main"},
            fim("s1", 100, branch="agent/limite-tamanho"),        # trocou de branch no meio
            fim("s2", 50, branch="feat/spec-007-exportar"),
            {"sessao": "s3", "tipo": "prompt", "specs": ["SPEC-009"]},
            fim("s3", 30),
            fim("s4", 7, branch="main"),
            fim("s5", 20, branch="agent/limite-tamanho", cache=1000),
        ]
        r = telemetria.tokens_por_spec(eventos, self.raiz)
        self.assertTrue(r["medido"])
        self.assertEqual(list(r["specs"]), ["SPEC-002", "SPEC-007", "SPEC-009", "sem SPEC"])
        self.assertEqual(r["specs"]["SPEC-002"],
                         {"sessoes": 2, "novos": 120, "cache_lido": 1000, "por": {"ciclo": 2}})
        self.assertEqual(r["specs"]["SPEC-007"]["por"], {"branch": 1})
        self.assertEqual(r["specs"]["SPEC-009"]["por"], {"prompt": 1})
        self.assertEqual(r["specs"]["sem SPEC"], {"sessoes": 1, "novos": 7, "cache_lido": 0,
                                                  "por": {"sem chave": 1}})

    def test_sem_leitura_e_nao_medido_e_nao_zero(self) -> None:
        r = telemetria.tokens_por_spec([{"sessao": "s1", "tipo": "prompt"}], self.raiz)
        self.assertEqual(r, {"medido": False, "specs": {}})
        with contextlib.redirect_stdout(io.StringIO()) as out:
            telemetria.cmd_por_spec([], self.raiz, False)
        self.assertIn("não medidos", out.getvalue())


class EsperaPorEstado(Tmp):
    AGORA = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)

    def test_trabalho_espera_maior_espera_e_voltas(self) -> None:
        self.ciclo("SPEC-002", "b", [
            ("enquadrando", "2026-11-03T08:00:00+00:00"),
            ("aguardando_aprovacao", "2026-11-03T09:00:00+00:00"),   # 10 h esperando
            ("construindo", "2026-11-03T19:00:00+00:00"),            # 2 h
            ("validando", "2026-11-03T21:00:00+00:00"),              # 1 h
            ("corrigindo_validacao", "2026-11-03T22:00:00+00:00"),   # 1 h
            ("validando", "2026-11-03T23:00:00+00:00"),              # 1 h
            ("pronto_para_pr", "2026-11-04T00:00:00+00:00"),         # 12 h até agora
        ])
        (l,) = telemetria.espera_dos_ciclos(self.raiz, None, self.AGORA)["ciclos"]
        self.assertEqual((l["lead_h"], l["trabalho_h"], l["espera_h"], l["espera_pct"]),
                         (28.0, 6.0, 22.0, 79))
        self.assertEqual(l["maior_espera"], {"estado": "pronto_para_pr", "h": 12.0})
        self.assertEqual(l["voltas"], {"spec": 0, "validacao": 1, "revisao": 0})

    def test_terminal_para_o_relogio_e_janela_filtra_so_os_fechados(self) -> None:
        self.ciclo("SPEC-001", None, [("construindo", "2026-09-01T00:00:00+00:00"),
                                      ("encerrado", "2026-09-01T05:00:00+00:00")])
        self.ciclo("SPEC-003", None, [("aguardando_entendimento", "2026-09-01T00:00:00+00:00")])
        r = telemetria.espera_dos_ciclos(self.raiz, None, self.AGORA)
        fechado = next(l for l in r["ciclos"] if l["spec"] == "SPEC-001")
        self.assertEqual((fechado["lead_h"], fechado["espera_h"]), (5.0, 0.0))
        r7 = telemetria.espera_dos_ciclos(self.raiz, 7, self.AGORA)
        self.assertEqual([l["spec"] for l in r7["ciclos"]], ["SPEC-003"])   # aberto sempre entra

    def test_saida_de_texto_por_ciclo_e_total(self) -> None:
        self.ciclo("SPEC-005", "b", [("aguardando_aprovacao", "2026-11-04T08:00:00+00:00"),
                                     ("construindo", "2026-11-04T10:00:00+00:00"),
                                     ("revisando", "2026-11-04T11:00:00+00:00"),
                                     ("corrigindo_revisao", "2026-11-04T11:30:00+00:00"),
                                     ("encerrado", "2026-11-04T12:00:00+00:00")])
        self.ciclo("SPEC-006", "c", [("construindo", "2026-11-04T09:00:00+00:00"),
                                     ("encerrado", "2026-11-04T10:00:00+00:00")])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            telemetria.cmd_espera(self.raiz, None, False)
        texto = out.getvalue()
        self.assertIn("SPEC-005", texto)
        self.assertIn("esperando pessoa 2,0 h (50%)", texto)
        self.assertIn("maior espera: aguardando_aprovacao 2,0 h", texto)
        self.assertIn("voltas: revisao 1", texto)
        self.assertIn("voltas: nenhuma", texto)          # SPEC-006: sem correção nem espera
        self.assertIn("Total: 2 ciclo(s), esperando pessoa 40% do tempo", texto)

    def test_sem_ciclo_diz_isso_e_historico_ruim_nao_quebra(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(telemetria.cmd_espera(self.raiz, None, False), 0)
        self.assertIn("nenhum ciclo", out.getvalue())
        self.ciclo("SPEC-004", None, [("construindo", "não é data")])
        self.assertEqual(telemetria.espera_dos_ciclos(self.raiz, None, self.AGORA)["ciclos"], [])


class Despacho(Tmp):
    def test_ruido_espera_e_por_spec_pela_cli(self) -> None:
        import os
        antes, argv = os.getcwd(), sys.argv
        os.chdir(self.raiz)
        try:
            for cmd in ("ruido", "espera", "por-spec", "tokens", "sessoes"):
                sys.argv = ["telemetria.py", cmd, "--json"] if cmd != "sessoes" else ["telemetria.py", cmd]
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(telemetria.main(), 0, cmd)
        finally:
            os.chdir(antes)
            sys.argv = argv


if __name__ == "__main__":
    unittest.main()
