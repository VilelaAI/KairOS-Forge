# ADR-0038 — Instruções enxutas: descriptions curtas, skill como roteador e menos paradas

- **Status:** aceito
- **Data:** 2026-09-06
- **Versão:** v0.31.0

## Contexto

Em setembro de 2026 a equipe do Codex publicou um guia de revisão de skills e prompts para
os modelos novos (Eric Provencher, *Rethinking skills and prompts for GPT-6 Astra*). O
argumento serve a qualquer CLI que este plugin atende, porque o mecanismo é o mesmo nos
quatro: **o que o modelo vê em toda sessão custa em toda sessão**, e instrução escrita para
um modelo que precisava de muleta vira freio num modelo que não precisa.

Cinco pontos do guia se aplicam diretamente a um plugin de 71 agentes e 18 skills:

1. A `description` de cada skill e agente é carregada como metadado na largada. Quando a
   soma não cabe, o Codex **encurta** as descriptions — o modelo passa a ver menos de cada
   uma e escolhe pior. Description longa não é "mais clara"; é menos lida.
2. Skill útil tem **divulgação progressiva**: raiz curta que roteia, detalhe em `references/`
   que só custa quando é chamado.
3. Skill escrita como itinerário passo a passo **superconstrange** um modelo que entende
   nuance; a instrução deve dizer o que importa e onde olhar, não ditar cada movimento.
4. Lembrete para rodar teste e revisar era necessário em modelo que não fazia isso sozinho.
   No modelo que faz, o mesmo lembrete produz teste desnecessário e ruído de contexto.
5. Fronteira de decisão escrita com força demais vira parada real num modelo que **respeita
   fronteiras** — ele para onde o autor ficaria feliz que continuasse.

A auditoria do plugin contra esses pontos, medida do filesystem:

| O que | Antes | Problema |
|---|---|---|
| Descriptions das 18 skills | 8.816 chars, 60–106 palavras cada | Maior custo estático do plugin, fora do orçamento do ADR-0027 (o próprio ADR registrava isso como limitação) |
| Descriptions dos 71 agentes | 19.042 chars | Idem. As 31 de apoio começavam com "Agente de apoio do squad…" + "NÃO implementa código" + lista de sinais — e os trios de cada squad tinham descriptions **idênticas**, então o roteamento entre Álvaro, Félix e Lúcia era cego |
| `references/` | 2 de 18 skills | O teto de 500 linhas era respeitado como teto, não como desenho de roteador; a `mobilizar` tinha 485 linhas lidas inteiras no caso simples |
| Hook `PostToolUse` pedagógico | A cada `Edit` em arquivo de produção | "Chame Ricardo, rode validar e revisar" — a mesma intenção já vive na Definition of Done da Laura, nas regras absolutas do `CLAUDE.md.template` e no anti-drift. Tripla redundância, cobrada a cada edição |
| Boilerplate nos agentes | 69k de 206k chars (34%) | "Como você responde" (quatro bullets "Sempre…"), "Stack default" e a nota do kairos-ai repetidos em cada um dos 71 arquivos |
| Paradas | "Checkpoint a cada 3 tasks" no anti-drift; três checkpoints do planejamento sempre | A contagem de 3 tasks é de antes de o quadro existir (ADR-0035); em feature simples, "2-3 abordagens com trade-offs" e duas rodadas de confirmação antes da SPEC são teatro |

O que **não** precisava mudar, e o ADR registra para não ser refeito: o ADR-0019 já dá
default recomendado a decisão reversível; o ADR-0015 restringe o Pare e Pergunte a conteúdo
inventável; o anti-drift tem lista fechada de motivos para bloquear; a definição de
conclusão (Done when, DoD, estado terminal do `ciclo.py`) já existe — o guia pede
exatamente isso para o modelo não parar cedo.

## Decisão

**1. Description é: o que faz, quando usar, uma negativa de roteamento.** Dono, artefatos,
lista de sinais e resumo do fluxo vão para o corpo, que só custa quando o ativo é invocado.
Teto por description (skill ≤ 300 chars, agente ≤ 260) e **a soma das descriptions entra no
orçamento estático** do `release.py check` — fecha a limitação declarada no ADR-0027. Os
trios de apoio ganham descriptions distintas, com a fronteira entre irmãos explícita
("pre-mortem é do Álvaro; red team, do Félix"). O eval de roteamento (`rodar.py`) deixa de
truncar o catálogo em 110 chars: a Laura passa a ver a description inteira, como o CLI vê.

**2. As cinco skills maiores viram roteador + `references/`** — `mobilizar`, `especificar`,
`entregar`, `auditar`, `avaliar`. A raiz mantém propósito, quando não usar, o fluxo com os
pontos de decisão, **todos os comandos** e um índice que diz quando ler cada referência.
Rubricas, templates, modos alternativos, justificativas e histórico de ADR saem da raiz
**verbatim** para `references/`. Nada foi descartado; o que mudou é quando cada parte custa.

**3. O hook pedagógico avisa uma vez por sessão**, no primeiro arquivo de produção editado,
marcado por `session_id`. Não foi removido: é o único ponto onde um usuário que nunca leu a
skill descobre que a DoD existe. Uma vez por sessão é o custo de um aviso; a cada edição era
o custo de um vício.

