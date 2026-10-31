"""Testes do `qualidade.py` — os gates de "deixar certo" sobre o diff (ADR-0045).

Só stdlib. A leitura de estrutura (complexidade, impressões, sítios de mutação) é
testada direto sobre texto; o caminho completo — diff, cobertura, duplicação e
mutação de verdade numa suíte — roda num repositório git temporário.

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
import time
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import qualidade  # noqa: E402

PYTHON_COMPLEXO = '''\
def f(x, ys):
    if x > 0 and x < 10:
        return [y for y in ys if y]
    elif x == 0:
        for y in ys:
            while y:
                y -= 1
    try:
        pass
    except ValueError:
        pass
    return 1 if x else 2
'''

JS = '''\
function soma(a, b) {
  if (a && b) { return a + b; }
  const c = a ?? 0;
  return c ? c : b?.valor;
}

const lista = (xs) => {
  return xs.filter((x) => {
    if (x) { return true; }
    return false;
  });
};

class Conta {
  async sacar(valor: number): Promise<void> {
    if (valor > this.saldo) { throw new Error('saldo {insuficiente}'); }
    this.saldo -= valor;
  }
}

function criar({ nome, idade }) {
  return nome || idade;
}
'''

GO = '''\
package conta

// Sacar { não é corpo }
func (c *Conta) Sacar(v int, extra interface{}) (interface{}, error) {
\tif v > c.saldo && v > 0 {
\t\treturn nil, erro
\t}
\tfor _, x := range c.itens {
\t\tswitch x {
\t\tcase 1:
\t\tcase 2:
\t\t}
\t}
\treturn nil, nil
}

func Novo() *Conta {
\treturn &Conta{}
}
'''


def nomes_e_cc(funcoes) -> dict[str, int]:
    return {f.nome: f.complexidade for f in funcoes}


class Limpar(unittest.TestCase):
    def test_python_apaga_comentario_e_miolo_de_string(self) -> None:
        texto = 'x = "a == b"  # c < d\ny = \'\'\'\nz > w\n\'\'\''
        limpo = qualidade.limpar(texto, "python")
        self.assertEqual(len(limpo), len(texto))
        self.assertEqual(limpo.count("\n"), texto.count("\n"))
        self.assertNotIn("==", limpo)
        self.assertNotIn("<", limpo)
        self.assertNotIn(">", limpo)
        self.assertIn('""', limpo.replace(" ", ""))

    def test_js_apaga_bloco_linha_e_template(self) -> None:
        texto = "a /* { */ && b // }\nc = `x ${y} {` + 'q\\'{'"
        limpo = qualidade.limpar(texto, "js")
        self.assertEqual(len(limpo), len(texto))
        self.assertNotIn("{", limpo)
        self.assertNotIn("}", limpo)
        self.assertIn("&&", limpo)

    def test_go_string_crua_nao_escapa(self) -> None:
        limpo = qualidade.limpar("s := `a\\` + x == y", "go")
        self.assertIn("==", limpo)

    def test_template_do_js_e_string_crua_do_go_atravessam_linhas(self) -> None:
        for texto, linguagem in (("q = `select *\nwhere a == b`\nc = d != e", "js"),
                                 ("q := `select *\nwhere a == b`\nc := d != e", "go")):
            limpo = qualidade.limpar(texto, linguagem)
            self.assertNotIn("==", limpo, linguagem)
            self.assertIn("!=", limpo, linguagem)

    def test_codigo_depois_do_comentario_continua_codigo(self) -> None:
        self.assertIn("==", qualidade.limpar("a = 1  # x < y\nb == c", "python"))
        self.assertIn("==", qualidade.limpar("a // x < y\nb == c", "js"))
        self.assertIn("==", qualidade.limpar("a /* x < y */ == b", "js"))

    def test_string_sem_fechar_termina_na_quebra(self) -> None:
        limpo = qualidade.limpar("a = 'sem fim\nb == c", "python")
        self.assertIn("==", limpo)


class ComplexidadePython(unittest.TestCase):
    def test_conta_as_decisoes_do_crapper(self) -> None:
        fs = qualidade.funcoes_python("m.py", PYTHON_COMPLEXO)
        self.assertEqual(nomes_e_cc(fs), {"f": 9})

    def test_classe_prefixa_e_aninhada_nao_e_unidade(self) -> None:
        texto = textwrap.dedent('''\
            class A:
                @property
                def b(self):
                    def interna():
                        return 1 if self else 2
                    return interna()
            ''')
        fs = qualidade.funcoes_python("m.py", texto)
        self.assertEqual(nomes_e_cc(fs), {"A.b": 2})
        self.assertEqual(fs[0].inicio, 2)  # o decorador conta como início

    def test_sintaxe_invalida_e_none(self) -> None:
        self.assertIsNone(qualidade.funcoes_python("m.py", "def (:"))


class ComplexidadeTexto(unittest.TestCase):
    def test_js_funcao_arrow_metodo_e_desestruturacao(self) -> None:
        fs = qualidade.funcoes_texto("m.ts", JS, "js")
        self.assertEqual(nomes_e_cc(fs), {"soma": 6, "lista": 2, "sacar": 2, "criar": 2})

    def test_js_callback_aninhado_conta_para_a_de_fora(self) -> None:
        fs = {f.nome: f for f in qualidade.funcoes_texto("m.js", JS, "js")}
        self.assertEqual((fs["lista"].inicio, fs["lista"].fim), (7, 12))

    def test_impressao_e_do_corpo_inteiro_ate_a_chave_que_fecha(self) -> None:
        texto = "function f(a) {\n  return g(a)}\n"
        f, = qualidade.funcoes_texto("m.js", texto, "js")
        self.assertEqual(f.impressoes, qualidade.impressoes_tokens("{\n  return g(a)}"))

    def test_go_receptor_e_interface_vazia_nao_enganam_o_corpo(self) -> None:
        fs = qualidade.funcoes_texto("c.go", GO, "go")
        self.assertEqual(nomes_e_cc(fs), {"Conta.Sacar": 6, "Novo": 1})
        sacar = next(f for f in fs if f.nome == "Conta.Sacar")
        self.assertEqual((sacar.inicio, sacar.fim), (4, 15))


class Cobertura(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-qualidade-")
        self.raiz = Path(self._tmp.name).resolve()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def ler(self, nome: str, texto: str):
        (self.raiz / nome).write_text(texto, encoding="utf-8")
        return qualidade.ler_cobertura(self.raiz, self.raiz / nome)

    def test_coverage_py_json(self) -> None:
        cob, formato = self.ler("coverage.json", json.dumps(
            {"files": {"pkg/m.py": {"executed_lines": [1, 2], "missing_lines": [3]}}}))
        self.assertEqual(formato, "coverage.py json")
        self.assertEqual(cob.do_arquivo("pkg/m.py"), ({1, 2}, {1, 2, 3}))

    def test_lcov_com_caminho_absoluto(self) -> None:
        cob, formato = self.ler("lcov.info",
                                f"SF:{self.raiz}/src/a.ts\nDA:1,3\nDA:2,0\nend_of_record\n")
        self.assertEqual(formato, "lcov")
        self.assertEqual(cob.do_arquivo("src/a.ts"), ({1}, {1, 2}))

    def test_cobertura_xml_casa_por_sufixo(self) -> None:
        cob, formato = self.ler("coverage.xml", '<coverage><packages><package><classes>'
                                '<class filename="m.py"><lines><line number="4" hits="1"/>'
                                '<line number="5" hits="0"/></lines></class>'
                                '</classes></package></packages></coverage>')
        self.assertEqual(formato, "cobertura xml")
        self.assertEqual(cob.do_arquivo("pkg/m.py"), ({4}, {4, 5}))

    def test_go_coverprofile_tira_o_modulo(self) -> None:
        (self.raiz / "go.mod").write_text("module exemplo.com/app\n", encoding="utf-8")
        cob, formato = self.ler("coverage.out", "mode: set\n"
                                "exemplo.com/app/conta/c.go:4.10,6.2 2 1\n"
                                "exemplo.com/app/conta/c.go:8.1,8.9 1 0\n")
        self.assertEqual(formato, "go coverprofile")
        self.assertEqual(cob.do_arquivo("conta/c.go"), ({4, 5, 6}, {4, 5, 6, 8}))

    def test_go_coverprofile_so_tira_o_prefixo_do_proprio_modulo(self) -> None:
        cob, _ = self.ler("coverage.out", "mode: set\nconta/c.go:4.10,5.2 1 1\n")
        self.assertEqual(cob.do_arquivo("conta/c.go"), ({4, 5}, {4, 5}))  # sem go.mod
        (self.raiz / "go.mod").write_text("module exemplo.com/app\n", encoding="utf-8")
        cob, _ = self.ler("coverage.out", "mode: set\noutro.com/lib/c.go:4.10,5.2 1 1\n")
        self.assertEqual(cob.do_arquivo("outro.com/lib/c.go"), ({4, 5}, {4, 5}))

    def test_arquivo_que_o_relatorio_nao_menciona_e_zero(self) -> None:
        cob, _ = self.ler("coverage.json", json.dumps({"files": {}}))
        self.assertEqual(cob.do_arquivo("x.py"), (set(), set()))


class Crap(unittest.TestCase):
    def test_formula(self) -> None:
        self.assertEqual(qualidade.crap(1, 1.0), 1.0)
        self.assertEqual(qualidade.crap(10, 0.0), 110.0)
        self.assertEqual(qualidade.crap(5, 0.5), 8.1)

    def test_sem_cobertura_cc_no_limite_ja_reprova(self) -> None:
        f = qualidade.Funcao("m.py", "f", 1, 20, 10, set())
        self.assertEqual(qualidade.avaliar_funcao(f, None, 10)["veredicto"], "acima_do_limite")

    def test_sem_cobertura_cc_abaixo_e_indeterminado(self) -> None:
        f = qualidade.Funcao("m.py", "f", 1, 20, 4, set())
        item = qualidade.avaliar_funcao(f, None, 10)
        self.assertEqual(item["veredicto"], "indeterminado")
        self.assertIsNone(item["crap"])


class Duplicacao(unittest.TestCase):
    MESMA_FORMA = textwrap.dedent('''\
        def alfa(xs):
            ys = filtrar(xs, impar)
            total = somar(ys)
            return mapear(ys, total)

        def beta(itens):
            mantidos = filtrar(itens, par)
            soma = somar(mantidos)
            return mapear(mantidos, soma)

        def gama(a):
            if a > 1:
                return outra(a)
            return a
        ''')

    def test_nome_e_literal_nao_contam(self) -> None:
        fs = {f.nome: f for f in qualidade.funcoes_python("m.py", self.MESMA_FORMA)}
        self.assertEqual(qualidade.jaccard(fs["alfa"].impressoes, fs["beta"].impressoes), 1.0)
        self.assertLess(qualidade.jaccard(fs["alfa"].impressoes, fs["gama"].impressoes), 0.5)

    def test_tokens_do_js_normalizam_local_e_mantem_chamada(self) -> None:
        a = qualidade.impressoes_tokens("{ const x = filtrar(xs, 1); return mapear(x); }")
        b = qualidade.impressoes_tokens("{ const y = filtrar(ys, 2); return mapear(y); }")
        c = qualidade.impressoes_tokens("{ const y = ordenar(ys, 2); return juntar(y); }")
        self.assertEqual(qualidade.jaccard(a, b), 1.0)
        self.assertLess(qualidade.jaccard(a, c), 0.8)

    def test_conjunto_vazio_nao_e_duplicado(self) -> None:
        self.assertEqual(qualidade.jaccard(set(), {"a"}), 0.0)

    def test_nome_no_fim_do_texto_tambem_normaliza(self) -> None:
        self.assertEqual(qualidade.impressoes_tokens("return a + b"),
                         qualidade.impressoes_tokens("return x + y"))

    def test_uma_impressao_por_janela_completa(self) -> None:
        # 5 tokens distintos, janelas de 4: exatamente 2 — janela cortada no fim não conta
        self.assertEqual(len(qualidade.impressoes_tokens("( ) ; , .")), 2)
        self.assertEqual(qualidade.impressoes_tokens("( )"), set())


class SitiosDeMutacao(unittest.TestCase):
    def sitios(self, linha: str, linguagem: str = "python") -> list[tuple[str, str]]:
        return [(s["original"], s["mutado"])
                for s in qualidade._sitios_da_linha("m", 1, linha, linguagem)]

    def test_operador_maior_nao_vira_dois(self) -> None:
        self.assertEqual(self.sitios("    if a <= b:"), [("<=", "<")])
        self.assertEqual(self.sitios("    ok = a === b", "js"), [("===", "!==")])

    def test_seta_sinal_e_atribuicao_nao_sao_operadores(self) -> None:
        self.assertEqual(self.sitios("    x = -1", "js"), [])
        self.assertEqual(self.sitios("    f = (a) => a", "js"), [])
        self.assertEqual(self.sitios("    x += 1"), [])
        self.assertEqual(self.sitios("    y = a - b"), [("-", "+")])

    def test_cabecalho_de_funcao_nao_muta(self) -> None:
        self.assertEqual(self.sitios("def f(a=1 + 2):"), [])

    def test_retorno_com_acento_respeita_a_coluna(self) -> None:
        texto = 'def f():\n    return "não" + x  # fim\n'
        s = qualidade.retornos_python("m.py", texto, [], {2})
        self.assertEqual(s[0]["original"], 'return "não" + x')
        mutado = qualidade.aplicar_mutacao(texto, s[0])
        self.assertIn("    return None  # fim", mutado)

    def test_python_que_nao_compila_ainda_tem_operador_e_nenhum_retorno(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "m.py").write_text("x = a + b\ndef (:\n    return x\n", encoding="utf-8")
            s = qualidade.sitios_de_mutacao(Path(d), "m.py", {1, 3})
        self.assertEqual([(x["linha"], x["tipo"]) for x in s], [(1, "operador")])

    def test_retorno_js_so_nas_linhas_tocadas(self) -> None:
        texto = "  return a + 1;\n  return b + 2;\n"
        limpo = qualidade.limpar(texto, "js").split("\n")
        s = qualidade.retornos_js("m.js", texto, limpo, {2})
        self.assertEqual([(x["linha"], x["original"]) for x in s], [(2, "return b + 2")])

    def test_retorno_js_ignora_ponto_e_virgula_do_comentario(self) -> None:
        texto = "  return total + 1; // a; b\n"
        limpo = qualidade.limpar(texto, "js").split("\n")
        s = qualidade.retornos_js("m.js", texto, limpo, {1})
        self.assertEqual(s[0]["original"], "return total + 1")

    def test_texto_que_nao_confere_nao_muta(self) -> None:
        sitio = {"linha": 1, "coluna": 0, "original": "x", "mutado": "y"}
        self.assertIsNone(qualidade.aplicar_mutacao("a", sitio))

    def test_escolher_divide_as_vagas_e_devolve_a_sobra(self) -> None:
        ret = [{"tipo": "retorno", "arquivo": "a", "linha": i, "coluna": 0} for i in range(10)]
        ops = [{"tipo": "operador", "arquivo": "a", "linha": i, "coluna": 1} for i in range(10)]
        self.assertEqual(sum(s["tipo"] == "retorno" for s in qualidade.escolher(ret + ops, 6)), 3)
        self.assertEqual(len(qualidade.escolher(ret + ops[:1], 6)), 6)


class Producao(unittest.TestCase):
    def test_pasta_de_dependencia_teste_e_extensao_ficam_de_fora(self) -> None:
        self.assertTrue(qualidade.eh_producao("src/app.py"))
        self.assertFalse(qualidade.eh_producao("node_modules/lib/x.js"))
        self.assertFalse(qualidade.eh_producao("src/vendor/x.go"))
        self.assertFalse(qualidade.eh_producao("tests/test_app.py"))
        self.assertFalse(qualidade.eh_producao("README.md"))

    def test_arquivo_no_teto_de_tamanho_ainda_e_medido(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.py"
            p.write_bytes(b"x" * qualidade.TETO_BYTES)
            self.assertTrue(qualidade._cabe(p))
            p.write_bytes(b"x" * (qualidade.TETO_BYTES + 1))
            self.assertFalse(qualidade._cabe(p))


def morreu(pid: int) -> bool:
    """Processo que não existe mais ou virou zumbi (morto, esperando quem o colha)."""
    for _ in range(40):
        try:
            estado = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        except OSError:
            return True
        if estado == "Z":
            return True
        time.sleep(0.05)
    return False


class Rodar(unittest.TestCase):
    @unittest.skipUnless(Path("/proc/self/stat").exists(), "precisa de /proc")
    def test_tempo_esgotado_mata_o_grupo_inteiro(self) -> None:
        # Com `shell=True`, matar só o shell deixa a suíte órfã rodando por trás.
        with tempfile.TemporaryDirectory() as d:
            neto = (f"{sys.executable} -c \"import os, time; open('pid', 'w')"
                    ".write(str(os.getpid())); time.sleep(30)\"; true")
            estado, segundos, _ = qualidade.rodar(neto, Path(d), 3)
            self.assertEqual(estado, "tempo")
            self.assertLess(segundos, 15)
            pid = int((Path(d) / "pid").read_text())
            vivo = not morreu(pid)
            if vivo:
                os.kill(pid, 9)
            self.assertFalse(vivo, "o neto sobreviveu ao tempo esgotado")


class Repo(unittest.TestCase):
    """Repositório git de verdade: a base em `main`, o trabalho na árvore."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-qualidade-")
        self.raiz = Path(self._tmp.name).resolve()
        self.git("init", "-q", "-b", "main")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.raiz), "-c", "user.name=t",
                        "-c", "user.email=t@t", *args], check=True, capture_output=True)

    def escrever(self, rel: str, texto: str) -> None:
        p = self.raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(texto), encoding="utf-8")

    def commitar(self) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")


