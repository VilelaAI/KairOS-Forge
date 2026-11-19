# INV — o total de outubro sai muito maior que a planilha

- **Sintoma:** o total sai R$ 287750.75; a planilha soma R$ 10550.75
- **Reprodução:** `python3 -m vendas.relatorio dados/outubro.csv`
- **Sintoma na saída:** `287750`

## Hipóteses

| # | Hipótese | Se fosse ela, veríamos | Como testei | Resultado |
|---|---|---|---|---|
| 1 | o total soma uma coluna errada | o erro em todas as linhas | somei linha a linha | não confirmada |

## Causa

`vendas/relatorio.py:16` soma errado.

## Prova

Ainda a fazer.

## Trava

`tests/test_valores.py` passa com o conserto em `vendas/valores.py`.
