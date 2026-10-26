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
  │        (Laura roteia os 71 agentes; o ciclo.py decide cada transição)
  ▼
/kairos-forge:entregar
  planejamento  entendimento ⏸ → abordagem ⏸ → SPEC → crítica ⇄ corrigir SPEC
                → aprovação da SPEC ⏸
  construção    construir → validar ⇄ corrigir → revisar → PR
                            ▲                    │ crítico
                            └──── corrigir ◀─────┘

  ⏸ gate do fundador: o arco para, o Hermes pergunta no chat e retoma
```

Correção de achado crítico da revisão volta à **validação**, não direto à
revisão — é aresta da máquina de estados (`ciclo.py`, ADR-0029), não lembrete.

Divisão de papéis — cada camada faz o que só ela faz bem:

| Camada | Responsabilidade |
|---|---|
| **Hermes** | Operação 24/7: canal de chat, kanban, cron, memória entre sessões, gates de aprovação, monitoramento contínuo depois do lançamento |
| **kairos-forge** | Engenharia: SPEC rastreável com crítica adversarial, design de UI (`desenhar`), implementação por especialistas, validação contra contrato, revisão multi-agente, deploy com gates (`lancar`), migração por estrangulamento, evals de IA |
| **oh-my-hermes** (opcional) | Ciclo de produto além da engenharia: monitoramento, marketing, criação — convive com a ponte. Deploy não é dele aqui: é do `/kairos-forge:lancar` (ADR-0020) |

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
2. `kairos-forge-ciclo` roda `claude -p "/kairos-forge:entregar …"` no projeto
   (git limpo, branch própria). A fábrica abre o ciclo, a Laura dimensiona e os
   arquitetos interrogam.
3. **Gate 1/3 — entendimento.** Chega o entendimento espelhado e as perguntas do
   Pare e Pergunte, se houver — a fábrica não inventa conteúdo. Você confirma ou
   corrige.
4. **Gate 2/3 — abordagem.** Chegam 2-3 abordagens com trade-offs e a
   recomendada. Você escolhe.
5. A fábrica escreve a SPEC e, **antes de você ver**, ao menos dois críticos que
   não a escreveram atacam premissa, requisito, plano e testabilidade; achado volta
   para a SPEC e a crítica reabre.
6. **Gate 3/3 — aprovação da SPEC.** Objetivo, requisitos P1, não-objetivos,
   plano e o que a crítica encontrou. Você responde **SIM / NÃO / AJUSTAR**.
7. A fábrica roda o resto do **arco fechado** (`/kairos-forge:entregar`,
   ADR-0023): constrói, valida, corrige o que bloqueou, revisa, corrige o que era
   crítico e valida de novo. O orçamento é contado por código: por padrão 2
   rodadas sem progresso por gate, teto de 6 — rodada que reduz os achados
   devolve a ficha. Falha volta ao agente responsável, não a você.
8. Chega o PR com validação sem bloqueio e revisão sem achados críticos.
   O merge é seu.

Feature sensível passa antes por `/kairos-forge:analisar-ameacas`, para as
mitigações nascerem na SPEC. Feature com UI passa pelo `/kairos-forge:desenhar`
entre a aprovação e a construção: os critérios visuais entram na SPEC já aprovada,
e você aceita a versão nova.

Em headless cada gate espera de verdade: o `claude -p` termina no gate, o Hermes
leva a pergunta ao chat, registra a sua resposta no `ciclo.py` e retoma — ao menos
quatro invocações por entrega. O atalho de feature Pequena (gates 1 e 2 numa
mensagem só) é de sessão interativa (ADR-0038).

Se o orçamento esgotar ou a fábrica precisar de decisão fora da SPEC, ela **para
e pergunta** em vez de insistir — a pergunta chega ao chat com o que já foi
tentado.

Também funciona sob demanda: "migra esse monólito com a fábrica" (Ivan,
`/migrar`), "roda a revisão de segurança da fábrica nesse diff" (`/revisar`),
"põe em produção" (`/lancar`, com o seu SIM explícito).

## Em que pé está o ciclo

O bot não deduz do log: lê o contrato público do arco (ADR-0034,
`docs/contrato-de-integracao.md`), no diretório do projeto e sempre com a SPEC:

```bash
python3 <plugin>/scripts/ciclo.py estado SPEC-NNN --json
```

| Campo | O que diz ao bot |
|---|---|
| `terminal` | Nada mais a registrar: PR aberto, SPEC recusada, encerrado à mão ou escalado — este último vai para você |
| `aguardando_humano` | Está num dos três gates — levar ao chat |
| `gate` | Qual loop está em jogo: `criticar`, `validar` ou `revisar` |
| `resultados_validos` | O que o `registrar` aceita agora — a resposta do fundador vira um destes |
| `spec_alterada` | A SPEC mudou depois da aprovação; resultado verde fica recusado até você aceitar a versão nova |
| `motivo_escalacao` | Por que escalou: orçamento, teto ou a decisão que falta |

O bot decide por esses campos, não comparando nome de estado — só para dizer como
um ciclo terminal acabou ele lê o `estado`. `<plugin>` é o diretório do plugin
instalado. O estado vive em `.agents/ciclo/<spec>.json` e sobrevive a reset de
contexto, troca de sessão e restart do Hermes.

## Fronteira de aprovação

Aprovação humana no que só gente decide — e ninguém aprova em seu nome:

- **Os três gates do planejamento** — entendimento, abordagem e aprovação da
  SPEC. Em headless cada um espera de verdade; sem SIM, não constrói.
- **Pare e Pergunte** — conteúdo que apareceria ao usuário final como verdade sem
  fonte.
- **SPEC alterada depois da aprovação** (`spec_alterada`) — só você aceita a
  versão nova (`ciclo.py reaprovar`); senão, a SPEC volta.
- **Faixa 3 do raio de explosão** (ADR-0031) — migration destrutiva, deleção,
  produção, dinheiro, credencial: não fecha por evidência, o arco escala.
- **Escalação** (`escalado`) — orçamento sem progresso esgotado, teto atingido ou
  decisão fora da SPEC: só você destrava.
- **Irreversível** — release de produção (SIM explícito no `/lancar`, sem default,
  com plano de rollback e gatilho), janela de corte de migração, mudança destrutiva
  de dados.
- **Merge do PR.**

Escolha reversível no meio do arco não trava: a fábrica declara o default
recomendado, registra a premissa e segue (ADR-0019). As perguntas chegam pelo
chat.

## Limitações

- Em headless o `entregar` escolhe o modo pela forma do plano, como em sessão:
  `mobilizar` quando há tarefas independentes, `rodar` no resto. O `mobilizar`
  isola cada teammate em worktree, porque ninguém olha em voo (ADR-0024). Para o
  paralelo de verdade no Claude Code, exporte `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
  no ambiente do Hermes; sem ela, o Passo 0 do `mobilizar` roda o mesmo quadro em
  série, com as mesmas dependências e a mesma contagem final. Agent Teams sob
  `claude -p` não foi testado; se não lançar, o resultado é o quadro em série.
- A ponte requer o plugin **v0.34.1+**: arco no `ciclo.py` (v0.21), planejamento
  em fases com crítica (v0.26), `estado --json` como contrato (v0.27) e
  `reaprovar` com `spec_alterada` (contrato 1.1). Confira com
  `python3 <plugin>/scripts/ciclo.py contrato` — `versao` 1.1 ou maior. Em versão
  anterior, atualize; sem como, a skill `kairos-forge-ciclo` tem no rodapé o
  procedimento legado (loop conduzido pelo Hermes, sem orçamento imposto por
  código).
- A telemetria de execução (ADR-0021) enxerga cada `claude -p` como um ciclo
  próprio — a dimensão Autonomia do `/auditar` lida com o fluxo headless de
  forma diferente da sessão interativa. Não é erro; é o desenho.
- O Claude Code não enxerga a memória do Hermes: as skills da ponte colam o
  contexto relevante no handoff — contexto que não foi colado não existe.
- As 18 skills do ciclo continuam sendo do plugin (Claude Code/Codex/
  OpenCode/Cursor); a ponte adiciona a superfície de operação 24/7, não uma
  quinta distribuição do plugin.
