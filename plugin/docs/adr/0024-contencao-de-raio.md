# ADR-0024 — Contenção de raio: worktree por teammate e reversibilidade declarada

- **Status:** aceito
- **Data:** 2026-08-01
- **Versão:** v0.18.0

## Contexto

O whitepaper Day-1 lista **sandboxes e ambientes de execução** entre os seis componentes do
harness: *"Where the agent's code actually runs, what it has access to, what it cannot
reach."*

O kairos-forge não tinha nenhum. A tabela comparativa do `/mobilizar` declarava com
honestidade o que existia:

| | `/rodar` | `/mobilizar` |
|---|---|---|
| File ownership | Não enforced | **Enforced via prompt** |

Ownership por prompt é disciplina: o teammate obedece porque foi instruído. Em L3 isso
basta — existe um humano lendo o diff antes do merge, e ele pega o que o prompt não segurou.
No L4 alvo não existe essa rede, e a diferença entre "pipeline autônomo" e "pipeline sem
supervisão" passa a ser exatamente esta: mudança errada é barata de desfazer, ou não?

## Decisão

Duas medidas no `/mobilizar`, ambas condicionadas ao nível de supervisão — não ao tamanho
do time.

### 1. Isolamento por worktree quando a supervisão humana sai do caminho

| Situação | Isolamento exigido |
|---|---|
| Humano vai revisar o PR antes do merge (L3) | **Prompt** — ownership declarado, como sempre |
| Execução autônoma sem revisão humana do diff (L4), ou 3+ teammates em áreas adjacentes | **Worktree** — fronteira física |

```bash
git worktree add .worktrees/<teammate> -b forge/<slug>-<teammate>
git merge --no-ff forge/<slug>-<teammate>     # Laura integra, uma de cada vez
git worktree remove .worktrees/<teammate>
```

Conflito deixa de ser violação de disciplina e vira **impossibilidade física**. Dois
teammates não conseguem sobrescrever o trabalho um do outro, e o merge explícito da Laura é
onde o conflito aparece cedo, em vez de virar corrupção silenciosa que só o humano
descobriria lendo o diff — o humano que, em L4, não está lendo.

O default **não** é worktree, e isso é deliberado: o custo é real (setup por teammate,
merges sequenciais, `.worktrees/` no `.gitignore`) e em fluxo supervisionado não se paga.
A regra é pagar quando a supervisão sai.

### 2. Reversibilidade declarada por tarefa autônoma

Toda task de execução autônoma carrega **como se desfaz**, anotado antes de executar:

- código → o commit é a unidade de revert;
- migration → o rollback existe e foi **rodado** em ambiente não produtivo;
- config/infra → o valor anterior anotado na descrição da task.

E a regra que fecha o critério:

> Tarefa cujo revert você não consegue escrever **não é autônoma** — é irreversível, e
> irreversível para no usuário.

