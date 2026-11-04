"""Testes do `painel.py --caixa` — a caixa de entrada da fábrica (ADR-0044).

Só stdlib. Os ciclos e o quadro são criados pelos próprios `ciclo.py` e `quadro.py`, num
diretório temporário: a caixa lê o mesmo estado que eles escrevem, e é isso que se testa.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import ciclo  # noqa: E402
import painel  # noqa: E402
import quadro  # noqa: E402

SPEC = """# SPEC-00{n} — Exemplo

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| EX-01 | Exportar lista | P1 | WHEN clica THEN baixa CSV em ≤ 2 s | Pendente | — |
"""


def chamar(modulo, *args: str) -> int:
    antigo = sys.argv
    sys.argv = [modulo.__name__ + ".py", *args]
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                return int(modulo.main() or 0)
            except SystemExit as e:
                return 1 if e.code else 0
    finally:
        sys.argv = antigo


class Caixa(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-painel-")
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        Path("docs/specs").mkdir(parents=True)
        for n in (1, 2, 3):
            Path(f"docs/specs/SPEC-00{n}-x.md").write_text(SPEC.format(n=n), encoding="utf-8")

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def tipos(self, d: dict) -> dict:
        return {(i["tipo"], i["onde"]) for i in d["itens"]}

    def test_vazia_quando_nada_espera(self) -> None:
        chamar(ciclo, "abrir", "SPEC-001", "--spec-aprovada")
        d = painel.caixa(Path.cwd())
        self.assertEqual(d["itens"], [])
        self.assertEqual(d["github"]["estado"], "nao_consultado")
        self.assertIn("Nada esperando", painel.render_caixa(d))

    def test_junta_gate_spec_alterada_escalado_e_bloqueio(self) -> None:
        chamar(ciclo, "abrir", "SPEC-001")                       # enquadrando
        chamar(ciclo, "registrar", "entendimento_pronto", "SPEC-001")  # → gate 1/3
        chamar(ciclo, "abrir", "SPEC-002", "--spec-aprovada")
        spec2 = Path("docs/specs/SPEC-002-x.md")
        spec2.write_text(spec2.read_text(encoding="utf-8").replace("≤ 2 s", "≤ 5 s"), encoding="utf-8")
        chamar(ciclo, "abrir", "SPEC-003", "--spec-aprovada")
        chamar(ciclo, "escalar", "SPEC-003", "--motivo", "orçamento de validar esgotado")
        chamar(quadro, "abrir", "forge-x")
        chamar(quadro, "adicionar", "forge-x", "--id", "T1", "--titulo", "migration",
               "--dono", "carlos-dba", "--posse", "migrations/**", "--pronto-quando", "roda")
        chamar(quadro, "iniciar", "forge-x", "T1")
        chamar(quadro, "bloquear", "forge-x", "T1", "--motivo", "falta decidir UUID ou bigint")

        d = painel.caixa(Path.cwd())
        self.assertEqual(self.tipos(d), {("gate", "SPEC-001"), ("spec_alterada", "SPEC-002"),
                                         ("escalado", "SPEC-003"), ("bloqueada", "forge-x")})
        escalado = next(i for i in d["itens"] if i["tipo"] == "escalado")
        self.assertIn("orçamento", escalado["o_que"])
        saida = painel.render_caixa(d)
        self.assertIn("gate 1/3", saida)
        self.assertIn("ciclo.py reaprovar SPEC-002", saida)

    def test_github_so_quando_pedido_e_so_pr_da_fabrica(self) -> None:
        issues = [{"number": 9, "title": "Exportar CSV", "url": "u9"}]
        prs = [
            {"number": 1, "title": "feat: da fábrica", "url": "u1", "isDraft": False,
             "commits": [{"authors": [{"name": "P"}], "messageHeadline": "feat: x",
                          "messageBody": "Fabrica: kairos-forge"}]},
            {"number": 2, "title": "feat: à mão", "url": "u2", "isDraft": False,
             "commits": [{"authors": [{"name": "P"}], "messageHeadline": "feat: y",
                          "messageBody": ""}]},
        ]
        respostas = [subprocess.CompletedProcess([], 0, stdout=json.dumps(x), stderr="")
                     for x in (issues, prs)]
        with mock.patch.object(painel.shutil, "which", return_value="/usr/bin/gh"), \
                mock.patch.object(subprocess, "run", side_effect=respostas):
            d = painel.caixa(Path.cwd(), github=True)
        self.assertEqual(d["github"]["estado"], "consultado")
        self.assertEqual(self.tipos(d), {("falta_informacao", "issue #9"),
                                         ("pr_da_fabrica", "PR #1")})

    def test_painel_sem_o_telemetria_ao_lado_diz_que_a_consulta_falhou(self) -> None:
        spec = importlib.util.spec_from_file_location("_painel_avulso", Path(painel.__file__))
        avulso = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {"telemetria": None}):
            spec.loader.exec_module(avulso)
        with mock.patch.object(avulso.shutil, "which", return_value="/usr/bin/gh"):
            self.assertEqual(avulso.caixa_github(Path.cwd()), ({"estado": "falhou"}, []))



SPEC_012 = """# SPEC-012 — Exportar CSV

