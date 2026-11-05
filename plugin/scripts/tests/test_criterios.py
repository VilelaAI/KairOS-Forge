"""Testes do `qualidade.py criterios` — o mutante por critério de aceite (ADR-0054).

Do PDD Kit: a especificação que verifica mas não descarta bug nenhum é verificação de
fachada. Aqui o critério de aceite é a especificação, e o comando que a Matriz de testes
lhe dá é quem verifica. A leitura da SPEC é testada sobre texto; o motor (rodízio,
segunda passada, teto) com uma suíte falsa que diz quem percebe qual mutante; o caminho
inteiro, num repositório git de verdade com testes de verdade.

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
import textwrap
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import qualidade  # noqa: E402

PY = sys.executable

SPEC = """\
# SPEC-001 — Idade

## Requisitos rastreáveis

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| IDA-01 | Adulto | P1 | WHEN 18 THEN adulto | Concluído | verificado: `{py} -m unittest -q test_idade` (05/11) |
| IDA-02 | Roda | P1 | WHEN 30 THEN roda | Concluído | verificado: rodei (05/11) |
| IDA-03 | Menor | P2 | WHEN 17 THEN menor | Concluído | verificado: `{py} -m unittest -q test_idade` (05/11) |
| IDA-04 | Futuro | P3 | WHEN x THEN y | Pendente | — |
| IDA-05 | Saudar | P2 | WHEN nome THEN olá | Concluído | verificado: olhei a tela (05/11) |
| IDA-06 | Quebrado | P2 | WHEN q THEN q | Concluído | verificado: rodei (05/11) |

## Matriz de testes

