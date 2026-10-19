# Início rápido — kairos-forge em 15 minutos

Este guia leva você de "acabei de ouvir falar de plugin" para "tenho a fábrica de 71 agentes rodando no meu projeto".

## Pré-requisitos

- Claude Code instalado (`npm install -g @anthropic-ai/claude-code`)
- Git
- Python 3 — hooks, guardrails, telemetria, painel, `ciclo.py` e `quadro.py` são scripts Python, só biblioteca padrão. O `sync-multi-cli.py instalar` (personas para outros CLIs) exige 3.10+
- `jq` — usado pelo lembrete de Definition of Done do Claude Code
- Um projeto onde você queira aplicar a fábrica (qualquer linguagem, qualquer stack)
- **Opcional, para `/mobilizar` no Claude Code**: `export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

> Este guia segue o fluxo do **Claude Code**. Usa Codex CLI, OpenCode ou Cursor? A instalação por CLI está na seção Instalação do [README](../README.md). Depois de instalado, as skills e o ciclo abaixo são os mesmos nos quatro, `/mobilizar` incluído (ADR-0035). O que muda de verdade são os hooks: o Claude Code tem todos; o Cursor tem telemetria e guardrail por `.cursor/hooks.json` (as classes de escrita só no modo CLI); o Codex, só o banner de início de sessão; o OpenCode, nenhum. Sem hook não há trajetória — o efeito disso está no Passo 4.

## Passo 1 — instalar o plugin

### Via marketplace

```
/plugin marketplace add VilelaAI/kairos-forge
/plugin install kairos-forge@kairos-forge
/reload-plugins
```

### Local (desenvolvimento)

```bash
git clone https://github.com/VilelaAI/kairos-forge.git
cd seu-projeto
claude --plugin-dir ../kairos-forge
```

Após instalar, no início da sessão você deve ver (lista de skills abreviada aqui):

```
🔥 kairos-forge v0.36 ativo — 71 agentes (40 core + 31 apoio em 10 squads) | skills: /kairos-forge:onboardar mapear-arquitetura … evoluir | Para mobilizar paralelo: export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

## Passo 2 — onboarding do projeto

```
/kairos-forge:onboardar
```

Entrevista de 7 perguntas. Reserve 15 minutos. Use ditado por voz se ajudar — quanto mais contexto, melhor.

Ao final você terá:

- `CLAUDE.md` preenchido na raiz do projeto (e `AGENTS.md`, se o time também usa Codex/Cursor/OpenCode)
- `contextos/` com contexto de projeto, stack, convenções, restrições e testes
- `decisoes/log.md`
- `decisoes/estado-operacional.md`
- `docs/specs/` com `criticas/`, `validacoes/` e `revisoes/` (um relatório por gate do arco) e `docs/adr/`
- `.agents/memory/` (índice de memórias de incidente) e `.agents/grafo/` (esquema do grafo de conhecimento)

## Passo 3 — primeira feature

### O caminho curto: uma skill até o PR

```
/kairos-forge:entregar quero exportar relatorios em CSV no dashboard
```

Rode numa branch própria, com git limpo — é pré-condição do arco. A fábrica declara
o orçamento e planeja com **três paradas suas**: entendimento, abordagem e aprovação
da SPEC. Antes da terceira, dois críticos que não escreveram a SPEC a atacam
(ADR-0033). Em feature Pequena, conduzida em sessão, as duas primeiras viram uma
mensagem só, com a abordagem recomendada como premissa (ADR-0038).

Aprovada, a SPEC é **selada por digest**: se requisito, critério ou plano mudar
depois, veredicto verde é recusado até você aceitar a versão nova
(`ciclo.py reaprovar`). Daí a fábrica constrói, valida, corrige o que bloqueou,
revisa, corrige o que era crítico e abre o PR. Falha na crítica, na validação ou na
revisão volta ao agente responsável — não a você. Quem decide o próximo passo é o
`ciclo.py`, não o agente (ADR-0029); merge e deploy continuam seus.

