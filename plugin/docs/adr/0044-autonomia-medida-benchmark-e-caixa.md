# ADR-0044 — Autonomia medida pelo git, benchmark colhido do histórico e caixa de entrada

- **Status:** aceito
- **Data:** 2026-10-26
- **Versão:** v0.37.0

## Contexto

A Warp publica em [warp.dev/factories](https://www.warp.dev/factories) o **Factories**: uma
fábrica de software agêntica em que um orquestrador (*foreman*) distribui o trabalho entre
agentes, automações disparam execuções por evento, cada execução roda em sandbox, avaliadores
e benchmarks medem a qualidade, a fábrica abre PRs de melhoria sobre ela mesma, e uma caixa de
entrada junta o que espera por uma pessoa. A métrica que o produto põe na frente é a
**autonomia**: a fração de PRs mesclados sem nenhum push humano. E, mesmo vendido como
fábrica autônoma, **ele não mescla por você**.

A pergunta que motivou a leitura veio do dono do ecossistema: o KairOS foi pensado desde o
início como fábrica de software agêntica rodando de forma 100% autônoma. A auditoria mostrou
que o forge já tem a maior parte da forma e que falta o que torna a autonomia uma afirmação
verificável:

| Mecanismo do Factories | O que o forge tinha | A lacuna |
|---|---|---|
| Orquestrador distribuindo trabalho | Laura, `/entregar` com `ciclo.py`, `/mobilizar` com `quadro.py` (ADR-0023/0029/0035) | nenhuma |
| Automação por evento | `templates/ci/`: revisar no PR, corrigir CI vermelho, auditar por cron, triar issue (ADR-0026/0040) | nenhuma |
| Sandbox por execução | worktree por teammate e POC em worktree (ADR-0024/0040) | VM descartável é runtime, não plugin (ADR-0001) |
| Autonomia = PRs mesclados sem push humano | dimensão **Autonomia** do `/auditar`: ciclos sem intervenção, lidos da trajetória (ADR-0021) | só existe onde há hook — no Codex e no OpenCode pontua 0. E mede o ciclo, não o PR: commit humano feito depois do PR aberto não aparece |
| Benchmark a partir de tarefas reais | `/avaliar` com gold set à mão; `comportamento-fabrica` com 14 casos; o laboratório Harness² adiado por falta de 30+ tarefas com parte selada (ADR-0025/0031/0043) | cada entrega já mesclada, com teste no diff, é um caso pronto, e ninguém a transformava em caso |
| Caixa de entrada | `painel.py` mostra um ciclo por vez; gates, escalações, bloqueios do quadro, issues de triagem e PRs ficam cada um no seu lugar | nada respondia "o que está esperando por mim agora?" |
| PRs de auto-melhoria | `/evoluir` com veredicto e humano dentro (ADR-0043) | recusado de propósito: é o auto-graft do ADR-0037 |
| Nunca mescla por você | auto-merge fora (ADR-0031) | convergência, não lacuna |

**Sobre o "100% autônomo".** Nem o produto que serviu de inspiração tira a pessoa do merge. A
régua do forge, desde o ADR-0024, é que a supervisão humana sai do caminho onde a
reversibilidade e a evidência mostram que pode sair, e não onde alguém declara. Os três gates
do planejamento (ADR-0033) e o merge continuam humanos. O que este ADR faz é dar número à
autonomia em todos os CLIs, para que a decisão de afrouxar um gate seja tomada com medição, e
dar à fábrica o benchmark que essa decisão precisa. O worker 24/7 e a notificação ativa são do
runtime ([kairos-symphony](https://github.com/VilelaAI/kairos-symphony)), que consome os
contratos daqui (ADR-0034).

## Decisão

**1. Autonomia de PR medida pelo git — `telemetria.py prs`.** Commit de agente é o que traz o
trailer `Fabrica: kairos-forge`, o `Co-Authored-By: Claude` que o Claude Code já põe por
padrão, ou o autor `kairos-forge` dos templates de CI, mais as `--marca REGEX` que o projeto
declarar. **Autonomia de PR** = PRs mesclados com ao menos um commit de agente e nenhum commit
humano ÷ PRs mesclados com ao menos um commit de agente. Sem PR da fábrica na janela, o número
é "não medido", nunca 0%.

- **Fonte:** o `gh` quando está autenticado (merge, squash e rebase, com os commits de cada
  PR); senão, os merges com commit de merge na primeira linha de `HEAD`. A saída diz qual fonte
  usou e, no git, que squash e rebase não aparecem.
- **O trailer passa a ser escrito.** O prompt do teammate do `/mobilizar`, o `anti-drift.md`, a
  candidata do `/otimizar` e o commit do `kairos-forge-corrigir.yml` terminam com
  `Fabrica: kairos-forge`. É o único jeito de
  reconhecer a fábrica nos CLIs que não põem trailer próprio. A chave é sem acento de
  propósito: o `git interpret-trailers` só reconhece chave ASCII. O detector aceita as duas grafias.
- **O `/auditar` reporta e não pontua.** A linha da dimensão Autonomia passa a trazer a
  autonomia de PR (taxa, N, fonte) ao lado da nota da trajetória. A rubrica não muda: mudar a
  régua torna incomparáveis as auditorias anteriores, e a divergência entre os dois números
  é o achado (ciclo limpo com PR remendado à mão depois, ou PR autônomo de uma fábrica sem
  hook).

O modelo não escreve o histórico do merge, e o número existe no Codex, no OpenCode e no CI,
onde a trajetória não existe. Medido no próprio repositório, fonte git: 8 PRs mesclados, 8 da
fábrica, 8 sem commit humano.

**2. Benchmark colhido do histórico — `prova.py colher`.** Cada PR mesclado da fábrica com teste
criado ou alterado vira um caso candidato em `evals/entregas/candidatos.jsonl`: o **pedido** é a
issue que o PR fechou (nunca o corpo do PR, que descreve a solução), a **base** é o commit de
antes da entrega (primeiro pai no merge; no squash, um atrás; no rebase, reconhecido pelo título
igual ao do último commit do PR, N atrás), e o **gabarito** são os testes que a entrega trouxe.
Sem `gh` ou sem issue ligada, o pedido é o título e o caso sai com `revisar_pedido: true`.

- `--validar` aplica ao passado a prova negativa do ADR-0039: em dois worktrees descartáveis,
  roda os testes da entrega contra a base (tem de falhar) e contra a entrega (tem de passar).
  Só fica o caso com oráculo `valido`; o que passa na base, ou não executa, sai com o motivo.
- A colheita é idempotente: caso já presente em `candidatos.jsonl`, `gold.jsonl` ou
  `selado.jsonl` da pasta de saída (por padrão `evals/entregas/`) não entra de novo.
- **Candidato não é caso selado.** A divisão visível × selado continua da Alice no `/avaliar`, e
  o `prova.py selado` (ADR-0043) passa a proteger o que for selado.

É a fonte do benchmark que o ADR-0043 pediu antes de abrir o laboratório Harness²: tarefas do
tamanho de uma entrega real, com teste que prova, em quantidade que cresce sozinha com o uso.

**3. Caixa de entrada — `painel.py --caixa`.** Uma vista só do que espera por uma pessoa: o gate
humano de cada ciclo (1/3 entendimento, 2/3 abordagem, 3/3 aprovação), a SPEC alterada depois
de aprovada (com o `ciclo.py reaprovar` a rodar), o ciclo escalado com o motivo, a tarefa
bloqueada e a vencida no quadro. Cada item diz onde está, o que espera e o comando que resolve.
Com `--github`, entram as issues `forge:falta-informacao` da triagem (ADR-0040) e os PRs abertos,
fora de rascunho, com commit da fábrica. Continua renderização (ADR-0013/0032): lê e mostra,
não escreve nada. O GitHub só entra quando pedido, porque é a única fonte que sai da máquina, e
a saída diz se foi consultado, se falta o `gh` ou se a consulta falhou. `--json` dá a mesma vista
para quem quiser notificar.

## Consequências

| O que | Antes | Depois |
|---|---|---|
| Autonomia no Codex e no OpenCode | 0, sem trajetória | autonomia de PR pelo histórico |
| Commit humano depois do PR aberto | invisível para a Autonomia | conta contra o PR |
| Commit do teammate, do `/otimizar` e do `corrigir.yml` | sem marca da fábrica | trailer `Fabrica: kairos-forge` |
| Caso de benchmark de entrega | escrito à mão | colhido do histórico, com oráculo validado |
| "O que espera por mim?" | ciclo por ciclo, quadro por quadro, GitHub à parte | `painel.py --caixa [--github]` |
| Rubrica do `/auditar` | — | inalterada; autonomia de PR reportada ao lado |

**Positivas**

- Autonomia vira número comparável entre CLIs e entre projetos, com definição escrita e fonte
  declarada.
- O benchmark da fábrica cresce com o uso, e cada caso nasce com a prova de que o teste separa
  quem resolveu de quem não resolveu.
- A pessoa tem um lugar para olhar antes de abrir ciclo por ciclo, e o mesmo JSON serve a quem
  for avisá-la.

**Negativas e limites, declarados**

- **O trailer diz quem digitou, não quem decidiu.** Uma sessão interativa em que a pessoa dita
  cada linha sai com `Co-Authored-By: Claude` e conta como agente. Por isso o 8 de 8 deste
  repositório é verdadeiro e pouco informativo. O número compara bem fábrica com ela mesma ao
  longo do tempo; comparar projetos pede saber como cada um trabalha.
- **O trailer pode ser omitido ou forjado.** Não é guardrail: commit de agente sem trailer conta
  como humano (subestima), e trailer posto em commit humano infla. O `anti-drift.md` proíbe o
  segundo; nada no código impede.
- **Sem `gh`, só merge com commit de merge.** Repositório que faz squash ou rebase precisa do
  `gh` autenticado. O `gh` traz até 200 PRs por consulta.
- **O pedido colhido sem issue é o título**, e título não é enunciado. Esses casos saem marcados
  para reescrita e não devem entrar no selado antes dela.
- **`--validar` custa tempo:** dois worktrees e duas execuções de teste por caso. Teste que
  depende de ambiente (banco, rede, segredo) sai `nao_executado` e é descartado, o que puxa o
  benchmark para o código mais fácil de testar.
- **Só teste criado ou alterado é gabarito.** Entrega que corrige bug sem teste novo não vira
  caso, e é exatamente a entrega que mais precisava de um.
- **A caixa é puxada, não empurrada.** Ninguém é avisado; quem quer aviso lê o `--json` (a ponte
  Hermes, o kairos-symphony, um cron). O JSON da caixa não entra no contrato assinado do
  ADR-0034 nesta versão; entra quando houver consumidor.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Auto-merge quando a autonomia de PR passar de um limiar | Fora desde o ADR-0031. O número informa a decisão humana de afrouxar um gate; não a toma. O próprio Factories não mescla por você |
| PRs de auto-melhoria abertos pela fábrica a partir da própria trajetória | É o auto-graft recusado no ADR-0037. A versão com humano dentro é o `/evoluir` com veredicto (ADR-0043) |
| Pontuar a autonomia de PR na rubrica do `/auditar` já | Torna incomparáveis as auditorias anteriores. Entra na rubrica quando houver algumas auditorias com os dois números lado a lado e se souber como divergem |
| Classe no `guardrail.py` exigindo o trailer em `git commit` | Só funcionaria onde há hook, e lá o Claude Code já põe o trailer dele. A lacuna está justamente nos CLIs sem hook |
| Reconhecer agente por e-mail ou conta de bot | Frágil e específico de cada projeto. O trailer é explícito e o `--marca` cobre o resto |
| Usar o corpo do PR como pedido do caso colhido | O corpo descreve a solução; caso que traz a solução no enunciado mede leitura |
| Selar automaticamente parte dos casos colhidos | A divisão e a rotação são decisão de quem avalia (ADR-0030). Selar por script tiraria a Alice da única decisão que é dela |
| Notificação ativa da caixa (Telegram, Slack, e-mail) | É runtime (ADR-0001). A ponte Hermes (ADR-0019) e o kairos-symphony consomem o `--json` |
| Custo em dinheiro por ciclo e execução remota com retomada local | Pedem quem chama a API e quem hospeda a VM. O ledger de consumo do `/mobilizar` (ADR-0013) é o que cabe no plugin; o resto é do kairos-symphony |
