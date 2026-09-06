# Gold set — composição e conjunto selado

Detalhe do Passo 2 da skill `avaliar`. A raiz traz o resumo; aqui estão as regras
completas de composição, o modelo de caso e a disciplina do conjunto selado.

## 2. Construir o gold set — versionado, fora dos prompts

`evals/<slug>/gold.jsonl`, um caso por linha, com a entrada e o esperado:

```json
{"entrada": "Posso cancelar depois de 30 dias?", "esperado": {"fundamentado": true, "cita": ["politica-cancelamento"]}}
```

Regras de composição:

- **Casos reais valem mais que sintéticos.** Puxe de logs, tickets, histórico. Caso
  inventado testa a sua imaginação, não o sistema.
- **Inclua as fronteiras.** Onde mais de uma resposta é defensável, aceite uma
  lista de esperados — e marque como fronteira, para não virar ruído na acurácia.
- **Inclua o adversarial.** Entrada maliciosa, ambígua, vazia, longa demais, em
  outro idioma. O caminho feliz sozinho sempre passa.
- **Inclua o "deve recusar".** Casos onde a resposta certa é não responder são os
  que mais separam sistema bom de sistema confiante.
- **Tamanho mínimo útil: ~30 casos** para ter sinal. Abaixo disso, uma resposta muda o
  percentual em mais de 3 pontos e a métrica vira ruído.
- **Para confiar no número agregado, ~500 casos.** Entre 30 e 500 o resultado orienta
  decisão pontual ("esse caso quebrou"), não conclusão sobre o comportamento inteiro.
  Diga qual dos dois você tem — apresentar 30 casos como se fossem 500 é o mesmo pecado
  de apresentar inferência como medição.
- **Teto de tempo: a suíte roda em menos que um café.** Suíte que passa de ~5 minutos
  deixa de ser rodada e vira ritual trimestral — e ritual trimestral não protege nada.
  Se estourar, simule o que custa dinheiro ou escreve em produção em vez de chamar de
  verdade.

### Conjunto selado — a metade que o construtor não vê

Divida o gold set em **visível** e **selado** (regra prática: ~60/40), e guarde o selado
em `evals/<slug>/selado.jsonl`:

- **Visível** é onde se ajusta. Quem constrói pode ler, rodar e iterar contra ele.
- **Selado** é onde se decide. Roda por último, e **só o resultado dele vale como
  aprovação**.

Sem essa divisão, o loop é: roda a suíte, lê as falhas, ajusta até passar, aprova — um
sistema ajustado ao próprio teste. Um agente calibrado contra uma suíte visível está
otimizando a suíte, não o comportamento.

**Rotacione.** A cada ciclo, mova alguns casos de um lado para o outro. Selado que nunca
muda vira visível na prática, porque o construtor aprende os casos por osmose.

**Divergência entre os dois é o sinal mais valioso do eval:** visível em 95% e selado em
70% não é ruído amostral — é ajuste ao teste, medido.
