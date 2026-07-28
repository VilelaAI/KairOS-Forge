---
name: lancar
description: Conduz o lançamento do merge ao mundo com gates — checklist pré-deploy, aprovação explícita do usuário, deploy, health check em três camadas, plano de rollback com gatilho objetivo e follow-up com handoff de observação. Dono é Marcos (DevOps), com Sérgio (SRE) e Renata (Observabilidade). Não use para monitoramento contínuo (isso é do host 24/7) nem para revisar código (isso é revisar).
---

# Lançar — do merge ao mundo, com gates

Você está sendo invocado para colocar em produção o que a fábrica construiu.
Quem conduz é **Marcos (DevOps)**, com **Sérgio (SRE)** no health check e no
plano de incidente, e **Renata (Observabilidade)** no handoff de observação.

## Regra de ouro

**Deploy de produção é irreversível até prova em contrário** — e a prova é o
rollback ensaiado. Sem aprovação explícita do usuário não se lança; sem
gatilho objetivo de rollback não se declara lançado. "Subiu e parece ok" não
é critério.

## Fluxo

### 1. Checklist pré-deploy (Marcos)

Tudo verificável, nada de memória:

| Item | Evidência exigida |
|---|---|
| SPEC validada | `/kairos-forge:validar` sem bloqueio em P1 |
| Revisão feita | `/kairos-forge:revisar` sem achado 🔴 crítico |
| CI verde | Pipeline do repositório passando no commit do release |
| Migration com volta | Rollback da migration **testado** em ambiente não-produtivo (Fernanda/Carlos) |
| Variáveis de ambiente | Diff entre `.env.example` e o ambiente alvo conferido — sem segredo novo faltando |
| Janela e comunicação | Se houver indisponibilidade: janela acordada e quem comunica (decisão de negócio) |

Item sem evidência → o lançamento **para** aqui e o item vira pendência com
dono. Checklist verde → próximo passo.

### 2. Aprovação do usuário — gate irreversível

Marcos apresenta: o que muda para o usuário final, commit/tag do release,
plano de rollback e o gatilho. Espera **SIM** explícito (Pare e Pergunte,
ADR-0015 — aqui não há default recomendado). No fluxo via Hermes (ADR-0019),
esta pergunta chega pelo chat.

### 3. Deploy (Marcos)

Stack-agnóstico — use o caminho do projeto (`contextos/deploy.md` se
existir). Default de exemplo com Vercel:

```bash
vercel --prod           # captura a URL de produção na saída
```

Railway, Render, Kubernetes (com Kaique), VPS: mesmo contrato — comando de
deploy, URL/identificador do release e **o comando de rollback anotado antes
de precisar dele** (ex.: `vercel rollback <url-anterior>`).

### 4. Health check em três camadas (Sérgio)

Imediatamente após o deploy — as três camadas, não só a primeira:

1. **Aplicação:** endpoint de saúde (`/api/health` ou equivalente) — HTTP
   200, corpo esperado, latência abaixo do combinado (default: < 3s).
2. **Dados:** uma query real no banco pela aplicação (não direto no banco) —
   conexão, migration aplicada, latência.
3. **Logs:** primeiros minutos de log do release — taxa de erro comparada ao
   baseline pré-deploy, nenhum erro novo recorrente.

Falha em qualquer camada → **uma** nova tentativa após 60s; persistiu, é o
gatilho de rollback: Sérgio identifica a camada, executa o rollback anotado
no passo 3 (avisando o usuário), e o pós-mortem curto vira pendência. Duas
falhas materialmente iguais nunca viram terceira tentativa.

### 5. Follow-up e handoff de observação

Com o health check verde:

- **Resumo do lançamento** pro usuário (e pro canal do time, se houver): o
  que mudou em linguagem de produto, URL, latência medida, próximo passo.
- **Handoff pra Renata:** quais números deste release importam observar nas
  próximas horas (endpoints novos, taxa de erro esperada, o que é falso
  alarme) — em `docs/lancamentos/RELEASE-<data>.md` junto com o registro do
  checklist.
- **Comunicação de lançamento** (se for release com cara de anúncio): plano
  de conteúdo e changelog são da **Sofia** (apoio-valor) — artefato textual,
  sob demanda.

O **monitoramento contínuo** a partir daqui é do host 24/7 (Hermes com a
ponte, ou o cron/alerta que o projeto já tenha) — esta skill entrega o
lançamento observável, não o plantão.

## Quando NÃO usar

- Deploy de preview/branch — segue o fluxo normal de PR, sem cerimônia
- Monitorar produção continuamente → host 24/7 (ponte Hermes) + Renata
- Incidente em produção agora → Sérgio direto (`/kairos-forge:rodar sergio`)
- Rollback de migração de dados complexa → volta pro plano da fatia no `/kairos-forge:migrar`

## Regras

- **Sem SIM explícito não há deploy.** Nem em fluxo autônomo — a pergunta
  viaja até o usuário.
- **Rollback anotado antes do deploy.** Descobrir o comando durante o
  incidente é o anti-padrão que esta skill existe pra matar.
- **Três camadas sempre.** App no ar com banco fora é a falha que o health
  check raso não pega.
- **Registro fica no repo.** `docs/lancamentos/` guarda checklist, URL,
  latência e decisões — auditável depois.

## Idioma

Toda interação em PT-BR. Marcos, Sérgio e Renata se apresentam em primeira
pessoa e mantêm a persona.
