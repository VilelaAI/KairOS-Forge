# ADR-0056 — Segredo na saída de ferramenta

- **Status:** aceito
- **Data:** 2026-11-05
- **Versão:** v0.49.0

## Contexto

O piso do ADR-0042 nega a leitura de segredo: `cat .env` pelo shell e a `Read` de
`.env`, `~/.ssh`, `.aws/credentials`, `*.pem`. Mas o segredo também chega pela saída de
um comando que ninguém classificaria como leitura de segredo:
- o `env` ou o `printenv`;
- o `docker inspect` e o `kubectl get secret -o yaml`;
- o teste vermelho que imprime a `DATABASE_URL` com a senha;
- o `git log -p` que mostra uma chave antiga;
- o `npm config list` com o token do registro;
- a ferramenta de MCP que devolve uma credencial.

O que entra no contexto vai à API do modelo na resposta seguinte e fica no transcript em
disco. Dali pode ir parar num commit, num corpo de PR ou numa mensagem. O ADR-0042 cobria
a porta da frente, e a saída era a dos fundos.

## Decisão

O segredo que aparece na saída do Bash ou de uma ferramenta de MCP é trocado por uma marca
antes de o modelo ler o resultado: `«segredo ocultado pelo kairos-forge: token GitHub»`.
Só o valor sai. O resto da linha e da saída fica como veio.

### A regra mora no Python: `guardrail.py saida`

É um modo novo do guardrail, como o `faixa3` (ADR-0052). Recebe os textos que a
ferramenta devolveu e responde com eles já ocultos, com o aviso para o modelo. Sai sempre
com exit 0.

- **O que é segredo.** Só formatos de alta precisão:
  - token com prefixo próprio: GitHub (`ghp_`, `github_pat_`), GitLab, Slack, Stripe,
    OpenAI e Anthropic (`sk-`), Google (`AIza`), chave de acesso AWS (`AKIA`, `ASIA`);
  - bloco de chave privada, inteiro, mesmo sem a linha do fim;
  - JWT;
  - senha dentro de URL de conexão (`postgres://app:<senha>@host`);
  - o valor de variável cujo nome diz segredo (`*_PASSWORD`, `*_SECRET`, `*_TOKEN`,
    `*_API_KEY`) ou de chave `password`, `secret`, `token`, `client_secret`. Esse valor
    tem de ter 8 ou mais caracteres e ser um valor de verdade, não uma referência.
- **O que passa.**
  - `api_key = os.environ["API_KEY"]`, `token = get_token()`, `tokenizer = …`,
    `max_tokens=4096`;
  - `${{ secrets.X }}`, `<seu-token>`, `{{ vault }}`;
  - hash de commit, UUID, `sha256:…`;
  - senha de 7 caracteres ou menos.

  O critério é o mesmo da pausa, com o custo invertido. O falso positivo esconde um valor
  da saída. O falso negativo manda o segredo para fora.
- **O modo.** É a classe `saida` em `"modos"` do `.agents/guardrails.json`. Em `bloqueio`,
  o padrão, o valor é ocultado. Em `aviso`, o texto fica como está e o modelo recebe o
  aviso de não copiar o valor.
- **A trajetória.** Cada achado vira um evento `segredo_na_saida` com o tipo, a contagem
  e o comando. O comando também passa pela ocultação, e o valor nunca é gravado. O
  `telemetria.py resumo` conta as saídas com segredo por tipo.

### Quem troca o resultado é um mod: `hooks/segredo.ts`

O gancho fica no `tool.call` do Bash e das ferramentas de MCP. Ele deixa a chamada rodar
inteira, uma vez, e só depois manda o texto que voltou ao `guardrail.py saida`.

Tem de ser um mod porque o resultado que um gancho em `tool.call` devolve é o que o modelo
lê e o que o transcript grava, no lugar do original. Um hook de settings no `PostToolUse`
só acrescenta texto depois, com o segredo já lido. Ele só reescreve a saída de MCP, e não a
do Bash.

