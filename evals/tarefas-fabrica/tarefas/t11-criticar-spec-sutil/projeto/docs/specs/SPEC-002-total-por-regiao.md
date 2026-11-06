# SPEC-002 — Total por região

**Apetite:** pequeno · **Origem:** pedido do time comercial, para o fechamento mensal

## Objetivo

Mostrar o total de vendas de cada região no relatório.

## Não-objetivos

- Filtro por mês ou por produto.
- Gráfico ou exportação.

## Requisitos rastreáveis

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| REG-01 | `--por-regiao` imprime uma linha por região, com o total, em ordem alfabética | P1 | WHEN `--por-regiao` com vendas em Sul e Norte THEN a linha `Norte: R$ <total>` vem antes de `Sul: R$ <total>` | Pendente | — |
| REG-02 | Só entram nos totais as vendas de 2026 | P1 | WHEN há venda com data de 2025 THEN ela não entra em nenhum total | Pendente | — |
| REG-03 | O total de cada região é exato em centavos, sem erro de ponto flutuante | P1 | WHEN a região tem vendas de 0.10 e 0.20 THEN a linha dela mostra `R$ 0.30` | Pendente | — |
| REG-04 | Venda com a região em branco é somada numa linha `(sem região)`, a última da saída | P2 | WHEN há venda com a região vazia THEN a última linha é `(sem região): R$ <total>` | Pendente | — |

## Plano

- T1 — Lucas: `totais_por_regiao` em `vendas/relatorio.py` e a flag `--por-regiao` (REG-01 a REG-04).
- T2 — Ricardo: os testes da matriz.

## Matriz de testes

| Requisito | Teste |
|---|---|
| REG-01 | `tests/test_regiao.py::test_ordem_alfabetica` |
| REG-02 | `tests/test_regiao.py::test_venda_de_2025_fora` |
| REG-03 | `tests/test_regiao.py::test_ordem_alfabetica` |
| REG-04 | `tests/test_regiao.py::test_regiao_em_branco_por_ultimo` |
