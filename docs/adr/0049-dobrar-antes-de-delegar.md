# ADR-0049 — Dobrar antes de delegar: subagente só onde ganha o contexto

- **Status:** proposto. Os critérios, o eval e a auditoria valem já; as mudanças de comportamento
  esperam a linha de base do eval e a sua concordância com os veredictos.
- **Data:** 2026-11-03
- **Versão:** v0.43.0

## Contexto

O artigo da Anthropic *Building agents: when to fold subagents into your main agent loop*
(out/2026) e o [single-agent-loop-kit](https://github.com/anthropics/single-agent-loop-kit)
(Apache 2.0) relatam algo que a equipe de IA aplicada viu em várias implantações: um agente só,
com skills e ferramentas carregadas sob demanda, muitas vezes supera tanto o prompt único quanto
o desenho com subagentes. Supera em qualidade e, com frequência, também em custo e latência.

Subagente continua valendo em três casos:
- o loop principal incha com o que ele lê;
- trabalho paralelo, ou verificação independente;
- conflito de ferramentas que skills não resolvem.

Persona própria, dono diferente, prompt longo e passos fixos não são motivo. O artigo chama de
lei de Conway a arquitetura que copia o organograma.

A fábrica tem 71 personas em 11 times e 10 squads. A auditoria
([`docs/loop-unico/AUDITORIA.md`](../loop-unico/AUDITORIA.md)) mostrou um retrato diferente do
organograma:
- **17 das 18 skills não abrem subagente.** A persona fala no mesmo contexto, e o arquivo dela
  não é lido.
- **Só o `/mobilizar` abre subagente,** em onda paralela.
- **A verificação não é independente.** A crítica adversarial, a revisão e a validação, que
  pelo próprio critério do artigo deveriam ganhar contexto independente, fazem papel no mesmo
  contexto que produziu o artefato. A independência é cobrada pelo nome da persona, não pelo
  contexto.

Faltava também o número que decide: nenhum eval media se a tarefa ficou pronta.

## Decisão

### 1. Critério escrito para delegar

Uma skill só abre subagente quando vale um dos três casos do artigo, e diz qual. Fora deles, o
papel entra no loop principal, e o conhecimento da persona entra como `references/` carregável.
O critério vale para o que for escrito daqui em diante. O que já existe muda pela lista de
trabalho da auditoria, um item por vez.

### 2. Eval de tarefa concluída de ponta a ponta

O `evals/tarefas-fabrica/` (dogfooding, não distribuído) tem oito tarefas:
- três de corrigir, duas de construir (uma é o arco inteiro do `/entregar`), duas de verificar
  (com defeitos plantados) e uma de perguntar;
- todas sobre o `relatorio-vendas`.

O que decide se a tarefa ficou pronta é código:
- o oráculo escondido;
- as checagens lidas do disco (bloco de contrato válido, estado do ciclo, arquivo intocado,
  resposta que pergunta).

`rodar.py validar` roda no CI, sem modelo e sem custo. Ele exige três coisas de cada tarefa:
- o projeto como está é reprovado;
- a solução de referência é aprovada;
- cada solução errada conhecida é reprovada.

A rodada paga (`rodar.py rodar`) usa `claude -p` com o plugin por `--plugin-dir` e sem as
configurações de quem roda. Ela grava rota de subagentes, skills, tokens e duração por tarefa e
rep. O `comparar` lista o que piorou, o que melhorou e onde a rota mudou.

### 3. Auditoria com veredicto por persona

O `docs/loop-unico/inventario.tsv` dá a cada persona um veredicto, com evidência e confiança:

| Veredicto | Personas |
|---|---|
| `principal` | 1 |
| `como-ferramenta` | 36: 18 na verificação, 16 só na onda paralela, 2 leitores pesados |
| `juntar` | 22, em 7 squads de apoio |
| `dobrar` | 12 |

A `AUDITORIA.md` ordena a lista de trabalho:
1. linha de base;
2. verificação isolada;
3. juntar o apoio;
4. correção no loop do `/entregar`;
5. dobrar o resto;
6. o Tucano de 7 para 3.

### 4. Nada muda sem medida

Cada item da lista é uma variante do eval, comparada com a última que ficou. Fica só se a
tarefa concluída não piorar. Toda rodada paga pede ok, com tamanho e estimativa de tokens.

## Consequências

- **A primeira mudança provável vai contra a tese do artigo:** mais subagente, não menos, na
  verificação. É o caso que o próprio artigo defende, a verificação às cegas, e a fábrica não
  fazia.
- **O organograma de 71 personas continua como identidade e como dono de conhecimento,** mas
  deixa de ser arquitetura. Personas juntadas ou dobradas viram `references/`, não somem do texto.
- **O eval de roteamento perde peso à medida que as personas dobram.** O artigo trata a precisão
  de roteamento como métrica de transição; depois da dobra, a pergunta passa a ser se o loop
  carregou a skill ou a reference certa.
- **A rodada paga tem custo e precisa do Claude Code autenticado** numa máquina descartável
  (`bypassPermissions` numa pasta temporária). Por isso ela não está no CI, só a validação seca.
- **O tráfego da auditoria é inferido do texto.** O real viria dos eventos de delegação do
  `execucao.py` nos projetos dos usuários, e juntar isso é outro passo.

## Alternativas consideradas

- **Dobrar direto, sem eval.** Recusado. O artigo e o kit insistem em medir antes, e o caso do
  agente de suporte deles mostra por quê: uma dobra baixou a latência e quebrou um processo que
  passava, o que só apareceu numa de duas rodadas.
- **Usar o kit como está.** O kit lê código de orquestração e espera traces de produção. A
  orquestração da fábrica é prosa nas skills, e as tarefas precisam do projeto e das checagens
  da fábrica (contrato, ciclo). Ficaram o desenho em variantes, a comparação por tarefa e a
  regra de uma mudança por vez; o código é próprio.
- **Juiz-LLM para a qualidade da crítica e da revisão.** Adiado. Defeito plantado e regex pegam o
  essencial sem juiz. O juiz entra pela higiene do `/avaliar` quando o eval crescer.

## Nota (v0.43.0): o que mudou depois da auditoria

O `/relatar` (ADR-0050) entrou depois desta auditoria, com a Talita falando no contexto principal, no mesmo padrão das outras: hoje são 18 das 19 skills sem subagente. A linha da Talita no inventário passa a citar a skill; o veredicto dela não foi reavaliado.

## Emenda (v0.50.5): tarefas de verificação que separam as variantes

Na linha de base, a fábrica acertou a `t04` e a `t05` em todas as rodadas. Com isso, a variante
1 (verificação isolada) não tinha como mostrar ganho nelas. E as duas só mediam o acerto, não o
bloqueio à toa, que a verificação isolada também pode aumentar.

O eval ganha três tarefas de verificação e uma checagem:
- **`t09-revisar-caminho-absoluto`:** o validador do diff recusa `..` mas deixa passar o caminho
  absoluto, os testes do diff passam, e há uma isca (`subprocess` com lista e `--`);
- **`t10-revisar-sem-defeito`:** um diff correto e testado, com iscas, em que o certo é aprovar com
  a lista do que foi examinado;
- **`t11-criticar-spec-sutil`:** uma SPEC com um critério de um sentido só (ADR-0053) e uma matriz
  que aponta o requisito para um teste que mede outra coisa, mais um requisito incomum mas bem
  feito como isca;
- **a checagem `bloqueios`:** lê só os achados bloqueantes do relatório e cobra os dois lados, o
  defeito plantado em `exige` e a isca em `proibido`.

Cada tarefa tem soluções erradas conhecidas, e o `rodar.py validar` (CI, sem modelo) exige que
todas sejam reprovadas. A variante 1 passa a ser medida em `t04`, `t05`, `t09`, `t10` e `t11`.
Ela só fica se não piorar nem o acerto nem o bloqueio à toa.

A linha de base precisa rodar de novo, agora com 11 tarefas, antes da variante 1. A rodada é
paga e pede ok.

Duas mudanças de apoio:
- **O `checar` do runner virou uma tabela, com uma função por tipo de checagem.** Ele era legado
  acima do limite do CRAP (CC 25), e o tipo novo o faria piorar. Agora tem CC 2.
- **Os fixtures das tarefas saem das medidas do `qualidade.py`.** No `.gitattributes`, ficam como
  `linguist-vendored`. São o projeto, a mudança com o defeito plantado e as soluções erradas de
  propósito, e medir CRAP e mutação de código escrito para estar errado não diz nada.

**Prova.**
- Contra o runner da `main`, as três tarefas são reprovadas no `validar`, e falham os 7 testes
  novos ou alterados do runner: a checagem `bloqueios`, a lista de valores, o branch da tarefa e
  as contagens. O teste que conferia "8 de 8" passou a contar as tarefas da pasta, com piso de
  11.
- Cada solução errada cai pelo motivo certo:
  - a revisão que só vê o `..` cai por "não bloqueou o caminho absoluto";
  - a que bloqueia o `subprocess`, por "bloqueou à toa";
  - a que bloqueia a divisão já protegida, pelo veredicto;
  - a que mexe no código, por "intocado";
  - a crítica que acha um defeito só, por "não bloqueou REG-03";
  - a que bloqueia o REG-04, por "bloqueou à toa".
- Os testes do diff da `t09` passam, e `servir_relatorio('/etc/hostname')` lê fora da pasta: o
  buraco é real.
- A mutação do `qualidade.py` sobre o runner mata 34 de 34. Os 3 sobreviventes da primeira
  rodada eram asserções que faltavam e viraram teste.
