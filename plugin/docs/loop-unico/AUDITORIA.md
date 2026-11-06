# Auditoria: subagente ou loop principal (ADR-0049)

Auditoria das 71 personas e dos pontos em que as 18 skills acionam alguém. Os critérios
vêm do artigo da Anthropic *Building agents: when to fold subagents into your main agent
loop* e do [single-agent-loop-kit](https://github.com/anthropics/single-agent-loop-kit)
(Apache 2.0). Um subagente só ganha contexto próprio em um destes três casos:

1. **Contexto:** ele lê muito mais do que o loop principal precisa depois.
2. **Trabalho paralelo ou verificação independente:** várias frentes em contextos
   descartáveis, ou alguém confere o trabalho de outro sem ver como foi feito.
3. **Conflito de ferramentas ou de instruções** que skills não resolvem.

Não contam como motivo:
- a persona ter voz própria;
- ser de outro time;
- o prompt ser longo;
- ter muitas ferramentas;
- ter passos fixos (passo fixo é código).

**Status:** veredictos propostos; falta a sua concordância. Nenhuma mudança de comportamento
foi feita. O inventário completo, uma linha por persona com evidência e confiança, está em
[`inventario.tsv`](inventario.tsv).

**Depois da auditoria (v0.43.0).** O `/relatar` (ADR-0050) entrou depois desta auditoria, com a Talita falando no contexto principal, no mesmo padrão das outras: hoje são 18 das 19 skills sem subagente. A linha da Talita no inventário passa a citar a skill; o veredicto dela não foi reavaliado.

## Como a fábrica delega hoje

O retrato é diferente do organograma de 71 personas:

- **17 das 18 skills não abrem subagente.** Elas fazem a persona falar no mesmo contexto: "acionar
  especialistas conceitualmente" (`skills/validar/SKILL.md:161`), "cada agente acionado se
  apresenta" (`skills/rodar/SKILL.md:57`), "Laura aciona o(s) arquiteto(s)"
  (`skills/especificar/SKILL.md:46`). Nenhuma delas manda ler o arquivo da persona: os
  41.731 tokens de `agents/` só entram quando a persona vira subagente de verdade.
- **Só o `/mobilizar` abre subagente.** São os teammates em onda paralela, via `Agent`,
  `spawn_agent` ou `task` (`skills/mobilizar/references/capacidades-por-cli.md:78`).
- **As 71 descrições vão na lista de agentes do Claude Code** (8.786 caracteres) e nos papéis
  do Codex. O modelo pode delegar por conta própria a qualquer uma delas. É essa escolha que o
  eval de roteamento mede, com 68 casos.
- **No Tucano (ADR-0047), sete agentes em contextos separados passam o bastão.** É o único
  lugar em que a fábrica é multiagente de ponta a ponta.

## Veredictos

| Veredicto | Personas | Confiança | Por quê |
|---|---|---|---|
| `principal` | 1 (Laura) | alta | A sessão do usuário já faz o papel dela: triagem e roteamento no contexto principal |
| `como-ferramenta`, verificação | 18 | alta | Critério 2: crítica, revisão, validação, juiz e painel só valem se não viram a produção |
| `como-ferramenta`, paralelo | 16 | média | Critério 2, mas só na onda do `/mobilizar`, com worktree. Fora dela, o conhecimento entra no loop como reference |
| `como-ferramenta`, leitura | 2 (Olívia, Rafael) | baixa | Critério 1, a confirmar medindo quanto o grafo e o diagnóstico leem |
| `juntar` | 22, em 7 squads de apoio | baixa | Squads de 3 ou 4 personas com descrições vizinhas e sem papel que ganhe contexto. 16 delas não aparecem em nenhuma skill |
| `dobrar` | 12 | média/baixa | Conhecimento de domínio sem nada que peça contexto separado. 4 delas (Aline, Gael, Igor, Nina) não aparecem em nenhuma skill |

Em tokens de prompt, o que vai para `juntar` (16.689) e `dobrar` (5.614) é mais da metade
dos 41.731.

## Achados

### A. A verificação não tem o contexto independente que exige

Este é o achado principal, e vai na direção contrária à tese do artigo: aqui falta
subagente, não sobra.

- **Crítica adversarial:** pede críticos "que não a escreveram" e escolhe entre "as personas
  que não participaram da redação"
  (`skills/especificar/references/critica-adversarial.md:9-17`). Numa sessão só, o mesmo
  contexto que escreveu a SPEC faz o papel dos dois críticos. A referência cita Huang et al.
  para recusar exatamente essa autocorreção.
- **Contrato da crítica:** cobra dois nomes distintos em `criticado_por`
  (`scripts/contrato.py`), não dois contextos. A independência é nominal.
- **Revisão:** "acionar revisores em paralelo (se possível)" (`skills/revisar/SKILL.md:85`).
  Sem o "possível", o revisor é o mesmo contexto que construiu.
- **Validação no `/entregar`:** a mesma sessão constrói e valida
  (`skills/validar/SKILL.md:161`).
- **O que já existe para resolver:** o kit dá a verificação às cegas como exemplo do que ganha
  contexto, e a Alethe diz o mesmo do validador ("numa sessão nova, nunca a do autor"). A
  peça de encaixe já existe: os blocos `kairos-critica`, `kairos-revisao` e `kairos-validacao`
  são o resultado estruturado que um subagente chamado como ferramenta devolve.
- **Medida:** as tarefas `t04`, `t05`, `t09` e `t11` do eval têm defeitos plantados e medem se a
  crítica e a revisão os acham. A `t09` e a `t11` também têm iscas, e a `t10` não tem defeito:
  as três medem se elas bloqueiam à toa.

### B. O conhecimento das personas não entra quando elas fazem papel no contexto

Quando a skill aciona a Helena "conceitualmente", o modelo fala como Helena com o que a skill
diz dela, não com o que está em `agents/helena-security.md`. Dobrar uma persona em
`references/` carregável pela skill passa a usar esse conhecimento no loop principal, sem
abrir contexto. A barreira de entrada é baixa: é texto que já existe.

### C. 20 personas que nenhuma skill cita

16 de apoio e 4 de plataforma (Aline, Gael, Igor, Nina) só são alcançadas pelo roteamento. Isso é o
organograma virando arquitetura (a lei de Conway, citada no artigo):
- cada squad de apoio tem 3 ou 4 personas vizinhas, como Naming (Bruno, Cora, Elisa),
  Microcopy (Celina, Ingrid, Letícia, Renato) e Narrativa (Dante, Helena, Marcos);
- todas disputam a mesma lista de 71 descrições que o modelo usa para escolher.

### D. O pacote do Tucano é o telefone sem fio

São sete agentes passando o bastão em trechos de três respostas (ADR-0047, item 7):
- Joana e Laura trabalham uma em cima da saída da outra, o que pede `juntar`;
- Lucas, Marina e Ricardo escrevem na mesma pasta, sem worktree, então não há ganho de
  paralelismo e o certo é `dobrar` no construtor;
- Helena e Patrícia no Codex são verificação de outra família e ficam.

O experimento entra numa variante própria do eval, depois da linha de base.

## A "cola": o que decide quem roda

- A regra de acionamento da Laura em `templates/squad-fabrica.yaml` (por nível) e a triagem do
  `/rodar` (`skills/rodar/SKILL.md:55`).
- As 71 `description` na lista de agentes (ADR-0038 já as cortou de 19 mil para 8,8 mil
  caracteres).
- Os papéis do Codex e do OpenCode gerados pelo sync, e o preâmbulo do Tucano com o bastão.

A maior parte é prosa. Ela some à medida que personas viram `references/`, sem script novo.

## Notas dos prompts

- **Regra que é limite duro já mora em código:** guardrail, ciclo, quadro e contrato. O ADR-0048
  passou a conferir no git o "consultivo não edita". Não sobrou regra crítica só em prosa.
- **Voz e persona:** "cada agente acionado se apresenta" em primeira pessoa (`/rodar`,
  `/validar`, `/revisar`, `/lancar`). Pelo kit, um agente tem uma voz, e cada apresentação custa
  tokens em toda resposta. É identidade de produto, então a decisão é sua (pergunta 1).
- **Instruções sobre outros agentes** ("pede pro Carlos antes de continuar"): somem com a dobra,
  porque o loop principal carrega a reference do Carlos.

## Lista de trabalho

Cada item é uma variante do eval (`evals/tarefas-fabrica/`), comparada com a última que ficou.
Fica só se não piorar a tarefa concluída.

- [ ] **0. Linha de base** (`base`): as 11 tarefas, 2 reps, depois de uma sonda pequena para
  medir tokens. Precisa do seu ok para gastar.
- [ ] **1. Verificação isolada** (`v1-verificacao-isolada`): crítica e revisão em subagente de
  contexto limpo, que recebe só o artefato e o critério e devolve o bloco de contrato. Achado A.
  Medido em `t04`, `t05`, `t09`, `t10` e `t11` (o acerto e o bloqueio à toa), com custo extra
  em tokens.
- [ ] **2. Juntar o apoio** (`v2-apoio-juntado`): os 7 squads de apoio sem papel viram uma
  persona cada. Achado C. Medido pelo eval de roteamento e por todas as tarefas, para ver se
  nada piora.
- [ ] **3. Correção no loop** (`v3-correcao-no-loop`): o loop de correção do `/entregar` carrega
  as references dos agentes nomeados em vez de repassar. Achado B. Medido em `t02`.
- [ ] **4. Dobrar o resto** (uma variante por grupo): as 12 personas `dobrar` viram
  `references/` das skills que as citam.
- [ ] **5. Tucano 7 → 3** (`v5-tucano-enxuto`): achado D, num eval à parte rodando no app.

## Perguntas abertas para o dono

1. A voz em primeira pessoa ("Diego aqui, Arquiteto de Sistemas") é identidade de produto que
   fica, ou pode virar só um rótulo?
2. A verificação isolada custa mais tokens por gate. Aceita esse custo, se o eval mostrar que
   ela acha mais defeito?
3. Verificação de outra família dentro do Claude Code: dá para contar com o Codex (`codex exec`)
   na máquina de quem usa, ou o padrão é contexto limpo da mesma família, declarado?
4. As 20 personas que nenhuma skill cita continuam como destino de roteamento, ou podem sair
   depois de juntadas?

## O que fica como está, e por quê

- **Os teammates do `/mobilizar` em onda paralela com worktree** são o caso de uso que o artigo
  defende.
- **O `/avaliar` já exige juiz de família diferente e cego à versão** (ADR-0031/0043).
- **A camada determinística** (ciclo, quadro, guardrail, contratos) é o que o artigo chama de
  limites no harness e nas ferramentas.

## Limites desta auditoria

- **Tráfego inferido do texto das skills, não medido.** Os eventos de delegação que o
  `execucao.py` grava nos projetos dos usuários dariam o tráfego real e as cadeias. Juntar isso
  é um passo à parte.
- **Mapa de papéis lido à mão** de cinco pontos: crítica, revisão, validação, juiz e painel.
  Uma persona pode ter papel que não está escrito na skill.
- **Nomes compartilhados conferidos um a um:** Helena, Marcos e Elisa existem duas vezes cada.
