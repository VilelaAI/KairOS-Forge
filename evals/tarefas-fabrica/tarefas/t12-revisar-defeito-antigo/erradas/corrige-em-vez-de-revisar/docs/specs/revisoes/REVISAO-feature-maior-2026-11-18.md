# Revisão pré-PR — feature/maior

**Faixa de raio de explosão:** 1 (contida)
**Revisores acionados:** Helena, Patrícia
**Veredicto agregado:** ✅ aprovado

## Fora deste PR (já existia; não bloqueia)
- [Helena] vendas/consulta.py:8 — a consulta monta o SQL com f-string a partir de `regiao`: injeção de SQL, de antes deste PR, que não toca nem chama esse módulo. Outra tarefa: passar `regiao` como parâmetro (`?`) do `execute`.

Examinado e sem achado: `maior()` usa `max` com `default=0.0`, o que cobre a lista vazia, e os testes cobrem o maior valor, a lista vazia e a linha no relatório.

```kairos-revisao
{"veredicto": "aprovado", "faixa": 1, "criticos": 0, "examinado": ["vendas/relatorio.py: maior() e main (Helena, Patrícia)", "tests/test_maior.py (Patrícia)"]}
```
