"""quadro.py — o quadro de tarefas, testado como CLI (ADR-0035/0036/0040)."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from tests.apoio import RAIZ, Repositorio, escrever, git, rodar

Q = ".agents/quadro/forge-x.json"


def q(raiz, *args, ok=True):
    r = rodar("quadro.py", *args, cwd=raiz)
    if ok:
        assert r.returncode == 0, f"{args}: rc={r.returncode}\n{r.stdout}\n{r.stderr}"
    return r


def vista(raiz):
    return json.loads(q(raiz, "estado", "forge-x", "--json").stdout)


def tarefa(raiz, tid, posse, depende="", **extra):
    args = ["adicionar", "forge-x", "--id", tid, "--titulo", f"tarefa {tid}",
            "--dono", "lucas-backend", "--posse", posse, "--pronto-quando", "teste passa",
            "--reverter", "git revert <sha>"]
    if depende:
        args += ["--depende", depende]
    for k, v in extra.items():
        args += [f"--{k.replace('_', '-')}", str(v)]
    return q(raiz, *args)


def envelhecer(raiz, tid, minutos=10):
    p = raiz / Q
    d = json.loads(p.read_text(encoding="utf-8"))
    passado = datetime.now(timezone.utc) - timedelta(minutes=minutos)
    d["tasks"][tid]["iniciado_em"] = passado.isoformat(timespec="seconds")
    p.write_text(json.dumps(d), encoding="utf-8")


class TestOndaEPosse(unittest.TestCase):
    def test_teto_de_onda_nao_devolve_o_setimo(self):
        with Repositorio() as raiz:
            q(raiz, "abrir", "forge-x", "--cli", "claude-code")
            for i in range(1, 8):
                tarefa(raiz, f"T{i}", f"src/m{i}/**")
            prontas = json.loads(q(raiz, "prontas", "forge-x", "--json").stdout)
            self.assertEqual(len(prontas["prontas"]), 6)
            self.assertIn("teto de onda", prontas["fora"]["T7"])
            self.assertEqual(vista(raiz)["cli"], "claude-code")

    def test_posse_sobreposta_nunca_sai_na_mesma_onda(self):
        with Repositorio() as raiz:
            q(raiz, "abrir", "forge-x")
            tarefa(raiz, "T1", "src/api/**")
            r = tarefa(raiz, "T2", "src/api/*")
            self.assertIn("posse sobreposta", r.stdout)
            prontas = json.loads(q(raiz, "prontas", "forge-x", "--json").stdout)["prontas"]
            self.assertEqual(len(prontas), 1)
            # Refinamento por caminho é a exceção declarada: o mais fundo manda.
            tarefa(raiz, "T3", "src/api/auth/**")
            tarefa(raiz, "T4", "src/web/**")
            self.assertEqual(len(json.loads(q(raiz, "prontas", "forge-x", "--json").stdout)["prontas"]), 3)
            q(raiz, "depender", "forge-x", "T2", "--de", "T1")
            self.assertEqual(vista(raiz)["tasks"]["T2"]["depende"], ["T1"])

    def test_iniciar_fora_da_onda_e_recusado(self):
        with Repositorio() as raiz:
            q(raiz, "abrir", "forge-x")
            tarefa(raiz, "T1", "a/**")
            tarefa(raiz, "T2", "b/**", depende="T1")
            antes = (raiz / Q).read_bytes()
            r = q(raiz, "iniciar", "forge-x", "T2", ok=False)
            self.assertEqual(r.returncode, 1)
            self.assertEqual((raiz / Q).read_bytes(), antes)

    def test_dependencia_inexistente_e_ciclo_sao_recusados(self):
        with Repositorio() as raiz:
            q(raiz, "abrir", "forge-x")
            r = q(raiz, "adicionar", "forge-x", "--id", "T1", "--titulo", "t", "--dono", "x",
                  "--posse", "a/**", "--pronto-quando", "ok", "--depende", "T9", ok=False)
            self.assertEqual(r.returncode, 1)
            self.assertFalse(json.loads((raiz / Q).read_text())["tasks"])
            tarefa(raiz, "T1", "a/**")
            tarefa(raiz, "T2", "b/**", depende="T1")
            r = q(raiz, "depender", "forge-x", "T1", "--de", "T2", ok=False)
            self.assertEqual(r.returncode, 1)
            self.assertIn("ciclo", r.stdout)


class TestProvaDeTrabalho(unittest.TestCase):
    """ADR-0040: concluir recusa DONE que o git não enxerga."""

    def _pronta_em_voo(self, raiz):
        q(raiz, "abrir", "forge-x")
        tarefa(raiz, "T1", "src/**")
        q(raiz, "iniciar", "forge-x", "T1")

    def test_sem_evidencia_ou_sem_gate_e_recusado(self):
        with Repositorio() as raiz:
            self._pronta_em_voo(raiz)
            antes = (raiz / Q).read_bytes()
            r = q(raiz, "concluir", "forge-x", "T1", "--evidencia", " ", "--gate-ok", ok=False)
            self.assertEqual(r.returncode, 1)
            r = q(raiz, "concluir", "forge-x", "T1", "--evidencia", "x", ok=False)
            self.assertEqual(r.returncode, 1)
            self.assertEqual((raiz / Q).read_bytes(), antes)

    def test_done_sem_commit_e_sem_diff_e_recusado(self):
        with Repositorio() as raiz:
            self._pronta_em_voo(raiz)
            antes = (raiz / Q).read_bytes()
            r = q(raiz, "concluir", "forge-x", "T1", "--evidencia", "fiz", "--gate-ok", ok=False)
            self.assertEqual(r.returncode, 1)
            self.assertIn("sem prova de trabalho", r.stdout)
            self.assertEqual((raiz / Q).read_bytes(), antes)

    def test_diff_nos_arquivos_de_posse_prova(self):
        with Repositorio() as raiz:
            self._pronta_em_voo(raiz)
            escrever(raiz, "src/novo.py", "print(1)\n")
            r = q(raiz, "concluir", "forge-x", "T1", "--evidencia", "fiz", "--gate-ok")
            self.assertIn("diff em", vista(raiz)["tasks"]["T1"]["prova_trabalho"])

    def test_diff_fora_da_posse_nao_prova(self):
        with Repositorio() as raiz:
            self._pronta_em_voo(raiz)
            escrever(raiz, "docs/outro.md", "x\n")
            r = q(raiz, "concluir", "forge-x", "T1", "--evidencia", "fiz", "--gate-ok", ok=False)
            self.assertEqual(r.returncode, 1)

    def test_head_avancado_prova(self):
        with Repositorio() as raiz:
            self._pronta_em_voo(raiz)
            escrever(raiz, "src/a.py", "x\n")
            git(raiz, "add", "-A")
            git(raiz, "commit", "-q", "-m", "feat: a")
            q(raiz, "concluir", "forge-x", "T1", "--evidencia", "commit", "--gate-ok")
            self.assertIn("HEAD avançou", vista(raiz)["tasks"]["T1"]["prova_trabalho"])

    def test_sem_diff_declarado_e_registrado(self):
        with Repositorio() as raiz:
            self._pronta_em_voo(raiz)
            q(raiz, "concluir", "forge-x", "T1", "--evidencia", "decisão registrada",
              "--gate-pulado", "sem gate", "--sem-diff", "tarefa de análise")
            self.assertIn("declarado sem diff", vista(raiz)["tasks"]["T1"]["prova_trabalho"])

    def test_fora_de_git_nao_verifica_e_avisa(self):
        with Repositorio(com_git=False) as raiz:
            self._pronta_em_voo(raiz)
            r = q(raiz, "concluir", "forge-x", "T1", "--evidencia", "fiz", "--gate-ok")
            self.assertIn("sem repositório git", r.stdout)

    def test_posse_ignorada_pelo_git_avisa_na_insercao(self):
        with Repositorio() as raiz:
            escrever(raiz, ".gitignore", "build/\n")
            q(raiz, "abrir", "forge-x")
            r = tarefa(raiz, "T1", "build/**")
            self.assertIn("posse ignorada pelo git", r.stdout)


class TestVarrerEPosseDoProcesso(unittest.TestCase):
    """ADR-0036/0040: prazo vencido libera a vaga só quando o processo comprovadamente morreu."""

    def test_vencida_sem_pid_e_bloqueada_com_posse_nao_provada(self):
        with Repositorio() as raiz:
            q(raiz, "abrir", "forge-x", "--tempo-limite", "1")
            tarefa(raiz, "T1", "a/**")
            q(raiz, "iniciar", "forge-x", "T1")
            envelhecer(raiz, "T1")
            self.assertEqual(vista(raiz)["vencidas"], ["T1"])
            r = q(raiz, "varrer", "forge-x")
            t = vista(raiz)["tasks"]["T1"]
            self.assertEqual(t["estado"], "bloqueada")
            self.assertIn("sem pid", t["processo"])
            self.assertIn("1 vaga(s) liberada(s)", r.stdout)

    def test_dry_run_nao_altera(self):
        with Repositorio() as raiz:
            q(raiz, "abrir", "forge-x", "--tempo-limite", "1")
            tarefa(raiz, "T1", "a/**")
            q(raiz, "iniciar", "forge-x", "T1")
            envelhecer(raiz, "T1")
            antes = (raiz / Q).read_bytes()
            q(raiz, "varrer", "forge-x", "--dry-run")
            self.assertEqual((raiz / Q).read_bytes(), antes)

    def test_processo_vivo_e_encerrado_antes_de_liberar_a_vaga(self):
        with Repositorio() as raiz:
            q(raiz, "abrir", "forge-x", "--tempo-limite", "1")
            tarefa(raiz, "T1", "a/**")
            # Worker que ignora TERM: só KILL derruba. O varrer precisa dos dois.
            worker = subprocess.Popen(
                [sys.executable, "-c",
                 "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                 "time.sleep(300)"],
                start_new_session=True)
            try:
                q(raiz, "iniciar", "forge-x", "T1", "--pid", str(worker.pid))
                envelhecer(raiz, "T1")
                r = q(raiz, "varrer", "forge-x")
                fim = time.monotonic() + 5
                while worker.poll() is None and time.monotonic() < fim:
                    time.sleep(0.1)
                self.assertIsNotNone(worker.poll(), "o worker deveria ter sido morto")
                t = vista(raiz)["tasks"]["T1"]
                self.assertEqual(t["estado"], "bloqueada")
                self.assertIn("encerrado", t["processo"])
            finally:
                if worker.poll() is None:
                    worker.kill()

    def test_processo_que_sobrevive_retem_a_vaga(self):
        with Repositorio() as raiz:
            q(raiz, "abrir", "forge-x", "--tempo-limite", "1")
            tarefa(raiz, "T1", "a/**")
            q(raiz, "iniciar", "forge-x", "T1", "--pid", str(os.getpid()))
            envelhecer(raiz, "T1")
            sys.path.insert(0, str(RAIZ / "scripts"))
            import quadro  # noqa: E402
            cwd = os.getcwd()
            os.chdir(raiz)
            try:
                import argparse
                import contextlib
                import io
                with mock.patch.object(quadro, "encerrar_processo", return_value="vivo"), \
                        contextlib.redirect_stdout(io.StringIO()):
                    rc = quadro.cmd_varrer(argparse.Namespace(slug="forge-x", dry_run=False))
            finally:
                os.chdir(cwd)
            self.assertEqual(rc, 1)
            t = vista(raiz)["tasks"]["T1"]
            self.assertEqual(t["estado"], "em_progresso", "vaga retida, não liberada")
            self.assertEqual(t["processo"], "vivo_apos_kill")
            self.assertIn("T1", [h.get("task") for h in
                                 json.loads((raiz / Q).read_text())["historico"]
                                 if h["evento"] == "reteve_vaga"])


class TestCompensacaoEEncerramento(unittest.TestCase):
    def _cadeia(self, raiz, reverter=True):
        q(raiz, "abrir", "forge-x")
        for tid, dep in (("T1", ""), ("T2", "T1"), ("T3", "T2"), ("T4", "")):
            args = ["adicionar", "forge-x", "--id", tid, "--titulo", tid, "--dono", "x",
                    "--posse", f"{tid.lower()}/**", "--pronto-quando", "ok"]
            if dep:
                args += ["--depende", dep]
            if reverter:
                args += ["--reverter", f"git revert {tid}"]
            q(raiz, *args)
        for tid in ("T1", "T4", "T2", "T3"):
            q(raiz, "iniciar", "forge-x", tid)
            q(raiz, "concluir", "forge-x", tid, "--evidencia", "ok", "--gate-ok",
              "--sem-diff", "teste")

    def test_compensar_desfaz_em_ordem_inversa_e_preserva_o_independente(self):
        with Repositorio() as raiz:
            self._cadeia(raiz)
            r = q(raiz, "compensar", "forge-x", "T1", "--motivo", "schema mudou", "--aplicar")
            self.assertIn("T4", r.stdout)
            v = vista(raiz)["tasks"]
            self.assertEqual([v[t]["estado"] for t in ("T1", "T2", "T3")], ["planejada"] * 3)
            self.assertEqual(v["T4"]["estado"], "concluida")
            self.assertEqual(v["T1"]["rodadas"], 1)
            self.assertEqual(v["T2"]["rodadas"], 0, "dependente não erra, é invalidada")
            plano = [h for h in json.loads((raiz / Q).read_text())["historico"]
                     if h["evento"] == "compensou"][0]["plano"]
            self.assertEqual(plano, ["T3", "T2", "T1"])

    def test_compensar_sem_reverter_recusa_o_plano_inteiro(self):
        with Repositorio() as raiz:
            self._cadeia(raiz, reverter=False)
            antes = (raiz / Q).read_bytes()
            r = q(raiz, "compensar", "forge-x", "T1", "--motivo", "x", "--aplicar", ok=False)
            self.assertEqual(r.returncode, 1)
            self.assertEqual((raiz / Q).read_bytes(), antes)

    def test_encerrar_recusa_lacuna_escondida(self):
        with Repositorio() as raiz:
            q(raiz, "abrir", "forge-x")
            tarefa(raiz, "T1", "a/**")
            tarefa(raiz, "T2", "b/**")
            q(raiz, "iniciar", "forge-x", "T1")
            q(raiz, "concluir", "forge-x", "T1", "--evidencia", "ok", "--gate-ok",
              "--sem-diff", "teste")
            r = q(raiz, "encerrar", "forge-x", ok=False)
            self.assertEqual(r.returncode, 1)
            self.assertFalse(vista(raiz)["encerrado"])
            q(raiz, "encerrar", "forge-x", "--lacuna", "T2: sem ambiente")
            self.assertTrue(vista(raiz)["encerrado"])

    def test_reabrir_respeita_o_orcamento_de_rodadas(self):
        with Repositorio() as raiz:
            q(raiz, "abrir", "forge-x", "--rodadas", "1")
            tarefa(raiz, "T1", "a/**")
            q(raiz, "iniciar", "forge-x", "T1")
            q(raiz, "bloquear", "forge-x", "T1", "--motivo", "x")
            q(raiz, "reabrir", "forge-x", "T1")
            q(raiz, "iniciar", "forge-x", "T1")
            q(raiz, "bloquear", "forge-x", "T1", "--motivo", "y")
            r = q(raiz, "reabrir", "forge-x", "T1", ok=False)
            self.assertEqual(r.returncode, 1)


class TestPublicacaoAtomica(unittest.TestCase):
    def test_falha_no_replace_preserva_o_quadro(self):
        with Repositorio() as raiz:
            q(raiz, "abrir", "forge-x")
            antes = (raiz / Q).read_bytes()
            sys.path.insert(0, str(RAIZ / "scripts"))
            import quadro  # noqa: E402
            cwd = os.getcwd()
            os.chdir(raiz)
            try:
                with mock.patch.object(quadro.os, "replace", side_effect=OSError("disco cheio")):
                    with self.assertRaises(OSError):
                        quadro.salvar(quadro.carregar("forge-x"))
            finally:
                os.chdir(cwd)
            self.assertEqual((raiz / Q).read_bytes(), antes)
            self.assertEqual(list((raiz / ".agents/quadro").glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
