# ADR-0020 — Skills `desenhar` e `lancar`: o ciclo de produto do oh-my-hermes no plugin

- **Status:** aceito
- **Data:** 2026-07-28
- **Versão:** v0.16.0

## Contexto

O oh-my-hermes (analisado no ADR-0019) organiza o ciclo de produto em
Understand → Design → Build → Check → **Ship** → Learn. Ao mapear as 36
skills dele contra a fábrica, três grupos apareceram:

1. **Já cobertos — e mais fundo — pela fábrica:** clarify-requirements
   (`especificar` + Joana + Pare e Pergunte), product-brief (SPEC rastreável),
   security-review (`revisar` + `analisar-ameacas`), review-github-pr
   (`revisar`), kanban-task (quadro vivo), choose-engine (roteamento da
   Laura), onboarding (`onboardar`), cto-status-report (Talita).
2. **Território do host 24/7 — não duplicar:** cron, monitoramento contínuo,
   observe-logs horário, auto-issue-triage, failure-recovery/dead-letter,
   computer-use, integrações de fornecedor (Buffer, Seedance). É exatamente o
   que a ponte Hermes (ADR-0019) delega ao Hermes.
3. **Lacunas reais do nosso fluxo:** (a) não existe artefato de **design**
   entre a SPEC e a implementação — Isabela e Pablo opinam, mas nada obriga
   fluxos, estados e critérios visuais a existirem antes do código, nem
   verificação visual depois; (b) o fluxo termina no `/revisar` — **o deploy
   não tem skill**: sem checklist pré-deploy, sem health check em camadas,
   sem plano de rollback ensaiado, sem follow-up.

## Decisão

Duas skills novas (13 → 15), preenchendo o grupo 3 com disciplina de sessão
— nada de runtime:

### `desenhar` (dona: Isabela, com Pablo e Ada)

Entre `especificar` e a implementação, para features com UI: produz
`docs/design/DESIGN-NNN.md` a partir da SPEC — fluxos de tela, os **cinco
estados** de cada view (carregando, vazio, erro, sucesso, parcial),
comportamento responsivo, critérios de acessibilidade (Ada) e critérios de
aceite visuais que o `/validar` consegue cobrar. Depois de implementado, o
modo `verificar` inspeciona o resultado real contra o DESIGN (a "visual
verification" do Designer do oh-my-hermes). Design é rascunho dirigido:
direção recomendada e reversível em vez de bloqueio por preferência.

### `lancar` (dono: Marcos, com Sérgio e Renata)

Do merge ao mundo, com gates: checklist pré-deploy (validar sem bloqueio,
revisar sem críticos, migration com rollback testado, variáveis de ambiente
conferidas), **aprovação explícita do usuário** (deploy de produção é
irreversível — Pare e Pergunte), deploy pelo Marcos (stack-agnóstico; a
skill documenta o caminho Vercel como default e como substituir), health
check em três camadas do Sérgio (endpoint, banco, logs), plano de rollback
com gatilho objetivo, e follow-up: resumo do que mudou + handoff de
observação pra Renata (o que monitorar). O monitoramento **contínuo** fica
com o host 24/7 (Hermes) — a skill entrega o lançamento, não o plantão.

**Absorvido de leve, sem skill nova:** a disciplina de product-marketing
(posicionamento, plano de conteúdo) já tem dona — Sofia (apoio-valor) ganha
o plano de comunicação de lançamento como artefato citado no `lancar`.

## Consequências

- Fluxo natural passa a ser: `especificar` → `desenhar` (UI) → `mobilizar`/
  `rodar` → `validar` → `revisar` → `lancar`, com `desenhar verificar` após
  a implementação.
- O ciclo headless da ponte Hermes ganha o `lancar` como etapa opcional
  pós-merge (com o gate do fundador pelo chat).
- Nenhum agente novo: Isabela, Pablo, Ada, Marcos, Sérgio, Renata e Sofia
  já existem — as skills dão processo ao que era conselho.
- Fica de fora, registrado: promoção staging→produção multi-ambiente e
  testes de jornada pós-deploy completos (V2 do próprio oh-my-hermes;
  reavaliar quando houver demanda).
