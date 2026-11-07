# ADR-0057 — Endurecimento dos gatilhos de CI

- **Status:** aceito
- **Data:** 2026-11-05
- **Versão:** v0.50.0

## Contexto

Os quatro gatilhos de `templates/ci/` (`revisar`, `corrigir`, `auditar` e `triar`) rodam
o `claude -p` no CI do projeto, com a `ANTHROPIC_API_KEY` e um token de escrita no
ambiente. A emenda ao ADR-0026 já tinha fechado a fronteira de confiança:
- texto de fora não entra no script por `${{ }}`;
- cada sessão declara as ferramentas na linha de comando, sem hooks nem MCP do projeto;
- o prompt diz que o texto de fora é dado;
- o `corrigir` ignora CI de fork.

Uma leitura dos templates achou o que ainda ficava aberto:

1. **O que roda com o segredo não vinha fixado.**
   - O Claude Code era instalado sem versão (`npm install -g @anthropic-ai/claude-code`).
   - A fábrica vinha da `main` do kairos-forge.
   - As actions eram citadas por tag (`actions/checkout@v4`), que pode ser movida para
     outro código.

   Qualquer uma das três mudava o que roda com o segredo do projeto sem ninguém do
   projeto decidir.
2. **O token do workflow ficava no disco.** O `actions/checkout` grava o token em
   `.git/config` por padrão. Rodei um Claude Code de verdade com as flags de hoje: o
   `Read` de `.git/config` devolveu o token, e o que o agente lê pode acabar no
   comentário público do `revisar`.
3. **As travas dependiam da versão.** Na 2.1.318, o `.claude/settings.json` de um
   branch não amplia nada: o `bypassPermissions` do projeto é ignorado, e a regra
   `allow` do projeto cai num workspace que não é confiável. Mas o template instalava a
   versão mais recente, e nada dizia que a proteção continuaria lá.
4. **O `corrigir` podia editar o próprio CI.** O prompt pedia para não tocar em
   `.github/workflows/`, mas a edição passava (provado com a CLI real).
5. **Segredo entrava e saía em texto.**
   - Entrava: o log de CI e a issue vão ao modelo, e o que ele lê vai à API.
   - Saía: o parecer, a triagem, a auditoria e o diagnóstico viram comentário ou PR
     públicos, e o agente pode repetir neles um segredo que leu no repositório.

## Decisão

1. **Versões fixadas.**
   - **Claude Code:** `npm install -g "@anthropic-ai/claude-code@$CLAUDE_CODE_VERSAO"`,
     com padrão `2.1.318` (a versão em que as travas abaixo foram provadas) e troca por
     `vars.CLAUDE_CODE_VERSAO`.
   - **Fábrica:** buscada por `git fetch --depth 1 … "$FORGE_REF"`, que aceita commit,
     tag ou branch, com padrão `main`. O README pede para fixar em `vars.FORGE_REF` um
     commit revisado. O kairos-forge não publica tags, por isso o padrão ainda é a
     `main`.
   - **Actions:** citadas pelo commit, com a versão num comentário (`checkout` v4.4.0,
     `setup-node` v4.4.0, `create-github-app-token` v1.12.0, `harden-runner` v2.22.3).
     As majors continuam as de antes; subir de major é outra decisão (tomada na emenda de
     v0.50.6, abaixo: as actions em `node24`).
2. **A fábrica entra como plugin da sessão** (`--plugin-dir /tmp/forge/plugin`), e não
   copiada para o `.claude/` do projeto. As skills carregam com o nome
   `kairos-forge:<skill>`, e o projeto deixa de ser fonte de settings.
3. **`--restricted` em todo `claude -p`.** Na 2.1.318, ele:
   - não lê settings de arquivo nenhum;
   - prende as ferramentas de arquivo às pastas de trabalho;
   - recusa `bypassPermissions`;
   - só deixa uma pessoa aprovar escrita em settings e em arquivos de configuração de
     ferramenta.

   Junto dele, `--tools` diz quais ferramentas existem na sessão. O `Skill` sempre
   entra, porque sem ele a fábrica não carrega. O `triar` e o `auditar` nem têm Bash. E
   `--permission-mode dontAsk` recusa o que não estiver liberado. O `corrigir` trocou o
   `acceptEdits` pelo `dontAsk`: as edições já estavam liberadas por `--allowedTools`, e
   o `acceptEdits` aprova mais do que isso.
4. **`persist-credentials: false` em todo checkout.** O `corrigir` só entrega o token
   ao git no passo do push (`gh auth setup-git`), depois que o agente terminou.
