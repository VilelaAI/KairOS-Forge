---
name: investigar
description: Acha e prova a causa de um defeito antes do conserto, com ficha em docs/investigacoes/ e o prova.py reproduzir como juiz (falha na base, passa agora). Use em erro sem explicação, falha que vem e vai, quebra depois de um merge ou lentidão nova. Causa já apontada é o rodar.
---

# Investigar — a causa antes do conserto

Algo quebra, falha só de vez em quando ou ficou lento, e ninguém sabe dizer onde. O
**Ricardo [Testes]** (`ricardo-testes`) conduz: transforma o defeito num comando que o mostra
e, no fim, num teste. O conserto é do dev dono da área. Em lentidão, o **Vinícius
[Performance]** cuida da medição; em incidente de produção, o **Sérgio [SRE]** contém o estrago
primeiro, e a investigação vem depois.

**Regra de ouro:** o conserto só começa depois que a causa está escrita na ficha e provada no
laço. Consertar o que não se reproduz, ou o que não se explica, troca um defeito visível por um
escondido. O método vem do corno-skills, que não declara licença: aproveitamos a ideia, e o
texto é nosso.

## Quando usar e quando não

- **Use** quando ninguém sabe a causa: gate vermelho sem achado que aponte o lugar, falha que
  aparece numa rodada e some na outra, comportamento que mudou sem commit suspeito, erro que só
  a pessoa viu, o `/entregar` em `atacando_premissa_validacao` ou `atacando_premissa_revisao`
  (ADR-0045).