O orçamento é por gate — crítica, validação e revisão, cada um com o seu — e conta
**rodadas sem progresso**, não rodadas (ADR-0032): se os achados
bloqueantes caem de 5 para 2, a rodada não é cobrada; se continuam 5, é. Convergir não
é patinar, e a contagem vem do relatório em disco, não da alegação do agente. Um teto
absoluto vale por cima, porque progresso lento demais também é motivo para chamar você.

É o modo recomendado quando você confia no fluxo e quer o resultado. As seções
abaixo mostram as mesmas etapas **uma a uma**, que é como você aprende o que a
fábrica faz em cada ponto — e como você conduz quando quer decidir no meio.

### 3a. (Brownfield) Mapear arquitetura antes de mexer

Se o projeto já existe e tem dívida estrutural, comece por um mapa honesto:

```
/kairos-forge:mapear-arquitetura
```

Diego coordena (com Fernanda/Thiago/Rafael conforme dimensões). Saída: `docs/arquitetura/MAPA-YYYY-MM-DD.md` com inventário, acoplamento, duplicação, bounded contexts e plano incremental de decomposição. Pule este passo se for greenfield ou se você já conhece bem a estrutura.

### 3a-bis. (Sistema herdado) Diagnosticar antes de escolher a briga

Se você herdou o sistema e não sabe o que atacar primeiro:

```
/kairos-forge:diagnosticar
```

Rafael conduz. A fábrica **mede** o que dá para medir (churn, concentração de autoria nos hotspots, razão teste/produção, dependências, dívida marcada), pontua seis dimensões com a rubrica publicada no próprio relatório, e devolve os achados ordenados por impacto × esforço com roadmap em três horizontes — em `docs/diagnosticos/`.

Duas coisas que ele **não** faz, de propósito: não promete ganho sem base (faixa com origem declarada, ou "não estimável com o acesso atual"), e não corrige nada — cada achado sai encaminhado para `/otimizar`, `/migrar` ou `/especificar`.

### 3b. Especificar antes de codar

```
/kairos-forge:especificar quero exportar relatorios em CSV no dashboard
```

Laura entra como Tech Lead, classifica a feature, e aciona os arquitetos relevantes:

> **Laura:** "Oi, Laura aqui — Tech Lead. Pelo escopo, vou chamar o Diego pra desenhar o fluxo e a Fernanda pra olhar o lado de dados. Camila, valida o escopo MVP comigo."
>
> **Diego:** "Diego aqui, Sistemas. Antes de desenhar — esse export é síncrono ou agendado? Quantas linhas em média?"
>
> **Camila:** "Camila aqui, PM. Fica como MVP só CSV mesmo? PDF fica pra V2?"

Eles interrogam, propõem 2-3 abordagens e recomendam uma (feature Média ou maior; na Pequena, seguem com a recomendada como premissa registrada — ADR-0038), e produzem `docs/specs/SPEC-001-exportar-relatorio-csv.md` com requisitos rastreáveis, critérios de aceite, gates e plano de implementação **agente por agente**.

Duas regras do plano valem saber (ADR-0039): a primeira tarefa é uma **fatia fim a fim** — um caminho fino que atravessa todas as camadas e já é testável —, e critério de aceite tem **valor, não adjetivo** ("em ≤ 2 s", "status 403", nunca "rápido" ou "robusto").

Antes de a SPEC chegar a você, **dois críticos que não a escreveram atacam o documento** (ADR-0033) — premissa, requisito, plano e testabilidade — e o relatório vai para `docs/specs/criticas/`. Era a única etapa do arco sem contraditório: a validação tem Ricardo e Patrícia, a revisão tem Helena e Patrícia, e a SPEC tinha só o autor. O parser cobra dois nomes distintos, porque um olhar só é revisão, não crítica.

### 3c. (Feature sensível) Modelar ameaças antes de implementar

Se a SPEC tocar auth, PII, billing, multi-tenant, upload, integração externa ou IA:

```
/kairos-forge:analisar-ameacas SPEC-001
```