**Origem:** issue #40 · faixa 2

## Contexto e problema

O time exporta à mão.

## Objetivo

Quem gerencia baixa o relatório em CSV, sem pedir ao suporte.

## Requisitos rastreáveis

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| EXP-01 | Exportar | P1 | WHEN clica THEN baixa em ≤ 2 s | Concluído | verificado: npm test -- exportar (04/11) |
| EXP-02 | Separador | P1 | WHEN abre THEN usa ; | Concluído | — |
| EXP-03 | Nome com data | P2 | WHEN baixa THEN nome tem a data | Pendente | — |
"""

VALIDACAO = """# Validação — SPEC-012

```kairos-validacao
{"spec": "SPEC-012", "veredicto": "aprovado_com_ressalvas", "bloqueios": 0, "sem_evidencia": 0,
 "verificado": ["EXP-01 (npm test -- exportar)"]}
```
"""

REVISAO = """# Revisão — SPEC-012

```kairos-revisao
{"veredicto": "aprovado", "faixa": 3, "criticos": 0, "examinado": ["src/exportar.py (Vinícius)"],
 "incompletos": [], "achados": [], "anteriores": {}}
```
"""


class CorpoDoPR(unittest.TestCase):
    """`painel.py --pr`: o que a pessoa decide em cima, a evidência recolhida embaixo."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-pr-")
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        for pasta in ("docs/specs/validacoes", "docs/specs/revisoes", ".agents/ciclo"):
            Path(pasta).mkdir(parents=True)
        Path("docs/specs/SPEC-012-exportar.md").write_text(SPEC_012, encoding="utf-8")
        Path("docs/specs/SPEC-0120-outra.md").write_text(SPEC.format(n="120"), encoding="utf-8")

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def entrega_completa(self) -> None:
        Path("docs/specs/validacoes/VALIDACAO-SPEC-012-2026-11-04.md").write_text(VALIDACAO, encoding="utf-8")
        Path("docs/specs/revisoes/REVISAO-SPEC-012-2026-11-04.md").write_text(REVISAO, encoding="utf-8")
        Path(".agents/ciclo/SPEC-012.json").write_text(json.dumps({
            "spec": "SPEC-012", "estado": "pronto_para_pr", "spec_digest": ciclo.digest_da_spec("SPEC-012"),
            "historico": [{"para": "validando"}, {"para": "corrigindo_validacao"},
                          {"para": "validando"}, {"para": "revisando"}, {"para": "pronto_para_pr"}]}),
            encoding="utf-8")

    def test_decisao_em_cima_evidencia_recolhida_e_spec_apontada(self) -> None:
        self.entrega_completa()
        corpo = painel.render_pr(painel.dados_do_pr(Path.cwd(), "spec-012"))
        topo, evidencia = corpo.split("<details>")
        self.assertTrue(topo.startswith("**SPEC:** SPEC-012 — Exportar CSV (`docs/specs/SPEC-012-exportar.md`)"
                                        " · **Origem:** issue #40 · faixa 2 · **Faixa:** 3 (revisão)\nRefs #40"))
        self.assertIn("- Aceitar as ressalvas da validação (`VALIDACAO-SPEC-012-2026-11-04.md`).", topo)
        self.assertIn("- Fica de fora ou sem prova: EXP-02 (P1), EXP-03 (P2).", topo)
        self.assertIn("- A triagem estimou faixa 2; o diff é faixa 3.", topo)
        self.assertIn("- Faixa 3, difícil de reverter", topo)
        self.assertIn("## O que muda\n\nQuem gerencia baixa o relatório em CSV, sem pedir ao suporte.", topo)
        self.assertNotIn("npm test", topo)                    # a evidência não polui o topo
        self.assertNotIn(self._tmp.name, corpo)               # nem o caminho da máquina
        self.assertIn("<summary>Evidência: 1/2 P1 verificados · validação aprovado_com_ressalvas · "
                      "revisão aprovado · 1 rodada(s) de correção</summary>", evidencia)
        self.assertIn("| EXP-01 | P1 | verificado: npm test -- exportar (04/11) |", evidencia)
        self.assertIn("| EXP-02 | P1 | concluído, sem `verificado:` |", evidencia)
        self.assertIn("| EXP-03 | P2 | pendente |", evidencia)
        self.assertIn("- Revisão: `aprovado`, faixa 3 (`docs/specs/revisoes/REVISAO-SPEC-012-2026-11-04.md`)", evidencia)
        self.assertIn("- Ciclo: `pronto_para_pr`; voltas de correção: validação 1 · revisão 0", evidencia)

    def test_sem_relatorio_spec_alterada_e_nada_alem_do_merge(self) -> None:
        p = painel.dados_do_pr(Path.cwd(), "SPEC-012")
        self.assertIn("Sem relatório de validação — o arco não fechou esse gate.", p["decisoes"])
        self.assertIn("- Validação: sem relatório", painel.render_pr(p))
        self.assertIn("· **Faixa:** 2 (estimada na triagem)\n", painel.render_pr(p))
        self.entrega_completa()
        spec = Path("docs/specs/SPEC-012-exportar.md")
        spec.write_text(spec.read_text(encoding="utf-8").replace("≤ 2 s", "≤ 5 s"), encoding="utf-8")
        self.assertIn("A SPEC mudou depois da aprovação: `ciclo.py reaprovar SPEC-012` antes do merge.",
                      painel.dados_do_pr(Path.cwd(), "SPEC-012")["decisoes"])
        limpa = {"id": "SPEC-1", "requisitos": [{"id": "A-1", "prioridade": "P1", "verificado": True}],
                 "relatorios": {"validacao": {"veredicto": "aprovado"},
                                "revisao": {"veredicto": "aprovado", "faixa": 1}}}
        cab = painel.cabecalho_da_spec("# SPEC-1 — x\n\n## Objetivo\n\n## Não-objetivos\n\nnada\n")
        self.assertEqual((cab["objetivo"], cab["issue"], cab["faixa_estimada"]), ("", None, None))
        self.assertEqual(painel.decisoes_do_pr(limpa, cab, None), ["Nada além do merge."])
        mesma = {**cab, "faixa_estimada": 1}                      # estimou certo: nada a dizer
        self.assertEqual(painel.decisoes_do_pr(limpa, mesma, None), ["Nada além do merge."])
        so_triagem = {**limpa, "relatorios": {"validacao": {"veredicto": "aprovado"},
                                              "revisao": {"veredicto": "aprovado"}}}
        self.assertTrue(painel.decisoes_do_pr(so_triagem, {**cab, "faixa_estimada": 3}, None)[0]
                        .startswith("Faixa 3, difícil de reverter"))

    def test_cli(self) -> None:
        self.entrega_completa()
        spec = Path("docs/specs/SPEC-012-exportar.md")           # alterada: vira item da caixa
        spec.write_text(spec.read_text(encoding="utf-8").replace("≤ 2 s", "≤ 5 s"), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(painel._cmd_pr(["--pr", "SPEC-012", "--outro"], True), 0)  # a SPEC é a de depois
            self.assertEqual(painel._cmd_caixa(["--caixa"], True), 0)
        self.assertIn('"Quem gerencia baixa o relatório em CSV', out.getvalue())   # sem \\u escapado
        self.assertIn('"a SPEC mudou depois da aprovação"', out.getvalue())
        for args, esperado in ((["--pr", "SPEC-012"], 0), (["--pr", "SPEC-012", "--json"], 0),
                               (["--pr", "SPEC-999"], 1), (["--pr"], 1), (["--caixa"], 0)):
            with self.subTest(args):
                self.assertEqual(chamar(painel, *args), esperado)


if __name__ == "__main__":
    unittest.main()