5. **O `corrigir` não edita `.github/`, `.claude/` nem `.agents/`.** As regras
   `Edit(./<pasta>/**)` e `Write(./<pasta>/**)` vão no `--disallowedTools`. A correção
   não mexe no próprio CI nem nas travas, e o `git add` também deixa `.claude/` de fora.
6. **Segredo fora do que entra e do que sai.** Um modo CLI novo,
   `guardrail.py ocultar ARQUIVO…`, aplica a regra do ADR-0056 no próprio arquivo, sai 0
   e diz no stderr o que ocultou.
   - Antes do agente, roda na issue (`triar`) e no log (`corrigir`).
   - Antes de publicar, roda no parecer, na triagem, na auditoria e no diagnóstico.
7. **Rede de saída, opcional.** O primeiro passo de cada job é o
   `step-security/harden-runner`, ligado por `vars.FORGE_SAIDA`:
   - `audit` registra os destinos;
   - `block` só deixa alcançar a API do modelo, o GitHub e o registro do npm.

   O `block` é gratuito em repositório público. Em privado, pede o plano da
   StepSecurity. Por isso o passo não é o padrão. Sem a variável, ele nem roda.

## Prova

Rodei o Claude Code 2.1.318 real contra a API falsa local, que pede uma ferramenta e
guarda o resultado. Os pedidos tentavam:
- ler o token em `.git/config` e a chave em `/proc/self/environ`;
- mandar dados para fora com `curl`, liberado por um `.claude/settings.json` hostil do
  branch (`allow: Bash(curl *)` e `defaultMode: bypassPermissions`);
- usar `git diff`;
- editar código, workflow e settings.

| Tentativa | Flags de antes | Flags de agora |
|---|---|---|
| `Read` de `/proc/self/environ` | recusado pelo próprio Claude Code | recusado |
| `Read` de `.git/config` com o token | **devolve o token** | devolve; por isso `persist-credentials: false` |
| `curl` liberado pelo settings do branch | recusado (na 2.1.318) | recusado: `--restricted` e `dontAsk` |
| `git diff` | roda | roda |
| Editar `.github/workflows/ci.yml` (`corrigir`) | — | **passava só com o `--restricted`**; recusado com a regra de caminho |
| Escrever `.claude/settings.local.json` | — | recusado |

Depois, extraí do YAML cada um dos quatro `claude -p`, com o mesmo parser dos testes, e
rodei com o Claude Code real:

| Template | Passa | É recusado |
|---|---|---|
| `revisar` | a skill `kairos-forge:revisar`, `git diff` | `curl` |
| `triar` | a skill `kairos-forge:especificar` | Bash: a ferramenta nem existe na sessão |
| `auditar` | a skill `kairos-forge:auditar` | Write: nem existe |
| `corrigir` | a skill `kairos-forge:validar`, a edição de `src/`, o gate (`npm test`) | edição em `.github/` e `.agents/`, `curl` |

O comando de rede do harden-runner não foi exercitado aqui: o ambiente não roda GitHub
Actions.

## Consequências

- **Testes.**
  - O `test_ci.py` passa a cobrar, no YAML:
    - action fixada por commit, com a versão;
    - `persist-credentials: false`;
    - as versões das variáveis;
    - nada de `git clone` nem de `cp` para o `.claude/`;
    - o passo de rede como primeiro e opcional;
    - a ocultação antes de cada publicação e antes do agente;
    - o token só depois do agente;
    - `--restricted`, `dontAsk`, `--tools` e as regras de caminho do `corrigir`.
  - Um teste roda de verdade o bloco do `revisar`, com uma CLI falsa que devolve um
    token, e confere que o parecer sai com a marca.
  - O `test_segredo.py` ganha o `ocultar` pela CLI.
  - As asserções antigas que fixavam o comportamento de antes foram trocadas por
    asserções mais estritas, não apagadas: o `acceptEdits` do `corrigir`, a ausência de
    `--permission-mode` nos outros três e o `create-github-app-token@v1` por tag.
  - **Prova negativa.** Nenhum dos testes novos (os 8 de `Endurecimento` e os 2 do
    `ocultar`) passa contra a `main`.
  - **Mutação.** O `qualidade.py` sobre o código do diff (o modo `ocultar`) mata 3 de 3.
    Os templates são YAML, e os testes acima os cobrem.
- **Subir o Claude Code é uma decisão.** O padrão fica na 2.1.318 até alguém conferir o
  `--restricted` e as regras numa versão nova e mudar a variável ou o template.
- **Sem tags, a fábrica ainda vem da `main` por padrão.** Publicar tags nas versões
  deixaria o padrão fixo sem pedir nada a quem instala. Fica como próximo passo.

## Alternativas consideradas

- **`--setting-sources user`** no lugar do `--restricted`. Recusado. Cortaria só os
  settings do projeto, sem prender as ferramentas de arquivo nem recusar o bypass.