class CrapNoDiff(Repo):
    def test_so_a_funcao_tocada_e_medida(self) -> None:
        self.escrever("app.py", "def velha(x):\n    return x\n")
        self.commitar()
        self.escrever("app.py", "def velha(x):\n    return x\n\n\n"
                                "def nova(x):\n    return 1 if x else 2\n")
        r = qualidade.analisar_crap(self.raiz, "main", None, 10)
        self.assertEqual([f["funcao"] for f in r["funcoes"]], ["nova"])
        self.assertEqual(r["funcoes"][0]["veredicto"], "indeterminado")

    def test_com_cobertura_calcula_e_reprova(self) -> None:
        self.escrever("app.py", "x = 1\n")
        self.commitar()
        self.escrever("app.py", "x = 1\n\n\n" + PYTHON_COMPLEXO)
        self.escrever("coverage.json", json.dumps(
            {"files": {"app.py": {"executed_lines": [4, 5, 6], "missing_lines": list(range(7, 16))}}}))
        r = qualidade.analisar_crap(self.raiz, "main", None, 10)
        f = r["funcoes"][0]
        self.assertEqual((f["complexidade"], f["cobertura"]), (9, 25.0))
        self.assertEqual(f["veredicto"], "acima_do_limite")
        self.assertEqual(r["cobertura"]["formato"], "coverage.py json")

    def test_legado_acima_que_nao_piora_nao_reprova(self) -> None:
        self.escrever("app.py", "x = 1\n\n\n" + PYTHON_COMPLEXO)
        self.commitar()
        self.escrever("app.py", "x = 2\n\n\n" + PYTHON_COMPLEXO.replace("pass\n", "y = 0\n", 1))
        f = qualidade.analisar_crap(self.raiz, "main", None, 9)["funcoes"][0]
        self.assertEqual((f["veredicto"], f["cc_base"]), ("legado_acima", 9))

    def test_legado_que_melhora_abaixo_do_limite_e_ok(self) -> None:
        f = qualidade.Funcao("m.py", "f", 1, 10, 4, set())
        item = qualidade.avaliar_funcao(f, None, 10, cc_base=12)
        self.assertEqual(item["veredicto"], "indeterminado")
        cob = qualidade.Cobertura(Path("."))
        for n in range(1, 11):
            cob.somar("m.py", n, True)
        self.assertEqual(qualidade.avaliar_funcao(f, cob, 10, cc_base=12)["veredicto"], "ok")

    def test_legado_que_piora_reprova(self) -> None:
        self.escrever("app.py", "x = 1\n\n\n" + PYTHON_COMPLEXO)
        self.commitar()
        self.escrever("app.py", "x = 1\n\n\n" + PYTHON_COMPLEXO.replace(
            "        pass\n", "        y = 1 if x else 0\n", 1))
        f = qualidade.analisar_crap(self.raiz, "main", None, 9)["funcoes"][0]
        self.assertEqual((f["veredicto"], f["complexidade"], f["cc_base"]),
                         ("acima_do_limite", 10, 9))

    def test_arquivo_gerado_fica_de_fora(self) -> None:
        self.escrever(".gitattributes", "espelho/** linguist-generated=true\n")
        self.escrever("espelho/app.py", "x = 1\n")
        self.commitar()
        self.escrever("espelho/app.py", "def f(x):\n    return x\n")
        self.assertEqual(qualidade.analisar_crap(self.raiz, "main", None, 10)["funcoes"], [])

    def test_sem_base_e_erro(self) -> None:
        self.assertIn("erro", qualidade.analisar_crap(self.raiz, "nao-existe", None, 10))
        self.assertIn("erro", qualidade.analisar_duplicacao(self.raiz, "nao-existe", 0.8, 4))

    def test_js_tocado_e_medido_pelo_diff(self) -> None:
        velha = "function velha(x) {\n  return x;\n}\n"
        self.escrever("app.js", velha)
        self.commitar()
        self.escrever("app.js", velha + "\nfunction nova(x) {\n  return x ? 1 : 2;\n}\n")
        r = qualidade.analisar_crap(self.raiz, "main", None, 10)
        self.assertEqual([(f["funcao"], f["complexidade"]) for f in r["funcoes"]], [("nova", 2)])
        self.assertEqual(r["nao_analisados"], [])


