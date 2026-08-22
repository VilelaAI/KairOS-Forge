# ADR-0035 — Mobilizar em qualquer CLI: o quadro sai da sessão

- **Status:** aceito
- **Data:** 2026-08-21
- **Versão:** v0.28.0

## Contexto

Desde a v0.1 o `/kairos-forge:mobilizar` se declarava **exclusivo do Claude Code**. A
skill abria com um "Pré-requisito CRÍTICO" mandando parar imediatamente em qualquer
outro CLI, e a tabela de limitações registrava `❌ skill avisa e sugere rodar` para
Codex, OpenCode e Cursor. O usuário que rodava `/mobilizar` no Codex recebia uma recusa
educada e a sugestão de trocar de ferramenta.

O motivo declarado eram quatro ferramentas nativas: `TeamCreate`, `TaskCreate`,
`TaskUpdate` e `SendMessage`. A justificativa nunca foi auditada contra o que os outros
CLIs de fato oferecem — ela foi escrita quando o Codex ainda não tinha multi-agente, e
sobreviveu por inércia depois que passou a ter.

Auditando agora, contra o código do `openai/codex` e não contra a suposição:

| O que o mobilizar usa | Equivalente no Codex |
|---|---|
| `Agent` com `team_name` | `spawn_agent` |
| `SendMessage` | `send_message`, `followup_task` |
| encerrar teammate | `close_agent` |
| esperar | `wait_agent` |
| listar quem está vivo | `list_agents` |
| `TeamCreate` (namespace) | `task_name` canônico (V2) |
| **`TaskCreate`/`TaskUpdate`/`TaskList`** | **não existe** |

Cinco dos seis mapeiam diretamente. O sexto — **o quadro compartilhado de tarefas com
dependências** — não tem equivalente em nenhuma versão do multi-agente do Codex; o
`update_plan` é uma lista de afazeres privada do agente, não um quadro com arestas,
posse e contagem.

A auditoria foi então estendida aos outros dois CLIs, e o resultado desmonta a premissa
inteira:

| | Lançar em paralelo | Falar com worker em voo | Allow-list |
|---|---|---|---|
| Claude Code | `Agent` + `team_name` | `SendMessage` | enforced |
| Codex CLI | `spawn_agent` | `send_message`/`followup_task` | parcial (`apply_patch` sobrevive) |
| OpenCode | `task` (várias chamadas numa mensagem; `background` opcional) | `task_id` retoma a sessão | **enforced** (`permission`) |
| Cursor | subagents orquestrados pelo agente principal | ❌ | instrução (`readonly`) |

**Os quatro sabem lançar worker em paralelo.** Nenhum dos três, além do Claude Code,
tinha o quadro. Ou seja: a skill estava presa a um CLI por **uma** ferramenta, não por
quatro — e essa uma é a que menos precisava ser do CLI.

## Decisão

**1. O quadro sai da sessão e vira arquivo do repositório.** `scripts/quadro.py`, estado
em `.agents/quadro/<slug>.json`. Mesmo movimento que o ADR-0029 fez com a máquina de
estados do `/entregar`, pelo mesmo motivo.

Não reimplementamos Agent Teams em cada CLI — tiramos do CLI a única peça que não era
portável. Cada CLI passa a precisar apenas do que já sabe fazer: lançar worker em
paralelo e esperar.

**2. O quadro é um só, inclusive no Claude Code.** Onde há Agent Teams, o quadro nativo
vira espelho de UI e a fonte da verdade continua sendo o arquivo. Dois quadros com
regras diferentes é a receita para os dois discordarem — e a divergência apareceria
justamente no caso em que ninguém está olhando.

**3. As três regras que eram prosa viram código.** Todas existiam na skill e todas
valiam enquanto havia um humano lendo:

