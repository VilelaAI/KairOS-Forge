#!/usr/bin/env python3
"""check-agent-security — auditoria de segurança do próprio setup da fábrica.

Inspirado no AgentShield do ECC (Everything Claude Code), mas em escopo MIT/genérico:
NÃO audita o código do cliente (isso é trabalho de `analisar-ameacas` e `revisar`).
Audita a *configuração do plugin* — os riscos que nascem de como a fábrica é montada.

Verifica três classes de risco:

  1. Allow-list de ferramentas dos agentes
     O CLAUDE.md exige `tools:` explícito em todo agente ("Nunca dar acesso total").
     Aqui isso vira check automático: falha se algum agente não tem `tools:`,
     tem `tools:` vazio, ou usa curinga (`*`, `all`).

  2. Injeção em hooks
     Hooks rodam comandos de shell. Sinaliza padrões perigosos em comandos de hook
     (download-e-executa, `eval` de entrada não confiável).

  3. Segredos hardcoded
     Varre os arquivos versionados do plugin atrás de chaves/tokens/credenciais
     que nunca deveriam estar no repositório.

Uso:
    python3 scripts/check-agent-security.py [RAIZ]

RAIZ default = diretório que contém este script (../). Sai com código 1 se houver
qualquer achado de severidade ALTA — pronto para CI ou pre-commit.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# --- localização da árvore a auditar -------------------------------------------------

def resolver_raiz(argv: list[str]) -> Path:
    if len(argv) > 1:
        return Path(argv[1]).resolve()
    # scripts/ fica na raiz da árvore (raiz/ ou plugin/)
    return Path(__file__).resolve().parent.parent


# --- modelo de achado ----------------------------------------------------------------

ALTA, MEDIA, BAIXA = "ALTA", "MEDIA", "BAIXA"
_ORDEM = {ALTA: 0, MEDIA: 1, BAIXA: 2}

achados: list[tuple[str, str, str]] = []  # (severidade, regra, detalhe)


def registrar(sev: str, regra: str, detalhe: str) -> None:
    achados.append((sev, regra, detalhe))


def rel(raiz: Path, p: Path) -> str:
    try:
        return str(p.relative_to(raiz))
    except ValueError:
        return str(p)


# --- 1. allow-list de ferramentas dos agentes ----------------------------------------

CURINGAS = {"*", "all", "todas", "todos", "any", "*.*"}


def extrair_frontmatter(texto: str) -> dict[str, str]:
    """Lê o bloco frontmatter YAML simples (chave: valor por linha)."""
    if not texto.startswith("---"):
        return {}
    fim = texto.find("\n---", 3)
    if fim == -1:
        return {}
    campos: dict[str, str] = {}
    for linha in texto[3:fim].splitlines():
        if ":" in linha and not linha.lstrip().startswith("#"):
            chave, _, valor = linha.partition(":")
            campos[chave.strip()] = valor.strip()
    return campos


def checar_agentes(raiz: Path) -> int:
    pasta = raiz / "agents"
    if not pasta.is_dir():
        return 0
    n = 0
    for arq in sorted(pasta.glob("*.md")):
        n += 1
        fm = extrair_frontmatter(arq.read_text(encoding="utf-8"))
        nome = rel(raiz, arq)
        tools = fm.get("tools")
        if tools is None:
            registrar(ALTA, "allow-list ausente", f"{nome}: sem campo `tools:` no frontmatter")
            continue
        tools_limpo = tools.strip().strip("[]").strip()
        if not tools_limpo:
            registrar(ALTA, "allow-list vazia", f"{nome}: `tools:` está vazio (= acesso indefinido)")
            continue
        itens = {t.strip().strip("'\"").lower() for t in tools_limpo.split(",") if t.strip()}
        curinga = itens & CURINGAS
        if curinga:
            registrar(ALTA, "allow-list curinga", f"{nome}: `tools:` usa curinga {sorted(curinga)} — proibido pelo CLAUDE.md")
    return n


# --- 2. injeção em hooks -------------------------------------------------------------

PADROES_HOOK = [
    (re.compile(r"curl[^\n|]*\|\s*(ba)?sh", re.I), "download-e-executa (curl | sh) em hook"),
    (re.compile(r"wget[^\n|]*\|\s*(ba)?sh", re.I), "download-e-executa (wget | sh) em hook"),
    (re.compile(r"\beval\b", re.I), "uso de `eval` em comando de hook"),
]


def comandos_de_hook(dados) -> list[str]:
    """Extrai só os `command` de dentro de um bloco `hooks` (recursivo)."""
    achados: list[str] = []
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            if chave == "command" and isinstance(valor, str):
                achados.append(valor)
            else:
                achados.extend(comandos_de_hook(valor))
    elif isinstance(dados, list):
        for item in dados:
            achados.extend(comandos_de_hook(item))
    return achados


def checar_hooks(raiz: Path) -> int:
    n = 0
    # No Kiro os hooks moram DENTRO da config de cada agente (ADR-0035) — sem
    # incluí-las aqui, 71 arquivos com comando de shell ficariam fora da varredura
    # de injeção, e a cobertura relatada diria "2 arquivos" achando que cobriu tudo.
    #
    # Nesses arquivos varremos APENAS os comandos de hook, nunca o texto inteiro:
    # a persona ocupa quase todo o arquivo, e a Alice (evals) e a Laura (que roteia
    # para evals) escrevem "eval" em prosa. Varrer o corpo acusaria as duas por
    # falarem do próprio trabalho — e alarme falso treina o time a ignorar alarme.
    candidatos = [raiz / "hooks" / "hooks.json", raiz / ".codex" / "hooks.json"]
    candidatos += sorted((raiz / ".kiro" / "agents").glob("*.json"))
    for arq in candidatos:
        if not arq.is_file():
            continue
        n += 1
        nome = rel(raiz, arq)
        texto = arq.read_text(encoding="utf-8")
        if arq.parent.name == "agents":
            try:
                cfg = json.loads(texto)
            except ValueError:
                registrar(MEDIA, "injeção em hook", f"{nome}: JSON inválido — não auditado")
                continue
            texto = "\n".join(comandos_de_hook(cfg.get("hooks", {})))
        for regex, descricao in PADROES_HOOK:
            if regex.search(texto):
                registrar(MEDIA, "injeção em hook", f"{nome}: {descricao}")
    return n


# --- 3. segredos hardcoded -----------------------------------------------------------

PADROES_SEGREDO = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "chave de acesso AWS"),
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"), "chave Anthropic"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "token pessoal GitHub"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{22,}"), "fine-grained PAT GitHub"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "chave privada"),
    (re.compile(r"""(?i)(api[_-]?key|secret|token|password|passwd)\s*[=:]\s*['"][A-Za-z0-9_\-]{16,}['"]"""), "credencial atribuída a literal"),
]

