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
  - `tests/segredo.test.ts` tem 11 testes no kit:
    - o Bash reescrito sem `ref` nem `text`;
    - a saída grande lida do arquivo;
    - o erro e o MCP retidos;
    - a saída vazia que não chega ao guardrail;
    - o arquivo que sumiu;
    - a saída sem segredo, que volta como veio;
    - o modo `aviso`;
    - sem Python e com a resposta ilegível, a chamada roda uma vez;
    - a recusa de baixo e a `Read`, que nem chegam.
- **Mutação.** O número entra no commit que fecha a mutação.
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
- **A trajetória do `execucao.py`** grava o comando dos gates como veio. Isso é anterior a
  este ADR e fica para outro.

## Alternativas consideradas

- **`PostToolUse` no hook de settings.** Recusado como caminho principal. Ele só
  acrescenta texto depois que o modelo já leu a saída, e não reescreve a saída do Bash.
- **Reter a saída inteira quando há segredo.** Recusado. O resto da saída é o que o agente
  precisa para seguir: o teste que falhou, a linha do log.
- **Detectar por entropia.** Recusado pelo falso positivo em hash, id e chave de cache.
- **A regra em TypeScript, dentro do mod.** Recusado pelo mesmo motivo do ADR-0052: uma
  segunda regra fora dos testes em Python e longe do guardrail.
- **Ocultar também na `Read`.** Recusado pelo `Write` por cima.
