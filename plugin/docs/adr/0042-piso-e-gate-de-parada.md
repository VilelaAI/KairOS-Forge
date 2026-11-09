# ADR-0042 — Piso de execução, gate de parada e hooks no Cursor

- **Status:** aceito
- **Data:** 2026-09-17
- **Versão:** v0.35.0

## Contexto

Em 12 de setembro de 2026 Felipe Rodrigues apresentou o **harness-toolkit** do Tech Leads
Club: uma camada de hooks para Cursor e Claude Code com oito regras de piso que
configuração nenhuma desliga, três checagens sempre ativas e vinte e quatro rails
opcionais, governada por um `config.json` versionado no repositório. A tese é a mesma do
ADR-0022 ("prompt pede, hook garante") e o toolkit é fruto do mesmo diagnóstico: modelo
melhor erra menos, mas erra, e quando erra só importa o que está entre ele e as quatro
superfícies que não se desfazem sozinhas (shell, arquivos, git, subagentes).

A licença é Elastic 2.0, não OSI. Nada do código pode entrar num plugin MIT. As ideias
podem, e a auditoria do `guardrail.py` contra o piso deles encontrou lacunas concretas:

| Regra do toolkit | O que o `guardrail.py` tinha | A lacuna |
|---|---|---|
| `secret-access` — nega **ler** `.env`, `~/.ssh`, `*.pem`, credencial AWS; libera `grep` pelo nome da variável | `.env` protegido só contra **escrita**; `cat .env \| curl` bloqueado como exfiltração | `cat .env` sozinho passava, e o segredo entrava no transcript e na trajetória |
| `wiring-tamper` — protege o arquivo em que o editor registra os hooks | nada | O agente podia editar `.claude/settings.json` e silenciar guardrail e telemetria de uma vez |
| `unprovable-destruction` — `rm -rf` com alvo em variável ou substituição | nada | Não dá para provar o que `rm -rf "$DIR"` apaga antes de rodar |
| `outside-project-destruction` — destruição fora do repositório e fora de temp | só a raiz e o home | `rm -rf /opt/outro-projeto` passava |
| `machine-control` — `shutdown`, `reboot`, `poweroff` | nada | Barato, e num container é exatamente o que se quer negar |
| Ship gate e Grind — o "terminei" contra evidência de PASS recente, no `stop` | `verificado:`, `prova.py` e corroboração, tudo lido **depois**, pelo `/validar` | Nada rodava no hook `Stop`; a DoD "gate antes de encerrar" era prosa |
| Cursor e Claude Code com uma lógica de decisão | hooks só no Claude Code; a tabela de limitações dizia que o Cursor não tinha telemetria nem guardrail | O Cursor expõe `hooks.json` com os eventos de ciclo de vida; o forge não os usava |

O que o forge já tinha equivalente, e o ADR registra para não ser refeito: os caminhos
sagrados que o agente não escreve (o `policy-surface-write` deles), `curl|sh`, force-push
em branch protegida, PR fora de estado, recusa registrada na trajetória, e a patinação do
ADR-0030 (o "loop de três tentativas" deles). E o que o forge tem e o toolkit não tem, por
serem produtos de camadas diferentes: máquina de estados, orçamento, compensação, contrato
de relatório, grafo. Os dois convivem no mesmo Claude Code sem conflito; este ADR não
duplica rails do toolkit, fecha o piso.

## Decisão

**1. Cinco regras novas no piso do `guardrail.py`.** Piso é o que não tem `modos` nem
`liberados`: roda antes de a configuração importar, e a configuração é um dos arquivos
que o agente não alcança — a mesma garantia por ordem de execução que o toolkit descreve.

- **Leitura de segredo** (classe `segredo`): comando que **mostra** conteúdo (`cat`,
  `head`, `sed`, `base64`, `cp`…) sobre `.env*`, `~/.ssh`, `~/.aws`, `*.pem`, `id_rsa`,
  `.npmrc`, e chamada ao serviço de metadados da nuvem. `grep`, `rg`, `ls`, `stat`,
  `test`, `wc` e `find` não estão na lista de leitores: procurar o nome de uma variável
  não é ler o valor dela. `.env.example` e afins passam. A tool `Read` ganha o mesmo
  critério pelo hook novo `leitura`.