# valores de exemplo/placeholder que NÃO são segredos reais
PLACEHOLDERS = re.compile(r"(?i)(exemplo|example|placeholder|your[_-]?|seu[_-]?|xxx+|<.*>|\.\.\.|sk-ant-xxxx|fake|dummy|test)")

EXT_VARRER = {".md", ".json", ".toml", ".py", ".yaml", ".yml", ".sh", ".js", ".ts"}
IGNORAR_DIRS = {".git", "node_modules", "__pycache__"}


def checar_segredos(raiz: Path) -> int:
    n = 0
    for arq in raiz.rglob("*"):
        if not arq.is_file() or arq.suffix not in EXT_VARRER:
            continue
        if any(parte in IGNORAR_DIRS for parte in arq.parts):
            continue
        # não acusar o próprio script de detecção (contém os regex)
        if arq.resolve() == Path(__file__).resolve():
            continue
        n += 1
        try:
            texto = arq.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for regex, descricao in PADROES_SEGREDO:
            for m in regex.finditer(texto):
                trecho = m.group(0)
                if PLACEHOLDERS.search(trecho):
                    continue
                registrar(ALTA, "segredo hardcoded", f"{rel(raiz, arq)}: possível {descricao} — '{trecho[:24]}…'")
    return n


# --- relatório -----------------------------------------------------------------------

def main(argv: list[str]) -> int:
    raiz = resolver_raiz(argv)
    print(f"🛡️  check-agent-security — auditando: {raiz}\n")

    n_ag = checar_agentes(raiz)
    n_hk = checar_hooks(raiz)
    n_sg = checar_segredos(raiz)

    print(f"Cobertura: {n_ag} agentes · {n_hk} arquivos de hook · {n_sg} arquivos varridos por segredos\n")

    if not achados:
        print("✅ Nenhum risco encontrado. Setup da fábrica está seguro.")
        return 0

    achados.sort(key=lambda a: _ORDEM[a[0]])
    icone = {ALTA: "🔴", MEDIA: "🟡", BAIXA: "🔵"}
    for sev, regra, detalhe in achados:
        print(f"{icone[sev]} [{sev}] {regra}: {detalhe}")

    altas = sum(1 for s, _, _ in achados if s == ALTA)
    print(f"\n{len(achados)} achado(s) — {altas} de severidade ALTA.")
    if altas:
        print("Falhando (exit 1): achados ALTA bloqueiam. Corrija antes de commitar.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
