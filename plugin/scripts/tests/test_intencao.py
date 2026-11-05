"""Testes do mapa de intenção e da fronteira de confiança da SPEC (ADR-0053).

Só stdlib. Do PDD Kit (GitHub Next): cada requisito aponta para de onde veio, nas
palavras de quem pediu, e o que a entrega assume sem provar fica escrito, com quem aceitou
e o teste que cobre. Três lugares leem isso:

1. O `painel.py` lê as seções (`## Mapa de intenção`, `## Confiado, não provado`,
   `## Não prometido`) junto com os requisitos.
2. O corpo do PR (`painel.py --pr`) põe no "O que você decide" o requisito sem origem, o
   inferido, a peça confiada sem teste verificado e o que não é prometido.
3. O guardrail acusa, ao escrever a SPEC, requisito sem origem (classe `intencao`, em
   `aviso`). SPEC que já estava na base sem o mapa é de antes da regra e passa.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from tests.test_guardrail import Sandbox, hook

import painel  # noqa: E402  (o caminho vem do test_guardrail)

REQUISITOS = """# SPEC-020 — Login

**Origem:** issue #7

## Objetivo

Quem tem conta entra com a senha certa.

## Requisitos rastreáveis

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| LOG-01 | Token só com a senha certa | P1 | WHEN senha errada THEN 401 sem token | Concluído | verificado: npm test -- login (05/11) |
| LOG-02 | Senha certa sempre entra | P1 | WHEN senha certa THEN token em ≤ 1 s | Concluído | verificado: npm test -- login (05/11) |
| LOG-03 | Bloqueio após 5 tentativas | P2 | WHEN 5 erros em 1 min THEN 429 | Pendente | — |
"""

MAPA_COMPLETO = """
## Mapa de intenção

| Requisito | De onde veio | Nas palavras de quem pediu |
|---|---|---|
| LOG-01, LOG-02 | issue #7 | "você só ganha token com a senha certa" |
| LOG-03 | varredura: autorização | — |
"""

FRONTEIRA = """
## Confiado, não provado

| O que se assume | Quem aceitou | Teste que cobre |
|---|---|---|
| bcrypt diz sim só para a senha certa | Ana (gate 3/3) | verificado: npm test -- bcrypt (05/11) |
| o banco devolve a conta gravada | — | planejado: teste da consulta |

## Não prometido

- o tempo de resposta sob carga
- a ordem entre dois logins simultâneos
"""


class Leitura(unittest.TestCase):
    def test_mapa_completo_com_linha_para_dois_requisitos(self) -> None:
        i = painel.intencao_da_spec(REQUISITOS + MAPA_COMPLETO)
        self.assertEqual(i, {"tem_mapa": True, "ids": ["LOG-01", "LOG-02", "LOG-03"],
                             "sem_origem": [], "inferidos": []})

    def test_sem_origem_e_inferido(self) -> None:
        mapa = MAPA_COMPLETO.replace("| LOG-03 | varredura: autorização |", "| LOG-03 | — |")
        mapa += "| LOG-02 | inferido — a fábrica deduziu | — |\n"
        i = painel.intencao_da_spec(REQUISITOS + mapa)
        self.assertEqual(i["sem_origem"], ["LOG-03"])
        self.assertEqual(i["inferidos"], ["LOG-02"])

    def test_tabela_de_cinco_colunas_e_linha_do_mapa_sem_fonte(self) -> None:
        texto = ("""| ID | Requisito | Prioridade | Status | Verificação |
|---|---|---|---|---|
| A-01 | x | P1 | Pendente | — |

## Mapa de intenção

