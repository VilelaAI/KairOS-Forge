# Mobilizar no Codex CLI — protocolo, limites e instalação

Referência de `/kairos-forge:mobilizar` quando o CLI é o Codex. Leia antes de lançar a
primeira onda. Tudo aqui foi conferido contra o código do `openai/codex`, não contra
posts de blog — vários deles descrevem campos que o Codex não aplica (veja "Erros
comuns" no fim).

## As ferramentas que existem

O Codex tem duas gerações de multi-agente. Descubra qual está ativa pelos nomes que
você enxerga; o fluxo do mobilizar funciona nas duas.

| Papel no mobilizar | V1 (default) | V2 (`features.multi_agent_v2 = true`) |
|---|---|---|
| Lançar worker | `spawn_agent` → `{agent_id, nickname}` | `spawn_agent` (exige `task_name`) → `{task_name, nickname}` |
| Esperar | `wait_agent` (status final por agente) | `wait_agent` (avisa quem tem novidade; o conteúdo vem na notificação) |
| Falar sem interromper | `send_input` | `send_message` |
| Mandar nova rodada | `send_input` com `interrupt` | `followup_task` (dispara turno se o worker está ocioso) |
| Listar quem está vivo | — | `list_agents` |
| Interromper | `send_input{interrupt: true}` | `interrupt_agent` |
| Encerrar | `close_agent` | `close_agent` |

Parâmetros de `spawn_agent` que o mobilizar usa:

| Campo | Uso no mobilizar |
|---|---|
| `task_name` | o id da tarefa do quadro (`t1_migration`). Minúsculas, dígitos e `_`. |
| `agent_type` | o id do agente da fábrica: `carlos-dba`, `marina-frontend`, … |
| `message` | o prompt do teammate (template do Passo 5 da skill) |
| `fork_turns` | **use `"none"`.** Veja "Por que `fork_turns: none`" abaixo. |
| `reasoning_effort` | o tier: `low` (rápido), omitido (padrão), `high`/`xhigh` (preciso) |
| `model` | omita, salvo pedido explícito — o filho herda o seu |

## Por que `fork_turns: "none"`

O default é `all`: o filho nasce com **todo o seu histórico**. Para o mobilizar isso é o
oposto do que se quer, por dois motivos.

O primeiro é custo: herdar a conversa inteira multiplica o contexto por teammate, e é
justamente o que o `/mobilizar` evita ao mandar subgrafo em vez de documento.

O segundo é mais sério. O valor de um time paralelo vem de os teammates serem
**independentes**; se todos herdam a sua análise, herdam também as suas suposições, e o
Ricardo deixa de ser capaz de descobrir que o Lucas entendeu o requisito errado — ele já
entendeu errado junto. Contexto herdado transforma seis pareceres em um parecer repetido
seis vezes.

Então: `fork_turns: "none"` e contexto explícito no `message`. Se um teammate precisa de
fato que está no seu histórico, ponha o fato no prompt dele — ou no grafo, que é onde
esse tipo de fato deveria estar.

## Espera: o laço correto

`wait_agent` **não** devolve o trabalho pronto. No V2 ele devolve "fulano tem novidade";
o conteúdo chega como notificação. Então o laço é:

1. `quadro.py prontas <slug>` → o que pode entrar agora.
2. `quadro.py iniciar <slug> <T> --agente <task_name>` para cada uma.
3. `spawn_agent` para cada uma (todas antes de esperar — senão você serializou o time).
4. `wait_agent` até alguém terminar.
5. Leia o resultado, registre com `quadro.py concluir` (ou `bloquear`).
6. `close_agent` em quem terminou. **Agente concluído continua ocupando vaga de
   concorrência até ser fechado** — esquecer isso trava a próxima onda com um erro que
   parece do teto de onda mas é seu.
7. Volte ao passo 1.

O passo 3 é o que separa time de fila: lançar-esperar-lançar-esperar é execução
sequencial com passos a mais.

## Os dois tetos

| Teto | Onde | Default |
|---|---|---|
| Threads concorrentes | `agents.max_concurrent_threads_per_session` no `config.toml` | 6 |
| Profundidade de aninhamento | `agents.max_depth` (só V1) | 1 |

O teto de onda do mobilizar (6, ADR-0033) coincide com o default do Codex. Não é
coincidência útil por acaso: se o usuário baixar o teto do Codex, **baixe o
`--teto-onda` junto** ao abrir o quadro, senão o quadro libera tarefas que o CLI recusa
lançar e você descobre isso no meio da onda.

`max_depth = 1` significa que um teammate seu **não** pode abrir subagentes próprios.
Para o mobilizar isso é bom: a decomposição é da Laura, e sub-time dentro de teammate é
como o file ownership vira ficção.

## As 71 personas como `agent_type`

`.codex/agents/<id>.toml` é gerado por `scripts/sync-multi-cli.py` a partir de
`agents/<id>.md`. Cada arquivo traz:

- `name` — o id, que é o que vai em `agent_type`;
- `description` — usada pelo Codex no roteamento;
- `developer_instructions` — a persona inteira;
- `nickname_candidates` — o primeiro nome, para o worker aparecer como "Carlos";
- `model_reasoning_effort = "high"` nos agentes que são `model: opus` no canônico;
- `[features] shell_tool = false` nos consultivos (14 dos 71).

**Instalação.** O Codex procura roles em `<config>/agents/*.toml`, com `<config>` sendo
`~/.codex` (pessoal) ou `.codex/` do projeto. Se o plugin não estiver nesse caminho:

```bash
mkdir -p ~/.codex/agents
cp <plugin>/.codex/agents/*.toml ~/.codex/agents/
```

Confira com `codex` iniciando uma sessão: `spawn_agent` deve listar os tipos
disponíveis. Se `agent_type: "carlos-dba"` responder "agent type is currently not
available", os roles não estão instalados — a fábrica ainda mobiliza, mas com agentes
genéricos e a persona colada no prompt, que é o degrade, não o alvo.

## Limite honesto: a allow-list não atravessa inteira

No Claude Code, `tools:` no frontmatter é **enforced**: Helena não escreve porque não
recebe a ferramenta. No Codex, um role file aplica só um conjunto fechado de chaves —
`developer_instructions`, `model`, `model_reasoning_effort`, `model_reasoning_summary`,
`model_verbosity`, `personality`, `service_tier`, e `features`/`skills` **apenas para
desabilitar**.

Consequências que você deve conhecer antes de prometer qualquer coisa ao usuário:

- `sandbox_mode` em role file **não é aplicado** (apesar do que muito tutorial diz).
  O sandbox do filho é o da sessão.
- `shell_tool = false` funciona e tira execução de comando, mas **`apply_patch`
  continua disponível**. Ou seja: o consultivo perde o shell, não a caneta.

Então, no Codex, "Helena não modifica código" é **instrução**, não fronteira — igual ao
Cursor, diferente do Claude Code. Quando a supervisão humana sair do caminho, a fronteira
que sobra é a física: worktree por teammate (Passo 6.1 da skill). Não anuncie ao usuário
uma garantia que este CLI não dá.

## Erros comuns

| Sintoma | Causa |
|---|---|
| A próxima onda não lança, mesmo com tarefa pronta | worker concluído não foi fechado — `close_agent` |
| Teammates chegam todos à mesma conclusão | `fork_turns` no default (`all`) — use `"none"` |
| "agent type is currently not available" | roles não instalados em `<config>/agents/` |
| Quadro libera 6, Codex recusa a partir da 4ª | `max_concurrent_threads_per_session` menor que o `--teto-onda` |
| `spawn_agent` recusa o `task_name` | só minúsculas, dígitos e `_` |
| Worker some com o trabalho feito | `wait_agent` devolve aviso, não conteúdo — leia a notificação antes de fechar |

## O que o Codex já concorda com a gente

Vale registrar, porque não é confirmação de conveniência: o papel embutido `worker` do
próprio Codex instrui, com estas palavras, a "atribuir explicitamente **ownership** da
tarefa (arquivos / responsabilidade)... para evitar conflitos de merge" e a sempre
avisar workers de que eles "**não estão sozinhos no repositório**" e não devem reverter
a edição de outro.

É o Passo 6 desta skill, escrito por outra equipe a partir do mesmo problema. A diferença
é que ali a disciplina é pedida no prompt e aqui ela é **serializada pelo quadro** antes
de alguém escrever — pedir a um worker que não colida funciona até o dia em que dois
pedidos razoáveis se cruzam.
