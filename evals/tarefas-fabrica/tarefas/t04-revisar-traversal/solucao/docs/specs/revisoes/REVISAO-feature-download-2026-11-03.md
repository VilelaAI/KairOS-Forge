# Revisão pré-PR — feature/download

## 🔴 Crítico
- [Helena] R1 · vendas/servidor.py:12 — path traversal: `nome` com `../` lê arquivo fora da pasta `relatorios/`.

```kairos-revisao
{"veredicto": "bloqueado", "faixa": 2, "criticos": 1, "examinado": ["vendas/servidor.py (Helena)", "tests/test_servidor.py (Patrícia)"], "achados": ["R1"]}
```
