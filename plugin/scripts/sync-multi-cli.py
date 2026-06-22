#!/usr/bin/env python3
"""sync-multi-cli.py — Sincroniza subagents do Claude Code para o formato Codex
e espelha o conteúdo canônico do root para o diretório publicado `plugin/`.

Skills (`skills/<nome>/SKILL.md`) são compartilhadas entre Claude Code e Codex
sem necessidade de duplicação — ambos os CLIs leem a mesma pasta quando
empacotados como plugin. Apenas os SUBAGENTS têm formato distinto:

    Claude Code:  agents/<id>.md
    Codex CLI:    .agents/<id>/AGENT.md

Este script:
  1. Copia os subagents do formato Claude Code (agents/) para o formato Codex
     (.agents/<id>/AGENT.md), preservando .agents/plugins/marketplace.json.
  2. Espelha o conteúdo canônico do root para `plugin/` (cópia vendorizada que o
     marketplace publica via `source: ./plugin`). O root é a árvore de
     desenvolvimento/`--plugin-dir`; `plugin/` é a árvore publicada. As duas são
     mantidas em lockstep. O espelhamento copia só o que é IDÊNTICO entre as duas
     — README.md e os marketplace.json divergem e NÃO são tocados aqui.

Uso:
    python3 scripts/sync-multi-cli.py

Roda este script sempre que mudar arquivos em agents/ ou skills/. O resultado é
commitado no git (agents/, .agents/, skills/ e plugin/).

NÃO modifica (mantidos manualmente):
    - README.md (root = readme do marketplace; plugin/README.md = readme do plugin)
    - .claude-plugin/marketplace.json e .agents/plugins/marketplace.json (catalogs do root)
"""
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parent.parent
AGENTS_SRC = ROOT / "agents"
CODEX_DIR = ROOT / ".agents"
PLUGIN_DIR = ROOT / "plugin"
PRESERVAR = {"plugins"}  # subdir mantido (marketplace.json fica em .agents/plugins/)

# Espelhamento root -> plugin/. Só subtrees/arquivos IDÊNTICOS entre as duas árvores.
# NÃO inclui README.md (diverge) nem os marketplace.json (exclusivos do root).
# `.agents` não entra aqui — é regenerado a partir de plugin/agents (sem plugins/).
MIRROR_DIRS = ["agents", "skills", "templates", "docs", "hooks", ".codex", "scripts"]
MIRROR_FILES = [
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    "CLAUDE.md",
    "AGENTS.md",
]


def limpar_subagents_codex(codex_dir: Path):
    """Remove apenas as pastas de subagent em codex_dir, preservando outras (plugins/)."""
    if not codex_dir.exists():
        codex_dir.mkdir(parents=True)
        return
    for item in codex_dir.iterdir():
        if item.is_dir() and item.name not in PRESERVAR:
            shutil.rmtree(item)


def sincronizar_subagents(agents_src: Path, codex_dir: Path) -> int:
    """Copia <agents_src>/<id>.md → <codex_dir>/<id>/AGENT.md (formato Codex)."""
    contagem = 0
    for agent_md in sorted(agents_src.glob("*.md")):
        nome = agent_md.stem
        target_dir = codex_dir / nome
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(agent_md, target_dir / "AGENT.md")
        contagem += 1
    return contagem


def espelhar_para_plugin() -> None:
    """Espelha o conteúdo canônico root → plugin/ e regenera plugin/.agents.

    plugin/ é a cópia publicada no marketplace (source: ./plugin), mantida em
    lockstep com o root. Só o que é idêntico é espelhado — README.md e os
    marketplace.json divergem e ficam fora.
    """
    if not PLUGIN_DIR.exists():
        print("  (plugin/ não existe — pulando espelhamento)")
        return

    # config.toml em .codex/ é configuração LOCAL (pode conter chave de API de MCP) —
    # nunca espelhar para plugin/ (seria publicado no marketplace).
    ignorar = shutil.ignore_patterns("config.toml")
    for nome in MIRROR_DIRS:
        src = ROOT / nome
        if not src.exists():
            continue
        dst = PLUGIN_DIR / nome
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=ignorar)

    for rel in MIRROR_FILES:
        src = ROOT / rel
        if not src.exists():
            continue
        dst = PLUGIN_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # Regenera plugin/.agents a partir de plugin/agents (sem plugins/ — plugin não é marketplace).
    plugin_codex = PLUGIN_DIR / ".agents"
    if plugin_codex.exists():
        shutil.rmtree(plugin_codex)
    plugin_codex.mkdir(parents=True)
    n = sincronizar_subagents(PLUGIN_DIR / "agents", plugin_codex)
    print(f"  ✓ plugin/ espelhado ({', '.join(MIRROR_DIRS)} + manifests); {n} subagents em plugin/.agents")


def main() -> int:
    if not AGENTS_SRC.exists():
        print(f"❌ agents/ não encontrado em {ROOT}", file=sys.stderr)
        return 1

    print(f"📂 root: {ROOT}")
    print("🧹 limpando subagents antigos em .agents/ (preservando plugins/)...")
    limpar_subagents_codex(CODEX_DIR)

    print("👥 sincronizando subagents (Claude Code → Codex)...")
    n = sincronizar_subagents(AGENTS_SRC, CODEX_DIR)
    print(f"  ✓ {n} subagents copiados como .agents/<id>/AGENT.md")

    print("📦 espelhando root → plugin/ (cópia publicada no marketplace)...")
    espelhar_para_plugin()

    print(f"\n✅ {n} subagents sincronizados em .agents/ e espelhados em plugin/.")
    print("\nLembre-se de commitar agents/, .agents/, skills/ e plugin/ no git.")
    print("\nNota: skills/ é compartilhado — Codex e Claude Code leem da mesma pasta quando empacotado como plugin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
