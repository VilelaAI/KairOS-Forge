# Início rápido — kairos-forge em 15 minutos

Este guia leva você de "acabei de ouvir falar de plugin" para "tenho a fábrica de 71 agentes rodando no meu projeto".

## Pré-requisitos

- Claude Code instalado (`npm install -g @anthropic-ai/claude-code`)
- Git
- Um projeto onde você queira aplicar a fábrica (qualquer linguagem, qualquer stack)
- **Opcional, para `/mobilizar`**: `export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

> Este guia segue o fluxo do **Claude Code**. Usa Codex CLI, OpenCode ou Cursor? A instalação por CLI está no [README do plugin](../README.md) — depois de instalado, as skills e o ciclo abaixo são os mesmos (exceto `/mobilizar`, exclusivo do Claude Code).

## Passo 1 — instalar o plugin

### Via marketplace

```
/plugin marketplace add VilelaAI/kairos-forge
/plugin install kairos-forge
/reload-plugins
```

### Local (desenvolvimento)

```bash
git clone https://github.com/VilelaAI/kairos-forge.git
cd seu-projeto
claude --plugin-dir ../kairos-forge
```

Após instalar, no início da sessão você deve ver:

```
🔥 kairos-forge v0.26 ativo — 71 agentes (40 core + 31 apoio em 10 squads) | skills: ...
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

A fábrica declara o orçamento, especifica, **para para você aprovar a SPEC**,
constrói, valida, corrige o que bloqueou, revisa, corrige o que era crítico e abre
o PR. Falha de validação ou revisão volta ao agente responsável — não a você.

O orçamento conta **rodadas sem progresso**, não rodadas (ADR-0032): se os achados
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

Eles interrogam, propõem 2-3 abordagens, recomendam uma, e produzem `docs/specs/SPEC-001-exportar-relatorio-csv.md` com requisitos rastreáveis, critérios de aceite, gates e plano de implementação **agente por agente**.

Antes de a SPEC chegar a você, **dois críticos que não a escreveram atacam o documento** (ADR-0033) — premissa, requisito, plano e testabilidade — e o relatório vai para `docs/specs/criticas/`. Era a única etapa do arco sem contraditório: a validação tem Ricardo e Patrícia, a revisão tem Helena e Patrícia, e a SPEC tinha só o autor. O parser cobra dois nomes distintos, porque um olhar só é revisão, não crítica.

### 3c. (Feature sensível) Modelar ameaças antes de implementar

Se a SPEC tocar auth, PII, billing, multi-tenant, upload, integração externa ou IA:

```
/kairos-forge:analisar-ameacas SPEC-001
```

Helena coordena (com Carlos/Marcos/Thiago/Gabriel/Renata conforme escopo). Saída: `docs/seguranca/AMEACAS-<slug>-YYYY-MM-DD.md` com ativos, trust boundaries, perfis realistas de atacante, abuse paths e mitigações priorizadas. Vira insumo direto para a SPEC e para o `/kairos-forge:revisar` depois.

### 3d. Implementar — escolha entre dois modos

#### Modo conversacional (sequencial)

```
/kairos-forge:rodar
```

Os agentes do plano da SPEC entram em sequência, cada um se apresentando, colaborando entre si por nome. Bom pra **entender** o que está acontecendo. Mais lento, mais tokens.

#### Modo paralelo (Agent Teams)

```
/kairos-forge:mobilizar SPEC-001
```

Laura cria um Agent Team (`TeamCreate`), distribui as tarefas (`TaskCreate`), e lança cada agente com file ownership próprio. Carlos faz a migration enquanto Lucas escreve o endpoint enquanto Marina cria o componente — tudo em paralelo.

O isolamento é proporcional à supervisão (ADR-0024): com humano revisando o PR, o ownership declarado no prompt basta. Em execução autônoma — ninguém lendo o diff — a Laura usa **worktree por teammate**, e aí o conflito deixa de ser questão de disciplina e vira impossibilidade física.

