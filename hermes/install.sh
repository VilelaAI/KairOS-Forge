#!/usr/bin/env bash
# Instala a ponte kairos-forge no Hermes Agent (~/.hermes/).
# Idempotente: rodar de novo apenas atualiza os arquivos.
set -euo pipefail

HERMES_DIR="${HERMES_HOME:-$HOME/.hermes}"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$HERMES_DIR" ]; then
  echo "❌ $HERMES_DIR não existe — instale o Hermes Agent primeiro:"
  echo "   https://hermes-agent.nousresearch.com/docs/getting-started/quickstart"
  exit 1
fi

mkdir -p "$HERMES_DIR/skills" "$HERMES_DIR/workflows"

instalados=0
for f in "$AQUI"/skills/*.md; do
  cp "$f" "$HERMES_DIR/skills/"
  instalados=$((instalados + 1))
done
for f in "$AQUI"/workflows/*.md; do
  cp "$f" "$HERMES_DIR/workflows/"
  instalados=$((instalados + 1))
done

echo "✅ Ponte kairos-forge instalada: $instalados arquivo(s) em $HERMES_DIR"
echo

if command -v claude >/dev/null 2>&1; then
  echo "✔ Claude Code encontrado."
else
  echo "⚠ Claude Code não encontrado — o motor da fábrica precisa dele:"
  echo "   npm install -g @anthropic-ai/claude-code"
fi

cat <<'FIM'

Próximos passos:
  1. No Claude Code, instale o plugin (uma vez por máquina):
       /plugin marketplace add VilelaAI/kairos-forge
       /plugin install kairos-forge@kairos-forge
  2. Mande pro seu bot Hermes:
       construir com a fábrica: [o que você quer]

O Hermes opera (kanban, aprovações, chat); a fábrica projeta e constrói
(SPEC, implementação, validação, revisão). Detalhes: hermes/README.md
FIM
