# ADR-0026 — Gatilhos por evento: a fábrica acorda sem ninguém digitar

- **Status:** aceito
- **Data:** 2026-08-01
- **Versão:** v0.19.0

## Contexto

A definição de L4 na régua de adoção é literal sobre o mecanismo:

> **L4 — Fábrica:** *"Pipelines autônomos cuidam de correções, QA, protótipos e fluxos
> repetíveis. O time confia mais no harness do que em revisão individual de código."*

Pipeline autônomo é, por definição, **orientado a evento**. Até a v0.18 o kairos-forge
tinha 16 skills e todas eram invocadas por slash command — um humano no teclado por unidade
de trabalho. A ponte Hermes (ADR-0019) adiciona chat 24/7 e cron, mas cada tarefa ainda
começa com uma frase do fundador.

E havia uma lacuna mais concreta: o repositório tem CI **para si mesmo** e nunca entregou
**nenhuma receita de CI para o projeto do usuário**. A fábrica que prega guardrails e gates
deixava o usuário montar a integração sozinho.

## Decisão

`templates/ci/` com três workflows prontos para o projeto do usuário, mais um README que é
metade instalação e metade modelo de segurança.

| Arquivo | Dispara quando | O que faz | Escreve |
|---|---|---|---|
| `kairos-forge-revisar.yml` | PR aberto/atualizado | `/revisar` e comenta o parecer | comentário |
| `kairos-forge-corrigir.yml` | CI do projeto falha | Diagnostica e corrige, **abrindo PR** | branch + PR |
| `kairos-forge-auditar.yml` | Segunda 09:00 (cron) | `/auditar` e abre issue com as 3 lacunas | issue |

### A ordem de instalação faz parte da decisão

O README abre com isto, e não é enfeite:

> Instale estes workflows **depois** de ter telemetria (ADR-0021) e guardrails
> determinísticos (ADR-0022) rodando. Gatilho por evento sem instrumento e sem contenção
> não é autonomia — é pipeline sem supervisão.

E o `/auditar` reforça pelo outro lado: na dimensão Autonomia, a lacuna "tudo verde e ainda
sem gatilho por evento" só é recomendada **depois** das lacunas de telemetria e guardrail.
Recomendar gatilho a um projeto sem guardrail seria recomendar dano automatizado.

A recomendação de adoção é gradual e por custo: comece pelo `auditar` (semanal, barato,
zero escrita em código), depois `revisar`, e só então `corrigir`.

### O modelo de segurança do `corrigir`

É o workflow que mais se aproxima do L4 e o mais perigoso. Cinco travas, nenhuma opcional:

1. **Nunca escreve em branch protegida.** Cria `forge/corrige-<branch>-<run>` e abre PR.
2. **Não reage a si mesmo** — a condição exclui branches que começam com `forge/corrige-`.
   Sem isso, um CI que continua vermelho vira loop infinito consumindo credencial.
3. **Deduplica** — se já existe PR de correção aberto para aquela branch, não empilha outro.
4. **Uma rodada, sem insistir.** O prompt carrega a regra que a fábrica já usa no `/lancar`
   e na ponte: *"duas falhas materialmente iguais nunca viram terceira tentativa"*.
5. **Escopo travado no prompt:** corrigir só o que causou a falha, não refatorar, não tocar
   em `.github/workflows/`. Agente que conserta o CI editando o CI é o Goodhart mais óbvio
   que existe — e o `guardrail.py` (ADR-0022) já protege esse caminho de qualquer forma.

Os três workflows rodam `guardrail.py verificar` antes de aceitar o resultado: em CI não
existe `PreToolUse`, então o mesmo contrato é verificado depois.

### Por que abre PR em vez de commitar direto

Porque L4 é *"o time confia mais no harness do que em **revisão individual de código**"* —
não "ninguém revisa nada". O PR é onde a evidência aparece. O que sai do caminho humano é a
leitura linha a linha; o que fica é a decisão de integrar.

O README diz explicitamente que auto-merge é decisão do time, e **não deve ser ativado
antes de o número da dimensão Autonomia justificar**. A régua existe; usá-la é escolha de
quem opera.

