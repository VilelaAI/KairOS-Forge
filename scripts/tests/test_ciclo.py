"""Testes do `ciclo.py` — os contratos de que um runner externo depende (ADR-0034).

Só stdlib. Cada teste roda num diretório temporário com `docs/specs/` e `.agents/ciclo/`
próprios, porque o `ciclo.py` trabalha relativo ao cwd — igual ao runner real.

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
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import ciclo  # noqa: E402

SPEC = """# SPEC-001 — Exemplo

## Requisitos rastreáveis

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| EX-01 | Exportar lista | P1 | WHEN clica THEN baixa CSV em ≤ 2 s | Pendente | — |
"""

VALIDACAO_OK = """# Validação — SPEC-001

**Veredicto:** aprovado

```kairos-validacao
{"spec": "SPEC-001", "veredicto": "aprovado", "bloqueios": 0, "verificado": ["EX-01 (npm test)"]}
```
"""


def rodar(*args: str) -> tuple[int, str, str]:
    """Chama o `main()` do ciclo.py como a CLI faria; devolve (exit, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    antigo = sys.argv
    sys.argv = ["ciclo.py", *args]
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                codigo = ciclo.main()
            except SystemExit as e:  # `resolver` usa sys.exit em erro
                codigo = 1 if e.code else 0
                if isinstance(e.code, str):
                    err.write(e.code)
    finally:
        sys.argv = antigo
    return int(codigo or 0), out.getvalue(), err.getvalue()


def estado(spec: str = "SPEC-001") -> dict:
    codigo, out, _ = rodar("estado", spec, "--json")
    assert codigo == 0, out
    return json.loads(out)


REVISAO_LIMPA = ('# Revisão\n\n**Veredicto:** aprovado\n\n```kairos-revisao\n'
                 '{"veredicto": "aprovado", "faixa": 1, "criticos": 0, '
                 '"examinado": ["x.py (Helena)"]}\n```\n')

# Um `gh` que responde o que o teste mandou e anota cada chamada. Shebang absoluto: o PATH
# do teste tem só a pasta dele, para o `gh` de verdade nunca ser chamado.
GH_FALSO = f"""#!{sys.executable}
import json, pathlib, sys
pasta = pathlib.Path(__file__).resolve().parent
cfg = json.loads((pasta / "gh.json").read_text(encoding="utf-8"))
with open(pasta / "chamadas.txt", "a", encoding="utf-8") as f:
    f.write(" ".join(sys.argv[1:]) + "\\n")
sys.stdout.write(cfg["saida"])
sys.stderr.write(cfg["erro"])
sys.exit(cfg["codigo"])
"""


class Sandbox(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kairos-forge-ciclo-")
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        Path("docs/specs/validacoes").mkdir(parents=True)
        Path("docs/specs/SPEC-001-exemplo.md").write_text(SPEC, encoding="utf-8")

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def sem_gh(self) -> Path:
        """O PATH passa a ser uma pasta vazia: nenhum `gh` alcançável."""
        pasta = Path(self._tmp.name) / "bin"
        pasta.mkdir(exist_ok=True)
        antigo = os.environ.get("PATH", "")
        self.addCleanup(os.environ.__setitem__, "PATH", antigo)
        os.environ["PATH"] = str(pasta)
        return pasta

    def gh_falso(self, saida: dict | str = "", erro: str = "", codigo: int = 0) -> Path:
        """Só um `gh` falso no PATH; devolve o arquivo onde ele anota as chamadas."""
        pasta = self.sem_gh()
        texto = saida if isinstance(saida, str) else json.dumps(saida)
        (pasta / "gh.json").write_text(json.dumps({"saida": texto, "erro": erro,
                                                   "codigo": codigo}), encoding="utf-8")
        gh = pasta / "gh"
        gh.write_text(GH_FALSO, encoding="utf-8")
        gh.chmod(0o755)
        return pasta / "chamadas.txt"


class RegistrarIdempotente(Sandbox):
    """Semântica at-least-once do runner: repetir `registrar` nunca avança dois estados."""

    def test_repetir_resultado_nao_avanca_duas_vezes(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        self.assertEqual(estado()["estado"], "construindo")
        self.assertEqual(rodar("registrar", "pronto", "SPEC-001")[0], 0)
        self.assertEqual(estado()["estado"], "validando")
        codigo, _, err = rodar("registrar", "pronto", "SPEC-001")  # o runner repete
        self.assertEqual(codigo, 1)
        self.assertIn("não é válido", err)
        self.assertEqual(estado()["estado"], "validando")
        self.assertEqual([h["resultado"] for h in estado()["historico"]], ["abrir", "pronto"])

    def test_repetir_em_terminal_e_recusado(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("registrar", "pronto", "SPEC-001")
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(VALIDACAO_OK, encoding="utf-8")
        rodar("registrar", "aprovado", "SPEC-001")
        Path("docs/specs/revisoes").mkdir()
        Path("docs/specs/revisoes/REVISAO-SPEC-001-2026-01-01.md").write_text(
            REVISAO_LIMPA, encoding="utf-8")
        rodar("registrar", "limpo", "SPEC-001")
        self.sem_gh()
        self.assertEqual(rodar("registrar", "pr_aberto", "SPEC-001", "--pr", "12")[0], 0)
        e = estado()
        self.assertTrue(e["terminal"])
        codigo, _, err = rodar("registrar", "pr_aberto", "SPEC-001", "--pr", "12")
        self.assertEqual(codigo, 1)
        self.assertIn("terminal", err)
        self.assertEqual(estado()["estado"], "encerrado")

    def test_registrar_sem_spec_usa_o_unico_ciclo_aberto(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        self.assertEqual(rodar("registrar", "pronto")[0], 0)
        self.assertEqual(estado()["estado"], "validando")

    def test_revisao_incompleta_nao_registra_limpo(self) -> None:
        # ADR-0046: revisor que não rodou não aprovou — o contrato recusa, o ciclo não fecha.
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("registrar", "pronto", "SPEC-001")
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(VALIDACAO_OK, encoding="utf-8")
        rodar("registrar", "aprovado", "SPEC-001")
        Path("docs/specs/revisoes").mkdir()
        Path("docs/specs/revisoes/REVISAO-SPEC-001-2026-01-01.md").write_text(
            '# Revisão\n\n```kairos-revisao\n{"veredicto": "aprovado", "faixa": 1, "criticos": 0, '
            '"examinado": ["x.py (Helena)"], "incompletos": ["Patrícia"]}\n```\n', encoding="utf-8")
        codigo, _, err = rodar("registrar", "limpo", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("incompleta", err)
        self.assertEqual(estado()["estado"], "revisando")

    def test_estado_com_spec_explicita_funciona_em_ciclo_encerrado(self) -> None:
        """Achado da POC: sem a SPEC, `estado` falha em ciclo fechado; com ela, responde."""
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("encerrar", "SPEC-001", "--motivo", "teste")
        self.assertTrue(estado()["terminal"])
        codigo, _, _ = rodar("estado", "--json")  # sem SPEC
        self.assertEqual(codigo, 1)


class DigestDaSpec(Sandbox):
    def test_status_e_verificacao_nao_contam(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        self.assertIs(estado()["spec_alterada"], False)
        p = Path("docs/specs/SPEC-001-exemplo.md")
        p.write_text(p.read_text(encoding="utf-8").replace(
            "| Pendente | — |", "| Concluído | verificado: npm test (01/01) |"), encoding="utf-8")
        self.assertIs(estado()["spec_alterada"], False)

    def test_criterio_alterado_recusa_verde_ate_reaprovar(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("registrar", "pronto", "SPEC-001")
        p = Path("docs/specs/SPEC-001-exemplo.md")
        p.write_text(p.read_text(encoding="utf-8").replace("≤ 2 s", "≤ 10 s"), encoding="utf-8")
        self.assertIs(estado()["spec_alterada"], True)
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(VALIDACAO_OK, encoding="utf-8")
        codigo, _, err = rodar("registrar", "aprovado", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("mudou depois da aprovação", err)
        self.assertEqual(rodar("reaprovar", "SPEC-001")[0], 0)
        self.assertIs(estado()["spec_alterada"], False)
        self.assertEqual(rodar("registrar", "aprovado", "SPEC-001")[0], 0)
        self.assertEqual(estado()["estado"], "revisando")

    def test_rodada_que_falha_nao_lava_a_spec_alterada(self) -> None:
        # Só a aprovação sela: um `bloqueado` no meio não pode virar o novo contrato.
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("registrar", "pronto", "SPEC-001")
        p = Path("docs/specs/SPEC-001-exemplo.md")
        p.write_text(p.read_text(encoding="utf-8").replace("≤ 2 s", "≤ 10 s"), encoding="utf-8")
        relatorio = Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md")
        relatorio.write_text("# Validação\n\n**Veredicto:** bloqueado\n", encoding="utf-8")
        self.assertEqual(rodar("registrar", "bloqueado", "SPEC-001")[0], 0)
        self.assertEqual(rodar("registrar", "pronto", "SPEC-001")[0], 0)
        self.assertIs(estado()["spec_alterada"], True)
        relatorio.write_text(VALIDACAO_OK, encoding="utf-8")
        codigo, _, err = rodar("registrar", "aprovado", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("mudou depois da aprovação", err)

    def test_reaprovar_antes_da_aprovacao_e_recusado(self) -> None:
        """Achado da POC: selar em `enquadrando`/`desenhando` sela um digest que não é contrato."""
        rodar("abrir", "SPEC-001")  # sem --spec-aprovada → enquadrando, sem selo
        self.assertIsNone(estado()["spec_alterada"])
        codigo, _, err = rodar("reaprovar", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("ainda não foi aprovada", err)
        self.assertNotIn("reaprovar", [h["resultado"] for h in estado()["historico"]])

    def test_sem_spec_no_disco_digest_e_null(self) -> None:
        rodar("abrir", "SPEC-999", "--spec-aprovada")
        self.assertIsNone(estado("SPEC-999")["spec_alterada"])


class RelatorioComBlocoInvalido(Sandbox):
    """A prosa é o formato antigo, sem bloco — não a saída de emergência de um bloco que
    o parser recusou. Senão o "limpo sem lista do que foi olhado" (ADR-0032) passa pela
    linha `**Veredicto:**`."""

    def validando_com(self, relatorio: str) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("registrar", "pronto", "SPEC-001")
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(
            relatorio, encoding="utf-8")

    def test_sem_cobertura_nao_aprova(self) -> None:
        self.validando_com(
            "# Validação\n\n**Veredicto:** aprovado\n\n```kairos-validacao\n"
            '{"spec": "SPEC-001", "veredicto": "aprovado", "bloqueios": 0, "verificado": []}\n```\n')
        codigo, _, err = rodar("registrar", "aprovado", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("sem_cobertura", err)
        self.assertEqual(estado()["estado"], "validando")

    def test_bloco_malformado_nao_aprova(self) -> None:
        self.validando_com(
            "# Validação\n\n**Veredicto:** aprovado\n\n```kairos-validacao\n{veredicto: aprovado\n```\n")
        codigo, _, err = rodar("registrar", "aprovado", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("json_invalido", err)
        self.assertEqual(estado()["estado"], "validando")

    def test_prosa_sem_bloco_continua_aceita(self) -> None:
        self.validando_com("# Validação\n\n**Veredicto:** aprovado\n")
        self.assertEqual(rodar("registrar", "aprovado", "SPEC-001")[0], 0)
        self.assertEqual(estado()["estado"], "revisando")
        self.assertEqual(estado()["historico"][-1]["fonte"], "prosa")

    def test_prosa_avisa_que_a_rodada_queima_ficha(self) -> None:
        self.validando_com("# Validação\n\n**Veredicto:** bloqueado\n")
        _, _, err = rodar("registrar", "bloqueado", "SPEC-001")
        self.assertEqual(estado()["estado"], "corrigindo_validacao")
        self.assertIn("queima ficha", err)

    def test_ciclo_escalado_nao_fala_mais_em_ficha(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada", "--orcamento-validar", "1")
        rodar("registrar", "pronto", "SPEC-001")
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(
            "# Validação\n\n**Veredicto:** bloqueado\n", encoding="utf-8")
        rodar("registrar", "bloqueado", "SPEC-001")
        rodar("registrar", "pronto", "SPEC-001")
        _, _, err = rodar("registrar", "bloqueado", "SPEC-001")
        self.assertEqual(estado()["estado"], "escalado")
        self.assertNotIn("queima ficha", err)

    def test_resultado_negativo_com_bloco_invalido_e_aceito(self) -> None:
        # Registrar o negativo é o lado conservador: a rodada só queima ficha.
        self.validando_com(
            "# Validação\n\n**Veredicto:** bloqueado\n\n```kairos-validacao\n{quebrado\n```\n")
        codigo, _, err = rodar("registrar", "bloqueado", "SPEC-001")
        self.assertEqual(codigo, 0)
        self.assertEqual(estado()["estado"], "corrigindo_validacao")
        self.assertEqual(estado()["historico"][-1]["fonte"], "invalido")
        self.assertIn("json_invalido", err)


class AtacarPremissa(Sandbox):
    """ADR-0045, do ub-mode: duas correções que falham no mesmo gate sem progresso
    partem da mesma premissa — a terceira só começa com ela escrita."""

    PREMISSA = "o cache é a fonte da verdade do saldo"

    def relatorio(self, bloqueios: int) -> None:
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(
            "# Validação\n\n**Veredicto:** bloqueado\n\n```kairos-validacao\n"
            f'{{"spec": "SPEC-001", "veredicto": "bloqueado", "bloqueios": {bloqueios}, '
            '"verificado": ["EX-01 (npm test)"]}\n```\n', encoding="utf-8")

    def validando(self, orcamento: str = "5") -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada", "--orcamento-validar", orcamento)
        rodar("registrar", "pronto", "SPEC-001")
        self.relatorio(2)

    def falhar_e_corrigir(self, vezes: int) -> None:
        for _ in range(vezes):
            self.assertEqual(rodar("registrar", "bloqueado", "SPEC-001")[0], 0)
            self.assertEqual(rodar("registrar", "pronto", "SPEC-001")[0], 0)

    def test_terceira_falha_seguida_exige_a_premissa(self) -> None:
        self.validando()
        self.falhar_e_corrigir(2)
        rodar("registrar", "bloqueado", "SPEC-001")
        e = estado()
        self.assertEqual(e["estado"], "atacando_premissa_validacao")
        self.assertEqual(e["resultados_validos"], ["premissa_escrita"])
        self.assertFalse(e["aguardando_humano"])
        self.assertEqual(e["contrato"], "1.4")
        self.assertIn("próxima correção", e["proximo_passo"])   # com orçamento, corrige
        self.assertNotIn("escalação", e["proximo_passo"])

    def test_premissa_precisa_ser_uma_frase(self) -> None:
        self.validando()
        self.falhar_e_corrigir(2)
        rodar("registrar", "bloqueado", "SPEC-001")
        codigo, _, err = rodar("registrar", "premissa_escrita", "SPEC-001", "--nota", "cache")
        self.assertEqual(codigo, 1)
        self.assertIn("uma frase", err)
        self.assertEqual(estado()["estado"], "atacando_premissa_validacao")
        self.assertEqual(rodar("registrar", "premissa_escrita", "SPEC-001",
                               "--nota", self.PREMISSA)[0], 0)
        self.assertEqual(estado()["estado"], "corrigindo_validacao")
        self.assertEqual(estado()["historico"][-1]["nota"], self.PREMISSA)

    def test_mesma_premissa_na_mesma_sequencia_e_recusada(self) -> None:
        self.validando()
        self.falhar_e_corrigir(2)
        rodar("registrar", "bloqueado", "SPEC-001")
        rodar("registrar", "premissa_escrita", "SPEC-001", "--nota", self.PREMISSA)
        rodar("registrar", "pronto", "SPEC-001")
        rodar("registrar", "bloqueado", "SPEC-001")  # a correção nova também falhou
        self.assertEqual(estado()["estado"], "atacando_premissa_validacao")
        codigo, _, err = rodar("registrar", "premissa_escrita", "SPEC-001",
                               "--nota", "  O CACHE é a fonte da verdade   do saldo ")
        self.assertEqual(codigo, 1)
        self.assertIn("já foi atacada", err)

    def test_progresso_zera_a_sequencia(self) -> None:
        self.validando()
        self.falhar_e_corrigir(2)
        self.relatorio(1)  # baixou de 2 para 1: está convergindo
        rodar("registrar", "bloqueado", "SPEC-001")
        self.assertEqual(estado()["estado"], "corrigindo_validacao")

    def test_piorar_e_voltar_um_pouco_nao_e_progresso(self) -> None:
        # A marca é a melhor contagem da sequência, não a última: 2 → 4 → 3 não convergiu.
        self.validando()
        self.falhar_e_corrigir(1)
        self.relatorio(4)
        self.falhar_e_corrigir(1)
        self.relatorio(3)
        rodar("registrar", "bloqueado", "SPEC-001")
        self.assertEqual(estado()["estado"], "atacando_premissa_validacao")

    def test_orcamento_padrao_ataca_a_premissa_e_a_leva_na_escalacao(self) -> None:
        # O /entregar e a ponte Hermes abrem com o orçamento padrão (2): a terceira falha
        # seguida é a que esgota o orçamento. Ela passa pelo ataque à premissa, sem ficha a
        # mais, e a premissa escrita vai para a escalação em vez de abrir uma terceira correção.
        self.validando("2")
        self.falhar_e_corrigir(2)
        rodar("registrar", "bloqueado", "SPEC-001")
        e = estado()
        self.assertEqual(e["estado"], "atacando_premissa_validacao")
        self.assertEqual(e["resultados_validos"], ["premissa_escrita"])
        self.assertIn("escalação", e["proximo_passo"])
        self.assertEqual(e["rodadas"]["validar"], 2)
        self.assertEqual(rodar("registrar", "premissa_escrita", "SPEC-001",
                               "--nota", self.PREMISSA)[0], 0)
        e = estado()
        self.assertEqual(e["estado"], "escalado")
        self.assertIn("orçamento de validar esgotado", e["motivo_escalacao"])
        self.assertIn(self.PREMISSA, e["motivo_escalacao"])
        self.assertIn("premissa", e["proximo_passo"])
        self.assertEqual(e["rodadas"]["validar"], 2)

    def test_com_orcamento_maior_a_escalacao_tambem_leva_a_premissa(self) -> None:
        # Orçamento 4: a terceira e a quarta falhas atacam uma premissa cada (ADR-0045) e pagam
        # uma correção cada; a quinta esgota o orçamento. A escalação leva a última premissa
        # atacada, como no orçamento padrão.
        segunda = "o arredondamento acontece antes da soma das parcelas"
        self.validando("4")
        self.falhar_e_corrigir(2)
        for premissa in (self.PREMISSA, segunda):
            rodar("registrar", "bloqueado", "SPEC-001")
            self.assertEqual(estado()["estado"], "atacando_premissa_validacao")
            self.assertEqual(rodar("registrar", "premissa_escrita", "SPEC-001", "--nota",
                                   premissa)[0], 0)
            self.assertEqual(rodar("registrar", "pronto", "SPEC-001")[0], 0)
        rodar("registrar", "bloqueado", "SPEC-001")
        e = estado()
        self.assertEqual(e["estado"], "escalado")
        self.assertIn("orçamento de validar esgotado", e["motivo_escalacao"])
        self.assertIn(segunda, e["motivo_escalacao"])

    def test_premissa_da_escalacao_tambem_precisa_ser_uma_frase(self) -> None:
        self.validando("2")
        self.falhar_e_corrigir(2)
        rodar("registrar", "bloqueado", "SPEC-001")
        codigo, _, err = rodar("registrar", "premissa_escrita", "SPEC-001", "--nota", "cache")
        self.assertEqual(codigo, 1)
        self.assertIn("uma frase", err)
        self.assertEqual(estado()["estado"], "atacando_premissa_validacao")

    def test_resultado_errado_no_ataque_da_escalacao_repete_o_passo_certo(self) -> None:
        # A recusa de um resultado inválido repete o próximo passo. No ataque que antecede a
        # escalação, o passo certo é o que diz que não há terceira correção — não o genérico,
        # que promete "a próxima correção".
        self.validando("2")
        self.falhar_e_corrigir(2)
        rodar("registrar", "bloqueado", "SPEC-001")
        codigo, _, err = rodar("registrar", "pronto", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("não há terceira correção", err)
        self.assertNotIn("A próxima correção parte de outra premissa", err)

    def test_orcamento_esgotado_sem_tres_falhas_seguidas_escala_direto(self) -> None:
        # Gate verde zera a sequência, não as fichas: a falha que esgota o orçamento depois
        # de um verde não é a terceira seguida e escala sem pedir premissa.
        self.validando("2")
        self.falhar_e_corrigir(1)
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(
            VALIDACAO_OK, encoding="utf-8")
        self.assertEqual(rodar("registrar", "aprovado", "SPEC-001")[0], 0)
        self.assertEqual(rodar("registrar", "critico", "SPEC-001")[0], 0)
        self.assertEqual(rodar("registrar", "pronto", "SPEC-001")[0], 0)  # reabre a validação
        self.relatorio(2)
        self.falhar_e_corrigir(1)
        rodar("registrar", "bloqueado", "SPEC-001")
        self.assertEqual(estado()["estado"], "escalado")

    def test_orcamento_um_escala_na_segunda_falha_sem_premissa(self) -> None:
        self.validando("1")
        self.falhar_e_corrigir(1)
        rodar("registrar", "bloqueado", "SPEC-001")
        self.assertEqual(estado()["estado"], "escalado")

    def test_premissa_ja_atacada_na_sequencia_escala_direto(self) -> None:
        # Com orçamento 3 a terceira falha ainda paga a correção: a premissa abre a correção,
        # e a quarta falha, que esgota o orçamento, escala sem pedir outra.
        self.validando("3")
        self.falhar_e_corrigir(2)
        rodar("registrar", "bloqueado", "SPEC-001")
        self.assertEqual(rodar("registrar", "premissa_escrita", "SPEC-001",
                               "--nota", self.PREMISSA)[0], 0)
        self.assertEqual(estado()["estado"], "corrigindo_validacao")
        rodar("registrar", "pronto", "SPEC-001")
        rodar("registrar", "bloqueado", "SPEC-001")
        self.assertEqual(estado()["estado"], "escalado")

    def test_contrato_publica_os_estados_novos(self) -> None:
        codigo, out, _ = rodar("contrato")
        c = json.loads(out)
        self.assertEqual(c["versao"], "1.4")
        # 1.4: o destino da premissa é calculado — a correção do mesmo gate, ou `escalado`
        # quando o orçamento acabou na terceira falha seguida.
        self.assertEqual(c["transicoes"]["atacando_premissa_revisao"],
                         {"premissa_escrita": None})
        self.assertIn("atacando_premissa_revisao", c["estados"])


class FaltaDeProva(Sandbox):
    """ADR-0048: validação bloqueada só por falta de prova vai para `provando`."""

    def bloqueado(self, sem_evidencia: int) -> None:
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(
            "# Validação\n\n```kairos-validacao\n"
            f'{{"veredicto": "bloqueado", "bloqueios": 2, "sem_evidencia": {sem_evidencia}, '
            '"verificado": ["EX-01 (npm test)"]}\n```\n', encoding="utf-8")
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("registrar", "pronto", "SPEC-001")
        self.assertEqual(rodar("registrar", "bloqueado", "SPEC-001")[0], 0)

    def test_so_falta_de_prova_vai_para_provando_e_volta_a_validar(self) -> None:
        self.bloqueado(sem_evidencia=2)
        e = estado()
        self.assertEqual(e["estado"], "provando")
        self.assertIn("ANTES de mexer no código", e["proximo_passo"])
        self.assertEqual(e["resultados_validos"], ["pronto"])
        self.assertEqual(rodar("registrar", "pronto", "SPEC-001")[0], 0)
        self.assertEqual(estado()["estado"], "validando")

    def test_falha_mostrada_vai_para_a_correcao(self) -> None:
        self.bloqueado(sem_evidencia=1)
        self.assertEqual(estado()["estado"], "corrigindo_validacao")

    def test_falta_de_prova_queima_rodada_como_qualquer_bloqueio(self) -> None:
        self.bloqueado(sem_evidencia=2)
        self.assertEqual(estado()["rodadas"]["validar"], 1)


class ReRevisao(Sandbox):
    """ADR-0048: cada 🔴 de uma revisão bloqueada fica pendente até ser resolvido."""

    def revisao(self, **campos) -> None:
        bloco = {"veredicto": "aprovado", "faixa": 1, "criticos": 0,
                 "examinado": ["api.py (Helena)"], **campos}
        Path("docs/specs/revisoes").mkdir(exist_ok=True)
        Path("docs/specs/revisoes/REVISAO-SPEC-001-2026-01-01.md").write_text(
            f"# Revisão\n\n```kairos-revisao\n{json.dumps(bloco)}\n```\n", encoding="utf-8")

    def revisando(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada", "--orcamento-revisar", "5")
        rodar("registrar", "pronto", "SPEC-001")
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(
            VALIDACAO_OK, encoding="utf-8")
        self.assertEqual(rodar("registrar", "aprovado", "SPEC-001")[0], 0)

    def critico_e_volta(self, achados: list[str], **campos) -> None:
        self.revisao(veredicto="bloqueado", criticos=len(achados), achados=achados, **campos)
        self.assertEqual(rodar("registrar", "critico", "SPEC-001")[0], 0)
        rodar("registrar", "pronto", "SPEC-001")         # corrigindo_revisao → validando
        self.assertEqual(rodar("registrar", "aprovado", "SPEC-001")[0], 0)

    def test_critico_fica_pendente_no_estado(self) -> None:
        self.revisando()
        self.critico_e_volta(["R1", "R2"])
        self.assertEqual(estado()["pendentes_revisao"], ["R1", "R2"])

    def test_limpo_sem_prestar_contas_e_recusado(self) -> None:
        self.revisando()
        self.critico_e_volta(["R1", "R2"])
        self.revisao()
        codigo, _, err = rodar("registrar", "limpo", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("R1", err)
        self.assertEqual(estado()["estado"], "revisando")

    def test_limpo_com_um_pendente_esquecido_e_recusado(self) -> None:
        self.revisando()
        self.critico_e_volta(["R1", "R2"])
        self.revisao(anteriores={"R1": "resolvido"})
        codigo, _, err = rodar("registrar", "limpo", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("R2", err)

    def test_limpo_prestando_contas_fecha_e_zera_os_pendentes(self) -> None:
        self.revisando()
        self.critico_e_volta(["R1", "R2"])
        self.revisao(anteriores={"R1": "resolvido", "R2": "resolvido"})
        self.assertEqual(rodar("registrar", "limpo", "SPEC-001")[0], 0)
        e = estado()
        self.assertEqual(e["estado"], "pronto_para_pr")
        self.assertEqual(e["pendentes_revisao"], [])

    def test_segunda_rodada_bloqueada_carrega_o_que_nao_foi_resolvido(self) -> None:
        self.revisando()
        self.critico_e_volta(["R1", "R2"])
        self.critico_e_volta(["R1", "R3"], anteriores={"R1": "nao_resolvido", "R2": "resolvido"})
        self.assertEqual(estado()["pendentes_revisao"], ["R1", "R3"])

    def test_limpo_em_prosa_com_pendente_e_recusado(self) -> None:
        self.revisando()
        self.critico_e_volta(["R1"])
        Path("docs/specs/revisoes/REVISAO-SPEC-001-2026-01-01.md").write_text(
            "# Revisão\n\n**Veredicto:** aprovado\n", encoding="utf-8")
        codigo, _, err = rodar("registrar", "limpo", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("R1", err)

    def test_estado_mostra_os_pendentes_so_quando_ha(self) -> None:
        self.revisando()
        self.assertNotIn("pendentes da revisão anterior", rodar("estado", "SPEC-001")[1])
        self.critico_e_volta(["R1"])
        self.assertIn("pendentes da revisão anterior: R1", rodar("estado", "SPEC-001")[1])

    def test_revisao_sem_ids_nao_cria_pendencia(self) -> None:
        self.revisando()
        self.revisao(veredicto="bloqueado", criticos=1)
        rodar("registrar", "critico", "SPEC-001")
        self.assertEqual(estado()["pendentes_revisao"], [])

    def test_contrato_publica_o_estado_e_o_campo(self) -> None:
        c = json.loads(rodar("contrato")[1])
        self.assertEqual(c["transicoes"]["provando"], {"pronto": "validando"})
        self.assertIn("pendentes_revisao", c["campos"])

    def test_revisao_incompleta_nao_conta_como_progresso(self) -> None:
        # ADR-0046: com um revisor a menos a contagem de 🔴 não está completa. Cair de 3 para
        # 1 porque a Helena não rodou não é convergência e não devolve a ficha.
        self.revisando()
        self.critico_e_volta(["R1", "R2", "R3"])
        self.assertEqual(estado()["rodadas"]["revisar"], 1)
        self.revisao(veredicto="bloqueado", criticos=1, achados=["R4"], incompletos=["Helena"],
                     anteriores={"R1": "resolvido", "R2": "resolvido", "R3": "resolvido"})
        _, _, err = rodar("registrar", "critico", "SPEC-001")
        e = estado()
        self.assertEqual(e["estado"], "corrigindo_revisao")
        self.assertEqual(e["rodadas"]["revisar"], 2)
        self.assertEqual(e["marca"]["revisar"], 3)
        self.assertNotIn("bloqueios", e["historico"][-1])
        self.assertIn("incompleta", err)

    def test_revisao_incompleta_sem_critico_e_bloqueio_valido(self) -> None:
        # Sem 🔴 dos revisores que rodaram, o bloco que o ADR-0046 pede (`bloqueado` com
        # `incompletos`) era recusado, e o único bloco aceito era apagar o `incompletos`.
        self.revisando()
        self.revisao(veredicto="bloqueado", criticos=0, incompletos=["Patrícia"])
        codigo, _, err = rodar("registrar", "limpo", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("BLOQUEADO", err)
        self.assertEqual(rodar("registrar", "critico", "SPEC-001")[0], 0)
        h = estado()["historico"][-1]
        self.assertEqual(h["fonte"], "contrato")
        self.assertNotIn("bloqueios", h)


class Faixa3(Sandbox):
    """ADR-0031: faixa 3 (difícil de reverter) não fecha por evidência. O /entregar escala
    em vez de abrir o PR; o ciclo recusa o `limpo` que o levaria ao PR."""

    def revisando_com(self, faixa: int) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("registrar", "pronto", "SPEC-001")
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(
            VALIDACAO_OK, encoding="utf-8")
        self.assertEqual(rodar("registrar", "aprovado", "SPEC-001")[0], 0)
        Path("docs/specs/revisoes").mkdir()
        bloco = {"veredicto": "aprovado", "faixa": faixa, "criticos": 0,
                 "examinado": ["migrations/0042_saldo.sql (Carlos)", "api.py (Helena)"]}
        Path("docs/specs/revisoes/REVISAO-SPEC-001-2026-01-01.md").write_text(
            f"# Revisão\n\n```kairos-revisao\n{json.dumps(bloco)}\n```\n", encoding="utf-8")

    def test_revisao_limpa_na_faixa_3_nao_vai_para_o_pr(self) -> None:
        self.revisando_com(3)
        codigo, _, err = rodar("registrar", "limpo", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("faixa 3", err)
        self.assertIn("ciclo.py escalar", err)
        self.assertEqual(estado()["estado"], "revisando")
        self.assertEqual(rodar("escalar", "SPEC-001", "--motivo",
                               "faixa 3: a migration apaga a coluna saldo")[0], 0)
        self.assertEqual(estado()["estado"], "escalado")

    def test_faixa_2_segue_para_o_pr(self) -> None:
        self.revisando_com(2)
        self.assertEqual(rodar("registrar", "limpo", "SPEC-001")[0], 0)
        self.assertEqual(estado()["estado"], "pronto_para_pr")

    def test_proximo_passo_da_revisao_avisa_da_faixa_3(self) -> None:
        self.revisando_com(1)
        self.assertIn("faixa 3", estado()["proximo_passo"])


class PrAberto(Sandbox):
    """`registrar pr_aberto` encerra o arco: precisa dizer qual PR, e o PR precisa existir."""

    def pronto_para_pr(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        rodar("registrar", "pronto", "SPEC-001")
        Path("docs/specs/validacoes/VALIDACAO-SPEC-001-2026-01-01.md").write_text(
            VALIDACAO_OK, encoding="utf-8")
        rodar("registrar", "aprovado", "SPEC-001")
        Path("docs/specs/revisoes").mkdir()
        Path("docs/specs/revisoes/REVISAO-SPEC-001-2026-01-01.md").write_text(
            REVISAO_LIMPA, encoding="utf-8")
        rodar("registrar", "limpo", "SPEC-001")
        self.assertEqual(estado()["estado"], "pronto_para_pr")

    def test_sem_referencia_nao_encerra(self) -> None:
        self.pronto_para_pr()
        self.sem_gh()
        codigo, _, err = rodar("registrar", "pr_aberto", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("--pr", err)
        self.assertEqual(estado()["estado"], "pronto_para_pr")

    def test_referencia_que_nao_e_de_pr_e_recusada(self) -> None:
        self.pronto_para_pr()
        self.sem_gh()
        for ref in ("amanhã", "https://github.com/o/r/issues/3", "12a"):
            codigo, _, err = rodar("registrar", "pr_aberto", "SPEC-001", "--pr", ref)
            self.assertEqual(codigo, 1, ref)
            self.assertIn("não é referência de PR", err, ref)
        self.assertEqual(estado()["estado"], "pronto_para_pr")

    def test_pr_aberto_conferido_pelo_gh_encerra(self) -> None:
        self.pronto_para_pr()
        chamadas = self.gh_falso({"number": 12, "state": "OPEN", "headRefName": "feat/x",
                                  "url": "https://github.com/o/r/pull/12"})
        self.assertEqual(rodar("registrar", "pr_aberto", "SPEC-001", "--pr", "#12")[0], 0)
        e = estado()
        self.assertEqual(e["estado"], "encerrado")
        h = e["historico"][-1]
        self.assertEqual((h["resultado"], h["pr"], h["pr_conferido"], h["pr_estado"]),
                         ("pr_aberto", "12", True, "aberto"))
        self.assertEqual(h["pr_url"], "https://github.com/o/r/pull/12")
        self.assertIn("pr view 12 --json", chamadas.read_text(encoding="utf-8"))

    def test_pr_mesclado_tambem_vale_e_a_url_vai_como_veio(self) -> None:
        self.pronto_para_pr()
        url = "https://github.com/o/r/pull/7"
        chamadas = self.gh_falso({"number": 7, "state": "MERGED", "url": url,
                                  "headRefName": "feat/x"})
        self.assertEqual(rodar("registrar", "pr_aberto", "SPEC-001", "--pr", url)[0], 0)
        h = estado()["historico"][-1]
        self.assertEqual((h["pr"], h["pr_estado"]), (url, "mesclado"))
        self.assertIn(f"pr view {url} --json", chamadas.read_text(encoding="utf-8"))

    def test_pr_fechado_sem_merge_e_recusado(self) -> None:
        self.pronto_para_pr()
        self.gh_falso({"number": 12, "state": "CLOSED", "url": "https://github.com/o/r/pull/12",
                       "headRefName": "feat/x"})
        codigo, _, err = rodar("registrar", "pr_aberto", "SPEC-001", "--pr", "12")
        self.assertEqual(codigo, 1)
        self.assertIn("fechado", err)
        self.assertEqual(estado()["estado"], "pronto_para_pr")

    def test_pr_que_o_gh_diz_nao_existir_e_recusado(self) -> None:
        self.pronto_para_pr()
        self.gh_falso(erro="GraphQL: Could not resolve to a PullRequest with the number of "
                           "999. (repository.pullRequest)\n", codigo=1)
        codigo, _, err = rodar("registrar", "pr_aberto", "SPEC-001", "--pr", "999")
        self.assertEqual(codigo, 1)
        self.assertIn("não existe", err)
        self.assertEqual(estado()["estado"], "pronto_para_pr")

    def test_sem_gh_encerra_e_registra_que_nao_conferiu(self) -> None:
        self.pronto_para_pr()
        self.sem_gh()
        codigo, _, err = rodar("registrar", "pr_aberto", "SPEC-001", "--pr", "12")
        self.assertEqual(codigo, 0)
        h = estado()["historico"][-1]
        self.assertEqual((h["pr"], h["pr_conferido"]), ("12", False))
        self.assertIn("gh", h["pr_nao_conferido"])
        self.assertIn("não conferido", err)

    def test_gh_sem_rede_nao_bloqueia(self) -> None:
        self.pronto_para_pr()
        self.gh_falso(erro="error connecting to api.github.com\n", codigo=1)
        self.assertEqual(rodar("registrar", "pr_aberto", "SPEC-001", "--pr", "12")[0], 0)
        h = estado()["historico"][-1]
        self.assertFalse(h["pr_conferido"])
        self.assertIn("api.github.com", h["pr_nao_conferido"])

    def test_gh_que_nao_executa_nao_bloqueia(self) -> None:
        self.pronto_para_pr()
        pasta = self.sem_gh()
        (pasta / "gh").write_text("sem permissão de execução\n", encoding="utf-8")
        self.assertEqual(rodar("registrar", "pr_aberto", "SPEC-001", "--pr", "12")[0], 0)
        h = estado()["historico"][-1]
        self.assertFalse(h["pr_conferido"])
        self.assertIn("gh não respondeu", h["pr_nao_conferido"])

    def test_resposta_ilegivel_do_gh_nao_bloqueia(self) -> None:
        self.pronto_para_pr()
        self.gh_falso("isto não é json")
        self.assertEqual(rodar("registrar", "pr_aberto", "SPEC-001", "--pr", "12")[0], 0)
        h = estado()["historico"][-1]
        self.assertEqual((h["pr_conferido"], h["pr_nao_conferido"]),
                         (False, "resposta do gh ilegível"))

    def test_pr_de_outra_branch_encerra_com_aviso(self) -> None:
        for args in (["init", "-q", "."],
                     ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                      "--allow-empty", "-m", "base"],
                     ["checkout", "-q", "-b", "feat/spec-001"]):
            subprocess.run(["git", *args], check=True, capture_output=True)
        self.pronto_para_pr()
        self.gh_falso({"number": 3, "state": "OPEN", "url": "https://github.com/o/r/pull/3",
                       "headRefName": "feat/outra"})
        codigo, _, err = rodar("registrar", "pr_aberto", "SPEC-001", "--pr", "3")
        self.assertEqual(codigo, 0)
        self.assertIn("feat/outra", err)
        self.assertEqual(estado()["historico"][-1]["pr_branch"], "feat/outra")


class AjudaEOpcaoDesconhecida(Sandbox):
    """`ciclo.py abrir -h` abria um ciclo para a SPEC "-h"; ajuda e erro de digitação não abrem nada."""

    def ciclos(self) -> list[str]:
        pasta = Path(".agents/ciclo")
        return sorted(p.name for p in pasta.glob("*.json")) if pasta.is_dir() else []

    def test_ajuda_em_qualquer_posicao_mostra_o_uso_e_sai_zero(self) -> None:
        for args in (["-h"], ["--help"], ["abrir", "-h"], ["abrir", "SPEC-001", "--help"],
                     ["registrar", "-h"], ["estado", "--json", "-h"]):
            codigo, out, _ = rodar(*args)
            self.assertEqual(codigo, 0, args)
            self.assertIn("ciclo.py", out, args)
        self.assertEqual(self.ciclos(), [])

    def test_opcao_desconhecida_recusa_sem_abrir(self) -> None:
        codigo, _, err = rodar("abrir", "--spec-aprovad", "SPEC-001")
        self.assertEqual(codigo, 1)
        self.assertIn("opção desconhecida: --spec-aprovad", err)
        self.assertEqual(self.ciclos(), [])

    def test_so_opcoes_sem_comando_e_erro_e_nao_excecao(self) -> None:
        codigo, _, err = rodar("--json")
        self.assertEqual(codigo, 1)
        self.assertIn("falta o comando", err)

    def test_sem_argumento_continua_saindo_um(self) -> None:
        codigo, out, _ = rodar()
        self.assertEqual(codigo, 1)
        self.assertIn("ciclo.py", out)

    def test_orcamento_com_nome_errado_era_ignorado_e_agora_recusa(self) -> None:
        codigo, _, err = rodar("abrir", "SPEC-001", "--orcamento-validacao", "3")
        self.assertEqual(codigo, 1)
        self.assertIn("--orcamento-validacao", err)
        self.assertEqual(self.ciclos(), [])

    def test_opcoes_conhecidas_seguem_valendo(self) -> None:
        self.assertEqual(rodar("abrir", "SPEC-001", "--spec-aprovada", "--orcamento-validar", "3")[0], 0)
        self.assertEqual(self.ciclos(), ["SPEC-001.json"])
        self.assertEqual(estado()["orcamento"]["validar"], 3)


class BranchDoCiclo(Sandbox):
    """O guardrail julga o `gh pr create` pela branch do ciclo — o `abrir` grava qual é."""

    def test_abrir_grava_a_branch(self) -> None:
        for args in (["init", "-q", "."],
                     ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                      "--allow-empty", "-m", "base"],
                     ["checkout", "-q", "-b", "feat/spec-001"]):
            subprocess.run(["git", *args], check=True, capture_output=True)
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        self.assertEqual(estado()["branch"], "feat/spec-001")

    def test_fora_de_um_repositorio_git_a_branch_e_nula(self) -> None:
        rodar("abrir", "SPEC-001", "--spec-aprovada")
        self.assertIsNone(estado()["branch"])


if __name__ == "__main__":
    unittest.main()