| Requisito | Tipo | Responsável | Comando/gate | Evidência esperada |
|---|---|---|---|---|
| IDA-01 | unit | [Ricardo] | `{py} -m unittest -q test_idade` | fronteira |
| IDA-02 | unit | [Ricardo] | `{py} -m unittest -q test_roda` | roda |
| IDA-05 | manual | [Ricardo] | `abrir a tela` | olho |
| IDA-06 | unit | [Ricardo] | `{py} -m unittest -q test_quebrado` | — |
""".replace("{py}", PY)

CODIGO = '''\
def classificar(idade):
    if idade >= 18:
        return "adulto"
    return "menor"


def saudar(nome):
    return "olá, " + nome
'''

TESTES = {
    "test_idade.py": '''\
        import unittest, pessoa
        class T(unittest.TestCase):
            def test_fronteira(self):
                self.assertEqual(pessoa.classificar(18), "adulto")
                self.assertEqual(pessoa.classificar(17), "menor")
        ''',
    "test_roda.py": '''\
        import unittest, pessoa
        class T(unittest.TestCase):
            def test_roda(self):
                pessoa.classificar(30)
        ''',
    "test_quebrado.py": '''\
        import unittest
        class T(unittest.TestCase):
            def test_quebrado(self):
                self.fail("vermelho")
        ''',
}


class Celula(unittest.TestCase):
    def test_so_o_que_esta_entre_crases_vira_comando(self) -> None:
        self.assertEqual(qualidade.comandos_da_celula("verificado: rodei os testes (05/11)"), [])
        self.assertEqual(qualidade.comandos_da_celula("`npm test -- login` e `npm run e2e`"),
                         ["npm test -- login", "npm run e2e"])

    def test_rotulo_e_a_definir_entre_crases_nao_sao_comando(self) -> None:
        for celula in ("`verificado: pnpm test (12/06)`", "`a definir`", "` `",
                       "`planejado: pytest`", "`em progresso: falta o e2e`"):
            self.assertEqual(qualidade.comandos_da_celula(celula), [], celula)


class Matriz(unittest.TestCase):
    def test_as_colunas_vem_do_cabecalho(self) -> None:
        matriz = qualidade.comandos_da_matriz(textwrap.dedent("""\
            ## Matriz de testes

            | Comando/gate | Tipo | Requisito |
            |---|---|---|
            | `pytest -k login` | unit | LOG-01, LOG-02 |
            | `abrir o app` | Manual | LOG-03 |
            """))
        self.assertEqual(matriz, {"LOG-01": ["pytest -k login"], "LOG-02": ["pytest -k login"]})

    def test_varias_linhas_juntam_sem_repetir_e_o_manual_fica_de_fora(self) -> None:
        matriz = qualidade.comandos_da_matriz(textwrap.dedent("""\
            ## Matriz de testes

            | Requisito | Tipo | Responsável | Comando/gate | Evidência |
            |---|---|---|---|---|
            | LOG-01, LOG-02 | unit | [Ricardo] | `pytest -k login` | x |
            | LOG-01 | unit | [Ricardo] | `pytest -k login` | x |
            | LOG-01 · LOG-04 | e2e | [Ricardo] | `pytest -k e2e` | x |
            | LOG-03 | manual | [Ricardo] | `abrir o app` | x |
            | LOG-05 | unit |
            """))
        self.assertEqual(matriz, {"LOG-01": ["pytest -k login", "pytest -k e2e"],
                                  "LOG-02": ["pytest -k login"], "LOG-04": ["pytest -k e2e"],
                                  "LOG-05": []})

    def test_sem_matriz_ou_sem_coluna_de_comando_nao_ha_comando(self) -> None:
        self.assertEqual(qualidade.comandos_da_matriz("# SPEC\n\n## Objetivo\n\nx\n"), {})
        self.assertEqual(qualidade.comandos_da_matriz(
            "## Matriz de testes\n\n| Requisito | Tipo |\n|---|---|\n| A-01 | unit |\n"), {})
        self.assertEqual(qualidade.comandos_da_matriz("## Matriz de testes\n\nnada\n"), {})


class CriteriosDaSpec(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.arquivo = Path(self._tmp.name) / "SPEC-001-idade.md"
        self.arquivo.write_text(SPEC, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_matriz_primeiro_verificado_depois_pendente_fora(self) -> None:
        por_id = {c["id"]: c for c in qualidade.criterios_da_spec(self.arquivo, None)}
        self.assertEqual(por_id["IDA-01"]["origem"], "matriz")
        self.assertEqual(por_id["IDA-03"]["origem"], "verificado")
        self.assertEqual(por_id["IDA-03"]["comando"], por_id["IDA-01"]["comando"])
        self.assertEqual(por_id["IDA-04"]["resultado"], "pendente")
        self.assertEqual((por_id["IDA-05"]["resultado"], por_id["IDA-05"]["origem"]),
                         ("sem_comando", None))
        self.assertNotIn("resultado", por_id["IDA-02"])

    def test_filtro_escolhe_e_traz_o_pendente_pedido(self) -> None:
        criterios = qualidade.criterios_da_spec(self.arquivo, {"IDA-04", "IDA-02"})
        self.assertEqual([c["id"] for c in criterios], ["IDA-02", "IDA-04"])
        self.assertEqual(criterios[1]["resultado"], "sem_comando")

    def test_varios_comandos_do_mesmo_criterio_rodam_juntos(self) -> None:
        self.arquivo.write_text(SPEC + "| IDA-02 | e2e | [Ricardo] | `make e2e` | x |\n",
                                encoding="utf-8")
        por_id = {c["id"]: c for c in qualidade.criterios_da_spec(self.arquivo, None)}
        self.assertTrue(por_id["IDA-02"]["comando"].endswith("test_roda && make e2e"))

    def test_gates_juntam_criterios_do_mesmo_comando(self) -> None:
        gates = qualidade._gates(qualidade.criterios_da_spec(self.arquivo, None))
        self.assertEqual([g["ids"] for g in gates], [["IDA-01", "IDA-03"], ["IDA-02"], ["IDA-06"]])


class Motor(unittest.TestCase):
    """O rodízio e a segunda passada, com uma suíte falsa: `percebe[comando]` é o
    conjunto de mutantes (pelo índice) que aquele comando percebe."""

    def rodar(self, percebe: dict[str, set[int]], n: int, teto: int = 900,
              base: dict[str, str] | None = None, plantaveis: set[int] | None = None):
        self.chamadas: list[tuple[str, int | None]] = []
        atual: list[int | None] = [None]
        mutantes = [{"arquivo": "a.py", "linha": i + 1, "original": "==", "mutado": "!=",
                     "indice": i} for i in range(n)]

        @contextlib.contextmanager
        def plantar(_arvore, sitio):
            if plantaveis is not None and sitio["indice"] not in plantaveis:
                yield False
                return
            atual[0] = sitio["indice"]
            try:
                yield True
            finally:
                atual[0] = None

        def rodar(comando, _cwd, _tempo):
            self.chamadas.append((comando, atual[0]))
            if atual[0] is None:
                return (base or {}).get(comando, "passou"), 0.01, ["última"]
            return ("falhou" if atual[0] in percebe[comando] else "passou"), 0.01, []

        gates = [{"comando": c, "ids": [c.upper()]} for c in percebe]
        with mock.patch.object(qualidade, "mutante_aplicado", plantar), \
                mock.patch.object(qualidade, "rodar", rodar):
            qualidade.julgar_criterios(gates, mutantes, Path("."), (60, teto))
        return {g["comando"]: g for g in gates}, mutantes

    def test_rodizio_espalha_o_credito_entre_os_criterios(self) -> None:
        gates, mutantes = self.rodar({"a": {0, 1, 2, 3}, "b": {0, 1, 2, 3}}, 4)
        self.assertEqual([m["pego_por"] for m in mutantes], [["A"], ["B"], ["A"], ["B"]])
        self.assertEqual({c: g["resultado"] for c, g in gates.items()},
                         {"a": "descarta", "b": "descarta"})
        self.assertEqual(len([c for c in self.chamadas if c[1] is not None]), 4)

    def test_quem_o_rodizio_nao_serviu_ainda_tenta_os_outros_mutantes(self) -> None:
        # `a` pega tudo e chega primeiro em 0 e 2; `b` só percebe o 2 — e o rodízio deu o
        # 2 para `a`. Sem a segunda passada, `b` sairia de fachada sem ter visto o 2.
        gates, mutantes = self.rodar({"a": {0, 1, 2, 3}, "b": {2}}, 4)
        self.assertEqual(gates["b"]["resultado"], "descarta")
        self.assertEqual(gates["b"]["percebeu"]["indice"], 2)
        self.assertEqual(mutantes[2]["pego_por"], ["A"])          # o primeiro crédito fica

    def test_fachada_so_depois_de_passar_com_todos(self) -> None:
        gates, mutantes = self.rodar({"a": {0, 1}, "b": set()}, 3)
        self.assertEqual(gates["b"]["resultado"], "fachada")
        self.assertEqual({m for c, m in self.chamadas if c == "b"}, {None, 0, 1, 2})
        self.assertEqual([m["resultado"] for m in mutantes], ["pego", "pego", "sem_criterio"])

    def test_mutante_que_ninguem_percebe_passou_por_todos(self) -> None:
        _, mutantes = self.rodar({"a": set(), "b": set(), "c": {0}}, 2)
        self.assertEqual(mutantes[1]["resultado"], "sem_criterio")
        self.assertEqual(sorted(c for c, m in self.chamadas if m == 1), ["a", "b", "c"])

    def test_teto_deixa_nao_julgado_e_nao_executado_com_o_motivo(self) -> None:
        gates, mutantes = self.rodar({"a": {0}}, 2, teto=-1)
        self.assertEqual(gates["a"]["resultado"], "nao_julgado")
        self.assertIn("teto de -1s", gates["a"]["motivo"])
        self.assertEqual({m["resultado"] for m in mutantes}, {"nao_executado"})
        self.assertIn("teto", mutantes[0]["motivo"])

    def test_base_vermelha_fica_fora_e_ninguem_julga_os_mutantes(self) -> None:
        gates, mutantes = self.rodar({"a": {0}, "b": {0}}, 1, base={"a": "falhou", "b": "tempo"})
        self.assertEqual({g["resultado"] for g in gates.values()}, {"vermelho"})
        self.assertEqual(gates["a"]["ultimas_linhas"], ["última"])
        self.assertEqual(mutantes[0]["resultado"], "nao_executado")
        self.assertEqual(mutantes[0]["motivo"], qualidade.SEM_GATE_VERDE)

    def test_sitio_que_nao_confere_nao_conta_contra_o_criterio(self) -> None:
        gates, mutantes = self.rodar({"a": set()}, 3, plantaveis={1})
        self.assertEqual(gates["a"]["resultado"], "fachada")
        self.assertEqual([m["resultado"] for m in mutantes],
                         ["nao_executado", "sem_criterio", "nao_executado"])
        self.assertEqual(mutantes[0]["motivo"], qualidade.NAO_CONFERE)
        self.assertNotIn(("a", 0), self.chamadas)

    def test_nenhum_sitio_plantavel_nao_e_fachada(self) -> None:
        gates, _ = self.rodar({"a": set()}, 2, plantaveis=set())
        self.assertEqual(gates["a"]["resultado"], "nao_julgado")
        self.assertIn("nenhum mutante", gates["a"]["motivo"])

    def test_por_mutante_tem_um_piso_e_o_teto_do_tempo_limite(self) -> None:
        gates, _ = self.rodar({"a": {0}}, 1)
        self.assertEqual(gates["a"]["por_mutante"], 30.0)


class Repo(unittest.TestCase):
    """Repositório git de verdade: a base em `main`, a entrega na árvore."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-criterios-")
        self.raiz = Path(self._tmp.name).resolve()
        self.git("init", "-q", "-b", "main")
        self.escrever("pessoa.py", "X = 1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.escrever("pessoa.py", CODIGO)
        for nome, texto in TESTES.items():
            self.escrever(nome, texto)
        self.escrever("docs/specs/SPEC-001-idade.md", SPEC)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.raiz), "-c", "user.name=t",
                        "-c", "user.email=t@t", *args], check=True, capture_output=True)

    def escrever(self, rel: str, texto: str) -> None:
        p = self.raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(texto), encoding="utf-8")

    def cli(self, *args: str) -> tuple[int, str]:
        saida = io.StringIO()
        antes, argv = os.getcwd(), sys.argv
        try:
            os.chdir(self.raiz)
            sys.argv = ["qualidade.py", "criterios", *args]
            with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(saida):
                codigo = qualidade.main()
        finally:
            os.chdir(antes)
            sys.argv = argv
        return codigo, saida.getvalue()


