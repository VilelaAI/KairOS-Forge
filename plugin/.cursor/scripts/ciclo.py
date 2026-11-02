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

E uma sexta, desde a v0.38 (ADR-0045, do ub-mode): **atacar a premissa.**

Duas correções seguidas que falham no mesmo gate, sem baixar a contagem de achados,
quase sempre partem da mesma premissa errada — e a terceira, escrita no mesmo embalo,
também. Na terceira falha seguida o ciclo não volta para a correção: vai para
`atacando_premissa_*`, e só sai com a premissa escrita em uma frase (`--nota`),
diferente das que já foram atacadas na mesma sequência. Progresso real ou gate verde
zeram a sequência. Com o orçamento padrão (2) a escalada chega antes, e a instrução
de `escalado` pede a mesma frase para levar ao humano.

Uso:
    ciclo.py abrir SPEC-001 [--orcamento-criticar 2] [--orcamento-validar 2]
                            [--orcamento-revisar 2] [--teto-criticar 6]
                            [--teto-validar 6] [--teto-revisar 6] [--spec-aprovada]
    ciclo.py estado [SPEC-001] [--json]
    ciclo.py registrar <resultado> [SPEC-001] [--nota "..."]
                         # premissa_escrita exige --nota com a premissa atacada
    ciclo.py reaprovar [SPEC-001]   # aceita a SPEC alterada depois da aprovação (humano);
                                    # recusado antes de a SPEC ter sido selada
    ciclo.py encerrar [SPEC-001] --motivo "..."

Digest da SPEC (v0.34.1): ao entrar em `construindo` o script grava o sha256 do
CONTRATO da SPEC — o texto com as células de Status e Verificação em branco, porque
essas mudam de propósito durante a construção. Se requisito, critério, prioridade ou
plano mudarem depois da aprovação, `estado` avisa, `spec_alterada` fica `true` na
vista pública e um resultado VERDE de gate (`aprovado`, `aprovado_com_ressalvas`,
`limpo`) é recusado até `reaprovar` — SPEC reescrita para casar com o construído é
o `verificado:` pelo avesso, e quem aceita a versão nova é gente.
    ciclo.py listar
    ciclo.py contrato        # contrato de integração (ADR-0034), legível por máquina