- **O Bash que respondeu** volta como um objeto novo, com o `stdout` e o `stderr`
  trocados. Esse objeto vai sem o `ref` e sem o `text` do original: com eles, o Claude Code
  reaproveitaria as mensagens que já tinha montado, e o segredo iria junto.
- **A saída grande.** O Claude Code guarda a saída inteira num arquivo e põe no `stdout`
  só o começo. O mod lê esse arquivo (até 4 MiB), examina a saída inteira e devolve a
  versão oculta sem o caminho do arquivo original. O Claude Code guarda de novo a versão
  oculta, e é o caminho dela que o modelo recebe.
- **O erro e a ferramenta de MCP** não têm uma forma de resultado que dê para reescrever.
  Voltam como resultado retido, e o modelo lê `<ferramenta> ran, and a plugin withheld its
  result:` seguido do texto já oculto.
- **O aviso.** Junto do resultado vai um aviso:
  - quantos segredos havia e de que tipo;
  - não tentar recuperar o valor;
  - se precisar dele, pedir à pessoa;
  - avisar que ele apareceu no terminal e pode ter de ser trocado.
- **O que não passa pelo exame.** A saída vazia nem chega ao Python. A chamada recusada
  embaixo não roda, e não há o que ler.
- **Se o exame falha.** Se o Python não roda, ou o arquivo da saída sumiu, a saída passa
  como veio. Sem Python não há guardrail nenhum da fábrica.

O teste de encaixe (`test_mod_painel.py`) passa a exigir, no código, que o segredo não
decida se a chamada roda:
- nada de `tool.check`;
- um só `next`, chamado antes do exame;
- o único `deny` é o do resultado retido, com o texto já oculto;
- o único script que ele roda é o `guardrail.py saida`.

## Prova

Rodei um Claude Code 2.1.318 de verdade, com `--plugin-dir` e a API falsa local do
ADR-0052, que pede um Bash e guarda o pedido seguinte, com o `tool_result`:

| Cenário | Sem o plugin | Com o plugin |
|---|---|---|
| `cat config.txt` com um token do GitHub dentro | o token chega à API e ao transcript | chega a marca; o token não está nem no pedido nem no transcript |
| Comando que falha com `DB_PASSWORD=…` no stderr | a senha chega como erro | o erro chega com a marca, como resultado retido |
| Saída de 67 KB com o token na última linha | — | a prévia e o caminho de um arquivo novo, com a marca; o token não chega à API |
| Saída sem segredo | — | igual à original |

O aviso chegou ao modelo junto do resultado. Cada achado saiu na trajetória com o tipo e o
comando, sem o valor.

## Consequências

- **Testes.**
  - `test_segredo.py` tem 14 testes:
    - 19 textos com segredo, cada um com o valor fora e a marca do tipo;
    - 19 que passam;
    - só o valor sai;
    - a chave privada inteira, também sem a linha do fim;
    - vários segredos na mesma saída;
    - o modo `aviso`;
    - a trajetória sem o valor em nenhum arquivo de `.agents/`;
    - a subpasta;
    - a falha aberta;
    - a linha do `resumo`.

    Contra a `main`, nenhum dos 14 passa.
  - `tests/segredo.test.ts` tem 15 testes no kit:
    - o Bash reescrito sem `ref` nem `text`;
    - a saída grande lida do arquivo;
    - o erro e o MCP retidos;
    - a saída vazia que não chega ao guardrail;
    - o arquivo que sumiu;
    - a saída sem segredo, que volta como veio;
    - o modo `aviso`;
    - sem Python e com a resposta ilegível, a chamada roda uma vez;
    - a resposta do guardrail mal formada (sem achado, aviso que não é texto, textos que
      não são objeto, nada), que deixa a saída como veio em vez de trocá-la por algo
      vazio;
    - a recusa de baixo e a `Read`, que nem chegam.
