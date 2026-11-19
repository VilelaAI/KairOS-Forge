---
name: investigar
description: Acha a causa de um bug, falha intermitente ou lentidão antes de corrigir - laço curto que reproduz, uma hipótese por vez, causa provada e escrita, teste que falha antes e passa depois. Use para "por que quebrou", "debuga", "teste intermitente", "funcionava ontem". Causa já conhecida é o rodar.
---

# Investigar — a causa antes do conserto

Você está sendo invocado porque algo quebra, falha às vezes ou ficou lento, e ninguém sabe
por quê. Quem conduz é o **Ricardo [Testes]** (`ricardo-testes`): ele monta o laço que mostra
o problema e o transforma em teste. Quem escreve o conserto é o dev da área do código. Lentidão
tem o **Vinícius [Performance]** medindo; incidente em produção, o **Sérgio [SRE]** estanca
primeiro, e a investigação vem depois.

**Regra de ouro:** sem laço que mostra o problema, não há conserto; sem causa provada, o
conserto só esconde o sintoma. A ideia vem do corno-skills (sem licença: a ideia, não o texto).

## Quando usar e quando não

- **Use** quando a causa é desconhecida: gate vermelho sem achado que aponte o lugar, teste
  que falha às vezes, "funcionava ontem", erro que só a pessoa viu, o `/entregar` em
  `atacando_premissa_validacao` ou `atacando_premissa_revisao` (ADR-0045).
- **Não use** quando o achado já traz `arquivo:linha` e a causa (o `/validar` e o `/revisar`
  costumam trazer): corrija direto pelo `/rodar` ou pelo loop do `/entregar`. Feature nova é
  o `/especificar`; métrica que se melhora em rodadas é o `/otimizar`.

## Os comandos

`${CLAUDE_PLUGIN_ROOT}/scripts/prova.py` (no Tucano, `.kairos-forge/scripts/prova.py`):

| Comando | O que confere |
|---|---|
| `prova.py reproduzir --antes --comando "<laço>" --sintoma "<regex>"` | o laço falha aqui com o sintoma, antes do conserto |
| `prova.py reproduzir --comando "<laço>" --sintoma "<regex>"` | o laço falha na base do diff com o sintoma e passa agora (`reproduz_e_corrige`) |
| `prova.py marcas` | nenhuma linha nova com a marca de depuração |
| `prova.py investigacao docs/investigacoes/INV-<slug>.md` | a ficha inteira: sai 0 pronta, 1 incompleta, 2 pare e pergunte |

## 0. Abra a ficha

Antes de mexer no código, crie `docs/investigacoes/INV-<slug>.md` no modelo de
`references/modelo-de-ficha.md`. Ela guarda o que se tentou, e é ela que o `investigacao`
confere no fim. Escreva o **Sintoma** com as palavras e a saída que a pessoa viu.

## 1. Monte o laço

O laço é um comando que sai diferente de 0 enquanto o problema existe e roda em segundos.
Escolha o mais barato que mostre o problema de verdade:

- um teste que falha, ou um script que chama só a parte suspeita;
- a CLI ou o servidor local com uma entrada fixa, comparando a saída com a certa;
- uma requisição ou um log real gravado em arquivo e repetido;
- o navegador automatizado (Playwright), quando o problema só aparece na tela;
- falha intermitente: o mesmo comando repetido muitas vezes, com semente fixa e carga, até
  falhar quase sempre;
- regressão entre versões: `git bisect run <laço>`.

Laço lento ou instável se conserta antes de seguir. Então confira que ele mostra **o problema
que a pessoa descreveu**, e não um erro vizinho:

```
prova.py reproduzir --antes --comando "<laço>" --sintoma "<regex do sintoma>"
```

Sai 0 com `reproduz`. Com `sintoma_diferente`, o laço achou outro erro: corrija o laço. Não
deu para montar o laço? Pare e peça o que falta (os passos exatos, um log, o ambiente, o dado),
com o que você já tentou escrito na ficha. Conserto sem reprodução é chute.

## 2. Encolha a reprodução

Com o laço falhando, tire uma coisa por vez (entrada, passo, configuração, dado) e rode de
novo a cada corte. Pare quando qualquer corte a mais fizer o problema sumir. A reprodução
mínima deixa menos suspeitos e vira o teste de regressão.

## 3. Uma hipótese por vez

- Na tabela `## Hipóteses` da ficha, de 2 a 4 causas possíveis, cada uma com o que se veria
  se fosse ela. Teste primeiro a mais barata de descartar, e mude uma coisa por vez.
- Prefira o depurador ao log. Log de depuração só nas fronteiras que separam as hipóteses, e
  sempre com a marca `forge-depura-<id>` (um id curto de letras e números), para achar e tirar
  todos no fim com `prova.py marcas`.