- **Não use** quando o achado já traz `arquivo:linha` e o motivo (o `/validar` e o `/revisar`
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

## A ficha conduz

A investigação é preencher `docs/investigacoes/INV-<slug>.md` (modelo em
`references/modelo-de-ficha.md`) de cima para baixo. Cada seção só se escreve com a anterior
pronta, e o `prova.py investigacao` confere todas no fim. Abra a ficha antes de tocar no código.

### Sintoma

Registre o relato da pessoa como ela o deu: a mensagem de erro, o valor errado, o tempo medido.
É contra esse registro que o laço vai ser julgado.

### Reprodução e sintoma na saída

O laço é um comando de poucos segundos cujo código de saída diz se o defeito está presente
(diferente de 0) ou não (0). Escolha pela situação, do mais barato para o mais caro:

| Situação | Laço |
|---|---|
| há teste perto do código | o teste, ou um novo que chama a função suspeita |
| CLI ou serviço local | a chamada que dispara o defeito, com um `diff` contra o resultado esperado |
| relato vindo de produção | a requisição ou o trecho de log gravados num arquivo e reenviados |
| defeito de tela | um roteiro do Playwright |
| falha que vem e vai | o comando num `for` de centenas de rodadas, com semente fixa e paralelismo, até a taxa de falha ficar alta |
| regressão | `git bisect run <laço>` a partir do último commit bom |

Na linha **Sintoma na saída**, a regex do sintoma. Antes de seguir, confirme:

```
prova.py reproduzir --antes --comando "<laço>" --sintoma "<regex do sintoma>"
```

`reproduz` quer dizer que o laço falha, e pelo motivo relatado. `sintoma_diferente` quer dizer
que ele tropeçou em outro defeito: quem se conserta, então, é o laço. Laço demorado ou que oscila
também se conserta antes de seguir.

Se nenhum laço sai, a investigação para aqui. Registre na ficha as tentativas e peça à pessoa o
que destrava: o roteiro que ela seguiu, o arquivo de log, a versão, o dado de entrada. Sem
reprodução, qualquer mudança é aposta.

Com o laço de pé, enxugue-o: retire um ingrediente por rodada (um passo, uma linha da entrada,
uma opção de configuração) enquanto o defeito continuar aparecendo. O que resta é o mínimo
necessário, e é dele que sai o teste da trava.

### Hipóteses

A tabela `## Hipóteses` tem uma linha por suspeita: a causa candidata, o sinal que a
confirmaria, o experimento feito e o resultado (`descartada` ou `confirmada`). Comece pelo
experimento mais rápido. Cada experimento muda uma variável só; com duas, o resultado não diz
qual delas importou.

Para observar, o depurador vem antes do log. Quando o log for o caminho, poucas linhas, nos
pontos em que as suspeitas divergem, cada uma marcada com `forge-depura-<id>` (letras minúsculas
e números): o `prova.py marcas` acha a que ficar para trás.

**Três linhas `descartada` e nenhuma `confirmada` encerram a rodada.** O `prova.py
investigacao` sai 2. Leve à pessoa a ficha como está, com o laço e cada suspeita derrubada pelo
experimento que a derrubou, e pergunte o que você não sabe sobre o sistema. Uma quarta
hipótese sem informação nova costuma repetir as três primeiras (a mesma lógica do ataque à
premissa, ADR-0045).

### Causa e prova

Uma hipótese vira `confirmada` quando o experimento controla o defeito: com a causa no lugar o
laço falha, sem ela o laço passa, e isso se repete. Ver o laço passar depois de uma mudança
qualquer é coincidência até ser explicado. `## Causa` leva o `arquivo:linha`, e `## Prova`
descreve o experimento. As duas ficam escritas antes da primeira linha do conserto.

### Trava

- O conserto mexe na linha da `## Causa`. Cercar o ponto que estoura com uma condição, um `try`
  ou um valor padrão apaga o sintoma e mantém o defeito. O `prova.py atalhos` acusa o `try`
  vazio (`erro-engolido`); o valor padrão que mascara, só quem revisa vê.
- A reprodução mínima vira teste, no arquivo de teste que já cobre aquele código quando houver,
  e a **Reprodução** da ficha passa a rodar esse teste. Então:

```
prova.py reproduzir --comando "<laço>" --sintoma "<regex do sintoma>"
```

  O resultado tem de ser `reproduz_e_corrige`: o laço falha na base do diff, com o sintoma, e
  passa na árvore de trabalho. Antes de rodar, só os testes do diff vão para a base; por isso o
  laço final é o teste, ou um comando que a base já tem (uma CLI, um endpoint). Um script novo
  fora da pasta de testes não existe na base, e o resultado é `sintoma_diferente`.
- Quando não há onde pôr um teste que pegue o defeito de verdade, a `## Trava` explica o
  motivo: isso também é informação para quem revisa.

## Lentidão

Aqui o laço mede: sai diferente de 0 quando o tempo passa do limite combinado com a pessoa, e o
`reproduzir` funciona do mesmo jeito. A ficha registra o tempo de partida, o perfil que mostrou
para onde o tempo vai e o tempo final. Melhora sem os dois números não entra como melhora. Ganho
incremental guiado por métrica é o `/otimizar`.

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

Termine com quatro linhas, nesta ordem (o gatilho de CI procura as duas primeiras):

- **Causa:** uma frase, com `arquivo:linha`.
- **Prova:** o experimento que controlou o defeito.
- **Conserto:** os arquivos mexidos e a mudança em cada um.
- **Trava:** o nome do teste novo e a linha do `prova.py reproduzir` com `reproduz_e_corrige`.

## Pronto quando

- Com a causa achada, a ficha `docs/investigacoes/INV-<slug>.md` tem sintoma, laço, hipóteses, `## Causa` com `arquivo:linha`, prova e trava, e `prova.py investigacao docs/investigacoes/INV-<slug>.md` sai 0.
- A resposta termina nas linhas de causa, prova, conserto e trava, com a saída de `prova.py reproduzir --comando "<laço>" --sintoma "<regex>"` em `reproduz_e_corrige`; na lentidão, com o tempo antes e depois.
- O conserto está onde a causa está: nenhum `erro-engolido` de `prova.py atalhos` nas linhas que ele acrescentou, nem valor padrão que esconda o erro.
- O commit do conserto diz a causa, o que mudou e como foi provado (`git log -1`); no CI, onde o agente não roda o `prova.py`, o `kairos-forge-corrigir.yml` roda o gate antes e depois e a resposta termina nas linhas `Causa:` (com `arquivo:linha`) e `Prova:`.
- Em qualquer saída, `prova.py marcas` sai 0: nenhum log com a marca `forge-depura-<id>` sobrou no diff.
- Sem causa, a parada: nenhum laço deu `reproduz` em `prova.py reproduzir --antes`, ou `prova.py investigacao` saiu 2 (três descartadas, nenhuma confirmada); a pessoa recebeu a ficha com as tentativas e cada suspeita derrubada, e a pergunta sobre o que falta saber.

## Referências

| Arquivo | Quando ler |
|---|---|
| `references/modelo-de-ficha.md` | ao abrir a ficha (passo 0) |