- **Teto de onda (ADR-0033).** "No máximo 6 teammates simultâneos" era um número numa
  tabela. Agora `prontas` não devolve o sétimo. O default coincide com o do Codex
  (`agents.max_concurrent_threads_per_session = 6`), o que evita que os dois tetos
  briguem.
- **Posse de arquivo (ADR-0024).** "Nunca paralelize escrita no mesmo arquivo" dependia
  de o teammate obedecer o prompt. Agora duas tarefas com posse sobreposta não saem na
  mesma onda — a serialização acontece antes de alguém escrever, não depois.
- **Contagem antes de declarar pronto.** "Nunca sintetize por cima de resultado parcial"
  era um pedido. Agora `encerrar` recusa quadro com tarefa aberta sem lacuna declarada.

**4. As 71 personas viram definições nativas de subagent em cada CLI.**
`sync-multi-cli.py` passa a gerar, a partir de `agents/<id>.md`:

- `.codex/agents/<id>.toml` — `description` como gatilho, corpo como
  `developer_instructions`, `model: opus` → `model_reasoning_effort = "high"`,
  `shell_tool = false` nos 14 consultivos;
- `.opencode/agent/<id>.md` — `mode: subagent` (sem ele o OpenCode carrega a persona mas
  a tool `task` não a oferece, e a onda paralela não acontece), com a allow-list
  traduzida para `permission` e `task: deny` em todos;
- `.cursor/agents/<id>.md` — já existia desde o ADR-0011.

Sem isso o spawn receberia a persona colada no prompt — persona como texto, não como
papel.

**5. `estado --json` do quadro entra no contrato assinado (ADR-0034)**, junto com
`ciclo` e `contrato`.

**6. A instalação por CLI vira comando, não parágrafo de README.** Codex e OpenCode
descobrem subagents no diretório de config *deles*, não no do plugin — então havia um
`cp` manual entre "instalei o plugin" e "as personas funcionam". Passo manual num
caminho que ninguém revisita erra em silêncio, e o sintoma (a persona não resolve, o
spawn cai no agente genérico) não aponta para a causa.

`sync-multi-cli.py instalar --cli <codex|opencode|cursor|todos> [--escopo global]
[--dry-run]` faz a cópia com três garantias que o `cp` não dava: é idempotente, remove
órfão de persona renomeada, e **preserva arquivo do usuário** quando o nome coincide —
detectado por uma marca de arquivo gerado, não por heurística. Um agente próprio chamado
`carlos-dba.toml` sobrevive ao sync; sem a marca, ele seria destruído em silêncio.

## Sobre a posse de arquivo: a heurística é declarada

Decidir se dois globs se sobrepõem não tem resposta barata no caso geral. O `quadro.py`
usa uma heurística explícita, com o viés escolhido de propósito: **falso positivo custa
paralelismo, falso negativo custa o arquivo** — então ela erra conservador.

Desempata só nos dois casos em que a precedência é inequívoca, e são os mesmos que
CODEOWNERS, gitignore e tsconfig já usam: **o caminho mais fundo manda** (Pablo em
`src/components/ui/**` manda ali dentro mesmo com Marina em `src/components/**`) e **o
nome mais específico manda** (Ricardo em `**/*.test.*` manda nos testes dentro da pasta
da Marina). O que sobra é colisão de verdade, e colisão de verdade serializa.

Recurso compartilhado que não é arquivo — API com rate limit, ambiente de teste único —
o quadro **não** vê. Essa aresta continua sendo julgamento da Laura, declarado com
`depender`. O quadro cobre a classe que dá para cobrir e não finge cobrir a outra.

## Consequências

**A tabela de limitações muda nos quatro CLIs.** `/mobilizar` passa de `❌` para `✅` no
Codex, no OpenCode e no Cursor. O que continua variando é a ergonomia, não a capacidade:

- **OpenCode** — o paralelismo está na *forma de chamar*: uma onda é **uma** mensagem
  com várias chamadas de `task`. Chamar-esperar-chamar é fila com passos a mais, e o
  resultado final é o mesmo, só mais lento — por isso o erro passa despercebido.
  `background: true` (atrás de `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`) é
  conveniência, não requisito.
- **Cursor** — não há tool de spawn: o agente principal orquestra os subagents. A Laura
  descreve a onda inteira de uma vez e registra os retornos. **Não há canal para falar
  com worker em voo**, então bloqueio resolvido vira subagent novo com contexto
  completo, e o prompt inicial precisa carregar tudo.

A degradação para "sem paralelismo" continua existindo — para qualquer CLI que não tenha
nenhum dos quatro mecanismos — mas deixa de ser o caso comum.

**A allow-list atravessa em dois CLIs e não nos outros dois, e isso está escrito.** No
Claude Code `tools:` é enforced; no OpenCode `permission: {edit: deny}` também é. Um role
file do Codex aplica só um conjunto fechado de chaves — `sandbox_mode` **não** está entre
elas, ao contrário do que boa parte dos tutoriais afirma, e `shell_tool = false` tira o
shell mas não o `apply_patch`. No Cursor a allow-list degrada para `readonly`.

Então "Helena não modifica código" é **fronteira** no Claude Code e no OpenCode e
**instrução** no Codex e no Cursor. Onde é só instrução e a supervisão humana sai do
caminho, a fronteira que sobra é a física: worktree por teammate (ADR-0024). A skill e as
referências dizem isso ao usuário, por CLI, em vez de anunciar uma garantia uniforme que
não existe.

**O painel ganha uma quinta fonte.** `painel.py` renderiza as mobilizações junto com
SPEC, ciclo, relatórios e trajetória — o checkpoint do `/mobilizar` já chamava o painel,
e agora o que ele desenha inclui o quadro.

**O guardrail ganha um quarto inegociável.** `.agents/quadro/**` entra ao lado de
`execucoes/`, `guardrails.json` e `ciclo/`: quem fecha a tarefa é a Laura via script, não
o worker escrevendo o próprio Done. Worker que fecha a própria tarefa é juiz em causa
própria sobre o próprio Definition of Done.

## Alternativas descartadas

**Reimplementar Agent Teams no Codex, em prosa dentro da skill.** Era o caminho óbvio:
uma seção "se for Codex, faça assim". Descartado porque o quadro em prosa é exatamente o
que o ADR-0029 já tinha condenado no arco — quem contaria as tarefas, resolveria as
dependências e decidiria se pode encerrar seria o modelo, sobre o próprio trabalho.
Portabilidade não vale o preço de devolver ao julgamento o que já tinha virado código.

**Manter a exclusividade e melhorar só a mensagem de recusa.** Era a leitura mínima do
problema relatado. Descartada ao auditar: cinco das seis primitivas já existiam do outro
lado. A recusa não estava protegendo o usuário de uma limitação real, estava repassando
uma suposição desatualizada.

**Um quadro por CLI, cada um usando o nativo.** Descartado pelo item 2: duas fontes de
verdade divergem, e as regras determinísticas (teto, posse, contagem) teriam de ser
reimplementadas em cada lado — reimplementação diverge na primeira regra nova, que é o
mesmo argumento do ADR-0034 para publicar contrato em vez de deixar o consumidor
adivinhar.

## Nota de corroboração

O papel embutido `worker` do próprio Codex instrui a "atribuir explicitamente
**ownership** da tarefa (arquivos / responsabilidade)... para evitar conflitos de merge"
e a sempre avisar workers de que eles "não estão sozinhos no repositório". É o Passo 6
desta skill, escrito por outra equipe a partir do mesmo problema.

A diferença é onde a regra mora: lá ela é pedida no prompt, aqui ela é **serializada
pelo quadro** antes de alguém escrever. Pedir a um worker que não colida funciona até o
dia em que dois pedidos razoáveis se cruzam.