- **Fiação dos hooks** (sagrado): `.cursor/hooks.json` e `.codex/hooks.json` inteiros;
  em `.claude/settings*.json` só a escrita que **altera o bloco `hooks`** — o agente
  edita esse arquivo por motivos legítimos (permissões, variáveis) e continua podendo.
- **Destruição não provável**: `rm -rf` cujo alvo vem de variável ou substituição.
- **Destruição fora do projeto**: `rm` recursivo em caminho absoluto, `~` ou `..` que
  resolve fora do repositório e fora de temp.
- **Controle da máquina**: `shutdown`, `reboot`, `halt`, `poweroff`, no início de um
  segmento de comando (não dentro de um nome de arquivo).

O critério de desenho é o deles: **negar a cauda destrutiva sem negar o caminho legítimo
parecido**. Regra que bloqueia `grep DATABASE_URL .env` é regra que o time desinstala.

**2. Gate de parada** (classe `parada`, hook `Stop`). A sessão que escreveu código de
produção e não rodou nenhum gate verde **depois da última escrita** não encerra em
silêncio: o hook lista os arquivos sem prova, os gates de `contextos/testes.md` e os
últimos gates vermelhos, lidos da trajetória que o `execucao.py` já grava. É o ship gate
do toolkit com a evidência da fábrica. Recorte deliberado: só a sessão atual, só
produção (teste e doc não contam), só o que veio depois do último gate verde — regra que
dispara em sessão de leitura vira ruído. Nasce em `aviso` (ADR-0030); em `bloqueio` o
modelo recebe a lista e continua. Nunca dispara duas vezes na mesma parada
(`stop_hook_active` no Claude Code, `loop_count` no Cursor), porque gate vermelho
viraria laço infinito.

**3. Hooks no Cursor, gerados pelo sync.** O `sync-multi-cli.py` passa a escrever
`.cursor/hooks.json` ligando `sessionStart`, `beforeSubmitPrompt`, `beforeShellExecution`,
`beforeReadFile`, `afterShellExecution`, `afterFileEdit`, `subagentStart` e `stop` aos
mesmos `execucao.py` e `guardrail.py` já espelhados em `.cursor/scripts/`. O payload do
Cursor é reconhecido **pela forma** (`conversation_id` sem `tool_input`), nunca por
configuração, e a resposta sai no dialeto dele (`permission`, `additional_context`,
`followup_message`) em vez de exit 2. O arquivo gerado é sagrado (fiação) e gerado
(ADR-0037) ao mesmo tempo. Duas linhas da tabela de limitações por CLI mudam de ❌ para ✅:
telemetria de execução e guardrails no Cursor. O que **não** muda: o Cursor não expõe
hook antes de uma edição de arquivo, então as classes de escrita (sagrados, gerado,
teste existente) ali dependem do modo CLI `guardrail.py verificar` no CI do projeto.

**4. Suíte de testes do guardrail** em `scripts/tests/test_guardrail.py`, no CI: dezesseis
casos cobrindo cada regra do piso (o que nega e o que libera), a fiação condicional do
Claude Code, o gate de parada nos dois modos e o adaptador do Cursor.

## Consequências

| O que | Antes | Depois |
|---|---|---|
| `cat .env` | passava | negado; `grep` passa |
| Editar `hooks` em `.claude/settings.json` | passava | negado; permissões continuam livres |
| `rm -rf "$DIR"`, `rm -rf /outro`, `reboot` | passavam | negados |
| Encerrar sessão com produção sem gate | silêncio | aviso com a lista; `bloqueio` devolve o trabalho |
| Cursor | sem telemetria, sem guardrail | `hooks.json` gerado; trajetória e piso iguais aos do Claude Code |
| Classes do guardrail | 6 | 8, mais 3 regras de comando no piso |

**Positivas**

