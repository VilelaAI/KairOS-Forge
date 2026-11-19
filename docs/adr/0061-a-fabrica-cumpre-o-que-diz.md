# ADR-0061 — A fábrica cumpre o que diz

- **Status:** aceito
- **Data:** 2026-11-19
- **Versão:** v0.54.0

## Contexto

O "Fora deste ADR" do ADR-0060 listou achados de dois mapeamentos: o das três ideias e o do
`## Pronto quando` de cada skill. Parte deles era defeito em script. O mecanismo existia, a
skill ou o ADR o anunciava, e o código falhava sem avisar:

- **`ciclo.py`:**
  - o ataque à premissa (ADR-0045) não acontecia com o orçamento padrão: o limiar é a
    terceira falha seguida, e o orçamento 2 escalava antes dela;
  - `registrar pr_aberto` encerrava o arco sem nenhuma referência ao PR;
  - a revisão limpa de faixa 3 seguia para o PR, embora o `contrato.py` declarasse que a faixa 3
    nunca fecha por evidência (ADR-0031).
- **`contrato.py`:** a revisão em que um revisor não rodou e não houve 🔴 não tinha bloco
  válido. O ADR-0046 manda registrá-la como `bloqueado` com `incompletos`, e a coerência exigia
  `criticos` de 1 para cima.
- **`prova.py pre-patch`:** qualquer saída diferente de 0 na base virava `falhou_na_base`, a
  prova de que o teste depende da mudança. Isso valia também para a dependência não instalada,
  o erro de sintaxe e o auxiliar de teste que ficou para trás.
- **`quadro.py`:**
  - a tarefa concluída com `--gate-pulado` contava como pronta e sumia num "N de N";
  - sem a foto do checkout no `iniciar`, o `concluir` aceitava qualquer arquivo em silêncio;
  - o quadro sem tarefa podia ser encerrado.
- **`telemetria.py`:**
  - no `custo-eval --teto`, a versão sem caso medido contava como variação 0 e passava, contra
    "não medido, nunca 0" (ADR-0050);
  - sem `baseline/`, a primeira subpasta em ordem alfabética virava a baseline;
  - o `corroborar` comparava por trecho nos dois sentidos. O comando mais amplo, o mais estreito
    e o só citado corroboravam a alegação.
- **`check-agent-security.py`:** não lia o bloco `hooks` de `.claude/settings*.json`. Apontado
  para `.claude`, como o `/auditar` faz, não lia arquivo de hook nenhum.
- **Menores:**
  - o `grafo.py validar` saía 0 sem grafo e aceitava entidade sem fonte;
  - o `painel.py` lia título e requisito dentro de bloco de código;
  - o `guardrail.py verificar` acusava o próprio `guardrail.py` como gerado, porque ele contém a
    marca de gerado como constante.

## Decisão

Cada defeito foi reproduzido com um teste que falhava antes do conserto. O conserto é o menor
que cumpre o que o ADR de origem promete.

### `ciclo.py` (contrato 1.4)

- **A premissa com o orçamento padrão.** Quando a falha que esgota o orçamento é a terceira
  seguida sem progresso e a sequência ainda não tem premissa, o ciclo passa por
  `atacando_premissa_*` sem gastar ficha. A premissa escrita segue para `escalado` e vai no
  `motivo_escalacao`. As duas regras do ADR-0045 continuam: a premissa vem na terceira falha, e
  o orçamento é fato. Por isso o destino de `premissa_escrita` passa a ser calculado, e o
  contrato do ciclo sobe para 1.4. Com qualquer orçamento, a escalação leva a última premissa
  atacada.
- **`pr_aberto` exige `--pr <URL ou número>`.**
  - Sem ele, ou com algo que não é PR, `registrar` sai 1 e o estado não muda.
  - Com o `gh`, o PR é conferido: o que não existe ou foi fechado sem merge é recusado.
  - Sem `gh`, ou sem resposta, o arco encerra com `pr_conferido: false`.
  - Branch diferente é aviso.
- **Faixa 3.** O `registrar limpo` com faixa 3 no bloco da revisão é recusado com exit 1, e a
  mensagem manda escalar com `ciclo.py escalar --motivo "faixa 3: …"`.
- **Revisão incompleta.** Com `incompletos` preenchido, a contagem dela não vale como progresso.

### `contrato.py` (contrato 1.3)

