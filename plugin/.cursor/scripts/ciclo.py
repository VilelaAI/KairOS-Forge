#!/usr/bin/env python3
"""ciclo.py — máquina de estados determinística do arco `/kairos-forge:entregar` (ADR-0029).

Até a v0.20 o arco vivia em prosa: a skill dizia "no bloqueio, corrija; máximo 2
rodadas; na terceira, escale". Quem contava as rodadas era o modelo — juiz em causa
própria sobre o próprio orçamento. Inspirado no padrão Inverted Agentic Orchestration
(cooperacode/IAO), a transição passa a ser decidida por código.

O que muda na prática: a skill **não escolhe** o próximo passo, ela **pergunta**.

    ciclo.py estado        → qual o passo agora
    ciclo.py registrar X   → o que aconteceu; o script decide o que vem depois

Três garantias que a prosa não dava:

  1. **Orçamento é fato, não promessa.** Esgotou, `registrar` devolve `escalado` —
     não existe "mais uma rodadinha".
  2. **Correção na revisão reabre a validação.** A regra que a skill pedia em prosa
     ("se a correção tocar produção, o /validar volta a valer") vira aresta do grafo:
     `corrigindo_revisao` só sai para `validando`. É o modo de falha silencioso do
     arco, fechado por construção.
  3. **Veredicto vem do artefato, não da palavra.** Registrar `aprovado` sem relatório
     de validação correspondente é recusado — o script lê `docs/specs/validacoes/`.

E uma quarta, desde a v0.24 (ADR-0032): **progresso real devolve a ficha.**

O orçamento plano confundia duas coisas diferentes. Cinco bloqueios que viram dois e
depois um é uma equipe convergindo — escalar na segunda rodada é interromper quem
estava resolvendo. Cinco bloqueios que continuam cinco é patinação, e a segunda rodada
já é uma a mais do que precisava. Agora o script compara a contagem de bloqueios com a
**melhor marca já atingida** naquele gate: baixou, a ficha volta; não baixou, queima.
Um teto absoluto de rodadas continua valendo por cima, porque convergência lenta demais
também é motivo para chamar alguém.

A contagem vem do bloco de contrato do relatório (`contrato.py`), nunca da alegação do
agente — mesma regra do veredicto. Relatório sem bloco de contrato degrada para o
comportamento anterior (toda rodada queima ficha), o que é honesto: sem número, não há
como afirmar progresso.

E o estado vive em `.agents/ciclo/<spec>.json`: sobrevive a reset de contexto, a troca
de sessão e a troca de CLI. O agente não escreve ali (guardrail bloqueia, ADR-0022) —
pelo mesmo motivo que não escreve a própria telemetria.

E uma quinta, desde a v0.26 (ADR-0033): **o planejamento também tem fases e gate.**

Os três checkpoints do `/especificar` — espelhar o entendimento, escolher a abordagem,
aprovar a SPEC — já existiam, em prosa. Prosa para um humano que está lendo; nada para
um runner headless. Agora são estados, e entre a SPEC escrita e a aprovação entra a
**crítica adversarial**: ao menos dois críticos que não escreveram a SPEC atacam
premissa, requisito, plano e testabilidade, com o resultado lido de artefato como
qualquer outro gate.

Por que só agora: em sessão, uma premissa errada é pega porque alguém lê antes de
aprovar. Sem ninguém lendo, o orçamento inteiro queima construindo a coisa errada com
disciplina impecável.

Uso:
    ciclo.py abrir SPEC-001 [--orcamento-criticar 2] [--orcamento-validar 2]
                            [--orcamento-revisar 2] [--teto-criticar 6]
                            [--teto-validar 6] [--teto-revisar 6] [--spec-aprovada]
    ciclo.py estado [SPEC-001] [--json]
    ciclo.py registrar <resultado> [SPEC-001] [--nota "..."]
    ciclo.py encerrar [SPEC-001] --motivo "..."
    ciclo.py listar

Só stdlib.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from contrato import ler_critica, ler_revisao, ler_validacao
except Exception:  # contrato ausente/quebrado nunca derruba a máquina de estados
    ler_critica = ler_revisao = ler_validacao = None  # type: ignore[assignment]

PASTA = Path(".agents/ciclo")

# Gates com orçamento próprio. Cada um conta rodadas SEM progresso, tem teto absoluto
# e guarda a melhor marca já atingida (ADR-0032).
GATES = ("criticar", "validar", "revisar")

# Onde cada gate lê o veredicto e a contagem de achados — sempre do artefato.
FONTE_DO_GATE = {
    "criticar": ("docs/specs/criticas", "CRITICA", "achados"),
    "validar": ("docs/specs/validacoes", "VALIDACAO", "bloqueios"),
    "revisar": ("docs/specs/revisoes", "REVISAO", "criticos"),
}

# Teto absoluto de rodadas por gate quando não declarado: 3× o orçamento. Progresso
# devolve ficha, mas não dá rodadas infinitas — convergir devagar demais também é
# motivo para chamar alguém.
FATOR_TETO = 3

# --- a máquina ---------------------------------------------------------------------
# estado → {resultado aceito: destino}. `None` marca destino calculado (orçamento).
TRANSICOES: dict[str, dict[str, str | None]] = {
    # Planejamento em fases (ADR-0033). Os três checkpoints já existiam no
    # /especificar como prosa — "espelhar entendimento", "propor abordagens",
    # "aprovar a SPEC". Viram estado porque prosa não para um runner headless: em
    # sessão o humano lê e responde no meio da conversa; sem ninguém lendo, uma
    # premissa errada queima o orçamento inteiro construindo a coisa certa errada.
    "enquadrando":         {"entendimento_pronto": "aguardando_entendimento"},
    "aguardando_entendimento": {"confirmado": "desenhando", "ajustar": "enquadrando"},
    "desenhando":          {"abordagens_prontas": "aguardando_abordagem"},
    "aguardando_abordagem": {"escolhida": "especificando", "ajustar": "desenhando"},
    "especificando":       {"spec_pronta": "criticando"},
    "criticando":          {"limpa": "aguardando_aprovacao", "com_achados": None},
    "corrigindo_spec":     {"pronto": "criticando"},
    "aguardando_aprovacao": {"aprovada": "construindo", "recusada": "encerrado"},
    "construindo":         {"pronto": "validando"},
    "validando":           {"aprovado": "revisando",
                            "aprovado_com_ressalvas": "revisando",
                            "bloqueado": None},
    "corrigindo_validacao": {"pronto": "validando"},
    # A aresta que fecha o modo de falha silencioso: correção de revisão NÃO volta
    # direto para revisar — ela reabre a validação.
    "revisando":           {"limpo": "pronto_para_pr", "critico": None},
    "corrigindo_revisao":  {"pronto": "validando"},
    "pronto_para_pr":      {"pr_aberto": "encerrado"},
}
TERMINAIS = {"encerrado", "escalado"}

# Resultado "limpo" de cada estado de gate. Registrá-lo exige que o ARTEFATO concorde —
# a regra do ADR-0029 aplicada aos três gates, não só à validação.
LIMPO_DO_GATE = {
    "criticando": {"limpa"},
    "validando": {"aprovado", "aprovado_com_ressalvas"},
    "revisando": {"limpo"},
}

INSTRUCAO = {
    "enquadrando": "Rode /kairos-forge:especificar até o passo 4. Laura dimensiona, os "
                   "arquitetos interrogam e você ESPELHA o entendimento — sem escrever SPEC "
                   "ainda. Ao final: `ciclo.py registrar entendimento_pronto`.",
    "aguardando_entendimento": "GATE HUMANO (1/3) — apresente o entendimento espelhado e as "
                               "perguntas abertas; espere confirmação. Depois: "
                               "`registrar confirmado` ou `registrar ajustar`. "
                               "Nunca responda pelo usuário.",
    "desenhando": "Passo 5 do /kairos-forge:especificar: 2-3 abordagens com trade-offs e uma "
                  "recomendação. Decisão arquiteturalmente significativa? Use o modo RFC. "
                  "Ao final: `registrar abordagens_prontas`.",
    "aguardando_abordagem": "GATE HUMANO (2/3) — apresente as abordagens, a recomendada e o "
                            "porquê; espere a escolha. Depois: `registrar escolhida` ou "
                            "`registrar ajustar`. Nunca escolha pelo usuário.",
    "especificando": "Passo 6: escreva a SPEC em docs/specs/ com requisitos rastreáveis, "
                     "plano por agente e matriz de testes. Ao final: `registrar spec_pronta`.",
    "criticando": "Crítica adversarial da SPEC: ao menos 2 críticos independentes, que NÃO "
                  "a escreveram, atacam premissa, requisito, plano e testabilidade. Relatório "
                  "em docs/specs/criticas/. Depois: `registrar limpa` ou `registrar com_achados`.",
    "corrigindo_spec": "Corrija os achados da crítica na SPEC — cada um, ou justifique por "
                       "escrito por que não. Depois: `registrar pronto` (a crítica REABRE).",
    "aguardando_aprovacao": "GATE HUMANO (3/3) — apresente objetivo, P1, não-objetivos e o "
                            "que a crítica encontrou; espere SIM/NÃO/AJUSTAR. Depois: "
                            "`registrar aprovada` ou `registrar recusada`. "
                            "Nunca responda pelo usuário.",
    "construindo": "Construa pela SPEC (/mobilizar ou /rodar). Cada tarefa com gate e "
                   "`verificado:`. Ao final: `registrar pronto`.",
    "validando": "Rode /kairos-forge:validar. Depois: `registrar aprovado` | "
                 "`registrar aprovado_com_ressalvas` | `registrar bloqueado`.",
    "corrigindo_validacao": "Corrija SÓ os achados bloqueantes, acionando os agentes que o "
                            "relatório nomeou. Rode o gate afetado. Depois: `registrar pronto`.",
    "revisando": "Rode /kairos-forge:revisar. Depois: `registrar limpo` (zero 🔴) ou "
                 "`registrar critico`.",
    "corrigindo_revisao": "Corrija os achados 🔴 — nunca por workaround. Depois: "
                          "`registrar pronto` (o ciclo REABRE a validação, não a revisão).",
    "pronto_para_pr": "Abra o PR com a evidência no corpo. NUNCA faça merge. Depois: "
                      "`registrar pr_aberto`.",
    "escalado": "PARADO. Leve ao usuário o achado exato, o que já foi tentado e a decisão "
                "necessária. Só o usuário destrava (novo `abrir` com orçamento ampliado).",
    "encerrado": "Ciclo encerrado. Salve o relatório em docs/specs/entregas/.",
}


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def caminho(spec: str) -> Path:
    return PASTA / f"{re.sub(r'[^A-Za-z0-9_-]', '-', spec)}.json"


def abertos() -> list[Path]:
    if not PASTA.is_dir():
        return []
    saida = []
    for p in sorted(PASTA.glob("*.json")):
        try:
            if json.loads(p.read_text(encoding="utf-8")).get("estado") not in TERMINAIS:
                saida.append(p)
        except Exception:
            continue
    return saida


def resolver(spec: str | None) -> Path:
    """Sem spec explícita, resolve para o único ciclo aberto — conveniência com limite."""
    if spec:
        p = caminho(spec)
        if not p.is_file():
            sys.exit(f"erro: não existe ciclo para '{spec}'. Abra com: ciclo.py abrir {spec}")
        return p
    ab = abertos()
    if not ab:
        sys.exit("erro: nenhum ciclo aberto. Abra com: ciclo.py abrir <SPEC>")
    if len(ab) > 1:
        nomes = ", ".join(p.stem for p in ab)
        sys.exit(f"erro: {len(ab)} ciclos abertos ({nomes}) — diga qual.")
    return ab[0]


def ler(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def gravar(p: Path, d: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)  # troca atômica — crash no meio não corrompe o estado


# --- corroboração do veredicto -----------------------------------------------------

def _mais_recente(pasta: str, prefixo: str, spec: str) -> str | None:
    p = Path(pasta)
    if not p.is_dir():
        return None
    alvo = re.sub(r"[^A-Za-z0-9_-]", "-", spec)
    cands = sorted(p.glob(f"{prefixo}-{alvo}-*.md"), key=lambda x: x.name, reverse=True)
    if not cands:
        return None
    try:
        return cands[0].read_text(encoding="utf-8")
    except Exception:
        return None


def _veredicto_da_prosa(texto: str) -> str | None:
    """Fallback para relatório sem bloco de contrato. Sem contagem — só veredicto."""
    m = re.search(r"\*\*Veredicto(?:\s+agregado)?:\*\*\s*(.+)", texto)
    if not m:
        return None
    t = m.group(1).strip().lower()
    if "bloquead" in t:
        return "bloqueado"
    if "ressalva" in t:
        return "aprovado_com_ressalvas"
    if "aprovad" in t:
        return "aprovado"
    return None


def ler_relatorio(spec: str, gate: str) -> tuple[str | None, int | None, str]:
    """(veredicto, contagem de bloqueios, fonte) do relatório mais recente do gate.

    Existe para que `registrar aprovado` não seja aceito na palavra do agente: a
    transição é alimentada por artefato. Mesmo princípio da corroboração de
    trajetória do ADR-0021.

    `fonte` é `contrato` (bloco cercado — tem contagem), `prosa` (formato antigo,
    veredicto sem contagem) ou `ausente`. Só `contrato` permite afirmar progresso:
    sem número não há comparação, e inventar uma seria pior que não ter.
    """
    pasta, prefixo, campo = FONTE_DO_GATE[gate]
    leitor = {"criticar": ler_critica, "validar": ler_validacao,
              "revisar": ler_revisao}[gate]
    texto = _mais_recente(pasta, prefixo, spec)
    if texto is None:
        return None, None, "ausente"
    if leitor is not None:
        r = leitor(texto)
        if r.ok:
            return r.dados["veredicto"], r.dados[campo], "contrato"
    return _veredicto_da_prosa(texto), None, "prosa"


# --- comandos ----------------------------------------------------------------------

def abrir(spec: str, orcamento: dict, teto: dict, spec_aprovada: bool) -> int:
    p = caminho(spec)
    if p.is_file():
        d = ler(p)
        if d.get("estado") not in TERMINAIS:
            sys.exit(f"erro: já existe ciclo aberto para {spec} em '{d['estado']}'. "
                     f"Veja: ciclo.py estado {spec}")
    estado = "construindo" if spec_aprovada else "enquadrando"
    d = {
        "spec": spec,
        "estado": estado,
        "aberto_em": agora(),
        "orcamento": dict(orcamento),
        "teto": dict(teto),
        # `rodadas` são as fichas consumidas SEM progresso — progresso zera.
        "rodadas": {g: 0 for g in GATES},
        # `rodadas_totais` nunca zera; é o que o teto absoluto mede.
        "rodadas_totais": {g: 0 for g in GATES},
        # melhor (menor) contagem de achados já atingida no gate; None = sem marca.
        "marca": {g: None for g in GATES},
        "historico": [{"t": agora(), "de": None, "para": estado, "resultado": "abrir"}],
    }
    gravar(p, d)
    imprimir(d)
    return 0


def compatibilizar(d: dict) -> dict:
    """Estado escrito por versão anterior ganha os campos novos sem perder história."""
    orc = d.setdefault("orcamento", {})
    d.setdefault("rodadas", {})
    d.setdefault("teto", {})
    d.setdefault("rodadas_totais", {})
    d.setdefault("marca", {})
    for g in GATES:
        orc.setdefault(g, 2)
        d["rodadas"].setdefault(g, 0)
        d["teto"].setdefault(g, max(1, orc[g]) * FATOR_TETO)
        d["rodadas_totais"].setdefault(g, d["rodadas"][g])
        d["marca"].setdefault(g, None)
    return d


def decidir_orcamento(d: dict, gate: str, bloqueios: int | None) -> tuple[str, str | None]:
    """Decide destino e motivo de escalação quando o gate falhou. Muta o estado.

    Ordem deliberada — o teto vem antes do progresso porque progresso não compra
    rodadas infinitas: uma feature que baixa de 40 bloqueios para 39 a cada rodada
    está "progredindo" e mesmo assim precisa de gente.
    """
    d["rodadas_totais"][gate] += 1
    destino = {"criticar": "corrigindo_spec", "validar": "corrigindo_validacao",
               "revisar": "corrigindo_revisao"}[gate]

    if d["rodadas_totais"][gate] >= d["teto"][gate]:
        return "escalado", (f"teto absoluto de {gate} atingido "
                            f"({d['rodadas_totais'][gate]}/{d['teto'][gate]} rodadas)")

    marca = d["marca"].get(gate)
    progrediu = bloqueios is not None and marca is not None and bloqueios < marca
    if bloqueios is not None and (marca is None or bloqueios < marca):
        d["marca"][gate] = bloqueios

    if progrediu:
        d["rodadas"][gate] = 0  # ficha devolvida
        return destino, None

    if d["rodadas"][gate] >= d["orcamento"][gate]:
        estagnado = "" if bloqueios is None else f", parado em {bloqueios} bloqueio(s)"
        return "escalado", (f"orçamento de {gate} esgotado sem progresso "
                            f"({d['rodadas'][gate]}/{d['orcamento'][gate]} rodadas{estagnado})")

    d["rodadas"][gate] += 1
    return destino, None


def registrar(spec: str | None, resultado: str, nota: str | None) -> int:
    p = resolver(spec)
    d = compatibilizar(ler(p))
    estado = d["estado"]

    if estado in TERMINAIS:
        print(f"🛑 ciclo em estado terminal '{estado}' — nada a registrar.\n"
              f"   {INSTRUCAO[estado]}", file=sys.stderr)
        return 1

    aceitos = TRANSICOES.get(estado, {})
    if resultado not in aceitos:
        validos = ", ".join(sorted(aceitos)) or "—"
        print(f"🛑 resultado '{resultado}' não é válido em '{estado}'.\n"
              f"   Válidos aqui: {validos}\n   {INSTRUCAO[estado]}", file=sys.stderr)
        return 1

    # Veredicto vem do artefato, não da palavra do agente.
    gate_do_estado = {"criticando": "criticar", "validando": "validar",
                      "revisando": "revisar"}.get(estado)
    veredicto = contagem = None
    fonte = "ausente"
    if gate_do_estado:
        veredicto, contagem, fonte = ler_relatorio(d["spec"], gate_do_estado)

    if resultado in LIMPO_DO_GATE.get(estado, ()):
        pasta, _, _ = FONTE_DO_GATE[gate_do_estado]
        if veredicto == "bloqueado":
            print(f"🛑 recusado: o relatório mais recente de {d['spec']} em {pasta}/ diz "
                  f"BLOQUEADO.\n   Registre o resultado negativo e corrija, ou rode o gate "
                  "de novo.", file=sys.stderr)
            return 1
        if veredicto is None:
            print(f"🛑 recusado: não encontrei relatório em {pasta}/ para {d['spec']}.\n"
                  f"   Rode o gate e salve o relatório antes de registrar o resultado.",
                  file=sys.stderr)
            return 1

    destino = aceitos[resultado]
    motivo = None

    if destino is None:  # bloqueio/crítico — o orçamento decide
        destino, motivo = decidir_orcamento(d, gate_do_estado or "validar", contagem)

    evento = {"t": agora(), "de": estado, "para": destino, "resultado": resultado}
    if contagem is not None:
        evento["bloqueios"] = contagem
    if gate_do_estado and fonte != "ausente":
        evento["fonte"] = fonte
    if nota:
        evento["nota"] = nota
    d["historico"].append(evento)
    d["estado"] = destino
    if motivo:
        d["motivo_escalacao"] = motivo
    gravar(p, d)
    imprimir(d)
    if gate_do_estado and fonte == "prosa" and destino not in TERMINAIS:
        print("\n   ⚠️  Relatório sem bloco de contrato — sem contagem de achados, toda "
              "rodada queima ficha.\n       Adicione o bloco ```kairos-"
              f"{'validacao' if gate_do_estado == 'validar' else 'revisao'}"
              " para que progresso conte (ADR-0032).", file=sys.stderr)
    return 0


def escalar(spec: str | None, motivo: str) -> int:
    p = resolver(spec)
    d = ler(p)
    d["historico"].append({"t": agora(), "de": d["estado"], "para": "escalado",
                           "resultado": "escalar", "nota": motivo})
    d["estado"] = "escalado"
    d["motivo_escalacao"] = motivo
    gravar(p, d)
    imprimir(d)
    return 0


def encerrar(spec: str | None, motivo: str) -> int:
    p = resolver(spec)
    d = ler(p)
    d["historico"].append({"t": agora(), "de": d["estado"], "para": "encerrado",
                           "resultado": "encerrar", "nota": motivo})
    d["estado"] = "encerrado"
    d["motivo_encerramento"] = motivo
    gravar(p, d)
    imprimir(d)
    return 0


def _placar(d: dict, gate: str) -> str:
    linha = f"{d['rodadas'][gate]}/{d['orcamento'][gate]}"
    tot, teto = d.get("rodadas_totais", {}).get(gate), d.get("teto", {}).get(gate)
    if tot is not None and teto is not None:
        linha += f" (total {tot}/{teto})"
    marca = (d.get("marca") or {}).get(gate)
    if marca is not None:
        linha += f" · melhor marca {marca}"
    return linha


def imprimir(d: dict) -> None:
    d = compatibilizar(d)
    e = d["estado"]
    icone = {"escalado": "⏸️", "encerrado": "✅", "pronto_para_pr": "🎯"}.get(
        e, "🙋" if e.startswith("aguardando_") else "🔁")
    print(f"{icone} {d['spec']} — estado: {e}")
    for g in GATES:
        print(f"   {g.capitalize():<9} {_placar(d, g)}")
    if d.get("motivo_escalacao"):
        print(f"   Motivo: {d['motivo_escalacao']}")
    if d.get("motivo_encerramento"):
        print(f"   Motivo: {d['motivo_encerramento']}")
    print(f"\n   PRÓXIMO PASSO: {INSTRUCAO[e]}")


def estado(spec: str | None, como_json: bool) -> int:
    p = resolver(spec)
    d = compatibilizar(ler(p))
    if como_json:
        print(json.dumps({**d, "proximo_passo": INSTRUCAO[d["estado"]]},
                         ensure_ascii=False, indent=2))
    else:
        imprimir(d)
    return 0


def listar() -> int:
    if not PASTA.is_dir():
        print("nenhum ciclo registrado.")
        return 0
    linhas = []
    for p in sorted(PASTA.glob("*.json")):
        try:
            d = compatibilizar(ler(p))
        except Exception:
            continue
        linhas.append((d["spec"], d["estado"],
                       *[f"{d['rodadas'][g]}/{d['orcamento'][g]}" for g in GATES]))
    if not linhas:
        print("nenhum ciclo registrado.")
        return 0
    cab = "".join(f"{g:>10}" for g in GATES)
    print(f"{'spec':<20} {'estado':<24}{cab}")
    print("-" * (44 + 10 * len(GATES)))
    for s, e, *placares in linhas:
        print(f"{s:<20} {e:<24}" + "".join(f"{p:>10}" for p in placares))
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__.strip())
        return 1

    como_json = "--json" in args
    args = [a for a in args if a != "--json"]

    def opcao(nome, conv, default):
        nonlocal args
        if nome in args:
            i = args.index(nome)
            try:
                v = conv(args[i + 1])
            except (IndexError, ValueError):
                sys.exit(f"erro: {nome} precisa de um valor")
            args = args[:i] + args[i + 2:]
            return v
        return default

    orcamento = {g: opcao(f"--orcamento-{g}", int, 2) for g in GATES}
    teto = {g: opcao(f"--teto-{g}", int, max(1, orcamento[g]) * FATOR_TETO) for g in GATES}
    motivo = opcao("--motivo", str, "")
    nota = opcao("--nota", str, None)
    spec_aprovada = "--spec-aprovada" in args
    args = [a for a in args if a != "--spec-aprovada"]

    cmd = args[0]
    resto = args[1:]

    if cmd == "abrir":
        if not resto:
            sys.exit("erro: uso — ciclo.py abrir <SPEC>")
        return abrir(resto[0], orcamento, teto, spec_aprovada)
    if cmd == "estado":
        return estado(resto[0] if resto else None, como_json)
    if cmd == "registrar":
        if not resto:
            sys.exit("erro: uso — ciclo.py registrar <resultado> [SPEC]")
        return registrar(resto[1] if len(resto) > 1 else None, resto[0], nota)
    if cmd == "escalar":
        if not motivo:
            sys.exit("erro: escalar exige --motivo")
        return escalar(resto[0] if resto else None, motivo)
    if cmd == "encerrar":
        if not motivo:
            sys.exit("erro: encerrar exige --motivo")
        return encerrar(resto[0] if resto else None, motivo)
    if cmd == "listar":
        return listar()

    print(__doc__.strip())
    return 1


if __name__ == "__main__":
    sys.exit(main())