| Requisito | De onde veio |
|---|---|
| A-01 |
""")
        i = painel.intencao_da_spec(texto)
        self.assertEqual((i["ids"], i["sem_origem"]), (["A-01"], ["A-01"]))

    def test_spec_sem_mapa(self) -> None:
        i = painel.intencao_da_spec(REQUISITOS)
        self.assertFalse(i["tem_mapa"])
        self.assertEqual(i["sem_origem"], ["LOG-01", "LOG-02", "LOG-03"])

    def test_fronteira_e_nao_prometido(self) -> None:
        texto = REQUISITOS + FRONTEIRA + "\n## Riscos\n\n- outro item que não é da seção\n"
        self.assertEqual(painel.confiado_da_spec(texto), [
            {"assume": "bcrypt diz sim só para a senha certa", "aceito_por": "Ana (gate 3/3)",
             "teste": "verificado: npm test -- bcrypt (05/11)", "testado": True},
            {"assume": "o banco devolve a conta gravada", "aceito_por": "—",
             "teste": "planejado: teste da consulta", "testado": False}])
        self.assertEqual(painel.itens_da_secao(texto, "Não prometido"),
                         ["o tempo de resposta sob carga", "a ordem entre dois logins simultâneos"])
        self.assertEqual(painel.confiado_da_spec(REQUISITOS), [])
        self.assertEqual(painel.itens_da_secao(REQUISITOS, "Não prometido"), [])


class CorpoDoPR(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-intencao-")
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        Path("docs/specs").mkdir(parents=True)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def decisoes(self, texto: str) -> list[str]:
        Path("docs/specs/SPEC-020-login.md").write_text(texto, encoding="utf-8")
        return painel.dados_do_pr(Path.cwd(), "SPEC-020")["decisoes"]

    def test_tudo_mapeado_e_testado_nao_acrescenta_nada(self) -> None:
        fronteira = FRONTEIRA.replace("| — | planejado: teste da consulta |",
                                      "| Ana | verificado: npm test -- conta (05/11) |")
        fronteira = fronteira[:fronteira.index("## Não prometido")]
        decisoes = self.decisoes(REQUISITOS + MAPA_COMPLETO + fronteira)
        self.assertFalse(any("intenção" in d or "Confiado" in d or "prometido" in d for d in decisoes))

    def test_sem_mapa_sem_origem_inferido_confiado_e_nao_prometido(self) -> None:
        self.assertIn("A SPEC não tem mapa de intenção: confira se cada requisito foi pedido "
                      "(ADR-0053).", self.decisoes(REQUISITOS))
        mapa = MAPA_COMPLETO.replace("| LOG-03 | varredura: autorização |", "| LOG-03 | |")
        mapa += "| LOG-02 | inferido | — |\n"
        decisoes = self.decisoes(REQUISITOS + mapa + FRONTEIRA)
        self.assertIn("Sem origem no mapa de intenção: LOG-03 — entraram sem ser pedidos?", decisoes)
        self.assertIn("Inferidos pela fábrica, não pedidos: LOG-02.", decisoes)
        self.assertIn("Confiado sem teste verificado: o banco devolve a conta gravada "
                      "(ninguém aceitou).", decisoes)
        self.assertIn("Não prometido, e o merge aceita assim: o tempo de resposta sob carga; "
                      "a ordem entre dois logins simultâneos.", decisoes)
        self.assertFalse(any("bcrypt" in d for d in decisoes))     # o testado não é decisão

    def test_aceito_por_aparece_e_a_evidencia_lista_a_fronteira(self) -> None:
        fronteira = FRONTEIRA.replace("| — | planejado", "| Bruno | planejado")
        Path("docs/specs/SPEC-020-login.md").write_text(REQUISITOS + MAPA_COMPLETO + fronteira,
                                                        encoding="utf-8")
        corpo = painel.render_pr(painel.dados_do_pr(Path.cwd(), "SPEC-020"))
        topo, evidencia = corpo.split("<details>")
        self.assertIn("Confiado sem teste verificado: o banco devolve a conta gravada "
                      "(aceito por Bruno).", topo)
        self.assertIn("| Confiado, não provado | Aceito por | Teste |", evidencia)
        self.assertIn("| bcrypt diz sim só para a senha certa | Ana (gate 3/3) | "
                      "verificado: npm test -- bcrypt (05/11) |", evidencia)

    def test_spec_montada_a_mao_sem_a_leitura_nao_ganha_sinal(self) -> None:
        spec = {"relatorios": {}, "requisitos": [], "id": "SPEC-1"}
        self.assertEqual(painel._intencao(spec, {}, None), [])
        self.assertEqual(painel._confiado(spec, {}, None), [])
        self.assertEqual(painel._nao_prometido(spec, {}, None), [])


class NoGuardrail(Sandbox):
    def setUp(self) -> None:
        super().setUp()
        tmp = self.raiz / ".tmp"
        tmp.mkdir()
        self._env = mock.patch.dict(os.environ, {"TMPDIR": str(tmp)})
        self._env.start()
        (self.raiz / "docs" / "specs").mkdir(parents=True)

    def tearDown(self) -> None:
        self._env.stop()
        super().tearDown()

    def escrever(self, texto: str, nome: str = "SPEC-020-login.md", sessao: str = "s1") -> tuple[int, str]:
        alvo = self.raiz / "docs" / "specs" / nome
        alvo.write_text(texto, encoding="utf-8")
        codigo, _, err = hook("spec", {"session_id": sessao, "cwd": str(self.raiz),
                                       "tool_input": {"file_path": str(alvo)}})
        return codigo, err

    def commitar(self) -> None:
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                        "-m", "spec"], check=True)

    def recusas(self) -> list[dict]:
        pasta = self.raiz / ".agents" / "execucoes"
        return [e for p in sorted(pasta.glob("*.jsonl")) for e in map(json.loads, p.read_text().splitlines())
                if e.get("classe") == "intencao"] if pasta.is_dir() else []

    def test_spec_nova_sem_mapa_avisa_uma_vez_e_deixa_rastro_sempre(self) -> None:
        codigo, err = self.escrever(REQUISITOS)
        self.assertEqual(codigo, 1)
        self.assertIn("requisito sem origem em `docs/specs/SPEC-020-login.md` — LOG-01, LOG-02, LOG-03", err)
        self.assertEqual(self.escrever(REQUISITOS)[0], 0)          # mesma sessão: calado
        self.assertEqual(self.escrever(REQUISITOS, sessao="s2")[0], 1)
        self.assertEqual(len(self.recusas()), 3)

    def test_mapa_completo_passa_e_parcial_aponta_o_que_falta(self) -> None:
        self.assertEqual(self.escrever(REQUISITOS + MAPA_COMPLETO)[0], 0)
        parcial = MAPA_COMPLETO.replace("| LOG-03 | varredura: autorização | — |\n", "")
        codigo, err = self.escrever(REQUISITOS + parcial, nome="SPEC-021-x.md")
        self.assertEqual(codigo, 1)
        self.assertIn("— LOG-03", err)

    def test_spec_antiga_sem_mapa_passa_e_com_mapa_vale(self) -> None:
        alvo = self.raiz / "docs" / "specs" / "SPEC-020-login.md"
        alvo.write_text(REQUISITOS, encoding="utf-8")
        self.commitar()
        self.assertEqual(self.escrever(REQUISITOS)[0], 0)
        parcial = MAPA_COMPLETO.replace("| LOG-03 | varredura: autorização | — |\n", "")
        self.assertEqual(self.escrever(REQUISITOS + parcial)[0], 1)

    def test_em_bloqueio_bloqueia_toda_vez(self) -> None:
        (self.raiz / ".agents").mkdir(exist_ok=True)
        (self.raiz / ".agents" / "guardrails.json").write_text('{"modos": {"intencao": "bloqueio"}}')
        self.assertEqual(self.escrever(REQUISITOS)[0], 2)
        self.assertEqual(self.escrever(REQUISITOS)[0], 2)

    def test_concluido_sem_verificado_continua_vindo_primeiro(self) -> None:
        sem_prova = REQUISITOS.replace("| verificado: npm test -- login (05/11) |\n| LOG-02", "| — |\n| LOG-02")
        codigo, err = self.escrever(sem_prova)
        self.assertEqual(codigo, 2)
        self.assertIn("'Concluído' sem célula `verificado:`", err)

    def test_lista_longa_corta_em_oito_e_diz_quantos_faltam(self) -> None:
        def spec(n: int) -> str:
            linhas = "".join(f"| R-{k:02d} | x | P2 | x | Pendente | — |\n" for k in range(1, n + 1))
            return "| ID | Req | P | Critério | Status | Verificação |\n|---|---|---|---|---|---|\n" + linhas
        codigo, err = self.escrever(spec(9), nome="SPEC-030-a.md")
        self.assertIn("R-01, R-02, R-03, R-04, R-05, R-06, R-07, R-08 e mais 1", err)
        codigo, err = self.escrever(spec(8), nome="SPEC-031-b.md")
        self.assertIn("R-07, R-08\n", err)                  # os oito, e a linha acaba ali
        self.assertNotIn("e mais", err)

    def test_vale_o_cwd_do_payload_nao_o_do_processo(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as outro:
            os.chdir(outro)
            try:
                self.assertEqual(self.escrever(REQUISITOS)[0], 1)
            finally:
                os.chdir(self.raiz)
        self.assertEqual(self.recusas()[0]["alvo"], "docs/specs/SPEC-020-login.md")

    def test_documento_sem_requisitos_nao_e_spec(self) -> None:
        self.assertEqual(self.escrever("# Notas\n\nnada aqui\n", nome="notas.md")[0], 0)


if __name__ == "__main__":
    unittest.main()
