# ADR-0029 — Máquina de estados determinística do arco `entregar`

- **Status:** aceito
- **Data:** 2026-08-02
- **Versão:** v0.21.0

## Contexto

A análise do repositório [cooperacode/IAO](https://github.com/cooperacode/IAO) — o padrão
*Inverted Agentic Orchestration*, de Yan Justino — expôs uma diferença de natureza entre os
dois harnesses:

> O IAO tem **garantia estrutural** onde temos **disciplina instrucional**: a máquina de
> estados dele não pode ser pulada; nossas regras podem ser driftadas.

No IAO, um binário compilado emite uma instrução por vez e o agente é o intérprete. A
sequência, o orçamento e a terminação são propriedade do código. No kairos-forge, a skill
`entregar` (ADR-0023) descrevia o mesmo arco **em prosa**: *"no bloqueio, corrija; máximo 2
rodadas; na terceira, escale"*.

Quem contava as rodadas era o modelo — juiz em causa própria sobre o próprio orçamento. E o
arco tinha uma regra especialmente frágil, escrita como aviso:

> *"Se a correção tocar código de produção, o `/validar` volta a valer: rode-o antes de
> reentrar na revisão. Correção que quebra requisito já validado é o modo de falha
> silencioso deste arco."*

Uma regra que o próprio texto classifica como modo de falha silencioso não deveria depender
de o modelo lembrar dela.

## Decisão

`scripts/ciclo.py` — máquina de estados de **um** fluxo, consultada pela skill.

**Não** é uma porta do IAO. Ficam de fora, por decisão: o protocolo de inbox, o binário
compilado, as quatro portas de linguagem e o modelo de "agente como intérprete burro" — que
seria incompatível com o ADR-0001 (plugin, não runtime) e com a fábrica de 71 agentes
roteados pela Laura. O que se importa é a **propriedade**: quem decide a transição é código.

### A máquina

```
especificando ─▶ aguardando_aprovacao ─▶ construindo ─▶ validando ──┐
                                              ▲                     │ bloqueado
                                     corrigindo_validacao ◀─────────┘ (orçamento)
                                                                     │ aprovado
                              revisando ◀──────────────────────────┘
                                  │ critico (orçamento)
                                  ▼
                         corrigindo_revisao ──▶ validando   ← a aresta que importa
                                  │ limpo (de revisando)
                                  ▼
                          pronto_para_pr ──▶ encerrado
```

`escalado` é terminal até o usuário destravar.

### Três garantias que a prosa não dava

**1. O orçamento é fato, não promessa.** `registrar bloqueado` com as rodadas esgotadas
devolve `escalado` — não existe "mais uma rodada, dessa vez vai". O contador vive no arquivo
de estado, não na memória da sessão.

**2. Correção de revisão reabre a validação.** `corrigindo_revisao` tem **uma única** aresta
de saída, e ela aponta para `validando`. A regra mais frágil do arco deixa de depender de
lembrança e passa a ser topologia do grafo.

**3. O veredicto vem do artefato.** `registrar aprovado` no estado `validando` lê o relatório
mais recente em `docs/specs/validacoes/` e extrai o `**Veredicto:**`. Sem relatório, recusa;
com relatório dizendo bloqueado, recusa. A transição é alimentada por evidência, não pela
palavra do agente — mesmo princípio da corroboração de trajetória do ADR-0021.

### Enforcement: o guardrail fecha a porta

Consultar não bastaria se fosse opcional. Duas regras novas no `guardrail.py` (ADR-0022):

- **`gh pr create` bloqueado** enquanto o estado não for `pronto_para_pr`. É a mesma classe
  de bloqueio que já recusa `rm -rf /`.
- **`gh pr merge` bloqueado** durante qualquer ciclo aberto — o arco termina no PR, e a
  decisão de integrar é do dono do repositório.

`git push` **não** é bloqueado: empurrar WIP para a branch é trabalho normal, e bloquear
geraria o falso positivo que desliga guardrail.

E `.agents/ciclo/**` entra nos caminhos **sagrados**, ao lado de `.agents/execucoes/` e
`.agents/guardrails.json`: o agente não escreve o próprio estado, pelo mesmo motivo pelo qual
não escreve a própria telemetria. Máquina de estados que o agente reescreve não é máquina de
estados.

### Estado sobrevive ao contexto

`.agents/ciclo/<spec>.json`, com escrita atômica (`os.replace`). Cada invocação relê o
arquivo — a entrega sobrevive a reset de contexto, troca de sessão e troca de CLI. É a
propriedade do IAO que mais valia a pena importar.

## Consequências

**Positivas**

- O orçamento do arco deixa de ser auto-reportado. Era o último lugar do fluxo onde o modelo
  julgava a si mesmo sobre um limite.
- O modo de falha silencioso do arco (correção que quebra requisito já validado) fica fechado
  por construção.
- A linhagem de rodadas do relatório de entrega passa a ser extraída de `historico`, não
  digitada de memória.
- Entrega interrompida é retomável: `ciclo.py estado` diz exatamente onde parou e o que
  fazer, sem depender do que ficou na conversa.

**Negativas e limites, declarados**

- **Não garante a qualidade do trabalho.** A máquina garante sequência, orçamento e
  terminação. Se o agente registra `pronto` sem ter corrigido de verdade, o ciclo avança —
  e o que pega isso é o `/validar` na volta, não o `ciclo.py`. Mesmo teto do IAO: exit code
  se verifica, qualidade não.
- **Bloqueio duro só no Claude Code.** `PreToolUse` não existe nos outros CLIs; lá o
  `ciclo.py` continua funcionando como máquina de estados, mas a obrigação de consultá-la
  degrada para disciplina — a mesma assimetria já declarada no ADR-0022, não uma nova.
- **`registrar` ainda aceita a palavra do agente** em todos os estados exceto `validando`.
  Corroborar `limpo` exigiria parsear o relatório de revisão, que hoje não tem formato fixo
  de veredicto em arquivo. Fica como lacuna conhecida.
- **Mais uma peça para manter:** script, arquivo de estado, duas regras de guardrail e a
  skill que consulta. É o custo de trocar promessa por fato.
- **Ciclo esquecido em aberto bloqueia PR.** `ciclo.py listar` mostra e
  `ciclo.py encerrar --motivo "..."` resolve — mas é uma pegadinha nova que não existia.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Portar o motor do IAO (binário + inbox + 4 linguagens) | Viola o ADR-0001 (plugin, não runtime) e assume um driver executando uma feature linear por vez — incompatível com Laura roteando 71 agentes e com `mobilizar` em paralelo |
| Só reforçar o texto da skill | Era o estado até a v0.20. O texto já dizia "máximo 2 rodadas" e nada impedia a terceira |
| Estender a máquina para o `mobilizar` também | O `mobilizar` é um grafo de tarefas paralelas, não uma sequência — a modelagem é outra. Escopo mantido no arco, onde a forma de máquina de estados é natural |
| Confiar em `registrar` sem ler o relatório | Manteria o auto-relato exatamente onde ele mais custa: no gate que decide se o trabalho passou |
| Bloquear `git push` junto com `gh pr create` | Falso positivo garantido em push de WIP — e guardrail que incomoda é guardrail desligado (ADR-0022) |
