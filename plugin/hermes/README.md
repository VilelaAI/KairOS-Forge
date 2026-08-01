# Ponte Hermes — a fábrica como motor de engenharia do Hermes Agent

Integra o kairos-forge ao [Hermes Agent](https://hermes-agent.nousresearch.com)
(NousResearch): você conversa com um bot no Telegram/Slack, e por trás dele a
fábrica — 71 agentes (40 core + 31 apoio em 10 squads) coordenados por Laura —
especifica, constrói, valida e revisa com disciplina de SPEC. Padrão de
integração inspirado no [oh-my-hermes](https://github.com/Salomondiei08/oh-my-hermes)
(ADR-0019).

## Arquitetura

```text
Fundador (Telegram/Slack)
  │
  ▼
Hermes Agent (24/7 no VPS) ──── opera: kanban, cron, memória, aprovações
  │
  │  skills da ponte: kairos-forge-fabrica (roteia) + kairos-forge-ciclo (conduz)
  ▼
Claude Code + plugin kairos-forge ──── constrói: a fábrica inteira vive aqui
  │        (Laura roteia os 71 agentes dentro do engine)
  ▼
especificar → aprovação do fundador → entregar
                                        └─ construir → validar ⇄ corrigir
                                           → revisar ⇄ corrigir → PR
```

Divisão de papéis — cada camada faz o que só ela faz bem:

| Camada | Responsabilidade |
|---|---|
| **Hermes** | Operação 24/7: canal de chat, kanban, cron, memória entre sessões, gates de aprovação |
| **kairos-forge** | Engenharia: SPEC rastreável, implementação por especialistas, validação contra contrato, revisão multi-agente, migração por estrangulamento, evals de IA |
| **oh-my-hermes** (opcional) | Ciclo de produto: deploy, monitoramento, marketing, criação — convive com a ponte; a fábrica assume a engenharia estruturada |

A fábrica **não** vira 71 profiles no Hermes — perfil demais é ruído. O Hermes
enxerga uma superfície (as skills da ponte); a Laura roteia os especialistas
dentro do engine.

## Instalação

```bash
# 1. Hermes Agent instalado e conectado ao Telegram (quickstart oficial)
# 2. Claude Code + plugin kairos-forge na mesma máquina:
npm install -g @anthropic-ai/claude-code
#    dentro do Claude Code:  /plugin marketplace add VilelaAI/kairos-forge
#                            /plugin install kairos-forge@kairos-forge

# 3. A ponte:
git clone https://github.com/VilelaAI/kairos-forge /tmp/kairos-forge
bash /tmp/kairos-forge/hermes/install.sh
```

## Uso

Mande pro bot:

```text
construir com a fábrica: exportação de relatórios em PDF com agendamento
```

O que acontece:

1. O Hermes cria o card no kanban e roteia pela skill `kairos-forge-fabrica`.
2. `kairos-forge-ciclo` roda `claude -p "/kairos-forge:especificar …"` — a
   SPEC rastreável chega pra você no chat com requisitos P1 e perguntas
   abertas.
3. Você responde **SIM / NÃO / AJUSTAR** (e as perguntas do Pare e Pergunte,
   se houver — a fábrica não inventa conteúdo).
4. A fábrica roda o **arco fechado** (`/kairos-forge:entregar`, ADR-0023):
   constrói, valida, corrige o que bloqueou, revisa, corrige o que era crítico —
   dentro de um orçamento de rodadas declarado. Falha volta ao agente
   responsável, não a você.
5. Chega o PR com validação sem bloqueio e revisão sem achados críticos.
   O merge é seu.

Se o orçamento esgotar ou a fábrica precisar de decisão fora da SPEC, ela **para
e pergunta** em vez de insistir — a pergunta chega ao chat com o que já foi
tentado.

Também funciona sob demanda: "migra esse monólito com a fábrica" (Ivan,
`/migrar`), "roda a revisão de segurança da fábrica nesse diff" (`/revisar`).

## Fronteira de aprovação

Aprovação humana somente no irreversível — SPEC antes de implementar, release
de produção, rollback, janela de corte de migração, mudança destrutiva de
dados. O resto segue com defaults declarados. As perguntas chegam pelo chat;
ninguém aprova em seu nome.

## Limitações

- `mobilizar` (paralelo via Agent Teams) requer sessão interativa — o ciclo
  headless usa `rodar` (sequencial). Para paralelo, abra `claude` no projeto.
- A ponte requer o plugin **v0.18.0+** para o arco fechado; em versão anterior a
  skill `kairos-forge-ciclo` cai no procedimento legado (loop conduzido pelo
  Hermes, documentado no rodapé dela).
- A telemetria de execução (ADR-0021) enxerga cada `claude -p` como um ciclo
  próprio — a dimensão Autonomia do `/auditar` lida com o fluxo headless de
  forma diferente da sessão interativa. Não é erro; é o desenho.
- O Claude Code não enxerga a memória do Hermes: as skills da ponte colam o
  contexto relevante no handoff — contexto que não foi colado não existe.
- As 17 skills do ciclo continuam sendo do plugin (Claude Code/Codex/
  OpenCode/Cursor); a ponte adiciona a superfície de operação 24/7, não uma
  quinta distribuição do plugin.
