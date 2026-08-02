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

E o estado vive em `.agents/ciclo/<spec>.json`: sobrevive a reset de contexto, a troca
de sessão e a troca de CLI. O agente não escreve ali (guardrail bloqueia, ADR-0022) —
pelo mesmo motivo que não escreve a própria telemetria.

Uso:
    ciclo.py abrir SPEC-001 [--orcamento-validar 2] [--orcamento-revisar 2] [--spec-aprovada]
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

PASTA = Path(".agents/ciclo")

# --- a máquina ---------------------------------------------------------------------
# estado → {resultado aceito: destino}. `None` marca destino calculado (orçamento).
TRANSICOES: dict[str, dict[str, str | None]] = {
    "especificando":       {"spec_pronta": "aguardando_aprovacao"},
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

INSTRUCAO = {
    "especificando": "Rode /kairos-forge:especificar. Ao final: `ciclo.py registrar spec_pronta`.",
    "aguardando_aprovacao": "GATE HUMANO — apresente objetivo, P1, não-objetivos e perguntas "
                            "abertas; espere SIM/NÃO/AJUSTAR. Depois: `registrar aprovada` ou "
                            "`registrar recusada`. Nunca responda pelo usuário.",
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

def veredicto_do_relatorio(spec: str) -> str | None:
    """Lê o veredicto do relatório de validação mais recente. None se não houver.

    Existe para que `registrar aprovado` não seja aceito na palavra do agente: a
    transição é alimentada por artefato. Mesmo princípio da corroboração de
    trajetória do ADR-0021.
    """
    pasta = Path("docs/specs/validacoes")
    if not pasta.is_dir():
        return None
    alvo = re.sub(r"[^A-Za-z0-9_-]", "-", spec)
    cands = sorted(pasta.glob(f"VALIDACAO-{alvo}-*.md"), key=lambda p: p.name, reverse=True)
    if not cands:
        return None
    m = re.search(r"\*\*Veredicto:\*\*\s*(.+)", cands[0].read_text(encoding="utf-8"))
    if not m:
        return None
    texto = m.group(1).strip().lower()
    if "bloquead" in texto:
        return "bloqueado"
    if "ressalva" in texto:
        return "aprovado_com_ressalvas"
    if "aprovad" in texto:
        return "aprovado"
    return None


# --- comandos ----------------------------------------------------------------------

def abrir(spec: str, orc_val: int, orc_rev: int, spec_aprovada: bool) -> int:
    p = caminho(spec)
    if p.is_file():
        d = ler(p)
        if d.get("estado") not in TERMINAIS:
            sys.exit(f"erro: já existe ciclo aberto para {spec} em '{d['estado']}'. "
                     f"Veja: ciclo.py estado {spec}")
    estado = "construindo" if spec_aprovada else "especificando"
    d = {
        "spec": spec,
        "estado": estado,
        "aberto_em": agora(),
        "orcamento": {"validar": orc_val, "revisar": orc_rev},
        "rodadas": {"validar": 0, "revisar": 0},
        "historico": [{"t": agora(), "de": None, "para": estado, "resultado": "abrir"}],
    }
    gravar(p, d)
    imprimir(d)
    return 0


def registrar(spec: str | None, resultado: str, nota: str | None) -> int:
    p = resolver(spec)
    d = ler(p)
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
    if estado == "validando" and resultado in ("aprovado", "aprovado_com_ressalvas"):
        real = veredicto_do_relatorio(d["spec"])
        if real == "bloqueado":
            print(f"🛑 recusado: o relatório de validação mais recente de {d['spec']} diz "
                  f"BLOQUEADO.\n   Registre `bloqueado` e corrija, ou rode a validação de novo.",
                  file=sys.stderr)
            return 1
        if real is None:
            print(f"🛑 recusado: não encontrei relatório em docs/specs/validacoes/ para "
                  f"{d['spec']}.\n   Rode /kairos-forge:validar antes de registrar o resultado.",
                  file=sys.stderr)
            return 1

    destino = aceitos[resultado]
    esgotou = None

    if destino is None:  # bloqueio/crítico — o orçamento decide
        gate = "validar" if estado == "validando" else "revisar"
        if d["rodadas"][gate] >= d["orcamento"][gate]:
            destino, esgotou = "escalado", gate
        else:
            d["rodadas"][gate] += 1
            destino = "corrigindo_validacao" if gate == "validar" else "corrigindo_revisao"

    d["historico"].append({"t": agora(), "de": estado, "para": destino,
                           "resultado": resultado, **({"nota": nota} if nota else {})})
    d["estado"] = destino
    if esgotou:
        d["motivo_escalacao"] = (f"orçamento de {esgotou} esgotado "
                                 f"({d['rodadas'][esgotou]}/{d['orcamento'][esgotou]} rodadas)")
    gravar(p, d)
    imprimir(d)
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


def imprimir(d: dict) -> None:
    e = d["estado"]
    icone = {"escalado": "⏸️", "encerrado": "✅", "pronto_para_pr": "🎯"}.get(e, "🔁")
    print(f"{icone} {d['spec']} — estado: {e}")
    print(f"   Rodadas: validar {d['rodadas']['validar']}/{d['orcamento']['validar']} · "
          f"revisar {d['rodadas']['revisar']}/{d['orcamento']['revisar']}")
    if d.get("motivo_escalacao"):
        print(f"   Motivo: {d['motivo_escalacao']}")
    if d.get("motivo_encerramento"):
        print(f"   Motivo: {d['motivo_encerramento']}")
    print(f"\n   PRÓXIMO PASSO: {INSTRUCAO[e]}")


def estado(spec: str | None, como_json: bool) -> int:
    p = resolver(spec)
    d = ler(p)
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
            d = ler(p)
        except Exception:
            continue
        linhas.append((d["spec"], d["estado"],
                       f"{d['rodadas']['validar']}/{d['orcamento']['validar']}",
                       f"{d['rodadas']['revisar']}/{d['orcamento']['revisar']}"))
    if not linhas:
        print("nenhum ciclo registrado.")
        return 0
    print(f"{'spec':<20} {'estado':<22} {'validar':>8} {'revisar':>8}")
    print("-" * 62)
    for s, e, v, r in linhas:
        print(f"{s:<20} {e:<22} {v:>8} {r:>8}")
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

    orc_val = opcao("--orcamento-validar", int, 2)
    orc_rev = opcao("--orcamento-revisar", int, 2)
    motivo = opcao("--motivo", str, "")
    nota = opcao("--nota", str, None)
    spec_aprovada = "--spec-aprovada" in args
    args = [a for a in args if a != "--spec-aprovada"]

    cmd = args[0]
    resto = args[1:]

    if cmd == "abrir":
        if not resto:
            sys.exit("erro: uso — ciclo.py abrir <SPEC>")
        return abrir(resto[0], orc_val, orc_rev, spec_aprovada)
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
