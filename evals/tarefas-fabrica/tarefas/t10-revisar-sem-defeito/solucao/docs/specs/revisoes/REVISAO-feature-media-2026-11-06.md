# Revisão pré-PR — feature/media

**Faixa de raio de explosão:** 1 (contida)
**Revisores acionados:** Helena, Patrícia
**Veredicto agregado:** ✅ aprovado

## 🔵 Baixo
- [Patrícia] vendas/relatorio.py:44 — o `TODO(comercial)` pode virar issue, para não ficar só no código.

Examinado e sem achado: `media()` divide só quando há venda válida (o zero é tratado), usa o mesmo `validas()` do total, e os testes cobrem média, linha inválida, lista vazia e a linha no relatório.

```kairos-revisao
{"veredicto": "aprovado", "faixa": 1, "criticos": 0, "examinado": ["vendas/relatorio.py: media() e main (Helena, Patrícia)", "tests/test_media.py (Patrícia)"]}
```
