# Revisão pré-PR — feature/download-seguro

**Veredicto agregado:** ❌ bloqueado

## 🔴 Crítico (qualquer revisor) → bloqueia merge
- [Helena] R1 · vendas/nomes.py:7 — caminho absoluto passa pelo validador: `Path("relatorios") / "/etc/passwd"` é `/etc/passwd`.
- [Helena] R2 · vendas/compactar.py:14 — `subprocess.run` com o caminho do relatório: risco de injeção de comando.

```kairos-revisao
{"veredicto": "bloqueado", "faixa": 2, "criticos": 2, "achados": ["R1", "R2"], "examinado": ["vendas/nomes.py (Helena)", "vendas/compactar.py (Helena)"]}
```