- O piso do forge passa a cobrir as quatro superfícies do diagrama do toolkit.
- A DoD deixa de depender de o modelo lembrar: quem cobra o gate é o hook.
- A dimensão Autonomia do `/auditar` passa a ser medida no Cursor.

**Negativas e limites, declarados**

- **Os hooks do Cursor seguem a documentação de setembro de 2026 e foram testados com
  payloads sintéticos**, não num Cursor real nesta sessão. Campos de `afterShellExecution`
  (saída, código de saída) são lidos de forma tolerante; se o nome for outro, a trajetória
  registra o comando com `ok: null`, nunca um resultado inventado.
- **Leitura de segredo é regex sobre o comando.** `python3 -c "print(open('.env').read())"`
  é pego pelo leitor `python3` mais o alvo; um leitor fora da lista não é. A lista cresce
  por evidência, não por antecipação.
- **Fiação condicional no Claude Code é heurística no `Edit`**: bloqueia quando a string
  trocada toca `hooks`, `guardrail`, `execucao.py` ou `kairos-forge`. Uma edição que
  reescreve o arquivo inteiro por `Write` é comparada por estrutura, que é o caminho
  exato.
- **O gate de parada só vê o que a trajetória viu.** Gate rodado fora do hook (CI,
  outra máquina) não conta; a saída é o autor declarar, que é o mesmo contrato do
  `verificado:`. E `ok: null` (saída indeterminada) não conta como verde — o gate que
  "rodou mas não se sabe" é exatamente o que a regra existe para expor.
- **`aviso` depende de alguém olhar.** Como no ADR-0039: taxa baixa e estável de
  recusas em `parada` é o sinal para promover a `bloqueio`.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Instalar o harness-toolkit e não mexer no `guardrail.py` | Licença Elastic 2.0 impede levar o piso deles para dentro do plugin; e um usuário do forge sem o toolkit ficaria sem piso. Os dois convivem, mas o forge precisa do próprio |
| Bloquear `source .env` e `. .env` também | Carregar variáveis para rodar o processo não mostra o valor; negar isso é negar o caminho legítimo, e a regra seria desligada |
| Proteger `.claude/settings.json` inteiro, como o toolkit | O agente edita permissões e variáveis ali com frequência (há skill oficial para isso); a fiação é só o bloco `hooks` |
| Gate de parada rodando lint e teste sozinho (o Grind deles) | Exige saber o comando do projeto e rodá-lo no hook, com tempo e efeito colateral; a fábrica já grava o que rodou, então cobrar a evidência é mais barato e não inventa gate |
| Gate de parada em `bloqueio` por default | Sessão de refactor sem gate declarado viraria laço de reclamação; `aviso` primeiro, promoção por taxa (ADR-0030) |
| Comment gate, duplication gate, supply-chain gate | São rails, não piso, e a Patrícia no `/revisar` e o `grafo.py codigo` (ADR-0041) cobrem parte disso por leitura; entram por ADR próprio se a trajetória pedir |
| Varredura proibindo os nomes `cursor`/`claude` nos scripts, como o `check-boundaries` deles | Os scripts do forge são o adaptador e o core ao mesmo tempo, e conhecem os caminhos dos mirrors por desenho (ADR-0037); a regra não se aplica sem separar camadas, que é outro ADR |

## Emenda (v0.43.1): a fiação é mais que o bloco `hooks`

A regra protegia, em `.claude/settings*.json`, só a escrita que mudava o bloco `hooks`. O
estudo dos mods do Claude Code mostrou que outras chaves do mesmo arquivo decidem o que roda
fora das ferramentas, e por isso fora deste guardrail. Um teste com o Claude Code 2.1.318,
isolado e com a API apontada para uma porta morta (nenhuma chamada saiu da máquina), provou
as duas pontas:

- **O guardrail deixava passar.** Rodado contra cada escrita, ele bloqueou os três controles
  (acrescentar um hook, remover um hook, Edit que toca `hooks`) e deixou passar
  `disableAllHooks` por Write e por Edit (o H maiúsculo escapava da busca), desligar o
  plugin da fábrica em `enabledPlugins`, ligar um marketplace local com um plugin de mod e
  `disableAllHooks` no `settings.local.json`.
