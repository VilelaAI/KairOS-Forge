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

Ou seja: a skill estava presa a um CLI por **uma** ferramenta, não por quatro. E essa
uma é a que menos precisava ser do CLI.

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

**4. As 71 personas viram roles de subagent do Codex.** `sync-multi-cli.py` passa a
gerar `.codex/agents/<id>.toml` a partir de `agents/<id>.md`, com `description` como
gatilho de roteamento, corpo como `developer_instructions`, `model: opus` traduzido para
`model_reasoning_effort = "high"` e `shell_tool = false` nos 14 consultivos. Sem isso o
`spawn_agent` só receberia a persona colada no prompt — persona como texto, não como
papel.

**5. `estado --json` do quadro entra no contrato assinado (ADR-0034)**, junto com
`ciclo` e `contrato`.

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

**A tabela de limitações muda.** `/mobilizar` passa de `❌` para `✅` no Codex. Cursor e
OpenCode continuam sem paralelismo — mas a degradação melhora: em vez de "não dá, use
rodar", a Laura oferece abrir o quadro e executar em série, entregando o mesmo rastreio,
os mesmos gates e a mesma recusa de encerrar escondendo lacuna. O que falta nesses CLIs
é o paralelismo, não o rastreio.

**A allow-list não atravessa inteira, e isso está escrito.** No Claude Code, `tools:` é
enforced. Um role file do Codex aplica só um conjunto fechado de chaves; `sandbox_mode`
**não** está entre elas (ao contrário do que boa parte dos tutoriais afirma), e
`shell_tool = false` tira o shell mas não o `apply_patch`. Então no Codex "Helena não
modifica código" é instrução, não fronteira — igual ao Cursor. Onde a supervisão humana
sai do caminho, a fronteira que sobra é a física: worktree por teammate (ADR-0024). A
skill e a referência dizem isso ao usuário em vez de anunciar garantia que o CLI não dá.

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
