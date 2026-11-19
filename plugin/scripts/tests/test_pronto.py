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

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
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

    def test_o_limite_de_tamanho_e_exato(self) -> None:
        def item(n: int) -> str:
            return "- `a` " + "x" * (n - len("`a` "))
        corpo = "# S\n\n## Pronto quando\n\n" + "\n".join([item(pronto.MAX_CHARS_ITEM), "- `b`", "- `c`"])
        self.assertEqual(pronto.problemas(corpo, SCRIPTS), [])
        corpo = corpo.replace(item(pronto.MAX_CHARS_ITEM), item(pronto.MAX_CHARS_ITEM + 1))
        self.assertEqual(pronto.problemas(corpo, SCRIPTS),
                         [f"item 1: {pronto.MAX_CHARS_ITEM + 1} caracteres, limite {pronto.MAX_CHARS_ITEM}"])

    def test_script_e_subcomando_citados(self) -> None:
        texto = ("## Pronto quando\n\n- `sumiu.py rodar`\n- `ciclo.py inventado`\n"
                 "- `ciclo.py <arquivo>` e `scripts/prova.py fontes SPEC-NNN`\n")
        self.assertEqual(pronto.problemas(texto, SCRIPTS), [
            "item 1: cita `sumiu.py`, que não existe em scripts/",
            "item 2: `ciclo.py inventado` — `inventado` não aparece no ciclo.py"])

    def test_cercas_de_codigo(self) -> None:
        # `~~~` e cerca de 4 crases contam; o título de exemplo dentro delas não abre seção.
        exemplo = "# x\n~~~\n## Pronto quando\n- exemplo\n~~~\n````\n```\n## Pronto quando\n````\n"
        texto = exemplo + "\n## Pronto quando\n\n- `a`\n- `b`\n- `c`\n"
        self.assertEqual((pronto.problemas(texto, SCRIPTS), pronto.itens(texto)),
                         ([], ["`a`", "`b`", "`c`"]))
        dentro = "## Pronto quando\n\n- `a`\n- `b`\n```\n- `c`\n```\n- `d`\n"
        self.assertEqual(pronto.problemas(dentro, SCRIPTS), ["linha fora da lista: ```"])

    def test_o_bloco_so_fecha_na_cerca_que_o_fecha(self) -> None:
        """O título de exemplo depois da primeira linha do bloco também fica dentro dele."""
        exemplo = "# x\n```\nexemplo\n## Pronto quando\n- `z`\n```\n"
        texto = exemplo + "\n## Pronto quando\n\n- `a`\n- `b`\n- `c`\n"
        self.assertEqual((pronto.problemas(texto, SCRIPTS), pronto.itens(texto)),
                         ([], ["`a`", "`b`", "`c`"]))

    def test_so_o_script_da_fabrica_e_conferido(self) -> None:
        texto = ("## Pronto quando\n\n- `pytest tests/test_login.py` passa\n"
                 "- `python3 evals/tarefas-fabrica/rodar.py validar` sai 0\n"
                 "- ``a `prova.py inventado` b`` e `scripts/ciclo.py estado`\n")
        self.assertEqual(pronto.problemas(texto, SCRIPTS),
                         ["item 3: `prova.py inventado` — `inventado` não aparece no prova.py"])

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
            {"type": "user", "message": {"content": [{"type": "text",
                                                      "text": "<command-name>/kairos-forge:sem-secao</command-name>"}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash",
                                                           "input": {"skill": "validar"}}]}},
            {"type": "assistant", "message": "texto"}, {"type": "system"}])
        self.addCleanup(os.unlink, caminho)
        # Sem o prefixo da fábrica não conta: `revisar` e `sem-secao` soltos são de outro dono.
        self.assertEqual(guardrail.skills_da_sessao(caminho, self.pasta),
                         ["revisar", "validar", "sem-secao"])
        sem_prefixo = transcript([chamada("revisar"), digitada("<command-name>/validar</command-name>")])
        self.addCleanup(os.unlink, sem_prefixo)
        self.assertEqual(guardrail.skills_da_sessao(sem_prefixo, self.pasta), [])
        self.assertEqual(guardrail.skills_da_sessao("/nao/existe.jsonl", self.pasta), [])

    def test_so_a_tool_skill_conta(self) -> None:
        """Outra ferramenta com `skill` na entrada, ou bloco que não é chamada, não vira skill."""
        caminho = transcript([
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"skill": "kairos-forge:revisar"}},
                {"type": "text", "name": "Skill", "input": {"skill": "kairos-forge:revisar"}}]}},
            chamada("kairos-forge:validar")])
        self.addCleanup(os.unlink, caminho)
        self.assertEqual(guardrail.skills_da_sessao(caminho, self.pasta), ["validar"])

    def test_duas_chamadas_na_mesma_resposta_entram_uma_vez(self) -> None:
        caminho = transcript([{"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "kairos-forge:revisar"}},
            {"type": "tool_use", "name": "Skill", "input": {"skill": "kairos-forge:revisar"}}]}}])
        self.addCleanup(os.unlink, caminho)
        self.assertEqual(guardrail.skills_da_sessao(caminho, self.pasta), ["revisar"])

    def test_so_a_pessoa_digita_o_comando(self) -> None:
        """A marca do comando digitado só conta no texto da pessoa, não em linha de outro tipo."""
        etiqueta = "command-name"   # a marca que o Claude Code grava quando a pessoa digita o comando
        caminho = transcript([
            {"type": "system", "message": {"content": f"<{etiqueta}>/kairos-forge:revisar</{etiqueta}>"}},
            digitada(f"<{etiqueta}>/kairos-forge:validar</{etiqueta}>")])
        self.addCleanup(os.unlink, caminho)
        self.assertEqual(guardrail.skills_da_sessao(caminho, self.pasta), ["validar"])

    def test_o_resultado_de_ferramenta_na_linha_da_pessoa(self) -> None:
        """A linha `user` com `tool_result`, a mais comum do transcript, não derruba a leitura."""
        etiqueta = "command-name"
        caminho = transcript([
            chamada("kairos-forge:revisar"),
            {"type": "user", "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "toolu_00",
                 "content": "Launching skill: kairos-forge:revisar"}]}},
            digitada(f"<{etiqueta}>/kairos-forge:validar</{etiqueta}>")])
        self.addCleanup(os.unlink, caminho)
        self.assertEqual(guardrail.skills_da_sessao(caminho, self.pasta), ["revisar", "validar"])

    def test_o_transcript_gravado_pelo_claude_code(self) -> None:
        """As duas linhas reais do 2.1.328, salvas como anexo da pesquisa (fato 6)."""
        anexo = RAIZ.parent / "docs/pesquisa/anexos/claude-code-2.1.328-skill-no-transcript.jsonl"
        linhas = [json.loads(l) for l in anexo.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([l["type"] for l in linhas], ["assistant", "user"])
        for linha in linhas:
            caminho = transcript([linha])
            self.addCleanup(os.unlink, caminho)
            self.assertEqual(guardrail.skills_da_sessao(caminho), ["pesquisar"], linha["type"])

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
        nomes = ["um", "dois", "tres", "quatro", "cinco", "seis"]
        for nome in nomes:
            (self.pasta / nome).mkdir(exist_ok=True)
            (self.pasta / nome / "SKILL.md").write_text(f"## Pronto quando\n\n{longo}", encoding="utf-8")
        caminho = transcript([chamada(f"kairos-forge:{nome}") for nome in nomes])
        self.addCleanup(os.unlink, caminho)
        texto = guardrail.pronto_das_skills({"transcript_path": caminho}, self.pasta)
        # Blocos inteiros, a skill usada por último primeiro; a que não cabe vai pelo nome.
        self.assertIn("/seis:\n", texto)
        self.assertIn("/cinco:\n", texto)
        self.assertNotIn("/um:\n", texto)
        self.assertIn("Sem espaço para o `## Pronto quando` de /um", texto)
        for nome in nomes:
            if f"/{nome}:\n" in texto:
                self.assertEqual(texto.count(f"`item 6 "), texto.count(f"`item 0 "))   # nada cortado
        self.assertLess(len(guardrail.CONFERENCIA) + len(texto), guardrail.TETO_DO_HOOK)
        self.assertEqual(guardrail.caber_no_teto([("a", "/a:\n- `x`")]), "/a:\n- `x`")

    def test_o_teto_conta_o_bloco_e_a_separacao(self) -> None:
        """Cada bloco custa o tamanho dele mais os 2 da separação: o que fecha o espaço cabe,
        um caractere a mais vai pelo nome."""
        from unittest import mock
        reserva = len(guardrail.CONFERENCIA) + len(guardrail.CABECA_DO_PRONTO) + 400
        with mock.patch.object(guardrail, "TETO_DO_HOOK", reserva + 100):   # 100 de espaço
            self.assertEqual(guardrail.caber_no_teto([("a", "a" * 98)]), "a" * 98)
            self.assertNotIn("a" * 99, guardrail.caber_no_teto([("a", "a" * 99)]))
            self.assertEqual(guardrail.caber_no_teto([("a", "a" * 48), ("b", "b" * 48)]),
                             "a" * 48 + "\n\n" + "b" * 48)
            apertado = guardrail.caber_no_teto([("a", "a" * 49), ("b", "b" * 49)])
            self.assertTrue(apertado.startswith(
                "b" * 49 + "\n\nSem espaço para o `## Pronto quando` de /a:"), apertado)

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

    def test_linha_malformada_nao_derruba_a_conferencia(self) -> None:
        caminho = transcript([
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill",
                                                           "input": "kairos-forge:revisar"}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill",
                                                           "input": ["kairos-forge:revisar"]}]}},
            chamada("kairos-forge:validar")])
        with open(caminho, "a", encoding="utf-8") as f:
            f.write("[" * 200_000 + "\n")   # aninhado demais para o json
        self.addCleanup(os.unlink, caminho)
        self.assertEqual(guardrail.skills_da_sessao(caminho, self.pasta), ["validar"])
        self.assertEqual(guardrail.skills_da_sessao("a\0b", self.pasta), [])

    def test_falha_na_lista_nao_tira_a_conferencia(self) -> None:
        from unittest import mock
        with tempfile.TemporaryDirectory() as cwd, \
                mock.patch.object(guardrail, "pronto_das_skills", side_effect=RuntimeError("x")):
            codigo, out, _ = hook("conferir", {"prompt": "faltou algo?", "cwd": cwd,
                                               "hook_event_name": "UserPromptSubmit"})
            eventos = "".join(p.read_text() for p in Path(cwd).rglob("*.jsonl"))
        self.assertEqual(codigo, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["additionalContext"],
                         guardrail.CONFERENCIA)
        self.assertIn("guardrail_erro", eventos)

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
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        saida = io.StringIO()
        with redirect_stdout(saida):
            achados = guardrail.marcas_e_fontes(self.raiz)
        # A marca é problema; a fonte nasce em aviso, porque olha o repositório inteiro.
        self.assertEqual(achados, ["a.py:2: marca de depuração que sobrou (forge-depura)"])
        self.assertIn("docs/nota.md:1: cita docs/pesquisa/sumiu.md, que não existe", saida.getvalue())
        self.assertIn("docs/pesquisa/ruim.md: sem **Resposta:**", saida.getvalue())
        (self.raiz / ".agents").mkdir()
        (self.raiz / ".agents" / "guardrails.json").write_text('{"modos": {"fontes": "bloqueio"}}',
                                                             encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            self.assertIn("docs/pesquisa/ruim.md: sem **Resposta:**", guardrail.marcas_e_fontes(self.raiz))
        r = subprocess.run([sys.executable, "-B", str(RAIZ / "guardrail.py"), "verificar", str(self.raiz)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("marca de depuração que sobrou", r.stdout)

    def test_limpo_e_sem_base(self) -> None:
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        with redirect_stdout(io.StringIO()) as saida:
            self.assertEqual(guardrail.marcas_e_fontes(self.raiz), [])
        self.assertEqual(saida.getvalue(), "")
        vazio = Path(tempfile.mkdtemp(prefix="kairos-forge-sem-git-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(vazio, ignore_errors=True))
        with redirect_stdout(io.StringIO()) as saida:
            self.assertEqual(guardrail.marcas_e_fontes(vazio), [])
        # Sem base para o diff, a marca não foi procurada, e isso aparece.
        self.assertIn("marca de depuração não conferida", saida.getvalue())

    def test_sem_o_prova_py_ao_lado(self) -> None:
        """Sem o prova.py importável (a cópia avulsa do guardrail), as duas conferências
        falham abertas com lista vazia — a soma não quebra o `verificar` — e dizem o que não olharam."""
        from unittest import mock
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        with mock.patch.dict(sys.modules, {"prova": None}), redirect_stdout(io.StringIO()) as saida:
            self.assertEqual(guardrail.marcas_e_fontes(self.raiz), [])
        self.assertIn("marca de depuração não conferida: ModuleNotFoundError", saida.getvalue())
        self.assertIn("fontes salvas não conferidas: ModuleNotFoundError", saida.getvalue())


class AListaDeSkillsDaTrajetoria(unittest.TestCase):
    def test_toda_skill_da_pasta_e_reconhecida(self) -> None:
        for p in sorted((RAIZ.parent / "skills").glob("*/SKILL.md")):
            with self.subTest(p.parent.name):
                self.assertEqual(execucao.SKILLS.findall(f"/kairos-forge:{p.parent.name} já"),
                                 [p.parent.name])
                self.assertEqual(execucao.SKILLS.findall(f"  /{p.parent.name}"), [p.parent.name])
                # Só no começo do prompt, e só o nome inteiro.
                self.assertEqual(execucao.SKILLS.findall(f"rode /{p.parent.name} já"), [])
                self.assertEqual(execucao.SKILLS.findall(f"/{p.parent.name}-cpf"), [])

    def test_sem_a_pasta_so_com_o_prefixo(self) -> None:
        rx = execucao.regex_das_skills(Path("/nao/existe"))
        self.assertEqual(rx.findall("/kairos-forge:qualquer e /solta"), ["qualquer"])
        self.assertEqual(rx.findall("/solta"), [])
        self.assertEqual(execucao.SKILLS.findall("/rodarzinho"), [])


if __name__ == "__main__":
    unittest.main()