- **O Claude Code obedece.** Com a fábrica carregada, os hooks de início gravaram a
  trajetória; com `"disableAllHooks": true` no `.claude/settings.json` do projeto, o plugin
  continuou listado, mas nenhum hook disparou: sem trajetória e sem guardrail, sem aviso. E
  numa pasta confiável, `extraKnownMarketplaces` com uma fonte `directory` dentro do próprio
  repositório mais `enabledPlugins` carregaram uma sonda (um mod que só grava um
  marcador) e rodaram o código dela, sem instalação nem pergunta. Numa pasta sem confiança,
  nada carregou.

O próprio Claude Code trata `.claude/` como caminho protegido: pergunta nos modos `default`
e `acceptEdits`, manda ao classificador no `auto`, recusa no `dontAsk`. Libera no
`bypassPermissions`, o modo de rodar sem supervisão, que é onde este piso é o único.

A fiação passa a ser um conjunto de chaves (`CHAVES_FIACAO`): `hooks`, `disableAllHooks`,
`enabledPlugins`, `extraKnownMarketplaces` e o apelido `additionalMarketplaces`,
`statusLine`, `subagentStatusLine`, `fileSuggestion` e `syncClaudeAiPlugins`. Os três
últimos de status são comandos que o Claude Code roda sozinho; um mod é código que roda no
processo dele e pode responder no lugar de um hook.

- **Write e Edit comparados pelo arquivo que resultaria**, chave a chave. Ausente, vazio e
  `false` contam igual. Edit que não se aplica ou deixa o JSON ilegível cai na busca pelo
  trecho, agora sem diferenciar maiúscula.
- **Qualquer `.claude/settings*.json`**: do projeto, local e do usuário. O
  `~/.claude/settings.json` desliga os hooks de plugin do mesmo jeito.
- **Pelo shell, a mesma fiação** entra no piso: redirecionamento, `tee`, `sed -i`/`perl -i`,
  `cp`/`mv`/`ln` com o arquivo como destino, `rm`, `truncate`, `dd` e interpretador que
  cita o arquivo. Ler e copiar para fora passam.

A alternativa recusada no texto original continua recusada: o arquivo inteiro não vira
sagrado, e permissões e variáveis seguem livres. O que muda é o que conta como fiação.

### Limites

- **Mod de terceiro instalado pela pessoa** fica no mesmo nível da fábrica e pode responder
  no lugar dos hooks dela (`classic.PreToolUse`) ou aprovar uma chamada (`tool.check`). Só a
  configuração gerenciada protege: a fábrica em `prependPlugins` e `allowManagedModsOnly`
  ligado (`docs/adocao.md`).
- **O shell não confere os caminhos sagrados.** Um `echo > .agents/execucoes/x.jsonl` passa
  pelo modo `comando`; o piso do shell cobre a fiação, não o medidor. Fica registrado como
  lacuna própria.
- **Não medi se `disableAllHooks` vale na mesma sessão** em que é escrito ou só na seguinte:
  isso pede turnos de modelo. A regra bloqueia antes, nos dois casos.
- **A busca do shell é heurística**: `python3 x.py; cat .claude/settings.json` bloqueia por
  engano, e uma escrita por um caminho montado em variável escapa.

## Emenda (v0.50.7): o aviso é para a pessoa

Uma pessoa mandou a tela de uma sessão em que o gate de parada tinha disparado:

> Stop hook error: Failed with non-blocking status code: ⚠️ kairos-forge (guardrail, modo
> aviso): parada sem prova — 10 arquivo(s) de produção escrito(s) sem nenhum gate verde depois

Ela perguntou como resolver "o erro". Não havia erro: o gate funcionou. Mas a tela mostrou
quatro defeitos nossos.

1. **O rótulo de erro.** No modo `aviso`, o guardrail saía com exit 1 e o texto no stderr. O
   Claude Code mostra qualquer exit 1 como "<evento> hook error: Failed with non-blocking
   status code", no `Stop` e também no `PreToolUse:Write`. A regra em observação parecia um
   hook quebrado.
