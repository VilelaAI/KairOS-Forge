---
name: kairos-forge-fabrica
description: Use quando a tarefa é engenharia estruturada — feature multi-arquivo, SPEC rastreável, diagnóstico ou migração de legado, design de UI, eval de IA, revisão pré-PR ou deploy com gates — e deve ser roteada para o Claude Code com o plugin kairos-forge como motor de engenharia
version: 1.1.0
tags: [roteamento, engenharia, kairos-forge, claude-code]
---

## Visão geral

O kairos-forge é uma fábrica de software com agentes especializados
coordenados por Laura (Tech Lead), instalada como plugin do Claude Code. Esta
skill ensina a reconhecer quando o trabalho pede a fábrica e a compor o
handoff — o Claude Code **não enxerga a memória do Hermes**, então todo
contexto relevante vai no prompt.

Divisão de papéis: **o Hermes opera** (kanban, cron, aprovações, canal com o
fundador, monitoramento contínuo); **a fábrica projeta e constrói** (SPEC,
implementação por especialistas, validação contra contrato, revisão
multi-agente, deploy com gates).

## Quando usar

Roteie para a fábrica quando a tarefa casar com qualquer linha:

| Sinal | O que a fábrica faz |
|---|---|
| Feature que toca 3+ arquivos, schema ou API | `/kairos-forge:entregar` — o arco inteiro: SPEC com três gates do fundador, construção, validação e revisão com correção dentro do orçamento, PR. Headless: siga a skill `kairos-forge-ciclo` |
| "Antes de codar, o que exatamente vamos construir?" | `/kairos-forge:especificar` — SPEC com requisitos, critérios de aceite e matriz de testes, sem construir |
| Feature sensível (auth, PII, pagamento) | `/kairos-forge:analisar-ameacas` antes de implementar — no fluxo headless, antes do `entregar` |
| Feature com UI | `/kairos-forge:desenhar SPEC-NNN` — fluxos e cinco estados por view (Isabela); `desenhar verificar` confere a implementação |
| Sistema existente: "o que dói e por onde começo?" | `/kairos-forge:diagnosticar` — seis dimensões medidas e roadmap por impacto × esforço (Rafael) |
| Migração/modernização de legado | `/kairos-forge:migrar` — estrangulamento com testes de caracterização e rollback (Ivan) |
| Feature com LLM que precisa de avaliação | `/kairos-forge:avaliar` — gold set versionado, rubrica em cinco eixos, gate no CI (Alice) |
| Revisão de segurança/qualidade antes de PR | `/kairos-forge:revisar` — Helena, Patrícia, Vinícius e Marcos, conforme o escopo |
| Deploy de produção | `/kairos-forge:lancar` — checklist, SIM explícito do fundador, health check em três camadas, rollback anotado (Marcos) |

**Não** roteie para a fábrica: correção de 1 arquivo (< 20 linhas — Codex ou
Hermes resolvem), monitoramento contínuo e ops do dia a dia (ficam no Hermes;
deploy de produção, não — é o `lancar`), decisão de produto (fica com o profile
de produto do Hermes).

## Pré-requisitos

- Claude Code instalado (`npm install -g @anthropic-ai/claude-code`)
- Plugin instalado no Claude Code: `/plugin marketplace add VilelaAI/kairos-forge`
  e `/plugin install kairos-forge@kairos-forge`
- Diretório do projeto acessível no servidor onde o Hermes roda

## Procedimento

1. Recupere da memória do Hermes o que existir: brief do produto, decisões de
   arquitetura, restrições, tentativas anteriores ("evitar X").
2. Componha o handoff — contexto explícito, tarefa específica, restrições:

   ```
   Contexto do projeto (da memória do Hermes):
   [colar entradas relevantes]

   Tarefa:
   /kairos-forge:<skill da linha da tabela> [descrição específica do que construir]

   Restrições:
   - Escopo cirúrgico: mudar só o que a tarefa exige, sem refatorar código vizinho
   - Nunca commitar segredos, .env, chaves ou credenciais — escanear git diff antes de cada commit
   - [restrições do brief]
   ```

3. Execute no diretório do projeto: sessão interativa (`claude`) quando o
   fundador quiser acompanhar, ou headless (`claude -p "<prompt>"`) no fluxo
   autônomo — com o `entregar`, siga a skill `kairos-forge-ciclo`, que conduz os
   gates do fundador.
4. Ao final, salve na memória do Hermes o resultado (SPEC criada, PR aberto,
   gates rodados) e atualize o card no kanban com a evidência.

## Fronteira de aprovação

A fábrica para no que só gente decide — e o Hermes é o canal: os três gates do
planejamento (entendimento, abordagem, aprovação da SPEC), perguntas do Pare e
Pergunte, SPEC alterada depois da aprovação (`reaprovar`), faixa 3 do raio de
explosão, escalação, release de produção (SIM explícito no `lancar`), janela de
corte de migração, mudança destrutiva de dados e merge. Repasse essas perguntas
ao fundador pelo chat e devolva a resposta ao ciclo. Nunca aprove em nome dele.

## Armadilhas

- Contexto implícito não existe: o que não for colado no prompt, a fábrica
  não sabe. Inclua sempre o brief e as decisões da memória.
- A fábrica trabalha em PT-BR e pergunta quando falta informação essencial
  (Pare e Pergunte) — repasse as perguntas ao fundador em vez de inventar
  respostas.
- Sempre passe a SPEC ao `ciclo.py` (`estado SPEC-NNN --json`, `registrar
  <resultado> SPEC-NNN`): sem ela o script procura "o único ciclo aberto" e
  recusa quando há mais de um.
- Um ciclo por branch, e uma branch por cópia do repositório. O `ciclo.py abrir`
  grava a branch do ciclo, e o guardrail julga o `gh pr create` pelos ciclos da
  branch atual: o PR de um ciclo pronto não espera outro, de outra branch, sair do
  gate. Branch sem ciclo não é atalho — ali valem todos os ciclos abertos. Dois arcos
  na mesma cópia ainda dividiriam a working tree: trabalho paralelo vai em outra
  cópia ou worktree (o estado do ciclo é relativo ao diretório).

## Verificação

- A saída esperada existe (SPEC em `docs/specs/`, código commitado, PR)
- Gates da SPEC rodados e verdes (`/kairos-forge:validar` sem bloqueio)
- Nenhum segredo em arquivos commitados
- Resultado registrado na memória do Hermes e no card do kanban
