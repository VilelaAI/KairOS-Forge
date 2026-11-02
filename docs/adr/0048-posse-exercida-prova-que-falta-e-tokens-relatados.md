# ADR-0048 — Posse exercida, prova que falta, re-revisão que presta contas e tokens relatados

- **Status:** aceito
- **Data:** 2026-11-02
- **Versão:** v0.41.0

## Contexto

A [Alethe Orchestrate](https://github.com/Kc1t/alethe-orchestrate-skill) (MIT, só stdlib) é uma
skill que orquestra Claude Code, Codex, Antigravity, Kimi e outras CLIs como workers sem
interface, em ondas, e mede o que cada um gastou. O núcleo dela é um executor de workers de
5.783 linhas, e esse núcleo não entra aqui. Spawnar CLIs é runtime, e a fábrica é plugin
(ADR-0001); o `/mobilizar` usa os subagentes nativos de cada CLI, e a delegação entre
harnesses já tem casa no Tucano (ADR-0047) e no kairos-symphony.

Em volta do executor há quatro mecanismos que cobrem lacunas da fábrica:

1. **O `concluir` não olhava o checkout.** O `quadro.py` confere colisão de posse no
   planejamento e exige evidência e gate na conclusão, mas nunca viu o que a tarefa de fato
   mudou. Em três lugares, "o consultivo não edita código" é só instrução:
   - no Codex, o `apply_patch` sobrevive à allow-list, e o perfil de agente não aceita
     `sandbox_mode` (ADR-0035);
   - no Cursor, a allow-list degrada para `readonly`;
   - no Tucano, a regra está no preâmbulo (ADR-0047).
2. **Falta de prova e falha mostrada davam no mesmo lugar.** O `/validar` marca "sem
   evidência" na matriz, mas o bloco `kairos-validacao` juntava tudo em `bloqueado`, e o
   `ciclo.py` mandava o construtor mexer no código quando o que faltava era rodar a checagem.
3. **A re-revisão começava do zero.** Depois de `corrigindo_revisao`, nada obrigava a nova
   revisão a dizer o que aconteceu com cada 🔴 da rodada anterior. Revisão limpa que esquece um
   🔴 é a mesma ausência de busca que a prova de cobertura recusa (ADR-0032).
4. **O ledger não media tokens.** O `quadro.py ledger` terminava com "O plugin não mede tokens
   de dentro da sessão. Custo real: /cost." Mas todo hook do Claude Code recebe o
   `transcript_path`, e o transcript registra o uso de cada resposta do modelo.

## Decisão

### 1. Posse exercida, conferida no git

Vem do `readOnlyViolation` da Alethe.
- **No `iniciar`:** o `quadro.py` tira uma foto do checkout, com o HEAD e o `git status`
  (cada arquivo listado com o sha256 do conteúdo). Com worktree, a foto é do worktree
  (`--checkout`).
- **No `concluir`:** compara com uma foto nova. O que mudou entre as duas, inclusive o que
  entrou em commit, e não cabe na posse da tarefa nem na das que trabalharam junto, recusa a
  conclusão. Para seguir, desfaça o que não era da tarefa ou conclua com
  `--fora-da-posse "motivo"`; o motivo fica registrado e aparece no ledger.
- **`--leitura`:** declara a tarefa que só lê. A posse dela é vazia, então qualquer arquivo
  mudado fica fora da posse.
- **Quem trabalhou junto:** sai da ordem do histórico do quadro, não do relógio. Os carimbos
  têm resolução de segundo, e o primeiro teste pegou uma tarefa que concluiu no mesmo segundo
  em que outra começou e foi tratada como vizinha.
- **Ficam fora da foto** o que script e hook escrevem: o próprio quadro, a trajetória e o
  estado do ciclo.

### 2. `sem_evidencia` na validação e o estado `provando`

Vem do PASS / FAIL / NOT_PROVEN da Alethe.
- **No bloco:** `kairos-validacao` ganha o campo opcional `sem_evidencia`, que diz quantos
  bloqueios são falta de prova. Ele nunca passa de `bloqueios`.
- **No ciclo:** quando todos os bloqueios são falta de prova, a validação bloqueada vai para
  o estado novo `provando`, e não para `corrigindo_validacao`.
- **Em `provando`:** roda-se a checagem que falta, ou o Ricardo escreve o teste, antes de
  mexer no código de produção. Se a prova falhar, a validação seguinte mostra a falha, e aí
  vem a correção.
- **Orçamento:** a rodada conta como qualquer bloqueio.

### 3. A re-revisão presta contas

Vem do ADDRESSED / NOT ADDRESSED da Alethe.
- **No bloco:** `kairos-revisao` ganha `achados` (um id por 🔴) e `anteriores`
  (`{id: resolvido | nao_resolvido}`). Um `nao_resolvido` exige veredicto `bloqueado`.
- **Entre rodadas:** o `ciclo.py` guarda os ids de uma revisão bloqueada em
  `pendentes_revisao` e recusa `limpo` enquanto algum não estiver marcado como `resolvido`.
  Um novo `critico` carrega adiante os não resolvidos junto com os novos.
- **Por que no estado do ciclo:** o relatório do mesmo dia sobrescreve o anterior, então o
  arquivo não serve de memória.

### 4. Tokens relatados, nunca estimados

Vem do "gasto real, nunca estimado" da Alethe.
- **Na sessão:** o `Stop` grava na trajetória o uso acumulado da sessão, lido do transcript.
  Cada resposta conta uma vez: uma resposta vira várias linhas com o mesmo `message.id`, e
  num transcript real 955 linhas eram 387 respostas.
- **No vínculo:** o worker roda `quadro.py vincular <slug> <T>` da própria sessão. O comando
  só lê o quadro, e o hook grava a sessão de quem o rodou.
- **Na atribuição:** o gasto entre uma leitura e a seguinte vai para a tarefa vinculada
  naquele momento.
- **No ledger:** tokens por teammate, e a divisão entre tarefa concluída, desfeita (por
  compensação, ADR-0036), em aberto e sem tarefa vinculada.
- **Cache lido:** vem à parte. É relido a cada resposta, domina a soma e custa uma fração.
- **Worktree:** a trajetória de um worktree ligado passa a ir para o checkout principal. Antes
  ela sumia com o worktree descartável (ADR-0024); o guardrail lê da mesma pasta.
- **Dinheiro:** fica fora, como no ADR-0044. Se um dia entrar, vale a regra da Alethe: preço
  só com fonte oficial e data.

### Versões de contrato

| Contrato | Antes | Agora | O que entrou |
|---|---|---|---|
| `contrato.py` | 1.1 | 1.2 | `sem_evidencia`, `achados`, `anteriores` |
| `ciclo.py` | 1.2 | 1.3 | estado `provando`, campo `pendentes_revisao` |
| `quadro.py` | 1.1 | 1.2 | `--leitura`, posse exercida, `vincular`, `concluida_em` |

Tudo é aditivo: relatório e quadro antigos continuam válidos, e a assinatura foi refeita
(ADR-0034).

## Consequências

- **"O consultivo não edita" passa a ser conferido depois do fato** nos CLIs em que era só
  instrução. Ele não impede a escrita; impede que ela passe despercebida.
- **Checkout compartilhado tem falso positivo.** Uma edição da líder no meio da onda, numa
  SPEC por exemplo, cai na tarefa que estiver em voo. O `--fora-da-posse` resolve, com
  registro. Com worktree por teammate a atribuição é exata.
- **A correção deixa de mexer no código por falta de prova,** o que tira uma fonte de
  mudança sem motivo na produção.
- **Os ids de 🔴 são opcionais no contrato,** porque obrigar seria mudança maior. O
  `/revisar` passa a pedi-los; revisão sem ids não cria pendência.
- **Tokens só no Claude Code.** No Codex não há hook de `Stop` na fábrica, e no Cursor e no
  OpenCode o formato não foi conferido. Nesses CLIs o número sai "não medido", nunca 0.
- **O vínculo depende do worker rodar `vincular`.** Sessão sem vínculo conta em "sem tarefa",
  e o número fica visível, não escondido.

## Alternativas consideradas

- **Trazer o executor de workers entre CLIs.** Recusado pelo ADR-0001. Se o kairos-symphony
  ganhar suporte ao Codex, a tabela de flags da Alethe é a referência:
  - Claude: `--permission-mode plan` para só leitura, `acceptEdits` para escrita;
  - Codex: `--sandbox read-only` para só leitura, `workspace-write` para escrita;
  - em ambos, sem MCP e com os subagentes desligados.
- **Checar a cota antes de abrir uma onda.** Adiado. Depende do formato interno dos arquivos de
  cada CLI, que muda sem aviso.
- **Playbooks em YAML, modo "sempre ligado" e painel com posições.** Recusados:
  - os playbooks seriam uma segunda linguagem de plano ao lado do `ciclo.py`;
  - o modo "sempre ligado" é contexto pago em toda interação, que o ADR-0038 cortou;
  - o painel com posições duplica o `rodar debate` (ADR-0018).
