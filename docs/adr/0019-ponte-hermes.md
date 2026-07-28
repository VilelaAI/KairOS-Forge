# ADR-0019 — Ponte Hermes: a fábrica como motor de engenharia do Hermes Agent

- **Status:** aceito
- **Data:** 2026-07-28
- **Versão:** v0.15.0

## Contexto

O [Hermes Agent](https://hermes-agent.nousresearch.com) (NousResearch) é um
agente 24/7 que roda num VPS e conversa por Telegram/Slack/Discord/WhatsApp,
com primitivas próprias: **profiles** (identidades), **skills** (`.md` em
`~/.hermes/skills/`), **workflows**, **kanban**, **cron**, memória e
aprovações. O [oh-my-hermes](https://github.com/Salomondiei08/oh-my-hermes)
(MIT) mostrou o padrão de extensão: uma camada curada de skills que compõe as
primitivas do Hermes num ciclo de produto — e que **roteia implementação
pesada para Claude Code e Codex como engines** (skill `choose-engine` →
`implement-with-claude-code`).

Isso fecha exatamente a lacuna mapeada na análise do produto (seção
KodeOrchestrator): o forge, por decisão (ADR-0001), não é runtime — não tem
24/7, cron, fila nem canal de chat. O Hermes tem tudo isso, é open-source, e
já espera receber um "engine" de engenharia. O encaixe natural: **Hermes
opera; a fábrica projeta e constrói.**

## Decisão

Criar a **ponte Hermes** em `hermes/` — no formato de skill do Hermes
(frontmatter `name/description/version/tags`, seções curtas), em PT-BR:

1. **`hermes/skills/kairos-forge-fabrica.md`** — skill de roteamento: ensina
   o Hermes a reconhecer trabalho de engenharia estruturada (feature
   multi-arquivo, SPEC, migração de legado, eval de IA, revisão pré-PR) e a
   rotear para o Claude Code **com o plugin kairos-forge**, compondo o
   handoff com contexto da memória do Hermes (o Claude Code não a enxerga).
2. **`hermes/skills/kairos-forge-ciclo.md`** — o ciclo completo headless:
   `claude -p "/kairos-forge:especificar …"` → gate do fundador (SPEC
   aprovada) → `rodar` → `validar` → `revisar` → PR, com evidência de volta
   pro kanban do Hermes a cada etapa.
3. **`hermes/workflows/entrega-com-kairos-forge.md`** — workflow no idioma do
   oh-my-hermes: de uma frase do fundador a um PR validado, com a fábrica
   como motor de engenharia.
4. **`hermes/install.sh`** — instala as skills/workflow em `~/.hermes/`,
   idempotente, e verifica dependências (Claude Code + plugin).
5. **`hermes/README.md`** — guia da integração: arquitetura, instalação, uso
   pelo Telegram, fronteira de aprovação.

**Inspiração absorvida no core:** o padrão "pergunta com default
recomendado" do oh-my-hermes entra no `/especificar` — escolha **reversível**
ganha default declarado e o fluxo segue; o Pare e Pergunte (ADR-0015)
continua mandando parar no que é **irreversível ou conteúdo inventável**. Os
dois compõem: default para o reversível, pergunta para o perigoso.

## O que fica de fora (e por quê)

- **Não criamos 71 profiles no Hermes.** O oh-my-hermes acerta: perfil demais
  vira ruído. A fábrica inteira vive **dentro do engine** — a Laura roteia os
  71 lá dentro; o Hermes conversa com 1 superfície.
- **O forge não vira runtime.** Cron, kanban, canal de chat e aprovação 24/7
  são do Hermes. A ponte compõe; não duplica (mesmo princípio do ai-memory,
  ADR-0010).
- **Sem paridade com oh-my-hermes.** Deploy, marketing, vídeo de lançamento,
  Buffer/Seedance são território deles — a ponte cobre só engenharia. Os dois
  convivem: oh-my-hermes para operar o produto, kairos-forge para construir
  com disciplina de SPEC.
- **`mobilizar` fica de fora do modo headless** (Agent Teams requer sessão
  interativa) — o ciclo usa `rodar`; quem quiser paralelo abre sessão
  interativa no projeto.

## Consequências

- O forge ganha a superfície **agente 24/7** sem trair o ADR-0001: você abre
  o Telegram, pede uma feature, e a SPEC/implementação/validação acontecem
  com a disciplina da fábrica — aprovação humana nos pontos irreversíveis.
- `hermes/` entra no espelhamento root → `plugin/` (release.py) e na
  varredura de consistência.
- Contagens de agentes/skills citadas em `hermes/README.md` entram nos
  padrões do `release.py` — não driftam.
- Registrado para o futuro: perfil dedicado "kairos" no Hermes (um profile
  que só roteia pra fábrica), e evidência de gate do `/validar` publicada
  como comentário estruturado no kanban.
