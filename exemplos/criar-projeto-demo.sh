#!/usr/bin/env bash
# criar-projeto-demo.sh — monta um projeto pequeno e real para testar a fábrica.
#
# Real importa: o gate precisa poder FALHAR. Um projeto de mentira, com teste que
# sempre passa, faz a fábrica parecer funcionar sem provar nada — que é exatamente
# o modo de falha que este harness existe para impedir.
#
# Uso:  bash exemplos/criar-projeto-demo.sh [destino]
#       (default: ~/kairos-demo)
set -euo pipefail

DEST="${1:-$HOME/kairos-demo}"

if [ -e "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null)" ]; then
  echo "❌ $DEST já existe e não está vazio. Escolha outro destino ou apague antes." >&2
  exit 1
fi

mkdir -p "$DEST"/{src,tests,contextos,decisoes,docs/specs/{criticas,validacoes,revisoes},docs/adr}
cd "$DEST"

# ── a aplicação: pequena, real, com um bug plantado ────────────────────────────
cat > src/vendas.py <<'PY'
"""Resumo de vendas a partir de um CSV. Pequeno de propósito."""
from __future__ import annotations

import csv
from pathlib import Path


def ler_vendas(caminho: Path) -> list[dict]:
    """Lê o CSV de vendas. Colunas: produto, quantidade, valor_unitario."""
    with open(caminho, newline="", encoding="utf-8") as fh:
        return [
            {"produto": l["produto"],
             "quantidade": int(l["quantidade"]),
             "valor_unitario": float(l["valor_unitario"])}
            for l in csv.DictReader(fh)
        ]


def total_por_produto(vendas: list[dict]) -> dict[str, float]:
    """Faturamento somado por produto."""
    totais: dict[str, float] = {}
    for v in vendas:
        totais[v["produto"]] = totais.get(v["produto"], 0.0) + v["quantidade"] * v["valor_unitario"]
    return totais


def resumo(vendas: list[dict]) -> dict:
    totais = total_por_produto(vendas)
    return {
        "produtos": len(totais),
        "faturamento": round(sum(totais.values()), 2),
        "por_produto": {k: round(v, 2) for k, v in sorted(totais.items())},
    }
PY

cat > tests/test_vendas.py <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.vendas import ler_vendas, resumo, total_por_produto

VENDAS = [
    {"produto": "caneta", "quantidade": 10, "valor_unitario": 2.5},
    {"produto": "caderno", "quantidade": 3, "valor_unitario": 20.0},
    {"produto": "caneta", "quantidade": 4, "valor_unitario": 2.5},
]


def test_total_por_produto_soma_linhas_repetidas():
    assert total_por_produto(VENDAS) == {"caneta": 35.0, "caderno": 60.0}


def test_resumo_conta_produtos_distintos():
    assert resumo(VENDAS)["produtos"] == 2


def test_resumo_faturamento():
    assert resumo(VENDAS)["faturamento"] == 95.0


def test_ler_vendas_le_csv(tmp_path):
    csv_path = tmp_path / "v.csv"
    csv_path.write_text("produto,quantidade,valor_unitario\ncaneta,2,3.0\n", encoding="utf-8")
    assert ler_vendas(csv_path) == [
        {"produto": "caneta", "quantidade": 2, "valor_unitario": 3.0}
    ]
PY

cat > vendas.csv <<'CSV'
produto,quantidade,valor_unitario
caneta,10,2.50
caderno,3,20.00
caneta,4,2.50
mochila,1,149.90
CSV

# ── contexto que a fábrica lê ──────────────────────────────────────────────────
cat > contextos/testes.md <<'MD'
# Testes

**Gate principal:** `python3 -m pytest -q`

Rodar do diretório raiz do projeto. Todos os testes precisam passar antes de
qualquer requisito ser marcado como Concluído.

Sem cobertura mínima formal ainda — a regra em vigor é: todo comportamento novo
entra com caminho feliz + pelo menos um caso de erro.
MD

cat > contextos/projeto.md <<'MD'
# Projeto — demo de vendas

CLI mínima que lê um CSV de vendas e resume faturamento por produto. Existe para
exercitar a fábrica kairos-forge num projeto de verdade, pequeno o bastante para
ler inteiro em dois minutos.

- `src/vendas.py` — leitura do CSV e agregação
- `tests/test_vendas.py` — pytest, é o gate
- `vendas.csv` — dado de exemplo

**Stack:** Python 3.11+, pytest, stdlib. Sem framework, sem banco.
MD

cat > contextos/convencoes.md <<'MD'
# Convenções

- PT-BR em nomes, comentários, docstrings e mensagens de commit.
- Conventional Commits: `feat(escopo): ...`, `fix(escopo): ...`, `test(escopo): ...`
- Toda função pública com docstring de uma linha dizendo o que faz.
- Sem dependência nova sem justificativa escrita na SPEC.
MD

cat > README.md <<'MD'
# demo de vendas — projeto de teste do kairos-forge

Projeto pequeno e real para exercitar a fábrica. Veja `docs/testar-localmente.md`
no repositório do kairos-forge para o roteiro.

```bash
python3 -m pytest -q          # o gate
python3 -c "from src.vendas import *; import json; print(json.dumps(resumo(ler_vendas('vendas.csv')), indent=2, ensure_ascii=False))"
```
MD

printf '__pycache__/\n.pytest_cache/\n*.pyc\n' > .gitignore

git init -q
git add -A
git -c user.email=demo@exemplo.local -c user.name="demo" commit -q -m "chore: projeto demo de vendas para testar o kairos-forge"
git checkout -q -b feature/exportar-json

echo "✅ projeto criado em $DEST (branch feature/exportar-json)"
echo
echo "Confira que o gate roda de verdade:"
echo "  cd $DEST && python3 -m pytest -q"