class CriteriosNoDiff(Repo):
    def test_cada_criterio_com_o_seu_veredicto(self) -> None:
        r = qualidade.analisar_criterios(self.raiz, "main", "SPEC-001", None, 25, (60, 300))
        self.assertNotIn("erro", r)
        por_id = {c["id"]: c for c in r["criterios"]}
        self.assertEqual({i: c["resultado"] for i, c in por_id.items()},
                         {"IDA-01": "descarta", "IDA-02": "fachada", "IDA-03": "descarta",
                          "IDA-04": "pendente", "IDA-05": "sem_comando", "IDA-06": "vermelho"})
        self.assertEqual(por_id["IDA-01"]["percebeu"]["funcao"], "classificar")
        self.assertEqual(por_id["IDA-01"]["compartilhado_com"], ["IDA-03"])
        self.assertNotIn("compartilhado_com", por_id["IDA-02"])
        sem = [m for m in r["mutantes"] if m["resultado"] == "sem_criterio"]
        self.assertEqual({m["funcao"] for m in sem}, {"saudar"})
        self.assertEqual(r["placar"], {"descarta": 2, "fachada": 1, "vermelho": 1,
                                       "sem_comando": 1, "pendente": 1, "nao_julgado": 0,
                                       "sem_criterio": 2})
        self.assertEqual(r["arquivo"], "docs/specs/SPEC-001-idade.md")
        self.assertEqual((self.raiz / "pessoa.py").read_text(), CODIGO)  # nunca tocado
        worktrees = subprocess.run(["git", "-C", str(self.raiz), "worktree", "list"],
                                   capture_output=True, text=True).stdout
        self.assertEqual(len(worktrees.strip().splitlines()), 1)

    def test_sem_sitio_no_diff_avisa_e_nao_julga(self) -> None:
        self.escrever("pessoa.py", "X = 2\n")
        r = qualidade.analisar_criterios(self.raiz, "main", "SPEC-001", {"IDA-01"}, 25, (60, 300))
        self.assertIn("nada a julgar", r["aviso"])
        self.assertEqual(r["criterios"][0]["resultado"], "nao_julgado")
        self.assertEqual(r["criterios"][0]["motivo"], r["aviso"])

    def test_sem_comando_algum_avisa(self) -> None:
        r = qualidade.analisar_criterios(self.raiz, "main", "SPEC-001", {"IDA-05"}, 25, (60, 300))
        self.assertIn("nenhum critério com comando", r["aviso"])
        self.assertEqual({m["resultado"] for m in r["mutantes"]}, {"nao_executado"})

    def test_spec_que_nao_existe_ou_id_fora_da_spec_e_erro(self) -> None:
        r = qualidade.analisar_criterios(self.raiz, "main", "SPEC-009", None, 25, (60, 300))
        self.assertIn("não achei SPEC-009", r["erro"])
        r = qualidade.analisar_criterios(self.raiz, "main", "SPEC-001", {"IDA-01", "IDA-9"},
                                         25, (60, 300))
        self.assertIn("IDA-9 não está", r["erro"])
        self.assertNotIn("criterios", r)                  # nada rodou
        r = qualidade.analisar_criterios(self.raiz, "nada", "SPEC-001", None, 25, (60, 300))
        self.assertIn("sem merge-base", r["erro"])

    def test_spec_sem_requisito_e_erro(self) -> None:
        self.escrever("docs/specs/SPEC-002-vazia.md", "# SPEC-002\n\n## Objetivo\n\nx\n")
        r = qualidade.analisar_criterios(self.raiz, "main", "SPEC-002", None, 25, (60, 300))
        self.assertIn("não tem requisito", r["erro"])

    def test_worktree_que_nao_monta_e_erro_e_ninguem_e_julgado(self) -> None:
        with mock.patch.object(qualidade, "montar_worktree", return_value="sem disco"):
            r = qualidade.analisar_criterios(self.raiz, "main", "SPEC-001", {"IDA-02"},
                                             25, (60, 300))
        self.assertEqual(r["erro"], "sem disco")
        self.assertEqual(r["criterios"][0]["resultado"], "nao_julgado")
        self.assertEqual(r["criterios"][0]["motivo"], "sem disco")


