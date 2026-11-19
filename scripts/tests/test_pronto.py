"""Pronto quando (ADR-0060): a forma da seção, a conferência que a lê e as skills da sessão.

- `pronto.py` cobra a forma num lugar só: título uma vez, de 3 a 7 itens de uma linha,
  cada um com o comando ou o artefato entre crases, ou com `(gate humano)` no fim, e o
  script e o subcomando citados existem.
- o `release.py check` aplica a forma em toda skill da fábrica;
- o `guardrail.py conferir` põe os itens das skills usadas na sessão na frente do modelo
  quando a pessoa pergunta se falta algo, lendo o transcript sem deixar texto virar caminho;
- o `guardrail.py verificar` reprova a marca de depuração que sobrou e a fonte fora da forma;
- a lista de skills do `execucao.py` sai da pasta, e não fica para trás.
"""
from __future__ import annotations

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
import guardrail  # noqa: E402
import pronto  # noqa: E402
from tests.test_guardrail import hook  # noqa: E402

SCRIPTS = {"ciclo.py": 'if comando == "estado": ...\n"--json"', "prova.py": '"fontes"'}
BOA = """# Skill

Texto.

```markdown
## Pronto quando
- dentro do bloco não conta
```

## Pronto quando

- O relatório está em `docs/x.md` e `ciclo.py estado --json` diz `encerrado`.
- `prova.py fontes` sai 0.
- A pessoa aprovou o plano (gate humano).

## Referências

- [a](references/a.md)
"""


class AForma(unittest.TestCase):
    def test_a_secao_boa(self) -> None:
        self.assertEqual(pronto.problemas(BOA, SCRIPTS), [])
        self.assertEqual(len(pronto.itens(BOA)), 3)
        self.assertEqual(pronto.itens(BOA)[2], "A pessoa aprovou o plano (gate humano).")

    def test_sem_a_secao_ou_so_dentro_do_bloco(self) -> None:
        self.assertEqual(pronto.problemas("# x\n", SCRIPTS), ["sem a seção `## Pronto quando`"])
        self.assertIsNone(pronto.itens("```\n## Pronto quando\n- a\n```\n"))

    def test_duas_vezes(self) -> None:
        self.assertIn("`## Pronto quando` aparece 2 vezes",
                      pronto.problemas(BOA + "\n## Pronto quando\n\n- `a`\n", SCRIPTS))

    def test_quantidade_de_itens(self) -> None:
        dois = "## Pronto quando\n\n- `a`\n- `b`\n"
        self.assertEqual(pronto.problemas(dois, SCRIPTS), ["2 itens; são de 3 a 7"])
        oito = "## Pronto quando\n\n" + "".join(f"- `a{i}`\n" for i in range(8))
        self.assertEqual(pronto.problemas(oito, SCRIPTS), ["8 itens; são de 3 a 7"])
        sete = "## Pronto quando\n\n" + "".join(f"- `a{i}`\n" for i in range(7))
        self.assertEqual(pronto.problemas(sete, SCRIPTS), [])

    def test_linha_fora_da_lista(self) -> None:
        texto = "## Pronto quando\n\nIntro.\n\n- `a`\n- `b`\n- `c`\n"
        self.assertEqual(pronto.problemas(texto, SCRIPTS), ["linha fora da lista: Intro."])

    def test_item_sem_prova_e_item_longo(self) -> None:
        texto = ("## Pronto quando\n\n- `a`\n- a pessoa decide (gate humano)\n- tudo certo\n"
                 "- `x` " + "y" * 280 + "\n- (gate humano) no começo não vale\n")
        self.assertEqual(pronto.problemas(texto, SCRIPTS), [
            "item 3: sem o comando ou o artefato entre crases, e sem `(gate humano)` no fim",
            "item 4: 284 caracteres, limite 280",
            "item 5: sem o comando ou o artefato entre crases, e sem `(gate humano)` no fim"])

    def test_script_e_subcomando_citados(self) -> None:
        texto = ("## Pronto quando\n\n- `sumiu.py rodar`\n- `ciclo.py inventado`\n"
                 "- `ciclo.py <arquivo>` e `scripts/prova.py fontes SPEC-NNN`\n")
        self.assertEqual(pronto.problemas(texto, SCRIPTS), [
            "item 1: cita `sumiu.py`, que não existe em scripts/",
            "item 2: `ciclo.py inventado` — `inventado` não aparece no ciclo.py"])

    def test_o_titulo_de_mesmo_nivel_fecha_a_secao(self) -> None:
        texto = "## Pronto quando\n\n- `a`\n- `b`\n- `c`\n\n# Outra\n\n- solta\n"
        self.assertEqual(pronto.itens(texto), ["`a`", "`b`", "`c`"])