### Ausência de credencial pula, não falha

Os três verificam `ANTHROPIC_API_KEY` e saem limpos se não houver. Fork e PR externo não
ficam vermelhos por falta de segredo — mesma regra do ADR-0025: falso vermelho treina o
time a ignorar o vermelho.

## Consequências

**Positivas**

- É o movimento mais visível de L4: a fábrica trabalha enquanto ninguém olha.
- Fecha a lacuna dos CLIs sem hook — Codex, OpenCode e Cursor não têm `PreToolUse` nem
  telemetria, mas todos têm CI. O `guardrail.py verificar` no pipeline é o caminho de
  paridade possível para eles (ADR-0022).
- `auditar` semanal por cron transforma o ritual de sexta em algo que acontece mesmo quando
  ninguém lembra — que era o modo de falha real do ADR-0012.

**Negativas e limites, declarados**

- **Custo por disparo, e ele multiplica.** Um `revisar` por PR num repo com 30 PRs/semana
  são 30 execuções. O README manda estimar antes de ligar os três; é a mitigação possível
  sem medir a conta do usuário.
- **São templates, não produto instalado.** O usuário copia e ajusta (nome do workflow de
  CI observado, cron, branch base). Não há mecanismo de atualização: melhorias no template
  não chegam a quem já copiou.
- **`workflow_run` tem armadilhas.** Dispara no contexto da branch default, exige checkout
  explícito do head, e o token tem permissões diferentes do `pull_request`. Os templates
  tratam isso, mas quem editar precisa saber.
- **Não há sandbox.** O agente roda no runner do GitHub com o que o `permissions:` der.
  Permissão mínima por workflow reduz o raio, não o elimina.
- **`corrigir` pode propor bobagem.** Uma rodada, escopo travado e PR obrigatório existem
  exatamente porque isso vai acontecer. O custo de uma proposta ruim é um PR fechado.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| `corrigir` commitando direto na branch do PR | Some com a evidência e com o ponto de decisão. Um erro passa a exigir arqueologia de commits em vez de fechar um PR |
| Usar a action oficial em vez de `claude -p` | O `claude -p` já é o caminho que a ponte Hermes usa e não depende da API de uma action específica. Menos superfície para quebrar |
| Instalar o plugin via marketplace no CI | O comando é TUI e não roda headless. Copiar `plugin/skills` e `plugin/agents` para `.claude/` é o caminho portátil documentado |
| Rodar `entregar` (arco completo) por gatilho | Arco completo dispara o gate de aprovação da SPEC, que precisa de humano. Gatilho por evento serve para o que fecha sem decisão de escopo: revisar, corrigir, auditar |
| Não entregar templates e deixar o usuário montar | Era o estado até a v0.18, e o resultado observado é que ninguém monta. Fábrica que não entrega a esteira entrega bancada |

## Emenda (v0.41.3): fronteira de confiança

Os templates passavam texto de fora ao `claude -p` sem marcá-lo como dado e sem declarar
ferramentas, e o `corrigir` interpolava o nome do branch no script com `${{ }}`. A
leitura de dois artigos sobre fábricas de agentes levou à conferência: o *How to Build
an Agent Factory* trata saída de ferramenta como dado não confiável. A conferência achou
três caminhos:

- **CI de fork no `corrigir`.** O `workflow_run` roda no contexto da base, com o segredo e
  token de escrita. Um branch de fork com o mesmo nome de um branch da base passava pelo
  checkout e entregava ao agente um log escrito por quem abriu o PR.
- **Nome de branch no script.** `git checkout -b "forge/corrige-${{ ...head_branch }}"`
  executa `$(...)` contido no nome. O checkout de antes bloqueava o caso de fork por
  acaso, não por desenho.
- **Ferramentas e hooks do branch.** Sem ferramentas na linha de comando, quem decidia
  era o `.claude/settings.json` do branch. E o `claude -p` roda os hooks e os servidores
  MCP do projeto mesmo numa pasta nunca confiada.

Decisão: a regra 6 do `templates/ci/README.md`. Nada de `${{ }}` de texto do evento em
`run:`; cada `claude -p` declara as ferramentas (`--allowedTools`, `--disallowedTools`),
desliga hooks e MCP do projeto e diz no prompt que o texto de fora é dado; o `corrigir`
filtra fork e só roda o comando de teste declarado em `GATE`.

