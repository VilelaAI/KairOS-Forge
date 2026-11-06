# Revisão pré-PR — feature/download-seguro

**Veredicto agregado:** ❌ bloqueado

## 🔴 Crítico (qualquer revisor) → bloqueia merge
- [Helena] R1 · vendas/servidor.py:13 — path traversal: um nome com `../` pode ler fora de `relatorios/`.

```kairos-revisao
{"veredicto": "bloqueado", "faixa": 2, "criticos": 1, "achados": ["R1"], "examinado": ["vendas/servidor.py (Helena)", "vendas/nomes.py (Helena)"]}
```
