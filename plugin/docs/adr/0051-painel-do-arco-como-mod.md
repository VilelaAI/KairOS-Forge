# ADR-0051 — O painel do arco como mod do Claude Code

- **Status:** aceito
- **Data:** 2026-11-05
- **Versão:** v0.44.0

## Contexto

O `/kairos-forge:entregar` roda o arco inteiro numa conversa:
especificar → construir → validar ⇄ corrigir → revisar ⇄ corrigir → PR.
O estado mora em `.agents/ciclo/` e `.agents/quadro/`, e o `painel.py` sabe desenhá-lo
(ADR-0013/0032). Mas para ver o painel, a pessoa precisava pedir, e pedir no meio de um
arco custa um turno do modelo ou um terminal ao lado. O gate humano chegava como texto no
fim de uma resposta longa, fácil de passar batido. O `painel.py --caixa` (ADR-0044) junta o
que espera por alguém, mas também só responde quando perguntado.

O Claude Code passou a carregar **mods**: um plugin pode nomear em `hooks/hooks.json`
(chave `modules`) um módulo TypeScript que engancha eventos do motor e desenha na interface
(um painel ao lado da conversa, uma faixa acima do prompt, a linha de status, toasts) e
registra comandos que respondem sem turno do modelo. Roda no terminal, no desktop e no
VS Code. No `-p` e na nuvem os ganchos rodam, mas nada é desenhado.

## Decisão

O primeiro mod da fábrica é o **painel do arco**, `hooks/painel.tsx`, no próprio plugin. É
pelo `$.plugin.root` que ele acha o `scripts/painel.py`. Tem quatro peças, todas de leitura:

- **`/forge-painel`** abre o painel ao lado da conversa. Para cada SPEC, mostra:
  - o progresso;
  - o trilho especificar → construir → validar → revisar → PR, com a fase marcada;
  - as fichas de cada gate e o motivo da escalação;
  - as colunas dos requisitos, com o aviso de "concluído sem `verificado:`";
  - o veredicto de cada relatório.

  Mostra também as mobilizações do quadro e, em cima, a caixa de entrada. Onde nenhuma
  superfície desenha, o mesmo quadro volta como texto.
- **A faixa acima do prompt** aparece só quando a caixa tem item: o primeiro, a contagem
  dos outros, `Ver` e `Ocultar`. Ocultar vale até a caixa mudar. Quando um gate humano novo
  chega, sai um toast, uma vez por gate.
- **`/forge-caixa [--github]`** devolve o `painel.py --caixa` como texto, na hora, até com um
  turno rodando.
- **A linha de status** diz o ciclo em curso e quantos itens esperam: `kairos-forge · SPEC-007
  validando · 📥 1`.

### Só aperta, nunca afrouxa

O mod não decide nada. Não engancha `tool.check`, não aprova nem recusa chamada, não
reescreve prompt nem chamada, não escreve arquivo e não roda nada além do `painel.py`, que
só lê (o `--html`, único modo que escreve, nunca é passado).

Os dois ganchos em `tool.call` têm um matcher só para o que muda o arco:
- o `ciclo.py` ou o `quadro.py` pelo shell;
- uma escrita em `docs/specs/` ou `.agents/ciclo|quadro/`.

Cada um chama `next(e)` com a chamada inteira e só depois pede uma leitura nova. O `.catch`
deixa passar mesmo quando o gancho falha, porque um mod de leitura que derruba uma
ferramenta seria pior que painel nenhum. O `test_mod_painel.py` trava isso no código: lista
as chamadas proibidas e confere o `.catch` de cada gancho.

### A regra fica no Python

O mod só desenha. Duas coisas que ele precisava saber passaram a vir prontas do
`painel.py --json`:
- a **fase** de cada ciclo, de uma tabela fechada de estados (estado novo no `ciclo.py` sem
  fase falha o teste). O escalado fica na fase de onde parou;
- as **colunas** de cada SPEC, com a regra do `verificado:`.

Assim o terminal, o HTML e o mod não divergem: "se o número aqui está errado, o bug está na
fonte".