- O `bloqueado` com `criticos` 0 vale quando `incompletos` não está vazio.
- A regra de cobertura (`examinado` não vazio) vale só para o veredicto que não é `bloqueado`. A
  revisão em que nenhum revisor rodou tem `examinado` vazio, e é honesto que tenha.
- `achados` vazio com 🔴 continua aceito: o ADR-0048 tornou os ids opcionais. Só o texto do
  esquema passa a dizer isso, para não prometer mais do que o parser cobra.

### `prova.py pre-patch`

- **Veredicto `erro_na_base`.** O teste que nem carrega na base é lido pela saída: módulo,
  nome, fixture, sintaxe, em Python, JS/TS e Go.
  - Quando o que falta é o que o diff acrescenta em código de produção, é prova: o teste de um
    símbolo novo não carrega porque o símbolo não existia.
  - O que o diff não explica sai `erro_na_base` e não prova nada: dependência ausente, fixture
    de plugin não instalado, sintaxe, auxiliar de fora do diff.
  - A asserção que só cita `SyntaxError` ou `No module named` continua falha comum.
- **O suporte de teste do diff vai para a base antes de rodar.** Entram o auxiliar e o
  `conftest.py`, novos ou mudados. Fica de fora o `_test.go`, que entra só na sua vez.
- **O `conftest.py` do diff que não carrega na base.** Ele faria todo teste novo da árvore sair
  `falhou_na_base`. Quando o pytest diz que não carregou o conftest e a regra normal deu prova,
  o teste roda de novo com os conftests da base.
  - Se passar, sai `passou_na_base`.
  - Se faltar uma fixture que o conftest do diff define, é prova.
  - Senão, vale a regra normal sobre a nova saída.

### `quadro.py` (contrato 1.3)

- **Gate pulado.**
  - O `--gate-pulado` exige motivo e não vale junto com `--gate-ok`.
  - A concluída com o gate pulado não conta como pronta: o quadro não se diz `completo`, e o
    `encerrar` pede `--lacuna "Tn: gate pulado — motivo"`.
  - A tarefa `--leitura` sem gate declarado não tem gate a pular.
  - O painel, o mod e a caixa mostram "🚧 gate pulado, sem lacuna" até a pessoa decidir.
- **Sem foto.** Sem a foto do checkout, o `concluir` recusa até receber `--sem-foto "motivo"`,
  no molde do `--fora-da-posse`, e o ledger registra.
- **Quadro vazio.** O quadro sem tarefa não encerra.

### `telemetria.py`

- **`custo-eval`.**
  - A versão sem variação medida sai em `nao_medido_no_teto` e reprova o `--teto`.
  - Sem `baseline/`, o `--baseline NOME` é obrigatório.
- **`corroborar`.** Só corrobora a execução que roda o comando alegado: as palavras dele
  inteiras e em sequência, até o fim do comando.
  - O prefixo é livre: `cd x &&`, `timeout`, variável de ambiente.
  - Depois do comando, só redirecionamento.
  - Não corroboram o comando mais curto, o mais estreito, um flag a mais nem o comando só
    citado em aspas, heredoc ou comentário.

### `check-agent-security.py`

Passa a varrer o bloco `hooks` de `.claude/settings.json` e `.claude/settings.local.json`, com os
mesmos padrões. As permissões não entram, porque o `deny` delas costuma citar o que protege.
Apontado para `.claude`, varre também o `.codex/hooks.json` e o `.cursor/hooks.json` do projeto.

### Menores

- **`grafo.py validar`:** sem entidade nenhuma, diz "Sem grafo de conhecimento" e sai 1. A
  entidade sem fonte reprova, e uma `fontes_de()` normaliza a forma para os três leitores. O CI
  só roda o `validar` quando há `entidades.jsonl`, `relacoes.jsonl` ou `aliases.jsonl`.
- **`painel.py`:** a SPEC é lida fora dos blocos de código. Por isso a matriz de exemplo
  cercada não roda no `qualidade.py criterios`, e o id do exemplo não vira "sem origem".
- **`guardrail.py`:** a marca de gerado só vale no cabeçalho: nas 5 primeiras linhas, ou nas 5
  depois do frontmatter.

### Versão

Três contratos mudam de forma e foram reassinados: `ciclo` 1.4, `contrato` 1.3 e `quadro` 1.3.
Todos são mudança MENOR, como os precedentes (ciclo 1.1 e 1.3, quadro 1.2). Em cada um, o que
muda é aceitação mais estrita ou derivado mais preciso: o `completo` do quadro deixa de contar
como pronta a tarefa que pulou o gate. Nenhum campo existente muda de sentido para quem já os
lia certo.

