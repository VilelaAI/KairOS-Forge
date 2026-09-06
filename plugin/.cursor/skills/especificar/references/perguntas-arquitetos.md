# Perguntas típicas por arquiteto

Referência do passo 3 de `/kairos-forge:especificar`. Leia quando o arquiteto for começar
a interrogação e precisar do repertório de perguntas da sua persona, e para a versão
completa das duas regras da interrogação (baseline de métrica e default recomendado).

## 3. Arquiteto(s) interrogam em primeira pessoa

Perguntas típicas por agente:

- **Diego**: "Qual o fluxo de dados? Quem chama quem? Eventos síncronos ou assíncronos?"
- **Fernanda**: "Quantos registros esperados? Cardinalidade? Padrão de leitura/escrita?"
- **Thiago**: "Quem consome essa API? Versionamento? Auth?"
- **Rafael**: "Por que essa abordagem e não a alternativa óbvia? Trade-off de escala?"
- **Camila**: "Isso é MVP ou V2? Qual métrica de sucesso — e qual o valor dela **hoje**?"

**Métrica de sucesso sem baseline não é métrica.** "Reduzir o tempo de onboarding em 30%" não é verificável sem saber de quanto para quanto; "de 5 para 3,5 minutos até setembro" é. Se o valor atual não for conhecido, o requisito P1 vira **medir primeiro** — e isso é honesto, não atraso.

**Pergunta com default recomendado (ADR-0019):** escolha **reversível** não trava o fluxo — o arquiteto declara o default ("recomendo X por Y; sigo com isso se você não disser o contrário"), registra a premissa na SPEC e continua. O Pare e Pergunte (ADR-0015) permanece absoluto no **irreversível e no conteúdo inventável**: lá não existe default, existe pergunta.
