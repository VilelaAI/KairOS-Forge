# ADR-0026 — Gatilhos por evento: a fábrica acorda sem ninguém digitar

- **Status:** aceito
- **Data:** 2026-08-01
- **Versão:** v0.19.0

## Contexto

A definição de L4 na régua de adoção é literal sobre o mecanismo:

> **L4 — Fábrica:** *"Pipelines autônomos cuidam de correções, QA, protótipos e fluxos
> repetíveis. O time confia mais no harness do que em revisão individual de código."*

Pipeline autônomo é, por definição, **orientado a evento**. Até a v0.18 o kairos-forge
tinha 16 skills e todas eram invocadas por slash command — um humano no teclado por unidade
de trabalho. A ponte Hermes (ADR-0019) adiciona chat 24/7 e cron, mas cada tarefa ainda
começa com uma frase do fundador.

E havia uma lacuna mais concreta: o repositório tem CI **para si mesmo** e nunca entregou
**nenhuma receita de CI para o projeto do usuário**. A fábrica que prega guardrails e gates
deixava o usuário montar a integração sozinho.

## Decisão

`templates/ci/` com três workflows prontos para o projeto do usuário, mais um README que é
metade instalação e metade modelo de segurança.

| Arquivo | Dispara quando | O que faz | Escreve |
|---|---|---|---|
| `kairos-forge-revisar.yml` | PR aberto/atualizado | `/revisar` e comenta o parecer | comentário |
| `kairos-forge-corrigir.yml` | CI do projeto falha | Diagnostica e corrige, **abrindo PR** | branch + PR |
| `kairos-forge-auditar.yml` | Segunda 09:00 (cron) | `/auditar` e abre issue com as 3 lacunas | issue |

### A ordem de instalação faz parte da decisão

O README abre com isto, e não é enfeite:

> Instale estes workflows **depois** de ter telemetria (ADR-0021) e guardrails
> determinísticos (ADR-0022) rodando. Gatilho por evento sem instrumento e sem contenção
> não é autonomia — é pipeline sem supervisão.

E o `/auditar` reforça pelo outro lado: na dimensão Autonomia, a lacuna "tudo verde e ainda
sem gatilho por evento" só é recomendada **depois** das lacunas de telemetria e guardrail.
Recomendar gatilho a um projeto sem guardrail seria recomendar dano automatizado.

A recomendação de adoção é gradual e por custo: comece pelo `auditar` (semanal, barato,
zero escrita em código), depois `revisar`, e só então `corrigir`.

### O modelo de segurança do `corrigir`

É o workflow que mais se aproxima do L4 e o mais perigoso. Cinco travas, nenhuma opcional:

1. **Nunca escreve em branch protegida.** Cria `forge/corrige-<branch>-<run>` e abre PR.
2. **Não reage a si mesmo** — a condição exclui branches que começam com `forge/corrige-`.
   Sem isso, um CI que continua vermelho vira loop infinito consumindo credencial.
3. **Deduplica** — se já existe PR de correção aberto para aquela branch, não empilha outro.
4. **Uma rodada, sem insistir.** O prompt carrega a regra que a fábrica já usa no `/lancar`
   e na ponte: *"duas falhas materialmente iguais nunca viram terceira tentativa"*.
5. **Escopo travado no prompt:** corrigir só o que causou a falha, não refatorar, não tocar
   em `.github/workflows/`. Agente que conserta o CI editando o CI é o Goodhart mais óbvio
   que existe — e o `guardrail.py` (ADR-0022) já protege esse caminho de qualquer forma.

Os três workflows rodam `guardrail.py verificar` antes de aceitar o resultado: em CI não
existe `PreToolUse`, então o mesmo contrato é verificado depois.

### Por que abre PR em vez de commitar direto

Porque L4 é *"o time confia mais no harness do que em **revisão individual de código**"* —
não "ninguém revisa nada". O PR é onde a evidência aparece. O que sai do caminho humano é a
leitura linha a linha; o que fica é a decisão de integrar.

O README diz explicitamente que auto-merge é decisão do time, e **não deve ser ativado
antes de o número da dimensão Autonomia justificar**. A régua existe; usá-la é escolha de
quem opera.

### Ausência de credencial pula, não falha

Os três verificam `ANTHROPIC_API_KEY` e saem limpos se não houver. Fork e PR externo não
ficam vermelhos por falta de segredo — mesma regra do ADR-0025: falso vermelho treina o
time a ignorar o vermelho.

## Consequências

**Positivas**

- É o movimento mais visível de L4: a fábrica trabalha enquanto ninguém olha.
- Fecha a lacuna dos CLIs sem hook — Codex, OpenCode e Cursor não têm `PreToolUse` nem
  telemetria, mas todos têm CI. O `guardrail.py verificar` no pipeline é o caminho de
  paridade possível para eles (ADR-0022).
- `auditar` semanal por cron transforma o ritual de sexta em algo que acontece mesmo quando
  ninguém lembra — que era o modo de falha real do ADR-0012.

**Negativas e limites, declarados**

- **Custo por disparo, e ele multiplica.** Um `revisar` por PR num repo com 30 PRs/semana
  são 30 execuções. O README manda estimar antes de ligar os três; é a mitigação possível
  sem medir a conta do usuário.
- **São templates, não produto instalado.** O usuário copia e ajusta (nome do workflow de
  CI observado, cron, branch base). Não há mecanismo de atualização: melhorias no template
  não chegam a quem já copiou.
- **`workflow_run` tem armadilhas.** Dispara no contexto da branch default, exige checkout
  explícito do head, e o token tem permissões diferentes do `pull_request`. Os templates
  tratam isso, mas quem editar precisa saber.
- **Não há sandbox.** O agente roda no runner do GitHub com o que o `permissions:` der.
  Permissão mínima por workflow reduz o raio, não o elimina.
- **`corrigir` pode propor bobagem.** Uma rodada, escopo travado e PR obrigatório existem
  exatamente porque isso vai acontecer. O custo de uma proposta ruim é um PR fechado.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| `corrigir` commitando direto na branch do PR | Some com a evidência e com o ponto de decisão. Um erro passa a exigir arqueologia de commits em vez de fechar um PR |
| Usar a action oficial em vez de `claude -p` | O `claude -p` já é o caminho que a ponte Hermes usa e não depende da API de uma action específica. Menos superfície para quebrar |
| Instalar o plugin via marketplace no CI | O comando é TUI e não roda headless. Copiar `plugin/skills` e `plugin/agents` para `.claude/` é o caminho portátil documentado |
| Rodar `entregar` (arco completo) por gatilho | Arco completo dispara o gate de aprovação da SPEC, que precisa de humano. Gatilho por evento serve para o que fecha sem decisão de escopo: revisar, corrigir, auditar |
| Não entregar templates e deixar o usuário montar | Era o estado até a v0.18, e o resultado observado é que ninguém monta. Fábrica que não entrega a esteira entrega bancada |
