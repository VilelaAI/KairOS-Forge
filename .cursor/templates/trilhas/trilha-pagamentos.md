# Trilha — Pagamentos e checkout

**Tema:** checkout com provedor de pagamento (Stripe, Mercado Pago, etc.), webhooks, recibos e reconciliação.
**Feature sensível:** SIM. `/kairos-forge:analisar-ameacas` é obrigatório antes de implementar.

## Requisitos típicos (rascunho — renumere e adapte na SPEC)

| ID | Requisito | Prioridade | Critério de aceite |
|---|---|---|---|
| PAG-01 | Como cliente, quero pagar via checkout do provedor, para concluir a compra. | P1 | WHEN pagamento aprovado THEN pedido SHALL mudar para pago exatamente uma vez (idempotente). |
| PAG-02 | Como sistema, quero processar webhooks do provedor, para refletir o estado real do pagamento. | P1 | WHEN webhook recebido THEN assinatura SHALL ser verificada; evento duplicado SHALL ser ignorado. |
| PAG-03 | Como cliente, quero receber recibo/confirmação, para ter comprovante. | P2 | WHEN pagamento confirmado THEN recibo SHALL ser gerado/enviado. |
| PAG-04 | Como financeiro, quero conciliar pedidos × transações do provedor, para detectar divergência. | P2 | WHEN rotina de conciliação roda THEN divergências SHALL aparecer em relatório. |
| PAG-05 | Como cliente, quero reembolso/cancelamento, para desistir com segurança. | P2 | WHEN reembolso emitido THEN estado do pedido e do provedor SHALL convergir. |

## Tarefas e agentes sugeridos

| Tarefa | Agente | Gate sugerido |
|---|---|---|
| Modelo de pedidos/transações + estados | Fernanda (desenho) + Carlos | migration com rollback |
| Integração com o provedor (checkout + API) | Thiago (contrato) + Lucas | integration com sandbox do provedor |
| Endpoint de webhook idempotente | Lucas | teste de duplicidade e assinatura inválida |
| Tela/fluxo de checkout | Marina | E2E do caminho feliz + recusa |
| Testes dos estados de pagamento | Ricardo | matriz aprovado/recusado/expirado/reembolsado |
| Revisão de segurança pré-PR | Helena | `/kairos-forge:revisar` |

## Riscos e ameaças típicas (insumo pro /analisar-ameacas)

- Webhook sem verificação de assinatura = qualquer um marca pedido como pago.
- Falta de idempotência: evento reentregue duplica baixa/estoque/e-mail.
- Confiar em valor vindo do cliente (preço/quantidade calculados no front).
- Segredos do provedor em código/log; chaves de teste em produção (e vice-versa).
- Estados órfãos: pagamento aprovado sem pedido, pedido pago sem transação (a conciliação PAG-04 existe por isso).

## Perguntas que o arquiteto DEVE fazer antes de fechar a SPEC

1. Qual provedor e qual modalidade (checkout hospedado, API direta, assinatura recorrente)?
2. Moeda única? Parcelamento? Pix/boleto além de cartão?
3. O que acontece com o carrinho/pedido se o pagamento expirar?
4. Reembolso é automático ou fluxo manual do admin?
5. Requisito fiscal (nota, recibo formal) agora ou follow-up?

## Fora do escopo desta trilha

Gestão de assinaturas/planos (trilha própria quando precisar), antifraude avançado, split de pagamento para marketplace.
