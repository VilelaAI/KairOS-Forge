#!/bin/sh
# Agente simulado da POC: faz o trabalho mínimo de cada estado do arco, SEM modelo,
# e responde no mesmo JSON que o `claude -p --output-format json --json-schema` devolve.
# Serve para provar o runner e o contrato; o julgamento do modelo fica para o modo real.
set -e
PROMPT="$1"
ESTADO=$(printf '%s' "$PROMPT" | sed -n 's/.*estado=\([a-z_]*\).*/\1/p' | head -1)
HOJE=$(date +%Y-%m-%d)
SPEC=$(printf "%s" "$PROMPT" | grep -oE "SPEC-[0-9]+" | head -1)

responder() {
  printf '{"type":"result","structured_output":{"resultado":"%s","nota":"%s"}}\n' "$1" "$2"
}

case "$ESTADO" in
  construindo)
    cat > saudacao.py <<'EOF'
def saudar(nome: str) -> str:
    if not nome or not nome.strip():
        raise ValueError("nome vazio")
    return f"Olá, {nome.strip()}!"
EOF
    mkdir -p tests
    cat > tests/test_saudacao.py <<'EOF'
import unittest
from saudacao import saudar

class TestSaudar(unittest.TestCase):
    def test_caminho_feliz(self):
        self.assertEqual(saudar("Ana"), "Olá, Ana!")
    def test_nome_vazio(self):
        with self.assertRaises(ValueError):
            saudar("   ")
EOF
    python3 -m unittest -q tests.test_saudacao 2>/dev/null
    # marca o requisito como Concluído com verificado: — só Status/Verificação mudam,
    # o digest do contrato da SPEC tem de continuar igual
    sed -i "s/| Pendente | — |/| Concluído | verificado: python3 -m unittest tests.test_saudacao ($(date +%d\\/%m)) |/" docs/specs/${SPEC}-*.md
    responder pronto "saudacao.py + tests/test_saudacao.py criados, unittest verde, SPEC marcada verificado:"
    ;;
  validando)
    mkdir -p docs/specs/validacoes
    cat > "docs/specs/validacoes/VALIDACAO-${SPEC}-${HOJE}.md" <<EOF
# Validação — ${SPEC} — ${HOJE}

**Veredicto:** aprovado
**Gates rodados:** python3 -m unittest tests.test_saudacao

## Matriz de rastreabilidade

| Requisito | Prioridade | Evidência | Gate | Corroboração | Status |
|---|---|---|---|---|---|
| SAU-01 | P1 | saudacao.py, tests/test_saudacao.py | unittest (2 testes) | sem telemetria | aprovado |

\`\`\`kairos-validacao
{"spec": "${SPEC}", "veredicto": "aprovado", "bloqueios": 0, "verificado": ["SAU-01 (python3 -m unittest tests.test_saudacao)"]}
\`\`\`
EOF
    responder aprovado "relatório de validação salvo com fence kairos-validacao"
    ;;
  revisando)
    mkdir -p docs/specs/revisoes
    cat > "docs/specs/revisoes/REVISAO-${SPEC}-${HOJE}.md" <<EOF
# Revisão pré-PR — ${SPEC}

**Faixa de raio de explosão:** 1
**Revisores acionados:** Helena, Patrícia
**Veredicto agregado:** ✅ aprovado

## ✅ O que está bom
- Função pura, sem entrada externa (Helena)
- Caminho feliz + 1 erro cobertos (Patrícia)

\`\`\`kairos-revisao
{"veredicto": "aprovado", "faixa": 1, "criticos": 0, "examinado": ["saudacao.py (Helena, Patrícia)", "tests/test_saudacao.py (Patrícia)"]}
\`\`\`
EOF
    responder limpo "revisão salva com fence kairos-revisao, zero críticos"
    ;;
  enquadrando)   responder entendimento_pronto "entendimento espelhado em 3 bullets" ;;
  desenhando)    responder abordagens_prontas "2 abordagens com trade-offs" ;;
  especificando) responder spec_pronta "SPEC escrita" ;;
  criticando)
    mkdir -p docs/specs/criticas
    cat > "docs/specs/criticas/CRITICA-${SPEC}-${HOJE}.md" <<EOF
# Crítica — ${SPEC} — ${HOJE}

**Críticos:** Joana (requisitos), Ricardo (testabilidade)
**Veredicto:** aprovado

## O que foi examinado
- Objetivo · SAU-01 · Plano (1 tarefa) · Matriz de testes

\`\`\`kairos-critica
{"spec": "${SPEC}", "veredicto": "aprovado", "achados": 0, "criticado_por": ["Joana", "Ricardo"], "examinado": ["objetivo", "SAU-01", "plano", "matriz de testes"]}
\`\`\`
EOF
    responder limpa "crítica salva com dois críticos"
    ;;
  corrigindo_validacao|corrigindo_revisao|corrigindo_spec) responder pronto "correção aplicada" ;;
  *) responder desconhecido "estado não coberto pelo simulado: $ESTADO" ;;
esac
