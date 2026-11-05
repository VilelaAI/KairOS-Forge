# Adoção por peça

O [início rápido](inicio-rapido.md) mostra a fábrica inteira, do `/onboardar` ao
`/auditar`. Quase nenhum time deve começar por ele. A aula 5 do Tech Leads Club (Fábricas
Agênticas) diz por quê:

> *"Não comecem simplesmente aplicar em toda empresa direto, é um tiro no pé. Começar por
> times é interessante: escolher algum, um time menor, explora e vai avaliando."* [01:17:08]

> *"Tem que plugar na infraestrutura da empresa e funcionar. Não pode dar trabalho, porque
> senão ninguém adota."* [02:04:38]

Cada peça da fábrica funciona sozinha. Este guia diz, para cada uma, o que ela resolve, o
que precisa antes, como saber se pegou e como desligar.

## O piloto

1. **Um time, um repositório.** Antes do time, uma pessoa: quem conduz o piloto usa a peça
   na própria sessão e vê onde ela entra no fluxo do time [01:57:55].
2. **Uma dor, uma peça.** Escolha nas tabelas abaixo a peça que responde ao que dói hoje,
   não a mais completa.
3. **Linha de base antes de ligar.** Rode o comando da coluna "Pegou?" e guarde a saída.
   Sem linha de base, o resultado depois é impressão.
4. **Critério e data escritos antes.** O que precisa mudar e quando o time olha de novo, em
   `decisoes/log.md` ou na issue do piloto.
5. **Uma peça por vez.** Com duas peças ligadas na mesma semana, não dá para dizer qual
   delas mudou o número.
6. **Veredicto na data**, com o vocabulário do `/evoluir` (ADR-0043): `ajudou`, `piorou`,
   `sem efeito observado` ou `confundido`. O time ter usado a peça não prova que ela ajudou.
   Só `ajudou` mantém a peça; o resto desliga, com o motivo escrito.
