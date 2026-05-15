---
name: especificar
description: Inicia o fluxo de spec-driven development para uma feature ou mudança. Use no início de qualquer trabalho não-trivial — antes de escrever código. Aciona Laura (Tech Lead) que classifica complexidade, decide arquitetos, registra requisitos rastreáveis e gates. Resultado é uma SPEC em docs/specs/SPEC-NNN-slug.md pronta para /mobilizar, /rodar e /validar.
---

# Especificar — fluxo spec-driven

Você está sendo invocado para iniciar o ciclo de design **antes** da implementação.

## Regra de ouro

Não codifique. Não chame teammate de implementação. Esta skill produz **artefato textual** — uma SPEC — que servirá de contrato para `/kairos-forge:mobilizar` ou execução manual depois.

## Fluxo

### 1. Laura entra primeiro

Invoque o agente `laura-tech-lead`. Ela vai:

- Ouvir a descrição do usuário
- Classificar o tamanho usando a matriz abaixo
- Decidir quais arquitetos da fábrica entram
- Definir o nível de cerimônia necessário

### 1.1. Auto-sizing obrigatório

Laura classifica antes de perguntar demais:

| Tamanho | Sinais | Saída esperada |
|---|---|---|
| **Trivial** | 1 arquivo, < 20 linhas, typo, rename, formatação | Não criar SPEC. Encaminhar execução direta. |
| **Pequeno** | 1-2 arquivos, sem schema/API/auth, baixo risco | SPEC curta ou plano inline com gate de teste. |
| **Médio** | 3+ arquivos, endpoint novo, tela nova, regra de negócio | SPEC completa com requisitos rastreáveis. |
| **Grande** | Banco + API + UI, integração externa, dados críticos | SPEC completa + tarefas atômicas + matriz de testes. |
| **Complexo** | Auth, PII, segurança, migração irreversível, decisão arquitetural | SPEC completa + ADR sugerido + validação formal antes de PR. |

Se for trivial, pare e diga por que a SPEC não compensa. Se for pequeno ou maior, continue.

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
- **Requisitos rastreáveis** — IDs estáveis, prioridade, critério de aceite e status
- **Plano de implementação** — tarefas atômicas, cada item ≤ 1 dia, com agente, arquivos, dependências e gates
- **Matriz de testes** — tipo de teste por requisito/tarefa, comando esperado e responsável
- **Riscos e mitigações**
- **Perguntas abertas** — se houver qualquer incerteza bloqueante
- **Próximo passo** — sugestão de comando (`/kairos-forge:mobilizar SPEC-<NNN>`)

Use este template mínimo:

```markdown
# SPEC-NNN — <título>

## Contexto e problema

## Objetivo

## Não-objetivos

## Invariantes

## Requisitos rastreáveis

| ID | Requisito | Prioridade | Critério de aceite | Status |
|---|---|---|---|---|
| <SLUG>-01 | Como <persona>, quero <ação>, para <resultado>. | P1 | WHEN <evento> THEN <resultado> SHALL <comportamento verificável>. | Pendente |

Prioridades:
- **P1**: necessário para entregar a mudança
- **P2**: importante, mas pode sair em follow-up se explicitamente aprovado
- **P3**: desejável, não bloqueia entrega

## Plano de implementação

| Tarefa | Agente | Requisito(s) | Arquivos/áreas | Depende de | Done when | Gate |
|---|---|---|---|---|---|---|
| T1 | [Carlos] | <SLUG>-01 | `migrations/` | - | Schema aplicado e rollback definido. | `npm test -- migrations` |

## Matriz de testes

| Requisito | Tipo | Responsável | Comando/gate | Evidência esperada |
|---|---|---|---|---|
| <SLUG>-01 | unit/integration/e2e/manual | [Ricardo] | `<comando real ou a definir>` | Caminho feliz + 1 erro cobertos. |

## Riscos e mitigações

## Perguntas abertas

## Validação

Antes de `/kairos-forge:revisar`, rode:

`/kairos-forge:validar SPEC-NNN`

## Próximo passo
```

Se o projeto tiver `contextos/testes.md`, use os comandos de lá. Se não tiver, registre o gate como `<a definir>` e recomende preencher esse contexto.

### 7. Confirmação ao usuário

```
✅ SPEC-NNN-<slug>.md criada por <Diego/Fernanda/etc>.

Plano tem N tarefas atribuídas a M agentes.

Próximos passos:
1. Revise a SPEC e ajuste se algo não bater
2. Quando aprovada, rode: /kairos-forge:mobilizar SPEC-NNN
   (ou execução sequencial: /kairos-forge:rodar)
3. Após implementar: /kairos-forge:validar SPEC-NNN
4. Antes do PR: /kairos-forge:revisar
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
- **Todo requisito P1 precisa de critério de aceite verificável.** Se não dá para verificar, ainda não é requisito pronto.
- **Todo item de implementação precisa de gate.** Pode ser teste automatizado, build, lint ou validação manual explícita.
