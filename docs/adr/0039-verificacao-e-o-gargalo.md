# ADR-0039 — Verificação é o gargalo: prova negativa dos testes, escada de verificação e revisão calibrada

- **Status:** aceito
- **Data:** 2026-09-17
- **Versão:** v0.32.0

## Contexto

Em setembro de 2026 o Tech Leads Club publicou o *TLC AI Dev Flow* — quatro skills
(`tlc-discover`, `tlc-plan`, `tlc-implement`, `the-judge`) e uma tese: *"código ficou
barato; prova, não"*. A fábrica agêntica que eles descrevem é o mesmo desenho que este
plugin persegue desde o ADR-0023 — humano nas pontas (intenção e direção), execução como
estação de agente, PR como fronteira — e boa parte do que o material propõe o forge já faz,
com mais estrutura: máquina de estados com orçamento (ADR-0029), compensação (ADR-0036),
trajetória corroborada (ADR-0021), contrato de relatório com prova de cobertura (ADR-0032),
gatilhos por evento (ADR-0026). Não se porta nada disso, e as quatro skills não entram no
plugin: duplicariam `especificar`, `mobilizar` e `revisar` em inglês e sem orquestração.

O que o material acerta, e nós tratávamos só de raspão, cabe em uma frase: **a verificação
do agente sobre o próprio trabalho não vale como prova**. A auditoria do plugin contra os
sete princípios deles encontrou cinco lacunas concretas:

| Princípio | O que o forge tinha | A lacuna |
|---|---|---|
| Teste pré-patch — o teste novo, rodado contra o código de antes, tem de **falhar** | `verificado:` na SPEC + `telemetria.py corroborar`: o gate rodou e passou | As duas checagens aceitam um teste que passa. Um teste que passa **sem** a mudança não prova a mudança, e nada media isso |
| Não deixar o agente reescrever a suite | `guardrail.py` protege `.github/workflows/**` com a justificativa "mexer nos próprios gates é Goodhart" | Teste existente **modificado** é o mesmo Goodhart, e passava em silêncio: asserção removida, caso pulado, arquivo apagado no mesmo diff da feature |
| Fatias verticais — um caminho fim a fim fino primeiro, depois aprofundar | Plano com tarefas atômicas e dependências | O exemplo do `modelo-spec.md` era **por camada** (T1 migrations, T2 backend, T3 frontend): exatamente o fatiamento horizontal que o modelo faz sozinho quando ninguém manda o contrário, e que deixa nada testável até a última tarefa |
| Verificação em camadas — barato primeiro, caro perto do PR | `/validar` roda gates; `/revisar` aciona Helena sempre | Sem ordem declarada. Um e2e rodado para confirmar o que o lint já disse queima orçamento do `/entregar` |
| Critério de aceite como resultado observável com valor, não adjetivo | `WHEN/THEN/SHALL` no template | Só a crítica adversarial perguntava "evidência é observável?"; "rápido" e "robusto" passavam |

E um sexto ponto, do quadro de code review multi-agente da mesma turma: a revisão com seis
especialistas e um consolidador tem a forma exata do `/revisar` — o que ela tem a mais é
uma **segunda passada obrigatória** por revisor, contra o efeito *cry wolf*: com 30% de
ruído o time aprende a ignorar tudo em poucos sprints, e aí o 🔴 verdadeiro passa junto. O
`/revisar` não relia achados nem media quantos o humano descartava; sem número, calibrar
persona era gosto.

## Decisão

**1. `prova.py` — prova negativa dos testes de um diff.** Script novo, só stdlib, dois
subcomandos:

- `pre-patch` cria um worktree descartável no merge-base com a branch base, copia só os
  testes **novos** do diff para dentro e roda o gate deles lá, sem o patch. Veredicto por
  arquivo: `falhou_na_base` (o teste depende da mudança), `passou_na_base` (não prova a
  mudança), `nao_executado` (ecossistema sem comando conhecido, ou nada coletado — declarado,
  nunca inventado). Deduz o comando por extensão (pytest ou unittest, vitest ou jest pelo
  `package.json`, `go test`) e aceita `--comando "<gate> {arquivo}"` para o resto.
  `node_modules`, `.venv`, `venv` e `vendor` da raiz são ligados por symlink no worktree,
  para que "faltou dependência" não se disfarce de "falhou na base".
