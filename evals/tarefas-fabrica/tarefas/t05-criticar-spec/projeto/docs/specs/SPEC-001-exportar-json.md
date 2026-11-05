# SPEC-001 — Exportar o relatório em JSON

**Apetite:** pequeno · **Origem:** pedido do time comercial

## Objetivo

Gerar um arquivo JSON com as vendas para o painel do comercial.

## Requisitos rastreáveis

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| EXP-01 | `--json saida.json` grava só as vendas válidas | P1 | WHEN `--json x.json` THEN x.json tem um objeto por venda válida, em ordem de data | Pendente | — |
| EXP-02 | A exportação deve ser rápida | P1 | A exportação é rápida e eficiente | Pendente | — |
| EXP-03 | O JSON inclui também as linhas inválidas, com `valor: null` | P2 | WHEN há linha inválida THEN ela aparece com `valor: null` | Pendente | — |

## Plano

- T1 — Lucas: `exportar_json` em `vendas/relatorio.py` e a flag `--json` (EXP-01, EXP-03).
- T2 — Ricardo: testes de EXP-01 e EXP-03.

## Matriz de testes

| Requisito | Teste |
|---|---|
| EXP-01 | `tests/test_exportar.py::test_so_validas` |
| EXP-03 | `tests/test_exportar.py::test_invalidas_com_null` |
