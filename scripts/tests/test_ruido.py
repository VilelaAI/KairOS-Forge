"""Testes do ruído da revisão no PR (`telemetria.py ruido --github`, emenda ao ADR-0039).

Só stdlib, com um `gh` falso no PATH. Três coisas:

1. O comentário que o gatilho de CI (`kairos-forge-revisar.yml`) escreve, gerado pelo passo
   real do template, tem a marca que o `ruido` procura e os achados que o parser lê. O
   rodapé, que ensina a marcar `descartado:`, não conta como achado.
2. Com `--github`, entra só a revisão mais recente da fábrica em cada PR, dentro da janela.
   Comentário de pessoa com a mesma forma não entra, e o descarte numa revisão antiga não
   conta pela nova.
3. Sem `--github`, nada sai da máquina; com `gh` indisponível, o número diz "não
   consultado", nunca 0.

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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import telemetria  # noqa: E402
from tests.test_ci import blocos_run, ler  # noqa: E402

RELATORIO = """# Revisão pré-PR — feat/x

**Veredicto agregado:** ❌ bloqueado

## 🔴 Crítico (qualquer revisor) → bloqueia merge
- [Helena] R1 · api/users.ts:42 — SQL injection. Use prepared statement.

## 🟠 Alto → corrigir antes do merge
- [Vinícius] queries/relatorios.sql — N+1 no loop.

## 🔵 Baixo → comentar e seguir
- [Patrícia] components/Form.tsx — Cobertura parcial de erro.
"""

GH_FALSO = """#!/usr/bin/env python3
import os, sys
with open(os.environ["GH_CHAMADAS"], "a", encoding="utf-8") as f:
    f.write(" ".join(sys.argv[1:]) + "\\n")
if os.environ.get("GH_SAIDA", "0") != "0":
    sys.exit(int(os.environ["GH_SAIDA"]))