class ArquivosDeProducao(Repo):
    def test_so_a_linguagem_pedida_e_so_producao(self) -> None:
        self.escrever(".gitattributes", "espelho/** linguist-generated=true\n")
        for rel in ("app.py", "web/app.js", "tests/test_app.py", "node_modules/x.py",
                    "espelho/app.py"):
            self.escrever(rel, "x = 1\n")
        self.commitar()
        self.assertEqual(qualidade.arquivos_de_producao(self.raiz, "python"), ["app.py"])
        self.assertEqual(qualidade.arquivos_de_producao(self.raiz, "js"), ["web/app.js"])


class DuplicacaoNoDiff(Repo):
    def test_funcao_nova_igual_a_uma_velha_e_achada(self) -> None:
        self.escrever("a.py", Duplicacao.MESMA_FORMA.split("\n\ndef beta")[0] + "\n")
        self.commitar()
        self.escrever("b.py", "def beta(itens):\n    mantidos = filtrar(itens, par)\n"
                              "    soma = somar(mantidos)\n    return mapear(mantidos, soma)\n")
        r = qualidade.analisar_duplicacao(self.raiz, "main", 0.8, 4)
        self.assertEqual(len(r["pares"]), 1)
        self.assertEqual(r["pares"][0]["nota"], 1.0)
        self.assertEqual(r["pares"][0]["outra"]["funcao"], "alfa")
        self.assertEqual(r["nao_analisados"], [])

    def test_funcao_curta_fica_fora_mesmo_longe_do_topo(self) -> None:
        curta = "def {}(xs):\n    ys = filtrar(xs, par)\n    return mapear(ys, dobro)\n"
        self.escrever("a.py", "X = 1\n\n\n" + curta.format("alfa"))
        self.commitar()
        self.escrever("b.py", "Y = 2\n\n\n" + curta.format("beta"))
        self.assertEqual(len(qualidade.analisar_duplicacao(self.raiz, "main", 0.8, 3)["pares"]), 1)
        self.assertEqual(qualidade.analisar_duplicacao(self.raiz, "main", 0.8, 4)["pares"], [])

    def test_so_o_arquivo_tocado_que_nao_compila_e_declarado(self) -> None:
        self.escrever("velho.py", "def (:\n")
        self.commitar()
        self.escrever("novo.py", "def (:\n")
        r = qualidade.analisar_duplicacao(self.raiz, "main", 0.8, 4)
        self.assertEqual([n["arquivo"] for n in r["nao_analisados"]], ["novo.py"])


