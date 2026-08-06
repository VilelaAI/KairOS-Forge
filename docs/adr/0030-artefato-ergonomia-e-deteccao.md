# ADR-0030 — Artefato ajustado ao resultado, ergonomia de guardrail e detecção em voo

- **Status:** aceito
- **Data:** 2026-08-02
- **Versão:** v0.22.0

## Contexto

Duas fontes externas foram analisadas na mesma semana, e os achados aproveitáveis das duas
caíram nas **mesmas três famílias** — daí um ADR só em vez de dois.

**Fonte 1 — "How to Build Your First Agent Factory"** (@Av1dlive, jul/2026). Artigo
promocional da Sage API; a tese arquitetural é separável do pitch e é boa. A central
confirma o programa L4: *"você trava no número de agentes que consegue assistir
pessoalmente; modelo melhor não move esse teto — ele move quando algo que não é você
consegue dizer não."* Ressalva registrada: o próprio autor admite que o worker nunca rodou
com chave de modelo (*"logged as offline"*) — ele demonstrou a linha, não os agentes nela.

**Fonte 2 — "Ferramentas de IA para Gestão de Projetos"** (Prof. Ahirton Lopes, UNIPDS,
10 módulos). Curso de gestão assistida por chat model. A maior parte mapeia em agentes que
já existem (Hugo, Breno, Iara, Talita) ou exige integração que um plugin não tem (Jira,
Slack, ata de reunião). O valor está nos catálogos de armadilha, que são de campo.

O que ficou de fora, e por quê: Sage API (somos stdlib-only e multi-CLI por desenho),
stamp master→variante e "agente certificado como produto" (nossas 71 personas são fixas
por regra), router como proxy no caminho do modelo (um plugin não senta ali), módulos de
reunião e Jira/Slack (território da ponte Hermes), portfólio multi-projeto.

## Decisão

### Família A — Artefato ajustado ao resultado

O mesmo Goodhart que o ADR-0022 fechou para o *medidor*, agora fechado para o *artefato*.

**A1. Conjunto selado no `/avaliar`.** O gold set se divide em visível (~60%, onde se
ajusta) e selado (~40%, onde se decide) — e **só o selado aprova**. Sem a divisão, o loop
é: roda a suíte, lê as falhas, ajusta até passar, aprova; um sistema ajustado ao próprio
teste. Rotação obrigatória, porque selado que nunca muda vira visível por osmose. E a
divergência entre os dois vira o sinal mais valioso do eval: visível em 95% com selado em
70% não é ruído amostral, é ajuste ao teste — medido.

**A2. Digest de certificação.** O `sha256` do artefato avaliado entra no relatório.
Artefato com digest diferente = eval vencida. É o que dá dente ao A1: sem digest, ajustar
o prompt depois da rodada selada custa zero (basta não mencionar); com digest, custa uma
reavaliação. A diferença entre uma regra e um lembrete.

**A3. Churn de SPEC no `diagnostico.py`.** Os slides chamam de *frequency of change*:
critério de aceite editado depois de entrar em sprint é scope creep silencioso. A variante
que importa para o harness é mais específica: **commit que altera a SPEC e código de
produção ao mesmo tempo** — a especificação sendo reescrita para casar com o que foi
construído, o `verificado:` pelo avesso. O script conta e reporta; **não julga**, porque
SPEC viva também é revisada por bom motivo.

### Família B — Ergonomia de guardrail

**B1. Recusa entra na trajetória.** Até agora a recusa era invisível: `PreToolUse` sai com
2, a ferramenta não roda, e o `PostToolUse` nunca dispara — a tentativa não existia em
lugar nenhum. Agora o `guardrail.py` grava o evento em `.agents/execucoes/` antes de sair,
o `telemetria.py resumo` reporta por classe, e o `/auditar` pontua.

O bloqueio ter funcionado não zera o fato de o agente ter tentado. **Um agente que passa
na validação alcançando ferramenta que não tem não está passando.**

**B2. Modo `aviso` por classe de regra.** *"Uma regra que falha em 30% dos PRs vai ser
desabilitada em uma semana."* `.agents/guardrails.json` ganha `modo` (global) e `modos`
(por classe): `bloqueio` (default, exit 2) ou `aviso` (exit 1 — o usuário vê, a execução
segue). A promoção não é por gosto: migra para `bloqueio` quando `recusas_em_modo_aviso`
cai, e o número está no `telemetria.py resumo`.

**Os caminhos sagrados nunca degradam.** `.agents/execucoes/`, `.agents/guardrails.json` e
`.agents/ciclo/` seguem em bloqueio incondicional — guardrail que só avisa sobre escrita no
próprio medidor não é guardrail.

### Família C — Detecção em voo

