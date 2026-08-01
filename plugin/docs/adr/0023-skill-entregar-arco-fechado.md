# ADR-0023 — Skill `entregar`: o arco fechado dentro do plugin

- **Status:** aceito
- **Data:** 2026-08-01
- **Versão:** v0.18.0

## Contexto

O modelo de fábrica do whitepaper Day-1 tem cinco partes: specs e contexto, agentes, testes
e gates, guardrails — e **loops de feedback que roteiam falhas de volta aos agentes para
correção**. Sobre a última, o paper é específico: *"If a test fails, the orchestration logic
captures the error output from that environment and routes it back to the model, asking it
to try again. The harness is what creates this automated 'think → act → observe' loop."*

A análise de 2026-08-01 encontrou esse loop **já desenhado no repositório** — e fora do
produto. Em `hermes/skills/kairos-forge-ciclo.md`:

> Bloqueio em requisito P1 → card → Blocked com o motivo exato e volta à etapa 3 (máximo 2
> rodadas de correção; na terceira, escale ao fundador). […] Achado crítico 🔴 volta à
> etapa 3.

Esse é exatamente o arco. Mas ele vive numa skill do **Hermes**, executada pelo agente do
Hermes, e só existe para quem roda a ponte. O usuário do plugin em Claude Code, Codex,
OpenCode ou Cursor tem 15 verbos e digita a sequência à mão — e dentro do plugin o
`/kairos-forge:validar` declara explicitamente *"Não implemente correções nesta skill"*,
devolvendo ao usuário uma recomendação de qual comando digitar em seguida.

É a assinatura do L3 na imagem de referência: *"humanos focam em planejamento, tarefas
paralelas e revisão final do pull request"*. O humano é o barramento que liga as etapas.

## Decisão

Promover o arco para dentro do plugin como a skill **`entregar`** (15 → 16 skills). Não é
invenção: é a lógica da ponte Hermes, generalizada para qualquer CLI e integrada às
disciplinas que a fábrica já tem.

### O arco

```
especificar → APROVAÇÃO → construir → validar ⇄ corrigir (máx 2) → revisar ⇄ corrigir (máx 2) → PR
```

Falha em validação ou revisão **não volta ao usuário**: volta ao agente que o relatório
nomeou (o `/validar` e o `/revisar` já nomeiam — Ricardo em cobertura, Helena em segurança,
Carlos em dados). Só os agentes dos achados entram — corrigir é cirurgia, não mutirão.

Uma regra sutil e importante: se a correção da revisão tocar código de produção, a validação
**volta a valer** antes de reentrar na revisão. Correção que quebra requisito já validado é
o modo de falha silencioso deste arco.

### Orçamento antes da rodada 1

Mesmo contrato do `/mobilizar` (ADR-0012) e do `/otimizar`: rodadas por gate, checkpoints,
critério de encerramento e escalação, tudo declarado e anunciado antes de começar.
Avisa-e-pausa em 80%, pausa em 100% (ADR-0013). Orçamento esgotado → **encerramento
honesto** com as pendências declaradas, nunca PR aberto com P1 bloqueado.

### A fronteira de aprovação sobrevive intacta

O arco fechado tira o humano da **digitação do próximo comando**, não do **julgamento**.
Cinco gates continuam parando o fluxo, e a skill os lista em tabela logo no topo:

- aprovação da SPEC antes de implementar;
- Pare e Pergunte (ADR-0015) — conteúdo inventável;
- deploy de produção (é do `/lancar`, com SIM explícito sem default);
- mudança irreversível (ADR-0024);
- merge do PR.

Isto é deliberado e é o ponto que separa L4 de "sem humano": o paper defende times híbridos
onde *"humans set direction, agents do the implementation, and clear handoff protocols
govern the boundary"*. A imagem de referência diz que o time confia mais no harness que na
**revisão individual de código** — o que sai é a leitura de cada diff, não a decisão.

### Escalação e linhagem

Para e devolve ao usuário em: duas falhas materialmente iguais na mesma etapa (mesma regra
que o `/lancar` e a ponte já usam), orçamento esgotado, achado que exige decisão fora da
SPEC, ou qualquer gate da fronteira de aprovação.

O registro vai para `docs/specs/entregas/ENTREGA-<SPEC>-<data>.md` com a tabela de rodadas —
**incluindo as que falharam**. Rodada escalada é evidência, não vergonha apagada; é o que
impede a próxima entrega de repetir a mesma tentativa. Mesma disciplina da linhagem do
`/otimizar`.

## Consequências

**Positivas**

- Os 16 verbos viram linha de montagem. É a diferença entre uma bancada com boas ferramentas
  e uma fábrica.
- O maior salto isolado de autonomia medida (ADR-0021): um ciclo de `entregar` que fecha
  sozinho registra 1 prompt e 0 intervenções.
- O usuário do plugin passa a ter o que só quem rodava a ponte Hermes tinha — sem depender
  de VPS, Telegram ou host 24/7.
- A ponte Hermes fica mais simples: `kairos-forge-ciclo` pode passar a chamar
  `claude -p "/kairos-forge:entregar …"` em vez de reimplementar a sequência.

**Negativas e limites, declarados**

- **É orquestração em prosa, não código.** A skill descreve o loop; quem executa é o modelo.
  Diferente do `guardrail.py`, aqui não há garantia determinística de que o orçamento será
  respeitado — a mitigação é o orçamento anunciado ao usuário na largada, o que torna o
  estouro visível.
- **Consome mais tokens que a sequência manual**, porque o contexto de todas as etapas
  atravessa o ciclo. Em compensação, elimina o custo de recontextualizar a cada comando novo.
- **Sobreposição de gatilho com `/mobilizar` e `/rodar`.** Mitigada pela fronteira explícita
  na `description` e pela seção "quando NÃO usar": `entregar` é o ciclo inteiro, as outras
  são etapas. O eval de roteamento da Laura (ADR-0025) ganha casos para essa fronteira.
- **Duas rodadas é um default, não uma verdade.** Projetos com suite lenta podem querer 1;
  refactors grandes, 3. O número é declarado e ajustável, e é isso que o torna honesto.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Fazer o `/validar` corrigir o que encontra | Quebra a independência avaliador/gerador, que é o princípio da Alice e a razão de a validação valer alguma coisa. O arco preserva a separação: validar acusa, o agente do domínio corrige |
| Deixar o arco só na ponte Hermes | Entrega o principal ganho de autonomia apenas a quem roda VPS + Telegram. A fábrica é o produto; a ponte é uma superfície |
| Um script Python orquestrando as skills | Skills são carregadas por match de tarefa no CLI, não por chamada programática. Um orquestrador externo precisaria de `claude -p` por etapa — que é exatamente o que a ponte faz, e perde o contexto entre etapas |
| Estender o `/mobilizar` em vez de criar skill nova | `mobilizar` é execução paralela de uma SPEC; o arco começa antes (especificar) e termina depois (PR). Empilhar as duas coisas numa skill só faria uma description impossível de rotear |
