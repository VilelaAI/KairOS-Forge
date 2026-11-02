"""Testes dos tokens relatados pela CLI (ADR-0048): o transcript, o worktree e o quadro.

Só stdlib. O formato do transcript é o do Claude Code, conferido num transcript real: uma
resposta do modelo vira várias linhas com o mesmo `message.id` e o mesmo uso.

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
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import execucao  # noqa: E402
import quadro  # noqa: E402
import telemetria  # noqa: E402


def resposta(mid: str, entrada: int, saida: int, cache_lido: int = 0, cache_escrito: int = 0,
             modelo: str = "claude-opus-5-5", texto: str = "ok") -> str:
    return json.dumps({"type": "assistant", "uuid": f"u-{mid}-{texto}", "message": {
        "id": mid, "model": modelo, "content": [{"type": "text", "text": texto}],
        "usage": {"input_tokens": entrada, "output_tokens": saida,
                  "cache_read_input_tokens": cache_lido,
                  "cache_creation_input_tokens": cache_escrito}}})


class Transcript(unittest.TestCase):
    def ler(self, *linhas: str) -> dict | None:
        with tempfile.TemporaryDirectory() as tmp:
            arq = Path(tmp) / "sessao.jsonl"
            arq.write_text("\n".join(linhas) + "\n", encoding="utf-8")
            return execucao.tokens_do_transcript(str(arq))

    def test_resposta_em_varias_linhas_conta_uma_vez(self) -> None:
        t = self.ler(resposta("m1", 10, 5, 1000, 200, texto="pensando"),
                     resposta("m1", 10, 5, 1000, 200, texto="resposta"),
                     resposta("m1", 10, 5, 1000, 200, texto="ferramenta"),
                     resposta("m2", 3, 7, 1200, 0))
        self.assertEqual(t["respostas"], 2)
        self.assertEqual((t["entrada"], t["saida"], t["cache_leitura"], t["cache_escrita"]),
                         (13, 12, 2200, 200))
        self.assertEqual(t["modelos"], ["claude-opus-5-5"])

    def test_vale_o_maior_valor_visto_na_mesma_resposta(self) -> None:
        t = self.ler(resposta("m1", 10, 1), resposta("m1", 10, 40))
        self.assertEqual(t["saida"], 40)

    def test_linha_de_usuario_e_modelo_sintetico_nao_entram(self) -> None:
        usuario = json.dumps({"type": "user", "message": {"content": "o campo usage é isto"}})
        t = self.ler(usuario, resposta("m1", 2, 3), resposta("m9", 0, 0, modelo="<synthetic>"),
                     "linha que não é json com \"usage\"", json.dumps(["usage", 1]),
                     json.dumps({"type": "assistant", "message": {"usage": "texto"}}))
        self.assertEqual(t["modelos"], ["claude-opus-5-5"])
        self.assertEqual(t["entrada"], 2)

    def test_sem_transcript_nao_ha_leitura(self) -> None:
        self.assertIsNone(execucao.tokens_do_transcript(""))
        self.assertIsNone(execucao.tokens_do_transcript("/nao/existe.jsonl"))
        self.assertIsNone(self.ler(json.dumps({"type": "user"})))

    def test_stop_grava_o_acumulado_so_quando_ha_leitura(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            arq = Path(tmp) / "s.jsonl"
            arq.write_text(resposta("m1", 1, 2) + "\n", encoding="utf-8")
            self.assertEqual(execucao.ev_fim({"transcript_path": str(arq)})["tokens"]["saida"], 2)
        self.assertEqual(execucao.ev_fim({}), {"tipo": "sessao_fim"})


class Worktree(unittest.TestCase):
    def test_worktree_ligado_grava_no_checkout_principal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            principal = Path(tmp, "repo").resolve()
            principal.mkdir()
            for args in (["init", "-q", "-b", "main"],
                         ["-c", "user.name=a", "-c", "user.email=a@b", "commit", "-q",
                          "--allow-empty", "-m", "base"],
                         ["worktree", "add", "-q", str(Path(tmp, "wt")), "-b", "wt"]):
                subprocess.run(["git", "-C", str(principal), *args], check=True,
                               capture_output=True)
            self.assertEqual(execucao.raiz_do_projeto(Path(tmp, "wt").resolve()), principal)
            self.assertEqual(execucao.raiz_do_projeto(principal), principal)

    def test_submodulo_e_pasta_comum_ficam_onde_estao(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sub = Path(tmp).resolve()
            (sub / "modulos").mkdir()
            (sub / ".git").write_text("gitdir: modulos\n", encoding="utf-8")
            self.assertEqual(execucao.raiz_do_projeto(sub), sub)       # sem commondir
            (sub / ".git").write_text("lixo\n", encoding="utf-8")
            self.assertEqual(execucao.raiz_do_projeto(sub), sub)


def leitura(sessao: str, t: str, novos_saida: int, cache: int = 0) -> dict:
    return {"t": t, "sessao": sessao, "tipo": "sessao_fim",
            "tokens": {"entrada": 0, "cache_escrita": 0, "cache_leitura": cache,
                       "saida": novos_saida, "respostas": 1}}


def vinculo(sessao: str, t: str, tarefa: str, slug: str = "forge-x") -> dict:
    return {"t": t, "sessao": sessao, "tipo": "comando",
            "cmd": f"python3 scripts/quadro.py vincular {slug} {tarefa}", "gate": None}


QUADRO = {
    "slug": "forge-x", "aberto_em": "2026-11-02T10:00:00+00:00", "encerrado_em": None,
    "tasks": {
        "T1": {"estado": "concluida", "compensacoes": []},
        "T2": {"estado": "concluida",
               "compensacoes": [{"em": "2026-11-02T10:30:00+00:00"}]},
        "T3": {"estado": "em_progresso", "compensacoes": []},
    },
}


class TokensDaMobilizacao(unittest.TestCase):
    def dividir(self, eventos: list[dict]) -> dict:
        r = telemetria.tokens_da_mobilizacao(eventos, QUADRO)
        return {k: v["saida"] for k, v in r["categorias"].items()} | {"_r": r}

    def test_lider_antes_da_abertura_nao_conta_e_depois_e_sem_tarefa(self) -> None:
        r = self.dividir([leitura("L", "2026-11-02T09:00:00+00:00", 500),
                          leitura("L", "2026-11-02T10:05:00+00:00", 800)])
        self.assertEqual(r["sem_tarefa"], 300)
        self.assertEqual(r["_r"]["sessoes"], 1)

    def test_gasto_vai_para_a_tarefa_vinculada_naquele_momento(self) -> None:
        r = self.dividir([vinculo("W", "2026-11-02T10:01:00+00:00", "T1"),
                          leitura("W", "2026-11-02T10:02:00+00:00", 100),
                          leitura("W", "2026-11-02T10:03:00+00:00", 150),
                          vinculo("W", "2026-11-02T10:04:00+00:00", "T3"),
                          leitura("W", "2026-11-02T10:05:00+00:00", 190)])
        self.assertEqual(r["concluida"], 150)
        self.assertEqual(r["aberta"], 40)
        self.assertEqual(r["_r"]["por_tarefa"]["T1"]["concluida"]["saida"], 150)

    def test_tarefa_compensada_depois_conta_como_desfeita(self) -> None:
        r = self.dividir([vinculo("W", "2026-11-02T10:01:00+00:00", "T2"),
                          leitura("W", "2026-11-02T10:10:00+00:00", 70),
                          leitura("W", "2026-11-02T10:40:00+00:00", 100)])
        self.assertEqual(r["desfeita"], 70)     # antes da compensação: trabalho desfeito
        self.assertEqual(r["concluida"], 30)    # refeito depois dela

    def test_vinculo_de_outro_quadro_nao_conta(self) -> None:
        r = self.dividir([vinculo("W", "2026-11-02T10:01:00+00:00", "T1", slug="forge-y"),
                          leitura("W", "2026-11-02T10:02:00+00:00", 100)])
        self.assertEqual(r["sem_tarefa"], 100)

    def test_transcript_novo_na_mesma_sessao_recomeca_a_conta(self) -> None:
        r = self.dividir([leitura("L", "2026-11-02T10:01:00+00:00", 900),
                          leitura("L", "2026-11-02T10:02:00+00:00", 50)])
        self.assertEqual(r["sem_tarefa"], 950)

    def test_sem_leitura_nao_e_medido(self) -> None:
        r = telemetria.tokens_da_mobilizacao([vinculo("W", "2026-11-02T10:01:00+00:00", "T1")],
                                             QUADRO)
        self.assertFalse(r["medido"])


LEITURAS = [leitura("A", "2026-11-02T10:00:00+00:00", 10, cache=1000),
            leitura("A", "2026-11-02T10:05:00+00:00", 30, cache=3000),
            leitura("B", "2026-11-02T10:05:00+00:00", 5)]


def saida_de(funcao, *args) -> tuple[object, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        r = funcao(*args)
    return r, out.getvalue()


class Resumo(unittest.TestCase):
    def test_vale_a_ultima_leitura_de_cada_sessao(self) -> None:
        m = telemetria.resumo_de_tokens(LEITURAS)
        self.assertEqual((m["sessoes_com_tokens"], m["tokens_novos"], m["tokens_cache_lido"]),
                         (2, 35, 3000))

    def test_linha_do_resumo_com_e_sem_medida(self) -> None:
        self.assertIn("não medidos", telemetria.linha_de_tokens_do_resumo({}))
        linha = telemetria.linha_de_tokens_do_resumo(telemetria.resumo_de_tokens(LEITURAS))
        self.assertIn("35", linha)
        self.assertIn("2 sessão(ões)", linha)

    def test_resumo_impresso_traz_os_tokens(self) -> None:
        m = {**telemetria.metricas(telemetria.por_sessao(LEITURAS)),
             **telemetria.resumo_de_tokens(LEITURAS)}
        _, texto = saida_de(telemetria.imprimir_resumo, m, 7)
        self.assertIn("Tokens novos:", texto)
        self.assertIn("últimos 7 dias", texto)

    def test_comando_tokens(self) -> None:
        codigo, texto = saida_de(telemetria.cmd_tokens, LEITURAS, False)
        self.assertEqual(codigo, 0)
        linhas = texto.strip().splitlines()
        self.assertEqual(len(linhas), 4)                     # cabeçalho, régua, A, B
        self.assertTrue(linhas[2].startswith("A ") and linhas[2].split()[2] == "30")
        codigo, texto = saida_de(telemetria.cmd_tokens, LEITURAS, True)
        self.assertEqual(json.loads(texto)["A"]["saida"], 30)
        _, texto = saida_de(telemetria.cmd_tokens, [], False)
        self.assertIn("não medidos", texto)

    def test_cli_despacha_tokens_e_sessoes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            antes, argv = os.getcwd(), sys.argv
            os.chdir(tmp)
            try:
                Path(".agents/execucoes").mkdir(parents=True)
                Path(".agents/execucoes/2026-11.jsonl").write_text(
                    "\n".join(json.dumps(e) for e in LEITURAS) + "\n", encoding="utf-8")
                for comando in ("tokens", "sessoes", "resumo"):
                    sys.argv = ["telemetria.py", comando]
                    codigo, texto = saida_de(telemetria.main)
                    self.assertEqual(codigo, 0, comando)
                    self.assertTrue(texto.strip(), comando)
            finally:
                sys.argv = argv
                os.chdir(antes)

    def test_formatar(self) -> None:
        self.assertEqual(telemetria.formatar(1_234_567), "1,2 mi")
        self.assertEqual(telemetria.formatar(45_300), "45 mil")
        self.assertEqual(telemetria.formatar(9_876), "9.876")


class Ledger(unittest.TestCase):
    def rodar(self, *args: str) -> str:
        out, antigo = io.StringIO(), sys.argv
        sys.argv = ["quadro.py", *args]
        try:
            with contextlib.redirect_stdout(out):
                quadro.main()
        finally:
            sys.argv = antigo
        return out.getvalue()

    def test_com_e_sem_medida(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            antes = os.getcwd()
            os.chdir(tmp)
            try:
                self.rodar("abrir", "forge-x")
                self.rodar("adicionar", "forge-x", "--id", "T1", "--titulo", "t",
                           "--dono", "lucas", "--posse", "src/**", "--pronto-quando", "ok")
                saida = self.rodar("ledger", "forge-x")
                self.assertIn("Tokens: não medidos", saida)
                self.assertNotIn("Tokens novos |", saida)
                Path(".agents/execucoes").mkdir(parents=True)
                eventos = [vinculo("W", "2099-01-01T00:00:00+00:00", "T1"),
                           leitura("W", "2099-01-01T00:01:00+00:00", 12_000, cache=90_000)]
                Path(".agents/execucoes/2099-01.jsonl").write_text(
                    "\n".join(json.dumps(e) for e in eventos) + "\n", encoding="utf-8")
                saida = self.rodar("ledger", "forge-x")
                self.assertIn("| lucas | padrao | 1 | 0 | 0 | 0 | 12 mil |", saida)
                self.assertIn("em aberto 12 mil", saida)
                self.assertIn("Cache lido à parte: 90 mil", saida)
            finally:
                os.chdir(antes)


if __name__ == "__main__":
    unittest.main()
