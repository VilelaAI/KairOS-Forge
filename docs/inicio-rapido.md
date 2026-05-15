# Início rápido — kairos-forge em 15 minutos

Este guia leva você de "acabei de ouvir falar de plugin" para "tenho a fábrica de 45 agentes rodando no meu projeto".

## Pré-requisitos

- Claude Code instalado (`npm install -g @anthropic-ai/claude-code`)
- Git
- Um projeto onde você queira aplicar a fábrica (qualquer linguagem, qualquer stack)
- **Opcional, para `/mobilizar`**: `export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

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
🔥 kairos-forge v0.5 ativo — 45 agentes (24 core + 21 apoio em 7 squads) | skills: ...
```

## Passo 2 — onboarding do projeto

```
/kairos-forge:onboardar
```

Entrevista de 7 perguntas. Reserve 15 minutos. Use ditado por voz se ajudar — quanto mais contexto, melhor.

Ao final você terá:

- `CLAUDE.md` preenchido na raiz do projeto
- `contextos/` com contexto de projeto, stack, convenções, restrições e testes
- `decisoes/log.md`
- `decisoes/estado-operacional.md`
- `docs/specs/`, `docs/specs/validacoes/` e `docs/adr/` prontos pros arquitetos popularem

## Passo 3 — primeira feature pelo fluxo correto

### 3a. (Brownfield) Mapear arquitetura antes de mexer

Se o projeto já existe e tem dívida estrutural, comece por um mapa honesto:

```
/kairos-forge:mapear-arquitetura
```

Diego coordena (com Fernanda/Thiago/Rafael conforme dimensões). Saída: `docs/arquitetura/MAPA-YYYY-MM-DD.md` com inventário, acoplamento, duplicação, bounded contexts e plano incremental de decomposição. Pule este passo se for greenfield ou se você já conhece bem a estrutura.

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

Laura cria um Agent Team (`TeamCreate`), distribui as tarefas (`TaskCreate`), e lança cada agente com file ownership isolado. Carlos faz a migration enquanto Lucas escreve o endpoint enquanto Marina cria o componente — tudo em paralelo, em worktrees separados.

**Requer** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` na sessão.

### 3e. Validar contra a SPEC

```
/kairos-forge:validar SPEC-001
```

Ricardo e Patrícia validam se a implementação cumpre os requisitos P1, critérios de aceite e gates declarados na SPEC. Se tocar auth, PII, dados persistentes ou UI, Helena, Carlos e Ada entram conceitualmente no parecer.

### 3f. Revisar antes do PR

```
/kairos-forge:revisar
```

Helena (segurança) + Patrícia (QA) sempre rodam. Vinícius (performance), Marcos (DevOps), Carlos (DBA), Ada (acessibilidade) entram automaticamente conforme os arquivos modificados no diff. Cada um produz parecer em primeira pessoa, com severidade.

Veredicto agregado: ✅ aprovado / ⚠️ ressalvas / ❌ bloqueado.

## Passo 4 — ritmo semanal

**Sextas-feiras** (ou quando lembrar):

```
/kairos-forge:auditar
```

Pontuação 0–100 nas 4 dimensões da fábrica. Vai vir baixa nas primeiras semanas — isso é normal.

Em seguida:

```
/kairos-forge:evoluir
```

5 perguntas → identifica UMA capacidade pra construir na próxima semana.

Loop semanal é o que faz a fábrica ficar mais inteligente com o tempo.

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

### "Vou misturar com o kairos-ai no mesmo projeto"

Não tem problema técnico, mas pense bem. Os dois sobrepõem o squad técnico. Se você tem requisito regulatório, use só o kairos-ai. Se não tem, só o forge. Misturar pode confundir os agentes.

## Próximos passos

- Leia [ADR-0001](adr/0001-plugin-em-vez-de-runtime.md) para entender por que isso é plugin
- Leia [ADR-0002](adr/0002-relacao-com-kairos-ai.md) para entender quando migrar pro kairos-ai
- Veja `templates/squad-fabrica.yaml` para entender como os 24 agentes são organizados
- Veja `templates/anti-drift.md` para o protocolo que mantém Agent Teams alinhados
- Quando tiver dor recorrente, rode `/kairos-forge:evoluir` pra virar capacidade nova
