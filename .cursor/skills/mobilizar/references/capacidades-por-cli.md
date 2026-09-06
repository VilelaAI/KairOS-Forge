# Capacidades por CLI — o quadro portável e o adaptador de lançamento

Referência de `/kairos-forge:mobilizar`: por que o quadro saiu do CLI (ADR-0035), o que
cada CLI sabe fazer, como lançar o worker em cada um e o que muda em relação a
`/kairos-forge:rodar`. Leia no Passo 0 quando ainda não souber em qual CLI está, e no
Passo 5 na hora de lançar a primeira onda.

## O que esta skill precisa (e o que não precisa)

Por muito tempo esta skill se declarou "exclusiva do Claude Code", citando quatro
ferramentas nativas. Auditando os quatro CLIs, **todos sabem lançar worker em paralelo**
— o que faltava em todos, menos no Claude Code, era **o quadro compartilhado de tarefas
com dependências.** Era ele sozinho que prendia a skill a um CLI.

A solução não foi reimplementar Agent Teams em cada CLI. Foi **tirar o quadro do CLI**:

> O quadro é um arquivo do repositório (`.agents/quadro/<slug>.json`, via
> `quadro.py`), não um objeto da sessão.

Isso resolve o problema de portabilidade e, de quebra, dois que o quadro nativo tinha:
ele **sobrevive** a reset de contexto e troca de CLI, e as decisões que dependiam do
seu julgamento — o que pode entrar agora, quantos cabem, quem colide com quem, se dá
para dizer que acabou — passam a ser **de código** (ADR-0035).

## Passo 0 — descubra o que este CLI sabe fazer

Antes de qualquer coisa, veja quais ferramentas você tem. Não pergunte ao usuário o que
dá para verificar sozinho.

| Capacidade | Claude Code | Codex CLI | OpenCode | Cursor |
|---|---|---|---|---|
| Lançar worker paralelo | `Agent` com `team_name` | `spawn_agent` | `task` (várias chamadas numa mensagem) | subagents (o agente principal orquestra) |
| Esperar por worker | `TaskList` | `wait_agent` | retorno da tool; ou notificação se `background` | retorno do subagent |
| Falar com worker | `SendMessage` | `send_message`, `followup_task` | `task` com `task_id` (retoma a sessão) | ❌ — reponha contexto num novo subagent |
| Encerrar worker | `shutdown_request` | `close_agent` | encerra sozinho ao responder | encerra sozinho |
| **Quadro com dependências** | **`quadro.py`** | **`quadro.py`** | **`quadro.py`** | **`quadro.py`** |

Decida assim, na ordem — pare no primeiro que casar:

1. **`Agent` com `team_name`?** → Claude Code. (Requer
   `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`; sem isso as ferramentas não aparecem e você
   cai no caso 4.)
2. **`spawn_agent`?** → Codex CLI. Leia
   `${CLAUDE_PLUGIN_ROOT}/skills/mobilizar/references/codex.md` **antes de lançar**.
3. **`task` com `subagent_type`?** → OpenCode. Lance a onda inteira em **uma** mensagem
   com várias chamadas — é o que torna a onda paralela em vez de fila. Com
   `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true` dá para usar `background: true` e
   seguir trabalhando; sem ele, o retorno das chamadas concorrentes já basta.
4. **Está no Cursor?** → o agente principal orquestra os subagents de
   `.cursor/agents/` em paralelo. Você não os lança por tool: descreve a onda que o
   quadro liberou e deixa a orquestração acontecer, registrando cada retorno no quadro.
   Sem canal de mensagem para worker em voo — se faltar contexto, abra um subagent novo
   com o contexto completo em vez de tentar corrigir o que já está rodando.
5. **Nenhum deles?** → sem paralelismo. Diga isso e ofereça a saída honesta:

```
Este CLI não expõe lançamento de worker em paralelo, então não há o que coordenar
em paralelo.

- /kairos-forge:rodar faz o mesmo trabalho em modo sequencial.
- Se quiser o rastreio de dependências, gates e contagem mesmo em série, eu abro o
  quadro (quadro.py) e executo as tarefas eu mesmo, na ordem que ele liberar — mesmo
  relatório final, mesma recusa de encerrar com lacuna escondida.
```

O quadro funciona em qualquer CLI porque é só Python e um arquivo. **O que varia entre
CLIs é como se lança e como se espera — não o que é uma tarefa, nem quando ela pode
entrar, nem quando dá para dizer que acabou.**

## Como lançar o worker, por CLI

| | Claude Code | Codex CLI | OpenCode |
|---|---|---|---|
| Lançar | `Agent(name: "<id>", team_name: "forge-<slug>", prompt: …)` | `spawn_agent(task_name: "<id>", agent_type: "<id>", message: …, fork_turns: "none")` | `task(subagent_type: "<id>", description: …, prompt: …)` |
| Paralelismo | uma chamada por teammate | uma chamada por teammate, **antes** de esperar | **todas as chamadas numa só mensagem** |
| Tier preciso | agente com `model: opus` já é | `reasoning_effort: "high"` | `model` do agente |
| Esperar | acompanhar `TaskList` | `wait_agent` | retorno das chamadas |
| Corrigir rota | `SendMessage` | `send_message` / `followup_task` | `task` com o `task_id` de volta |
| Encerrar | `SendMessage{type:"shutdown_request"}` | `close_agent` | automático |

Em todos, o id do agente é o mesmo (`carlos-dba`, `marina-frontend`): as 71 personas são
geradas como `.codex/agents/*.toml` (Codex), `.opencode/agent/*.md` (OpenCode) e
`.cursor/agents/*.md` (Cursor). Limites e instalação por CLI em `references/codex.md` e
`references/opencode-cursor.md`.

## Modos de invocação

| Comando | Quando usar |
|---|---|
| `/kairos-forge:mobilizar <spec>` | Implementar uma SPEC de `docs/specs/` em paralelo |
| `/kairos-forge:mobilizar <feature-livre>` | Sem SPEC formal — só uma descrição da tarefa |
| `/kairos-forge:mobilizar revisao <branch>` | Time de revisão (Helena + Patrícia + Vinícius) lê o diff em paralelo |

## Diferença prática vs `/rodar`

| | `/rodar` | `/mobilizar` |
|---|---|---|
| Execução | Sequencial, conversacional | Paralela, isolada |
| Contexto | Compartilhado | Isolado por teammate |
| File ownership | Não enforced | Quadro serializa colisão; worktree quando não há revisão humana |
| Rastreio | Conversa | Quadro em arquivo, sobrevive à sessão |
| Custo de tokens | Menor | Maior |
| Adequado pra | Discussão, design, code review | Implementação de SPEC |
| Requer | Nada além do plugin | Claude Code (Agent Teams) ou Codex (subagents) |
