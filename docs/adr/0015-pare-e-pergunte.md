# ADR-0015 — Pare e Pergunte: condições de parada contra invenção de conteúdo

**Status:** Aceito
**Data:** 2026-07-28

## Contexto

Análise de duas skills do ecossistema Replit-Orchestrator do usuário (`briefing-interviewer` e `pm-requirements-expert`) — o mesmo ecossistema cujo `briefing.md` já inspirou o ritual `verificado:` do `/validar` (ADR-0005). Avaliação contra o catálogo atual:

- **Já coberto (e com contrato mais rico):** a entrevista de discovery é o `/onboardar` + `/especificar` + Joana (elicitação, ADR-0014); o checklist do `briefing.md` é subconjunto da tabela de requisitos da SPEC (IDs, prioridades, critérios, gates, Verificação); o PRD é a SPEC; BDD Given/When/Then é o WHEN/THEN/SHALL do Caio; "não apagar itens, estado só com prova" é o ritual `verificado:`.
- **Genuinamente novo e valioso:** três disciplinas que a fábrica não tinha sistematizadas.

## Decisão

A partir da **v0.11.1**, três absorções — como mudanças de prompt, sem skill nem agente novos:

### 1. Tabela "Pare e Pergunte" (condições de parada contra invenção de conteúdo)

O modo de falha que as duas skills atacam: quando a única forma de completar a tarefa é **inventar conteúdo que aparecerá ao usuário final como verdade**, o agente inventa — e a dívida é silenciosa até alguém de fora achar o erro. A tabela vira disciplina em três pontos:

- **`/especificar`**: antes de escrever requisito, checar as condições — conteúdo institucional/jurídico sem fonte oficial, integração sem provedor definido, cálculo de negócio sem fórmula e caso-teste, dado pessoal real não confirmado, "igual ao site X" sem referência acessível, asset de terceiro sem decisão de hospedagem. Caiu numa condição → **pergunta obrigatória ao usuário**, nunca preencher com achismo.
- **Joana (`apoio-joana-elicitacao`)**: as mesmas condições na entrevista de elicitação — é onde o vago aparece primeiro.
- **`anti-drift.md`**: teammates ganham a condição na lista "Quando bloquear" — conteúdo que apareceria como verdade sem fonte confirmada é bloqueio, não criatividade.

A versão do forge é **genérica/MIT**: as condições regulatórias específicas das skills originais (página obrigatória por lei, texto de legislação) degradam para a regra geral "conteúdo institucional/jurídico sem fonte oficial = bloqueio + recomendação de kairos-ai quando for domínio regulado".

### 2. Apetite vs escopo (Shape Up) no auto-sizing do `/especificar`

Apetite **fixo**, escopo **variável**: a pergunta da classificação deixa de ser só "que tamanho isso tem?" e passa a incluir "quanto vale investir nisso?" — e o escopo é cortado para caber no apetite, não o contrário.

### 3. Working Backwards no espelhamento do `/especificar`

Ao espelhar o entendimento (passo 4), o arquiteto inclui: "se isso fosse lançado hoje, o que o usuário veria funcionando?" — o critério de sucesso visível vira âncora dos requisitos P1.

## O que deliberadamente NÃO foi adotado

- **O contrato `briefing.md` na raiz + painel.** Seria estado duplicado da SPEC — exatamente a "planilha paralela" que o ADR-0013 rejeitou para o quadro vivo. O checklist com `verificado:` já vive na SPEC; o quadro vivo já renderiza o progresso. Quem usa o painel Monitor do Replit-Orchestrator continua usando as skills originais dele — os dois convivem no mesmo projeto sem conflito, pois escrevem em arquivos distintos.
- **Pasta `docs/prd/`.** A SPEC é o PRD da fábrica; duas fontes de requisito dessincronizam.
- **Skill de entrevista dedicada.** `/onboardar` (projeto), `/especificar` (feature) e Joana (elicitação) já cobrem as três altitudes.

## Versão

Mudanças de prompt em skill/agente/template: bump **patch** 0.11.0 → **0.11.1**.

## Consequências

Boas: o anti-padrão mais caro do vibe coding (conteúdo inventado com cara de verdade) ganha guarda explícita nos três pontos onde nasce — especificação, elicitação e execução paralela. Custos: mais uma tabela para os prompts carregarem; mitigado por ser curta e compartilhar a mesma redação-base.

## Alternativas consideradas

1. **Adotar `briefing.md` como contrato adicional.** Rejeitado: estado duplicado (ver acima).
2. **Criar skill `entrevistar`.** Rejeitado: três skills/personas já cobrem o fluxo; a lacuna era a disciplina, não o fluxo.
3. **Só documentar, sem mudar prompts.** Rejeitado: condição de parada que não está no prompt não para ninguém.