class MutacaoNoDiff(Repo):
    CODIGO = '''\
        def classificar(idade):
            if idade >= 18:
                return "adulto"
            return "menor"
        '''

    def preparar(self, teste: str) -> dict:
        self.escrever("pessoa.py", "X = 1\n")
        self.commitar()
        self.escrever("pessoa.py", self.CODIGO)
        self.escrever("test_pessoa.py", teste)
        self.comando = f"{sys.executable} -m unittest -q test_pessoa"
        return qualidade.analisar_mutacao(self.raiz, "main", self.comando, 25, 60, 300)

    def test_suite_que_nao_confere_deixa_mutante_vivo(self) -> None:
        r = self.preparar('''\
            import unittest, pessoa
            class T(unittest.TestCase):
                def test_roda(self):
                    pessoa.classificar(30)
            ''')
        self.assertNotIn("erro", r)
        self.assertEqual(r["placar"]["sobreviventes"], 3)
        self.assertEqual({m["funcao"] for m in r["mutantes"]}, {"classificar"})

    def test_suite_que_confere_a_fronteira_mata_todos(self) -> None:
        r = self.preparar('''\
            import unittest, pessoa
            class T(unittest.TestCase):
                def test_fronteira(self):
                    self.assertEqual(pessoa.classificar(18), "adulto")
                    self.assertEqual(pessoa.classificar(17), "menor")
            ''')
        self.assertEqual((r["placar"]["mortos"], r["placar"]["sobreviventes"]), (3, 0))
        self.assertEqual(r["placar"]["pontuacao"], 1.0)
        self.assertEqual(r["comando"], self.comando)  # o --comando explícito vence a dedução
        self.assertEqual((self.raiz / "pessoa.py").read_text(),
                         textwrap.dedent(self.CODIGO))  # o original nunca é tocado

    def test_base_vermelha_nao_julga_mutante(self) -> None:
        r = self.preparar('''\
            import unittest
            class T(unittest.TestCase):
                def test_quebrado(self):
                    self.fail("vermelho")
            ''')
        self.assertIn("base vermelha", r["erro"])
        self.assertEqual(r["mutantes"], [])


