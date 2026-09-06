# Abrir o PR e registrar a entrega

Material de apoio da skill `entregar`. Leia quando o estado for `pronto_para_pr`
(formato do título e corpo do PR) e ao encerrar o ciclo (modelo do relatório em
`docs/specs/entregas/` e de onde vem a linhagem de rodadas).

### 8. `pronto_para_pr` — abrir o PR

Com validação sem bloqueio em P1 e revisão sem 🔴:

- Título: `<tipo>(<escopo>): <o que muda>` em PT-BR.
- Corpo: objetivo da SPEC, requisitos P1 com evidência, gates rodados, ressalvas
  aceitas e follow-ups abertos, rodadas de correção consumidas (`ciclo.py estado`).
- **Nunca** faça merge — e o guardrail bloqueia `gh pr merge` durante um ciclo
  aberto. A integração é decisão do dono do repositório.
- Depois: `ciclo.py registrar pr_aberto`.

### 9. Encerrar e registrar

Salve `docs/specs/entregas/ENTREGA-<SPEC-NNN>-YYYY-MM-DD.md`:

```markdown
# Entrega — SPEC-NNN — YYYY-MM-DD

**Desfecho:** PR aberto / encerrado por orçamento / escalado
**Modo:** mobilizar | rodar
**Orçamento:** validar N/2 · revisar N/2

## Linhagem de rodadas

| # | Etapa | Achado | Agente | Ação | Bloqueios | Resultado |
|---|---|---|---|---|---|---|
| 1 | validar | 3 P1 sem teste | Ricardo | testes de erro adicionados | 3 → 1 | ficha devolvida |
| 2 | validar | EXP-02 sem teste | Ricardo | teste de erro adicionado | 1 → 0 | aprovado |

## Evidência final
## Ressalvas e follow-ups aceitos
## O que ficou de fora (se encerrou por orçamento)
## Próximo passo
```

A linhagem não é digitada de memória: `ciclo.py estado --json` traz o
`historico` completo com cada transição, o resultado registrado e o horário.
A tabela registra **também as rodadas que falharam** — rodada revertida ou
escalada é evidência, não vergonha apagada, e é o que impede a próxima entrega de
repetir a mesma tentativa.

Ao final, `ciclo.py encerrar --motivo "PR #N aberto"`.