Helena coordena (com Carlos/Marcos/Thiago/Gabriel/Renata conforme escopo). Saída: `docs/seguranca/AMEACAS-<slug>-YYYY-MM-DD.md` com ativos, trust boundaries, perfis realistas de atacante, abuse paths e mitigações priorizadas. Vira insumo direto para a SPEC e para o `/kairos-forge:revisar` depois.

### 3c-bis. (Feature com UI) Desenhar antes de construir

```
/kairos-forge:desenhar SPEC-001
```

Isabela conduz, com Pablo no sistema de design e Ada na acessibilidade. Saída: `docs/design/DESIGN-001-<slug>.md` com fluxos, os cinco estados de cada view e critérios visuais que o `/validar` consegue cobrar. O sistema de design do projeto mora em `DESIGN.md` na raiz, dono Pablo (ADR-0040); depois de implementado, `/kairos-forge:desenhar verificar DESIGN-001` confere o resultado contra o desenho da feature e contra o `DESIGN.md`. Sem UI, pule.

### 3d. Implementar — escolha entre dois modos

#### Modo conversacional (sequencial)

```
/kairos-forge:rodar
```

Os agentes do plano da SPEC entram em sequência, cada um se apresentando, colaborando entre si por nome. Bom pra **entender** o que está acontecendo. Mais lento, mais tokens.

#### Modo paralelo (time sobre um quadro)

```
/kairos-forge:mobilizar SPEC-001
```

Laura abre um quadro de tarefas (`quadro.py`, estado em `.agents/quadro/`), registra cada tarefa da SPEC com dono, posse de arquivo, gate e dependências, e lança em ondas o que o quadro libera. Paralelo não é tudo ao mesmo tempo: o endpoint do Lucas espera a migration do Carlos se lê a saída dela (`--depende`), enquanto um componente da Marina que não depende de nenhum dos dois entra na mesma onda.

Quem decide é código, não prosa (ADR-0035/0036): o quadro solta no máximo 6 tarefas por onda, serializa posse de arquivo sobreposta, bloqueia por tempo limite o worker que sumiu e devolve a vaga (`varrer`), desfaz em ordem inversa a tarefa que se revelou inválida e só o que foi construído sobre ela (`compensar`), e recusa `encerrar` com tarefa aberta sem lacuna declarada.

O isolamento é proporcional à supervisão (ADR-0024): com humano revisando o PR, o ownership declarado no prompt basta. Em execução autônoma — ninguém lendo o diff — a Laura usa **worktree por teammate**, e aí o conflito deixa de ser questão de disciplina e vira impossibilidade física.