class NoReleaseCheck(unittest.TestCase):
    def test_a_skill_fora_da_forma_aparece_com_o_caminho(self) -> None:
        import release
        with tempfile.TemporaryDirectory(prefix="kairos-forge-release-") as tmp:
            raiz = Path(tmp)
            for rel, texto in (("skills/a/SKILL.md", "# a\n"), ("skills/b/SKILL.md", BOA),
                               ("scripts/ciclo.py", SCRIPTS["ciclo.py"]),
                               ("scripts/prova.py", SCRIPTS["prova.py"])):
                (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
                (raiz / rel).write_text(texto, encoding="utf-8")
            self.assertEqual(release.problemas_do_pronto(raiz),
                             ["skills/a/SKILL.md: sem a seção `## Pronto quando`"])


class ASkillsDaFabrica(unittest.TestCase):
    def test_toda_skill_tem_a_secao_na_forma(self) -> None:
        codigo = {p.name: p.read_text(encoding="utf-8") for p in RAIZ.glob("*.py")}
        skills = sorted((RAIZ.parent / "skills").glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skills), 21)
        for p in skills:
            with self.subTest(p.parent.name):
                self.assertEqual(pronto.problemas(p.read_text(encoding="utf-8"), codigo), [])


def transcript(linhas: list[dict]) -> str:
    arq = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    arq.write("\n".join(json.dumps(l) for l in linhas) + "\nnão é json\n[1]\n")
    arq.close()
    return arq.name


def chamada(skill: str) -> dict:
    return {"type": "assistant", "message": {"content": [
        {"type": "text", "text": "vou usar"},
        {"type": "tool_use", "name": "Skill", "input": {"skill": skill}}]}}


def digitada(texto: str) -> dict:
    return {"type": "user", "message": {"content": texto}}


class AConferencia(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-pronto-")
        self.addCleanup(self._tmp.cleanup)
        self.pasta = Path(self._tmp.name)
        for nome, extra in (("revisar", "- `prova.py origem REVISAO.md` sai 0.\n"),
                            ("validar", "- a pessoa decide (gate humano)\n"), ("sem-secao", None)):
            (self.pasta / nome).mkdir()
            corpo = f"# {nome}\n" + (f"\n## Pronto quando\n\n{extra}- `b`\n- `c`\n" if extra else "")
            (self.pasta / nome / "SKILL.md").write_text(corpo, encoding="utf-8")

    def test_as_skills_da_sessao_em_ordem_e_sem_repetir(self) -> None:
        caminho = transcript([
            chamada("kairos-forge:revisar"),
            digitada("<command-message>x</command-message>\n<command-name>/kairos-forge:validar</command-name>"),
            chamada("revisar"), chamada("outro-plugin:revisar"), chamada("kairos-forge:../../etc"),
            chamada("kairos-forge:inexistente"),
            digitada("<command-name>/outro:validar</command-name>"),
            {"type": "user", "message": {"content": [{"type": "text",
                                                      "text": "<command-name>sem-secao</command-name>"}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash",
                                                           "input": {"skill": "validar"}}]}},
            {"type": "assistant", "message": "texto"}, {"type": "system"}])
        self.addCleanup(os.unlink, caminho)
        self.assertEqual(guardrail.skills_da_sessao(caminho, self.pasta),
                         ["revisar", "validar", "sem-secao"])
        self.assertEqual(guardrail.skills_da_sessao("/nao/existe.jsonl", self.pasta), [])

    def test_os_itens_entram_na_conferencia(self) -> None:
        caminho = transcript([chamada("kairos-forge:revisar"), chamada("kairos-forge:sem-secao")])
        self.addCleanup(os.unlink, caminho)
        texto = guardrail.pronto_das_skills({"transcript_path": caminho}, self.pasta)
        self.assertIn("/revisar:\n- `prova.py origem REVISAO.md` sai 0.\n- `b`\n- `c`", texto)
        self.assertNotIn("sem-secao", texto)
        self.assertIn("(ADR-0060)", texto)
        self.assertEqual(guardrail.pronto_das_skills({}, self.pasta), "")

    def test_o_texto_tem_teto(self) -> None:
        longo = "".join(f"- `item {i} " + "x" * 200 + "`\n" for i in range(7))
        (self.pasta / "revisar" / "SKILL.md").write_text(f"## Pronto quando\n\n{longo}", encoding="utf-8")
        (self.pasta / "validar" / "SKILL.md").write_text(f"## Pronto quando\n\n{longo}", encoding="utf-8")
        caminho = transcript([chamada("kairos-forge:revisar"), chamada("kairos-forge:validar")])
        self.addCleanup(os.unlink, caminho)
        texto = guardrail.pronto_das_skills({"transcript_path": caminho}, self.pasta)
        self.assertTrue(texto.endswith(" […]"))
        self.assertLess(len(texto), guardrail.MAX_PRONTO + 400)

    def test_pelo_hook_com_as_skills_da_fabrica(self) -> None:
        caminho = transcript([chamada("kairos-forge:revisar")])
        self.addCleanup(os.unlink, caminho)
        codigo, out, _ = hook("conferir", {"prompt": "faltou algo?", "transcript_path": caminho,
                                           "hook_event_name": "UserPromptSubmit"})
        contexto = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(codigo, 0)
        self.assertIn("o que chegou no meio do trabalho", contexto)
        self.assertIn("/revisar:\n- ", contexto)
        codigo, out, _ = hook("conferir", {"prompt": "faltou algo?",
                                           "hook_event_name": "UserPromptSubmit"})
        self.assertNotIn("/revisar:", json.loads(out)["hookSpecificOutput"]["additionalContext"])

    def test_sem_o_pronto_py_ao_lado(self) -> None:
        caminho = transcript([chamada("kairos-forge:revisar")])
        self.addCleanup(os.unlink, caminho)
        salvo = sys.modules.pop("pronto")
        sys.modules["pronto"] = None   # import falha como na cópia avulsa
        try:
            self.assertEqual(guardrail.pronto_das_skills({"transcript_path": caminho}, self.pasta), "")
        finally:
            sys.modules["pronto"] = salvo


