# ADR-0060 — Investigar antes de corrigir, fonte salva e "Pronto quando"

- **Status:** aceito
- **Data:** 2026-11-19
- **Versão:** v0.53.0

## Contexto

O ADR-0058 anotou três ideias do [corno-skills](https://github.com/adlernatanael/corno-skills)
para depois:

- a `corno-investiga`, um método de investigação de bug;
- a `corno-pesquisa`, a fonte primária salva no repositório;
- o "Pronto quando" em cada skill.

O repositório não declara licença: daqui sai a ideia, não o texto.

Um mapeamento da fábrica, com um leitor por tema e um por skill, mostrou o tamanho de cada
lacuna.

- **Correção sem causa.**
  - Nenhum caminho de correção pedia reprodução, hipótese ou causa escrita.
  - O `prova.py pre-patch` só roda arquivo de teste novo, e a regressão de um bug costuma
    entrar num arquivo de teste que já existe.
  - O `kairos-forge-corrigir.yml` nunca rodava o gate ele mesmo e abria o PR mesmo com o gate
    ainda vermelho. O teste dele cobrava que a causa *não* aparecesse no topo do PR.
- **Fonte que some.**
  - A fábrica consulta documentação em poucos pontos e não guarda nada: os ADR-0050 a 0057
    não têm um link sequer.
  - Os gatilhos de CI rodam sem web.
  - `contextos/` é convenção do projeto, e o `prova.py decisoes` conta tudo o que está lá como
    decisão.
- **"Terminei" sem critério.**
  - Nenhuma das 19 skills dizia o que precisa estar provado para dar o trabalho por terminado.
  - O `conferir` do ADR-0058 dava ao modelo uma lista genérica quando a pessoa perguntava se
    faltava algo.

## Decisão

### 1. Investigar antes de corrigir

**Skill `/investigar`, dono Ricardo.** O Vinícius mede a lentidão e o Sérgio estanca o
incidente antes. O método:

- abrir a ficha `docs/investigacoes/INV-<slug>.md`, com sintoma, laço, regex do sintoma,
  hipóteses, causa, prova e trava;
- montar um laço curto que sai diferente de 0 enquanto o problema existe, e encolher a
  reprodução;
- testar uma hipótese por vez, com o log de depuração marcado `forge-depura-<id>`;
- parar e perguntar depois de três hipóteses descartadas;
- provar a causa ligando e desligando o problema, e escrevê-la antes do conserto;
- consertar na raiz e travar com teste.

**A parte determinística, no `prova.py`:**

- **`reproduzir --comando "<laço>" --sintoma "<regex>"`.** Roda o laço num worktree na base do
  diff, com os testes do diff (novos e mudados) copiados e os apagados tirados, e na árvore de
  trabalho. Os veredictos são `reproduz_e_corrige`, `nao_reproduz`, `sintoma_diferente`,
  `nao_corrige` e `nao_executado` (saída 126 ou 127, ou tempo esgotado, com o grupo de processos
  morto junto). Com `--antes`, roda só aqui, antes do conserto, e o veredicto bom é `reproduz`.
  Sem `--sintoma`, qualquer saída diferente de 0 conta como o problema, e o comando diz isso.
- **`investigacao <ficha>`.** Lê a ficha, roda a reprodução dela e confere a marca. Sai 0
  quando está pronta, 1 quando está incompleta e 2 para "pare e pergunte".
- **`marcas`.** Acha a linha nova com `forge-depura-<id>` (id de letras e números, de qualquer
  tamanho), fora do Markdown, da trajetória e do que o `.gitattributes` marca como gerado ou
  vendored. Também entra no `guardrail.py verificar` como problema; sem base para comparar, o
  `verificar` avisa que não conferiu. A função `gerados` mudou do `qualidade.py` para o
  `prova.py`, que os dois usam.

**No `kairos-forge-corrigir.yml`:**

- o GATE é o laço. Roda antes do agente: se passa, a falha não se reproduz ali e não há
  correção; se nem roda (saída 124, 126 ou 127: tempo esgotado, comando sem permissão ou
  inexistente), o vermelho é do ambiente e também não há. Roda depois: se ainda falha, não há
  PR, e o diagnóstico do agente e o fim da saída do gate vão para o resumo do job;
- `PREPARO`, opcional, instala as dependências do gate antes da primeira rodada;
- o gate roda o código do projeto, que a correção pode ter mudado. Por isso roda sem o
  segredo, com `timeout -k 30 480` e sem os arquivos de comando do runner (`GITHUB_ENV`,
  `GITHUB_OUTPUT`, `GITHUB_PATH`, `GITHUB_STEP_SUMMARY`), também quando o agente o roda; a saída
  dele que o job imprime fica entre `::stop-commands::`; o agente não edita `.git/`; e o git do
  passo que comita e empurra, que tem o token no ambiente, ignora os hooks e o fsmonitor do
  repositório;
- o prompt nomeia a skill e pede as linhas `Causa:` e `Prova:`;
- a última linha de cada uma, em lista ou em negrito, vai no commit e no topo do PR como texto
  inerte: sem controle nem crase, até 300 caracteres, UTF-8 válido, entre crases e com o rótulo
  "escrita pelo agente". Sem causa, o PR avisa;
- a correção que muda o que o gate roda (`package.json`, `pyproject.toml`, `conftest.py`, a
  config do jest ou do vitest e afins) ganha um aviso no topo do PR e no job: passar mudando o
  gate pode ser o gate afrouxado.

**No eval de tarefa:** a `t13-investigar-total-errado` traz só o sintoma, e a causa está longe
dele. Junto vem a checagem nova `ausente`.

**No `ciclo.py`, nada muda.** No `atacando_premissa_*`, o `/entregar` aponta para o método, e a
premissa escrita é a hipótese confirmada.

### 2. Fonte primária salva

**Skill `/pesquisar`, dono Rafael**, com o Thiago nas integrações. O método:

- achar a versão que o projeto usa e ler a fonte primária dessa versão;
- separar fato (com fonte, versão e data) de inferência;
- salvar em `docs/pesquisa/<assunto>.md`;
- quem decide a partir da pesquisa cita o caminho dela.

**Em `docs/pesquisa/`, e não em `contextos/pesquisa/` como se pensou antes.** `contextos/` é
convenção do projeto. Texto de terceiro ali ganha peso de regra, e a triagem do CI lê a pasta
inteira como contexto. Além disso, o `prova.py decisoes` contaria cada pesquisa como decisão
tomada depois da SPEC.

**`prova.py fontes [SPEC-NNN]`**, sem rede:

- confere a forma de cada pesquisa: data válida e não futura, resposta, cada fato com fonte,
  versão e data, nenhum segredo;
- acha as citações a `docs/pesquisa/` que apontam para arquivo que não existe, em todo `.md`;
- com o id de uma SPEC, lista as pesquisas que ela cita e as que mudaram depois da aprovação
  (pela data de autor do commit, que um rebase não muda);
- pesquisa com mais de 180 dias vira aviso;
- também entra no `guardrail.py verificar`, onde nasce em aviso, como as classes novas de antes
  (`{"modos": {"fontes": "bloqueio"}}` endurece).

A primeira pesquisa da fábrica é a desta decisão: `docs/pesquisa/claude-code-user-prompt-submit.md`.

### 3. "Pronto quando" em cada skill

- **As 21 skills ganham `## Pronto quando`**: de 3 a 7 itens de uma linha, cada um com o
  comando ou o artefato que o prova entre crases, ou com `(gate humano)` quando quem decide é a
  pessoa.
- **`scripts/pronto.py`, sem I/O, guarda a forma num lugar só.** Ele também confere que o
  script citado existe e que o subcomando aparece no código dele. O `release.py check` cobra a
  forma em toda skill.
- **As 19 seções das skills que já existiam foram escritas com contraditório:**
  - um agente escreveu cada uma, partindo de um levantamento do que a skill já exige;
  - dois verificadores tentaram derrubá-la, um pela fidelidade ao texto da skill e outro pela
    forma e pelos comandos;
  - um corretor julgou o que eles acharam.
- **O `guardrail.py conferir` passa a ler o transcript** quando a pessoa pergunta se falta
  algo:
  - acha as skills da fábrica usadas na sessão, pela tool `Skill` ou pelo `<command-name>`;
  - acrescenta o `## Pronto quando` delas à conferência, em blocos inteiros, da skill usada por
    último para a primeira, enquanto couberem nos 10.000 caracteres do `additionalContext`; a que
    não cabe vira uma linha que aponta o `SKILL.md` dela, e nenhum item sai cortado;
  - só aceita nome com o prefixo `kairos-forge:` e que existe em `skills/`;
  - se a leitura falha, a conferência vai sem a lista, e a falha fica na trajetória como
    `guardrail_erro`.
- **A lista de skills da trajetória (`execucao.py`) sai da pasta.** A escrita à mão já não
  tinha o `diagnosticar` nem o `relatar`.

## Prova

**Testes**, todos num git de verdade quando há git:

- **`test_investigar.py`:**
  - o laço nos dois lados;
  - o teste de regressão escrito num arquivo de teste que já existia;
  - o sintoma diferente, a correção que não corrige e o tempo estourado;
  - nenhum worktree sobrando;
  - a marca de depuração, com o `.gitattributes`;
  - a ficha pronta, a incompleta e o "pare e pergunte" que sai 2.
- **`test_fontes.py`:**
  - a forma de cada parte da pesquisa e o segredo no texto;
  - a idade da pesquisa e a citação quebrada em qualquer `.md`;
  - o modo SPEC, com a pesquisa mudada depois da aprovação, comitada ou não.
- **`test_pronto.py`:**
  - a forma, inclusive dentro de bloco de código;
  - toda skill da fábrica na forma;
  - as skills da sessão lidas do transcript, nas duas formas, com nome que não existe e com o
    prefixo de outro plugin;
  - o teto do texto e o `verificar`;
  - a lista de skills derivada da pasta.
- **`test_ci.py`**, sobre o `corrigir`, com cada passo rodado como o runner roda (`bash -eo
  pipefail`):
  - o gate antes e depois, o gate que nem roda (124, 126, 127) e o `PREPARO`;
  - o gate que tenta escrever em `GITHUB_ENV` e afins sem alcançá-los, e a saída dele que não
    vira comando do runner;
  - ainda vermelho, o resumo com o diagnóstico e o fim da saída, sem segredo;
  - a causa no topo do PR e no commit, a última linha em lista, o texto inerte, o aviso quando
    ela falta e quando a correção muda o gate;
  - o hook do repositório que não roda no commit do PR, e roda num commit comum;
  - os logs do gate fora do commit.
- **A pesquisa** cita como fonte do formato do transcript duas linhas reais dele, salvas em
  `docs/pesquisa/anexos/`, e o `test_pronto.py` as lê.

**Revisão adversarial**, depois da primeira versão completa: um revisor pela documentação, um
pelos scripts e um pelo gatilho de CI. O que acharam e foi corrigido: trechos das duas skills
novas perto demais do texto do corno-skills (reescritos com estrutura e palavras próprias); a
marca de depuração de id curto que escapava; a regressão num teste apagado ou renomeado; o
laço inexistente contado como falha; a saída que não era UTF-8; o filho do laço que sobrevivia
ao tempo esgotado; a conferência sem o prefixo da fábrica e cortada no meio de um item; e, no
`corrigir.yml`, tudo o que o item do CI acima descreve.

**Eval:**

- 13 de 13 tarefas distinguem a base da solução.
- Na `t13`, cada errada reprova por um motivo só: o conserto no sintoma, pelo oráculo; o
  conserto sem ficha, pela checagem `arquivo`; o log esquecido, pela `ausente`.

**Claude Code 2.1.328, com o plugin e uma API falsa**, em dois turnos: uma skill da fábrica,
depois "faltou algo?". O pedido do segundo turno chegou à API assim:

- com a skill chamada pelo modelo, a conferência traz o `## Pronto quando` dela. No transcript,
  a chamada é um `tool_use` de nome `Skill` com `input.skill` igual a `kairos-forge:pesquisar`;
- com a skill digitada pela pessoa, também traz. No transcript, ela aparece como
  `<command-name>/kairos-forge:pesquisar</command-name>`;
- sem skill nenhuma, a conferência vem sem a lista.

## Limites

- **O `reproduzir` lê o código de saída e uma regex.** Laço que sai 0 com a saída errada não
  reproduz nada: o laço tem de falhar. Sem `--sintoma`, ele não distingue o problema relatado de
  um vizinho.
- **No `corrigir.yml`, o sintoma não é conferido.** Lá o laço é o gate inteiro, sem regex: o
  gate que falha por outro motivo conta como reprodução.
- **O gate roda código que a correção mudou.** As travas acima tiram dele o segredo, os
  arquivos de comando e os hooks do git do passo do PR, mas o runner é dele enquanto ele roda:
  o resto da defesa é o PR, que nunca vai para a base sem uma pessoa.
- **O `investigacao` confere a ficha e a reprodução, não a verdade da causa.** Quem julga se a
  causa escrita é a verdadeira é o revisor.
- **O `fontes` não acessa a rede.** Link morto e fonte secundária passam. E acusa como segredo
  o exemplo de credencial que a documentação de uma biblioteca traz: passe o `guardrail.py
  ocultar` no arquivo.
- **A `t13` não mede a ordem.** Ela confere a ficha, a causa e o conserto no fim, não que a
  causa foi escrita antes do conserto.
- **O `pronto.py` cobra a forma e o comando existente, não a verdade do item.** A verificação
  adversarial das 19 seções rodou uma vez.
- **A lista na conferência só existe no Claude Code.** O formato do `tool_use` da `Skill` foi
  observado, não está documentado (ver a pesquisa).
- **No `corrigir.yml`, o GATE precisa rodar no runner, com as dependências.** Antes, o PR abria
  mesmo vermelho; agora não abre.
- **A Laura não muda, para não exigir a rodada paga do eval de roteamento.** As skills novas são
  achadas pela description.

## Fora deste ADR

Achados do mapeamento que já existiam e ficam para outra tarefa:

- **`ciclo.py`:**
  - o `atacando_premissa_*` não é alcançado com o orçamento padrão de 2 rodadas (o
    `LIMIAR_PREMISSA` é 3);
  - o `registrar pr_aberto` não confere que o PR existe;
  - a faixa 3 da revisão não é lida.
- **`/onboardar`:** gera `contextos/testes.md` em tabela, mas o `guardrail.py gates_declarados`
  só lê lista com crase.
- **`painel.py _secao`:** não ignora bloco de código.
- **`guardrail.py verificar`:** acusa o próprio `scripts/guardrail.py` como gerado, porque ele
  contém a marca de arquivo gerado.
- **Tucano:** os corpos citam `forge-<x>` de skills que não estão no time.
- **`prova.py pre-patch`:** conta erro de import como `falhou_na_base`.

Achados de quem escreveu e verificou o `## Pronto quando` de cada skill, fora da seção. Cada
um é uma frase da skill que discorda de outra, de um script ou de um ADR:

- **`/onboardar`:** cita o "ADR-E003", que não existe; o objetivo não lista `decisoes/log.md`,
  `.agents/memory/` nem `.agents/grafo/`.
- **`/analisar-ameacas`:** diz que o artefato vai para a SPEC ou para `decisoes/`, e salva em
  `docs/seguranca/`; não diz quem aceita o risco.
- **`/evoluir`:** diz que produz a SPEC, e produz o EVOL; a saída para o `/otimizar` não tem
  tipo no EVOL.
- **`/lancar`:** não menciona a pausa da faixa 3 no deploy (ADR-0052); pendência e pós-mortem
  sem lugar de registro.
- **`/avaliar`:** o `custo-eval --teto` conta versão sem caso medido como variação 0; o texto
  superestima o que o `prova.py selado` pega.
- **`/mapear-arquitetura`:** diz que só lê, e roda o `grafo.py codigo`, que escreve.
- **`/otimizar`:** o `git reset --hard` vem antes de registrar a rodada.
- **`/auditar`:** dá 4 pontos de segurança com saída 0, mas achado médio também sai 0; o
  `check-agent-security.py` não varre o bloco `hooks` de `.claude/settings*.json`; o template de
  CI proíbe a escrita que a skill manda fazer.
- **`/relatar`:** sugere o `painel.py --html`, que escreve arquivo.
- **`/revisar`:** o `contrato.py` aceita `achados` vazio com críticos.
- **`/diagnosticar`:** o `grafo.py codigo` sem `--raiz` extrai a árvore errada fora da pasta
  atual.
- **`/mapear-conhecimento`:** o `grafo.py validar` aceita entidade com `"fontes": []`.
- **`/rodar`:** a POC em `.worktrees/` conta como produção para o gate de parada; o debate vai
  para `docs/decisoes/`, fora do que o `prova.py decisoes` lê.
- **`/mobilizar`:** "pronto só com gate rodado", mas o `concluir` aceita `--gate-pulado`; sem
  foto no `iniciar`, a posse não é conferida; o quadro sem tarefas pode ser encerrado.
- **`/desenhar`:** dois caminhos para o `DESIGN-NNN`; o `painel.py` e o `guardrail.py`
  discordam sobre a SPEC sem mapa.
- **`/entregar`:** o `contrato.py` declara que a faixa 3 nunca fecha por evidência, e nenhum
  código aplica isso.
- **`/validar`:** o `corroborar` aceita substring nos dois sentidos.
- **`/especificar`:** a numeração dos checkpoints está desatualizada; o modelo de confirmação do
  passo 8 não mostra a crítica, os inferidos, o confiado nem o não prometido.
- **`/migrar`:** o `modo-rfc.md` manda o ADR para `decisoes/`, e o resto da fábrica usa
  `docs/adr/`.
