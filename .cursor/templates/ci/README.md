# Gatilhos por evento — a fábrica trabalhando sem ninguém digitar

Receitas de CI para **o projeto do usuário** (não para o repo do plugin). São o
que separa L3 de L4 na prática: em L3 a fábrica acorda quando alguém digita uma
skill; aqui ela acorda porque um PR abriu, um CI ficou vermelho ou é sexta-feira.

> **Ordem importa.** Instale estes workflows **depois** de ter telemetria
> (ADR-0021) e guardrails determinísticos (ADR-0022) rodando. Gatilho por evento
> sem instrumento e sem contenção não é autonomia — é pipeline sem supervisão,
> e o `/kairos-forge:auditar` vai apontar isso como lacuna, não como avanço.

## O que tem aqui

| Arquivo | Dispara quando | O que faz | Escreve? |
|---|---|---|---|
| `kairos-forge-revisar.yml` | PR aberto ou atualizado | Roda `/kairos-forge:revisar` e comenta o parecer | Só comentário |
| `kairos-forge-corrigir.yml` | CI do projeto falha | Diagnostica e tenta corrigir, **abrindo PR** | Branch nova + PR |
| `kairos-forge-auditar.yml` | Segunda-feira 09:00 (cron) | Roda `/kairos-forge:auditar` e abre issue com as 3 lacunas | Issue |

## Instalação

```bash
mkdir -p .github/workflows
cp <plugin>/templates/ci/kairos-forge-*.yml .github/workflows/
```

Depois, no repositório: **Settings → Secrets → Actions**, crie
`ANTHROPIC_API_KEY`. Sem o segredo, os workflows **pulam** com uma mensagem clara
em vez de falhar — falso vermelho treina o time a ignorar o vermelho.

Ajuste em cada arquivo o que for do seu projeto: nome do workflow de CI que o
`corrigir` observa, horário do cron, e a branch base.

## O modelo de segurança

Autonomia só é segura se o erro for barato. As cinco regras que estes workflows
seguem, e que você deve manter se editá-los:

1. **Nunca escreve em branch protegida.** O `corrigir` cria `forge/corrige-<run>`
   e abre PR. Merge continua sendo decisão humana — é a fronteira de aprovação do
   ADR-0023, que sobrevive a L4 inteira.
2. **Uma tentativa por evento.** `concurrency` com `cancel-in-progress` e uma
   única rodada por execução. Loop de correção que se auto-dispara é como se
   queima orçamento (e credencial) dormindo.
3. **Permissão mínima por workflow.** `revisar` só lê o código e escreve
   comentário; `auditar` só abre issue. Nenhum tem `contents: write` além do
   necessário.
4. **Timeout em tudo.** Job travado é custo silencioso.
5. **Guardrail roda junto.** Cada workflow chama `guardrail.py verificar` antes
   de aceitar o resultado — em CI não existe `PreToolUse`, então o mesmo contrato
   é verificado depois (ADR-0022).

## Por que `corrigir` abre PR em vez de commitar direto

Porque L4 é *"o time confia mais no harness do que em revisão individual de
código"* — e não *"ninguém revisa nada"*. O PR é onde a evidência aparece
(gates rodados, o que mudou, por quê). O que sai do caminho humano é a leitura
linha a linha; o que fica é a decisão de integrar.

Se o seu time quiser auto-merge depois que a confiança estiver medida e alta,
isso é uma decisão de vocês — e a régua está no `/kairos-forge:auditar`, dimensão
Autonomia. Não ative auto-merge antes de o número justificar.

## Custo

Cada disparo consome tokens. Antes de ligar os três, estime: um `revisar` por PR
num repo com 30 PRs/semana é 30 execuções semanais. Comece pelo `auditar`
(semanal, barato), depois `revisar`, e só então `corrigir`.