A fábrica sobe para a v0.54.0.

Quem dirige o arco por fora precisa saber de uma mudança: `registrar pr_aberto` sem `--pr` agora
sai 1. O `proximo_passo` do `estado --json` já diz o comando com o `--pr`.

## Prova

- **Testes.** 912 testes stdlib passam. Cada defeito tem um teste que falhava antes do conserto,
  e o cético da frente desfez o conserto parte por parte para ver o teste cair. Entre eles:
  - o `pr_aberto` com um `gh` falso;
  - o `pre-patch` com um pytest mínimo para o CI e com o pytest 9.2 de verdade, inclusive o
    conftest que não carrega;
  - o quadro num git de verdade;
  - o mod do painel com o kit do Claude Code.
- **Duas rodadas por frente.** As seis frentes rodaram em paralelo, cada uma num worktree
  próprio. Um corretor reproduziu e consertou. Um cético aplicou o patch num worktree limpo e
  tentou derrubá-lo. Os céticos acharam e consertaram:
  - a falha comum de asserção que virava `erro_na_base`;
  - a fixture de plugin que virava prova falsa;
  - o comando em várias linhas que deixava de corroborar;
  - o comando só comentado que corroborava;
  - o bloco `hooks` serializado numa linha só, que juntava dois comandos num achado;
  - o settings fora de UTF-8 que derrubava a auditoria;
  - o `--gate-pulado` da tarefa só de leitura, que virava lacuna falsa;
  - a revisão incompleta sem nenhum revisor que rodou;
  - a recusa no ataque da escalação, que prometia uma correção que não vem.
- **Os dois achados que ficaram de fora dos céticos** foram consertados depois:
  - o conftest que não carrega na base;
  - a escalação com orçamento maior, que não levava a premissa.
- **A conferência do `## Pronto quando` no Claude Code 2.1.328, com o plugin da v0.53.0 e uma
  API falsa.** A prova que o ADR-0060 deixou pendente depois dos ajustes da revisão foi feita em
  quatro variantes:
  - a skill chamada pelo modelo;
  - a skill digitada pela pessoa;
  - nenhuma skill;
  - duas skills na mesma sessão, com os blocos inteiros das duas.

## Limites

- **Faixa 3 só em prosa.** Relatório de revisão sem bloco não tem faixa lida, e a faixa 3
  escrita só em prosa não é recusada.
- **PR sem `gh`.** O `--pr` pega a omissão, mas não prova que o PR existe.
- **Validação parada por falta de prova.** Três validações seguidas bloqueadas só por falta de
  prova também pedem a premissa. Com orçamento 3 ou mais, isso já acontecia.
- **`pre-patch`.**
  - O auxiliar de teste fora de pasta de teste (por exemplo `src/test-utils.ts`) não vai para a
    base. Quando falta, é tomado por produção do diff, como antes.
  - A nova rodada sem o conftest é só do pytest: o setup do jest em `__tests__/` que importa
    produção nova ainda faz todo teste novo da árvore contar como prova.
- **`corroborar`.**
  - O prefixo é livre: `echo pytest tests/` sem aspas corrobora.
  - Um `;` dentro de aspas conta como separador.
  - `bash -c "pytest"` não corrobora.
- **`custo-eval`.** Toma como pasta o primeiro argumento que não começa com `--`. A pasta vem
  antes dos flags.
- **Gate pulado.** Não tem caminho barato para virar `ok` depois que o gate roda. Só o
  `compensar`, que exige `--reverter`.
- **`check-agent-security.py`.** Não varre o `statusLine`, o `apiKeyHelper` nem os scripts que
  os hooks chamam.
- **Marca de gerado no `sync-multi-cli.py instalar`.** Ele ainda considera nosso o arquivo com a
  marca em qualquer lugar.

## Fora deste ADR

Continuam para outra tarefa estes achados do ADR-0060, que não são deste grupo:

- **`/onboardar`:** gera o `contextos/testes.md` em tabela, e o `guardrail.py gates_declarados`
  só lê lista com crase.
- **Tucano:** os corpos citam `forge-<x>` de skills que não estão no time.
- **Texto que se contradiz:** a lista do grupo 2, no ADR-0060.
