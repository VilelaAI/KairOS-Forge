# ADR-0054 — Mutante por critério de aceite

- **Status:** aceito
- **Data:** 2026-11-05
- **Versão:** v0.47.0

## Contexto

O ADR-0053 trouxe três dos quatro mecanismos do PDD Kit (GitHub Next, nov/2026) e deixou o
quarto para depois: um bug plantado por critério. No PDD Kit, a especificação que verifica
mas não descarta bug nenhum é "verificação de fachada". Para pegá-la, eles plantam um bug
que viola a cláusula e conferem se o verificador o recusa.

A fábrica já tinha duas metades disso:
- **O teste novo tem de falhar sem a mudança** (`prova.py pre-patch`, ADR-0039). Prova que
  o teste depende do patch, mas não diz de qual parte do patch nem de qual critério.
- **A suíte tem de matar mutantes nas linhas tocadas** (`qualidade.py mutacao`,
  ADR-0045). Prova que *algum* teste percebe a linha mudar, mas não diz qual.

Faltava a ligação entre as duas e a SPEC. A célula `verificado:` diz que o critério X foi
provado pelo comando Y, e nada conferia se Y percebe alguma coisa no código que a entrega
tocou. Um teste que chama a função e não confere o resultado fica verde. Um teste que
confere outra coisa também fica. Nos dois casos a suíte inteira pode até matar o mutante,
por outro teste, e o critério segue "verificado" sem que o teste dele prove nada.

## Decisão

### `qualidade.py criterios SPEC-NNN`

Um quarto subcomando, que olha a SPEC em vez da suíte.

1. **De onde vem o comando de cada critério.** Da coluna Comando/gate da
   `## Matriz de testes`: só o que está entre crases. Sem linha na matriz, vale o comando
   entre crases da célula `verificado:`.
   - As colunas são achadas pelo cabeçalho.
   - Linha do tipo `manual` não tem comando.
   - Uma linha pode cobrir vários ids (`LOG-01, LOG-02`).
   - Vários comandos do mesmo critério rodam juntos, com `&&`.
   - Texto fora das crases nunca roda no shell.
2. **Os mutantes.** São os mesmos da `mutacao`: operador trocado e `return x` →
   `return None` nas linhas que o diff tocou, até `--max`, num worktree descartável.
3. **A base.** O comando de cada critério roda primeiro sem mutante nenhum. O que falha
   ali sai `vermelho` e não julga nada.
4. **O rodízio.** Cada mutante passa pelos critérios em rodízio (o mutante *i* começa no
   critério *i* mod *n*) até um perceber, isto é, até o comando falhar ou estourar o tempo.
   O rodízio espalha o crédito, e o mutante que passa por todos fica marcado.
5. **A segunda passada.** O critério que não percebeu nada no rodízio tenta os mutantes que
   o rodízio não lhe deu, até o primeiro que perceba. Sem isso, um critério que só percebe
   o mutante que outro critério pegou antes sairia fachada sem ter sido testado contra ele.

### Os veredictos

| Critério | Quando |
|---|---|
| `descarta` | Percebeu ao menos um mutante. O relatório diz qual |
| `fachada` | Passou com todos os mutantes plantados no código tocado |
| `vermelho` | O comando falha sem mutante nenhum |
| `sem_comando` | Nada entre crases na matriz nem no `verificado:` |
| `pendente` | Status Pendente: fica fora, a não ser que `--requisitos` o peça |
| `nao_julgado` | Teto da rodada, nenhum sítio no diff, worktree que não montou |

O mutante que passou por todos os critérios verdes sai `sem_criterio`: a entrega mudou um
comportamento que nenhum critério de aceite segura. A suíte inteira pode pegá-lo, mas
nenhum critério pegou. Ele é listado e não reprova.

Exit 1 com fachada, com SPEC que não existe ou com id de `--requisitos` que a SPEC não tem.
Julgar nada e sair verde seria o pior resultado.

Critérios com o mesmo comando dividem o veredicto. O comando roda uma vez só, e o
relatório diz com quem dividiu. Um comando que roda a suíte inteira percebe tudo e não
separa critério nenhum. Por isso a matriz pede, a partir de agora, o comando que roda só
o teste daquele requisito.

### No arco

- **`/validar`.** O passo 4.1 ganha o `criterios`, por último, porque é o mais caro.
  - O critério de fachada vira "sem evidência" na matriz e conta em `sem_evidencia`. Em
    P1, isso bloqueia, e o `ciclo.py` manda o arco para `provando` (ADR-0048). Lá, o Ricardo
    escreve o teste que perceba o comportamento do critério, antes de qualquer mudança no
    código.
  - O mutante sem critério é ressalva com o mutante nomeado. Falta um critério, ou é algo
    para `## Não prometido`? Quem decide é a pessoa, no PR. O agente não inventa o
    requisito (ADR-0015).
