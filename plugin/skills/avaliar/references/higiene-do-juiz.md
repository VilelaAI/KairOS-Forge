# Higiene do juiz

Detalhe do Passo 3 da skill `avaliar`. A raiz lista as cinco regras em uma linha cada;
aqui está a justificativa de cada uma e por que autocrítica não substitui juiz externo.

## Higiene do juiz — cinco regras, e a primeira nos atinge em cheio

Juiz enviesado é pior que juiz nenhum: ele lava um chute em número e depois age sobre
ele. O viés é medido e é grande — no mesmo conjunto de saídas, um juiz devolveu 93,3% e
outro devolveu 39,5%.

1. **Família diferente da que gerou.** Modelo reconhece a própria escrita e a julga com
   outra régua — para cima ou para baixo, e as duas direções já foram medidas. Isto vale
   com força aqui: rodando dentro do Claude Code, o default preguiçoso é **Claude
   julgando Claude**, que é exatamente o caso a evitar. Se só houver uma família
   disponível, **diga isso no relatório** e trate o número como piso de confiança, não
   como medida.
2. **Painel quando errar é caro.** Dois ou três juízes de fornecedores diferentes, e o
   agregado entre famílias é o que quebra erro correlacionado. Um juiz só é aceitável em
   avaliação barata e reversível.
3. **Objetivamente checável vai para código, nunca para o juiz.** O teste passou? O
   arquivo existe? O estado mudou? O comando rodou? Isso é `if`, não julgamento — e sai
   de graça, sem viés e sem token.
4. **Versão do juiz pinada e registrada.** Juiz é software com versão. Um que atualiza em
   silêncio torna incomparável todo score de antes e depois — e a falha é quieta: a suíte
   continua produzindo números que pararam de significar a mesma coisa semanas atrás. É o
   irmão simétrico do digest do artefato (passo 3.5): um fixa **o que** foi avaliado, o
   outro fixa **quem** avaliou.
5. **Nunca recompense a forma.** Zero pontos para comprimento, presença de palavra-chave,
   contagem de citação, fraseado exato, número de chamadas de ferramenta ou similaridade
   com uma referência. Recompense a forma e o agente aprende a forma: otimizar contra um
   juiz por tempo suficiente ensina a **parecer certo em vez de estar certo**, e aí sua
   defesa virou superfície de ataque.

**Autocrítica não substitui juiz externo.** Pedir ao modelo que revise o próprio trabalho
sem fundamentação externa não ajuda de forma confiável e frequentemente piora (Huang et
al., ICLR 2024). A autocrítica do `anti-drift.md` funciona porque **não** é intrínseca:
ela critica contra o "Done when" da task e exige evidência de `arquivo:linha`. Tirada a
âncora externa, vira ruído com aparência de rigor.

## Por que o digest do artefato é a outra metade

Do Passo 3.5 da skill: sem digest, ajustar o prompt depois da rodada selada custa zero —
basta não mencionar. Com digest, custa uma reavaliação. A diferença entre uma regra e um
lembrete. É o que dá dente à regra do conjunto selado.