**4. O boilerplate das personas vira um parágrafo.** Os quatro bullets de "Como você
responde", a seção "Stack default" e a nota do kairos-ai (nos de apoio) viram um parágrafo
com o mesmo conteúdo — PT-BR, primeira pessoa, apoio complementa e não substitui, stack é
default e adapta sem perguntar, regulado é kairos-ai.

Por que **não** foi um preâmbulo gerado pelo sync: o Claude Code carrega `agents/` direto
(o marketplace aponta para `plugin/`, cópia byte a byte). Não há etapa de geração onde
injetar um preâmbulo sem transformar `agents/` em artefato gerado — o que contradiz "agents/
é canônico" e cairia na classe `gerado` do guardrail (ADR-0037). Comprimir em 71 lugares foi
o custo de manter o canônico canônico.

**5. Parar onde a parada compra algo.**

- Anti-drift: **checkpoint por onda, não por contagem**. O worker não puxa tarefa; a onda
  vem do quadro (`quadro.py prontas`) e o checkpoint da Laura acontece entre ondas. A regra
  "a cada 3 tasks" era de antes de o quadro existir.
- `/especificar` e `/entregar` em sessão: feature **Pequena** (classificação do auto-sizing da Laura) segue
  com o default recomendado (ADR-0019) nos checkpoints de entendimento e abordagem — o
  entendimento espelhado e a abordagem recomendada vão numa mensagem só, com a premissa
  registrada na SPEC, e o fluxo continua salvo objeção. As "2-3 abordagens com trade-offs"
  ficam para Médio, Grande e Complexo. A aprovação da SPEC continua sendo gate sempre.
- **O `ciclo.py` não muda.** Conduzido pelo runner headless, os três estados de gate humano
  permanecem exatamente como o ADR-0033 os desenhou, porque ali ninguém está lendo e a
  premissa errada não é pega de graça. O contrato v1.0 (ADR-0034) fica intacto; a mudança é
  só na prosa da sessão, onde o usuário está presente e a segunda parada não compra nada.

## Consequências

| O que | Antes | Depois |
|---|---|---|
| Descriptions dos 71 agentes | 19.042 chars | 8.786 chars (máx. 195) |
| Descriptions das 18 skills | 8.816 chars | 3.322 chars |
| `agents/` total | 206k chars | 167k chars |
| Skills com `references/` | 2 | 7 |
| Raiz das cinco skills reestruturadas | 1.743 linhas | 894 linhas |
| Hook pedagógico | a cada edição | uma vez por sessão |

**Positivas**

- No Codex, as descriptions cabem sem encurtar — o modelo vê o critério de escolha inteiro.
- A soma das descriptions vira catraca no CI: skill nova com description de parágrafo falha
  no `check`, não seis meses depois quando o roteamento piorou.
- Os trios de apoio passam a ser roteáveis entre si.
- Uma sessão que só corrige um typo carrega ~4k tokens a menos de metadado.

**Negativas e limites, declarados**

- **Description curta é aposta de roteamento.** A negativa explícita de cada uma é o que
  sustenta a fronteira; o eval de roteamento da Laura é o teste. Ele precisa de CLI
  autenticado e **não rodou neste ambiente** (sem credencial) — roda no merge para `main`
  pelo CI. Se cair abaixo de 90%, a description que causou a queda volta a ganhar a palavra
  que faltava, uma por vez, e nunca o parágrafo inteiro.
- **Guias servem a modelos diferentes.** Skill de repositório orienta o agente de qualquer
  contribuidor, com qualquer modelo. A raiz curta assume que o modelo lê o índice e busca a
  referência quando precisa; um modelo que não faz isso perde o detalhe que antes vinha de
  graça. O sinal a observar é `/validar` reprovando por passo que a raiz só aponta.
- **A compressão do boilerplate ainda é 71 cópias.** Reduziu, não eliminou. Eliminar exige
  decidir que `agents/` é gerado — decisão separada, com ADR próprio, se algum dia valer.
- **Uma vez por sessão depende de `session_id`** no input do hook e de `$TMPDIR`. Sem
  `session_id`, o marcador cai em `sem-sessao` e o aviso passa a ser uma vez por máquina até
  o reboot — degrada para menos aviso, nunca para mais.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Remover o hook pedagógico | A DoD estaria só em texto que quem nunca leu a skill não vê. Uma vez por sessão custa um aviso |
| Preâmbulo comum injetado pelo sync | Transforma `agents/` em gerado; contradiz o canônico e o guardrail do ADR-0037 |
| Flag `--porte simples` no `ciclo.py` pulando os dois gates | Muda o contrato v1.0 e reabre o que o ADR-0033 fechou: em headless não há quem leia a premissa antes de o orçamento queimar |
| Descriptions só mais curtas, sem teto no `check` | Foi assim que chegaram a 106 palavras: por adição incremental, cada uma pequena. Sem catraca a deriva volta |
| Reestruturar as 18 skills de uma vez | As cinco maiores eram 60% do material; as outras cabem em 110–250 linhas e não têm modo alternativo para separar. Fazer todas seria custo sem o ganho, e a catraca de 500 linhas segura o resto |
