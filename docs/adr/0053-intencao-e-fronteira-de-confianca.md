# ADR-0053 — Intenção e fronteira de confiança na SPEC: o que cabe do PDD Kit

- **Status:** aceito
- **Data:** 2026-11-05
- **Versão:** v0.46.0

## Contexto

O PDD Kit (GitHub Next, nov/2026, protótipo de pesquisa) pergunta o que, afinal, um time
assina quando mescla código que ninguém leu linha a linha. A resposta deles é prova formal:
uma especificação em Verus (Rust) e um verificador que prova o código contra ela para
toda entrada.

A prova formal não cabe aqui. É só para Rust, é protótipo e mora dentro de um app (o
Chopin). A fábrica é plugin genérico para qualquer linguagem (ADR-0001).

O que cabe é o jeito como eles chegam até a prova. Quatro mecanismos sobrevivem sem o
Verus, e três deles entram neste ADR.

1. **A regra nos dois sentidos.** O primeiro cartão do PDD Kit perguntou se "você só ganha
   um token com a senha certa" também quer dizer "com a senha certa você sempre ganha".
   Um login que recusa todo mundo cumpre a primeira frase. Sozinho, o agente escolhe uma
   das metades sem avisar.
2. **O mapa de intenção.** Cada requisito liga às palavras de quem pediu. O ADR-0015 já
   proíbe inventar requisito, mas nada mostrava de onde cada um tinha vindo.
3. **A fronteira de confiança e o "não prometido".** O plano deles lista o que é provado, o
   que é só confiado (cada peça aceita por uma pessoa e com um teste) e o que ninguém
   promete. Na SPEC da fábrica, isso ficava implícito: a biblioteca que faz o que diz e o
   provedor que responde viravam premissa silenciosa. A latência sob carga, que ninguém
   garantiu, não aparecia em lugar nenhum.
4. **Um bug plantado por critério.** A especificação que verifica mas descarta quase nada
   é a "verificação de fachada" deles. A fábrica já tem metade disso: o teste novo tem de
   falhar sem a mudança (`prova.py`, ADR-0039) e a mutação roda por função tocada
   (`qualidade.py`, ADR-0045). Falta ligar o mutante ao critério de aceite. Fica para a
   etapa seguinte.

## Decisão

### 1. Critério nos dois sentidos

O requisito que proíbe o caso ruim ganha o critério do caso bom ao lado, ou diz por que
tem um sentido só. "Nunca grava a senha no log" não tem outro lado.

A regra entra no modelo da SPEC, nas regras do `/especificar` e no eixo Requisito da
crítica adversarial (ADR-0033). Não vira código: parear o caso bom com o ruim pede
julgamento, e um regex sobre "só", "nunca" e "não" daria mais falso positivo do que acerto.

### 2. Mapa de intenção

A SPEC ganha a seção `## Mapa de intenção`: requisito, de onde veio e as palavras de quem
pediu.

- **De onde pode vir:** o pedido, a issue, a resposta de um gate, a varredura das nove
  dimensões, a trilha ou um ADR.
- **O que a fábrica deduziu** fica `inferido`, e a pessoa confirma no gate 3/3.
- **Uma linha cobre vários ids** (`LOG-01, LOG-02`).

Três lugares leem a seção:
- **O `painel.py`** lê junto com os requisitos e devolve `sem_origem` e `inferidos`.
- **O guardrail** ganha a classe `intencao`. Ao escrever a SPEC, acusa requisito sem
  origem. Nasce em `aviso` e avisa uma vez por arquivo na sessão, com o rastro sempre na
  trajetória.
  - SPEC nova sem a seção também conta.
  - SPEC que já estava na base sem o mapa é de antes da regra e passa. Com o mapa, vale
    para ela também.
- **O corpo do PR** (`painel.py --pr`) põe no "O que você decide":
  - o requisito sem origem ("entraram sem ser pedidos?");
  - o inferido;
  - a SPEC sem mapa.

