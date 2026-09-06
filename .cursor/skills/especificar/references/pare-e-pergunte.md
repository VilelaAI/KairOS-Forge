# Pare e Pergunte — condições de parada (ADR-0015)

Referência do passo 4.1 de `/kairos-forge:especificar`. Leia antes de escrever o primeiro
requisito — e sempre que uma lacuna parecer "fácil de preencher". Esta tabela é a fronteira
de aprovação humana: nenhuma situação abaixo admite default.

## 4.1. Pare e Pergunte — condições de parada (ADR-0015)

Antes de escrever qualquer requisito, verifique se dá para escrevê-lo **honestamente**. Se a tarefa cair numa condição abaixo, **pare e faça a pergunta** — nunca preencha a lacuna com achismo, placeholder ou texto genérico:

| Situação | Pergunta obrigatória |
|---|---|
| Conteúdo institucional/jurídico/regulatório citado sem fonte oficial | "De onde vem o texto? Você cola o oficial, ou adiamos até ter a fonte?" — proibido redigir "com base na legislação aplicável" (domínio regulado de verdade → kairos-ai) |
| Integração externa sem provedor definido (pagamento, e-mail, mapa) | "Qual provedor exatamente?" |
| Cálculo de negócio (preço, imposto, prazo) sem fórmula | "Qual a fórmula exata? Arredondamento? Qual o caso-teste esperado?" |
| Dados pessoais reais que apareceriam como exemplo/conteúdo | "Confirma esses dados? Posso usar exatamente assim?" — nunca 'Fulano de Tal' achando que alguém revisa depois |
| "Igual ao site X" sem URL acessível ou screenshot | "Tem referência que carrega? Sem ela não é pixel-perfect, é estimativa" |
| Asset de terceiro (PDF, imagem, vídeo) em domínio alheio | "Linko a URL externa (risco de 404) ou baixamos e hospedamos? Decisão registrada na SPEC" |
| Tela/funcionalidade vaga ("dashboard") sem saber o que mostra | "O que exatamente essa tela mostra? Quais dados, quais ações?" (caso pra Joana, do apoio-requisitos) |

**Regra de ouro:** se a única forma de escrever o requisito é inventar conteúdo que aparecerá ao usuário final como verdade, **pare**. Inventar é dívida silenciosa — só aparece quando alguém de fora descobre o erro.