7. **Outro time só depois** de algumas peças mantidas no primeiro. Veja
   [Levar para outro time](#levar-para-outro-time).

## Por onde começar

A aula usa cinco estágios, tirados da Factory ("não dá para levar totalmente a sério",
[35:41]): funcional, documentado, padronizado, com loop de feedback e autônomo. Servem para
escolher a primeira peça:

| O repositório hoje | Comece por |
|---|---|
| O código roda, o setup é manual, nada está escrito | Contexto: `/onboardar`, `/diagnosticar`, grafo de código |
| Fluxos e arquitetura estão escritos | Qualidade sem modelo: os gates no CI e os guardrails |
| Teste, segurança e métrica são padrão do time | SPEC e revisão: `/especificar`, `/validar`, `/revisar`; depois `/entregar` |
| A fábrica já entrega em sessão, com trajetória medida | Os gatilhos: revisão no PR, triagem e, por último, correção de CI |

O quinto estágio, a fábrica que melhora a si mesma sem ninguém, fica de fora de propósito:
PR de auto-melhoria e auto-merge não entram (ADR-0037, ADR-0044). O `/evoluir` propõe;
quem decide é uma pessoa.

## Sem instalar nada

Os scripts da fábrica são Python só com a biblioteca padrão e leem o git e os arquivos que
existem. Não precisam do plugin, do `/onboardar` nem de `.agents/`. Clone uma vez:

```bash
git clone --depth 1 https://github.com/VilelaAI/kairos-forge /tmp/forge
```

Depois, da raiz do seu projeto, numa branch com mudança. `<plugin>` é `/tmp/forge` (ou o
diretório do plugin instalado), e `main` é a base: troque pela sua.

```bash
python3 <plugin>/scripts/guardrail.py verificar .
python3 <plugin>/scripts/prova.py atalhos --base main
python3 <plugin>/scripts/prova.py testes-alterados --base main
python3 <plugin>/scripts/qualidade.py crap --base main
python3 <plugin>/scripts/qualidade.py duplicacao --base main
python3 <plugin>/scripts/diagnostico.py coletar .
python3 <plugin>/scripts/grafo.py codigo
python3 <plugin>/scripts/telemetria.py prs --dias 30
python3 <plugin>/scripts/telemetria.py comparar --dias 90
```

O que cada um responde:

- **`guardrail.py verificar`:** segredo versionado, requisito `Concluído` sem prova,
  relatório com contrato quebrado e, como aviso, teste existente afrouxado.
- **`prova.py atalhos`:** TLS desligado, erro engolido, tipo burlado, HTML sem escape e
  `sleep` como sincronia, nas linhas que o diff acrescenta. É uma lista para alguém julgar,
  e sai 0.
- **`prova.py testes-alterados`:** teste existente que perdeu asserção, ganhou `skip` ou
  foi apagado.
- **`qualidade.py crap`:** complexidade × falta de cobertura das funções tocadas. Sem
  relatório de cobertura, sai sem nota; com `--cobertura coverage.json`, dá a nota.
- **`qualidade.py duplicacao`:** função tocada parecida demais com outra que já existe.
- **`diagnostico.py coletar`:** churn, concentração de autoria nos hotspots, razão
  teste/produção e taxa de reversão.
- **`grafo.py codigo`:** quem importa quem, por AST, em Python, JS/TS e Go. É o único que
  escreve: `.agents/grafo/codigo.jsonl`, regenerável. Depois, `grafo.py contexto <arquivo>`
  mostra a vizinhança.
- **`telemetria.py prs` e `comparar`:** dos PRs mesclados, quantos são da fábrica, quantos
  chegaram ao merge sem commit humano, e se a entrega da fábrica é revertida ou corrigida
  mais que a humana. Com menos de cinco PRs em cada grupo, diz "não comparável" em vez de
  inventar taxa.

Nenhum gasta token. São a linha de base do piloto e o primeiro passo de quem ainda não
decidiu.

## As peças, por camada

A aula pede para pensar *"como é o instrumento de cada uma dessas camadas na minha
empresa"* [47:58]. As camadas são de onde vem o trabalho, o contexto, o controle, a
execução e a qualidade. Nas tabelas, os comandos de script levam `<plugin>/scripts/` na
frente.

### Qualidade: o que diz se o trabalho saiu certo

| Peça | Resolve | Precisa antes | Pegou? |
|---|---|---|---|
| Gates sem modelo no CI (o job em `templates/ci/README.md`) | PR com segredo, teste afrouxado ou caso selado vazado chegando ao merge | Nada: sem segredo nem token | O histórico do job; cada vermelho traz o motivo |
| Guardrails em hook (vêm com o plugin) | Agente que roda `rm -rf`, lê `.env`, faz force-push na `main` ou marca requisito pronto sem prova | O plugin no Claude Code ou no Cursor | `telemetria.py resumo`: recusas por classe |
| `/revisar` em sessão | Diff sem olhar de segurança e QA antes do PR | O plugin | `telemetria.py ruido`: achados descartados por revisor |
| Revisão no PR (`templates/ci/kairos-forge-revisar.yml`) | PR que ninguém revisa a tempo | O segredo `ANTHROPIC_API_KEY` | `telemetria.py ruido --github`: achados que o time marcou ` · descartado: <motivo>` editando o comentário da revisão mais recente de cada PR |
| `/validar` | "Pronto" que é só alegação; teste que passa sem o patch; critério cujo teste fica verde com qualquer bug plantado | Uma SPEC (`/especificar`) | O relatório em `docs/specs/validacoes/`: P1 sem evidência |
| Auditoria semanal (`/auditar` ou `templates/ci/kairos-forge-auditar.yml`) | Ninguém sabe se a fábrica está melhorando | O plugin, ou o segredo no CI | A pontuação de uma semana contra a outra |

### Contexto: o que o agente sabe do projeto

| Peça | Resolve | Precisa antes | Pegou? |
|---|---|---|---|
| `/onboardar` | Agente que não sabe a stack, os comandos de teste nem o que não tocar | Nada | **Sem número.** Veja se a sessão seguinte usa os comandos de `contextos/testes.md` sem você repetir |
| `/diagnosticar` | Sistema herdado sem saber por onde começar | Nada | `diagnostico.py coletar .` de novo na data do piloto: churn e reversões |
| Grafo de código | Mudança que quebra quem chama de fora do diff | Código em Python, JS/TS ou Go | `grafo.py contexto <arquivo>` antes do PR lista os importadores |
| `/mapear-conhecimento` | SPECs, ADRs e decisões que ninguém acha | Algumas features já com SPEC | `/mapear-conhecimento consultar "<pergunta>"` responde com a fonte |

### De onde vem o trabalho

| Peça | Resolve | Precisa antes | Pegou? |
|---|---|---|---|
| Triagem de issue (`templates/ci/kairos-forge-triar.yml`) | Backlog sem triagem; issue que chega sem informação | O segredo e os nove rótulos `forge:*` (`templates/ci/README.md`) | `painel.py --caixa --github`: issues `forge:falta-informacao` esperando resposta |

Se o trabalho chega pelo Slack, a aula começaria por um bot ali [48:11]. Na fábrica, a
entrada é a issue.

### Controle: quem decide o próximo passo

| Peça | Resolve | Precisa antes | Pegou? |
|---|---|---|---|
| `/especificar` | Código que começa antes de alguém entender o pedido | O plugin | SPECs em `docs/specs/` com as críticas em `docs/specs/criticas/` |
| `/entregar` | Você encadeando especificar, construir, validar e revisar à mão | `/especificar`, `/validar` e `/revisar` mantidos no piloto; branch própria num worktree | `telemetria.py espera` (quanto do ciclo esperou alguém), `telemetria.py prs` e `painel.py --caixa` |
| Painel do arco (`/forge-painel`, só no Claude Code com mods) | Gate humano que passa batido no fim de uma resposta longa; arco que você só vê perguntando | O plugin; nada a configurar (ADR-0051) | `telemetria.py espera`: a espera nos gates `aguardando_*` cai depois do piloto |
| Pausa da faixa 3 na execução (só no Claude Code com mods) | Agente em modo automático aplicando infraestrutura, publicando ou migrando banco remoto antes de qualquer revisão | `/entregar` ou `/mobilizar` no piloto; nada a configurar (ADR-0052) | `telemetria.py resumo`: as pausas da faixa 3 por efeito, e quantas viraram `escalado` no `telemetria.py espera` |
| `/mobilizar` | Feature grande demais para um agente só | `/entregar` mantido; no Claude Code, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | `quadro.py ledger <slug>`: tokens por tarefa concluída, desfeita e em aberto (só no Claude Code) |

### Execução: onde o trabalho roda

| Peça | Resolve | Precisa antes | Pegou? |
|---|---|---|---|
| O mesmo plugin para o time | Cada pessoa com um jeito de pedir ao agente | O piloto com peças mantidas | Ver [Levar para outro time](#levar-para-outro-time) |
| Correção de CI vermelho (`templates/ci/kairos-forge-corrigir.yml`) | Branch vermelha esperando alguém ler o log | Guardrails e telemetria rodando (ADR-0026) e o app da fábrica, para o PR disparar o CI (`docs/identidade-do-agente.md`) | `telemetria.py prs`: PRs `forge/corrige-*` mesclados sem commit humano; `telemetria.py comparar` |

## Desligar

- **Workflow de CI:** apague o arquivo de `.github/workflows/`. Sem o segredo
  `ANTHROPIC_API_KEY`, os quatro gatilhos já pulam com uma mensagem, em vez de falhar.
- **Plugin:** `/plugin disable` ou `/plugin uninstall`. Saem juntos as skills, as personas
  e os hooks, ou seja, a telemetria e os guardrails. O que o `/onboardar` e as skills
  escreveram (`CLAUDE.md`, `contextos/`, `docs/specs/`, `decisoes/`) é texto do projeto e
  fica.
- **Uma classe de guardrail:** `{"modos": {"<classe>": "aviso"}}` em
  `.agents/guardrails.json`, escrito por você, não pelo agente. O piso não desliga: caminhos
  sagrados, leitura de segredo, fiação dos hooks, `rm -rf` fora do projeto, controle da
  máquina e pular os hooks do git. Ele só sai junto com o plugin.
- **Script avulso:** não deixa rastro, fora o `.agents/grafo/codigo.jsonl` do
  `grafo.py codigo`.

## Levar para outro time

**O mesmo plugin para todo mundo do repositório.** Versione as duas chaves em
`.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "kairos-forge": { "source": { "source": "github", "repo": "VilelaAI/kairos-forge" } }
  },
  "enabledPlugins": { "kairos-forge@kairos-forge": true }
}
```

O Claude Code só registra o marketplace numa pasta em que a pessoa confiou, no diálogo de
confiança. Quem vir *"enabled in project settings but isn't installed"* roda uma vez:

```bash
claude plugin install kairos-forge@kairos-forge --scope project
```

Quem precisa ficar de fora desliga só para si: `/plugin uninstall` e *Disable for me*, que
grava `false` no `.claude/settings.local.json`. Para a organização inteira, as mesmas duas
chaves vão nas configurações gerenciadas
([Manage plugins for your organization](https://code.claude.com/docs/en/plugins/org)).
No Codex, no OpenCode e no Cursor, a instalação está no [README](../README.md).

**Mods de terceiros convivem mal com o piso.** Um mod instalado por uma pessoa fica no mesmo
nível da fábrica e pode responder no lugar dos hooks dela ou aprovar uma chamada que o
guardrail recusou. Onde o time depende do piso, instale a fábrica pelas configurações
gerenciadas com `prependPlugins` e ligue `allowManagedModsOnly`
([Manage mods for your organization](https://code.claude.com/docs/en/plugins/mods/admin)).
Sem isso, o guardrail ainda impede o agente de mexer na fiação, mas não impede uma pessoa de
instalar um mod que a contorne.

**As mesmas peças, na mesma ordem.** O time novo começa pelas peças que o primeiro
manteve, com a linha de base dele, e não pela fábrica inteira. A proposta leva o
veredicto de cada peça e o comando que mediu.

## O que não fazer

- Instalar tudo e começar pelo `/entregar` num time que nunca escreveu SPEC.
- Ligar a correção de CI antes dos guardrails e da telemetria (ADR-0026).
- Ligar duas peças na mesma semana.
- Contar adoção como resultado.
