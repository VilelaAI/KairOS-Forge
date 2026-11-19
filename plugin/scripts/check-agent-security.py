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
     (download-e-executa, `eval` de entrada não confiável): em `hooks/hooks.json`,
     `.codex/hooks.json`, `.cursor/hooks.json` e no bloco `hooks` de
     `.claude/settings.json` e `.claude/settings.local.json`.

  3. Segredos hardcoded
     Varre os arquivos versionados do plugin atrás de chaves/tokens/credenciais
     que nunca deveriam estar no repositório.

  4. Identidade da fábrica
     Workflow da fábrica (que cita `kairos-forge`) não age com o token de uma pessoa:
     um `secrets.*PAT*` ou `secrets.GH_TOKEN` dá ao agente toda a escrita que a pessoa
     tem, e revogar o agente é revogar a pessoa. O certo é o app da fábrica
     (`vars.FORGE_APP_ID`) ou o token do workflow. Olha `.github/workflows/` e
     `templates/ci/`; apontado para o `.claude` de um projeto, olha os workflows dele.

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


SETTINGS_DO_CLAUDE = ("settings.json", "settings.local.json")


def arquivos_de_hook(raiz: Path) -> list[tuple[Path, bool]]:
    """Cada arquivo que liga comando de shell a um evento, e se só o bloco `hooks` dele conta.

    `hooks/hooks.json` (plugin), `.codex/hooks.json` e `.cursor/hooks.json` são inteiros de
    hook. Num `.claude/settings*.json`, só o bloco `hooks` roda como hook: o resto é
    permissão e variável, e um `deny` de `curl | sh` é proteção, não risco. Apontado para o
    `.claude` de um projeto, olha os settings ali e o Codex e o Cursor da pasta do projeto."""
    inteiros = [raiz / "hooks" / "hooks.json", raiz / ".codex" / "hooks.json",
                raiz / ".cursor" / "hooks.json"]
    settings = [raiz / ".claude" / nome for nome in SETTINGS_DO_CLAUDE]
    if raiz.name == ".claude":                       # `check-agent-security.py .claude`
        inteiros += [raiz.parent / ".codex" / "hooks.json", raiz.parent / ".cursor" / "hooks.json"]
        settings += [raiz / nome for nome in SETTINGS_DO_CLAUDE]
    return [(arq, False) for arq in inteiros] + [(arq, True) for arq in settings]


def texto_de_hook(arq: Path, so_o_bloco: bool) -> str | None:
    """O texto em que os padrões são procurados; None num settings sem bloco `hooks`.
    Settings ilegível é varrido inteiro: melhor um achado a mais que um hook sem olhar. Byte
    fora de UTF-8 vira U+FFFD, como o Claude Code lê, em vez de derrubar a auditoria. O bloco
    volta com um item por linha, como o arquivo gravado com indentação: os padrões param no fim
    da linha, e o `curl` de um comando não se junta ao `| sh` de outro."""
    texto = arq.read_text(encoding="utf-8", errors="replace")
    if not so_o_bloco:
        return texto
    try:
        cfg = json.loads(texto)
    except ValueError:
        return texto
    if not isinstance(cfg, dict):
        return texto
    bloco = cfg.get("hooks")
    return json.dumps(bloco, ensure_ascii=False, indent=2) if bloco else None


def checar_hooks(raiz: Path) -> int:
    n = 0
    for arq, so_o_bloco in arquivos_de_hook(raiz):
        if not arq.is_file():
            continue
        texto = texto_de_hook(arq, so_o_bloco)
        if texto is None:
            continue
        n += 1
        nome = rel(raiz, arq)
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


# --- 4. identidade da fábrica -------------------------------------------------------

SECRET_CITADO = re.compile(r"secrets\.([A-Za-z0-9_]+)")
TOKEN_DE_PESSOA = re.compile(r"(^|_)(PAT|PERSONAL|PESSOAL)(_|$)|^GH_TOKEN$|^GITHUB_PAT$", re.I)


def pastas_de_workflow(raiz: Path) -> list[Path]:
    pastas = [raiz / ".github" / "workflows", raiz / "templates" / "ci"]
    if raiz.name == ".claude":                       # `check-agent-security.py .claude`
        pastas.append(raiz.parent / ".github" / "workflows")
    return [d for d in pastas if d.is_dir()]


def checar_identidade(raiz: Path) -> int:
    n = 0
    for arq in sorted(a for d in pastas_de_workflow(raiz) for a in d.glob("*.y*ml")):
        texto = arq.read_text(encoding="utf-8", errors="replace")
        if "kairos-forge" not in texto:
            continue
        n += 1
        for nome in sorted({m for m in SECRET_CITADO.findall(texto) if TOKEN_DE_PESSOA.search(m)}):
            registrar(MEDIA, "identidade da fábrica",
                      f"{rel(raiz, arq)}: usa `secrets.{nome}`, que parece token de pessoa — use o "
                      "app da fábrica (vars.FORGE_APP_ID) ou o github.token "
                      "(docs/identidade-do-agente.md)")
    return n


# --- relatório -----------------------------------------------------------------------

def main(argv: list[str]) -> int:
    raiz = resolver_raiz(argv)
    print(f"🛡️  check-agent-security — auditando: {raiz}\n")

    n_ag = checar_agentes(raiz)
    n_hk = checar_hooks(raiz)
    n_sg = checar_segredos(raiz)
    n_wf = checar_identidade(raiz)

    print(f"Cobertura: {n_ag} agentes · {n_hk} arquivos de hook · {n_sg} arquivos varridos por "
          f"segredos · {n_wf} workflows da fábrica\n")

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
