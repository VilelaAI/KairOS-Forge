# ADR-0013 — Ledger de consumo, quadro vivo e trilhas por tema (inspirações KodeOne)

**Status:** Aceito
**Data:** 2026-07-25

## Contexto

Análise do produto [KodeOne](https://kodeone.ai) (estúdio brasileiro de vibe coding, concorrente de Lovable/Replit) a pedido do usuário. Do que o produto entrega, boa parte a fábrica já cobre ou está deliberadamente fora do escopo de plugin:

- **Já coberto:** "Ultracode" (fan-out paralelo + verificação adversarial) é o `/mobilizar` + `/revisar` + autocrítica do anti-drift; "contexto que não se perde" é o grafo (ADR-0009) + memória em camadas (ADR-0010).
- **Runtime/SaaS, não portável (ADR-0001):** preview ao vivo, deploy 1-clique, produção 24/7, billing real de créditos, editor/hub.

Sobram **três ideias de produto genuinamente boas e portáveis para prompts**:

1. **"Créditos à vista" / "o orquestrador que se paga".** O KodeOne mostra, por execução e por agente, quanto foi consumido — e quanto o *roteamento inteligente* economizou rodando o modelo certo em cada etapa em vez de jogar o mais caro em tudo. A fábrica tinha orçamento declarado (ADR-0012), mas nenhuma **transparência de consumo** no encerramento e nenhuma disciplina explícita de **tier de modelo por teammate**.
2. **"Quadro que a IA move" (KodeOne Boards).** Cards andam porque os agentes estão construindo — e "Pronto" só quando a revisão passa: *"progresso de verdade, não chute"*. A fábrica já tem exatamente essa semântica no ritual `verificado:` da SPEC, mas não tinha **visualização de progresso** — e usuários de Codex/OpenCode/Cursor nem veem o TaskList nativo do Claude Code.
3. **"Squads por tema" (modo guiado).** No plano iniciante, o usuário não monta skills — escolhe um tema (`auth-completo`, `checkout-stripe`, `painel-admin`…) que já vem com o caminho embalado. A fábrica era toda "modo dev": quem chega sem saber o que pedir não tinha porta de entrada guiada.

## Decisão

A partir da **v0.10.2**, três adições — todas como prompts/templates, sem runtime:

### 1. Ledger de consumo e roteamento de modelo no `/mobilizar`

- **Na largada**, Laura define e anuncia o **tier de modelo por teammate**: `rápido` (trabalho mecânico — seeds, fixtures, docs de rotina, extração), `padrão` (implementação) e `preciso` (arquitetura, segurança, revisão final). Rodar o modelo certo em cada etapa é o que faz o orquestrador se pagar — o mesmo princípio do modelo-por-etapa do grafo (ADR-0009).
- **No encerramento**, o relatório ganha o **Ledger da mobilização**: tabela por teammate com tasks entregues, rodadas de correção e tier usado. Honestidade sobre o limite: o plugin não enxerga tokens de dentro da sessão — o ledger registra o que dá pra medir (tasks, rodadas, tier) e aponta o comando de custo do CLI (`/cost` no Claude Code) para o número real.
- **Avisa-e-pausa** no orçamento de complexidade (ADR-0012): ao cruzar ~80% de qualquer limite, avisar no próximo checkpoint; ao atingir 100%, **pausar** (não lançar novas tasks) e perguntar — encerrar com lacunas declaradas ou ampliar o orçamento. Sem susto, como no KodeOne.

### 2. Quadro vivo nos checkpoints (`/mobilizar` e `/rodar`)

Sem planilha paralela e sem arquivo novo: o estado canônico continua sendo a SPEC (coluna Status/Verificação) e as tasks. O que muda é a **renderização**: a cada checkpoint (e no encerramento), Laura mostra o quadro em uma linha por coluna — `A fazer / Em progresso (quem) / Pronto (✓gate)` — com percentual de progresso. Regra herdada do ritual `verificado:`: **card só entra em "Pronto" com gate rodado**. No `/rodar`, o mesmo quadro leve aparece ao fim de cada entrega — é o que dá visibilidade em Codex/OpenCode/Cursor, onde não há TaskList nativo.

### 3. Trilhas por tema (`templates/trilhas/`) — modo guiado

Blueprints de SPEC para os temas que todo produto web repete, inspirados nos squads do KodeOne mas stack-agnósticos:

| Trilha | Tema |
|---|---|
| `trilha-auth.md` | Login social + e-mail/senha, sessão, RLS |
| `trilha-pagamentos.md` | Checkout, webhooks, recibos, reconciliação |
| `trilha-painel-admin.md` | CRUD, filtros, permissões, auditoria |
| `trilha-api.md` | Endpoints tipados, validação, versionamento, docs |
| `trilha-seed-dados.md` | Seeds, fixtures e dados de teste |

Cada trilha traz: requisitos típicos com IDs prontos (ponto de partida da tabela da SPEC), tarefas com agentes e gates sugeridos, riscos/ameaças típicas (insumo direto pro `/analisar-ameacas`) e as perguntas que o arquiteto **deve** fazer antes de fechar a SPEC. O `/especificar` detecta quando a feature casa com uma trilha e parte dela em vez de começar do zero; o iniciante pode pedir só "quero login" que Laura reconhece a trilha. A trilha é ponto de partida, não fôrma: o arquiteto adapta ao projeto real.

## O que deliberadamente NÃO foi portado

- **Créditos/billing reais, medição de tokens em runtime.** Plugin não mede consumo de API; fingir precisão seria mentira. O ledger é operacional (tasks/rodadas/tier) e aponta para a medição real do CLI.
- **Kanban interativo/arquivo de quadro.** Duplicaria o estado da SPEC (anti-padrão "planilha paralela" que o próprio KodeOne critica). O quadro é renderização do estado canônico, não estado novo.
- **Preview, deploy, produção 24/7, DevOps gerenciado.** Runtime (ADR-0001). As personas de plataforma (Marcos, Igor, Gael, Kaique…) seguem cobrindo o desenho.
- **Trilha `deploy-edge` do KodeOne.** Deploy é do runtime do usuário; a fábrica desenha pipeline via personas, não empacota deploy.

## Versão

Sem skill nem agente novos — templates + mudanças de prompt: bump **patch** 0.10.1 → **0.10.2** (mesmo precedente dos ADRs 0007-segurança e 0010).

## Consequências

Boas:

- Custo de orquestração deixa de ser caixa-preta: tier declarado na largada, ledger no encerramento, pausa antes do estouro.
- Progresso visível em qualquer CLI, com a semântica forte que já existia ("Pronto" = gate rodado).
- Porta de entrada guiada para quem não sabe por onde começar — sem criar um "modo iniciante" separado que bifurcaria o produto.

Custos:

- Ledger sem tokens reais pode frustrar quem espera número exato. Mitigado: o relatório diz explicitamente o que mede e aponta o `/cost`.
- Trilhas podem envelhecer em relação a stacks. Mitigado: são stack-agnósticas por construção e curtas; `/evoluir` é o ritual natural para revisá-las.

## Alternativas consideradas

1. **Medir tokens de verdade por agente.** Rejeitado: exigiria runtime/hook de plataforma que o plugin não tem; melhor um ledger honesto do que um número inventado.
2. **Arquivo de quadro por SPEC (`QUADRO-*.md`).** Rejeitado: estado duplicado dessincroniza — a SPEC já é o quadro; só faltava renderizar.
3. **Skill nova `guiar` para o modo iniciante.** Rejeitado: trilha é conteúdo, não fluxo novo — o `/especificar` já é o fluxo certo; uma 13ª skill duplicaria a entrada.
4. **Portar squads por tema como agentes novos.** Rejeitado: os 52 agentes cobrem os papéis; trilha organiza o *caminho*, não cria persona.