**Requer** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` na sessão.

### 3e. Validar contra a SPEC

```
/kairos-forge:validar SPEC-001
```

Ricardo e Patrícia validam se a implementação cumpre os requisitos P1, critérios de aceite e gates declarados na SPEC. Se tocar auth, PII, dados persistentes ou UI, Helena, Carlos e Ada entram conceitualmente no parecer.

A validação também **confere a evidência contra o que realmente rodou** (ADR-0021): a célula `verificado:` da SPEC é escrita pelo agente que fez o trabalho, então ela é conferida contra a trajetória gravada pelos hooks. Alegação sem lastro vira "não corroborada" e bloqueia P1 igual a "sem evidência".

### 3f. Revisar antes do PR

```
/kairos-forge:revisar
```

Helena (segurança) + Patrícia (QA) sempre rodam. Vinícius (performance), Marcos (DevOps), Carlos (DBA), Ada (acessibilidade) entram automaticamente conforme os arquivos modificados no diff. Cada um produz parecer em primeira pessoa, com severidade.

Veredicto agregado: ✅ aprovado / ⚠️ ressalvas / ❌ bloqueado.

O relatório abre com a **faixa de raio de explosão** (ADR-0031), porque ela é que decide o rigor — e a pergunta não é "quão confiante estou?", é **"quanto custa desfazer se estiver errado?"**:

| Faixa | Exemplo | O que fecha |
|---|---|---|
| 1 — reversível e contido | Texto de UI, teste, função isolada coberta | Gates verdes |
| 2 — reversível mas amplo | Utilitário compartilhado, schema, contrato interno | Gates verdes **e** trajetória limpa |
| 3 — difícil de reverter | Migration destrutiva, deleção, produção, dinheiro | **Humano decide, sempre** |

Um diff de 20 linhas na faixa 3 recebe mais escrutínio que um de 400 na faixa 1. Se o projeto tem histórico git, a taxa de reversão da área tocada (`diagnostico.py`) é evidência para subir de faixa — é o sinal que o modelo não consegue influenciar.

O relatório é salvo em `docs/specs/revisoes/` com um bloco de contrato (ADR-0032) que o `/kairos-forge:entregar` lê do disco. Duas regras nele valem saber: **zero 🔴 exige a lista do que foi lido** — "não achei nada" sem dizer onde procurou é ausência de busca, não ausência de defeito; e a fence é própria da revisão, nunca a mesma da validação.

### 3f-bis. Ver onde tudo está, numa tela

A qualquer momento, do diretório do projeto:

```bash
python3 <plugin>/scripts/painel.py              # tudo
python3 <plugin>/scripts/painel.py SPEC-001     # uma SPEC
python3 <plugin>/scripts/painel.py --html quadro.html   # página pra mandar pra alguém
```

Sai o quadro vivo: requisitos por coluna (A fazer / Em progresso / Pronto), progresso da SPEC, estado do arco com as fichas de orçamento, veredicto dos dois gates com a cobertura declarada, e a trajetória dos últimos 14 dias. O HTML é autocontido — abre sem rede.

Duas coisas que ele **não** faz, de propósito: não escreve nada (é renderização do estado canônico, nunca planilha paralela — ADR-0013), e não conta como "Pronto" requisito marcado `Concluído` sem `verificado:` — esse cai para "Em progresso" e aparece no aviso. Um quadro que somasse a palavra mostraria progresso que a própria `/validar` recusaria.

### 3g. Alimentar a memória da fábrica

Quando SPECs, ADRs e decisões acumularem (tipicamente depois das primeiras 2-3 features):

```
/kairos-forge:mapear-conhecimento construir
```

Olívia extrai entidades e relações com proveniência para `.agents/grafo/`. Nas rodadas seguintes, `/mobilizar` semeia os teammates com subgrafos em vez de contexto inteiro, `/validar` checa afirmações contra arestas ("a tripla X não existe; o que existe é Y, da fonte Z"), e perguntas multi-hop ("o que depende do componente que essa SPEC muda?") ganham resposta fundamentada.

## Passo 4 — ritmo semanal

**Sextas-feiras** (ou quando lembrar):

```
/kairos-forge:auditar
```

Pontuação 0–120 nas 6 dimensões da fábrica (Fundação, Pipeline, Guardrails, Conhecimento, Estrutura e **Autonomia**). Vai vir baixa nas primeiras semanas — isso é normal, e a dimensão Autonomia vem zerada até você ter algumas semanas de ciclos registrados.

O relatório também estima o **nível da fábrica** (L2 Babá / L3 Gerente / L4 Fábrica) a partir da telemetria — não da impressão. L4 exige *todos* os critérios da linha, não a média: 90% de autonomia sem guardrail determinístico é classificado como pipeline sem supervisão, com essas palavras.

Em seguida:

```
/kairos-forge:evoluir
```

5 perguntas → identifica UMA capacidade pra construir na próxima semana.

Loop semanal é o que faz a fábrica ficar mais inteligente com o tempo.

## Passo 5 — o que o harness faz sozinho

Três coisas passam a acontecer sem você pedir. Vale saber o que são para não
estranhar.

**Os hooks gravam a trajetória.** Cada sessão anexa eventos a
`.agents/execucoes/*.jsonl` — quais gates rodaram, o que passou, quantas vezes
você precisou intervir. Nunca registra o texto dos seus prompts nem segredos
(comandos passam por redação). Está no `.gitignore` por padrão: é matéria-prima
local, e o que sobe de camada é o número agregado na auditoria.

Para ver onde você está:

```bash
python3 <plugin>/scripts/telemetria.py resumo --dias 30
```

**Os guardrails podem bloquear.** Se um agente tentar `rm -rf /`, force-push em
`main`, escrever em `.env` ou marcar um requisito como "Concluído" sem a célula
`verificado:`, a ação é recusada e o motivo vai para o agente, que corrige. Se o
bloqueio atrapalhar algo legítimo no seu projeto, ajuste
`.agents/guardrails.json` (campo `liberados`) — **você**, não o agente: ele não
escreve a própria regra.

**A evidência passa a ser conferida.** O `/validar` cruza cada `verificado:` com
o que realmente rodou. Isso significa que uma SPEC otimista não passa mais só
porque o texto está bem escrito.

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

Mobilizar é caro em tokens e exige `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Pra tarefa pequena, invocação direta de 1-2 agentes é mais eficiente.

### "Vou ligar os gatilhos de CI logo de cara"

Gatilho por evento (`templates/ci/`) sem telemetria e sem guardrail não é autonomia — é pipeline sem supervisão. A ordem é: instrumentar (hooks de telemetria) → conter (guardrails) → disparar (CI). O `/auditar` recomenda as lacunas nessa ordem de propósito.

### "Vou misturar com o kairos-ai no mesmo projeto"

Não tem problema técnico, mas pense bem. Os dois sobrepõem o squad técnico. Se você tem requisito regulatório, use só o kairos-ai. Se não tem, só o forge. Misturar pode confundir os agentes.

## Próximos passos

- Leia [ADR-0001](adr/0001-plugin-em-vez-de-runtime.md) para entender por que isso é plugin
- Leia [ADR-0002](adr/0002-relacao-com-kairos-ai.md) para entender quando migrar pro kairos-ai
- Leia [ADR-0009](adr/0009-graph-engineering.md) e [memória persistente](memoria-persistente.md) para as camadas de memória da fábrica (grafo + ai-memory opcional)
- Veja `templates/squad-fabrica.yaml` para entender como os 40 agentes core são organizados
- Veja `templates/anti-drift.md` para o protocolo que mantém Agent Teams alinhados
- Leia [ADR-0021](adr/0021-observabilidade-do-harness.md) e [ADR-0022](adr/0022-guardrails-deterministicos.md) para entender como a fábrica mede e contém a si mesma
- Leia [ADR-0023](adr/0023-skill-entregar-arco-fechado.md) para o arco fechado do `/entregar`
- Leia a [análise do whitepaper](revisoes/2026-08-01-analise-whitepaper-novo-sdlc-e-caminho-l4.md) se quiser o raciocínio completo por trás do caminho até L4
- Veja `templates/ci/` quando já tiver telemetria e guardrails rodando
- Quando tiver dor recorrente, rode `/kairos-forge:evoluir` pra virar capacidade nova
