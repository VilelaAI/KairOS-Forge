# ADR-0045 — Deixar certo: CRAP, duplicação e mutação no diff, e atacar a premissa no arco

- **Status:** aceito
- **Data:** 2026-10-31
- **Versão:** v0.38.0

## Contexto

O [ub-mode](https://github.com/unclebob/ub-mode), de Robert C. Martin, é uma skill de
disciplina para agente que escreve código, em três partes: **fazer funcionar** (TDD,
menor mudança, dados antes da lógica, redesenho em vez de enxerto, fronteira, idempotência),
**deixar certo** (causa e não sintoma, unidade verificável, teste de comportamento, refatoração
com comportamento fixado) e **prática** (log, contexto enxuto, limpeza de worktree, commit
pequeno com porquê e prova). O que separa o ub-mode de uma lista de bons conselhos são três
ferramentas que ele usa como gate, do mesmo autor e sob licença 0BSD: o
[crapper](https://github.com/unclebob/crapper) (CRAP por função: `CC² × (1 − cobertura)³ + CC`,
abaixo de 10), o [dryer](https://github.com/unclebob/dryer) (duplicação estrutural por
Jaccard de impressões, abaixo de 0,8) e o [mutator](https://github.com/unclebob/mutator)
(mutação: mutante que sobrevive é teste que não percebe o comportamento mudar).

O pedido foi absorver o ub-mode no KairOS e, se possível, por fluxo determinístico. A
auditoria princípio a princípio mostrou que a fábrica já cobria a maior parte, em prosa ou
em código, e que faltavam exatamente as partes que o ub-mode entrega a ferramentas:

| Princípio do ub-mode | O que a fábrica tinha | A lacuna |
|---|---|---|
| TDD: ver o teste falhar pelo motivo esperado | `prova.py pre-patch`: teste novo roda na base sem o patch e precisa falhar (ADR-0039) | nenhuma no gate; a ordem "teste primeiro" estava implícita no anti-drift |
| Menor mudança, uma decisão num lugar, subtrair antes de somar | autocrítica estruturada contra o "Pronto quando" (anti-drift 6.1) | não estava escrito |
| Redesenhar em vez de enxertar; dados antes da lógica; fronteira; idempotência | `/especificar` (abordagens), `/diagnosticar` audita idempotência e fronteira no sistema do usuário | não chegava ao teammate que constrói |
| Atacar a premissa depois de duas correções frustradas no mesmo gate | `/entregar` mandava escalar em "duas falhas materialmente iguais" — em prosa, julgado pelo próprio agente | **nenhum mecanismo**: com orçamento maior, a terceira correção saía no mesmo embalo das duas |
| Causa raiz, unidade verificável | correção roteada ao agente responsável, gates do barato ao caro (ADR-0023/0039) | nenhuma |
| Teste de comportamento ("passaria com a função devolvendo nada?") | `prova.py` pega o teste que passa sem a mudança; não pega o teste que passa com a mudança **errada** | **nenhum gate** |
| CRAP < 10 por função | nenhum | **nenhum gate** |
| Duplicação < 0,8 | nenhum | **nenhum gate** |
| Mutantes mortos, código morto apagado | `/validar` citava "mutação, quando o projeto tiver" | **nenhum gate da fábrica** |
| Refatorar: fixar, mudar, provar | testes de caracterização no `/migrar` (ADR-0041) | fora do `/migrar`, só implícito |
| Log de cada ação e do porquê | telemetria por hook e trajetória (ADR-0021) | nenhuma |
| Contexto enxuto | `/mobilizar` delega, disclosure progressivo das skills (ADR-0035/0038) | nenhuma |
| Limpeza de worktree | worktree descartável removido no `finally` do `prova.py`; worktree por teammate (ADR-0024) | nenhuma relevante para este ADR |
| Commit pequeno com porquê, o quê e prova | Conventional Commits PT-BR e trailer `Fabrica:` (ADR-0044) | o corpo do commit não pedia a prova |

## Decisão

### 1. `scripts/qualidade.py` — os gates de "deixar certo", no diff

Três subcomandos, só stdlib, sempre sobre as funções que o diff tocou (o mesmo diff do
`prova.py`, contra o merge-base, incluindo o que não foi commitado):

- **`crap`** — complexidade ciclomática × cobertura, com a fórmula e as decisões do crapper.
  Python pela `ast`; JS/TS e Go por varredura de texto com comentário e string apagados
  (heurística declarada). Cobertura lida do relatório que a suíte já gera (coverage.py json
  ou xml, LCOV, Cobertura, `go test -coverprofile`), nunca rodada pelo script. Sem relatório,
  CRAP não é inventado: função com CC no limite reprova mesmo assim (CRAP ≥ CC), as outras
  saem `indeterminado`.
- **`duplicacao`** — Jaccard de impressões estruturais (subárvores normalizadas no Python,
  janelas de tokens normalizados no JS/TS e no Go) entre cada função tocada e as demais da
  mesma linguagem. Nome local e literal não contam; chamada, operador e forma contam.
- **`mutacao`** — operadores trocados um por vez nas linhas tocadas, mais o mutante que o
  ub-mode pede por extenso: `return x` → `return None`/`undefined`. Roda num worktree
  descartável do HEAD com o não-commitado aplicado; a suíte tem de passar antes (base
  vermelha não julga mutante); cada mutante tem tempo limite, e o processo inteiro morre
  quando estoura. `--max` e `--teto` limitam o custo; a escolha dos sítios é determinística
  (metade das vagas para retornos, o resto espalhado pelo diff).

Arquivo marcado `linguist-generated` ou `linguist-vendored` no `.gitattributes` fica fora
das três medidas. O forge ganha um `.gitattributes` marcando `plugin/`, `.cursor/`,
`.codex/agents/`, `.opencode/agent/`, `.agents/*/AGENT.md` e o manifesto de ativos — o que
também recolhe esses arquivos no diff dos PRs.

**A catraca do legado.** Medir só o diff resolve metade do problema de brownfield; a outra
metade é a função antiga que o diff toca. Exigir CRAP < 10 de toda função tocada empurraria
o agente para reescritas que ninguém pediu (o oposto de "menor mudança"); não exigir nada
deixaria o legado piorar um `if` de cada vez. A regra fica no meio, como a catraca do
`/otimizar`: a complexidade da mesma função na base vem do `git show`; se ela já estava no
limite ou acima e o diff não a fez subir, o veredicto é `legado_acima` (listado, não
reprova). Piorou, reprova. Melhorou até ficar abaixo do limite, vale a regra cheia.

### 2. Os gates no `/validar`

Passo 4.1 novo, depois dos gates do projeto e do mais barato ao mais caro: `duplicacao`,
`crap`, `mutacao`. CRAP no limite em função nova ou que piorou **bloqueia**; `legado_acima`
é ressalva; par duplicado é ressalva (bloqueia quando o plano mandava reutilizar); mutante
sobrevivente em linha de requisito P1 **bloqueia**, com exceção escrita para mutante
equivalente. O placar entra no `verificado` do bloco `kairos-validacao` — o contrato dos
relatórios não muda.

### 3. Atacar a premissa no `ciclo.py` (contrato 1.2)

Três estados novos, `atacando_premissa_spec`, `atacando_premissa_validacao` e
`atacando_premissa_revisao`, com uma aresta cada (`premissa_escrita` → a correção do mesmo
gate). O ciclo entra num deles na **terceira falha seguida do mesmo gate sem baixar a
contagem de achados** — duas correções frustradas — e só sai com a premissa em uma frase
(`--nota`, ao menos 20 caracteres) que ainda não foi atacada na mesma sequência. Progresso
real e gate verde zeram a sequência. Estado e aresta novos são mudança **menor** pelas
regras do ADR-0034: um laço que segue `resultados_validos` e `proximo_passo` continua
funcionando sem mudança. O contrato vai de 1.1 para 1.2 e é reassinado.

Com o orçamento padrão (2 rodadas), a escalada chega antes da terceira correção; por isso a
instrução de `escalado` passa a pedir a mesma frase para levar ao humano. Os estados novos
aparecem com `--orcamento-<gate>` de 3 ou mais — o caso típico de runner headless, que é
justamente onde ninguém está lendo para notar a repetição.

Para caber, `registrar` e `decidir_orcamento` foram fatiados: as recusas de resultado verde,
a checagem da premissa e os avisos de fonte viraram funções próprias. A complexidade de
`registrar` caiu de 26 para 13 e a de `decidir_orcamento`, de 10 para 6 — a catraca do item
1 aplicada ao próprio diff deste ADR.

### 4. A disciplina no teammate e no Ricardo

O `anti-drift.md` ganha a seção 6.2, "Primeiro funcionar, depois deixar certo", com os
princípios do ub-mode **reescritos nas palavras da fábrica**; a Definition of Done ganha o
item dos três números do diff; e o corpo do commit passa a dizer por quê, o que mudou e como
foi provado. O Ricardo vira o dono dos números do `qualidade.py`. A `description` dele não
muda, então o roteamento da Laura também não.

## Consequências

- **O "deixar certo" vira número com nome.** Função complexa demais para os testes que tem,
  decisão morando em dois lugares e teste que não percebe a linha mudar deixam de depender do
  olho de quem revisa no fim do dia.
- **O próprio script passa nos gates que impõe.** As 93 funções do `qualidade.py` ficam abaixo
  de CRAP 10 (a maior, 8,4) com a cobertura da própria suíte (93%); das 105 funções que o diff
  deste ADR toca, nenhuma forma par duplicado e só `registrar` sai `legado_acima`. A mutação
  sobre o diff, `ciclo.py` incluído, matou 25 de 25 mutantes — depois de os sobreviventes das
  rodadas anteriores apontarem buracos reais nos testes, todos fechados. O mais caro estava no
  `ciclo.py`: mutada para guardar a última contagem de achados em vez da melhor, a marca de
  progresso deixava 2 → 4 → 3 passar por convergência, e nenhum teste percebia. É o tipo de
  achado que justifica o gate.
- **Custo.** Mutação roda a suíte uma vez por mutante. O teto padrão (25 mutantes, 900 s) cabe
  numa rodada do `/entregar` em projeto com suíte de segundos; em suíte lenta, o `/validar`
  reduz o `--max` ou passa um `--comando` focado.
- **Heurística declarada.** JS/TS e Go não têm árvore sintática em stdlib; a varredura acerta
  função, método, arrow com bloco e receptor de Go, e o que ela não entende sai em
  `nao_analisados`. Sítio de mutação simbólico exige espaço em volta, o que deixa de fora código
  sem formatação — preferimos perder sítio a mutar o meio de `->` ou de um genérico.
- **Cobertura velha mente.** Relatório mais antigo que o código tocado sai com aviso, não com
  silêncio.
- **Contrato do `ciclo` em 1.2.** Consumidor que segue `resultados_validos` não muda nada; quem
  compara nome de estado precisa conhecer os três estados novos.

## Alternativas consideradas

- **Copiar o `SKILL.md` do ub-mode como skill nova.** Recusada: o repositório não declara
  licença, e a skill seria uma pasta de prompts ao lado de uma fábrica que já tem metade
  daquilo em código. Ideias, não texto — o mesmo critério dos ADRs 0042 e 0043.
- **Chamar o crapper, o dryer e o mutator diretamente.** São 0BSD e completos (seis
  linguagens, snapshot para o uml-viewer), mas exigem clone ao lado, `.venv` próprio e
  instalam cobertura no projeto. O plugin é só stdlib e não instala nada no projeto do
  usuário (ADR-0001). Quem já usa as ferramentas pode continuar; o `qualidade.py` é a versão
  que roda em qualquer CLI sem instalação.
- **Medir o repositório inteiro.** Recusada: legado que ninguém pediu para mexer viraria
  bloqueio permanente, e o agente seria empurrado para reescrever o que não era tarefa dele.
  A catraca resolve o legado tocado; o resto é assunto do `/diagnosticar`.
- **Bloquear no CRAP do legado tocado.** Recusada pelo mesmo motivo, e porque a correção
  certa (quebrar a função) é decisão de escopo, que no arco é humana.
- **Atacar a premissa só em prosa.** Era o que havia ("duas falhas materialmente iguais →
  escale"), julgado pelo próprio agente sobre a própria repetição — o juiz em causa própria
  que o ADR-0029 tirou do orçamento. Em código, a sequência é contada pelo `ciclo.py`.
- **Exigir a premissa desde a segunda falha.** Recusada: uma correção frustrada é normal; a
  regra do ub-mode é sobre duas, e antecipar faria o agente escrever premissa como ritual.