2. **O texto falava com quem não o lia.** "Depois, encerre de novo" e "diga ao usuário por
   quê" são instruções para o modelo. Só que o modelo não lê o aviso; só a pessoa lê.
3. **Não havia onde declarar a pasta sem teste.** O texto original diz que a ausência
   declarada é aceitável. Mas a única forma de declarar era repetir o motivo em cada
   sessão, e uma pasta de experimentos disparava o aviso em toda parada.
4. **A linha do gate vermelho cortava o comando em 80 caracteres.** O que ficava era o
   `bash -c 'cd /Users/…`, e o que sumia era justamente o teste que tinha rodado.

A lista da tela também trazia arquivos do scratchpad (`/private/tmp/claude-501/…`). Isso já
estava corrigido desde a v0.41.2, porque escrita fora do projeto deixou de contar como
produção. A sessão da tela rodava uma versão anterior.

### Decisão

- **O aviso sai como `systemMessage`, com exit 0**, em toda classe que está em `aviso`:
  `teste`, `parada`, `regua`, `checkout`, `intencao` e qualquer classe que o projeto
  rebaixe. O Claude Code mostra "Stop says: …" e "PreToolUse:Write says: …", sem rótulo de
  erro.
  - O bloqueio continua em exit 2 com o stderr, que vai ao modelo.
  - O Cursor continua no dialeto dele.
  - Dentro do script, `AVISOU` (1) continua separando "avisou" de "nada a dizer". O `main`
    traduz para exit 0 na fronteira do processo.
  - A linha sai em ASCII: o "⚠️" e os acentos viram escapes do JSON. Assim um stdout em
    cp1252, no Windows, não derruba o aviso, e a tela fica igual (conferido no Claude Code
    real).
- **A falha do próprio guardrail vai pelo mesmo canal.** Ela já saía com exit 0 (ADR-0046),
  mas com o texto no stderr, e com exit 0 o Claude Code não mostra o stderr. Ninguém via a
  falha, e o ADR-0046 prometia que a pessoa veria. Ficam no stderr dois casos: o Cursor e
  os modos `faixa3` e `saida`, cujo stdout o mod lê como resposta.
- **O texto da parada é escrito para quem o lê.**
  - Em `aviso`, o texto fala com a pessoa. Diz o que aconteceu e o que ela pode pedir: o
    gate de `contextos/testes.md` (até dois) ou, sem ele, "o teste ou o lint do projeto".
    Avisa que o teste rodado em background não conta, porque o hook só vê o comando
    começar. E mostra como declarar a pasta sem teste.
  - Em `bloqueio`, o texto continua falando com o modelo, como antes. Ganha só a nota sobre
    o primeiro plano.
- **`sem_gate` em `.agents/guardrails.json`** declara as pastas sem teste:
  - É uma lista de globs, por exemplo `["experiments/**"]`.
  - A escrita que casa com ela sai da conta da parada, em `aviso` e em `bloqueio`, e o resto
    continua contando.
  - Fica num arquivo que o agente não escreve, porque `.agents/guardrails.json` é sagrado:
    quem declara a ausência é a pessoa.
  - Não é um modo `desligado`: a classe segue valendo para todas as outras pastas.
  - Valor mal formado é ignorado, sem derrubar o hook.
- **A linha do gate vermelho** traz o nome do gate e o comando com o começo e o fim, em 90
  caracteres.

### Prova

- **Claude Code 2.1.319 com hooks mínimos e uma API falsa**, numa sessão interativa no tmux:
  - Exit 1 com stderr reproduz a tela da pessoa: "Stop hook error: Failed with non-blocking
    status code" e "PreToolUse:Write hook error".
  - `systemMessage` com exit 0 aparece como "Stop says:" e "PreToolUse:Write says:", com as
    várias linhas preservadas.
  - Nas duas formas, nenhum pedido à API traz o texto: o modelo nunca leu o aviso.
  - No 2.0.77, "Stop says:" também.
  - Em `-p`, a saída de texto e a de `--output-format json` são as mesmas nas duas formas.
    Ou seja, o que os gatilhos de CI publicam não muda.
