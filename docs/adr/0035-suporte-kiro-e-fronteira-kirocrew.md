# ADR-0035 — Suporte ao Kiro CLI e a fronteira com o Kiro Crew

- **Status:** aceito
- **Data:** 2026-08-08
- **Versão:** v0.28.0

## Contexto

Análise do [KiroCrew](https://github.com/kirodotdev/KiroCrew) (Apache 2.0, AWS/Kiro) a
pedido do usuário, com duas perguntas explícitas: *"faz sentido adaptarmos o forge pra
suportar o KiroCrew?"* e *"faz sentido usar os dois juntos?"*.

A resposta depende de separar duas coisas que o nome junta:

| | O que é | Papel |
|---|---|---|
| **kiro-cli** | O agente. Terminal e ACP. | Um **CLI**, como Claude Code e Codex |
| **Kiro Crew** | Gateway: sessões, memória, agenda, aprovações, política, dashboard, Slack/Telegram | Um **orquestrador**, como o Hermes e o LionCode |

São perguntas diferentes com respostas diferentes.

### O kiro-cli é o CLI mais compatível que já avaliamos

O formato bate quase linha a linha com o que já é canônico aqui:

| Peça | Claude Code | Kiro CLI |
|---|---|---|
| Skills | `skills/<n>/SKILL.md` | `.kiro/skills/<n>/SKILL.md` — **mesmo formato** |
| Agentes | `agents/<id>.md` com `tools:` | `.kiro/agents/<id>.json` com `tools`/`allowedTools` |
| Hooks | `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop` | `agentSpawn`, `userPromptSubmit`, `preToolUse`, `postToolUse`, `stop` |
| Bloqueio | exit 2 no `PreToolUse`, stderr vai pro modelo | **idem** |

A última linha é a que decide. O Cursor e o Codex CLI não têm hook bloqueante, e por
isso a telemetria do ADR-0021 e os guardrails do ADR-0022 **não funcionam** neles — a
dimensão Autonomia do `/auditar` pontua 0 e o `/validar` pula a corroboração de
trajetória. No Kiro elas funcionam. É o primeiro CLI depois do Claude Code onde o
harness inteiro roda, e não só a pasta de prompts.

E a allow-list é de verdade: no Cursor ela degrada para `readonly: true` porque não há
onde declarar ferramenta por ferramenta. No Kiro há.

### O Kiro Crew não é um CLI — é o consumidor que o ADR-0034 previu

O Gateway roda cada agente como `kiro-cli acp --agent <id>`. Ele não substitui o forge:
ele resolve o que o forge deliberadamente não resolve — persistir entre sessões, agendar,
receber webhook, falar em Slack/Telegram, segurar aprovação, sandbox de OS.

Isso é exatamente a divisão do ADR-0032 com o LionCode e do ADR-0019 com o Hermes:

> **Kiro Crew é o *quando/onde*. O forge é o *como*.**
> O Gateway responde "o agente continua depois que você fecha o terminal".
> O forge responde "o que ele fez presta".

O ADR-0034 já tornou `ciclo.py estado --json` e as três fences superfície pública
versionada, *"para o kairos-symphony dirigir o arco em vez de reimplementá-lo"*. O Kiro
Crew é a segunda instância dessa mesma porta. Não há nada novo a construir do lado do
arco — só a porta a documentar.

### O atrito real: o Crew tem memória e sintetiza skills sozinho

O Kiro Crew mantém memória, lições e **skills sintetizadas de padrões repetidos**,
editáveis pelo dashboard. O forge tem três camadas (ADR-0009/0010) com **o repositório
como fonte da verdade**, 18 skills curadas, teto de 500 linhas (ADR-0027) e skill nova
entrando por ADR.

Se os dois escrevem, há duas verdades — e a que o usuário versiona perde para a que o
Gateway reescreve sozinho.

## Decisão

### A — O Kiro CLI vira alvo de primeira classe do sync

`scripts/sync-multi-cli.py` passa a gerar `.kiro/` junto de `.agents/` e `.cursor/`:

```
.kiro/agents/<id>.json              71 configs (prompt, tools, allowedTools, hooks)
.kiro/skills/<verbo>/SKILL.md       18 skills (mirror — mesmo formato)
.kiro/steering/kairos-forge.md      contexto sempre carregado (papel do banner)
.kiro/scripts/, .kiro/templates/    suporte referenciado pelas skills
```

`model:` não é traduzido (os identificadores não mapeiam 1:1) — mesma decisão do Cursor.

### B — Uma só tabela de ferramentas, em `scripts/kiro.py`

A allow-list dos agentes e os matchers dos hooks precisam concordar. Se divergirem, o
guardrail fica pendurado num matcher que nunca casa — um medidor que mede nada e diz
que está tudo bem, o modo de falha que o CI já corrigiu uma vez no
`check-agent-security.py`. Por isso a tabela é única:

| Claude Code | Kiro | Agentes |
|---|---|---|
| `Read` | `fs_read` | 71 |
| `Grep` / `Glob` | `grep` / `glob` | 71 |
| `Write` / `Edit` / `NotebookEdit` | `fs_write` | 54 |
| `Bash` | `execute_bash` | 30 |
| `WebSearch` / `WebFetch` | `web` | 6 |

Ferramenta sem entrada na tabela **quebra o sync** em vez de gerar um agente com
allow-list silenciosamente menor do que a declarada.

`allowedTools` (o que roda sem confirmar) recebe só a leitura pura — `fs_read`, `grep`,
`glob`. Escrita e shell continuam pedindo confirmação: é a fronteira que o Claude Code
aplica por padrão e o critério de admissão do ADR-0024. Quem quiser mais autonomia
afrouxa do lado do Kiro, conscientemente.

### C — O adaptador de payload mora na fronteira, não nos scripts canônicos

`guardrail.py` e `execucao.py` falam o formato do Claude Code. O Kiro entrega outro. Em
vez de espalhar `if kiro:` dentro deles, `kiro.py adaptar <script> <args>` normaliza o
stdin e repassa, **propagando o código de saída intacto** — é o que faz o exit 2
continuar bloqueando.

Verificado ponta a ponta: escrita em caminho sagrado bloqueia (exit 2), `rm -rf /`
bloqueia (exit 2), escrita comum passa (exit 0), e a trajetória completa
(`sessao_inicio` → `prompt` → `escrita` → `sessao_fim`) chega no `telemetria.py resumo`.

### D — O que NÃO adotamos do Kiro Crew

A memória, as lições e a síntese automática de skills do Gateway **não viram camada do
forge**. O repositório continua a fonte da verdade: `decisoes/`, `.agents/`,
`contextos/` e o grafo são do forge; o episódico é do Gateway (o papel que hoje é do
ai-memory). Skill que o Gateway escreve sozinho não entra em `skills/` — lá se entra
por ADR, com teto de 500 linhas.

E o forge **não depende** do Kiro Crew. A ponte é opcional e por contrato, como a do
Hermes. Somos MIT e multi-CLI por ADR-0004; amarrar o arco a um Gateway de um fornecedor
específico trocaria independência por conveniência.

## Consequências

### Positivas

- Kiro é o **segundo CLI com o harness completo** — telemetria, guardrails bloqueantes
  e allow-list real. A tabela de limitações deixa de ter uma só coluna cheia.
- 71 agentes e 18 skills chegam sem reescrita: o canônico não mudou, só ganhou um alvo.
- O `release.py check` passa a verificar as configs geradas — `tools` não vazio,
  `prompt` não vazio, e `preToolUse` com os matchers que realmente casam.
- Sob Kiro Crew, os agentes do forge rodam como `kiro-cli acp --agent laura-tech-lead`.
  A fábrica ganha 24/7, agenda e Slack sem escrever gateway nenhum.

### Negativas e riscos

- **Mais um mirror gerado.** Terceiro alvo do sync, terceira superfície de paridade no
  CI. Custo real, mitigado por ser tudo derivado e verificado.
- **Duas pontes com o mesmo papel.** `hermes/` e Kiro Crew ocupam o mesmo lugar. Não
  resolvemos isso agora; fica registrado que resolver é devido.

### O que ficou por verificar

Honestidade sobre o que não foi testado contra um Kiro instalado — nenhuma destas
afirmações foi confirmada em execução, e as três mudam o desenho se estiverem erradas:

1. **Hooks sob ACP.** A documentação da CLI descreve os hooks e há relato de exit 2
   bloqueando no terminal (macOS), mas existe [issue aberta](https://github.com/kirodotdev/Kiro/issues/8465)
   afirmando que os hooks *não disparam* em `kiro-cli chat` nem em `kiro-cli acp`. Como
   o Crew dirige o CLI por ACP, isso é exatamente o caminho que importa. **Mitigação já
   desenhada:** o Kiro Crew avalia todo tool call no gate PreToolUse *dele* antes de
   deixar o kiro-cli rodar — então sob Crew o `guardrail.py verificar` pendura ali, e
   não nos hooks do CLI. Sem hooks, degrada como Codex/Cursor: Autonomia pontua 0 e o
   `/validar` pula a corroboração. Comportamento honesto, não bug.
2. **O evento `stop`.** Documentado na lista de eventos, ausente do exemplo oficial de
   config. Se não existir, a trajetória perde o evento de fim.
3. **A categoria `web`.** É categoria aceita no campo `tools`, não nome de tool builtin.
   Se sumir, o sintoma é a config recusada na carga — barulhento, que é como se quer.

### Fora de escopo, registrado

`/mobilizar` continua exigindo Agent Teams do Claude Code. O Kiro tem subagents e o Crew
tem `spawn_run`, o que faz dele o candidato mais promissor a um segundo caminho para o
paralelismo — mas prometer sem testar seria inventar capacidade. Por ora, o steering
aponta para `rodar`, como nos demais CLIs.