Só stdlib.
"""
from __future__ import annotations

import hashlib

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True   # não escrever __pycache__ no diretório do plugin
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from contrato import AUSENTE, ler_critica, ler_revisao, ler_validacao
except Exception:  # contrato ausente/quebrado nunca derruba a máquina de estados
    ler_critica = ler_revisao = ler_validacao = None  # type: ignore[assignment]
    AUSENTE = "ausente"

PASTA = Path(".agents/ciclo")

# --- contrato de integração (ADR-0034) ----------------------------------------------
# A saída de `estado --json` é CONTRATO PÚBLICO: o kairos-symphony e qualquer outro
# orquestrador dependem dela para saber o próximo passo, se precisa de humano e o que
# `registrar` aceita agora. Mudança de forma sem bump aqui quebra consumidor em silêncio
# — e o `release.py check` recusa, comparando o digest da declaração.
#
# MENOR (1.x): campo novo, estado novo, aresta nova. Consumidor antigo continua válido.
# MAIOR (x.0): campo removido/renomeado, semântica alterada, aresta removida.
CONTRATO_VERSAO = "1.2"   # 1.1: campo `spec_alterada` (digest do contrato da SPEC)
                          # 1.2: estados `atacando_premissa_*` (ADR-0045)

# Gates com orçamento próprio. Cada um conta rodadas SEM progresso, tem teto absoluto
# e guarda a melhor marca já atingida (ADR-0032).
GATES = ("criticar", "validar", "revisar")

# Onde cada gate lê o veredicto e a contagem de achados — sempre do artefato.
FONTE_DO_GATE = {
    "criticar": ("docs/specs/criticas", "CRITICA", "achados"),
    "validar": ("docs/specs/validacoes", "VALIDACAO", "bloqueios"),
    "revisar": ("docs/specs/revisoes", "REVISAO", "criticos"),
}
FENCE_DO_GATE = {"criticar": "kairos-critica", "validar": "kairos-validacao",
                 "revisar": "kairos-revisao"}

# Teto absoluto de rodadas por gate quando não declarado: 3× o orçamento. Progresso
# devolve ficha, mas não dá rodadas infinitas — convergir devagar demais também é
# motivo para chamar alguém.
FATOR_TETO = 3

# Atacar a premissa (ADR-0045): na terceira falha seguida do mesmo gate sem progresso
# — duas correções frustradas — a próxima correção só começa com a premissa escrita.
LIMIAR_PREMISSA = 3
TAMANHO_MINIMO_PREMISSA = 20  # uma frase, não uma palavra
CORRIGIR = {"criticar": "corrigindo_spec", "validar": "corrigindo_validacao",
            "revisar": "corrigindo_revisao"}
ATACAR_PREMISSA = {"criticar": "atacando_premissa_spec",
                   "validar": "atacando_premissa_validacao",
                   "revisar": "atacando_premissa_revisao"}
GATE_DA_PREMISSA = {estado: gate for gate, estado in ATACAR_PREMISSA.items()}

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
    # ADR-0045: a premissa escrita reabre a correção do mesmo gate.
    **{estado: {"premissa_escrita": CORRIGIR[gate]} for gate, estado in ATACAR_PREMISSA.items()},
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
    "escalado": "PARADO. Leve ao usuário o achado exato, o que já foi tentado, a premissa "
                "que as tentativas compartilharam (em uma frase) e a decisão necessária. Só "
                "o usuário destrava (novo `abrir` com orçamento ampliado).",
    **{estado: (f"ATAQUE A PREMISSA — duas correções seguidas falharam no gate de {gate} sem "
                "baixar os achados; a terceira não começa sem isto. Escreva em UMA frase a "
                "premissa que as duas compartilharam, diga quais agentes ou componentes "
                "sustentam o desequilíbrio e o que sai da atribuição. A próxima correção parte "
                "de outra premissa. Depois: `registrar premissa_escrita --nota \"<a premissa>\"`.")
       for gate, estado in ATACAR_PREMISSA.items()},
    "encerrado": "Ciclo encerrado. Salve o relatório em docs/specs/entregas/.",
}


# Todos os estados alcançáveis, derivados do grafo — nunca digitados à mão.
ESTADOS = sorted({*TRANSICOES, *TERMINAIS,
                  *(d for m in TRANSICOES.values() for d in m.values() if d)})

# Campos GARANTIDOS na saída de `estado --json`. O que não está aqui é interno e
# pode mudar sem aviso; o que está aqui só muda com bump de CONTRATO_VERSAO.
CAMPOS_ESTADO = {
    "contrato": "string",            # versão deste contrato
    "spec": "string",
    "estado": "string",              # um de `estados`
    "terminal": "boolean",           # nada mais a registrar
    "aguardando_humano": "boolean",  # precisa de resposta de gente, não de agente
    "gate": "string|null",           # gate em jogo agora (criticar/validar/revisar)
    "proximo_passo": "string",       # instrução legível
    "resultados_validos": "string[]",  # o que `registrar` aceita NESTE estado
    "orcamento": "object", "rodadas": "object", "rodadas_totais": "object",
    "teto": "object", "marca": "object",
    "historico": "object[]",
    "spec_alterada": "boolean|null",  # contrato da SPEC mudou desde a aprovação; null = sem digest
    "motivo_escalacao": "string?", "motivo_encerramento": "string?",
}


def contrato_publico() -> dict:
    """Declaração legível por máquina do contrato. `ciclo.py contrato --json`.

    Publica o grafo inteiro — estados, terminais, gates e transições — para que o
    consumidor não precise repetir a máquina do lado dele. Repetir é o caminho curto
    para os dois discordarem depois da primeira aresta nova.
    """
    return {
        "nome": "kairos-forge/ciclo",
        "versao": CONTRATO_VERSAO,
        "comando": "ciclo.py estado --json",
        "estados": ESTADOS,
        "terminais": sorted(TERMINAIS),
        "aguardando_humano": [e for e in ESTADOS if e.startswith("aguardando_")],
        "gates": list(GATES),
        "transicoes": {e: dict(m) for e, m in TRANSICOES.items()},
        "campos": CAMPOS_ESTADO,
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


def ler_relatorio(spec: str, gate: str) -> tuple[str | None, int | None, str, str | None]:
    """(veredicto, contagem de bloqueios, fonte, erro) do relatório mais recente do gate.

    Existe para que `registrar aprovado` não seja aceito na palavra do agente: a
    transição é alimentada por artefato. Mesmo princípio da corroboração de
    trajetória do ADR-0021.

    `fonte` é `contrato` (bloco cercado — tem contagem), `prosa` (formato antigo,
    sem bloco: veredicto sem contagem), `invalido` (há bloco e o parser o recusou —
    `erro` diz por quê) ou `ausente`. Só `contrato` permite afirmar progresso: sem
    número não há comparação, e inventar uma seria pior que não ter. E bloco recusado
    não cai para a prosa: senão o "limpo sem lista do que foi olhado" que o parser
    barra (ADR-0032) passava pela linha `**Veredicto:**` do mesmo arquivo.
    """
    pasta, prefixo, campo = FONTE_DO_GATE[gate]
    leitor = {"criticar": ler_critica, "validar": ler_validacao,
              "revisar": ler_revisao}[gate]
    texto = _mais_recente(pasta, prefixo, spec)
    if texto is None:
        return None, None, "ausente", None
    if leitor is not None:
        r = leitor(texto)
        if r.ok:
            return r.dados["veredicto"], r.dados[campo], "contrato", None
        if r.codigo != AUSENTE:
            return None, None, "invalido", f"[{r.codigo}] {r.erro}"
    return _veredicto_da_prosa(texto), None, "prosa", None


# --- comandos ----------------------------------------------------------------------

# --- digest do contrato da SPEC ----------------------------------------------------
# Inspirado no digest de definição do checkpoint do MHL: retomar contra uma definição
# que mudou é aviso, nunca silêncio. Aqui a definição é a SPEC aprovada.

PASTA_SPECS = Path("docs/specs")
CELULA_PROGRESSO = re.compile(
    r"(?i)^(pendente|em progresso|conclu[ií]do|—|-|)$|^(verificado|em progresso)\s*:")


def arquivo_da_spec(spec: str) -> Path | None:
    """`docs/specs/SPEC-001*.md` — o primeiro que casar; subpastas (relatórios) ficam fora."""
    if not PASTA_SPECS.is_dir():
        return None
    achados = sorted(p for p in PASTA_SPECS.glob(f"{spec}*.md") if p.is_file())
    return achados[0] if achados else None


def contrato_da_spec(texto: str) -> str:
    """O texto da SPEC sem o que muda de propósito durante a construção.

    Células de tabela com Status (Pendente/Em progresso/Concluído) ou Verificação
    (`verificado:`, `em progresso:`, `—`) são zeradas; espaço em branco é normalizado.
    O que sobra — requisitos, critérios, prioridades, plano, matriz, não-objetivos —
    é o contrato que a validação cobra.
    """
    linhas = []
    for linha in texto.splitlines():
        s = linha.strip()
        if s.startswith("|") and s.endswith("|"):
            celulas = [c.strip() for c in s.strip("|").split("|")]
            celulas = ["" if CELULA_PROGRESSO.match(c) else c for c in celulas]
            s = "|" + "|".join(celulas) + "|"
        s = re.sub(r"\s+", " ", s)
        if s:
            linhas.append(s)
    return "\n".join(linhas)


def digest_da_spec(spec: str) -> str | None:
    p = arquivo_da_spec(spec)
    if p is None:
        return None
    try:
        return hashlib.sha256(contrato_da_spec(p.read_text(encoding="utf-8")).encode("utf-8")).hexdigest()
    except OSError:
        return None


def selar_spec(d: dict, momento: str) -> None:
    """Grava o digest do contrato da SPEC. Sem arquivo, grava None e avisa uma vez."""
    dig = digest_da_spec(d["spec"])
    d["spec_digest"] = dig
    d["spec_selada_em"] = agora()
    d["spec_selada_por"] = momento
    if dig is None:
        print(f"   ⚠️  SPEC {d['spec']} não encontrada em {PASTA_SPECS}/ — sem digest, "
              "alteração da SPEC depois da aprovação não será detectada.", file=sys.stderr)


def spec_alterada(d: dict) -> bool | None:
    """True se o contrato da SPEC mudou desde o selo; None sem selo ou sem arquivo."""
    selo = d.get("spec_digest")
    if not selo:
        return None
    atual = digest_da_spec(d["spec"])
    if atual is None:
        return None
    return atual != selo


def branch_atual() -> str | None:
    """A branch em que o ciclo nasce. O guardrail julga o `gh pr create` pelos ciclos da
    branch atual; sem ela, com dois ciclos abertos, o PR do que está pronto esperava o
    outro sair do gate."""
    try:
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    nome = r.stdout.strip()
    return nome if r.returncode == 0 and nome and nome != "HEAD" else None


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
        "branch": branch_atual(),
        "orcamento": dict(orcamento),
        "teto": dict(teto),
        # `rodadas` são as fichas consumidas SEM progresso — progresso zera.
        "rodadas": {g: 0 for g in GATES},
        # `rodadas_totais` nunca zera; é o que o teto absoluto mede.
        "rodadas_totais": {g: 0 for g in GATES},
        # melhor (menor) contagem de achados já atingida no gate; None = sem marca.
        "marca": {g: None for g in GATES},
        # falhas seguidas do gate sem progresso e premissas já atacadas nessa sequência.
        "seguidas": {g: 0 for g in GATES},
        "premissas": {g: [] for g in GATES},
        "historico": [{"t": agora(), "de": None, "para": estado, "resultado": "abrir"}],
    }
    if spec_aprovada:
        selar_spec(d, "abrir --spec-aprovada")
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
    d.setdefault("seguidas", {})
    d.setdefault("premissas", {})
    for g in GATES:
        orc.setdefault(g, 2)
        d["rodadas"].setdefault(g, 0)
        d["teto"].setdefault(g, max(1, orc[g]) * FATOR_TETO)
        d["rodadas_totais"].setdefault(g, d["rodadas"][g])
        d["marca"].setdefault(g, None)
        d["seguidas"].setdefault(g, 0)
        d["premissas"].setdefault(g, [])
    return d


def _progrediu(d: dict, gate: str, bloqueios: int | None) -> bool:
    """Atualiza a melhor marca do gate e diz se a contagem caiu abaixo da anterior."""
    marca = d["marca"].get(gate)
    if bloqueios is not None and (marca is None or bloqueios < marca):
        d["marca"][gate] = bloqueios
    return bloqueios is not None and marca is not None and bloqueios < marca


def zerar_sequencia(d: dict, gate: str) -> None:
    d["seguidas"][gate] = 0
    d["premissas"][gate] = []


def decidir_orcamento(d: dict, gate: str, bloqueios: int | None) -> tuple[str, str | None]:
    """Decide destino e motivo de escalação quando o gate falhou. Muta o estado.

    Ordem deliberada — o teto vem antes do progresso porque progresso não compra
    rodadas infinitas: uma feature que baixa de 40 bloqueios para 39 a cada rodada
    está "progredindo" e mesmo assim precisa de gente.
    """
    d["rodadas_totais"][gate] += 1
    if d["rodadas_totais"][gate] >= d["teto"][gate]:
        return "escalado", (f"teto absoluto de {gate} atingido "
                            f"({d['rodadas_totais'][gate]}/{d['teto'][gate]} rodadas)")

    if _progrediu(d, gate, bloqueios):
        d["rodadas"][gate] = 0  # ficha devolvida
        zerar_sequencia(d, gate)  # convergindo: não é a mesma premissa falhando
        return CORRIGIR[gate], None

    if d["rodadas"][gate] >= d["orcamento"][gate]:
        estagnado = "" if bloqueios is None else f", parado em {bloqueios} bloqueio(s)"
        return "escalado", (f"orçamento de {gate} esgotado sem progresso "
                            f"({d['rodadas'][gate]}/{d['orcamento'][gate]} rodadas{estagnado})")

    d["rodadas"][gate] += 1
    d["seguidas"][gate] += 1
    atacar = d["seguidas"][gate] >= LIMIAR_PREMISSA
    return (ATACAR_PREMISSA[gate] if atacar else CORRIGIR[gate]), None


def _recusa_do_verde(d: dict, estado: str, gate: str, leitura: tuple) -> str | None:
    """Por que um resultado verde não pode ser registrado agora — ou None se pode.

    Veredicto vem do artefato, não da palavra do agente.
    """
    veredicto, _, fonte, erro_bloco = leitura
    pasta = FONTE_DO_GATE[gate][0]
    if estado != "criticando" and spec_alterada(d):
        return (f"🛑 recusado: o contrato da SPEC {d['spec']} mudou depois da aprovação "
                f"(requisito, critério, prioridade ou plano — Status e Verificação não "
                f"contam).\n   Resultado verde contra contrato que se moveu é o "
                f"`verificado:` pelo avesso. Mostre o diff da SPEC ao usuário e, se ele "
                f"aceitar a versão nova, rode `ciclo.py reaprovar {d['spec']}`; senão, "
                f"volte a SPEC.")
    if fonte == "invalido":
        return (f"🛑 recusado: o relatório mais recente de {d['spec']} em {pasta}/ tem um "
                f"bloco ```{FENCE_DO_GATE[gate]} que o parser recusa "
                f"{erro_bloco}.\n   A linha `**Veredicto:**` não substitui bloco "
                "inválido (ADR-0032). Corrija o bloco — ou o relatório, se ele diz "
                "limpo sem a lista do que foi examinado — e registre de novo.")
    if veredicto == "bloqueado":
        return (f"🛑 recusado: o relatório mais recente de {d['spec']} em {pasta}/ diz "
                f"BLOQUEADO.\n   Registre o resultado negativo e corrija, ou rode o gate "
                "de novo.")
    if veredicto is None:
        return (f"🛑 recusado: não encontrei relatório em {pasta}/ para {d['spec']}.\n"
                f"   Rode o gate e salve o relatório antes de registrar o resultado.")
    return None


def _recusa_da_premissa(d: dict, estado: str, nota: str | None) -> str | None:
    """A premissa é uma frase de verdade e não é a mesma já atacada nesta sequência."""
    gate = GATE_DA_PREMISSA[estado]
    premissa = " ".join((nota or "").split())
    if len(premissa) < TAMANHO_MINIMO_PREMISSA:
        return ("🛑 recusado: escreva a premissa em uma frase com `--nota \"...\"` — a "
                "suposição que as correções que falharam compartilharam. Sem ela, a "
                "próxima correção repete as anteriores.")
    if premissa.casefold() in (p.casefold() for p in d["premissas"][gate]):
        return ("🛑 recusado: essa premissa já foi atacada nesta sequência e a correção "
                "falhou de novo. Mesma premissa, mesma correção: procure a suposição que "
                "ainda não foi questionada.")
    d["premissas"][gate].append(premissa)
    return None


def _recusa(d: dict, estado: str, resultado: str, gate: str | None, leitura: tuple,
            nota: str | None) -> str | None:
    if resultado in LIMPO_DO_GATE.get(estado, ()):
        return _recusa_do_verde(d, estado, gate, leitura)
    if estado in GATE_DA_PREMISSA:
        return _recusa_da_premissa(d, estado, nota)
    return None


def _depois_de_registrar(d: dict, estado: str, resultado: str, gate: str | None) -> None:
    """Efeitos que dependem do que acabou de acontecer, fora da transição em si."""
    if d["estado"] == "construindo" and estado != "construindo":
        selar_spec(d, f"registrar {resultado}")
    if resultado in LIMPO_DO_GATE.get(estado, ()):
        zerar_sequencia(d, gate)  # gate verde encerra a sequência de falhas


def _avisar_fonte(gate: str | None, fonte: str, erro_bloco: str | None, destino: str) -> None:
    if not gate or destino in TERMINAIS:
        return
    if fonte == "prosa":
        print("\n   ⚠️  Relatório sem bloco de contrato — sem contagem de achados, toda "
              f"rodada queima ficha.\n       Adicione o bloco ```{FENCE_DO_GATE[gate]}"
              " para que progresso conte (ADR-0032).", file=sys.stderr)
    if fonte == "invalido":
        print(f"\n   ⚠️  O bloco ```{FENCE_DO_GATE[gate]} do relatório foi recusado "
              f"{erro_bloco} — sem contagem, esta rodada queima ficha.\n       Corrija o "
              "bloco antes da próxima rodada (ADR-0032).", file=sys.stderr)


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

    gate_do_estado = {"criticando": "criticar", "validando": "validar",
                      "revisando": "revisar"}.get(estado)
    leitura = (ler_relatorio(d["spec"], gate_do_estado) if gate_do_estado
               else (None, None, "ausente", None))
    _, contagem, fonte, erro_bloco = leitura
    recusa = _recusa(d, estado, resultado, gate_do_estado, leitura, nota)
    if recusa:
        print(recusa, file=sys.stderr)
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
    _depois_de_registrar(d, estado, resultado, gate_do_estado)
    gravar(p, d)
    imprimir(d)
    _avisar_fonte(gate_do_estado, fonte, erro_bloco, destino)
    return 0


def reaprovar(spec: str | None) -> int:
    """O humano aceitou a SPEC alterada: sela o digest novo e registra no histórico."""
    p = resolver(spec)
    d = compatibilizar(ler(p))
    if d["estado"] in TERMINAIS:
        print(f"🛑 ciclo em estado terminal '{d['estado']}' — nada a reaprovar.", file=sys.stderr)
        return 1
    if not d.get("spec_digest"):
        # Achado da POC do MHL (docs/pocs): reaprovar antes da aprovação selava um digest
        # que ainda não era contrato. Antes de `construindo` a SPEC é rascunho — quem a
        # aceita é `registrar aprovada` (ou `abrir --spec-aprovada`), não este comando.
        print(f"🛑 nada a reaprovar: a SPEC {d['spec']} ainda não foi aprovada "
              f"(estado '{d['estado']}', sem digest selado).\n   O selo nasce em "
              "`registrar aprovada` ou `abrir --spec-aprovada`; `reaprovar` só existe "
              "para aceitar mudança DEPOIS disso.", file=sys.stderr)
        return 1
    anterior = d.get("spec_digest")
    selar_spec(d, "reaprovar")
    d["historico"].append({"t": agora(), "de": d["estado"], "para": d["estado"],
                           "resultado": "reaprovar",
                           "digest_anterior": (anterior or "")[:12] or None,
                           "digest": (d["spec_digest"] or "")[:12] or None})
    gravar(p, d)
    print(f"✍️  {d['spec']} reaprovada — contrato selado em {(d['spec_digest'] or '—')[:12]}. "
          "Decisão humana registrada no histórico.")
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
    if spec_alterada(d) and e not in TERMINAIS:
        print(f"   ⚠️  SPEC alterada desde a aprovação (selo {d['spec_digest'][:12]}, "
              f"{d.get('spec_selada_por', '?')}). Resultado verde de gate será recusado "
              f"até `ciclo.py reaprovar {d['spec']}` — decisão do humano.")
    print(f"\n   PRÓXIMO PASSO: {INSTRUCAO[e]}")


def vista_publica(d: dict) -> dict:
    """O estado como o contrato promete (ADR-0034). Campos derivados, nunca gravados.

    `terminal`, `aguardando_humano`, `gate` e `resultados_validos` saem daqui em vez
    de o consumidor deduzir do nome do estado — string comparada por fora vira
    acoplamento que quebra no dia em que um estado é renomeado.
    """
    e = d["estado"]
    return {
        **d,
        "contrato": CONTRATO_VERSAO,
        "estado": e,
        "terminal": e in TERMINAIS,
        "aguardando_humano": e.startswith("aguardando_"),
        "gate": {"criticando": "criticar", "validando": "validar",
                 "revisando": "revisar"}.get(e),
        "proximo_passo": INSTRUCAO[e],
        "resultados_validos": sorted(TRANSICOES.get(e, {})),
        "spec_alterada": spec_alterada(d),
    }


def estado(spec: str | None, como_json: bool) -> int:
    p = resolver(spec)
    d = compatibilizar(ler(p))
    if como_json:
        print(json.dumps(vista_publica(d), ensure_ascii=False, indent=2))
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
    if cmd == "reaprovar":
        return reaprovar(resto[0] if resto else None)
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
    if cmd == "contrato":
        print(json.dumps(contrato_publico(), ensure_ascii=False, indent=2))
        return 0

    print(__doc__.strip())
    return 1


if __name__ == "__main__":
    sys.exit(main())
