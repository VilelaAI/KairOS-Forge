#!/usr/bin/env python3
"""guardrail.py — guardrails determinísticos da fábrica (ADR-0022).

O whitepaper Day-1 define hooks como *"deterministic code that runs at specific
lifecycle points... the place for things the agent should never forget but often
does"*. Até a v0.17 os hooks do kairos-forge só imprimiam texto: o PostToolUse
sugeria lembrar do Ricardo e não impedia nada. As regras duras da fábrica moravam
todas em prosa que o modelo pode driftar — a inversão exata do que o paper
recomenda.

Este script é a parte que **bloqueia**. Três classes de risco:

  1. Comando destrutivo      — apagar a raiz, force-push em branch protegida,
                               DROP/TRUNCATE fora de migration, curl|sh, chmod 777
  2. Arquivo protegido       — segredos, config de CI, e os dois arquivos que o
                               agente NUNCA pode escrever (ver "Goodhart" abaixo)
  3. Integridade da SPEC     — status "Concluído" sem célula `verificado:`

## Goodhart: o agente não escreve o próprio medidor

Dois caminhos são bloqueados sem possibilidade de configuração:

    .agents/execucoes/**    a trajetória que o /validar usa para corroborar
    .agents/guardrails.json a configuração destes próprios guardrails

É o mesmo princípio que o `/kairos-forge:otimizar` já aplica ("a métrica é
sagrada — otimizar o medidor é o modo de falha clássico"), aplicado ao harness.
Corroboração que o agente pode reescrever não corrobora nada, e guardrail que o
agente pode afrouxar não guarda nada. Quem edita esses dois arquivos é o humano.

## Modos

Hook (payload do hook em stdin, exit 2 = bloqueia e o motivo vai para o modelo):

    guardrail.py comando    # PreToolUse  matcher Bash
    guardrail.py escrita    # PreToolUse  matcher Write|Edit
    guardrail.py spec       # PostToolUse matcher Write|Edit

CLI, sem hook — o caminho para Codex/OpenCode/Cursor e para CI/pre-commit,
onde não existe PreToolUse (exit 1 se houver achado):

    guardrail.py verificar [CAMINHO]

## Configuração (opcional)

`.agents/guardrails.json` no projeto:

    {
      "protegidos":      ["infra/terraform/**"],   // além dos defaults
      "comandos_extra":  ["kubectl delete"],       // regex, além dos defaults
      "liberados":       [".github/workflows/**"]  // abre mão de um default
    }

Só stdlib.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- 1. comandos destrutivos --------------------------------------------------------
# Precisão importa mais que cobertura: guardrail com falso positivo é guardrail que o
# usuário desliga, e aí não guarda nada. `rm -rf node_modules` passa; `rm -rf /` não.
COMANDOS = [
    (r"\brm\s+(-\w+\s+)*-\w*[rf]\w*\s+(/|~|\$HOME|/\*|~/\*)(\s|$|;)",
     "apagar a raiz do sistema ou o home inteiro"),
    (r"\bgit\s+push\b.*(--force|-f)\b(?!.*--force-with-lease).*\b(main|master|develop|production|prod)\b",
     "force-push em branch protegida (use --force-with-lease em branch própria)"),
    (r"\bgit\s+push\b.*\b(origin\s+)?(main|master|production|prod)\b.*(--force|-f)\b",
     "force-push em branch protegida"),
    (r"(?i)\bdrop\s+(table|database|schema)\b", "DROP de tabela/banco/schema"),
    (r"(?i)\btruncate\s+table\b", "TRUNCATE de tabela"),
    (r"(?i)\bdelete\s+from\s+\w+\s*(;|'|\"|`|$)", "DELETE sem WHERE"),
    (r"\b(curl|wget)\b[^|;]*\|\s*(sudo\s+)?(ba|z|k)?sh\b",
     "baixar-e-executar (curl|sh) — vetor de supply chain"),
    (r"\bchmod\s+(-\w+\s+)*777\b", "chmod 777"),
    (r"(?i)\b(cat|dotenv|source)\b[^;|]*\.env\b[^;]*\|\s*(curl|nc|wget)",
     "exfiltração de .env por rede"),
    (r"\bgit\s+checkout\s+(.*\s)?--\s+\.(\s|$)", "descartar TODAS as mudanças não commitadas"),
]

# --- 2. arquivos protegidos ---------------------------------------------------------
# Inegociáveis: o agente não escreve o próprio medidor nem a própria regra.
SAGRADOS = [
    (".agents/execucoes/**", "a trajetória que o /kairos-forge:validar usa para corroborar evidência"),
    (".agents/guardrails.json", "a configuração destes guardrails"),
    (".agents/ciclo/**", "o estado da máquina do arco /kairos-forge:entregar (ADR-0029)"),
]

# --- 4. abertura de PR fora de estado (ADR-0029) -------------------------------------
ABRE_PR = re.compile(r"\bgh\s+pr\s+create\b")
FECHA_PR = re.compile(r"\bgh\s+pr\s+merge\b")

PROTEGIDOS_PADRAO = [
    (".env", "arquivo de segredos"),
    (".env.*", "arquivo de segredos"),
    ("**/*.pem", "chave privada"),
    ("**/*.key", "chave privada"),
    ("**/id_rsa*", "chave SSH"),
    (".github/workflows/**", "configuração de CI — mexer nos próprios gates é Goodhart"),
]

# Casam com um padrão protegido mas existem para ser versionados e editados.
EXCECOES = ["*.example", "*.sample", "*.template", "*.dist", "*.md"]

# --- 3. integridade da SPEC ---------------------------------------------------------
LINHA_TABELA = re.compile(r"^\s*\|.*\|\s*$")


def carregar_config(raiz: Path) -> dict:
    arq = raiz / ".agents" / "guardrails.json"
    if not arq.is_file():
        return {}
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except Exception:
        return {}


# --- modo por classe de regra (ADR-0030) --------------------------------------------
# Regra que falha demais é regra que o time desliga na semana seguinte. `aviso` deixa
# a regra rodar e medir antes de morder; `bloqueio` é o default e o destino.
# Promoção não é por gosto: migre para `bloqueio` quando a taxa de aviso cair — o
# `telemetria.py resumo` mostra o número.
MODO_PADRAO = "bloqueio"


def modo_de(cfg: dict, classe: str) -> str:
    modo = (cfg.get("modos", {}) or {}).get(classe) or cfg.get("modo") or MODO_PADRAO
    return modo if modo in ("bloqueio", "aviso") else MODO_PADRAO


def registrar_recusa(raiz: Path, classe: str, regra: str, alvo: str, modo: str) -> None:
    """Grava a tentativa na trajetória.

    O bloqueio funcionou e o agente segue em frente — mas *ter tentado* é sinal, e sinal
    que não é registrado não existe. Um agente que passa na validação alcançando ferramenta
    que não tem não está passando (ADR-0030).
    """
    try:
        pasta = raiz.resolve() / ".agents" / "execucoes"
        pasta.mkdir(parents=True, exist_ok=True)
        evento = {
            "t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sessao": (os.environ.get("CLAUDE_SESSION_ID") or "?")[:16],
            "tipo": "recusa",
            "classe": classe,
            "regra": regra[:120],
            "alvo": alvo[:200],
            "modo": modo,
        }
        with (pasta / f"{datetime.now(timezone.utc):%Y-%m}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(evento, ensure_ascii=False) + "\n")
    except Exception:
        pass  # registro nunca derruba o guardrail


def bloquear(motivo: str, detalhe: str, saida: str, modo: str = "bloqueio") -> int:
    """exit 2 bloqueia e manda o motivo ao modelo; exit 1 avisa e deixa passar."""
    if modo == "aviso":
        print(f"⚠️  kairos-forge (guardrail, modo aviso): {motivo}\n\n{detalhe}\n\n{saida}\n"
              "Esta regra está em observação — hoje ela avisa, não bloqueia.", file=sys.stderr)
        return 1
    print(f"🛑 kairos-forge (guardrail): {motivo}\n\n{detalhe}\n\n{saida}", file=sys.stderr)
    return 2


def relativo(caminho: str, raiz: Path) -> str:
    try:
        return str(Path(caminho).resolve().relative_to(raiz.resolve()))
    except Exception:
        return caminho


def casa(rel: str, padrao: str) -> bool:
    rel = rel.replace("\\", "/")
    if fnmatch.fnmatch(rel, padrao):
        return True
    # `dir/**` deve casar com o próprio dir e com tudo abaixo
    if padrao.endswith("/**") and (rel == padrao[:-3] or rel.startswith(padrao[:-2])):
        return True
    return False


# --- modo hook: comando -------------------------------------------------------------

def ciclo_aberto(raiz: Path) -> dict | None:
    """O ciclo do /entregar em andamento, se houver. None quando não há máquina rodando."""
    pasta = raiz / ".agents" / "ciclo"
    if not pasta.is_dir():
        return None
    for p in sorted(pasta.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("estado") not in ("encerrado", "escalado"):
            return d
    return None


def checar_comando(payload: dict) -> int:
    cmd = str((payload.get("tool_input") or {}).get("command") or "")
    if not cmd.strip():
        return 0
    raiz = Path(payload.get("cwd") or ".")
    cfg = carregar_config(raiz)

    # Abertura/merge de PR obedecem à máquina de estados, quando ela está rodando.
    ciclo = ciclo_aberto(raiz)
    if ciclo:
        if FECHA_PR.search(cmd):
            registrar_recusa(raiz, "ciclo", "merge durante ciclo aberto", cmd[:200], "bloqueio")
            return bloquear(
                "merge de PR bloqueado durante um ciclo do /kairos-forge:entregar",
                f"Ciclo {ciclo['spec']} em '{ciclo['estado']}'.",
                "O arco termina no PR — a decisão de integrar é do dono do repositório "
                "(ADR-0023). Peça o merge ao usuário.",
            )
        if ABRE_PR.search(cmd) and ciclo.get("estado") != "pronto_para_pr":
            registrar_recusa(raiz, "ciclo", "PR fora de estado", cmd[:200], "bloqueio")
            return bloquear(
                f"abertura de PR fora de estado — o ciclo {ciclo['spec']} está em "
                f"'{ciclo['estado']}', não em 'pronto_para_pr'",
                f"Rodadas: validar {ciclo['rodadas']['validar']}/{ciclo['orcamento']['validar']} · "
                f"revisar {ciclo['rodadas']['revisar']}/{ciclo['orcamento']['revisar']}.",
                "PR com P1 bloqueado ou 🔴 aberto transfere para o revisor humano exatamente o "
                "trabalho que o arco existe para absorver. Rode `ciclo.py estado` e siga o "
                "próximo passo que ele indica.",
            )

    regras = list(COMANDOS) + [(r, "regra do projeto") for r in cfg.get("comandos_extra", [])]
    modo = modo_de(cfg, "comando")
    for padrao, motivo in regras:
        try:
            if re.search(padrao, cmd):
                registrar_recusa(raiz, "comando", motivo, cmd[:200], modo)
                return bloquear(
                    f"comando bloqueado — {motivo}",
                    f"Comando: {cmd[:300]}",
                    "Se for realmente necessário, peça ao usuário para executar. "
                    "Ação irreversível não roda em fluxo autônomo (ADR-0024).",
                    modo,
                )
        except re.error:
            continue
    return 0


# --- modo hook: escrita -------------------------------------------------------------

def checar_escrita(payload: dict) -> int:
    entrada = payload.get("tool_input") or {}
    caminho = str(entrada.get("file_path") or entrada.get("notebook_path") or "")
    if not caminho:
        return 0
    raiz = Path(payload.get("cwd") or ".")
    rel = relativo(caminho, raiz)
    cfg = carregar_config(raiz)
    liberados = cfg.get("liberados", [])

    # Sagrados NUNCA degradam para aviso: são o medidor e a regra. Guardrail que só
    # avisa sobre escrita no próprio medidor não é guardrail (ADR-0022).
    for padrao, motivo in SAGRADOS:
        if casa(rel, padrao):
            registrar_recusa(raiz, "sagrado", motivo, rel, "bloqueio")
            return bloquear(
                f"escrita bloqueada em `{rel}` — {motivo}",
                "Este caminho é inegociável: o agente não escreve o próprio medidor "
                "nem a própria regra. Corroboração que o agente reescreve não corrobora, "
                "e guardrail que o agente afrouxa não guarda.",
                "Quem edita este arquivo é o humano. Explique o que precisa mudar e por quê.",
            )

    if any(casa(rel, exc) or casa(Path(rel).name, exc) for exc in EXCECOES):
        return 0

    protegidos = list(PROTEGIDOS_PADRAO) + [
        (p, "protegido pelo projeto") for p in cfg.get("protegidos", [])
    ]
    modo = modo_de(cfg, "protegido")
    for padrao, motivo in protegidos:
        if casa(rel, padrao) and not any(casa(rel, lib) for lib in liberados):
            registrar_recusa(raiz, "protegido", motivo, rel, modo)
            return bloquear(
                f"escrita bloqueada em `{rel}` — {motivo}",
                "Caminho protegido por guardrail determinístico.",
                "Peça a mudança ao usuário, ou libere o caminho em "
                "`.agents/guardrails.json` (campo `liberados`) — o que o usuário edita, "
                "não você.",
                modo,
            )
    return 0


# --- modo hook: integridade da SPEC -------------------------------------------------

def linhas_incoerentes(texto: str) -> list[str]:
    """Linhas de tabela com Status 'Concluído' e Verificação sem `verificado:`.

    O ritual da fábrica: marcar pronto sem prova de execução é o anti-padrão que a
    coluna Verificação existe para impedir. Aqui isso vira check, não lembrete.
    """
    achados = []
    for linha in texto.splitlines():
        if not LINHA_TABELA.match(linha):
            continue
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        if len(celulas) < 2:
            continue
        if not any(c.lower() == "concluído" or c.lower() == "concluido" for c in celulas):
            continue
        if any(c.lower().startswith("verificado:") for c in celulas):
            continue
        achados.append(linha.strip()[:160])
    return achados


def checar_spec(payload: dict) -> int:
    entrada = payload.get("tool_input") or {}
    caminho = str(entrada.get("file_path") or "")
    if "docs/specs/" not in caminho.replace("\\", "/") or not caminho.endswith(".md"):
        return 0
    try:
        texto = Path(caminho).read_text(encoding="utf-8")
    except Exception:
        return 0
    achados = linhas_incoerentes(texto)
    if not achados:
        return 0
    raiz = Path(payload.get("cwd") or ".")
    modo = modo_de(carregar_config(raiz), "spec")
    registrar_recusa(raiz, "spec", "Concluído sem verificado:", caminho, modo)
    lista = "\n".join(f"  · {a}" for a in achados[:5])
    return bloquear(
        f"SPEC com status inconsistente — {len(achados)} requisito(s) marcado(s) "
        f"'Concluído' sem célula `verificado:`",
        f"Em {relativo(caminho, Path(payload.get('cwd') or '.'))}:\n{lista}",
        "Corrija agora: rode o gate e escreva `verificado: <como confirmei> (<dd/mm>)`, "
        "ou volte o status para 'Em progresso' com `em progresso: <o que falta>`. "
        "O /kairos-forge:validar trataria isso como 'sem evidência' e bloquearia P1.",
        modo,
    )


# --- modo CLI (Codex/OpenCode/Cursor, CI, pre-commit) -------------------------------

def verificar(alvo: Path) -> int:
    """Sem PreToolUse não há bloqueio prévio — então o mesmo contrato roda depois."""
    problemas: list[str] = []
    raiz = alvo if alvo.is_dir() else alvo.parent

    specs = sorted(raiz.rglob("docs/specs/*.md")) if alvo.is_dir() else (
        [alvo] if "docs/specs/" in str(alvo).replace("\\", "/") else []
    )
    for spec in specs:
        for linha in linhas_incoerentes(spec.read_text(encoding="utf-8")):
            problemas.append(f"{spec}: 'Concluído' sem `verificado:` — {linha}")

    for padrao, motivo in PROTEGIDOS_PADRAO[:5]:  # só os de segredo, não o de CI
        for achado in raiz.rglob(padrao.replace("**/", "")):
            if achado.is_file() and ".git/" not in str(achado):
                problemas.append(f"{achado}: {motivo} versionado no projeto?")

    if problemas:
        print(f"🛑 guardrail: {len(problemas)} achado(s)")
        for p in problemas:
            print(f"  ✗ {p}")
        return 1
    print("✅ guardrail: sem achados")
    return 0


MODOS = {"comando": checar_comando, "escrita": checar_escrita, "spec": checar_spec}


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__.strip())
        return 1

    if args[0] == "verificar":
        alvo = Path(args[1]) if len(args) > 1 else Path.cwd()
        return verificar(alvo)

    modo = MODOS.get(args[0])
    if modo is None:
        print(__doc__.strip())
        return 1
    try:
        bruto = sys.stdin.read()
        payload = json.loads(bruto) if bruto.strip() else {}
        return modo(payload)
    except Exception:
        # Guardrail quebrado nunca trava a sessão — falha aberta, mas silenciosa.
        # (Bloquear por bug próprio seria pior que a ausência do check.)
        return 0


if __name__ == "__main__":
    sys.exit(main())