**C1. `execucao.py alerta`.** A fábrica media tudo *depois* e não detectava nada *durante*.
Três padrões, em `PostToolUse`, que avisam sem bloquear:

| Padrão | Gatilho |
|---|---|
| Repetição | mesmo comando, 3 **falhas** seguidas |
| Alternância | dois comandos revezando 4 rodadas, nenhum passando |
| Sem progresso | 8 escritas em produção sem **nenhum gate** rodado no meio |

Todos exigem **falha**, não só repetição — rodar o mesmo teste 3× enquanto conserta é
trabalho normal. E o terceiro carrega a distinção que os slides fazem melhor:
**progresso é comando que rodou, não arquivo que mudou.** Contador que zera a cada escrita
deixa o agente editar-falhar-editar parecendo saudável enquanto queima orçamento.

Dispara no turno em que o padrão **fecha**, não a cada turno depois — alarme repetido é
alarme ignorado. Bateria de 13 casos (3 detecções, 10 negativos) protege contra falso
positivo, mesma disciplina do ADR-0022.

### Independente — estimativa e priorização

**Estimativa probabilística no Breno.** Verificação prévia: `PERT`, `Monte Carlo`, `P85`,
"três pontos" tinham **zero ocorrências** na fábrica. Breno ganha três pontos por item,
PERT, variância e a faixa P50/P85/P95 — com a regra de comunicação (*nunca prometa o P50*)
e a de coleta (*"que coisa técnica específica pode fazer isso levar o dobro?"*, individual
antes do grupo, porque em roda o pessimista sai encolhido).

É a mesma disciplina que o `/diagnosticar` já exige para ganho projetado — faixa com base
declarada, nunca número único —, agora aplicada a prazo.

Não toca o **apetite** do `/especificar` (Shape Up), que rejeita estimativa por desenho:
apetite responde "quanto vale investir", P85 responde "qual a chance de caber". Perguntas
diferentes, donos diferentes.

**RICE e WSJF no Hugo**, que só tinha ICE. Cada régua responde uma pergunta: ICE triagem,
RICE "qual entrega mais valor", WSJF "qual não pode esperar". Divergência entre RICE e WSJF
não é erro — é a informação, e some se você a esconder numa média.

**Baseline obrigatória no `/especificar`.** Métrica de sucesso sem valor atual não é
verificável. Sem baseline conhecida, o P1 vira **medir primeiro**.

## Consequências

**Positivas**

- O anti-Goodhart do harness passa a cobrir o artefato, não só o medidor — era a metade
  que faltava.
- A recusa deixa de ser invisível, e com ela vem o dado que diz se uma regra está mal
  calibrada ou se falta instrução.
- O modo `aviso` resolve o risco de adoção que o próprio ADR-0022 levantou e para o qual
  só havia bateria de teste como mitigação.
- Detecção em voo é a primeira coisa no harness que age **durante** o problema.

**Negativas e limites, declarados**

- **Conjunto selado e digest são disciplina, não código.** Nada impede o construtor de ler
  o selado ou de omitir o digest. O que a skill dá é a mecânica e o critério; a integridade
  continua sendo do time — diferente do `guardrail.py`, que recusa.
- **Churn de SPEC conta a criação junto.** O commit que cria a SPEC com código já entra na
  contagem "junto com código". Preferi o falso positivo ao falso negativo, e a skill diz que
  é sinal, não veredicto.
- **Os detectores só veem o que o hook vê.** Trabalho feito sem Bash/Write/Edit — leitura,
  raciocínio, chamada de subagente — é invisível para eles. Um agente pode patinar em
  território que o detector não cobre.
- **`aviso` mal usado vira permanente.** Regra que fica em observação para sempre é
  decoração; por isso o `/auditar` pontua a *tendência* das recusas, não a existência delas.
- **Estimativa probabilística é tão boa quanto o pessimista.** Se o P vem inflado (cenário
  de incêndio em vez de azar normal), a faixa infla junto. A técnica de coleta mitiga; não
  elimina.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Adotar a Sage API como gate calibrado | Quebra a premissa stdlib-only/multi-CLI, e é justamente a parte que o artigo tinha interesse comercial em vender |
| Bloquear em vez de avisar na detecção em voo | Patinar não é violação — é sinal. Bloquear geraria falso positivo caro num lugar onde o modelo pode estar legitimamente iterando |
| Fazer o `diagnostico.py` julgar o churn de SPEC | Julgamento é da skill. Script que julga dá aparência de objetividade a uma escolha subjetiva |
| Detectar patinação dentro do `execucao.py ferramenta` | Quebraria a invariante 2 do ADR-0021 (nunca escrever em stdout). Modo `alerta` separado preserva a invariante e isola quem fala |
| Adotar os módulos de reunião e Jira/Slack dos slides | Exigem integração que um plugin não tem; é território da ponte Hermes (ADR-0019) |
