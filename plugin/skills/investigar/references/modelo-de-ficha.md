# Modelo da ficha de investigação

Salve em `docs/investigacoes/INV-<slug>.md`, com um `<slug>` curto do que quebra. O
`prova.py investigacao` lê os campos e as seções pelo nome, então mantenha os títulos.

```markdown
# INV — <o que quebra, em uma frase>

- **Sintoma:** <o que a pessoa viu: a mensagem, a saída errada ou o tempo, com as palavras dela>
- **Reprodução:** `<o laço: comando que sai diferente de 0 enquanto o problema existe>`
- **Sintoma na saída:** `<regex que casa com o sintoma na saída do laço>`

## Hipóteses

| # | Hipótese | Se fosse ela, veríamos | Como testei | Resultado |
|---|---|---|---|---|
| 1 | <causa possível> | <o que apareceria> | <o que rodei> | descartada |
| 2 | <causa possível> | <o que apareceria> | <o que rodei> | confirmada |

## Causa

<a causa em uma ou duas frases, com `arquivo:linha`; no mínimo 20 caracteres>

## Prova

<o que liga e desliga o problema: com a causa, o laço falha; sem ela, passa>

## Trava

<o teste que falha antes e passa depois, ou por que não há lugar certo para ele>
```

## Como o `prova.py investigacao` lê

| Parte | Regra |
|---|---|
| **Sintoma** | preenchido, sem o `<…>` do modelo |
| **Reprodução** | o comando entre crases; é ele que o `reproduzir` roda na base e agora |
| **Sintoma na saída** | a regex entre crases; o laço que falha por outro motivo dá `sintoma_diferente` |
| `## Hipóteses` | tabela com `#` na primeira coluna; a última coluna começa com `descartada`, `confirmada` ou qualquer outra coisa (aberta) |
| `## Causa` | 20 caracteres ou mais |
| `## Prova`, `## Trava` | preenchidas |

Veredictos: **pronta** (sai 0) quando tudo está preenchido, há hipótese confirmada, a
reprodução dá `reproduz_e_corrige` e nenhuma marca de depuração sobrou; **pare e pergunte**
(sai 2) com 3 hipóteses descartadas e nenhuma confirmada; **incompleta** (sai 1) no resto, com
a lista do que falta.

A ficha fica em `docs/`, e não em `decisoes/`: é evidência de uma investigação, não uma
escolha. A decisão que ela motivar vai para `decisoes/log.md` ou para um ADR, citando a ficha.
