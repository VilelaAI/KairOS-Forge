# ADR-0046 — A régua não se afrouxa, o hook do git não se pula, e a revisão falha fechada

- **Status:** aceito
- **Data:** 2026-10-31
- **Versão:** v0.39.0

## Contexto

O [ECC](https://github.com/affaan-m/ecc) ("Everything Claude Code", licença MIT) é um plugin
da mesma família que o nosso, com escala muito maior: 71 agentes, 314 skills, 98 comandos,
adaptadores para 14 CLIs. A leitura dele, feita sem executar nada do repositório, mostrou
uma assimetria: das centenas de arquivos, poucas dezenas de scripts são gate de verdade; o
resto é prosa. O que vale trazer está nesses scripts e na forma como o ECC avalia os
próprios mecanismos, não no volume.

Quatro coisas apareceram como lacuna real do nosso lado, todas baratas e determinísticas:

| No ECC | O que tínhamos | A lacuna |
|---|---|---|
| `block-no-verify.js` bloqueia `--no-verify` e `-c core.hooksPath=` | o piso do ADR-0042 (segredo, fiação dos hooks do *editor*, destruição, controle da máquina) | nada impedia o agente de pular o pre-commit e o pre-push do **projeto** |
| `config-protection.js` bloqueia edição de config de lint e formatter existente, e dos arquivos de *ignore* | `.github/workflows/**` protegido como Goodhart; a classe `teste` (ADR-0039) para teste afrouxado | a régua que mora fora do CI — `.eslintrc`, `ruff.toml`, `tsconfig`, `.coveragerc`, `.pre-commit-config.yaml` — e a supressão inline (`# noqa`, `@ts-ignore`, `# pragma: no cover`) ficavam livres |
| hooks de segurança tratam entrada incompleta como falha fechada | `guardrail.py` falhava aberto em qualquer exceção, sem rastro ("falha aberta, mas silenciosa") | guardrail quebrado sumia sem ninguém ver |
| `orch-review.workflow.js`: "uncertainty must never clear a blocker"; revisor que morreu faz o veredicto falhar fechado | `/revisar` 4.5: "achado que não sobrevive sai antes de ser publicado"; o contrato não sabia quem tinha revisado | um 🔴 duvidoso saía junto com o ruído, e revisão com um revisor a menos podia fechar limpa |

## Decisão

### 1. Pular os hooks do git entra no piso

Nova regra de comando no piso (sem `modos`, sem `liberados`): `--no-verify` em qualquer
subcomando do git, `git commit -n` (inclusive agrupado, como `-an`), `core.hooksPath` trocado
na linha de comando (`-c` ou `--config-env`), `git config core.hooksPath <valor>`, e as
variáveis que desligam os gerenciadores de hook — `HUSKY=0`, `HUSKY_SKIP_HOOKS=1`,
`LEFTHOOK=0` e o `SKIP=` do pre-commit — antes de um `git`. As variáveis vão além do ECC.

Precisão primeiro, porque o piso não se configura. Antes de procurar, sai o texto livre que
pode **mencionar** a flag sem usá-la: o corpo dos heredocs e o valor de `-m`/`--message`. As
aspas em geral ficam, então `bash -c "git commit --no-verify"` continua sendo o comando. No
`git commit`, o agrupamento de flags curtas é lido letra a letra e para na primeira opção que
leva valor colado: `-uno` e `-cmain` não são `-n`. Em `git push`, `-n` é `--dry-run` e passa.

### 2. Classe `regua`: a config do gate e a supressão inline

Classe nova no `guardrail.py`, que nasce em `aviso` como `teste` e `parada`:

- **config da régua que já existia na base** — lint, formatter, typecheck, cobertura e os
  próprios hooks do git (`.husky/**`, `.pre-commit-config.yaml`, `lefthook.yml`,
  `lint-staged`), mais os arquivos de *ignore* (uma linha no `.eslintignore` cala o arquivo
  inteiro sem tocar no código nem na config). Criar a primeira config é setup e passa;
- **supressão inline adicionada em código de produção** — `eslint-disable`, `@ts-ignore`,
  `# noqa`, `# type: ignore`, `pylint: disable`, `//nolint`, `# nosec`,
  `# pragma: no cover`, `istanbul/c8/v8 ignore`, `rubocop:disable`, `@SuppressWarnings`,
  `#[allow(`. Conta o saldo do que entra contra o que sai (mover uma supressão não avisa),
  fora de literal de string, e não conta em teste (`@ts-expect-error` em teste é de
  propósito). `# pragma: no cover` importa em dobro: tira a linha do relatório que o `crap`
  do `qualidade.py` lê (ADR-0045).

O aviso sai uma vez por arquivo na sessão; o rastro vai para a trajetória sempre. O modo
`verificar` (Codex, OpenCode, CI) aplica o mesmo critério ao diff contra a base, deixando
fora os espelhos `linguist-generated`, e só falha com `{"modos": {"regua": "bloqueio"}}`.

`aviso`, não `bloqueio`, porque migração de versão e regra nova do time também mexem nessas
configs, e porque um falso positivo do linter às vezes pede mesmo a supressão. A diferença
entre os dois casos é o porquê escrito — no commit e, na supressão, no próprio comentário.
Promova a `bloqueio` quando a taxa de aviso cair, como as outras classes em observação.

### 3. O guardrail falha aberto, mas não em silêncio

Bloquear por bug próprio continua pior que a ausência do check, então a falha segue aberta.
O que muda: a exceção vira evento `guardrail_erro` na trajetória (modo e erro) e uma linha no
stderr. O `telemetria.py resumo` conta `falhas_do_guardrail`, e o `/auditar` reporta o
número e o considera para o top 3 — naquelas chamadas, o guardrail não guardou nada.

### 4. Na revisão, dúvida não refuta e revisor ausente não aprova

- **`/revisar` 4.5:** o 🔴 só sai se a releitura o **refutar** (o código citado não está ali,
  ou o caminho não acontece). Dúvida não é refutação: o achado fica com ` · incerto`, conta
  em `criticos` e bloqueia. O falso positivo custa uma rodada de correção; o falso negativo
  vai para produção. Para 🟠, 🟡 e 🔵 vale a regra antiga.
- **Contrato 1.1:** campo opcional `incompletos[]` na fence `kairos-revisao` — o revisor da
  faixa que não entregou parecer. Não-vazio exige `bloqueado`; com veredicto limpo o código é
  `sem_cobertura`, e o `ciclo.py` recusa `registrar limpo`. Campo opcional novo é MENOR pelas
  regras do ADR-0034: relatório sem o campo vale como antes. Exigir os nomes de Helena e
  Patrícia no `examinado` fecharia mais, mas seria regra de aceitação mais estrita (MAIOR) e
  quebraria relatórios antigos.

## Consequências

- **Primeiro achado no próprio repositório.** O `verificar` sobre o diff deste ADR acusou o
  `import prova  # noqa: E402` que o ADR-0045 adicionou ao `qualidade.py` — supressão
  legítima, com o motivo no próprio comentário. É o caso para o qual a classe nasce em aviso.
- **Os gates do ADR-0045 sobre este diff acharam três bugs.**
  - No CRAP, o diff começou com 8 funções reprovadas: 6 legadas que subiram de
    complexidade e uma nova no limite. A solução foi extrair e testar, não pedir exceção.
    Terminou com zero reprovadas, e `checar_escrita`, `checar_comando` e `ler_revisao` saíram
    *abaixo* da complexidade da base.
  - Na mutação, foram três rodadas de 60 sítios.
    - A primeira não julgou nada, porque um commit no meio da rodada desencontrou o worktree do
      diff. Era um bug do `qualidade.py`, corrigido fixando o HEAD num SHA.
    - A segunda matou 51. Entre os vivos estava um bug de ordem: `teste` e `regua`, que só
      avisam, rodavam antes de `protegido`, e um teste existente num caminho protegido recebia
      só aviso. Estavam também dois `try/except` que engoliam erro do git em silêncio,
      justamente o que este ADR proíbe.
    - A terceira matou 58. Os dois vivos (uma condição redundante e um teste que não distinguia
      o `cwd` do payload do processo) foram fechados e conferidos à mão.
- **Mais uma superfície de piso.** Uma regra de piso com falso positivo não tem válvula de
  configuração. Os testes cobrem os casos que mais confundem (mensagem que cita a flag,
  heredoc, valor colado, `push -n`); um caso novo que bloqueie errado volta como bug.
- **Contrato do `contrato` em 1.1.** Quem lê a revisão continua lendo igual; quem a produz
  ganha um campo para dizer o que faltou, e passa a ter de dizer.

## Alternativas consideradas

- **Bloquear a régua por default, como o ECC.** Recusada: o ECC bloqueia (exit 2) porque não
  tem modo de observação; nós temos, e toda classe que ainda não mediu a própria taxa de
  falso positivo nasce em `aviso` (ADR-0030/0039).
- **Falhar fechado em qualquer exceção do guardrail.** Recusada pelo motivo original: um bug
  num regex não pode travar a sessão inteira. O ECC também só fecha quando o hook não
  consegue ler a entrada inteira.
- **Trazer o GateGuard** (o agente só edita depois de provar que investigou). Recusada: o
  próprio ECC pré-registrou e rodou a avaliação, e o efeito **não foi confirmado** (52% contra
  38%, p = 0,21) a um custo de 35–45% mais turnos. A metodologia dele — hipótese escrita
  antes, braço placebo, avaliador validado com iscas, usuário simulado que só responde o que
  é perguntado — é o que vale, e fica para um ADR próprio sobre o `/avaliar` e o `/evoluir`.
- **Trazer os "instincts"** (lições extraídas da sessão e injetadas no SessionStart com a
  confiança que o próprio modelo atribuiu). Recusada: é o auto-enxerto dos ADRs 0037 e 0043.