- **Mutação.** Com as suítes Python e o kit como comando, a primeira rodada deixou 5 de 35
  mutantes vivos:
  - quatro na validação da resposta do guardrail, que nenhum teste mandava mal formada, e
    que viraram os quatro casos acima;
  - um equivalente no `textosDe` (o texto vazio já é barrado depois), que saiu do código.

  Cada um dos quatro casos derruba o seu mutante, plantado à mão. A rodada final mata 33
  de 33.
- **CRAP.** O kit não gera relatório de cobertura do TypeScript. As funções do mod ficam
  com complexidade de 8 ou menos, abaixo do limite mesmo sem cobertura, e quem prova o
  comportamento é a mutação com o kit.
- **Custo.** Um processo Python por chamada de Bash ou de MCP que devolve texto, como o da
  pausa no `tool.check`.

## Limites declarados

- **Só no Claude Code.** No Cursor, o `afterShellExecution` não muda a saída do shell. O
  `postToolUse` dele tem `updated_mcp_tool_output`, mas só para MCP, e fica para um
  próximo passo. Codex, OpenCode e Tucano não têm onde trocar a saída.
- **A `Read` fica de fora.** Ocultar ali faria um `Write` posterior, montado a partir do que
  o modelo leu, gravar a marca por cima do segredo real. A `Read` de arquivo de segredo já
  é negada (ADR-0042). O segredo embutido num arquivo de código continua visível pela
  `Read`.
- **Formato que a lista não conhece passa.** O caso típico é o valor em base64 de um
  `kubectl get secret -o yaml` sob uma chave de nome livre. A senha curta também passa.
  Pegar isso pede entropia, e a entropia esconderia hash e id em toda saída.
- **O arquivo original da saída grande fica no disco**, na pasta do transcript. O caminho
  dele não chega ao modelo.
- **O segredo que o próprio modelo escreveu no comando** ele já tinha. O comando vai à API
  como foi escrito.
- **A trajetória do `execucao.py`** tinha regra própria, mais fraca. Corrigido na emenda de
  v0.50.4, abaixo.

## Alternativas consideradas

- **`PostToolUse` no hook de settings.** Recusado como caminho principal. Ele só
  acrescenta texto depois que o modelo já leu a saída, e não reescreve a saída do Bash.
- **Reter a saída inteira quando há segredo.** Recusado. O resto da saída é o que o agente
  precisa para seguir: o teste que falhou, a linha do log.
- **Detectar por entropia.** Recusado pelo falso positivo em hash, id e chave de cache.
- **A regra em TypeScript, dentro do mod.** Recusado pelo mesmo motivo do ADR-0052: uma
  segunda regra fora dos testes em Python e longe do guardrail.
- **Ocultar também na `Read`.** Recusado pelo `Write` por cima.

## Emenda (v0.50.4): a trajetória sem segredo

O último limite acima dizia que a trajetória do `execucao.py` gravava o comando dos gates
como veio. Isso não era exato, e o que acontecia era pior do que parecia. Havia uma regra
própria, o `redigir`, com três padrões, e ela errava nos dois sentidos.

Das 19 amostras de segredo do `test_segredo.py`, deixava passar 15, entre elas:
- `DB_PASSWORD=…`, porque procurava `password` como palavra solta, e o sublinhado a gruda
  no nome;
- `postgres://app:<senha>@host`;
- as chaves da AWS, da Stripe, do Google e da OpenAI;
- `{"password": "…"}`.

E apagava o que não era segredo:
- toda palavra de 40 caracteres ou mais, como o hash de um commit e o nome longo de um teste;
- o `auth` de `gh auth status`;
- o diretório de `mkdir -p`.

O nome longo apagado fazia o `telemetria.py corroborar` não achar o gate que tinha rodado.

O `guardrail.py` também gravava texto sem passar por regra nenhuma:
- o comando da recusa;
- o comando da pausa da faixa 3, justamente onde costuma ter credencial
  (`PGPASSWORD=… psql prod -f migration.sql`);
