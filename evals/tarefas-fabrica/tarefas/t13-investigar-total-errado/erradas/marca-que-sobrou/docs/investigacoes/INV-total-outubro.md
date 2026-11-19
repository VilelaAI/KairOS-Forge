# INV — o total de outubro sai muito maior que a planilha

- **Sintoma:** `python3 -m vendas.relatorio dados/outubro.csv` mostra Total: R$ 287750.75; a planilha soma R$ 10550.75
- **Reprodução:** `python3 -m unittest tests.test_valores`
- **Sintoma na saída:** `30000\.0 != 300\.0|FAILED`

## Hipóteses

| # | Hipótese | Se fosse ela, veríamos | Como testei | Resultado |
|---|---|---|---|---|
| 1 | linha duplicada no CSV | mais vendas que linhas na planilha | contei as linhas: 6 e 6 | descartada |
| 2 | o total soma uma coluna errada | o erro em todas as linhas | somei linha a linha | descartada |
| 3 | a conversão trata o ponto decimal como milhar | só as linhas com ponto saem 100 vezes maiores | `para_reais("300.00")` deu 30000.0 | confirmada |

## Causa

`vendas/valores.py:7` tira todo ponto antes de trocar a vírgula: em `300.00`, sem vírgula, o ponto é decimal e vira milhar.

## Prova

Com a conversão antiga, as duas linhas com ponto decimal somam 280000 a mais; tratando o ponto como decimal quando não há vírgula, o total bate com a planilha.

## Trava

`tests/test_valores.py` falha na base (30000.0 != 300.0) e passa com o conserto; o ticket médio usa a mesma conversão e fica certo junto.