Roda nos quatro CLIs. No Claude Code, **requer** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` na sessão (o `TeamCreate` é só espelho de UI; o registro é o quadro). No Codex e no OpenCode, instale antes as personas: `python3 <plugin>/scripts/sync-multi-cli.py instalar --cli codex` (ou `--cli opencode`). No Cursor, o agente principal orquestra os subagents. Sem paralelismo, a skill não recusa: oferece o `/rodar` ou roda o mesmo quadro em série.

### 3e. Validar contra a SPEC

```
/kairos-forge:validar SPEC-001
```

Ricardo e Patrícia validam se a implementação cumpre os requisitos P1, critérios de aceite e gates declarados na SPEC. Se tocar auth, PII, dados persistentes ou UI, Helena, Carlos e Ada entram conceitualmente no parecer.

A validação também **confere a evidência contra o que realmente rodou** (ADR-0021): a célula `verificado:` da SPEC é escrita pelo agente que fez o trabalho, então ela é conferida contra a trajetória gravada pelos hooks. Alegação sem lastro vira "não corroborada" e bloqueia P1 igual a "sem evidência". Em CLI sem trajetória (Codex, OpenCode), essa etapa é pulada sem penalizar o veredicto.

E confere a prova, não só o verde (ADR-0039): `prova.py pre-patch` roda o teste novo contra a base, sem o patch — teste que passa ali não prova a mudança —, e `prova.py testes-alterados` lista teste existente modificado ou afrouxado no diff, cobrando a justificativa arquivo a arquivo. Os gates sobem do barato ao caro (lint e tipos → unitários → integração → e2e) e param no primeiro vermelho. Com a camada de código do grafo (3i), `grafo.py contexto` aponta os chamadores fora do diff — a regressão que ninguém olhou (ADR-0041).

### 3f. Revisar antes do PR

```
/kairos-forge:revisar
```

Helena (segurança) + Patrícia (QA) sempre rodam. Vinícius (performance), Marcos (DevOps), Carlos (DBA), Ada (acessibilidade) entram automaticamente conforme os arquivos modificados no diff. Cada um produz parecer em primeira pessoa, com severidade.

Veredicto agregado: ✅ aprovado / ⚠️ ressalvas / ❌ bloqueado.

Antes de publicar, cada revisor relê os próprios achados contra o diff — o código citado existe nessa linha? o problema acontece de fato nesse caminho? — e o que não sobrevive sai (ADR-0039). Achado que você decide não acatar não é apagado: ganha `· descartado: <motivo>` na própria linha, e `telemetria.py ruido` mede o ruído por revisor, número que o `/auditar` reporta.

O relatório abre com a **faixa de raio de explosão** (ADR-0031), porque ela é que decide o rigor — e a pergunta não é "quão confiante estou?", é **"quanto custa desfazer se estiver errado?"**:

| Faixa | Exemplo | O que fecha |
|---|---|---|
| 1 — reversível e contido | Texto de UI, teste, função isolada coberta | Gates verdes |
| 2 — reversível mas amplo | Utilitário compartilhado, schema, contrato interno, arquivo com 5+ importadores em `grafo.py contexto` | Gates verdes **e** trajetória limpa |
| 3 — difícil de reverter | Migration destrutiva, deleção, produção, dinheiro | **Humano decide, sempre** |

Um diff de 20 linhas na faixa 3 recebe mais escrutínio que um de 400 na faixa 1. Se o projeto tem histórico git, a taxa de reversão da área tocada (`diagnostico.py`) é evidência para subir de faixa — é o sinal que o modelo não consegue influenciar.

O relatório é salvo em `docs/specs/revisoes/` com um bloco de contrato (ADR-0032) que o `/kairos-forge:entregar` lê do disco. Duas regras nele valem saber: **zero 🔴 exige a lista do que foi lido** — "não achei nada" sem dizer onde procurou é ausência de busca, não ausência de defeito; e a fence é própria da revisão, nunca a mesma da validação.

### 3g. (Depois do merge) Lançar com gates

```
/kairos-forge:lancar
```

Marcos conduz, com Sérgio no health check e Renata na observação. Checklist com evidência (validação sem bloqueio em P1, revisão sem 🔴, CI verde, rollback da migration testado), **SIM explícito seu**, health check em três camadas e rollback com gatilho objetivo. Deploy de produção nunca sai sem a sua aprovação — nem de dentro do `/entregar`, que termina no PR.

### 3h. Ver onde tudo está, numa tela

A qualquer momento, do diretório do projeto:

```bash
python3 <plugin>/scripts/painel.py              # tudo
python3 <plugin>/scripts/painel.py SPEC-001     # uma SPEC
python3 <plugin>/scripts/painel.py --html quadro.html   # página pra mandar pra alguém
```

Sai o quadro vivo: requisitos por coluna (A fazer / Em progresso / Pronto), progresso da SPEC, estado do arco com as fichas de orçamento, veredicto dos três gates (crítica, validação, revisão) com a cobertura declarada, as mobilizações do quadro (onda, em voo, o que pode lançar, o que venceu o prazo) e a trajetória dos últimos 14 dias. O HTML é autocontido — abre sem rede.

Duas coisas que ele **não** faz, de propósito: não escreve nada (é renderização do estado canônico, nunca planilha paralela — ADR-0013), e não conta como "Pronto" requisito marcado `Concluído` sem `verificado:` — esse cai para "Em progresso" e aparece no aviso. Um quadro que somasse a palavra mostraria progresso que a própria `/validar` recusaria.

### 3i. Alimentar a memória da fábrica

Quando SPECs, ADRs e decisões acumularem (tipicamente depois das primeiras 2-3 features):

```
/kairos-forge:mapear-conhecimento construir
```

Olívia extrai entidades e relações com proveniência para `.agents/grafo/`. Nas rodadas seguintes, `/mobilizar` semeia os teammates com subgrafos em vez de contexto inteiro, `/validar` checa afirmações contra arestas ("a tripla X não existe; o que existe é Y, da fonte Z"), e perguntas multi-hop ("o que depende do componente que essa SPEC muda?") ganham resposta fundamentada.

A **camada de código** não espera documento acumular (ADR-0041): sai do próprio código, sem modelo, e é útil desde a primeira feature. O `construir` e o `atualizar` a regeneram; dá para rodar direto:

```bash
python3 <plugin>/scripts/grafo.py codigo                            # importa/herda/instancia por AST (Python, JS/TS, Go)
python3 <plugin>/scripts/grafo.py contexto src/api/relatorios.py    # quem importa, o que importa, quem cita o arquivo
```

O `codigo.jsonl` é regenerável a qualquer momento e nunca se edita à mão. O `contexto` é o que o `/validar` usa para achar chamadores fora do diff e o `/revisar` para contar importadores.

### Fora do fluxo, sob demanda

- `/kairos-forge:otimizar` — ciclo de catraca contra uma métrica que um comando mede: uma mudança por rodada, medir, manter ou reverter via git (ADR-0012).
- `/kairos-forge:migrar` — modernização de legado por estrangulamento, com Ivan: testes de caracterização, rota de corte com rollback, manter-ou-reverter por fatia (ADR-0018).

## Passo 4 — ritmo semanal

**Sextas-feiras** (ou quando lembrar):

```
/kairos-forge:auditar
```

Pontuação 0–120 nas 6 dimensões da fábrica (Fundação, Pipeline, Guardrails, Conhecimento, Estrutura e **Autonomia**). Vai vir baixa nas primeiras semanas — isso é normal. A Autonomia sai da telemetria, não da impressão: no Claude Code e no Cursor ela só ganha sentido depois de algumas semanas de ciclos registrados; no Codex e no OpenCode, sem hooks que gravem trajetória, fica em 0 — medida honesta, não bug. Ali, o caminho é rodar os checks equivalentes no CI do projeto (`templates/ci/`).

O relatório também estima o **nível da fábrica** (L2 Babá / L3 Gerente / L4 Fábrica) a partir da telemetria — não da impressão. L4 exige *todos* os critérios da linha, não a média: 90% de autonomia sem guardrail determinístico é classificado como pipeline sem supervisão, com essas palavras.

Em seguida:

```
/kairos-forge:evoluir
```

Antes das perguntas, a fábrica lê a própria trajetória (`telemetria.py resumo`, ADR-0037) e dá veredicto à evolução da semana anterior: `ajudou`, `piorou`, `sem efeito observado` ou `confundido` — este é o default quando não dá para isolar a causa, e adoção não conta como evidência (ADR-0043). Lição só sobe para `.agents/memory/` com contraste concreto.

Depois, 5 perguntas → identifica UMA capacidade pra construir na próxima semana.

Loop semanal é o que faz a fábrica ficar mais inteligente com o tempo.

## Passo 5 — o que o harness faz sozinho

Três coisas passam a acontecer sem você pedir. Vale saber o que são para não
estranhar.

**Os hooks gravam a trajetória.** Cada sessão anexa eventos a
`.agents/execucoes/*.jsonl` — quais gates rodaram, o que passou, quantas vezes
você precisou intervir. Nunca registra o texto dos seus prompts nem segredos
(comandos passam por redação). O `/onboardar` acrescenta `.agents/execucoes/` ao
`.gitignore`: é matéria-prima local, e o que sobe de camada é o número agregado na
auditoria.

Em voo, o mesmo registro avisa quando o agente patina — mesmo comando falhando em
sequência, escritas em produção sem gate no meio (ADR-0030). E, no Claude Code, o
primeiro arquivo de produção editado na sessão traz o lembrete da Definition of
Done, uma vez só (ADR-0038).

Para ver onde você está:

```bash
python3 <plugin>/scripts/telemetria.py resumo --dias 30
```

**Os guardrails podem bloquear.** Se um agente tentar `rm -rf /`, force-push em
`main`, escrever em `.env` ou marcar um requisito como "Concluído" sem a célula
`verificado:`, a ação é recusada e o motivo vai para o agente, que corrige. O
`guardrail.py` também recusa:

- ler segredo — `cat .env`, chave SSH, `*.pem` —, pelo shell ou pela tool `Read`
  (`grep NOME .env` passa: procurar o nome não é ler o valor);
- mexer na fiação dos hooks (`.cursor/hooks.json`, `.codex/hooks.json`, o bloco
  `hooks` de `.claude/settings*.json`);
- `rm -rf` com alvo em variável ou fora do projeto, e `shutdown`/`reboot`;
- editar artefato gerado pelo sync em vez do canônico;
- relatório de crítica, validação ou revisão com contrato malformado, ou "limpo"
  sem dizer o que examinou;
- abrir PR fora de estado durante um `/entregar`.

Duas regras nascem em `aviso` e deixam rastro em vez de bloquear (ADR-0039/0042):
edição em teste existente (o `/validar` cobra a justificativa) e o **gate de
parada** — sessão que escreveu produção sem gate verde depois não encerra em
silêncio.

Se um bloqueio atrapalhar algo legítimo, quem ajusta `.agents/guardrails.json` é
**você**, não o agente — ele não escreve a própria regra. `liberados` só libera
caminho de escrita (ex.: `.github/workflows/**`); `modos` rebaixa uma classe para
`aviso` (ex.: `{"contrato": "aviso"}`) ou promove `teste` e `parada` a
`bloqueio`. O piso não se configura: os quatro caminhos sagrados
(`.agents/execucoes/`, `.agents/guardrails.json`, `.agents/ciclo/`,
`.agents/quadro/`), a leitura de segredo, a fiação dos hooks, o `rm -rf` com alvo em
variável ou fora do projeto e o `shutdown`/`reboot`. Onde não há hook — Codex, OpenCode e, no Cursor, as classes de
escrita —, o mesmo guardrail roda em modo CLI (`guardrail.py verificar`), no CI ou
num pre-commit.

**A evidência passa a ser conferida.** O `/validar` cruza cada `verificado:` com
o que realmente rodou. Isso significa que uma SPEC otimista não passa mais só
porque o texto está bem escrito.

## Se você vem de PRD, Design Doc, RFC e task

A fábrica usa os mesmos documentos com outros nomes (ADR-0040):

| Na sua empresa | No forge | Onde |
|---|---|---|
| PRD (o porquê, a nível de produto) | Contexto, objetivo e Working Backwards da SPEC; Camila (PM) e o apoio-requisitos quando precisa de mais | `docs/specs/SPEC-NNN.md`, seções iniciais |
| Design Doc / TDD (problema + solução técnica de alto nível) | A SPEC: abordagem escolhida, diagrama, invariantes | `docs/specs/SPEC-NNN.md` |
| RFC (opções em aberto para uma decisão) | Modo RFC do `/especificar`, revisado por Rafael | `docs/rfcs/` |
| ADR (decisão tomada) | ADR | `docs/adr/` |
| Task / ticket (o quê, sem o porquê) | Plano de implementação da SPEC — tarefas de ≤ 1 dia, unidade de posse do quadro | mesma SPEC, seção Plano |
| Issue no board | Origem da SPEC; triada por `templates/ci/kairos-forge-triar.yml` | campo Origem |
| Design doc no Notion/Confluence | Link no campo Origem; o contrato fica no repo | campo Origem |
| Branch de POC | `/kairos-forge:rodar explorar <missão>` — notas em `docs/pocs/`, código nunca vira PR | `docs/pocs/` |
| Sistema de design / guia de estilo | `DESIGN.md` na raiz, formato getdesign.md, dono Pablo; `/kairos-forge:desenhar verificar` confere a implementação contra ele | `DESIGN.md` |

## Atalhos úteis

```bash
# Chamar Laura direto pra qualquer dúvida de coordenação
/kairos-forge:rodar laura

# Time de arquitetura inteiro pra brainstorm
/kairos-forge:rodar arquitetura

# Auditoria de segurança standalone (sem PR)
/kairos-forge:rodar helena

# QA review sem mexer em código
/kairos-forge:rodar patricia

# Pergunta multi-hop fundamentada no grafo de conhecimento
/kairos-forge:mapear-conhecimento consultar "o que depende do módulo de billing?"

# Eval de uma feature de IA antes de ela ir pra produção (Alice)
/kairos-forge:avaliar o resumo automatico de tickets
```

## Anti-padrões que matam o setup

### "Vou pular o /especificar, é simples"

Você vai pagar 3x mais tempo refazendo depois.

### "Vou usar só o codificador, os outros agentes são overhead"

Sem Helena, você não sabe que vulnerabilidade introduziu. Sem Patrícia, você não sabe se quebrou nada.

### "Vou rodar /auditar quando lembrar"

Se não for ritual fixo, não acontece. Coloque na agenda recorrente.

### "Vou usar `/mobilizar` pra tudo"

Mobilizar é caro em tokens e, no Claude Code, exige `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Pra tarefa pequena, invocação direta de 1-2 agentes é mais eficiente.

### "Vou ligar os gatilhos de CI logo de cara"

Gatilho por evento (`templates/ci/`) sem telemetria e sem guardrail não é autonomia — é pipeline sem supervisão. A ordem é: instrumentar (hooks de telemetria) → conter (guardrails) → disparar (CI). O `/auditar` recomenda as lacunas nessa ordem de propósito.

### "Vou misturar com o kairos-ai no mesmo projeto"

Não tem problema técnico, mas pense bem. Os dois sobrepõem o squad técnico. Se você tem requisito regulatório, use só o kairos-ai. Se não tem, só o forge. Misturar pode confundir os agentes.

## Próximos passos

- Leia [ADR-0001](adr/0001-plugin-em-vez-de-runtime.md) para entender por que isso é plugin
- Leia [ADR-0002](adr/0002-relacao-com-kairos-ai.md) para entender quando migrar pro kairos-ai
- Leia [ADR-0009](adr/0009-graph-engineering.md) e [memória persistente](memoria-persistente.md) para as camadas de memória da fábrica (grafo + ai-memory opcional)
- Veja `templates/squad-fabrica.yaml` para entender como os 40 agentes core são organizados
- Veja `templates/anti-drift.md` para o protocolo que mantém alinhados os teammates do `/mobilizar`, em qualquer CLI
- Leia [ADR-0021](adr/0021-observabilidade-do-harness.md), [ADR-0022](adr/0022-guardrails-deterministicos.md) e [ADR-0042](adr/0042-piso-e-gate-de-parada.md) para entender como a fábrica mede e contém a si mesma — o piso que não se configura e o gate de parada
- Leia [ADR-0023](adr/0023-skill-entregar-arco-fechado.md), [ADR-0029](adr/0029-maquina-de-estados-do-arco.md) e [ADR-0033](adr/0033-planejamento-em-fases-e-critica-adversarial.md) para o arco fechado do `/entregar`, a máquina de estados que decide a transição e o planejamento em fases com crítica adversarial
- Leia [ADR-0035](adr/0035-mobilizar-multi-cli.md) para o `/mobilizar` nos quatro CLIs e o quadro de tarefas em arquivo
- Leia [ADR-0039](adr/0039-verificacao-e-o-gargalo.md) para por que a verificação do agente sobre o próprio trabalho não vale como prova
- Leia [ADR-0043](adr/0043-juiz-cego-selado-e-veredicto.md) para o juiz cego do `/avaliar`, o conjunto selado que não vaza e o veredicto da evolução anterior
- Leia a [análise do whitepaper](revisoes/2026-08-01-analise-whitepaper-novo-sdlc-e-caminho-l4.md) se quiser o raciocínio completo por trás do caminho até L4
- Veja `templates/ci/` quando já tiver telemetria e guardrails rodando
- Quando tiver dor recorrente, rode `/kairos-forge:evoluir` pra virar capacidade nova
