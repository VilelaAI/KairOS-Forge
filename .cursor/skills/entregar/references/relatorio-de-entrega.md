# Abrir o PR e registrar a entrega

Material de apoio da skill `entregar`. Leia quando o estado for `pronto_para_pr`
(formato do título e corpo do PR) e ao encerrar o ciclo (modelo do relatório em
`docs/specs/entregas/` e de onde vem a linhagem de rodadas).

### 8. `pronto_para_pr` — abrir o PR

Com validação sem bloqueio em P1 e revisão sem 🔴:

- Título: `<tipo>(<escopo>): <o que muda>` em PT-BR.
- Corpo: `painel.py --pr SPEC-NNN > corpo.md`. A pessoa lê o topo e decide; o resto ela abre
  se quiser. Por isso a ordem é esta:
  1. **Cabeçalho:** a SPEC apontada pelo caminho, nunca repetida; a Origem com `Refs #N`
     (troque por `Closes #N` se o PR entrega a issue inteira); a faixa, da revisão ou a
     estimada na triagem.
  2. **O que você decide:** o script já lista o que os arquivos dizem (ressalvas a aceitar,
     requisito fora ou sem prova, faixa 3, triagem que subestimou a faixa, SPEC alterada,
     gate sem relatório). Acrescente o que exige julgamento: decisão registrada depois da
     aprovação (`prova.py decisoes`), trade-off aceito, o que entrou sem ser pedido. Sem
     nada, fica "Nada além do merge".
  3. **O que muda:** 2 a 3 linhas para quem usa o sistema, não para quem lê o diff. O
     script começa pela primeira linha do Objetivo da SPEC.
  4. **Evidência, recolhida:** requisitos com a célula Verificação, veredicto e arquivo de
     cada gate, voltas de correção do ciclo. Sai dos arquivos, e você não reescreve: número
     que passa pelo modelo é número que pode mudar no caminho.
- Apague os comentários `<!-- -->` que preencheu. Os 🟠 e 🟡 da revisão entram como
  follow-up em "O que você decide" quando a revisão saiu `aprovado_com_ressalvas`.
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