class MontarWorktree(Repo):
    def test_diff_que_nao_aplica_para_antes_de_mutar(self) -> None:
        # Senão a mutação rodaria, calada, sobre o código do último commit.
        self.escrever("app.py", "X = 1\n")
        self.commitar()
        self.escrever("app.py", "X = 2\n")
        real = subprocess.run

        def apply_falha(cmd, *args, **kwargs):
            if isinstance(cmd, list) and "apply" in cmd:
                return subprocess.CompletedProcess(cmd, 1, "", "patch corrompido")
            return real(cmd, *args, **kwargs)

        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(qualidade.subprocess, "run", apply_falha):
            erro = qualidade.montar_worktree(self.raiz, Path(d) / "arvore")
        self.assertIn("não consegui aplicar o diff não-commitado: patch corrompido", erro)


class SuiteDeduzida(Repo):
    def pacote(self, dados) -> None:
        self.escrever("package.json", dados if isinstance(dados, str) else json.dumps(dados))

    def test_js_pela_dependencia_e_pelo_script(self) -> None:
        self.pacote({"devDependencies": {"vitest": "1"}})
        self.assertEqual(qualidade._comando_js(self.raiz), "npx vitest run")
        self.pacote({"dependencies": {"jest": "29"}})
        self.assertEqual(qualidade._comando_js(self.raiz), "npx jest --ci")
        self.pacote({"scripts": {"test": "node t.js"}})
        self.assertEqual(qualidade._comando_js(self.raiz), "npm test --silent")

    def test_js_sem_como_rodar_e_none(self) -> None:
        self.pacote({"scripts": {}})
        self.assertIsNone(qualidade._comando_js(self.raiz))
        self.pacote("{ quebrado")
        self.assertIsNone(qualidade._comando_js(self.raiz))

    def test_diff_misto_pede_comando(self) -> None:
        self.assertIsNone(qualidade.comando_da_suite(self.raiz, {"python", "go"}))
        self.assertEqual(qualidade.comando_da_suite(self.raiz, {"go"}), "go test ./...")


