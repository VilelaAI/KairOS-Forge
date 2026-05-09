#!/usr/bin/env python3
"""sync-multi-cli.py — Sincroniza subagents do Claude Code para o formato Codex.

Skills (`skills/<nome>/SKILL.md`) são compartilhadas entre Claude Code e Codex
sem necessidade de duplicação — ambos os CLIs leem a mesma pasta quando
empacotados como plugin. Apenas os SUBAGENTS têm formato distinto:

    Claude Code:  agents/<id>.md
    Codex CLI:    .agents/<id>/AGENT.md

Este script copia os subagents do formato Claude Code para o formato Codex.

Uso:
    python3 scripts/sync-multi-cli.py

Roda este script sempre que mudar arquivos em agents/. O resultado é commitado
no git. Usuário final do Codex CLI pega os arquivos prontos no install.

NÃO modifica:
    - agents/ (canônico do Claude Code)
    - skills/ (compartilhado entre Claude Code e Codex)
    - hooks/hooks.json (Claude Code) — Codex usa .codex/hooks.json
    - .codex-plugin/plugin.json (manifest Codex, mantido manual)
    - .agents/plugins/marketplace.json (marketplace, mantido manual)
"""
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parent.parent
AGENTS_SRC = ROOT / "agents"
CODEX_DIR = ROOT / ".agents"
PRESERVAR = {"plugins"}  # subdir mantido (marketplace.json fica em .agents/plugins/)


def limpar_subagents_codex():
    """Remove apenas as pastas de subagent em .agents/, preservando outras (plugins/)."""
    if not CODEX_DIR.exists():
        CODEX_DIR.mkdir()
        return
    for item in CODEX_DIR.iterdir():
        if item.is_dir() and item.name not in PRESERVAR:
            shutil.rmtree(item)


def sincronizar_subagents():
    """Copia agents/<id>.md → .agents/<id>/AGENT.md (formato Codex)."""
    contagem = 0
    for agent_md in AGENTS_SRC.glob("*.md"):
        nome = agent_md.stem
        target_dir = CODEX_DIR / nome
        target_dir.mkdir()
        shutil.copy2(agent_md, target_dir / "AGENT.md")
        contagem += 1
    return contagem


def main() -> int:
    if not AGENTS_SRC.exists():
        print(f"❌ agents/ não encontrado em {ROOT}", file=sys.stderr)
        return 1

    print(f"📂 root: {ROOT}")
    print("🧹 limpando subagents antigos em .agents/ (preservando plugins/)...")
    limpar_subagents_codex()

    print("👥 sincronizando subagents (Claude Code → Codex)...")
    n = sincronizar_subagents()
    print(f"  ✓ {n} subagents copiados como .agents/<id>/AGENT.md")

    print(f"\n✅ {n} arquivos sincronizados em .agents/")
    print("\nLembre-se de commitar .agents/ no git para que usuários do Codex CLI peguem os arquivos prontos.")
    print("\nNota: skills/ é compartilhado — Codex e Claude Code leem da mesma pasta quando empacotado como plugin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