class Cli(Repo):
    def test_fachada_sai_1_e_mostra_o_que_ninguem_percebe(self) -> None:
        codigo, saida = self.cli("SPEC-001", "--base", "main")
        self.assertEqual(codigo, 1)
        self.assertIn("❌ IDA-02 (P1) — fachada: passou com os 5 mutantes", saida)
        self.assertIn("✅ IDA-01 (P1) — percebe `>=` → `>` em pessoa.py:2 classificar "
                      "(o mesmo comando de IDA-03)", saida)
        self.assertIn("🟡 pessoa.py:8 saudar: `+` → `-`", saida)
        self.assertIn("· IDA-04 (P3) — pendente", saida)
        self.assertIn("percebe: 2 · fachada: 1 · vermelho: 1 · sem comando: 1 · "
                      "não julgado: 0 · pendente: 1", saida)
        self.assertIn("5 de 5 sítios, 2 sem critério", saida)

    def test_todos_percebem_sai_0_e_json_tem_a_forma(self) -> None:
        codigo, saida = self.cli("SPEC-001", "--base", "main", "--requisitos", "IDA-01",
                                 "--json")
        self.assertEqual(codigo, 0)
        r = json.loads(saida)
        self.assertEqual(r["criterios"][0]["resultado"], "descarta")
        self.assertEqual(r["spec"], "SPEC-001")

    def test_max_limita_os_mutantes(self) -> None:
        codigo, saida = self.cli("SPEC-001", "--base", "main", "--requisitos", "IDA-01",
                                 "--max", "2", "--json")
        self.assertEqual(len(json.loads(saida)["mutantes"]), 2)

    def test_sem_spec_e_erro_e_nao_julgado_imprime_o_motivo(self) -> None:
        codigo, saida = self.cli("--base", "main")
        self.assertEqual(codigo, 1)
        self.assertIn("diga a SPEC", saida)
        codigo, saida = self.cli("SPEC-001", "--base", "main", "--requisitos", "IDA-02",
                                 "--teto", "-1")
        self.assertEqual(codigo, 0)
        self.assertIn("⚠️  IDA-02 (P1) — não julgado: teto de -1s", saida)
        self.assertNotIn("nenhum critério percebe", saida)

    def test_aviso_aparece_na_saida(self) -> None:
        codigo, saida = self.cli("SPEC-001", "--base", "main", "--requisitos", "IDA-05")
        self.assertEqual(codigo, 0)
        self.assertIn("nenhum critério com comando", saida)
        self.assertIn("sem comando entre crases", saida)


if __name__ == "__main__":
    unittest.main()