Efeito colateral: nas versões recentes do Claude Code, `claude -p` sem regra de allow
nega edição e Bash, e o allow do `.claude/settings.json` não vale numa pasta nunca
confiada, como a do runner. O `corrigir` provavelmente não conseguia editar; não foi
conferido num runner. Agora ele edita por `--permission-mode acceptEdits` e roda só o
`GATE`.

O `scripts/tests/test_ci.py` lê os YAML e roda cada `claude -p` contra uma CLI falsa.

## Emenda (v0.42.8): a fábrica com identidade própria

Na aula 5 do Tech Leads Club, o bot do professor tem conta própria no GitHub: *"porque a
gente consegue dar permissões específicas para ele e ver o que ele está fazendo"*. Ele também
alerta contra o atalho comum: *"não usem o mesmo acesso de uma pessoa para um agente; a pessoa
precisa de mais acesso às vezes, e aí tu dá um monte de escrita para o agente"*. Se algo der
errado, o agente se bane, se bloqueia e se revoga sem tirar acesso de ninguém.

Os gatilhos já agiam com o token do workflow, que não é uma pessoa. A conferência achou dois
defeitos e uma lacuna:

- **O PR do `corrigir` nunca disparava o CI.** O GitHub não dispara workflows a partir de
  ações feitas com o token do workflow, e o corpo do PR dizia "se o CI daqui também ficar
  vermelho" sobre um CI que não ia rodar.
- **O `corrigir` não lia o log.** O `permissions:` declarava `contents` e `pull-requests`, e
  declarar zera o resto. Sem `actions: read`, o `gh run view --log-failed` falhava calado, e o
  agente corrigia com "log indisponível" no lugar do erro.
- **Nada impedia um token pessoal.** Trocar o `github.token` por um `secrets.GH_PAT` "para o CI
  disparar" era o conserto óbvio, e é exatamente o que a aula manda não fazer.

As três correções:

- **App da fábrica, opcional, nos quatro gatilhos.** O passo "Identidade da fábrica" gera o
  token do GitHub App (`actions/create-github-app-token`) quando a variável `FORGE_APP_ID`
  existe. Todo `GH_TOKEN` e o checkout do `corrigir` usam esse token, com o token do workflow
  como reserva. Com o app:
  - tudo sai em nome dele;
  - as permissões são as da instalação;
  - revogar é suspender o app;
  - o PR do `corrigir` dispara o CI.

  Chave ausente ou inválida não derruba o job (`continue-on-error`), e sem o app o `corrigir`
  avisa no PR que o CI precisa ser disparado à mão.
- **`actions: read` no `corrigir`.** É a permissão que faltava para o log.
- **`check-agent-security.py` acusa token de pessoa.** Workflow que cita `kairos-forge` e usa
  `secrets.GH_TOKEN`, `secrets.GITHUB_PAT` ou qualquer `secrets.*PAT*` vira achado `MEDIA`.
  Apontado para o `.claude` de um projeto, o checker olha os workflows dele, e o `/auditar`
  já o roda.

O guia `docs/identidade-do-agente.md` traz:
- as permissões mínimas por gatilho;
- a branch protegida com o app fora da lista de quem contorna a proteção (o merge continua
  humano);
- como revogar;
- e a conta da fábrica no tracker e nas fontes ligadas por MCP.

A sessão assistida no terminal continua com a identidade de quem está ali aprovando, separada
pelo trailer (ADR-0044).

### Limites

- **O app é configuração do usuário.** O plugin não cria conta nem app; ele usa um quando
  existe e acusa o atalho que não deve existir.
- **O detector olha o nome do segredo, não o conteúdo.** Um token pessoal guardado como
  `secrets.CHAVE_DO_BOT` passa. O nome é o que a revisão do workflow enxerga, e o guia diz qual
  usar.
- **`actions/create-github-app-token@v1` é dependência externa.** Fica pinada na versão
  principal, como o `actions/checkout@v4` dos mesmos arquivos.
