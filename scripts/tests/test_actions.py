"""Testes das actions dos workflows: fixadas por commit e fora do Node 20 (emenda ao ADR-0057).

O GitHub descontinuou o runtime Node 20 das actions, e o CI do repositório já avisava. As
actions dos workflows do repositório e dos templates que o usuário copia (`templates/ci/`)
passam a uma versão que roda em `node24`, sempre citadas pelo commit, com a versão num
comentário. A tabela abaixo é a primeira versão de cada uma em `node24`, conferida no
`action.yml` daquele commit.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
ARQUIVOS = sorted((RAIZ / ".github" / "workflows").glob("*.yml")) + sorted((RAIZ / "templates" / "ci").glob("*.yml"))
USO = re.compile(r"^\s*-?\s*uses:\s*(\S+)(.*)$", re.M)
FIXADA = re.compile(r"^([\w.-]+/[\w.-]+)@([0-9a-f]{40})$")
VERSAO = re.compile(r"^\s*#\s*v(\d+)\.(\d+)\.(\d+)\s*$")
PRIMEIRA_EM_NODE24 = {                 # a primeira versão de cada action em `using: node24`
    "actions/checkout": (5, 0, 0),
    "actions/setup-node": (5, 0, 0),
    "actions/setup-python": (6, 0, 0),
    "actions/create-github-app-token": (3, 0, 0),
    "step-security/harden-runner": (2, 22, 4),
    "actions/configure-pages": (6, 0, 0),
    "actions/deploy-pages": (5, 0, 0),
    "actions/upload-pages-artifact": (5, 0, 0),   # composite; a v5 usa o upload-artifact v7
}


def usos() -> list[tuple[str, str, str]]:
    """(arquivo, referência depois do `@`, resto da linha) de cada `uses:`."""
    saida = []
    for arq in ARQUIVOS:
        for m in USO.finditer(arq.read_text(encoding="utf-8")):
            saida.append((arq.relative_to(RAIZ).as_posix(), m.group(1), m.group(2)))
    return saida


class ActionsFixadasEmNode24(unittest.TestCase):
    def test_ha_actions_para_conferir(self) -> None:
        self.assertGreaterEqual(len(usos()), 28)   # o que há hoje: a regex não pode casar com nada

    def test_toda_action_fixada_por_commit_com_a_versao(self) -> None:
        for arquivo, ref, resto in usos():
            with self.subTest(arquivo=arquivo, ref=ref):
                self.assertRegex(ref, FIXADA)
                self.assertRegex(resto, VERSAO)

    def test_nenhuma_action_numa_versao_de_antes_do_node24(self) -> None:
        for arquivo, ref, resto in usos():
            acao = FIXADA.match(ref).group(1)
            versao = tuple(int(x) for x in VERSAO.match(resto).groups())
            with self.subTest(arquivo=arquivo, acao=acao):
                self.assertIn(acao, PRIMEIRA_EM_NODE24, "action nova: confira o runtime e entre na tabela")
                self.assertGreaterEqual(versao, PRIMEIRA_EM_NODE24[acao])

    def test_a_mesma_versao_aponta_para_o_mesmo_commit_em_todo_lugar(self) -> None:
        vistos: dict[tuple[str, str], set[str]] = {}
        for _, ref, resto in usos():
            acao, sha = FIXADA.match(ref).groups()
            vistos.setdefault((acao, resto.strip()), set()).add(sha)
        for (acao, versao), shas in vistos.items():
            with self.subTest(acao=acao, versao=versao):
                self.assertEqual(len(shas), 1, shas)


class NodeDoClaudeCodeNosTemplates(unittest.TestCase):
    """O Node que instala o Claude Code, num job que roda com o segredo do projeto."""

    def test_node_em_suporte_e_sem_o_cache_automatico_do_setup_node(self) -> None:
        for arq in sorted((RAIZ / "templates" / "ci").glob("*.yml")):
            texto = arq.read_text(encoding="utf-8")
            passo = texto[texto.index("uses: actions/setup-node@"):]
            passo = passo[:passo.index("\n\n")]
            with self.subTest(arq.name):
                versao = int(re.search(r'node-version: "(\d+)"', passo).group(1))
                self.assertGreaterEqual(versao, 22)                 # o 20 saiu de suporte em 2026-04
                self.assertIn("package-manager-cache: false", passo)


if __name__ == "__main__":
    unittest.main()
