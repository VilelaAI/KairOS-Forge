# ADR-0055 — A pausa da faixa 3 no Cursor

- **Status:** aceito
- **Data:** 2026-11-05
- **Versão:** v0.48.0

## Contexto

O ADR-0052 fez a chamada que um revert não desfaz parar por uma pessoa durante o arco. No
Claude Code, quem pergunta é um mod, porque o `ask` de um mod é de uma pessoa: nenhum
classificador o aprova, e sem pessoa ele vira recusa. Nos outros CLIs não havia pausa, e
o ADR deixou anotado que o Cursor tem `permission: "ask"` no dialeto de hooks dele e
poderia receber o mesmo `guardrail.py faixa3`.

Antes de ligar, a pergunta era se esse `ask` é de uma pessoa. A documentação do Cursor diz
que `ask` pede aprovação. O fórum diz mais:

- **Cursor 3.21.16 (out/2026).** Um hook de `beforeShellExecution` que responde `ask`
  ganha a pergunta nos modos Allowlist e Run Everything. No modo Auto-review, quando o
  classificador do próprio Cursor acha o comando seguro, a pergunta é ignorada e o
  comando roda. `deny` vale nos três modos. A equipe do Cursor confirmou e recomendou
  responder `deny` para o que não pode rodar sem revisão. Até a data deste ADR, não há
  correção.
- **Relatos anteriores, no mesmo sentido:** a allow-list passando por cima do `ask`
  (dez/2025), o `ask` "sem efeito prático" (fev/2026), o shell em sandbox rodando o
  comando assim mesmo (mar/2026) e um pedido de veredicto autoritativo dos hooks
  (jul/2026).

Pela regra do ADR-0052, uma pergunta que um classificador pode responder no lugar da
pessoa não é a pausa da faixa 3.

A leitura também achou duas lacunas no que já existia:
- **O `beforeMCPExecution` do Cursor manda `tool_input` como texto JSON.** O
  `normalizar_payload` reconhecia o Cursor pela falta do `tool_input`. Com ele presente, o
  payload passaria por um do Claude Code e a resposta sairia no dialeto errado. Hoje
  nenhum hook de MCP estava ligado, então era só latente.
- **O `faixa3` procurava o ciclo aberto no `cwd` do payload.** O ciclo mora na raiz do
  projeto. Um comando rodado numa subpasta (`cd infra && terraform apply`, ou o `cwd` que o
  Cursor manda) não achava o ciclo, e a pausa não acontecia. Isso valia também para o
  Claude Code.

## Decisão

### No Cursor, a pausa nasce como recusa com o cartão

O `.cursor/hooks.json` gerado passa a chamar `guardrail.py faixa3`:
- no `beforeShellExecution`, ao lado do `comando`;
- num `beforeMCPExecution` novo.

O Cursor junta as respostas dos hooks do mesmo evento: `deny` vence `ask`, que vence
`allow`. O piso e a pausa ficam em entradas separadas.

O `faixa3` responde no dialeto do Cursor:

| Situação | Resposta |
|---|---|
| A chamada não para | `{"permission": "allow"}`. Uma resposta fora do esquema bloqueia a ação no Cursor, e o `{"pausa": false}` que o mod lê travaria todo comando |
| Para, padrão | `deny` com o cartão |
| Para, com `"faixa_3_cursor": "perguntar"` em `.agents/guardrails.json` | `ask`, com o cartão na pergunta, para quem não usa o Auto-review |

O cartão da recusa diz:
- o efeito, e que um revert não o desfaz;
- o ciclo e o estado em que ele está;
- que, no Cursor, a pergunta não chega a uma pessoa em todo modo;
- o que o agente faz: não contorna, registra o `ciclo.py escalar` com o motivo, mostra o
  comando à pessoa e espera.

Quem roda a ação é a pessoa, no terminal dela. Ou ela liga a pergunta, no arquivo que só
ela escreve.

O evento da pausa na trajetória ganha `decisao` (`deny` ou `ask`) e `cli`. O
`telemetria.py resumo` segue contando as pausas por efeito.

