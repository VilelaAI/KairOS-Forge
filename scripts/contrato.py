#!/usr/bin/env python3
"""contrato.py — contratos de fronteira dos relatórios da fábrica (ADR-0032).

MÓDULO PURO: string entra, resultado sai. Sem I/O, sem rede, sem estado, **nunca
levanta exceção**. É o que permite testá-lo byte a byte e chamá-lo de dentro de um
hook sem risco de derrubar a sessão.

Por que existe: até a v0.23 o `ciclo.py` lia o veredicto da validação com um regex
sobre prosa (`**Veredicto:** ...`). Funciona até o dia em que um relatório de
**revisão** — que tem exatamente a mesma linha — é lido como se fosse validação. O
contrato passa a ser um bloco cercado explícito, com fence **própria por tipo**:

    ```kairos-critica        → crítica adversarial da SPEC (/kairos-forge:especificar)
    ```kairos-validacao      → aceite contra a SPEC  (/kairos-forge:validar)
    ```kairos-revisao        → code review pré-PR    (/kairos-forge:revisar)

As três fences são deliberadamente distintas. Um validador que emitisse o bloco do
revisor seria aceito por engano se a fence fosse compartilhada — a separação é o
ponto, não um detalhe de estilo.

## Prova de cobertura

A regra que dá dente ao contrato: **relatório limpo exige lista do que foi olhado.**

    bloqueios == 0  ⇒  `verificado` não pode ser vazio
    criticos  == 0  ⇒  `examinado`  não pode ser vazio
    achados   == 0  ⇒  `examinado`  não pode ser vazio

"Não achei nada" sem dizer onde procurou não é ausência de defeito, é ausência de
busca — e as duas coisas produzem o mesmo texto tranquilizador. A regra já existia em
prosa no `anti-drift.md` ("olhei e parece bom não é crítica"); aqui ela vira código
que recusa.

Uso como biblioteca:

    from contrato import ler_validacao, ler_revisao
    r = ler_validacao(texto)
    if r.ok: r.dados["veredicto"], r.dados["bloqueios"]

Uso como CLI (para os CLIs sem hook, para o CI e para depurar):

    contrato.py criticar <arquivo.md>
    contrato.py validar  <arquivo.md>
    contrato.py revisar  <arquivo.md>
    contrato.py esquema        # contrato de integração (ADR-0034), legível por máquina

Só stdlib.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- fences: uma por tipo, nunca compartilhada --------------------------------------

FENCE_VALIDACAO = "kairos-validacao"
FENCE_REVISAO = "kairos-revisao"
FENCE_CRITICA = "kairos-critica"

# Mínimo de críticos independentes na crítica da SPEC (ADR-0033). Um crítico só é
# revisão; adversarial exige mais de um olhar, e é o parser que cobra.
MIN_CRITICOS = 2

VEREDICTOS = ("aprovado", "aprovado_com_ressalvas", "bloqueado")
FAIXAS = (1, 2, 3)

# O que a re-revisão diz de cada 🔴 da rodada anterior (ADR-0048, do ADDRESSED / NOT
# ADDRESSED da Alethe). Tentativa que deixa o defeito no lugar é `nao_resolvido`.
ESTADOS_ANTERIOR = ("resolvido", "nao_resolvido")

# --- contrato de integração (ADR-0034) ----------------------------------------------
# As três fences e as regras abaixo são CONTRATO PÚBLICO — o kairos-symphony (e
# qualquer outro consumidor) precisa produzir e ler estes blocos. `contrato.py esquema`
# publica a declaração legível por máquina; o `release.py check` recusa mudança de forma
# sem bump, comparando digest.
#
# MENOR (1.x): campo opcional novo, fence nova, mensagem de erro diferente.
# MAIOR (x.0): campo obrigatório novo ou removido, regra de aceitação mais estrita.
CONTRATO_VERSAO = "1.2"   # 1.1: `incompletos` na revisão (ADR-0046)
                          # 1.2: `sem_evidencia` na validação; `achados` e `anteriores`
                          #      na revisão (ADR-0048)

# Teto de itens nas listas de cobertura. Existe para o parser não virar vetor de
# payload absurdo, não porque 200 seja um número especial.
MAX_ITENS = 200

# Códigos de erro. `estrutural` merece retry do agente; `sem_cobertura` é achado de
# conteúdo (o relatório está errado, não malformado) e não deve ser "tentado de novo"
# sem que alguém olhe.
AUSENTE = "ausente"
JSON_INVALIDO = "json_invalido"
ESTRUTURAL = "estrutural"
SEM_COBERTURA = "sem_cobertura"


@dataclass
class Resultado:
    """Resultado de leitura de contrato. Nunca lança — o erro vem no campo."""
    ok: bool
    codigo: str | None = None
    erro: str | None = None
    dados: dict = field(default_factory=dict)


def _falha(codigo: str, erro: str) -> Resultado:
    return Resultado(ok=False, codigo=codigo, erro=erro)


# --- extração ------------------------------------------------------------------------

def extrair_ultimo_bloco(texto: str, fence: str) -> str | None:
    """Conteúdo do último bloco FECHADO com essa fence. None se não houver.

    Três tolerâncias deliberadas, porque as três acontecem em texto real de modelo:

    · **CRLF** — arquivo salvo no Windows não pode invalidar o contrato.
    · **Fence colada no preâmbulo** — sem linha em branco antes da abertura.
    · **Indentação até 3 espaços** — o que o CommonMark ainda considera fence.

    E uma intolerância deliberada: bloco **não fechado** não conta. Saída truncada no
    meio é exatamente o caso em que aceitar o parcial produz o dano — melhor não ter
    contrato do que ter meio contrato.

    O **último** vence porque o modelo às vezes mostra um rascunho antes do final.
    """
    if not texto:
        return None
    t = texto.replace("\r\n", "\n").replace("\r", "\n")
    padrao = re.compile(
        rf"^[ ]{{0,3}}```[ \t]*{re.escape(fence)}[ \t]*\n(.*?)^[ ]{{0,3}}```[ \t]*$",
        re.MULTILINE | re.DOTALL,
    )
    achados = padrao.findall(t)
    return achados[-1] if achados else None


def _lista_de(valor, campo: str) -> tuple[list[str] | None, str | None]:
    if not isinstance(valor, list):
        return None, f"campo '{campo}' precisa ser lista"
    if len(valor) > MAX_ITENS:
        return None, f"campo '{campo}' tem {len(valor)} itens, teto {MAX_ITENS}"
    itens = [str(v).strip() for v in valor if str(v).strip()]
    return itens, None


def _inteiro_de(valor, campo: str) -> tuple[int | None, str | None]:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 0:
        return None, f"campo '{campo}' precisa ser inteiro >= 0"
    return valor, None


def _estados_de(valor, campo: str) -> tuple[dict[str, str] | None, str | None]:
    """`{"R1": "resolvido", "R2": "nao_resolvido"}`, tolerando acento e espaço no valor."""
    if not isinstance(valor, dict):
        return None, f"campo '{campo}' precisa ser objeto {{id: estado}}"
    if len(valor) > MAX_ITENS:
        return None, f"campo '{campo}' tem {len(valor)} itens, teto {MAX_ITENS}"
    saida: dict[str, str] = {}
    for chave, estado in valor.items():
        norma = str(estado).strip().lower().replace("ã", "a").replace(" ", "_")
        if norma not in ESTADOS_ANTERIOR:
            return None, (f"'{campo}.{chave}' = '{estado}' inválido — use "
                          f"{' ou '.join(ESTADOS_ANTERIOR)}")
        saida[str(chave).strip()] = norma
    return saida, None


def _carregar(texto: str, fence: str) -> tuple[dict | None, Resultado | None]:
    bruto = extrair_ultimo_bloco(texto, fence)
    if bruto is None:
        return None, _falha(AUSENTE, f"nenhum bloco ```{fence} fechado no documento")
    try:
        dados = json.loads(bruto)
    except Exception as e:
        return None, _falha(JSON_INVALIDO, f"bloco ```{fence} não é JSON válido — {e}")
    if not isinstance(dados, dict):
        return None, _falha(ESTRUTURAL, f"bloco ```{fence} precisa ser um objeto JSON")
    return dados, None


# --- contrato da validação ------------------------------------------------------------

def ler_validacao(texto: str) -> Resultado:
    """Lê o bloco ```kairos-validacao. Campos: veredicto, bloqueios, verificado[] e, desde o
    contrato 1.2, o opcional sem_evidencia — quantos bloqueios são falta de prova, não
    falha mostrada (o NOT_PROVEN da Alethe, ADR-0048)."""
    dados, erro = _carregar(texto, FENCE_VALIDACAO)
    if erro:
        return erro

    veredicto = str(dados.get("veredicto", "")).strip().lower().replace(" ", "_")
    if veredicto not in VEREDICTOS:
        return _falha(ESTRUTURAL, f"veredicto '{dados.get('veredicto')}' inválido — "
                                  f"use um de: {', '.join(VEREDICTOS)}")

    bloqueios, e = _inteiro_de(dados.get("bloqueios"), "bloqueios")
    if e:
        return _falha(ESTRUTURAL, e)

    verificado, e = _lista_de(dados.get("verificado", []), "verificado")
    if e:
        return _falha(ESTRUTURAL, e)

    falha = _coerencia_da_validacao(veredicto, bloqueios, verificado)
    prova, falha = (None, falha) if falha else _falta_de_prova(dados, bloqueios)
    if falha:
        return falha

    return Resultado(ok=True, dados={
        "tipo": "validacao",
        "veredicto": veredicto,
        "bloqueios": bloqueios,
        **prova,
        "verificado": verificado,
        "spec": str(dados.get("spec", "")).strip() or None,
    })


def _coerencia_da_validacao(veredicto: str, bloqueios: int,
                            verificado: list[str]) -> Resultado | None:
    """O veredicto não pode contradizer a própria contagem, e limpo exige cobertura."""
    if veredicto == "bloqueado" and bloqueios == 0:
        return _falha(ESTRUTURAL, "veredicto 'bloqueado' com bloqueios=0 — "
                                  "se nada bloqueia, o veredicto é outro")
    if veredicto != "bloqueado" and bloqueios > 0:
        return _falha(ESTRUTURAL, f"veredicto '{veredicto}' com bloqueios={bloqueios} — "
                                  "achado bloqueante não vira ressalva por escolha de palavra")
    if bloqueios == 0 and not verificado:
        return _falha(SEM_COBERTURA, "relatório sem bloqueio precisa listar em "
                                     "'verificado' o que foi conferido — requisito, gate "
                                     "ou arquivo. Lista vazia com veredicto limpo é "
                                     "ausência de busca, não ausência de defeito")
    return None


def _falta_de_prova(dados: dict, bloqueios: int) -> tuple[dict | None, Resultado | None]:
    """`sem_evidencia` e o derivado `so_falta_prova`: nenhuma falha foi mostrada, o que
    falta é rodar a checagem, não mexer no código (ADR-0048)."""
    sem_evidencia, e = _inteiro_de(dados.get("sem_evidencia", 0), "sem_evidencia")
    if e:
        return None, _falha(ESTRUTURAL, e)
    if sem_evidencia > bloqueios:
        return None, _falha(ESTRUTURAL, f"sem_evidencia={sem_evidencia} maior que "
                                        f"bloqueios={bloqueios} — requisito sem prova é um "
                                        "tipo de bloqueio, não um a mais")
    return {"sem_evidencia": sem_evidencia,
            "so_falta_prova": bloqueios > 0 and sem_evidencia == bloqueios}, None


# --- contrato da revisão --------------------------------------------------------------

def _coerencia_da_revisao(veredicto: str, criticos: int, examinado: list[str],
                          incompletos: list[str]) -> Resultado | None:
    """A falha de coerência, cobertura ou completude da revisão; None se o bloco se sustenta."""
    if veredicto == "bloqueado" and criticos == 0:
        return _falha(ESTRUTURAL, "veredicto 'bloqueado' com criticos=0 — "
                                  "🔴 é o que bloqueia; sem 🔴 o veredicto é outro")
    if veredicto != "bloqueado" and criticos > 0:
        return _falha(ESTRUTURAL, f"veredicto '{veredicto}' com criticos={criticos} — "
                                  "🔴 não vira ressalva (regra 6 do /kairos-forge:revisar)")
    if criticos == 0 and not examinado:
        return _falha(SEM_COBERTURA, "revisão sem 🔴 precisa listar em 'examinado' o que "
                                     "foi lido — arquivo, dimensão ou revisor. Lista vazia "
                                     "com veredicto limpo é ausência de busca")
    # ADR-0046, do orch-review do ECC: revisor que não rodou não aprovou. Revisão com uma
    # dimensão a menos e veredicto limpo é o mesmo texto tranquilizador da lista vazia.
    if incompletos and veredicto != "bloqueado":
        return _falha(SEM_COBERTURA, f"revisão incompleta — sem parecer de "
                                     f"{', '.join(incompletos)}. Revisão incompleta não "
                                     "aprova: acione de novo quem faltou")
    return None


def ler_revisao(texto: str) -> Resultado:
    """Lê o bloco ```kairos-revisao. Campos: veredicto, faixa, criticos, examinado[] e, desde
    o contrato 1.1, o opcional incompletos[] — revisor da faixa que não entregou parecer."""
    dados, erro = _carregar(texto, FENCE_REVISAO)
    if erro:
        return erro

    veredicto = str(dados.get("veredicto", "")).strip().lower().replace(" ", "_")
    if veredicto not in VEREDICTOS:
        return _falha(ESTRUTURAL, f"veredicto '{dados.get('veredicto')}' inválido — "
                                  f"use um de: {', '.join(VEREDICTOS)}")

    faixa, falha = _faixa_de(dados)
    if falha:
        return falha

    criticos, e = _inteiro_de(dados.get("criticos"), "criticos")
    if e:
        return _falha(ESTRUTURAL, e)

    examinado, e = _lista_de(dados.get("examinado", []), "examinado")
    if e:
        return _falha(ESTRUTURAL, e)

    incompletos, e = _lista_de(dados.get("incompletos", []), "incompletos")
    if e:
        return _falha(ESTRUTURAL, e)
    falha = _coerencia_da_revisao(veredicto, criticos, examinado, incompletos)
    if falha:
        return falha

    rodada, falha = _rodada_da_revisao(dados, veredicto, criticos)
    if falha:
        return falha

    return Resultado(ok=True, dados={
        "tipo": "revisao",
        "veredicto": veredicto,
        "faixa": faixa,
        "criticos": criticos,
        "examinado": examinado,
        "incompletos": incompletos,
        **rodada,
    })


def _faixa_de(dados: dict) -> tuple[int | None, Resultado | None]:
    faixa = dados.get("faixa")
    if isinstance(faixa, str) and faixa.strip().isdigit():
        faixa = int(faixa.strip())
    if faixa not in FAIXAS:
        return None, _falha(ESTRUTURAL, f"faixa '{dados.get('faixa')}' inválida — use 1 "
                                        "(contida), 2 (ampla) ou 3 (difícil de reverter)")
    return faixa, None


def _achados_de(dados: dict, criticos: int) -> tuple[list[str] | None, str | None]:
    """Um id por 🔴, sem repetição (ADR-0048)."""
    achados, e = _lista_de(dados.get("achados", []), "achados")
    if e:
        return None, e
    if achados and len(achados) != criticos:
        return None, f"'achados' lista {len(achados)} id(s) e criticos={criticos} — um id por 🔴"
    if len({a.casefold() for a in achados}) != len(achados):
        return None, "id repetido em 'achados' — cada 🔴 tem o seu"
    return achados, None


def _anteriores_de(dados: dict, veredicto: str) -> tuple[dict | None, str | None]:
    """O que a re-revisão diz de cada 🔴 anterior; não resolvido mantém o bloqueio."""
    anteriores, e = _estados_de(dados.get("anteriores", {}), "anteriores")
    if e:
        return None, e
    abertos = sorted(k for k, v in anteriores.items() if v == "nao_resolvido")
    if abertos and veredicto != "bloqueado":
        return None, (f"🔴 anterior não resolvido ({', '.join(abertos)}) com veredicto "
                      f"'{veredicto}' — o defeito segue no lugar, o 🔴 também")
    return anteriores, None


def _rodada_da_revisao(dados: dict, veredicto: str,
                       criticos: int) -> tuple[dict | None, Resultado | None]:
    achados, e = _achados_de(dados, criticos)
    anteriores, e2 = _anteriores_de(dados, veredicto) if not e else (None, None)
    if e or e2:
        return None, _falha(ESTRUTURAL, e or e2)
    return {"achados": achados, "anteriores": anteriores}, None


# --- a re-revisão presta contas (ADR-0048) -------------------------------------------
# Depois de uma correção, a revisão começava do zero, e nada obrigava a dizer o que
# aconteceu com cada 🔴 da rodada anterior. Revisão limpa que esquece um 🔴 é a mesma
# ausência de busca que a prova de cobertura recusa. As duas funções abaixo são o que o
# `ciclo.py` chama: ele guarda os ids pendentes entre as rodadas (o relatório do mesmo
# dia sobrescreve o anterior, então o arquivo não serve de memória).

def prestar_contas(pendentes: list[str], dados: dict) -> str | None:
    """Por que esta revisão não pode fechar limpa diante dos 🔴 pendentes — ou None."""
    if not pendentes:
        return None
    marcados = {k.casefold(): v for k, v in (dados.get("anteriores") or {}).items()}
    faltando = [p for p in pendentes if p.casefold() not in marcados]
    if faltando:
        return (f"re-revisão sem conta de {len(faltando)} 🔴 da rodada anterior "
                f"({', '.join(faltando)}) — marque cada um em 'anteriores' como "
                "resolvido ou nao_resolvido, olhando o diff da correção")
    abertos = [p for p in pendentes if marcados[p.casefold()] != "resolvido"]
    if abertos:
        return f"🔴 da rodada anterior ainda não resolvido: {', '.join(abertos)}"
    return None


def pendentes_depois(pendentes: list[str], dados: dict) -> list[str]:
    """Os 🔴 que seguem abertos depois de uma revisão bloqueada: os novos desta rodada e os
    anteriores que ela não marcou como resolvidos."""
    marcados = {k.casefold(): v for k, v in (dados.get("anteriores") or {}).items()}
    seguem = [p for p in pendentes if marcados.get(p.casefold()) != "resolvido"]
    novos = [a for a in dados.get("achados") or [] if a.casefold() not in
             {s.casefold() for s in seguem}]
    return seguem + novos


# --- contrato da crítica da SPEC (ADR-0033) -------------------------------------------

def ler_critica(texto: str) -> Resultado:
    """Lê o bloco ```kairos-critica. Campos: veredicto, achados, criticado_por[], examinado[].

    A diferença para os outros dois: além de coerência e cobertura, este contrato cobra
    **independência** — pelo menos {MIN_CRITICOS} críticos distintos. Um crítico só é
    revisão; adversarial é mais de um olhar, e quem cobra é o parser, não o prompt.
    """
    dados, erro = _carregar(texto, FENCE_CRITICA)
    if erro:
        return erro

    veredicto = str(dados.get("veredicto", "")).strip().lower().replace(" ", "_")
    if veredicto not in VEREDICTOS:
        return _falha(ESTRUTURAL, f"veredicto '{dados.get('veredicto')}' inválido — "
                                  f"use um de: {', '.join(VEREDICTOS)}")

    achados, e = _inteiro_de(dados.get("achados"), "achados")
    if e:
        return _falha(ESTRUTURAL, e)

    criticos, e = _lista_de(dados.get("criticado_por", []), "criticado_por")
    if e:
        return _falha(ESTRUTURAL, e)
    distintos = sorted({c.lower() for c in criticos})
    if len(distintos) < MIN_CRITICOS:
        return _falha(ESTRUTURAL, f"crítica da SPEC exige ao menos {MIN_CRITICOS} críticos "
                                  f"distintos em 'criticado_por'; veio {len(distintos)}. "
                                  "Um olhar só é revisão, não crítica adversarial")

    examinado, e = _lista_de(dados.get("examinado", []), "examinado")
    if e:
        return _falha(ESTRUTURAL, e)

    if veredicto == "bloqueado" and achados == 0:
        return _falha(ESTRUTURAL, "veredicto 'bloqueado' com achados=0 — "
                                  "se nada foi encontrado, o veredicto é outro")
    if veredicto != "bloqueado" and achados > 0:
        return _falha(ESTRUTURAL, f"veredicto '{veredicto}' com achados={achados} — "
                                  "achado que impede a SPEC não vira ressalva por escolha "
                                  "de palavra")

    if achados == 0 and not examinado:
        return _falha(SEM_COBERTURA, "crítica sem achado precisa listar em 'examinado' o que "
                                     "foi lido da SPEC — objetivo, requisitos, plano, matriz "
                                     "de testes. Lista vazia com veredicto limpo é ausência "
                                     "de busca")

    return Resultado(ok=True, dados={
        "tipo": "critica",
        "veredicto": veredicto,
        "achados": achados,
        "criticado_por": criticos,
        "examinado": examinado,
        "spec": str(dados.get("spec", "")).strip() or None,
    })


LEITORES = {"validar": ler_validacao, "revisar": ler_revisao, "criticar": ler_critica}


# --- declaração pública do contrato (ADR-0034) ----------------------------------------

def contrato_publico() -> dict:
    """Os três contratos, legíveis por máquina. `contrato.py esquema`.

    Existe para o consumidor gerar o próprio validador em vez de reimplementar as
    regras de cabeça — regra reimplementada de cabeça diverge na primeira mudança.
    """
    comum = ["extração: último bloco FECHADO com a fence vence",
             "tolera CRLF, fence colada no preâmbulo e indentação até 3 espaços",
             "bloco não fechado NÃO conta — parcial é pior que ausente",
             "coerência: veredicto 'bloqueado' ⟺ contagem de achados ≥ 1",
             f"listas com no máximo {MAX_ITENS} itens"]
    return {
        "nome": "kairos-forge/contrato",
        "versao": CONTRATO_VERSAO,
        "comando": "contrato.py <criticar|validar|revisar> <arquivo.md>",
        "veredictos": list(VEREDICTOS),
        "codigos_de_erro": {
            AUSENTE: "nenhum bloco com a fence esperada",
            JSON_INVALIDO: "bloco não é JSON válido",
            ESTRUTURAL: "campo ausente, tipo errado ou incoerência — cabe retry",
            SEM_COBERTURA: "veredicto limpo sem lista do que foi olhado — achado, não retry",
        },
        "relatorios": {
            "critica": {
                "fence": FENCE_CRITICA,
                "pasta": "docs/specs/criticas/",
                "arquivo": "CRITICA-<SPEC>-<AAAA-MM-DD>.md",
                "obrigatorios": {"veredicto": "string", "achados": "integer>=0",
                                 "criticado_por": "string[]", "examinado": "string[]"},
                "opcionais": {"spec": "string"},
                "regras": comum + [
                    "cobertura: achados=0 exige 'examinado' não-vazio",
                    f"independência: ao menos {MIN_CRITICOS} nomes DISTINTOS em "
                    "'criticado_por' (case-insensitive)",
                ],
            },
            "validacao": {
                "fence": FENCE_VALIDACAO,
                "pasta": "docs/specs/validacoes/",
                "arquivo": "VALIDACAO-<SPEC>-<AAAA-MM-DD>.md",
                "obrigatorios": {"veredicto": "string", "bloqueios": "integer>=0",
                                 "verificado": "string[]"},
                "opcionais": {"spec": "string", "sem_evidencia": "integer>=0"},
                "regras": comum + [
                    "cobertura: bloqueios=0 exige 'verificado' não-vazio",
                    "sem_evidencia ≤ bloqueios: falta de prova é um tipo de bloqueio (1.2)",
                    "sem_evidencia = bloqueios > 0: nenhuma falha mostrada — o ciclo manda "
                    "rodar a prova antes de mexer no código (1.2)",
                ],
            },
            "revisao": {
                "fence": FENCE_REVISAO,
                "pasta": "docs/specs/revisoes/",
                "arquivo": "REVISAO-<SPEC ou slug>-<AAAA-MM-DD>.md",
                "obrigatorios": {"veredicto": "string", "faixa": "1|2|3",
                                 "criticos": "integer>=0", "examinado": "string[]"},
                "opcionais": {"incompletos": "string[]", "achados": "string[]",
                              "anteriores": "object<string," + "|".join(ESTADOS_ANTERIOR) + ">"},
                "regras": comum + [
                    "cobertura: criticos=0 exige 'examinado' não-vazio",
                    "completude: 'incompletos' não-vazio exige veredicto 'bloqueado' — "
                    "revisor que não rodou não aprovou (1.1)",
                    "achados: um id por 🔴, sem repetição (1.2)",
                    "anteriores: 'nao_resolvido' exige veredicto 'bloqueado' (1.2)",
                    "re-revisão: com 🔴 pendente da rodada anterior, fechar limpo exige cada "
                    "id em 'anteriores' como 'resolvido' — cobrado pelo ciclo.py (1.2)",
                    "faixa 3 (difícil de reverter) nunca fecha por evidência — ADR-0031",
                ],
            },
        },
    }


# --- CLI --------------------------------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "esquema":
        print(json.dumps(contrato_publico(), ensure_ascii=False, indent=2))
        return 0
    if len(args) < 2 or args[0] not in LEITORES:
        print(__doc__.strip())
        return 1
    try:
        texto = Path(args[1]).read_text(encoding="utf-8")
    except Exception as e:
        print(f"🛑 não consegui ler {args[1]}: {e}", file=sys.stderr)
        return 1
    r = LEITORES[args[0]](texto)
    if r.ok:
        print(json.dumps(r.dados, ensure_ascii=False, indent=2))
        return 0
    print(f"🛑 contrato inválido [{r.codigo}]: {r.erro}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
