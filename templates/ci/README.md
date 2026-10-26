# Gatilhos por evento — a fábrica trabalhando sem ninguém digitar

Receitas de CI para **o projeto do usuário** (não para o repo do plugin). São o
que separa L3 de L4 na prática: em L3 a fábrica acorda quando alguém digita uma
skill; aqui ela acorda porque um PR abriu, um CI ficou vermelho, uma issue chegou
ou é segunda-feira de manhã.

> **Ordem importa.** Instale estes workflows **depois** de ter telemetria
> (ADR-0021) e guardrails determinísticos (ADR-0022) rodando. Gatilho por evento
> sem instrumento e sem contenção não é autonomia — é pipeline sem supervisão,
> e o `/kairos-forge:auditar` vai apontar isso como lacuna, não como avanço.

## O que tem aqui

| Arquivo | Dispara quando | O que faz | Escreve? |
|---|---|---|---|
| `kairos-forge-revisar.yml` | PR aberto, atualizado, reaberto ou tirado de rascunho (PR em rascunho é ignorado) | Roda `/kairos-forge:revisar` e comenta o parecer | Só comentário |
| `kairos-forge-corrigir.yml` | O workflow de CI observado termina em falha numa branch que **não** é a default nem `forge/corrige-*` | Diagnostica e tenta corrigir em uma rodada, **abrindo PR** contra a branch que falhou; pula se já houver PR de correção aberto para ela | Branch nova + PR |
| `kairos-forge-auditar.yml` | Segunda-feira 09:00 em UTC-3 (cron `0 12 * * 1` — o cron do Actions é UTC), ou manual | Roda `/kairos-forge:auditar` e abre issue com as 3 lacunas | Issue |
| `kairos-forge-triar.yml` | Issue aberta/reaberta, ou rotulada `forge:triar` | Laura e Joana classificam: `forge:pronto` · `forge:precisa-spec` · `forge:falta-informacao` (com as perguntas) · `forge:aguardar` (ADR-0040) | Rótulo + comentário |

## Instalação

```bash
mkdir -p .github/workflows
cp <plugin>/templates/ci/kairos-forge-*.yml .github/workflows/
```

Depois, no repositório: **Settings → Secrets → Actions**, crie
`ANTHROPIC_API_KEY`. Sem o segredo, os workflows **pulam** com uma mensagem clara
em vez de falhar — falso vermelho treina o time a ignorar o vermelho.

Ajuste em cada arquivo o que for do seu projeto: o nome do workflow de CI que o
`corrigir` observa (`workflows: ["CI"]`) e o horário do cron do `auditar`, em UTC.
A branch protegida não precisa de ajuste: o `corrigir` compara com a default do
repositório (`github.event.repository.default_branch`).

## O modelo de segurança

Autonomia só é segura se o erro for barato. As cinco regras que estes workflows
seguem, e que você deve manter se editá-los:

1. **Nunca escreve na branch que falhou nem na default.** O `corrigir` só age em
   falha fora da default, cria `forge/corrige-<branch que falhou>-<id da execução de CI>`
   e abre PR **contra a branch que falhou**. Merge continua sendo decisão humana —
   é a fronteira de aprovação do ADR-0023, que sobrevive a L4 inteira.
2. **Uma tentativa por evento, sem auto-disparo.** O `concurrency` muda por workflow:
   - `revisar`, `auditar` e `triar` usam `cancel-in-progress: true` — evento novo no
     mesmo PR, na mesma issue ou na auditoria cancela a execução anterior, e só a
     mais recente conta.
   - `corrigir` agrupa por branch com `cancel-in-progress: false` — a correção em
     andamento não é cortada no meio; a falha seguinte da mesma branch espera na
     fila e, se a anterior abriu PR, encontra o PR e pula. O job ignora falha em
     `forge/corrige-*`, então o CI do próprio PR de correção não dispara outra
     correção, e o prompt pede uma rodada só.

   Loop de correção que se auto-dispara é como se queima orçamento (e credencial)
   dormindo.
3. **Permissão mínima por workflow.** `revisar`: `contents: read` e
   `pull-requests: write`, para comentar. `auditar` e `triar`: `contents: read` e
   `issues: write`. Só o `corrigir` tem `contents: write` — para empurrar a branch
   nova —, além de `pull-requests: write`.
4. **Timeout em tudo.** 20 min no `revisar` e no `auditar`, 30 no `corrigir`, 15 no
   `triar`. Job travado é custo silencioso.
5. **Guardrail depois do fato — e só o `corrigir` bloqueia nele.** Em CI não existe
   `PreToolUse`, então o contrato do `guardrail.py` roda depois (ADR-0022), e cada
   workflow o usa de um jeito:
   - `corrigir`: `guardrail.py verificar .` depois da rodada e **antes** do PR. Com
     achado, o passo sai 1, nada é empurrado e o PR não abre — é o único em que o
     guardrail bloqueia.
   - `revisar`: roda antes da revisão, com `|| true`. O resultado fica no log do
     job; não bloqueia e não entra no parecer.
   - `auditar` e `triar`: não chamam o guardrail — não escrevem código.

## Gates determinísticos sem modelo

Nem todo gate da fábrica precisa de modelo. As checagens abaixo são código puro —
sem `ANTHROPIC_API_KEY`, sem custo de token — e são a parte do harness que funciona em
**qualquer** CLI. Não há arquivo para copiar: cole o job abaixo no seu CI. Em Codex e
OpenCode, onde o guardrail não tem hook, é este job que cumpre o "guardrails rodando"
da nota do topo.

