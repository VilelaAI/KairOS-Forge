# Revisão pré-PR — feature/download-seguro

**Faixa de raio de explosão:** 2 (ampla)
**Revisores acionados:** Helena, Patrícia
**Veredicto agregado:** ❌ bloqueado

## 🔴 Crítico (qualquer revisor) → bloqueia merge
- [Helena] R1 · vendas/nomes.py:7 — o validador só recusa `..`; um caminho absoluto passa. `Path("relatorios") / "/etc/passwd"` é `/etc/passwd` (conferido rodando a expressão), então `servir_relatorio("/etc/passwd")` lê qualquer arquivo do servidor. Use `(BASE / nome).resolve()` e exija `is_relative_to(BASE.resolve())`.

## 🔵 Baixo
- [Patrícia] tests/test_servidor.py — falta o caso do caminho absoluto, que é o que o validador deixa passar.

Examinado e sem achado: `vendas/compactar.py` — lista de argumentos sem shell, com `--` antes do nome.

```kairos-revisao
{"veredicto": "bloqueado", "faixa": 2, "criticos": 1, "achados": ["R1"], "examinado": ["vendas/nomes.py (Helena)", "vendas/servidor.py (Helena)", "vendas/compactar.py (Helena)", "tests/test_servidor.py (Patrícia)"]}
```
