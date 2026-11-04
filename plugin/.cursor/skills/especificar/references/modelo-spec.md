# Modelo da SPEC — seções e template mínimo

Referência do passo 6 de `/kairos-forge:especificar`. Leia na hora de escrever o arquivo
`docs/specs/SPEC-<NNN>-<slug>.md`: lista de seções obrigatórias, template mínimo,
prioridades e os estados de Status × conteúdo obrigatório em Verificação (que a
`/validar` lê por código).

## 6. Após aprovação, escrever a SPEC

Em `docs/specs/SPEC-<NNN>-<slug>.md` no projeto do usuário, com seções:

- **Origem** — issue, card ou link do design doc externo de onde o pedido veio, se houver (ADR-0040); o contrato fica aqui, o link é rastro
- **Contexto e problema** — qual dor real (referencie o RFC, se houver)
- **Objetivo** — uma frase
- **Não-objetivos** — o que está fora
- **Invariantes** — o que precisa ser verdade ao final
- **Desenho do programa** — em SPEC Pequena+ que cria ou muda interface: os tipos e as assinaturas públicas que a mudança cria ou altera, o caminho de chamada da T1 (por onde a entrada chega e onde o dado é gravado ou devolvido) e as **portas de mão única** com o formato literal (schema gravado, contrato de API pública, migração). Sai do `grafo.py contexto` dos arquivos tocados (passo 2.1). Decidir o formato antes de construir custa menos que discutir no review (Dex Horthy, *Why Software Factories Fail*); o que não é interface pública fica para quem constrói
- **Diagrama** — em SPEC Média+ com fluxo entre componentes, bloco Mermaid do desenho (à mão ou via `grafo.py mermaid`); o diagrama deriva do texto, nunca o substitui
- **Requisitos rastreáveis** — IDs estáveis, prioridade, critério de aceite **com valor concreto, nunca adjetivo** (ADR-0039) e status
- **Varredura** — em SPEC Média+, as nove dimensões que ninguém escreve sem lista: cada uma termina num requisito, numa proteção que já existe ou em `n/a` com motivo (tabela abaixo)
- **Plano de implementação** — tarefas atômicas, cada item ≤ 1 dia (a unidade de posse do quadro), com agente, arquivos, dependências e gates; **T1 é a fatia fim a fim** (ADR-0039); a coluna **Reusa** aponta o `arquivo:função` que já existe e a tarefa usa em vez de escrever de novo — é ela que o gate de duplicação do `/validar` cobra
- **Matriz de testes** — tipo de teste por requisito/tarefa, comando esperado e responsável; o tipo é a camada da escada de verificação que o `/validar` sobe do barato ao caro
- **Riscos e mitigações**
- **Perguntas abertas** — se houver qualquer incerteza bloqueante
- **Próximo passo** — sugestão de comando (`/kairos-forge:mobilizar SPEC-<NNN>`)

### Varredura das nove dimensões

O plano cobre o que alguém pensou; a varredura cobre o que ninguém escreve. Cada dimensão
termina num requisito (o ID), numa proteção que já existe (`existente — <onde>`) ou em
`n/a — <motivo>`. Dimensão que pede resposta de produto vira **pergunta aberta** (Pare e
Pergunte, ADR-0015), nunca critério inventado.

| Dimensão | O que cobrir |
|---|---|
| validação | limites, formatos, sanitização; URL que o servidor busca a pedido do usuário; limite que só desabilita um botão também precisa recusar a requisição que pula o botão |
| modos de falha | tempo limite, gravação parcial, rollback |
| idempotência | retentativa segura, chave de deduplicação |
| autorização | quem chama o quê, limite de taxa; consulta que revela pessoas |
| concorrência | corrida, garantia de ordem |
| ciclo de vida do dado | expiração, exclusão, backfill; o que o usuário digitou volta igual depois de salvar, reabrir e salvar |
| falha de dependência | o que acontece quando a chamada externa falha |
| transições de estado | transições válidas e as guardas de cada uma |
| observabilidade | log, métrica, trace |

Concorrência e observabilidade são as que mais se escondem: nenhuma aparece até falhar. O
critério precisa observar a dimensão — duplicata recusada porque a linha já existe não diz
nada sobre duas requisições chegando juntas.

Adaptado da varredura da skill tlc-spec-lean (Tech Leads Club, CC-BY-4.0).

Use este template mínimo:

```markdown
# SPEC-NNN — <título>

**Origem:** <issue #123 · card · link do design doc externo — ou "conversa">

## Contexto e problema

## Objetivo

## Não-objetivos

## Invariantes

## Desenho do programa

- **Tipos e assinaturas públicas:** `<arquivo>` · `<assinatura>` (novo · muda · intocado)
- **Caminho da T1:** <entrada> → <função> → <função> → <onde grava ou devolve>
- **Portas de mão única:** <schema · API pública · migração — com o formato literal> (ou "nenhuma")

## Requisitos rastreáveis

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| <SLUG>-01 | Como <persona>, quero <ação>, para <resultado>. | P1 | WHEN <evento> THEN <resultado> SHALL <comportamento verificável, com valor: "em ≤ 2 s", "status 403" — nunca "rápido", "correto">. | Pendente | — |

Prioridades:
- **P1**: necessário para entregar a mudança
- **P2**: importante, mas pode sair em follow-up se explicitamente aprovado
- **P3**: desejável, não bloqueia entrega

Estados de Status × conteúdo obrigatório em Verificação:
- **Pendente** → Verificação = `—` (ainda não iniciado).
- **Em progresso** → Verificação começa com `em progresso: <o que ainda falta>`. Conta 0.5 no progresso da SPEC.
- **Concluído** → Verificação começa com `verificado: <como confirmei> (<dd/mm>)`. Sem essa linha, a `/validar` trata como "sem evidência" e bloqueia P1.

## Varredura

- validação: <ID · existente — <onde> · n/a — <motivo>>
- modos de falha:
- idempotência:
- autorização:
- concorrência:
- ciclo de vida do dado:
- falha de dependência:
- transições de estado:
- observabilidade:

## Plano de implementação

| Tarefa | Agente | Requisito(s) | Arquivos/áreas | Reusa | Depende de | Done when | Gate |
|---|---|---|---|---|---|---|---|
| T1 | [Lucas] | <SLUG>-01 | `api/<slug>/`, `app/<slug>/` | `lib/http.ts:responderErro` | - | **Fatia fim a fim:** o caso mínimo atravessa todas as camadas e é testável de ponta a ponta. | `npm test -- <slug>` |
| T2 | [Carlos] | <SLUG>-02 | `migrations/` | — | T1 | Schema completo aplicado e rollback definido. | `npm test -- migrations` |

## Matriz de testes

| Requisito | Tipo | Responsável | Comando/gate | Evidência esperada |
|---|---|---|---|---|
| <SLUG>-01 | unit/integration/e2e/manual | [Ricardo] | `<comando real ou a definir>` | Caminho feliz + 1 erro cobertos; o teste novo falha sem a mudança. |

Tipo é a **camada** da escada de verificação (ADR-0039): `unit` roda antes de `integration`, que roda antes de `e2e` — o `/validar` sobe a escada do barato ao caro e para na primeira camada vermelha.

## Riscos e mitigações

## Perguntas abertas

## Validação

Antes de `/kairos-forge:revisar`, rode:

`/kairos-forge:validar SPEC-NNN`

## Próximo passo
```