class Impressao(unittest.TestCase):
    def imprimir(self, funcao, r: dict) -> str:
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            funcao(r)
        return saida.getvalue()

    def test_mutacao_mostra_placar_e_sobrevivente(self) -> None:
        r = {"base": "main", "ponto": "abc", "comando": "pytest", "base_segundos": 1.2,
             "sitios": 4, "aviso": "x",
             "mutantes": [{"arquivo": "a.py", "linha": 3, "funcao": "f", "original": ">=",
                           "mutado": ">", "resultado": "sobreviveu"},
                          {"arquivo": "a.py", "linha": 5, "original": "+", "mutado": "-",
                           "resultado": "nao_executado", "motivo": "teto"}],
             "placar": qualidade.placar([{"resultado": "sobreviveu"},
                                         {"resultado": "nao_executado"}])}
        saida = self.imprimir(qualidade.imprimir_mutacao, r)
        self.assertIn("❌ a.py:3 f: `>=` → `>`", saida)
        self.assertIn("— teto", saida)
        self.assertIn("0 mortos, 1 sobreviventes, 1 não executados — pontuação 0%", saida)

    def test_mutacao_sem_mutante_nao_inventa_pontuacao(self) -> None:
        r = {"base": "main", "ponto": "abc", "comando": None, "sitios": 0, "mutantes": [],
             "placar": qualidade.placar([])}
        self.assertIn("pontuação —", self.imprimir(qualidade.imprimir_mutacao, r))

    def test_duplicacao_mostra_o_par(self) -> None:
        r = {"base": "main", "ponto": "abc", "tocadas": 1, "comparadas": 2, "min_linhas": 4,
             "limite": 0.8, "nao_analisados": [{"arquivo": "q.py", "motivo": "ilegível"}],
             "pares": [{"nota": 0.91, "tocada": {"arquivo": "a.py", "linha": 1, "funcao": "f"},
                        "outra": {"arquivo": "b.py", "linha": 9, "funcao": "g"}}]}
        saida = self.imprimir(qualidade.imprimir_duplicacao, r)
        self.assertIn("❌ 0.91  a.py:1 f  ≈  b.py:9 g", saida)
        self.assertIn("q.py: ilegível", saida)