Isto generaliza um contrato que a fábrica já aplicava em dois lugares isolados: o
`/kairos-forge:otimizar` só entra em catraca com revert barato ("mudança irreversível não
entra em catraca"), e o `/kairos-forge:lancar` exige o comando de rollback **anotado antes
do deploy** ("descobrir o comando durante o incidente é o anti-padrão que esta skill existe
pra matar"). O que era regra de duas skills vira critério de admissão da autonomia.

## Consequências

**Positivas**

- Autonomia passa a ter um teste de admissão objetivo: se não dá pra desfazer, não roda
  sozinho. Isso é mais útil que uma lista de ações proibidas, porque cobre casos que
  ninguém enumerou.
- O worktree resolve o problema que o hook não consegue resolver — ownership por teammate
  não é enforçável no `PreToolUse` porque o payload não diz qual teammate chamou (ADR-0022).
- Conflito de escrita paralela vira erro de merge visível em vez de sobrescrita silenciosa.

**Negativas e limites, declarados**

- **Worktree custa.** Setup por teammate, disco, e os merges deixam de ser gratuitos. Por
  isso é condicional, não default.
- **Não é sandbox de verdade.** Worktree isola o *working tree*, não o processo: um teammate
  ainda pode rodar comando que afete o sistema inteiro. Contra isso, o guardrail de comando
  (ADR-0022) e — fora do alcance de um plugin — container ou VM.
- **Agent Teams e worktree têm atrito.** Os teammates do Claude Code compartilham o
  diretório da sessão; usar worktree exige que cada prompt de teammate declare o próprio
  caminho e que a Laura faça os merges. É orquestração em prosa, com as limitações que isso
  implica.
- **"Execução autônoma" é um julgamento**, não um flag. A skill descreve a regra; quem
  decide se o diff será lido por um humano é quem dispara o ciclo.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Worktree sempre, por default | Cobra o custo de todo mundo para resolver o problema de quem roda sem supervisão. A maioria dos ciclos ainda termina em PR revisado por humano |
| Container por teammate | Fora do alcance de um plugin — exigiria runtime, imagem e orquestração. É decisão do ambiente do usuário, não do plugin (ADR-0001) |
| Enforçar ownership no hook `PreToolUse` | Sem atribuição de teammate no payload, só geraria falso positivo em série — e falso positivo desliga guardrail (ADR-0022) |
| Lista fixa de ações proibidas em vez do critério de reversibilidade | Lista fixa envelhece e sempre tem buraco. "Você consegue escrever o revert?" cobre o caso que ninguém previu |

## Emenda (v0.42.10): construir fora do checkout principal

Na aula 5 do Tech Leads Club, o professor cita um hook que não deixa implementar nada no clone
principal: o agente constrói num worktree, e quem está no checkout principal segue trabalhando.
Esta ADR já pedia worktree quando a supervisão sai do caminho, mas só para o teammate do
`/mobilizar`. O arco do `/entregar`, que também constrói sem ninguém olhar cada escrita entre
os gates, rodava no checkout principal. E a conferência achou o que impedia levá-lo para um
worktree.

**O estado morava no diretório de onde o script rodava.** O `ciclo.py` e o `quadro.py`
gravavam em `.agents/ciclo/` e `.agents/quadro/` relativos ao diretório atual. Daí três
consequências:

- **O ciclo aberto num worktree sumia.** A caixa, o painel, a telemetria e o guardrail do
  `gh pr create`, rodando do checkout principal, não o enxergavam.
- **O `vincular` falhava no modo worktree.** O teammate em worktree que rodava o
  `quadro.py vincular` pedido pelo ADR-0048 recebia "quadro não existe", e os tokens dele
  ficavam sem tarefa. É um defeito que já estava na `main`, justamente no modo worktree.
- **A telemetria rodada num worktree lia uma pasta vazia.** O hook grava a trajetória no
  checkout principal desde o ADR-0048.

Agora o estado mora onde a trajetória já morava:

- **O `ciclo.py` e o `quadro.py` resolvem a pasta no checkout principal.** O
  `execucao.raiz_do_projeto`, que lê o `.git` sem rodar git, faz isso também quando o script
  roda num worktree ligado. A SPEC continua lida do diretório atual: o digest é o do branch em
  construção.
- **Os leitores usam a mesma resolução:**
  - guardrail;
  - painel;
  - telemetria, inclusive a trajetória;
  - `prova.py decisoes`.

  Fora de worktree, nada muda.
- **Os caminhos sagrados valem também pelo checkout principal.** O guardrail conferia
  `.agents/execucoes/**`, `.agents/ciclo/**` e `.agents/quadro/**` só pelo caminho relativo ao
  diretório da sessão. De dentro de um worktree, uma escrita por caminho absoluto na trajetória
  do principal passava, um buraco aberto desde o ADR-0048. Agora o caminho conta também
  relativo ao checkout principal.
- **Classe nova `checkout`, em `aviso`.** Avisa quando há escrita de código de produção num
  checkout principal enquanto um ciclo aberto constrói no branch dele:
  - os estados que contam são `construindo`, `corrigindo_*`, `provando` e
    `atacando_premissa_*` da validação e da revisão;
  - o aviso sai uma vez por sessão;
  - o rastro fica na trajetória sempre;
  - worktree ligado, teste, documentação e ciclo construindo noutro branch não contam;
  - `"checkout_principal": "sempre"` no `guardrails.json` estende a regra a toda escrita de
    produção ali, que é o hook da aula;
  - `{"modos": {"checkout": "bloqueio"}}` a torna dura.
- **O Passo 0 do `/entregar`** recomenda abrir o arco num worktree.

### Limites

- **A recomendação não cria o worktree.** O `/entregar` diz o comando; criar a pasta, instalar
  as dependências nela e removê-la depois do merge continuam com quem roda o arco.
- **Rodar o script de uma subpasta do checkout principal** continua gravando o estado ali,
  como antes. Só o worktree ligado foi resolvido.
- **Escrita pelo shell não passa por esta conferência.** A classe `checkout` e os sagrados olham
  as ferramentas de escrita; um `echo >` no terminal é da classe de comando.
