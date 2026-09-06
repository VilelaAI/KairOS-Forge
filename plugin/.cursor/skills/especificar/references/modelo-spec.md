# Modelo da SPEC — seções e template mínimo

Referência do passo 6 de `/kairos-forge:especificar`. Leia na hora de escrever o arquivo
`docs/specs/SPEC-<NNN>-<slug>.md`: lista de seções obrigatórias, template mínimo,
prioridades e os estados de Status × conteúdo obrigatório em Verificação (que a
`/validar` lê por código).

## 6. Após aprovação, escrever a SPEC

Em `docs/specs/SPEC-<NNN>-<slug>.md` no projeto do usuário, com seções:

- **Contexto e problema** — qual dor real (referencie o RFC, se houver)
- **Objetivo** — uma frase
- **Não-objetivos** — o que está fora
- **Invariantes** — o que precisa ser verdade ao final
- **Diagrama** — em SPEC Média+ com fluxo entre componentes, bloco Mermaid do desenho (à mão ou via `grafo.py mermaid`); o diagrama deriva do texto, nunca o substitui
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

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| <SLUG>-01 | Como <persona>, quero <ação>, para <resultado>. | P1 | WHEN <evento> THEN <resultado> SHALL <comportamento verificável>. | Pendente | — |

Prioridades:
- **P1**: necessário para entregar a mudança
- **P2**: importante, mas pode sair em follow-up se explicitamente aprovado
- **P3**: desejável, não bloqueia entrega

Estados de Status × conteúdo obrigatório em Verificação:
- **Pendente** → Verificação = `—` (ainda não iniciado).
- **Em progresso** → Verificação começa com `em progresso: <o que ainda falta>`. Conta 0.5 no progresso da SPEC.
- **Concluído** → Verificação começa com `verificado: <como confirmei> (<dd/mm>)`. Sem essa linha, a `/validar` trata como "sem evidência" e bloqueia P1.

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