- `testes-alterados` lista os testes que **já existiam** no merge-base e mudaram ou
  sumiram no diff, com os sinais de afrouxamento lidos do `git diff -U0`: asserção
  removida, caso removido, pulo adicionado (`skip`, `only`, `xit`, `#[ignore]`…), arquivo
  apagado.

Nenhum dos dois é veredicto: refactor legítimo muda teste, e teste de regressão de bug
que a base já corrigia passa na base por definição. O script transforma o silêncio em
achado com nome; quem julga a justificativa é o `/validar`.

**2. Classe `teste` no `guardrail.py`.** Edição em arquivo de teste que existia antes do
diff (no merge-base com a base; sem base, no HEAD) vira a sexta classe de regra. Nasce em
modo `aviso` — a primeira classe com default diferente de `bloqueio`, e a exceção é
deliberada: editar teste existente é legítimo com frequência demais para bloquear por
default, e regra que bloqueia refactor honesto é regra que o time desliga na semana
seguinte (ADR-0030). O valor está no rastro: **toda** edição é registrada na trajetória
(`tipo: recusa, classe: teste`), o aviso aparece uma vez por arquivo por sessão (mesma
técnica do lembrete de DoD, ADR-0038), e o `/validar` passa a poder verificar "não mexi em
teste" em vez de acreditar. O modo CLI (`verificar`) imprime os sinais do
`testes-alterados` e só endurece com `{"modos": {"teste": "bloqueio"}}` — a mesma
assimetria do `gerado` (ADR-0037): o hook conhece a intenção, o CLI só vê o diff.

**3. `/validar` ganha o passo 3.7 (prova negativa) e uma ordem no passo 4.** Requisito
coberto só por teste `passou_na_base` é "sem evidência"; teste existente com sinal e sem
justificativa **bloqueia** em P1 — suite verde afrouxada é evidência contra. Os gates
rodam do barato ao caro (lint e tipos → unitários → integração → navegador → segurança e
mutação) e o gate barato vermelho encerra a rodada: a correção volta com o achado barato,
e o orçamento do `/entregar` não paga o e2e para confirmar o lint. A coluna Tipo da matriz
de testes é declarada como a camada dessa escada. O relatório ganha a seção "Prova negativa
dos testes". **A fence `kairos-validacao` não muda** — o contrato v1.0 (ADR-0034) fica
intacto; a prova é seção do corpo, não campo do bloco.

**4. `/revisar` ganha a segunda passada e mede o próprio ruído.** Antes de publicar, cada
revisor relê cada achado contra o diff: o código citado existe naquela linha, e o problema
acontece de fato nesse caminho ou só se parece com um padrão? Patrícia absorve a dimensão
de regressão e alucinação — teste afrouxado (via `prova.py testes-alterados`), import
fantasma, símbolo inexistente, código morto — porque é o erro que a IA ingênua mais comete
e o mais barato de checar. E o descarte passa a ser **marcado, não apagado**: achado que o
humano não acata recebe ` · descartado: <motivo>` na própria linha do relatório salvo.
`telemetria.py ruido` lê essa marca e devolve, por revisor, achados, descartados e taxa;
o `/auditar` reporta revisor com ≥ 30% de ruído (mínimo 3 achados) como lacuna, dona
Patrícia, e reporta "não medido" quando ninguém marca — porque zero descartes em muitos
achados é mais provável ser ninguém marcando do que revisor perfeito.

**5. Fatia fim a fim e critério sem adjetivo, na origem.** No `/especificar`: a primeira
tarefa do plano é uma fatia vertical fina e testável, e o exemplo do `modelo-spec.md` passa
a mostrar isso em vez de T1 = migrations; critério de aceite tem valor concreto ("em ≤ 2 s",
"status 403"), nunca adjetivo. A crítica adversarial ganha as duas perguntas nos eixos de
testabilidade e escopo. A DoD do teammate e o anti-drift ganham a mesma linha: o teste novo
falha sem a mudança, e teste existente não se afrouxa para a suite ficar verde. O
`quadro.py` **não muda**: a fatia é decisão de plano, e um campo novo no quadro tocaria o
contrato assinado sem necessidade.

**6. Um caso novo no gold set** (`conclusao-04`, capacidade `conclusao-verificada`,
determinístico): o eval de comportamento passa a cobrir a prova negativa — 9 dos 14 casos
decididos sem modelo no caminho.

## Consequências