- a mensagem de erro do `guardrail_erro`.

A trajetória fica em disco. O `.gitignore` sugerido a deixa fora do git, mas nada garante
que o projeto a ignore.

### Decisão

- **Uma regra só, em `scripts/segredos.py`.** Os padrões e a marca saem do `guardrail.py`
  para um módulo pequeno, sem I/O. Quem usa:
  - o `guardrail.py`, na saída de ferramenta, no `ocultar` e em toda gravação;
  - o `execucao.py`, no comando de cada gate;
  - o `telemetria.py corroborar`, no comando alegado.

  O sync leva o módulo para o Cursor e para o Tucano, junto dos scripts que o importam.
- **Três padrões a mais, que valem também para a saída de ferramenta:**
  - o token depois de `Bearer`, com 16 caracteres ou mais e ao menos um dígito
    ("Bearer authentication" é texto);
  - o valor de `--password`, `--token`, `--secret`, `--api-key` e parecidas, separado por
    espaço (o `=` já era coberto);
  - a senha em `-u usuario:senha`.

  Continuam passando `--password-stdin`, `--token-file`, `git push -u origin main`,
  `docker run -u 1000:1000` e as referências (`$DB_PASS`, `${TOKEN}`).
- **No `execucao.py`:**
  - o comando é gravado já sem o segredo;
  - o gate é classificado pelo comando cru, porque a marca não pode apagar o sinal de que um
    teste rodou;
  - sem o `segredos.py`, numa cópia antiga sem o módulo, o comando vira
    `«comando não gravado…»` em vez de ir cru. O gate continua classificado, e a telemetria
    não quebra.
- **No `guardrail.py`:** o `registrar_evento` passa todo texto do evento pela regra antes de
  gravar. Isso cobre a recusa, a pausa, o segredo na saída e o erro. A mensagem de erro
  também sai sem o segredo no aviso do stderr.
- **No `corroborar`:** o alegado passa pela mesma regra que o gravado, e por isso os dois
  batem. O alegado também volta oculto na resposta.

**Para limpar a trajetória gravada antes disto**, uma pessoa roda, da raiz do projeto:

```bash
python3 <plugin>/scripts/guardrail.py ocultar .agents/execucoes/*.jsonl
```

O comando troca só o valor, e cada linha continua sendo JSON válido. É a pessoa quem roda,
porque o agente não escreve na própria trajetória (ADR-0022).

### Prova

O `test_trajetoria_sem_segredo.py` tem 14 testes:
- os três padrões novos, e o que parece segredo mas passa;
- cada um dos 19 formatos de segredo fora do comando gravado, e os 19 textos sem segredo
  gravados como vieram;
- o hash, o nome longo de teste, `gh auth status` e `mkdir -p` intactos;
- o gate classificado pelo comando cru, e "não gravado" sem o módulo;
- o hook de verdade gravando três comandos sem nenhum dos segredos no disco;
- o evento do guardrail com todo texto oculto e o resto intacto;
- a recusa de comando pelo hook;
- o erro sem o segredo no disco e no aviso;
- o `corroborar` achando o nome longo e o alegado com segredo, e os seus três veredictos;
- todo módulo local que um script de suporte importa, presente na lista do sync.

As suítes do ADR-0056 continuam passando com a regra no módulo novo, inclusive as 19
amostras que passam intactas.

- **Prova negativa.** Contra a `main` anterior, o arquivo de teste nem carrega, porque o
  `segredos.py` não existe. Com o módulo copiado para a base, 11 dos 13 testes da época
  falham. Os 2 que passam testam o próprio módulo copiado.
- **Mutação.** O `qualidade.py` sobre as linhas do diff mata 16 de 16.
- **CRAP.** Fica abaixo de 10 nas funções tocadas. O `corroborar` ganhou teste para os três
  veredictos e chegou a 100% de cobertura. O `ev_ferramenta` é legado que já estava acima e
  não piorou.
