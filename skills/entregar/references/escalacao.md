# Escalação e encerramento honesto por orçamento

Material de apoio da skill `entregar`. Leia quando o `ciclo.py` devolver `escalado`,
quando você mesmo precisar escalar (`ciclo.py escalar --motivo "..."`) ou quando o
orçamento acabar sem fechar o arco — aqui estão os gatilhos, o formato da mensagem
de escalação e o formato do encerramento por orçamento.

## Escalação

O `ciclo.py` escala **sozinho** quando o orçamento de um gate esgota. Você escala
manualmente (`ciclo.py escalar --motivo "..."`) quando:

- **Duas falhas materialmente iguais** na mesma etapa. Insistir na terceira é
  gastar orçamento em ruído. Se o gate falha pelo mesmo motivo depois de uma
  correção, o problema não é a correção — é o entendimento.
- **Orçamento esgotado** em qualquer loop.
- **Achado exige decisão fora da SPEC** — trade-off arquitetural, mudança de
  escopo, requisito que se revelou impossível.
- **Qualquer gate da fronteira de aprovação** foi tocado.
- **Pare e Pergunte disparou** durante a construção.

Formato da escalação — específica, com o que você já tentou (o `historico` do
`ciclo.py estado --json` tem os dados):

```
⏸️ Entrega pausada na etapa <N> (<etapa>).

Motivo: <duas falhas iguais | orçamento | decisão fora da SPEC>
Achado: <o achado exato, com arquivo:linha>
Já tentei: <as rodadas consumidas e o que cada uma mudou>
Preciso de: <a decisão específica que destrava>

Estado atual: <o que está pronto e verificado, o que não está>
```

## Encerramento honesto por orçamento

Quando o orçamento acaba sem fechar o arco, entregue o estado real:

```
🔁 Entrega encerrada por orçamento — SPEC-NNN

Concluídos e verificados: <lista com evidência>
Não concluídos: <lista com o que falta em cada um>
Rodadas: validar 2/2 · revisar 1/2
Último bloqueio: <achado exato e agente sugerido>

PR NÃO foi aberto porque <motivo>.
Próximo passo: <ampliar orçamento | decidir X | fatiar a SPEC>
```

Nunca abra PR com P1 bloqueado. "Quase pronto" não é pronto, e PR aberto com
gate vermelho transfere para o revisor humano exatamente o trabalho que o arco
existe para absorver.