| O que | Antes | Depois |
|---|---|---|
| Teste novo que passa sem a mudança | invisível | `passou_na_base`, requisito sem evidência |
| Teste existente afrouxado no diff | invisível | sinal por arquivo + rastro na trajetória; bloqueia em P1 sem justificativa |
| Ordem dos gates no `/validar` | nenhuma | barato → caro; barato vermelho encerra a rodada |
| Falso positivo da revisão | publicado; nunca medido | releitura antes de publicar; `descartado:` medido por revisor |
| T1 no exemplo da SPEC | migrations (camada) | fatia fim a fim |
| Classes do guardrail | 5, todas `bloqueio` | 6; `teste` nasce em `aviso` |

**Positivas**

- Fecha as duas formas de gate verde sem prova que o eval `conclusao-verificada` não
  conseguia pegar, e as duas são checadas por código.
- "Não mexi em teste" vira afirmação verificável, não confiança.
- Ruído por revisor vira número; calibrar persona deixa de ser gosto.
- O orçamento do `/entregar` para de pagar gate caro para confirmar gate barato.

**Negativas e limites, declarados**

- **O `pre-patch` lê exit code, não intenção.** Teste que falha na base por motivo alheio
  ao patch (fixture ausente, serviço externo, `__init__.py` que só existe na feature) conta
  como `falhou_na_base` — falso negativo do lado seguro. Teste de regressão de bug já
  corrigido na base é o falso positivo conhecido, e o autor declara a exceção no relatório.
- **O worktree é uma cópia da base sem instalação.** Dependência ligada por symlink cobre o
  caso comum; projeto com build step (geração de código, compilação de proto) sai
  `nao_executado` ou falha por motivo errado. `--comando` é a válvula.
- **Sinal de afrouxamento é regex sobre diff.** Cobre os padrões correntes de sete
  ecossistemas; asserção reescrita para ficar mais fraca (`assertEqual(x, 3)` →
  `assertTrue(x)`) não dispara. O guardrail registra que o arquivo mudou; a leitura do
  conteúdo continua sendo do revisor.
- **`teste` em `aviso` depende de alguém olhar a trajetória.** É a regra do ADR-0030:
  taxa baixa e estável é o sinal para promover a `bloqueio` num projeto onde só o humano
  toca a suite; até lá, é rastro, não muro.
- **Ruído só existe se o humano marcar.** A convenção `descartado:` é a mais barata que
  encontramos (uma palavra na linha do achado, no arquivo que já existe), e mesmo assim
  pode não pegar. Por isso "não medido" é resultado declarado, nunca lido como zero.
- **A escada de gates é prosa.** O `/validar` não tem como ordenar por código o que o
  projeto declara em `contextos/testes.md`; a ordem é instrução e a coluna Tipo é o dado.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Instalar as skills `tlc-*` junto com o plugin | Duplicam `especificar`/`mobilizar`/`revisar` em inglês, sem máquina de estados, orçamento nem trajetória; confundiriam o roteamento da Laura. Servem como benchmark externo, não como peça |
| Bloquear edição em teste existente por default | Refactor legítimo edita teste o tempo todo; regra que morde o caso honesto é desligada na semana seguinte (ADR-0030). O rastro entrega o valor sem o custo |
| Campo `passou_na_base` na fence `kairos-validacao` | Muda a forma do contrato v1.0 e obriga reassinatura (ADR-0034) por um dado que o corpo do relatório carrega igualmente bem. O `ciclo.py` decide por `bloqueios`, e a prova negativa já alimenta esse número |
| Campo `fim_a_fim` na tarefa do `quadro.py` com checagem na onda 1 | Toca o contrato público do quadro; a fatia é decisão de plano e o crítico de escopo já cobra. Se o sinal aparecer na trajetória, volta como ADR próprio |
| Rodar o `pre-patch` com `git stash` em vez de worktree | Stash mexe na árvore de trabalho do usuário no meio de uma sessão; worktree é isolado e descartável, e a fábrica já usa worktree por teammate (ADR-0024) |
| Medir ruído por reação no PR (thumbs down, thread resolvida) | Depende da plataforma e de API; a marca no arquivo funciona em qualquer CLI e em qualquer forge, e é o mesmo arquivo que o contrato já governa |
| Revisor dedicado "Regressão e Alucinação" (persona nova) | Persona nova exige ADR e vaga num time; a dimensão cabe na Patrícia, que já cobre regressão, e o determinístico dela é um comando |