### CLI antigo continua inteiro

O mod mora no plugin principal porque nenhum CLI conhecido quebra com ele. Foi testado com
um plugin de sonda e com o próprio plugin da fábrica, carregados de verdade, com a API
desligada:

| Claude Code | Com a chave `modules` no `hooks.json` |
|---|---|
| 2.0.77 | Igual sem ela: o plugin carrega, com 19 skills, 71 agentes e os hooks |
| 2.1.207 | Ignora o módulo e roda os hooks de settings |
| 2.1.286 e 2.1.318 | Rodam os dois |

O que quebrava era outra coisa: o campo `types` no `plugin.json`, que o guia de mods
sugere para o contrato de estado. O 2.0.77 recusa o manifesto inteiro por ele
("Unrecognized key"), e com o manifesto iriam os guardrails da fábrica. Então o contrato
fica em `types/index.d.ts`, onde o `claude plugin validate` o acha por convenção, e o
`plugin.json` não muda. O teste trava as chaves do manifesto.

## Consequências

- Arquivos novos:
  - `hooks/painel.tsx` e `hooks/vista.ts`: o módulo e as funções puras de vista;
  - `types/index.d.ts`: o contrato do `$.state`, espelhado em `plugin/`;
  - `tests/painel.test.tsx`: os testes do kit `claude plugin test`. Não vão para `plugin/`,
    porque quem instala não precisa deles;
  - `tsconfig.json`: igual ao que o motor escreve ao carregar o mod em desenvolvimento.
- O CI ganha o job `mod-painel`: `claude plugin validate` (raiz e `plugin/`) e
  `claude plugin test .`, com o Claude Code pinado em 2.1.318, sem chave de API.
  - Os testes rodam o painel nas quatro superfícies, a faixa, o toast, os dois comandos, a
    falta de Python e a chamada de ferramenta passando inteira.
  - Cada um dos dez estragos plantados no mod é acusado por pelo menos um teste.
- O CRAP do `qualidade.py` (ADR-0045) não se mede no TypeScript do mod: o kit de teste não
  gera relatório de cobertura, então toda função sai com 0%. Para o mod, a régua é a
  mutação, rodada com o `claude plugin test` como comando. O desenho saiu de dentro do
  `register` (CC 47 → 6), e a maior função ficou com CC 14.
- A leitura custa duas execuções do `painel.py` (cerca de 100 ms cada). Ela roda no início
  da sessão, no fim de cada turno, depois de cada chamada que muda o arco e nos botões. Uma
  leitura por vez: o pedido que chega durante uma leitura vira mais uma, depois dela.
- O mod precisa do `python3` no PATH, como os hooks. Sem ele, o painel diz o porquê, a
  faixa e o status se calam, e a última leitura boa continua na tela.
- Só no Claude Code. No Codex, no OpenCode, no Cursor e no Tucano o painel continua sendo
  o `painel.py` no terminal.

## Alternativas consideradas

- **Um plugin separado, `kairos-forge-painel`.** Recusado. Instalado do marketplace, cada
  plugin vira uma cópia própria no cache e o mod não acharia o `scripts/painel.py` do outro.
  Copiar os scripts para ele seria um segundo lugar com o mesmo número.
- **A regra da fase e das colunas no TypeScript.** Recusado. Seria uma segunda
  implementação do que o `painel.py` já decide e testa.
- **Ler `.agents/ciclo/` direto com `$.fs`.** Recusado pelo mesmo motivo. O caminho do
  checkout principal num worktree (ADR-0024) já é resolvido pelo `execucao.py`.
- **Atualizar por relógio.** Recusado. Rodar Python a cada poucos segundos com o arco
  parado é custo sem leitura nova. Os eventos que mudam o arco já passam pelo motor.
- **Botão que responde o gate preenchendo o prompt.** Adiado. O gate já é uma pergunta na
  conversa, e o botão só copiaria o nome dele.
- **Pausar a faixa 3 na execução** (segurar `tool.call` até uma pessoa liberar). Fica para
  o próximo mod. Aquele aperta uma regra e precisa de desenho próprio; este só mostra.