- **`guardrail.py verificar .` em todo PR.** No Codex e no OpenCode é o único caminho do
  guardrail; no Cursor é o que sobra das classes de escrita, que lá não têm hook antes da
  edição (ADR-0042 e a tabela de limitações por CLI do plugin). No CI ele observa o que
  ficou no repositório: SPEC com `Concluído` sem `verificado:`, relatório com bloco de
  contrato inválido, arquivo de segredo na árvore e, como aviso, teste existente com
  sinal de afrouxamento (bloqueia só com `{"modos": {"teste": "bloqueio"}}` em
  `.agents/guardrails.json`; mede contra a primeira ref que existir entre `origin/HEAD`,
  `origin/main`, `origin/master`, `main` e `master` — com outra default, use o
  `testes-alterados` com `--base`). O que ele **não** vê: comando destrutivo, leitura de segredo
  e gate de parada (só existem em hook) e escrita em arquivo protegido que não seja
  segredo — `.github/workflows/`, `.agents/ciclo/`, a fiação dos hooks. Ali, no CI, quem
  olha é a revisão do diff. A checagem de artefato gerado compara com o HEAD e, num
  checkout limpo, não tem o que ver — ela serve ao pre-commit.
- **`prova.py selado`** quando o projeto tiver `evals/*/selado.jsonl` (ADR-0043; passo 7
  do `/kairos-forge:avaliar`). Caso selado copiado para prompt, skill, persona,
  `contextos/`, teste ou doc, ou repetido no `gold.jsonl` visível, sai 1. Sem selado no
  repositório, diz que não há o que proteger e sai 0 — pode ficar ligado desde já.
- **Opcional (ADR-0039).** `prova.py testes-alterados` sai 1 quando teste existente perde
  asserção ou caso, ganha `skip` ou é apagado — a versão dura do aviso do `verificar`.
  `prova.py pre-patch` roda cada teste novo contra a base num worktree descartável e sai
  1 se ele passar lá, porque então não prova a mudança. Precisa das dependências do
  projeto instaladas, como no seu job de testes: sem elas o teste falha na base por falta
  de dependência e conta como `falhou_na_base`, um verde falso.

```yaml
name: kairos-forge — gates sem modelo

on:
  pull_request:

permissions:
  contents: read

concurrency:
  group: forge-gates-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  gates:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0 # o diff contra a base precisa de histórico

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Baixar a fábrica
        run: git clone --depth 1 https://github.com/VilelaAI/kairos-forge /tmp/forge

      - name: Guardrail
        run: python3 /tmp/forge/scripts/guardrail.py verificar .

      - name: Selado fora da instrução
        run: python3 /tmp/forge/scripts/prova.py selado

      # Opcionais (ADR-0039). O pre-patch exige as dependências do projeto instaladas antes.
      # - name: Teste existente afrouxado
      #   run: python3 /tmp/forge/scripts/prova.py testes-alterados --base "origin/${{ github.base_ref }}"
      # - name: Teste novo prova a mudança
      #   run: python3 /tmp/forge/scripts/prova.py pre-patch --base "origin/${{ github.base_ref }}"
```

Rode o `verificar` num checkout limpo, antes de instalar dependências: a varredura de
segredo percorre a árvore inteira (só `.git/` fica fora). Ela aplica as mesmas exceções
do hook de escrita — `*.example`, `*.sample`, `*.template`, `*.dist`, `*.md` —, então um
`.env.example` versionado passa e um `.env` não.

## O rótulo da triagem é fila, lock e pausa

No `triar`, o rótulo faz três coisas ao mesmo tempo: é a **fila** (quem consome o backlog
filtra por ele), o **lock** (issue que já tem `forge:*` não é triada de novo — dois agentes
nunca pegam a mesma; para re-triar, aplique `forge:triar`) e o **ponto de pausa humano**:
o workflow nunca aplica `forge:construir`. Esse rótulo é seu — movê-lo é a aprovação de
intenção, a mesma fronteira do ADR-0023. O que consome `forge:construir` (o arco
`/entregar` headless) ainda não existe como template, de propósito: entra quando o arco
headless tiver trajetória medida.

Crie os seis rótulos no repositório antes de instalar — os quatro que o workflow aplica
(`forge:pronto`, `forge:precisa-spec`, `forge:falta-informacao`, `forge:aguardar`) e os
dois que são do humano (`forge:triar`, para pedir re-triagem, e `forge:construir`):

```bash
for r in pronto precisa-spec falta-informacao aguardar triar construir; do
  gh label create "forge:$r" --force
done
```

## Por que `corrigir` abre PR em vez de commitar direto

Porque L4 é *"o time confia mais no harness do que em revisão individual de
código"* — e não *"ninguém revisa nada"*. O PR é onde a evidência aparece
(gates rodados, o que mudou, por quê). O que sai do caminho humano é a leitura
linha a linha; o que fica é a decisão de integrar.

Se o seu time quiser auto-merge depois que a confiança estiver medida e alta,
isso é uma decisão de vocês — e a régua está no `/kairos-forge:auditar`, dimensão
Autonomia. Não ative auto-merge antes de o número justificar.

## Custo

Cada disparo consome tokens. Antes de ligar os quatro, estime: um `revisar` por PR
num repo com 30 PRs/semana é 30 execuções semanais. Comece pelo `auditar`
(semanal, barato), depois `triar` (uma leitura por issue) e `revisar`, e só então
`corrigir`. Os gates sem modelo ficam fora dessa conta: não gastam token.