- **Três descartadas e nenhuma confirmada: pare.** O `prova.py investigacao` sai 2. Mostre à
  pessoa o laço, o que foi descartado e por quê, e peça a informação que falta. Insistir sem
  pista nova só gasta o orçamento (o mesmo espírito do ataque à premissa, ADR-0045).

## 4. Prove a causa

Confirmada é a hipótese em que mexer na causa liga e desliga o problema no laço. "Parou de
falhar" sem saber por quê não é causa. Escreva `## Causa` (com `arquivo:linha`) e `## Prova`
na ficha **antes** do conserto.

## 5. Corrija na raiz e trave

- O conserto vai onde a causa está, não onde o sintoma aparece. Guarda em volta do ponto que
  quebra não é conserto. O `try` vazio o `prova.py atalhos` acha (`erro-engolido`); o valor
  padrão que esconde o erro nenhum script acha, e quem revisa olha.
- A reprodução mínima vira teste, no arquivo de teste que já existe se for o caso, e o laço
  da ficha passa a rodá-lo. Então:

```
prova.py reproduzir --comando "<laço>" --sintoma "<regex do sintoma>"
```

  Tem de dar `reproduz_e_corrige`: falha na base do diff com o sintoma e passa agora. Só os
  testes do diff são copiados para a base antes de rodar, então o laço da ficha é o teste, ou
  um comando que já existe na base (a CLI, um endpoint). Script novo fora da pasta de testes
  não existe lá e dá `sintoma_diferente`.
- Sem lugar certo para o teste (só daria um teste raso demais), isso é um achado: diga na
  `## Trava` por quê.

## Lentidão

O laço é a medição: o tempo antes, onde o tempo vai (perfil, log com horário) e o tempo depois.
Ele sai diferente de 0 acima do limite combinado, para o `reproduzir` funcionar igual. Sem
número antes e depois, não houve melhora. Melhoria contínua por métrica é o `/otimizar`.

## No arco e no CI

- **`/entregar`**: no `corrigindo_validacao` ou no `corrigindo_revisao` sem lugar apontado, e
  sempre em `atacando_premissa_validacao` ou `atacando_premissa_revisao`, a correção passa por
  esta skill. A premissa que o `ciclo.py` pede é a suposição que as correções que falharam
  compartilharam: ela entra na ficha como a primeira hipótese a testar.
- **`kairos-forge-corrigir.yml`**: o gate vermelho é o laço. Lá o agente não roda o `prova.py`
  (só o gate e git de leitura): o workflow roda o gate antes do agente (se passa, não há o que
  corrigir) e depois (se ainda falha, não abre PR), e as linhas `**Causa:**` e `**Prova:**` da
  resposta vão para o commit e para o topo do PR.

## Cuidado

Não copie dado pessoal para o log nem para a ficha: nenhum script o reconhece. Antes do
commit, `guardrail.py ocultar <arquivo>` troca pela marca o segredo que a regra do
`segredos.py` reconhece. O commit diz a causa, o que mudou e como foi provado (`templates/anti-drift.md`).

## Resposta

Uma linha para cada, nesta forma (o gatilho de CI lê a `Causa:` e a `Prova:`):

- **Causa:** em uma frase, com `arquivo:linha`.
- **Prova:** o que ligava e desligava o problema.
- **Conserto:** o que mudou e onde.
- **Trava:** o teste novo e a saída do `prova.py reproduzir` com `reproduz_e_corrige`.

## Pronto quando

- Com a causa achada, a ficha `docs/investigacoes/INV-<slug>.md` tem sintoma, laço, hipóteses, `## Causa` com `arquivo:linha`, prova e trava, e `prova.py investigacao docs/investigacoes/INV-<slug>.md` sai 0.
- A resposta dá causa, prova, conserto e trava, com a saída de `prova.py reproduzir --comando "<laço>" --sintoma "<regex>"` em `reproduz_e_corrige`; na lentidão, com o tempo antes e depois.
- O conserto está onde a causa está: nenhum `erro-engolido` de `prova.py atalhos` nas linhas que ele acrescentou, nem valor padrão que esconda o erro.
- O commit do conserto diz a causa, o que mudou e como foi provado (`git log -1`); no CI, onde o agente não roda o `prova.py`, o `kairos-forge-corrigir.yml` roda o gate antes e depois e a resposta termina nas linhas `Causa:` (com `arquivo:linha`) e `Prova:`.
- Em qualquer saída, `prova.py marcas` sai 0: nenhum log com a marca `forge-depura-<id>` sobrou no diff.
- Sem causa, a parada: nenhum laço deu `reproduz` em `prova.py reproduzir --antes`, ou `prova.py investigacao` saiu 2 (três descartadas, nenhuma confirmada); a ficha guarda o que se tentou e a pessoa recebeu o laço tentado, o descartado e por quê, e o pedido do que falta.

## Referências

| Arquivo | Quando ler |
|---|---|
| `references/modelo-de-ficha.md` | ao abrir a ficha (passo 0) |