- **O plugin de verdade, com `--plugin-dir`**, numa sessão que escreve `src/app.py` e encerra:
  - Na `main` (v0.50.6) aparece "Stop hook error", seguido do texto para o modelo.
  - Nesta versão aparece "Stop says: ⚠️ kairos-forge (guardrail, modo aviso): o agente
    encerrou sem gate verde…", seguido do texto para a pessoa.
- **`scripts/tests/test_aviso.py`**, com 18 testes. Contra a `main`, 15 falham. Os três que
  passam guardam o que não muda: o bloqueio pelo stderr, o "sem nada a dizer, nada sai" e o
  Cursor no dialeto dele. Os testes cobrem:
  - o canal na fronteira do processo, na parada, na classe `teste` e na falha do guardrail;
  - os modos do mod, que continuam no stderr;
  - o Cursor, que continua no dialeto dele;
  - o texto para a pessoa e para o modelo;
  - o gate de `contextos/testes.md`;
  - a linha do gate, que só traz o gate que falhou, com o começo e o fim do comando;
  - a lista, que cabe inteira com oito arquivos e, com mais, diz quantos faltam;
  - o `sem_gate` com uma pasta declarada, com tudo declarado, em bloqueio e mal formado.
- **Testes alterados.** São os helpers que leem o texto do aviso: `hook()` (`test_guardrail`),
  `escrever` (`test_checkout`) e `parada` (`test_execucao`). Eles passam a ler o
  `systemMessage` e a recusar aviso que ainda saia pelo stderr. Também mudam as três
  asserções da falha do guardrail (`test_guardrail` e `test_trajetoria_sem_segredo`). O que
  cada teste cobra não mudou; mudou o canal.

### Limites

- **O modelo continua sem ler o aviso**, como antes. Classe que deve mudar o que o agente
  faz vai para `bloqueio`.
- **O teste rodado em background continua não contando.** O `PostToolUse` chega quando o
  comando começa, e o fim dele não passa por hook nenhum. O texto agora diz isso.
  (Resolvido na emenda v0.50.8, abaixo: o fim é lido do transcript.)
- **No Cursor, a parada em `aviso` segue sem nada na tela.** O evento `stop` de lá só tem
  `followup_message`, que reabre o agente.
- **Codex e OpenCode**, sem hook de parada, não mudam.

## Emenda (v0.50.8): o gate rodado em background

O limite que a emenda anterior deixou declarado é justamente o caso da tela que a
motivou: a avaliação rodava em background quando o agente encerrou. Até aqui, o gate de
parada não tinha como ver um gate rodado em background:

- **Ele avisava com o teste ainda rodando.** Para o hook, a sessão tinha encerrado; para o
  Claude Code, ela só estava parada, esperando o trabalho em background acordá-la.
- **E avisava de novo depois que o teste passava.** O `PostToolUse` chega quando o comando
  começa, sem saída nem código, e o fim dele não passa por hook nenhum. O gate ficava
  indeterminado para sempre.

### O que o Claude Code entrega

Conferido no Claude Code 2.1.319 com a API falsa, numa sessão interativa no tmux, em que o
agente escreve um arquivo, roda um `pytest` em background e encerra:

- **O `PostToolUse` do comando em background** traz `tool_response.backgroundTaskId`, o id
  da tarefa.
- **O `Stop` traz `background_tasks`**: a lista do que ainda roda, com o id, o tipo
  (`shell`, `subagent`…), o status e o comando. A lista vem vazia quando nada roda.
- **O fim fica no transcript** como `<task-notification>`, com o id da tarefa, `<status>`
  (`completed`, `failed`) e o resumo com "exit code N". O formato muda conforme o momento:
  - com a sessão parada, uma entrada `user` com `origin.kind: "task-notification"`;
  - no meio de um turno, um anexo `queued_command` com a mesma origem.
