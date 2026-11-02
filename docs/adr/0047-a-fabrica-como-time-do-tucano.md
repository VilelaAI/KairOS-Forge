# ADR-0047 — A fábrica como time do Tucano

- **Status:** aceito, experimental até o primeiro projeto real importado no app
- **Data:** 2026-10-31
- **Versão:** v0.40.0

## Contexto

O pedido foi ter uma visão completa da operação da fábrica, separada por projeto, e poder
delegar uma tarefa para o Claude Code, outra para o Codex e outra para o OpenCode. O
[Tucano](https://github.com/eduwxyz/tucano) (Apache 2.0, local, Mac/Linux/Windows) já faz
quase tudo isso por conta própria:
- agentes com nome trabalham em canais, cada um com o seu harness e o seu modelo;
- toda ação com efeito fora passa por um gateway MCP com aprovação amarrada à chamada exata;
- tem rotinas, uso por agente, um computador Linux isolado por agente e PR por aprovação.

Três caminhos foram pesados:

| Caminho | O que ganha | Por que não agora |
|---|---|---|
| Console no `kairos-symphony` | o daemon e o contrato do arco já existem | falta tudo da interface, e o symphony só fala com o Claude Code |
| Fork do Tucano com a fábrica dentro | runtime e interface prontos | o Tucano tinha 4 dias e seis versões; e ele isola a CLI de propósito, então a fábrica não entra como plugin |
| **A fábrica como time que o Tucano importa** | nenhuma linha no Tucano; testável hoje | os guardrails em hook não rodam lá dentro (abaixo) |

O isolamento foi conferido no código (`src/core/engines/`):
- **Claude Code:** sobe com `--tools ''`, `--setting-sources ''` e `--strict-mcp-config`;
- **Codex:** roda com HOME próprio, `--ignore-user-config` e skills desligadas;
- **OpenCode:** sobe com a config do projeto desligada.

Tudo que o agente faz passa pelas ferramentas do gateway. O que o Tucano **importa** é
um time: um Markdown com um bloco ` ```json tucano-team ` (versão 1) contendo agentes,
skills, canais e rotinas (`src/core/team.ts`).

## Decisão

### 1. `.tucano/` é o quinto alvo do sync

O `sync-multi-cli.py` gera `.tucano/kairos-forge-entrega.md` ao lado de `.agents/`,
`.codex/agents/`, `.opencode/agent/` e `.cursor/`, pelo novo `scripts/tucano.py`.
Como os outros espelhos, ele é marcado como gerado (guardrail e `.gitattributes`) e tem a
paridade conferida com `plugin/`.

### 2. O pacote de entrega, não as 71 personas

O pacote tem sete agentes: Laura, Joana, Lucas, Marina, Ricardo, Helena e Patrícia. O
Tucano roda quatro respostas em paralelo, e 71 agentes na barra lateral atrapalham. Outros
perfis viram pacotes quando houver uso.

O harness vem do modelo:
- **quem constrói** pensa com o Claude Code;
- **quem revisa** (Helena, Patrícia) pensa com o Codex, a mesma regra de juiz de outra
  família do ADR-0031;
- **o Ricardo** vai para o OpenCode quando a instalação recebe `--opencode-modelo`.

### 3. A persona ganha um preâmbulo, e a skill leva as references

A instrução de cada agente é o corpo da persona precedido de um preâmbulo que diz o que
muda dentro do Tucano:
- **o canal é o projeto:** o canal tem o nome da pasta emprestada, porque o agente não vê o
  tópico do canal;
- **os scripts da fábrica estão em `.kairos-forge/scripts/`;**
- **o estado mora no repositório;**
- **passa-se a vez com @handle;**
- **os guardrails em hook não rodam ali:** respeite-os e rode `guardrail.py verificar`
  antes do PR;
- **merge é do humano;**
- **skill da fábrica não se muda com `propor_skill`.**

Persona sem Write/Edit na allow-list ganha a linha "consultivo", como o `readonly` do Cursor.

Seis skills entram: `especificar`, `entregar`, `analisar-ameacas`, `validar`, `revisar` e
`auditar`. O conteúdo de `references/` vai embutido no corpo, porque o Tucano lê uma receita
só (`ler_skill`), e `${CLAUDE_PLUGIN_ROOT}` vira `.kairos-forge`.

### 4. `tucano.py instalar` prepara o projeto

Roda na raiz do projeto:
- copia os scripts que as skills citam e os templates para `.kairos-forge/`;
- grava `.kairos-forge/time-tucano.md` com o canal no nome da pasta.

Antes de escrever, valida o time pelas regras do importador do Tucano. A primeira delas é a
que mais engana: **modelo desconhecido vira `sonnet` sem aviso** na importação. Por isso a
lista de modelos é fechada, e `--opencode-modelo` em branco recusa a instalação.

## Consequências

- **O pedido funciona sem fork.** Você importa o time, empresta a pasta, liga o computador
  dos agentes e chama `@laura` no canal do projeto. Cada agente aparece com o seu harness, e
  o PR chega como pedido de aprovação.
- **Os guardrails em hook não rodam dentro do Tucano**, porque ele não deixa hook entrar na
  CLI, e no computador do agente comando roda sem perguntar.
  - O Docker protege a máquina, mas dentro da pasta emprestada nada impede `--no-verify`.
  - O que segura: push só para `agent/*`, PR por aprovação, `guardrail.py verificar` antes do
    PR e no CI.
  - É o mesmo nível do Codex e do OpenCode hoje. Trazer o piso de volta exige a política no
    gateway do Tucano (o "degrau 3").
- **O arco não anda sozinho até o fim.** O Tucano encadeia no máximo 3 respostas de agente por
  mensagem humana, então um `/entregar` completo pede "segue" no meio. O estado está no
  `ciclo.py`, e o "segue" retoma do ponto certo.
- **Todos os agentes montam a mesma pasta**, sem worktree por teammate (ADR-0024). No começo,
  um agente escreve código por projeto de cada vez.
- **O importador real é TypeScript e não roda no nosso CI.** O validador do `tucano.py` repete
  as regras do Tucano v0.2.2, e o teste trava esse formato. O upstream muda rápido: a primeira
  prova de verdade é importar o arquivo no app.

## Alternativas consideradas

- **Fork agora.** Adiado, pelos dois motivos da tabela. Ele volta como degrau 3 se a política
  no gateway e a visão por projeto não entrarem no Tucano como ponto de extensão. A conversa
  com o autor vem antes do fork.
- **Conector MCP da fábrica** (estado do ciclo, quadro, caixa, `prova`, `qualidade` como
  ferramentas do gateway, com aprovação nas sensíveis). É o próximo degrau: este ADR resolve
  primeiro a tradução das pessoas e das receitas.
- **Importar as 71 personas.** Recusado pelo motivo do item 2.
