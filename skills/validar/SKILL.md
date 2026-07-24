---
name: validar
description: Valida uma implementação contra uma SPEC rastreável antes da revisão pré-PR. Use depois de /kairos-forge:mobilizar ou /kairos-forge:rodar e antes de /kairos-forge:revisar. Compara requisitos, tarefas, critérios de aceite, gates de teste e evidências. Produz relatório em docs/specs/validacoes/.
---

# Validar — aceite contra SPEC

Você está sendo invocado para verificar se o trabalho implementado cumpre o contrato da SPEC.

## Regra de ouro

Não implemente correções nesta skill. Você pode ler arquivos, analisar diff, rodar comandos de teste/lint/build e salvar relatório. Se encontrar falha, registre objetivamente e recomende qual agente deve corrigir.

## Quando usar

- Depois de implementar uma SPEC com `/kairos-forge:mobilizar`.
- Depois de executar uma feature por `/kairos-forge:rodar`.
- Antes de `/kairos-forge:revisar`, para separar aceite funcional de code review.
- Quando o usuário perguntar "isso cumpre a spec?".

## Fluxo

### 1. Localizar a SPEC

Aceite entradas como:

- `/kairos-forge:validar SPEC-001`
- `/kairos-forge:validar docs/specs/SPEC-001-exportar-csv.md`
- `/kairos-forge:validar` com uma única SPEC modificada na branch

Se houver ambiguidade, pergunte qual SPEC validar.

### 2. Ler contrato e contexto

Leia:

- `docs/specs/SPEC-<NNN>-<slug>.md`
- `contextos/testes.md`, se existir
- `decisoes/estado-operacional.md`, se existir
- Diff atual contra a base (`git diff origin/main...HEAD`, ou base equivalente)

Extraia:

- Requisitos rastreáveis e prioridades
- Critérios de aceite
- Tarefas planejadas
- Gates e comandos esperados
- Perguntas abertas

### 3. Validar rastreabilidade

Monte uma matriz:

| Requisito | Prioridade | Evidência no diff | Teste/gate | Status SPEC | Verificação SPEC | Status validação |
|---|---|---|---|---|---|---|
| EXP-01 | P1 | arquivo/linha ou commit | comando rodado | Concluído | `verificado: pnpm test (12/06)` | aprovado/falhou/sem evidência |

Regras:

- P1 sem evidência no diff bloqueia validação.
- P1 sem teste/gate exige justificativa explícita.
- Pergunta aberta não resolvida bloqueia se impactar P1.
- P2 pode virar follow-up se o relatório registrar a decisão.
- P3 não bloqueia, mas deve aparecer como pendência.
- **Status "Concluído" na SPEC sem célula Verificação iniciando com `verificado:` = "sem evidência" automático.** Não importa se o código está no diff: marcar pronto sem prova de execução é o anti-padrão que o ritual existe para impedir. Inspirado no `briefing.md` do Replit-Orchestrator.
- **Status "Em progresso" sem célula Verificação iniciando com `em progresso:` = falha de contrato.** O autor da SPEC deve listar o que ainda falta. Conta 0.5 no percentual da SPEC se o conteúdo for plausível.
- SPECs antigas (anteriores à coluna Verificação) ficam fora dessas duas últimas regras — registrar como "SPEC anterior ao ritual de verificação" no veredicto.

### 3.5. Fundamentar afirmações no grafo (se existir)

Se o projeto tem `.agents/grafo/entidades.jsonl`, use o grafo como base de fatos do avaliador (ADR-0009) — validação deixa de ser "parece certo" e vira checagem de fato:

1. Para cada entidade central da SPEC, serialize o contexto: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/grafo.py subgrafo "<entidade>" --saltos 2`.
2. Cheque as afirmações da SPEC e das células `verificado:` contra as arestas. Afirmação confirmada cita a aresta: `(A) --[predicado]--> (B) [fonte: arquivo]`.
3. Afirmação **contradita** pelo grafo entra nos achados com a evidência específica: "a tripla (X, depende de, Y) não existe no grafo; o que existe é (X, substitui, Z), da fonte W".
4. Afirmação **ausente** do grafo não é aprovada nem rejeitada em silêncio: registre como "sem aresta no grafo" e **escale ao usuário** — pode ser erro da SPEC ou lacuna de cobertura do grafo (nesse caso, recomende `/kairos-forge:mapear-conhecimento atualizar`).
5. Declare no relatório a data da última construção do grafo (de `.agents/grafo/GRAFO.md`) — fundamentação em grafo velho vale menos e o leitor precisa saber.

Sem grafo no projeto, pule esta etapa sem penalizar o veredicto.

### 4. Rodar gates

Rode apenas comandos relevantes e seguros:

- gates declarados na SPEC
- comandos de `contextos/testes.md`
- comandos padrão evidentes do projeto (`npm test`, `npm run lint`, `pytest`, `go test ./...`) quando não houver contexto

Se um comando for destrutivo, exigir segredo, depender de serviço externo ou tiver custo alto, não rode; registre como "não executado" e explique.

### 5. Acionar especialistas conceitualmente

Produza parecer em primeira pessoa, sem criar código:

- **Ricardo** valida cobertura e gates.
- **Patrícia** valida critérios de aceite e regressões.
- **Helena** entra se a SPEC tocar auth, PII, autorização, input externo ou segurança.
- **Carlos** entra se houver migration, SQL, índice, RLS ou dados persistentes.
- **Ada** entra se houver UI acessível.

### 6. Salvar relatório

Salve em:

`docs/specs/validacoes/VALIDACAO-<SPEC-NNN>-YYYY-MM-DD.md`

Formato:

```markdown
# Validação — SPEC-NNN — YYYY-MM-DD

**Veredicto:** aprovado / aprovado com ressalvas / bloqueado
**Base analisada:** <branch/base>
**Gates rodados:** <lista>

## Matriz de rastreabilidade

| Requisito | Prioridade | Evidência | Gate | Status |
|---|---|---|---|---|

## Achados bloqueantes

## Ressalvas

## Evidências de teste

## Fundamentação no grafo

(Se `.agents/grafo/` existir: afirmações confirmadas com aresta citada, contradições com a evidência do grafo, e afirmações sem aresta escaladas ao usuário. Data da última construção do grafo.)

## Follow-ups aceitos

## Próximo passo

- Se bloqueado: corrigir com <agente(s)> e rodar `/kairos-forge:validar SPEC-NNN` de novo.
- Se aprovado: rodar `/kairos-forge:revisar`.
```

### 7. Responder ao usuário

Resumo curto:

```markdown
Validação da SPEC-NNN: <veredicto>.

P1: X/Y aprovados.
Gates: A passaram, B falharam, C não rodaram.
Relatório salvo em `docs/specs/validacoes/VALIDACAO-SPEC-NNN-YYYY-MM-DD.md`.

Próximo passo: <corrigir com agente X | rodar /kairos-forge:revisar>.
```

## Veredictos

- **Aprovado**: todos os P1 têm evidência, critérios de aceite cobertos e gates relevantes passaram.
- **Aprovado com ressalvas**: P1 ok, mas há P2/P3 pendentes ou gate não rodado com justificativa aceitável.
- **Bloqueado**: qualquer P1 sem evidência, critério de aceite falhando, gate essencial falhando ou pergunta aberta bloqueante.

## Regras

- **Não confunda validação com revisão.** Validação responde "cumpre a SPEC?". Revisão responde "o código está seguro, testado, performático e pronto para PR?".
- **Não aprove no escuro.** Sem evidência, status é "sem evidência", não "aprovado".
- **Não esconda P2/P3.** O usuário pode aceitar follow-up, mas precisa aparecer.
- **Marca "Concluído" na SPEC só com `verificado:` na coluna Verificação.** Diff existe + teste passou + arquivo/comando/URL citado no `verificado:`. Confiança em "código está aí" não é evidência.
- **PT-BR em tudo.**