- **Uma notificação forjada fica de fora.** O mesmo texto impresso por um comando volta
  como `tool_result`, sem essa origem. Também ficam de fora as entradas `queue-operation`,
  porque nelas cai também o que a pessoa digita.

### Decisão

- **O `execucao.py` grava o id da tarefa** (`tarefa`) no evento do comando que vai para
  background. O `ok` continua `None`.
- **O `guardrail.py` lê, no `Stop`, o fim de cada tarefa no transcript**
  (`execucao.conclusoes_em_background`):
  - Só vale "exit code 0" como verde. `failed`, ou um código diferente de zero, é vermelho.
  - Parado sem código (`killed`) não se afirma.
  - O resultado vale na posição em que o gate começou. O que ele verificou foi o código
    daquele momento, então uma escrita feita depois do início continua pendente.
- **A parada espera enquanto um gate que cobre as escritas ainda roda.** É gate (pelo mesmo
  classificador da trajetória), está em `background_tasks` e começou depois da última
  escrita pendente: a sessão está em pausa, não encerrando. Não há aviso nem recusa
  registrada. Já um gate que começou antes de alguma escrita (um teste em modo watch, por
  exemplo) não a cobre e não segura nada. O mesmo vale para o que roda e não é gate, como
  um servidor de desenvolvimento.
- **O fim pode chegar ao transcript depois do hook.** Numa de três sessões reais com o
  plugin, a linha ainda não estava lá quando o `Stop` rodou. Por isso, se o gate começou em
  background, não roda mais e o fim ainda não foi lido, o guardrail relê o transcript a cada
  0,25 s por até 1,5 s. Só espera quando a versão relata o `background_tasks` e há
  transcript para reler.
- **O texto muda.** "Em background também vale: conta quando terminar" substitui o "não
  conta", e o texto para o modelo perde a nota sobre o primeiro plano.
- **O `sleep` da releitura** é o único candidato do `prova.py atalhos`. Não é sincronia às
  cegas: cada passo confere a condição, e a espera tem teto. Também não há evento a esperar,
  porque quem grava o transcript é outro processo. A justificativa fica no comentário, ao
  lado do código.

### Prova

- **O plugin de verdade, com `--plugin-dir`**, numa sessão que escreve `src/app.py`, roda
  um `pytest` em background que termina depois de o agente encerrar:
  - Na `main` (v0.50.7) aparecem dois avisos, um com o teste ainda rodando e outro depois de
    ele passar com exit 0.
  - Nesta versão, com o teste passando, não aparece aviso nenhum.
  - Nesta versão, com o teste falhando, o aviso só aparece depois do fim, e traz "Últimos
    gates, todos vermelhos: teste: `pytest -q`".
  - Sem a releitura do transcript, uma das três sessões verdes ainda avisava. Com ela,
    repeti três sessões verdes e uma vermelha. As verdes ficaram sem aviso, e a vermelha
    avisou uma vez, com a linha do gate. Não dá para dizer em quantas a releitura chegou a
    ser acionada.
- **`scripts/tests/test_gate_em_background.py`**, com 20 testes. Os formatos das linhas são
  os do transcript real. Os testes cobrem:
  - os dois formatos, o resultado pelo código de saída e a notificação forjada, a da fila
    e a sem origem, que não contam, e o arquivo ilegível, que não derruba o hook;
  - o id gravado no início;
  - o verde e o vermelho em background;
  - a espera enquanto o gate roda e cobre as escritas, e o gate em modo watch e o servidor,
    que não seguram;
  - o verde que não cobre a escrita feita depois do início;
  - o caminho inteiro pelos dois hooks, em processo;
  - o término que chega depois do hook, o teto da espera e a espera que não acontece sem
    motivo.

### Limites

- **A telemetria não muda.** O `/auditar` e o `corroborar` continuam vendo o gate em
  background como indeterminado. Só o gate de parada lê o fim.
- **Só no Claude Code**, e conferido no 2.1.319. Versão que não relata `background_tasks`
  nem grava a origem fica como antes: sem espera, com o gate indeterminado.
- **Gate que roda num subagente** não entra. O fim dele é o do subagente, não o do comando.