print(open(os.environ["GH_PRS"], encoding="utf-8").read())
"""


def ha(dias: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")


def comentario(corpo: str, dias: int) -> dict:
    return {"author": {"login": "github-actions"}, "body": corpo, "createdAt": ha(dias)}


def da_fabrica(relatorio: str) -> str:
    return f"## 🔥 {telemetria.MARCA_REVISAO_NO_PR}\n\n{relatorio}\n---\n_Parecer automático._"


def descartar(texto: str, revisor: str, motivo: str = "falso positivo") -> str:
    linhas = [f"{l} · descartado: {motivo}" if l.startswith(f"- [{revisor}]") else l
              for l in texto.splitlines()]
    return "\n".join(linhas)


class ComentarioDoGatilhoDeCI(unittest.TestCase):
    def corpo_do_comentario(self) -> str:
        (script,) = [s for _, s in blocos_run(ler("revisar")) if "gh pr comment" in s]
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "revisao.md").write_text(RELATORIO, encoding="utf-8")
            gh = Path(tmp) / "bin" / "gh"
            gh.parent.mkdir()
            gh.write_text('#!/bin/sh\nwhile [ "$1" != "--body-file" ]; do shift; done\n'
                          'cp "$2" corpo.md\n', encoding="utf-8")
            gh.chmod(0o755)
            env = {**os.environ, "PATH": f"{gh.parent}{os.pathsep}{os.environ.get('PATH', '')}",
                   "GH_TOKEN": "x", "PR": "7"}
            subprocess.run(["bash", "-e", "-c", script], cwd=tmp, env=env, check=True,
                           capture_output=True, text=True)
            return (Path(tmp) / "corpo.md").read_text(encoding="utf-8")

    def test_o_comentario_tem_a_marca_e_os_achados_que_o_ruido_le(self) -> None:
        corpo = self.corpo_do_comentario()
        self.assertIn(telemetria.MARCA_REVISAO_NO_PR, corpo)
        self.assertIn("descartado: <motivo>", corpo)               # o rodapé ensina a marcar
        achados = telemetria.achados_de(corpo)
        self.assertEqual([(a["revisor"], a["severidade"]) for a in achados],
                         [("Helena", "critico"), ("Vinícius", "alto"), ("Patrícia", "baixo")])
        self.assertFalse(any(a["descartado"] for a in achados))     # e não conta como descarte
        editado = telemetria.achados_de(descartar(corpo, "Vinícius"))
        self.assertEqual([a["revisor"] for a in editado if a["descartado"]], ["Vinícius"])


class RuidoComGithub(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-ruido-")
        base = Path(self._tmp.name)
        self.raiz, self.bin = base / "repo", base / "bin"
        self.chamadas, self.prs = base / "chamadas.txt", base / "prs.json"
        pasta = self.raiz / "docs" / "specs" / "revisoes"
        pasta.mkdir(parents=True)
        hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        (pasta / f"REVISAO-y-{hoje}.md").write_text(
            "## 🟡 Médio\n- [Patrícia] a.py — sem teste · descartado: coberto em b.py\n",
            encoding="utf-8")
        self.bin.mkdir()
        (self.bin / "gh").write_text(GH_FALSO, encoding="utf-8")
        (self.bin / "gh").chmod(0o755)
        humano = "## 🔴 Crítico\n- [Alguém] isto não é da fábrica · descartado: x"
        self.prs.write_text(json.dumps([
            {"number": 10, "comments": [
                comentario(da_fabrica(descartar(RELATORIO, "Helena")), 5),   # revisão antiga
                comentario(humano, 3),
                comentario(da_fabrica(descartar(RELATORIO, "Vinícius")), 2),  # a que conta
            ]},
            {"number": 11, "comments": [comentario(da_fabrica(RELATORIO), 200)]},
            {"number": 12, "comments": []},
        ]), encoding="utf-8")
        self.env = {"PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}",
                    "GH_CHAMADAS": str(self.chamadas), "GH_PRS": str(self.prs)}

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def ruido(self, dias: int | None, github: bool, saida: str = "0") -> dict:
        with mock.patch.dict(os.environ, {**self.env, "GH_SAIDA": saida}):
            return telemetria.ruido(self.raiz, dias, github=github)

    def test_so_a_revisao_mais_recente_de_cada_pr_na_janela(self) -> None:
        r = self.ruido(90, github=True)
        self.assertEqual((r["relatorios"], r["prs"], r["github"]), (1, 1, "consultado"))
        self.assertEqual((r["achados"], r["descartados"], r["ruido_pct"]), (4, 2, 50))
        self.assertEqual(r["por_revisor"]["Vinícius"], {"achados": 1, "descartados": 1,
                                                        "ruido_pct": 100})
        self.assertEqual(r["por_revisor"]["Helena"]["descartados"], 0)   # o descarte antigo não conta
        self.assertNotIn("Alguém", r["por_revisor"])                     # comentário de pessoa
        self.assertIn("pr list --state all", self.chamadas.read_text(encoding="utf-8"))
        self.assertEqual(self.ruido(None, github=True)["prs"], 2)          # sem janela, o PR 11 entra

    def test_sem_github_nada_sai_da_maquina(self) -> None:
        r = self.ruido(90, github=False)
        self.assertEqual((r["prs"], r["github"], r["achados"]), (None, "nao_pedido", 1))
        self.assertFalse(self.chamadas.exists())

    def test_gh_indisponivel_e_nao_consultado_nunca_zero(self) -> None:
        r = self.ruido(90, github=True, saida="1")
        self.assertEqual((r["prs"], r["github"], r["achados"]), (None, "indisponivel", 1))

    def rodar(self, *args: str, saida: str = "0") -> str:
        """`telemetria.py ruido` pelo main(), no processo, para a cobertura enxergar."""
        texto, antes = io.StringIO(), os.getcwd()
        try:
            os.chdir(self.raiz)
            with mock.patch.dict(os.environ, {**self.env, "GH_SAIDA": saida}), \
                    mock.patch.object(sys, "argv", ["telemetria.py", "ruido", *args]), \
                    contextlib.redirect_stdout(texto):
                self.assertEqual(telemetria.main(), 0)
        finally:
            os.chdir(antes)
        return texto.getvalue()

    def test_pela_cli(self) -> None:
        saida = self.rodar("--github", "--dias", "90")
        self.assertIn("a revisão mais recente da fábrica em 1 PR(s) entra na conta", saida)
        self.assertIn("Relatórios: 1   PRs: 1   Achados: 4   Descartados: 2", saida)
        self.assertIn("Ruído geral: 50%", saida)
        self.assertIn("rode com --github", self.rodar("--dias", "90"))
        self.assertIn("Relatórios: 1   PRs: —", self.rodar("--dias", "90"))
        self.assertIn("`gh` indisponível ou sem acesso", self.rodar("--github", saida="1"))
        self.assertEqual(json.loads(self.rodar("--github", "--json"))["prs"], 2)

    def test_sem_nada_e_sem_marca(self) -> None:
        relatorio = next((self.raiz / "docs" / "specs" / "revisoes").glob("*.md"))
        relatorio.write_text("## 🟡 Médio\n- [Patrícia] a.py — sem teste\n", encoding="utf-8")
        self.assertIn("Ruído: não medido", self.rodar("--dias", "90"))
        relatorio.unlink()
        self.assertIn("nenhum relatório em docs/specs/revisoes/", self.rodar("--dias", "90"))


class FronteiraDaJanela(unittest.TestCase):
    """O que cai exatamente no corte da janela entra, no disco e no PR."""

    def test_relatorio_do_dia_do_corte_entra(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp) / "docs" / "specs" / "revisoes"
            pasta.mkdir(parents=True)
            corte = (datetime.now(timezone.utc) - timedelta(days=30)).date()
            (pasta / f"REVISAO-a-{corte}.md").write_text("a", encoding="utf-8")
            (pasta / f"REVISAO-b-{corte - timedelta(days=1)}.md").write_text("b", encoding="utf-8")
            self.assertEqual(telemetria.relatorios_em_disco(Path(tmp), 30), ["a"])

    def test_revisao_criada_no_instante_do_corte_entra(self) -> None:
        corte = datetime(2026, 11, 1, tzinfo=timezone.utc)
        def pr(quando: str) -> dict:
            return {"comments": [{"body": da_fabrica("x"), "createdAt": quando}]}
        self.assertIsNotNone(telemetria._revisao_mais_recente(pr("2026-11-01T00:00:00Z"), corte))
        self.assertIsNone(telemetria._revisao_mais_recente(pr("2026-10-31T23:59:59Z"), corte))


class TabelaPorRevisor(unittest.TestCase):
    def test_alerta_a_partir_de_30_por_cento_com_tres_achados(self) -> None:
        texto = io.StringIO()
        with contextlib.redirect_stdout(texto):
            telemetria.imprimir_por_revisor({
                "Helena": {"achados": 3, "descartados": 1, "ruido_pct": 30},
                "Ana": {"achados": 2, "descartados": 2, "ruido_pct": 100},
                "Bia": {"achados": 4, "descartados": 1, "ruido_pct": 25}})
        linhas = {l.split()[0]: l for l in texto.getvalue().splitlines()[2:]}
        self.assertTrue(linhas["Helena"].endswith("30%  ⚠️"))
        self.assertTrue(linhas["Ana"].endswith("100%"))       # dois achados: pouco para alertar
        self.assertTrue(linhas["Bia"].endswith("25%"))


class DataNoNome(unittest.TestCase):
    def test_data_impossivel_ou_ausente_conta_como_sem_data(self) -> None:
        self.assertEqual(str(telemetria._data_no_nome("REVISAO-x-2026-11-04.md")), "2026-11-04")
        self.assertIsNone(telemetria._data_no_nome("REVISAO-x-2026-13-45.md"))
        self.assertIsNone(telemetria._data_no_nome("REVISAO-x.md"))


if __name__ == "__main__":
    unittest.main()