- **`/especificar`.** O modelo da SPEC diz como escrever o Comando/gate: entre crases, só o
  teste daquele requisito. O eixo Testabilidade da crítica adversarial pergunta se é assim.
  Comando que serve a todos os requisitos já é achado na crítica.
- **Ricardo.** Passa a ser dono também desse número: cada critério com o seu teste, e o
  teste percebendo o código.

## Consequências

- **Nenhum contrato muda.** O `kairos-validacao` já tinha `sem_evidencia`, e a fachada
  entra nele. O `ciclo.py` já tinha `provando`.
- **Testes.** `test_criterios.py` tem 30 testes:
  - a leitura da matriz: a coluna pelo cabeçalho, o manual, as várias linhas, o texto fora
    das crases;
  - o motor contra uma suíte falsa: o rodízio e a direção dele, a segunda passada, a
    fachada só depois de todos, o teto, a base vermelha, o sítio que não confere, o piso
    do tempo por mutante;
  - o caminho inteiro num git de verdade: os seis veredictos numa SPEC, o comando dividido,
    o comportamento sem critério, o arquivo original intocado e o worktree removido;
  - os erros: SPEC que não existe, SPEC sem requisito, id fora da SPEC, worktree que não
    monta.

  O `test_qualidade.py` ganha o sítio que não confere, com o `julgar` real.
- **O `criterios` rodado sobre o próprio diff.** Uma SPEC desta entrega com cinco
  requisitos, cada um apontando para a classe de teste que o prova.
  - Na primeira rodada, o critério "a mutação de antes segue igual" saiu **de fachada**.
    Os mutantes do código que o refactor tocou (`mutante_aplicado`, `julgar`) estavam no
    caminho do sítio que não confere, e a `MutacaoNoDiff` não percorria esse caminho. A
    suíte inteira também não. Virou teste.
  - Na segunda rodada, os 5 critérios percebem. O único mutante sem critério é o `>` →
    `>=` do teto, uma comparação de tempo em ponto flutuante, que é equivalente.
- **Mutação.** A mutação do `qualidade.py` sobre o diff deixou 6 de 60 mutantes vivos na
  primeira rodada:
  - os 2 do sítio que não confere, os mesmos que o teste em casa apontou, viraram teste;
  - 2 equivalentes saíram do código: o preenchimento da linha curta da matriz sem conta, e
    o `percebe` devolvendo o próprio booleano;
  - o `+` → `-` do rodízio, que com dois critérios dá a mesma ordem, virou um teste com
    três.

  A rodada final mata 59 de 60, e o que sobra é o equivalente do teto. Cada teste novo
  falha com o seu mutante plantado à mão, rodado com `python3 -B`, porque um `cp` que
  restaura um arquivo do mesmo tamanho no mesmo segundo deixa o bytecode velho valendo.
- **Custo.** No pior caso, cada mutante roda o comando de cada critério: *critérios ×
  mutantes* execuções de um teste só. No caso comum, o rodízio para no primeiro que
  percebe. `--max` e `--teto` limitam a rodada, como na `mutacao`.
- **O `julgar` da `mutacao`** passou a plantar e desfazer o mutante pelo mesmo
  `mutante_aplicado`, e o worktree descartável virou `no_worktree`. As duas medidas
  dividem o código em vez de copiá-lo.

## Limites declarados

- **O mutante é genérico, não dirigido.** O PDD Kit planta o bug que viola exatamente a
  cláusula. Aqui o mutante é o mesmo para todos os critérios. Um mutante que quebra tudo dá
  crédito a qualquer critério que o tente. Por isso o relatório mostra qual mutante cada
  critério percebeu: quem valida vê se ele é do critério.
- **O critério tem de ser deste diff.** Um requisito entregue num PR anterior não tem
  código tocado aqui, e sai fachada. Tire-o da rodada com `--requisitos`.
- **O comando vem do repositório.** Roda com a mesma confiança da suíte do projeto, que o
  `/validar` já roda. Os gatilhos de CI não rodam o `criterios`.

## Alternativas consideradas

- **A matriz completa, critério × mutante.** Recusada pelo custo. O rodízio com segunda
  passada dá as mesmas duas respostas, qual critério é fachada e qual mutante ninguém
  percebe, com menos execuções.
- **O mutante dirigido escrito pelo agente.** Recusado. Seria o agente julgando o próprio
  trabalho, que é o que o ADR-0039 tira da prova. O mutante genérico é determinístico e não
  sabe o que o critério espera.
- **Ligar teste a requisito pela cobertura de cada teste.** Recusado por ora. Pede
  cobertura por teste em cada linguagem, e o script é só stdlib. A Matriz de testes já diz
  qual comando prova qual requisito.
- **Mutante sem critério reprovando.** Recusado. Um comportamento sem critério pode ser
  legítimo (log, mensagem, ajuste de borda), e a decisão de virar requisito é da pessoa.
