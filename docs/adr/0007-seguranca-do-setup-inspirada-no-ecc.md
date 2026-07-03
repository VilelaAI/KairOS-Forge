# ADR-0007 — Segurança do setup da fábrica (inspirado no ECC)

**Status:** Aceito
**Data:** 2026-05-29

## Contexto

Foi feita uma análise comparativa do [ECC — Everything Claude Code](https://github.com/affaan-m/ECC) (Affaan Mustafa), o concorrente mais visível do nicho de plugins multi-CLI para harnesses de agentes (~163–195K estrelas em mai/2026). O ECC é da mesma família que o kairos-forge: plugin multi-CLI, MIT, não-runtime, distribuído por marketplace.

A análise identificou que, em **arquitetura e disciplina**, o kairos-forge não está atrás — a curadoria deliberada (45 agentes, 10 skills) é vantagem de posicionamento, não defasagem. Mas o ECC tem **mecanismos concretos** que cobrem lacunas reais do forge. Três foram considerados absorvíveis por serem técnicos/genéricos (e portanto compatíveis com o escopo MIT do forge, não regulatórios do kairos-ai):

1. **Captura automática de aprendizado** ("instinct system" com confidence scoring) que alimentaria o `/evoluir`, hoje 100% manual.
2. **AgentShield** — scanning de segurança do *próprio setup* (allow-lists, injeção em hooks, segredos, risco de MCP), não do código do cliente.
3. **Guia de otimização de tokens** (model selection, thinking budget, autocompact, desligar MCP não usado).

O CLAUDE.md já **exige** allow-list explícita de ferramentas por agente ("Nunca dar acesso total"), mas não havia **nenhuma verificação automática** disso. As skills `analisar-ameacas` e `revisar` miram o código do produto, deixando a segurança da própria configuração da fábrica sem cobertura.

## Decisão

Absorver primeiro o item de **maior multiplicador** (segurança do setup destrava confiança em escalar agentes), seguindo a regra de ouro do forge de **uma capacidade por vez**:

- **Novo `scripts/check-agent-security.py`** — versão MIT/genérica e enxuta do conceito AgentShield. Sem dependências (stdlib). Audita três classes de risco da *configuração*: (a) allow-list de `tools:` ausente/vazia/curinga nos agentes; (b) padrões de injeção em comandos de hook (`curl|sh`, `eval`); (c) segredos hardcoded (chaves AWS/Anthropic/GitHub, chave privada, credencial atribuída a literal), com filtro de placeholders. Sai com código 1 em achados de severidade ALTA — pronto para CI/pre-commit. Recebe a raiz a auditar como argumento.
- **`/kairos-forge:auditar` ganha um critério na dimensão Guardrails** — "setup de agentes/hooks customizados auditado". A dimensão continua com 20 pontos: os 5 critérios anteriores foram rebalanceados (4→3 em lint, CI, gates e pre-commit) para abrir 4 pontos ao novo critério. A skill instrui rodar o script apontando para `.claude` do projeto cliente.

Os outros dois conceitos (captura automática para o `evoluir`; guia de tokens) ficam registrados como candidatos para os próximos ciclos de `/evoluir`, não implementados agora.

## O que foi deliberadamente NÃO absorvido do ECC

- **Dashboard (Tkinter), daemon e control plane em Rust** — viola ADR-0001 (plugin, não runtime). Mesma lógica que já barra dashboard Next.js e worker headless vindos do kairos-ai.
- **Inflação de superfície** (119–249 skills, 28–63 agentes) — a curadoria do forge é feature, não déficit.
- **Modelo comercial Pro e packs de domínio** (prediction-market etc.) — fora de escopo; domínios vão para o kairos-ai.
- **Auto-correção em loop / assertions binárias / Ralph Loop** — território regulado do kairos-ai. Do vocabulário de verificação do ECC (grader types, pass@k), só o conceito de *grader para output não-determinístico* é genérico; não foi implementado nesta rodada.

## Consequências

Boas:

- A exigência do CLAUDE.md sobre allow-lists deixa de ser honra-system e vira check automático — guarda de regressão (passa hoje com os 45 agentes; falha se alguém afrouxar).
- O próprio repositório do plugin ganha um scanner de segredos rodável em CI.
- A auditoria semanal passa a enxergar a segurança da configuração do projeto cliente, não só do produto.

Custos / limitações:

- O script é heurístico: a detecção de injeção em hook e de segredos é por regex, sujeita a falsos negativos. É um piso de segurança, não substitui revisão da Helena.
- O critério novo da auditoria pontua cheio quando o projeto não tem config customizada em `.claude/` — correto, mas significa que projetos sem agentes próprios não exercitam o check.
- Manter a duplicação atual entre a árvore raiz e `plugin/` exige espelhar o script e a edição da skill nas duas. (A divergência raiz↔plugin é uma dívida pré-existente, registrada aqui mas não resolvida neste ADR.)

## Versão

Patch **0.6.0 → 0.6.1**: mudança em prompt de skill (`auditar`) + novo script de tooling. Não adiciona skill nem agente (não justifica minor). Atualizados os 4 arquivos de versão (2 `marketplace.json` + 2 `plugin.json`).