- **`--bare`.** Recusado. Desliga a descoberta de `CLAUDE.md` e a carga dos plugins
  pelo caminho de sempre, e a fábrica depende das skills.
- **Fixar a fábrica num commit escrito no template.** Recusado. O template não sabe o
  commit em que ele mesmo vai ser mesclado, e o número envelheceria a cada versão.
- **Harden-runner em `block` por padrão.** Recusado pelo custo em repositório privado.
- **Proibir o `Read` de `.git/config` por regra.** Recusado como defesa principal. O
  token nem precisa estar no disco: `persist-credentials: false` resolve na origem.

## Emenda (v0.50.1): tags de versão

O `FORGE_REF` padrão era a `main`, porque o kairos-forge não publicava tags. Agora:

- **Cada versão ganha a tag `vX.Y.Z`**, no commit da linha principal (first-parent) em
  que o `version` do `.claude-plugin/plugin.json` passou a valer. É uma tag anotada, com
  a data e o assunto desse commit.
  - A versão que entrou junto com outra num único commit (um squash de várias versões)
    não tem commit próprio e fica sem tag, em vez de ganhar um commit alheio. No
    histórico até a v0.50.0, isso dá 55 tags.
  - Tag não se move nem se apaga. A que já existe em outro commit fica como está, e o
    comando sai 1.
- **Quem decide é o `release.py tags`.** Sem `--publicar`, mostra o plano contra as tags
  do clone e não cria nada. Com `--publicar`, compara com as do `origin`, cria as que
  faltam e publica num push só, sem `--force`.
- **Quem publica é o GitHub**, no workflow `.github/workflows/tags.yml`. Ele roda na
  `main` quando o manifesto muda, ou à mão. O checkout é fixado por commit, sem
  credencial no disco, e só o passo que publica recebe o token, com `contents: write`.
  No primeiro run, marca também as versões anteriores.
- **O template sabe a própria versão.** O `release.py bump` reescreve o padrão como
  `FORGE_REF: ${{ vars.FORGE_REF || 'vX.Y.Z' }}`, e o `check` cobra que ele bata com o
  manifesto. Quem copia um template recebe a fábrica da versão que copiou. A troca de
  versão passa a ser uma decisão de quem instala, e não um efeito da `main` do dia.

Isso revê a alternativa recusada "fixar a fábrica num commit escrito no template". O
template não sabe o commit em que vai ser mesclado, mas sabe a versão. A tag liga as duas
coisas depois do merge.

**Por que um workflow, e não a tag criada por quem faz o merge.** A sessão que preparou
esta mudança só conseguia fazer push em branch: a criação da tag voltou com HTTP 403. E
uma tag que depende de alguém lembrar de criá-la falha justo na versão em que ninguém
lembrou.

**Prova.** O `test_tags.py` roda o comando num git de verdade, com um remoto local:
- o ensaio não cria nada;
- cada versão sai no commit em que entrou;
- a versão mesclada junto com outra, o manifesto ilegível e a versão fora de X.Y.Z ficam
  sem tag;
- a tag é anotada, com a data e o assunto do commit;
- a segunda rodada não publica nada, e a versão nova ganha só a dela;
- a tag divergente no `origin` não se move, e as outras saem;
- a tag que só existe no clone é publicada, e a tag do clone em outro commit para tudo;
- sem `origin`, o erro é uma linha.

O mesmo arquivo cobra o workflow: o gatilho, a permissão, o checkout e nada que mova ou
apague tag. O `test_ci.py` cobra o padrão dos quatro templates contra a versão do
manifesto, e o `check` recusa o template que voltar para `'main'`. Nenhum dos testes
novos passa contra a `main`.

Na mutação do `qualidade.py` sobre o código do diff, a primeira rodada deixou dois
mutantes vivos. Um aceitava `version: "dev"` como versão. O outro dizia "ensaio" num run
que publicou. Os dois viraram teste, e a rodada final mata 21 de 21. O CRAP fica abaixo de
10 nas 12 funções tocadas, com a cobertura medida nos subprocessos do teste.

O workflow em si não rodou aqui: o ambiente não roda GitHub Actions. O primeiro run é o
merge desta emenda.

**O que o primeiro run ensinou (v0.50.2).** O merge publicou 55 das 56 tags, e a v0.19.0
voltou recusada: `refusing to allow a GitHub App to create or update workflow
.github/workflows/ci.yml without workflows permission`. O token do workflow não tem a
permissão `workflows`, e nenhuma linha de `permissions:` a concede. Por isso ele só cria
uma ref cujos arquivos de workflow já existem em alguma ref do repositório.
- O `ci.yml` da v0.34.2 e o da v0.44.0 estavam na ponta de branches antigas, e essas tags
  passaram.
