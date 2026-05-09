---
name: especificar
description: Inicia o fluxo de spec-driven development para uma feature ou mudança. Use no início de qualquer trabalho não-trivial — antes de escrever código. Aciona Laura (Tech Lead) que decide quais arquitetos entram (Diego para sistemas, Fernanda para dados, Thiago para integrações, Rafael para decisão escalável). Resultado é uma SPEC em docs/specs/SPEC-NNN-slug.md pronta para o time implementar via /mobilizar.
---

# Especificar — fluxo spec-driven

Você está sendo invocado para iniciar o ciclo de design **antes** da implementação.

## Regra de ouro

Não codifique. Não chame teammate de implementação. Esta skill produz **artefato textual** — uma SPEC — que servirá de contrato para `/kairos-forge:mobilizar` ou execução manual depois.

## Fluxo

### 1. Laura entra primeiro

Invoque o agente `laura-tech-lead`. Ela vai:

- Ouvir a descrição do usuário
- Classificar o tamanho (feature pequena, média, grande, decisão arquitetural)
- Decidir quais arquitetos da fábrica entram

### 2. Laura aciona o(s) arquiteto(s)

Mapeamento que Laura usa:

| Tipo de mudança | Arquiteto principal |
|---|---|
| Feature com banco novo | **Fernanda** (dados) |
| Feature com API/integração | **Thiago** (integrações) |
| Feature com fluxo complexo entre componentes | **Diego** (sistemas) |
| Decisão de tecnologia ou padrão | **Rafael** (Staff) |
| Múltiplas dimensões | **Diego coordena**, chama Fernanda/Thiago conforme necessário |

Se a tarefa for primariamente de produto (escopo, priorização, MVP), Laura aciona **Camila (PM)** antes ou junto.

### 3. Arquiteto(s) interrogam em primeira pessoa

Perguntas típicas por agente:

- **Diego**: "Qual o fluxo de dados? Quem chama quem? Eventos síncronos ou assíncronos?"
- **Fernanda**: "Quantos registros esperados? Cardinalidade? Padrão de leitura/escrita?"
- **Thiago**: "Quem consome essa API? Versionamento? Auth?"
- **Rafael**: "Por que essa abordagem e não a alternativa óbvia? Trade-off de escala?"
- **Camila**: "Isso é MVP ou V2? Qual métrica de sucesso?"

### 4. Espelhar entendimento

Antes de escrever a SPEC, o arquiteto líder **resume em 3 bullets** o problema como entendeu. Pede correção do usuário.

### 5. Propor 2-3 abordagens

Cada uma com trade-offs explícitos (complexidade, custo, reversibilidade). Recomendar uma.

### 6. Após aprovação, escrever a SPEC

Em `docs/specs/SPEC-<NNN>-<slug>.md` no projeto do usuário, com seções:

- **Contexto e problema** — qual dor real
- **Objetivo** — uma frase
- **Não-objetivos** — o que está fora
- **Invariantes** — o que precisa ser verdade ao final
- **Plano de implementação** — lista numerada, cada item ≤ 1 dia, **com agente sugerido entre colchetes** (ex: "1. [Carlos] Migration cria tabela X com RLS Y")
- **Estratégia de teste** — o que Ricardo deve cobrir
- **Riscos e mitigações**
- **Próximo passo** — sugestão de comando (`/kairos-forge:mobilizar SPEC-<NNN>`)

### 7. Confirmação ao usuário

```
✅ SPEC-NNN-<slug>.md criada por <Diego/Fernanda/etc>.

Plano tem N tarefas atribuídas a M agentes.

Próximos passos:
1. Revise a SPEC e ajuste se algo não bater
2. Quando aprovada, rode: /kairos-forge:mobilizar SPEC-NNN
   (ou execução sequencial: /kairos-forge:rodar)
3. Antes do PR: /kairos-forge:revisar
```

## Quando NÃO escrever SPEC

Pular SPEC é OK pra:

- Mudança em 1 arquivo, < 20 linhas
- Renomeação, formatação, atualização de dep menor
- Correção de typo

NÃO pule pra:

- Endpoint novo
- Mudança em schema de banco
- Integração com sistema externo
- Mudança em auth/autorização/PII
- Refactor que toca 3+ arquivos

## Regras

- **Não pule a interrogação.** Mesmo que o usuário insista que "é simples". Se for, sai rápido.
- **Não escreva código nesta skill.** Implementação é com `/mobilizar` ou invocação direta dos devs.
- **Não invente requisitos.** Se o arquiteto não conseguiu obter clareza, registre como pergunta aberta na SPEC e pare.
- **Nomeie agentes específicos no plano de implementação.** Não escreva "developer" genérico — escreva "Marina" ou "Lucas".