### O MCP do Cursor, normalizado

O payload do Cursor passa a ser reconhecido por ter `conversation_id` e não ter
`tool_input` em objeto.
- **O `tool_input` em texto vira objeto.** JSON ilegível, ou que não é objeto, vira `{}`.
- **A ferramenta ganha o nome do Claude Code:** `mcp__<servidor>__<ferramenta>`, ou
  `Bash` para o shell. A mesma regra serve aos dois CLIs.
- **A linha que lança um servidor stdio fica de fora.** Ela vem em `command`, mas não é
  shell do agente, e não é julgada como tal.

### A raiz é a pasta com `.git` mais próxima

O `faixa3` sobe do `cwd` do payload até a pasta com `.git` antes de procurar o ciclo e o
quadro. Daí, o worktree ligado já resolvia para o checkout principal (ADR-0048).

## Prova

- **Testes.** `test_faixa3.py` passa de 17 para 30 testes:
  - a subpasta, no Claude Code e no Cursor;
  - o `allow` no esquema fora do arco e no que passa dentro dele;
  - a recusa com o cartão e o evento (`deny`, `cursor`);
  - o `perguntar` que vira `ask` para a pessoa;
  - o MCP pelo nome com `tool_input` em texto;
  - a linha que lança o servidor stdio, que não é o comando;
  - o `tool_input` ilegível ou que não é objeto;
  - o MCP sem servidor;
  - o payload do Claude Code intocado;
  - o shell do Cursor que vira `Bash`;
  - o sync, que liga a pausa no shell e no MCP.
- **Prova negativa.** Rodados contra a `main`, 12 dos 13 testes novos falham. O que passa
  é a guarda de que o payload do Claude Code continua intocado.
- **O que não foi exercitado.** Não rodei um Cursor de verdade, porque não há Cursor no
  ambiente de trabalho. A precedência entre hooks, o esquema da resposta e o
  comportamento do `ask` por modo vêm da documentação do Cursor e do relato confirmado no
  fórum, não de uma rodada minha.

## Consequências

- **No Cursor, ação irreversível no arco não roda pelo agente.** Ela fica com a pessoa. É
  mais atrito que a pergunta do Claude Code, e é o preço de não haver, no Cursor, uma
  pergunta que só uma pessoa responde.
- **A pergunta é opt-in e tem risco.** Um time em Allowlist ou Run Everything que liga
  `"faixa_3_cursor": "perguntar"` ganha a pergunta. Se mudar para o Auto-review depois, a
  pergunta para de valer sem aviso. A chave fica no arquivo que só o humano escreve, com
  o aviso ao lado.
- **Nenhum contrato muda.** O JSON que o mod do Claude Code lê ganha `decisao`, que ele
  ignora.
- **Codex, OpenCode e Tucano** seguem sem pausa. A regra é da skill, cumprida pelo agente.

## Alternativas consideradas

- **`ask` como padrão no Cursor.** Recusado. No Auto-review, o classificador responde no
  lugar da pessoa, e é exatamente o que o ADR-0052 recusou no `ask` do hook de settings do
  Claude Code.
- **`failClosed: true` no hook da pausa.** Recusado. Um Python quebrado travaria todo
  comando de shell. O ADR-0052 já escolheu falhar aberto, registrando o erro, pela mesma
  razão.
- **`matcher` no hook para rodar só em comandos suspeitos.** Recusado. Seria uma segunda
  cópia da regra, em regex, fora dos testes. O `faixa3` custa um processo Python por
  comando, o mesmo do `comando`, que já roda.
- **Juntar a pausa ao modo `comando`.** Recusado. Misturaria o piso, que bloqueia sempre,
  com a pausa, que depende do arco. Como entradas separadas, o próprio Cursor junta as
  respostas pela precedência.
- **Descobrir o modo do Cursor e responder `ask` só onde ele vale.** Não dá: o payload do
  `beforeShellExecution` não diz o modo de execução.
