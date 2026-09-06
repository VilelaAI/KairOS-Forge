"""Invariantes do pacote — o que o `release.py check` não cobre (ADR-0039)."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from tests.apoio import RAIZ

FERRAMENTAS_CONHECIDAS = {"Read", "Write", "Edit", "MultiEdit", "NotebookEdit", "NotebookRead",
                          "Grep", "Glob", "Bash", "WebSearch", "WebFetch", "Agent", "Task",
                          "Skill", "TodoWrite"}


def frontmatter(p: Path) -> dict:
    t = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    campos = {}
    for linha in (m.group(1) if m else "").splitlines():
        if ":" in linha:
            k, _, v = linha.partition(":")
            campos[k.strip()] = v.strip()
    return campos


class TestCaminhosCitados(unittest.TestCase):
    def test_todo_caminho_do_plugin_citado_existe(self):
        """`${CLAUDE_PLUGIN_ROOT}/x` em skill, template ou hook aponta para arquivo real, sem `..`."""
        fontes = list((RAIZ / "skills").rglob("*.md")) + list((RAIZ / "templates").rglob("*.md")) \
            + [RAIZ / "hooks" / "hooks.json"] + list((RAIZ / "agents").glob("*.md"))
        vistos = set()
        for f in fontes:
            for rel in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", f.read_text(encoding="utf-8")):
                rel = rel.rstrip(".")
                if rel in vistos:
                    continue
                vistos.add(rel)
                with self.subTest(fonte=f.relative_to(RAIZ), caminho=rel):
                    self.assertNotIn("..", rel)
                    alvo = RAIZ / rel
                    if "<" in rel or "*" in rel:
                        continue
                    self.assertTrue(alvo.exists() or alvo.parent.is_dir(), rel)
        self.assertGreater(len(vistos), 5)

    def test_toda_reference_citada_por_uma_skill_existe(self):
        for skill in (RAIZ / "skills").glob("*/SKILL.md"):
            texto = skill.read_text(encoding="utf-8")
            for rel in set(re.findall(r"references/([A-Za-z0-9_.-]+\.md)", texto)):
                with self.subTest(skill=skill.parent.name, ref=rel):
                    candidatos = list((RAIZ / "skills").glob(f"*/references/{rel}"))
                    self.assertTrue(candidatos, rel)

    def test_toda_skill_com_references_as_cita_na_raiz(self):
        """Reference que ninguém aponta é contexto que ninguém carrega."""
        for pasta in (RAIZ / "skills").glob("*/references"):
            raiz = (pasta.parent / "SKILL.md").read_text(encoding="utf-8")
            for ref in pasta.glob("*.md"):
                with self.subTest(skill=pasta.parent.name, ref=ref.name):
                    self.assertIn(ref.name, raiz)


class TestAgentes(unittest.TestCase):
    def test_allow_list_so_com_ferramentas_conhecidas(self):
        for agente in (RAIZ / "agents").glob("*.md"):
            fm = frontmatter(agente)
            tools = {t.strip() for t in fm.get("tools", "").split(",") if t.strip()}
            with self.subTest(agente=agente.stem):
                self.assertTrue(tools, "sem allow-list")
                self.assertTrue(tools <= FERRAMENTAS_CONHECIDAS, tools - FERRAMENTAS_CONHECIDAS)
                self.assertEqual(fm.get("name"), agente.stem)

    def test_consultivos_nao_podem_implementar(self):
        """fronteira-03: quem recomenda não executa a própria recomendação — por allow-list."""
        for aid in ("rafael-staff", "isabela-ux", "diego-sistemas", "helena-security",
                    "camila-pm", "patricia-qa"):
            tools = {t.strip() for t in frontmatter(RAIZ / "agents" / f"{aid}.md")["tools"].split(",")}
            with self.subTest(agente=aid):
                self.assertFalse(tools & {"Write", "Edit", "MultiEdit", "NotebookEdit"}, tools)

    def test_apoio_nao_tem_bash(self):
        """Squads de apoio produzem texto; sem shell não há como 'só dessa vez' rodar algo."""
        for agente in (RAIZ / "agents").glob("apoio-*.md"):
            tools = {t.strip() for t in frontmatter(agente)["tools"].split(",")}
            with self.subTest(agente=agente.stem):
                self.assertNotIn("Bash", tools)


class TestSkills(unittest.TestCase):
    def test_deploy_so_por_invocacao_humana(self):
        """ADR-0039: `lancar` constrói o vetor de deploy; o modelo não a aciona sozinho."""
        self.assertEqual(frontmatter(RAIZ / "skills/lancar/SKILL.md").get("disable-model-invocation"), "true")

    def test_nomes_de_skill_sao_verbos_no_infinitivo(self):
        for skill in (RAIZ / "skills").glob("*/SKILL.md"):
            nome = skill.parent.name
            with self.subTest(skill=nome):
                self.assertEqual(frontmatter(skill).get("name"), nome)
                self.assertTrue(nome.split("-")[0].endswith(("ar", "er", "ir")), nome)


class TestGoldSets(unittest.TestCase):
    def test_todo_caso_deterministico_do_gold_set_tem_teste(self):
        """O gold set de comportamento e a suíte não podem divergir em silêncio (ADR-0031/0039)."""
        gold = RAIZ / "evals/comportamento-fabrica/gold.jsonl"
        ids = [json.loads(l)["id"] for l in gold.read_text(encoding="utf-8").splitlines()
               if l.strip() and json.loads(l)["verificacao"] == "deterministica"]
        suite = "".join(p.read_text(encoding="utf-8") for p in Path(__file__).parent.glob("test_*.py"))
        for cid in ids:
            with self.subTest(caso=cid):
                self.assertIn(cid, suite, f"caso determinístico '{cid}' sem teste que o cite")

    def test_gold_de_roteamento_so_cita_agentes_existentes(self):
        agentes = {p.stem for p in (RAIZ / "agents").glob("*.md")}
        for linha in (RAIZ / "evals/roteamento-laura/gold.jsonl").read_text(encoding="utf-8").splitlines():
            if linha.strip():
                for aid in json.loads(linha)["esperado"]:
                    self.assertIn(aid, agentes)


class TestGuardrailEDocs(unittest.TestCase):
    def test_sagrados_do_guardrail_aparecem_no_anti_drift(self):
        """A regra que o código impõe precisa estar escrita onde o teammate lê."""
        anti = (RAIZ / "templates/anti-drift.md").read_text(encoding="utf-8")
        for caminho in (".agents/execucoes/", ".agents/guardrails.json"):
            self.assertIn(caminho, anti)

    def test_mensagens_de_erro_documentadas_existem_no_script(self):
        """Doc que cita saída que o script não emite envelhece sem ninguém notar."""
        ciclo = (RAIZ / "scripts/ciclo.py").read_text(encoding="utf-8")
        entregar = (RAIZ / "skills/entregar/SKILL.md").read_text(encoding="utf-8")
        for estado in re.findall(r"`(aguardando_[a-z_]+|corrigindo_[a-z_]+|pronto_para_pr|escalado)`", entregar):
            with self.subTest(estado=estado):
                self.assertIn(f'"{estado}"', ciclo)


if __name__ == "__main__":
    unittest.main()