class OVerificar(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-verificar-")
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_COUNT": "1",
               "GIT_CONFIG_KEY_0": "commit.gpgsign", "GIT_CONFIG_VALUE_0": "false"}
        self.git = lambda *a: subprocess.run(["git", *a], cwd=self.raiz, env=env, check=True,
                                             capture_output=True)
        self.git("init", "-q", "-b", "main")
        (self.raiz / "a.py").write_text("x = 1\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")

    def test_marca_que_sobrou_e_fonte_quebrada(self) -> None:
        (self.raiz / "a.py").write_text("x = 1\nprint('[forge-" + "depura-77aa]')\n", encoding="utf-8")
        (self.raiz / "docs").mkdir()
        (self.raiz / "docs" / "nota.md").write_text("Ver docs/pesquisa/sumiu.md.\n", encoding="utf-8")
        (self.raiz / "docs" / "pesquisa").mkdir()
        (self.raiz / "docs" / "pesquisa" / "ruim.md").write_text("# x\n", encoding="utf-8")
        achados = guardrail.marcas_e_fontes(self.raiz)
        self.assertIn("a.py:2: marca de depuração que sobrou (forge-depura)", achados)
        self.assertIn("docs/nota.md:1: cita docs/pesquisa/sumiu.md, que não existe", achados)
        self.assertIn("docs/pesquisa/ruim.md: sem **Resposta:**", achados)
        r = subprocess.run([sys.executable, "-B", str(RAIZ / "guardrail.py"), "verificar", str(self.raiz)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("marca de depuração que sobrou", r.stdout)

    def test_limpo_e_sem_base(self) -> None:
        self.assertEqual(guardrail.marcas_e_fontes(self.raiz), [])
        vazio = Path(tempfile.mkdtemp(prefix="kairos-forge-sem-git-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(vazio, ignore_errors=True))
        self.assertEqual(guardrail.marcas_e_fontes(vazio), [])


class AListaDeSkillsDaTrajetoria(unittest.TestCase):
    def test_toda_skill_da_pasta_e_reconhecida(self) -> None:
        for p in sorted((RAIZ.parent / "skills").glob("*/SKILL.md")):
            with self.subTest(p.parent.name):
                self.assertEqual(execucao.SKILLS.findall(f"rode /kairos-forge:{p.parent.name} já"),
                                 [p.parent.name])
                self.assertEqual(execucao.SKILLS.findall(f"/{p.parent.name}"), [p.parent.name])

    def test_sem_a_pasta_so_com_o_prefixo(self) -> None:
        rx = execucao.regex_das_skills(Path("/nao/existe"))
        self.assertEqual(rx.findall("/kairos-forge:qualquer e /solta"), ["qualquer"])
        self.assertEqual(execucao.SKILLS.findall("/rodarzinho /mapear-conhecimento"),
                         ["mapear-conhecimento"])


if __name__ == "__main__":
    unittest.main()