- O da v0.19.0 não estava em nenhuma.

Como o push não é atômico, as outras 55 tags saíram, e o job ficou vermelho só pela que
faltou.

- **Versão nova não cai nisso.** O workflow marca o commit da ponta da `main`, que já tem
  esses arquivos.
- **Tag antiga recusada.** O caminho é publicar uma branch no commit dela, com uma
  credencial que tenha a permissão `workflows`, e rodar o workflow à mão. Foi o que se fez
  com `claude/ancora-tag-v0.19.0`. Depois que a tag existe, a branch pode ser apagada:
  a própria tag segura o commit.
- **Alternativa.** A pessoa roda `python3 scripts/release.py tags --publicar` no próprio
  clone.

Em nenhum dos dois casos o workflow ganha `workflows`. Um token que edita workflow, num
job que roda a cada versão, é mais permissão do que uma tag histórica vale.

## Emenda (v0.50.6): as actions em `node24`

O GitHub descontinuou o runtime Node 20 das actions, e o próprio CI deste repositório já
avisava: "Node.js 20 is deprecated", e a action era forçada a rodar em Node 24. A Decisão 1
deixou a troca de major para outra decisão, e esta é ela.

**Uma versão por action: a primeira em `node24`, no patch mais recente dela.** Não é a
última major. É a menor mudança que resolve. Para cada uma, o commit veio do
`git ls-remote` (nenhuma das tags é anotada), e o runtime foi lido no `action.yml` daquele
commit.

| Action | Antes | Agora |
|---|---|---|
| `actions/checkout` | v4.4.0 (`node20`) | v5.1.0 |
| `actions/setup-node` | v4.4.0 (`node20`) | v5.0.0 |
| `actions/setup-python` (CI do repositório) | v5, por tag | v6.3.0 |
| `actions/create-github-app-token` | v1.12.0 (`node20`) | v3.3.0. A v2 ainda roda em `node20` |
| `step-security/harden-runner` | v2.22.3 (`node20`) | v2.22.4 |
| `configure-pages`, `upload-pages-artifact`, `deploy-pages` (Pages) | v5, v3, v4, por tag | v6.0.0, v5.0.0, v5.0.1 |

**O que muda para quem instala, lido nas notas de cada major:**
- **`create-github-app-token`.**
  - A v2 removeu as entradas com sublinhado (`app_id`, `private_key`), e os templates usam as
    com hífen.
  - A v3 exige `NODE_USE_ENV_PROXY=1` para usar proxy HTTP, e runner self-hosted 2.327.1 ou
    mais novo.
  - O `app-id` continua aceito, mas está obsoleto em favor de `client-id`. Os templates
    seguem com `app-id`, porque trocar quebraria quem já configurou `vars.FORGE_APP_ID` com
    o id numérico do app. Mudar para o Client ID fica para outra decisão.
- **`checkout` v5.** Só troca o runtime, e também pede o runner 2.327.1. A v5.1.0 traz
  `allow-unsafe-pr-checkout`, que nasce `false` e recusa o checkout de código de fork em
  workflow de `workflow_run` ou `pull_request_target`. Isso reforça a regra de fork do
  ADR-0026: o `corrigir` já descartava fork antes do checkout.
- **`setup-node` v5.** Liga cache automático quando o `package.json` do projeto tem o campo
  `packageManager`. Nos templates, o Node só instala o Claude Code, e um cache sem lockfile
  poderia falhar o job. Por isso, `package-manager-cache: false`.

**De quebra:**
- **O Claude Code passa a ser instalado sobre Node 22.** O Node 20 saiu de suporte em abril
  de 2026, e esse job roda com o segredo do projeto. É a mesma versão em que o job
  `mod-painel` deste CI já roda o Claude Code fixado.
- **Os workflows do próprio repositório** (`ci.yml`, `pages.yml`) também passam a citar as
  actions pelo commit, como os templates e o `tags.yml`.

**Prova.**
- O `test_actions.py` lê os 28 `uses:` dos workflows e dos templates e exige:
  - o commit;
  - a versão no comentário;
  - uma versão igual ou posterior à primeira em `node24` de cada action;
  - o mesmo commit para a mesma versão em todo lugar.

  Action nova fora da tabela reprova até alguém conferir o runtime dela.
- Nos templates, o mesmo arquivo cobra o `setup-node` com Node 22 ou mais novo e sem o cache
  automático. Contra a `main`, falha em 15 casos, mais 2 erros.
- O `test_ci.py` trocou a exigência da major 1 do token pela 3.
- O workflow em si não rodou aqui, porque o ambiente não roda GitHub Actions. O primeiro run é
  o CI deste PR.
