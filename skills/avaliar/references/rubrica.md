# Rubrica — os cinco eixos

Detalhe do Passo 3 da skill `avaliar`: o que cada eixo pergunta e como se pontua.

## 3. Escrever a rubrica — os cinco eixos

Sem isto, o eval não mede nada. Pontue **só os eixos que se aplicam** e diga quais
foram descartados e por quê:

| Eixo | O que pergunta | Como se pontua |
|---|---|---|
| **Sucesso da tarefa** | A saída resolve o que foi pedido? | Binário por caso, ou escala curta (0/1/2) com âncora escrita para cada valor |
| **Uso de ferramenta** | Chamou as ferramentas certas, com os argumentos certos, sem chamada supérflua? | Compara a sequência esperada com a executada |
| **Conformidade de trajetória** | O caminho foi legítimo, ou a resposta certa saiu por sorte? | Verifica se as etapas obrigatórias aconteceram (consultou a base antes de afirmar?) |
| **Alucinação / fundamentação** | Toda afirmação tem lastro na fonte disponível? | Conta afirmações sem fonte; qualquer uma já é falha no caso |
| **Qualidade da resposta** | Formato, tom, idioma, completude | Rubrica curta e explícita, ou juiz-LLM com critério escrito |

**Conformidade de trajetória é o eixo que mais se esquece e o que mais dói.** Uma
saída fluente que pulou a etapa de verificação é falha mais perigosa que um erro
visível — porque parece certa. É o mesmo princípio que o `/kairos-forge:validar`
aplica ao corroborar `verificado:` contra a trajetória registrada (ADR-0021).

Juiz-LLM entra só onde a verificação programática não alcança (tom, completude),
**sempre com critério escrito** e com uma amostra conferida à mão para calibrar.
Juiz sem rubrica é o mesmo achismo com mais tokens.
