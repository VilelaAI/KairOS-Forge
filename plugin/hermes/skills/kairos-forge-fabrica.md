---
name: kairos-forge-fabrica
description: Use quando a tarefa é engenharia estruturada — feature multi-arquivo, SPEC rastreável, migração de legado, eval de IA ou revisão pré-PR — e deve ser roteada para o Claude Code com o plugin kairos-forge como motor de engenharia
version: 1.0.0
tags: [roteamento, engenharia, kairos-forge, claude-code]
---

## Visão geral

O kairos-forge é uma fábrica de software com agentes especializados
coordenados por Laura (Tech Lead), instalada como plugin do Claude Code. Esta
skill ensina a reconhecer quando o trabalho pede a fábrica e a compor o
handoff — o Claude Code **não enxerga a memória do Hermes**, então todo
contexto relevante vai no prompt.

Divisão de papéis: **o Hermes opera** (kanban, cron, aprovações, canal com o
fundador); **a fábrica projeta e constrói** (SPEC, implementação por
especialistas, validação contra contrato, revisão multi-agente).

## Quando usar

Roteie para a fábrica quando a tarefa casar com qualquer linha:

| Sinal | O que a fábrica faz |
|---|---|
| Feature que toca 3+ arquivos, schema ou API | `/kairos-forge:especificar` → SPEC rastreável → implementação com gates |
| "Antes de codar, o que exatamente vamos construir?" | SPEC com requisitos, critérios de aceite e matriz de testes |
| Migração/modernização de legado | `/kairos-forge:migrar` — estrangulamento com testes de caracterização e rollback |
| Feature com LLM que precisa de avaliação | Alice (Evals de IA) — gold set, regressão de prompt como gate |
| Revisão de segurança/qualidade antes de PR | `/kairos-forge:revisar` — Helena (segurança), Patrícia (QA), Vinícius (performance) |
| Feature sensível (auth, PII, pagamento) | `/kairos-forge:analisar-ameacas` antes de implementar |

**Não** roteie para a fábrica: correção de 1 arquivo (< 20 linhas — Codex ou
Hermes resolvem), tarefa de ops/deploy/monitoramento (fica no Hermes), decisão
de produto (fica com o profile de produto do Hermes).

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
   /kairos-forge:especificar [descrição específica do que construir]

   Restrições:
   - Escopo cirúrgico: mudar só o que a tarefa exige, sem refatorar código vizinho
   - Nunca commitar segredos, .env, chaves ou credenciais — escanear git diff antes de cada commit
   - [restrições do brief]
   ```

3. Execute no diretório do projeto: sessão interativa (`claude`) quando o
   fundador quiser acompanhar, ou headless (`claude -p "<prompt>"`) no fluxo
   autônomo — nesse caso siga a skill `kairos-forge-ciclo`.
4. Ao final, salve na memória do Hermes o resultado (SPEC criada, PR aberto,
   gates rodados) e atualize o card no kanban com a evidência.

## Fronteira de aprovação

A fábrica pede aprovação nos pontos irreversíveis — e o Hermes é o canal:
SPEC aprovada antes de implementar, migração com janela de corte, release de
produção, rollback, mudança destrutiva de dados. Repasse essas perguntas ao
fundador pelo chat e devolva a resposta ao ciclo. Nunca aprove em nome dele.

## Armadilhas

- Contexto implícito não existe: o que não for colado no prompt, a fábrica
  não sabe. Inclua sempre o brief e as decisões da memória.
- A fábrica trabalha em PT-BR e pergunta quando falta informação essencial
  (Pare e Pergunte) — repasse as perguntas ao fundador em vez de inventar
  respostas.
- Um ciclo por vez por projeto: não dispare duas SPECs simultâneas no mesmo
  repositório.

## Verificação

- A saída esperada existe (SPEC em `docs/specs/`, código commitado, PR)
- Gates da SPEC rodados e verdes (`/kairos-forge:validar` sem bloqueio)
- Nenhum segredo em arquivos commitados
- Resultado registrado na memória do Hermes e no card do kanban
