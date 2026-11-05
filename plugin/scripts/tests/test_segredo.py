"""Testes do segredo na saída de ferramenta (ADR-0056).

Só stdlib. O `guardrail.py saida` recebe o que uma ferramenta devolveu e troca cada
segredo por uma marca, antes de o modelo ver. Quem troca o resultado é o mod
(`hooks/segredo.ts`, testado pelo kit do Claude Code); aqui fica a regra:

1. Precisão: os formatos de segredo viram marca; código, hash, UUID e referência a
   variável passam. O falso positivo esconde um valor; o falso negativo manda o segredo
   para fora.
2. Saída: o texto oculto, o aviso para o modelo e o modo (`aviso` deixa o texto como
   está), sempre exit 0.
3. Trajetória: o achado é gravado com o tipo e o comando, nunca com o valor.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from unittest import mock

from tests.test_guardrail import Sandbox, hook

import guardrail  # noqa: E402  (o caminho vem do test_guardrail)
import telemetria  # noqa: E402

# Os exemplos são montados na hora: o arquivo não carrega nada com cara de segredo, e o
# `check-agent-security.py` (que procura segredo versionado) segue limpo.
GH = "ghp_" + "a" * 36
AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
INICIO_CHAVE, FIM_CHAVE = "-----BEGIN " + "RSA PRIVATE KEY-----", "-----END " + "RSA PRIVATE KEY-----"
JWT = ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
       "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U")

# (texto, o valor que não pode sobrar, o tipo)
OCULTA = (
    (f"GITHUB_TOKEN={GH}", GH, "token GitHub"),
    ("github_pat_" + "B" * 30, "github_pat_" + "B" * 30, "token GitHub"),
    ("glpat-" + "c" * 20, "glpat-" + "c" * 20, "token GitLab"),
    (f"export AWS_ACCESS_KEY_ID={AWS}", AWS, "chave de acesso AWS"),
    ("ASIAABCDEFGHIJKLMNOP", "ASIAABCDEFGHIJKLMNOP", "chave de acesso AWS"),
    ("SLACK=xoxb-123456789012-abcdef", "xoxb-123456789012-abcdef", "token Slack"),
    ("STRIPE_KEY=sk_live_" + "1" * 24, "sk_live_" + "1" * 24, "chave Stripe"),
    ("rk_test_" + "Z" * 20, "rk_test_" + "Z" * 20, "chave Stripe"),
    ("sk-ant-api03-" + "x" * 30, "sk-ant-api03-" + "x" * 30, "chave de API de modelo"),
    ("OPENAI=sk-proj-" + "y" * 24, "sk-proj-" + "y" * 24, "chave de API de modelo"),
    ("AIza" + "D" * 35, "AIza" + "D" * 35, "chave de API Google"),
    (f'"access_token": "{JWT}"', JWT, "JWT"),
    ("DATABASE_URL=postgres://app:S3nh4Forte@prod-db.acme.com:5432/app", "S3nh4Forte",
     "senha em URL de conexão"),
    ("redis://default:abc123xyz@cache:6379", "abc123xyz", "senha em URL de conexão"),
    ("SECRET_KEY = 'django-insecure-abc123xyz789'", "django-insecure-abc123xyz789",
     "valor de variável secreta"),
    ("DB_PASSWORD=postgres123", "postgres123", "valor de variável secreta"),
    ("MY_API_KEY: abcdef0123456789", "abcdef0123456789", "valor de variável secreta"),
    ("client_secret: " + "'abcdefgh12345678'", "abcdefgh12345678", "valor de chave secreta"),
    ('{"password": "correct-horse-battery"}', "correct-horse-battery", "valor de chave secreta"),
)
PASSA = (
    'api_key = os.environ["API_KEY"]', "token = get_token()", "max_tokens=4096",
    "tokenizer = AutoTokenizer.from_pretrained('x')", "password: ${{ secrets.DB }}",
    "TOKEN=<seu-token-aqui>", "SECRET={{ vault_secret }}", 'password = "hunter2"',
    "commit 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
    "uuid 123e4567-e89b-12d3-a456-426614174000", "sha256:9f86d081884c7d659a2feaa0c55ad015",
    "postgres://localhost:5432/app", "https://example.com/a:b@c", "sk-learn", "ghp_curto",
    "AKIA-nao-e-chave", "Bearer ${TOKEN}", "export TOKEN_LIMIT=100", "secret_santa = True",
)


class Precisao(unittest.TestCase):
    def test_cada_formato_vira_marca_e_o_valor_some(self) -> None:
        for texto, valor, tipo in OCULTA:
            with self.subTest(texto):
                oculto, tipos = guardrail.ocultar_segredos(texto)
                self.assertNotIn(valor, oculto)
                self.assertIn(guardrail.MARCA_SEGREDO.format(tipo=tipo), oculto)
                self.assertEqual(tipos, [tipo])

    def test_codigo_hash_uuid_e_referencia_passam(self) -> None:
        for texto in PASSA:
            with self.subTest(texto):
                self.assertEqual(guardrail.ocultar_segredos(texto), (texto, []))

    def test_so_o_valor_sai_e_o_resto_da_linha_fica(self) -> None:
        oculto, _ = guardrail.ocultar_segredos("DATABASE_URL=postgres://app:S3nh4Forte@db:5432/app fim")
        self.assertEqual(oculto, "DATABASE_URL=postgres://app:«segredo ocultado pelo kairos-forge: "
                                 "senha em URL de conexão»@db:5432/app fim")

    def test_chave_privada_sai_inteira_ate_sem_o_fim(self) -> None:
        bloco = f"{INICIO_CHAVE}\nMIIEow\nabc\n{FIM_CHAVE}"
        oculto, tipos = guardrail.ocultar_segredos(f"antes\n{bloco}\ndepois")
        self.assertEqual(oculto, "antes\n«segredo ocultado pelo kairos-forge: chave privada»\ndepois")
        cortada, _ = guardrail.ocultar_segredos("x\n-----BEGIN " + "OPENSSH PRIVATE KEY-----\nAAAA\nBBBB")
        self.assertEqual(cortada, "x\n«segredo ocultado pelo kairos-forge: chave privada»")

    def test_varios_na_mesma_saida_e_nenhum_conta_duas_vezes(self) -> None:
        texto = f"GITHUB_TOKEN={GH}\nAWS={AWS}\nnada\nGH2={GH}"
        oculto, tipos = guardrail.ocultar_segredos(texto)
        self.assertEqual(tipos, ["chave de acesso AWS", "token GitHub", "token GitHub"])
        self.assertNotIn(GH, oculto)
        self.assertIn("nada", oculto)


class Saida(Sandbox):
    def saida(self, textos, comando: str = "env", ferramenta: str = "Bash") -> dict:
        codigo, out, _ = hook("saida", {"cwd": str(self.raiz), "tool_name": ferramenta,
                                        "tool_input": {"command": comando}, "textos": textos})
        self.assertEqual(codigo, 0)
        return json.loads(out)

    def eventos(self) -> list[dict]:
        pasta = self.raiz / ".agents" / "execucoes"
        return [json.loads(l) for p in sorted(pasta.glob("*.jsonl"))
                for l in p.read_text(encoding="utf-8").splitlines()] if pasta.is_dir() else []

    def test_sem_segredo_nada_acontece(self) -> None:
        self.assertEqual(self.saida({"stdout": "tudo certo", "stderr": ""}), {"achados": 0})
        self.assertEqual(self.saida("não é um objeto"), {"achados": 0})
        self.assertEqual(self.eventos(), [])

    def test_oculta_cada_campo_e_avisa(self) -> None:
        r = self.saida({"stdout": f"GITHUB_TOKEN={GH}\nfim", "stderr": "DB_PASSWORD=postgres123"})
        self.assertEqual(r["achados"], 2)
        self.assertTrue(r["ocultar"])
        self.assertEqual(r["textos"]["stdout"],
                         "GITHUB_TOKEN=«segredo ocultado pelo kairos-forge: token GitHub»\nfim")
        self.assertNotIn("postgres123", r["textos"]["stderr"])
        for trecho in ("a saída de `Bash` tinha 2 segredo(s)", "token GitHub (1)",
                       "valor de variável secreta (1)", "ocultados antes de chegar a você",
                       "ADR-0056", "Não tente recuperar o valor", "peça à pessoa",
                       "pode ter de ser trocado"):
            self.assertIn(trecho, r["aviso"])

    def test_na_trajetoria_o_achado_sem_o_valor(self) -> None:
        self.saida({"texto": f"chave {GH}"}, comando=f"curl -H 'Authorization: token {GH}' x",
                   ferramenta="mcp__vault__ler")
        [evento] = self.eventos()
        self.assertEqual((evento["tipo"], evento["classe"], evento["regra"], evento["quantos"],
                          evento["modo"]), ("segredo_na_saida", "saida", "token GitHub", 1, "bloqueio"))
        self.assertIn("«segredo ocultado pelo kairos-forge: token GitHub»", evento["alvo"])
        for arquivo in (self.raiz / ".agents").rglob("*"):
            if arquivo.is_file():
                self.assertNotIn(GH, arquivo.read_text(encoding="utf-8"))

    def test_mcp_sem_comando_grava_o_nome_da_ferramenta(self) -> None:
        codigo, out, _ = hook("saida", {"cwd": str(self.raiz), "tool_name": "mcp__vault__ler",
                                        "textos": {"texto": GH}})
        self.assertIn("`mcp__vault__ler`", json.loads(out)["aviso"])
        self.assertEqual(self.eventos()[0]["alvo"], "mcp__vault__ler")

    def test_modo_aviso_deixa_o_texto_e_avisa_diferente(self) -> None:
        (self.raiz / ".agents").mkdir()
        (self.raiz / ".agents" / "guardrails.json").write_text('{"modos": {"saida": "aviso"}}',
                                                               encoding="utf-8")
        r = self.saida({"stdout": f"GITHUB_TOKEN={GH}"})
        self.assertFalse(r["ocultar"])
        self.assertEqual(r["textos"], {"stdout": f"GITHUB_TOKEN={GH}"})
        self.assertIn("deixados como estão", r["aviso"])
        self.assertIn("Não copie o valor", r["aviso"])
        self.assertEqual(self.eventos()[0]["modo"], "aviso")

    def test_numa_subpasta_grava_na_raiz(self) -> None:
        (self.raiz / "infra").mkdir()
        hook("saida", {"cwd": str(self.raiz / "infra"), "tool_name": "Bash",
                       "tool_input": {"command": "env"}, "textos": {"stdout": GH}})
        self.assertEqual(len(self.eventos()), 1)

    def test_pelo_main_com_stdin_e_ilegivel_falha_aberto(self) -> None:
        for entrada, esperado in ((json.dumps({"cwd": str(self.raiz), "tool_name": "Bash",
                                               "textos": {"stdout": GH}}), "achados"),
                                  ("{ isto não é json", "")):
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(sys, "argv", ["guardrail.py", "saida"]), \
                    mock.patch.object(sys, "stdin", io.StringIO(entrada)), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(guardrail.main(), 0)
            self.assertIn(esperado, out.getvalue())
        self.assertEqual(out.getvalue(), "")              # sem JSON, o mod deixa passar
        self.assertIn("falhou e deixou passar", err.getvalue())


class OcultarArquivo(unittest.TestCase):
    """O modo CLI que os gatilhos de CI rodam no que vão publicar (ADR-0057)."""

    def rodar(self, *arquivos) -> tuple[int, str]:
        err = io.StringIO()
        with mock.patch.object(sys, "argv", ["guardrail.py", "ocultar", *map(str, arquivos)]), \
                contextlib.redirect_stderr(err):
            return guardrail.main(), err.getvalue()

    def test_troca_no_proprio_arquivo_e_diz_no_stderr(self) -> None:
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            parecer, limpo = Path(tmp) / "revisao.md", Path(tmp) / "limpo.md"
            parecer.write_text(f"achado: {GH}\nfim\n", encoding="utf-8")
            limpo.write_text("nada aqui\n", encoding="utf-8")
            codigo, err = self.rodar(parecer, limpo, Path(tmp) / "sumiu.md")
            self.assertEqual(codigo, 0)
            self.assertEqual(parecer.read_text(encoding="utf-8"),
                             "achado: «segredo ocultado pelo kairos-forge: token GitHub»\nfim\n")
            self.assertEqual(limpo.read_text(encoding="utf-8"), "nada aqui\n")
            self.assertIn("revisao.md: 1 segredo(s) ocultado(s) antes de publicar — token GitHub (1)", err)
            self.assertNotIn("limpo.md", err)
            self.assertIn("sumiu.md", err)

    def test_sem_arquivo_nada_a_fazer(self) -> None:
        self.assertEqual(self.rodar(), (0, ""))


class NoResumo(unittest.TestCase):
    def test_o_resumo_conta_as_saidas_com_segredo_por_tipo(self) -> None:
        eventos = [{"sessao": "s1", "tipo": "segredo_na_saida", "regra": "token GitHub"},
                   {"sessao": "s1", "tipo": "segredo_na_saida", "regra": "token GitHub, JWT"},
                   {"sessao": "s2", "tipo": "segredo_na_saida", "regra": "JWT"}]
        m = telemetria.metricas(telemetria.por_sessao(eventos))
        self.assertEqual(m["segredos_na_saida"], 3)
        self.assertEqual(m["segredos_por_tipo"], {"token GitHub": 2, "JWT": 2})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            telemetria.imprimir_resumo(m, 7)
        self.assertIn("  Segredos na saída:    3 — token GitHub (2), JWT (2)\n", out.getvalue())

    def test_sem_achado_a_linha_nao_aparece(self) -> None:
        m = telemetria.metricas(telemetria.por_sessao([]))
        self.assertEqual(telemetria.linha_de_segredos_do_resumo(m), "")


if __name__ == "__main__":
    unittest.main()
