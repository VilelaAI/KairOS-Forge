# ADR-0008 — SRE/Incident Commander e Engenheiro AIOps no squad Plataforma

**Status:** Aceito
**Data:** 2026-07-03

## Contexto

O ADR-0007 fechou as lacunas de provisionamento (Igor), orquestração (Kaique), entrega declarativa (Gael) e rede (Nina). Restava o lado de **operação assistida por IA e resposta a incidente** — tema de um segundo workshop de referência ([Imersão AIOps Prática, Veronez](https://eventos.veronez.ai/)): troubleshooting assistido, auto-remediation, observabilidade aumentada com LLM, gestão de incidentes e redução de ruído de alertas.

Boa parte desse conteúdo já estava coberta: Dockerfile/manifests (Marcos/Kaique), pipelines (Marcos), containers ECS/EKS (Kaique), features de IA (Gabriel), e a própria construção de agentes/MCP — que é o que o `kairos-forge` já é. Sobravam duas lacunas reais:

1. **Ciclo de incidente.** Marcos faz deploy, rollback e define SLO, mas ninguém era dono de plantão/on-call, triagem por severidade, runbooks, war room, postmortem blameless, MTTR/MTTD e política de error budget.
2. **IA aplicada à telemetria.** Renata instrumenta (logs, métricas, traces, alertas), mas não havia camada de detecção de anomalia, correlação/deduplicação de alertas (alert fatigue), RCA assistida e análise preditiva por cima desses sinais.

## Decisão

Ainda dentro da v0.7.0 (mesmo release do ADR-0007), o squad Plataforma ganha **mais dois agentes core** (a fábrica passa de 49 para 51; core de 28 para 30):

- **🧯 Sérgio — SRE / Incident Commander** (`sergio-sre`): resposta a incidente, on-call, runbooks, severidade, war room, postmortem blameless, MTTR/MTTD, error budgets, design de auto-remediation.
- **🔮 Aline — Engenheira AIOps** (`aline-aiops`): detecção de anomalia, correlação/deduplicação de alertas, redução de ruído, RCA assistida, análise preditiva, observabilidade aumentada com LLM.

Ambos são core (allow-list `Read, Write, Edit, Grep, Glob, Bash`) e ganham níveis de acionamento próprios no `squad-fabrica.yaml` (`resposta_a_incidente`, `aiops_deteccao`).

### Fronteiras (para não duplicar)

- **Aline × Renata:** Renata **cria** os sinais (instrumentação); Aline **aplica IA** em cima deles (detecção, correlação, predição). Aline nunca substitui a instrumentação-base.
- **Sérgio × Marcos:** Marcos builda/deploya/rollback e define SLO; Sérgio comanda o incidente, escreve o postmortem e cuida da prática de confiabilidade (error budget).
- **Aline → Sérgio:** a detecção da Aline alimenta a resposta do Sérgio.
- **Aline × Gabriel:** Gabriel faz IA de **produto**; Aline faz IA de **operações**.

### Posicionamento (limite deliberado)

O `kairos-forge` é um plugin de **personas/prompts**, não um runtime. Worker headless 24/7 e auto-correção ao vivo estão na lista de "não portar" (ADR-0002 / CLAUDE.md). Por isso Sérgio e Aline **desenham** estratégias e artefatos (runbooks, políticas, regras de detecção, planos de correlação) — não executam remediação nem rodam modelos em produção. Isso mantém o forge do lado lite/MIT, sem invadir o território de runtime do KairOS.

### Versão

Não há novo bump: os dois agentes entram no **mesmo minor 0.7.0** já aberto pelo ADR-0007 (um único release que adiciona seis especialistas de plataforma/ops). A convenção "adicionar agente = bump minor" foi satisfeita pelo 0.6.x → 0.7.0; agentes adicionais antes da publicação do release não exigem novo bump. Só as contagens sobem (49 → 51, 28 → 30 core).

## Consequências

Boas:

- A fábrica cobre agora o ciclo completo de operação: provisionar → orquestrar → entregar → expor → **observar com IA → responder a incidente**.
- Renata deixa de acumular dois papéis (instrumentar + analisar por IA), com fronteira explícita para a Aline.
- Confiabilidade vira prática com dono (Sérgio), não um apêndice do deploy.

Custos:

- Sobreposição sensível Aline × Renata e Sérgio × Marcos. Mitigada nos prompts, que declaram a divisão, e nos níveis de acionamento distintos.
- Mais duas personas para conhecer — os `sinais_ativacao` e a Laura roteiam por contexto.

## Alternativas consideradas

1. **Ampliar a Renata para cobrir AIOps.** Rejeitado: acumularia instrumentação + analytics de IA numa persona só, escondendo a fronteira que justamente queremos explícita.
2. **Ampliar o Marcos para cobrir incidente.** Rejeitado: mistura entrega (CI/CD, rollback) com prática de confiabilidade (on-call, error budget) — papéis distintos na indústria (DevOps × SRE).
3. **Criar um agente de auto-remediation que executa.** Rejeitado: viraria runtime, o que o forge explicitamente não é (ADR-0002). Sérgio/Aline desenham; execução ao vivo fica fora.
4. **Não adicionar nada (AIOps já coberto).** Considerado, mas as duas lacunas (ciclo de incidente e IA sobre telemetria) eram reais e recorrentes.
