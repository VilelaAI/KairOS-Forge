# Trilhas por tema (modo guiado — ADR-0013)

Referência do passo 1.2 de `/kairos-forge:especificar`. Leia quando a feature casar com
um tema conhecido — auth, pagamentos, painel-admin, api, seed-dados — antes de começar a
interrogação do zero.

## 1.2. Trilhas por tema (modo guiado — ADR-0013)

Antes de interrogar do zero, cheque se a feature casa com uma trilha em `${CLAUDE_PLUGIN_ROOT}/templates/trilhas/` (índice em `TRILHAS.md`): auth, pagamentos, painel-admin, api, seed-dados. Sinais são diretos — "quero login" → trilha-auth; "checkout"/"cobrar" → trilha-pagamentos; "painel"/"admin" → trilha-painel-admin.

Se casar, **parta da trilha em vez do zero**: os requisitos típicos viram rascunho da tabela (renumerados pro projeto), as "perguntas que o arquiteto DEVE fazer" entram na interrogação, os riscos alimentam o `/kairos-forge:analisar-ameacas` (obrigatório nas trilhas marcadas como sensíveis), e as tarefas/gates sugeridos são o ponto de partida do plano. **Trilha é rascunho, não fôrma**: o arquiteto adapta ao stack (`contextos/stack.md`) e corta o que não se aplica. Pro usuário iniciante, isso é o modo guiado — ele diz o tema, a fábrica já sabe o caminho e o que perguntar.