class Cli(Repo):
    def rodar(self, *args: str) -> tuple[int, str]:
        saida = io.StringIO()
        antes, argv = os.getcwd(), sys.argv
        try:
            os.chdir(self.raiz)
            sys.argv = ["qualidade.py", *args]
            with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(io.StringIO()):
                codigo = qualidade.main()
        finally:
            os.chdir(antes)
            sys.argv = argv
        return codigo, saida.getvalue()

    def test_exit_1_quando_ha_achado_e_0_quando_nao(self) -> None:
        self.escrever("app.py", "x = 1\n")
        self.commitar()
        self.escrever("app.py", PYTHON_COMPLEXO)
        codigo, saida = self.rodar("crap", "--base", "main", "--limite", "9")
        self.assertEqual(codigo, 1)
        self.assertIn("❌", saida)
        codigo, _ = self.rodar("crap", "--base", "main", "--limite", "50", "--json")
        self.assertEqual(codigo, 0)
        codigo, saida = self.rodar("duplicacao", "--base", "main")
        self.assertEqual(codigo, 0)
        self.assertIn("nenhum par", saida)

    def test_opcao_sem_valor_no_fim_usa_o_padrao(self) -> None:
        self.escrever("app.py", "x = 1\n")
        self.commitar()
        self.escrever("app.py", PYTHON_COMPLEXO)
        codigo, saida = self.rodar("crap", "--base", "main", "--limite")
        self.assertEqual(codigo, 0)
        self.assertIn("limite 10", saida)

    def test_mutacao_sem_sitio_avisa_e_sai_0(self) -> None:
        self.escrever("app.py", "X = 1\n")
        self.commitar()
        self.escrever("app.py", "X = 2\n")
        codigo, saida = self.rodar("mutacao", "--base", "main", "--comando", "true")
        self.assertEqual(codigo, 0)
        self.assertIn("nada a mutar", saida)

    def test_subcomando_desconhecido_mostra_o_uso(self) -> None:
        codigo, saida = self.rodar("medir")
        self.assertEqual(codigo, 1)
        self.assertIn("qualidade.py crap", saida)


if __name__ == "__main__":
    unittest.main()