### 3. Fronteira de confiança e "não prometido"

A SPEC ganha duas seções.

- **`## Confiado, não provado`.** O que a entrega assume sem provar, com quem aceitou e o
  teste que cobre. O teste fica `planejado:` até rodar e `verificado:` depois, a mesma
  convenção da coluna Verificação.
- **`## Não prometido`.** A propriedade do que **é** entregue que ninguém garante. Não é o
  mesmo que não-objetivo: este é o que fica fora do escopo.

Quem usa as duas seções:
- **O `/validar`** roda os testes `planejado:` da fronteira e põe no relatório a peça sem
  teste.
- **O corpo do PR** traz no "O que você decide":
  - cada peça confiada sem teste verificado, com quem a aceitou ou "ninguém aceitou";
  - a lista do não prometido, como o que o merge aceita.

  Na evidência recolhida, a tabela da fronteira inteira.
- **O gate 3/3** do `ciclo.py` passa a mandar apresentar os inferidos, o confiado e o não
  prometido junto com o objetivo e os P1.

### O que muda na crítica

O eixo Testabilidade ganha a segunda pergunta dos revisores do PDD Kit: a SPEC promete mais
do que dá para verificar? O que ela assume sem provar está em Confiado, e o que ninguém
garante está em Não prometido? O eixo Requisito ganha o mapa e os dois sentidos.

## Consequências

- **Nenhum contrato muda.** As fences `kairos-critica`, `kairos-validacao` e
  `kairos-revisao` e o `ciclo.py estado --json` ficam como estão. Muda o texto do gate 3/3,
  que não faz parte da assinatura. O `painel.py --json` ganha `intencao`, `confiado` e
  `nao_prometido` por SPEC.
- **Testes.** `test_intencao.py` tem 17 testes, dos quais 14 falham contra a `main`. Cobrem:
  - a leitura das três seções;
  - os sinais no corpo do PR;
  - a classe `intencao`: SPEC nova, mapa parcial, SPEC antiga, modo `bloqueio`, a ordem
    com a checagem de "Concluído sem verificado" e o documento que não é SPEC.

  A mutação do `qualidade.py` deixou 6 de 42 mutantes vivos na primeira rodada. Os que
  eram lacuna viraram teste. A rodada final mata 40 de 41, e o que sobra é equivalente: o
  `[]` devolvido quando o import falha, que o chamador lê como `None`.
- **SPECs antigas.** Seguem sem mapa até alguém editá-lo. O corpo do PR delas passa a dizer
  "A SPEC não tem mapa de intenção", o que é verdade e é para a pessoa ver.
- **Requisito da varredura** tem origem própria (`varredura: <dimensão>`). Ele não veio de
  quem pediu, mas também não foi inventado: veio da lista que existe justamente para cobrir
  o que ninguém pede.

## Alternativas consideradas

- **Prova formal (Verus, Dafny, Lean) como trilha.** Adiado. Serve a uma linguagem por vez e
  a especificações que alguém do time saiba ler, e o próprio PDD Kit é protótipo. Volta à
  mesa quando houver um projeto em Rust pedindo.
- **O mapa de intenção dentro da tabela de requisitos, como coluna.** Recusado. A tabela já
  tem seis colunas, e a citação de quem pediu é longa. A seção separada também deixa uma
  linha cobrir vários requisitos.
- **Os dois sentidos como regra de código.** Recusado pelo falso positivo (acima).
- **O cartão de comprovação (o quiz do PDD Kit).** Recusado por ora. Uma pergunta para
  conferir se a pessoa entendeu o que aprova, antes do gate 3/3, é atrito em toda SPEC. O
  cartão que explica antes de pedir já entrou na pausa da faixa 3 (ADR-0052).
- **Mutante por critério de aceite.** Fica para a etapa seguinte. Precisa ligar o teste ao
  requisito, que hoje só a célula `verificado:` faz, por texto.
