# ADR-0031 — Higiene de juiz, comportamento da fábrica sob eval e faixa de raio de explosão

- **Status:** aceito
- **Data:** 2026-08-02
- **Versão:** v0.23.0

## Contexto

Dois artigos de *eval engineering* publicados na mesma semana, com a mesma tese e ênfases
diferentes:

- **Hanako** (@hanakoxbt, 2026-08-01) — *"Eval Engineering: build the gate that lets your
  agents merge without you"*. Foco no **gate**: o que precisa estar verdadeiro para uma
  mudança entrar sem humano no caminho.
- **Argona** (@Argona0x, 2026-07-28) — *"Eval Engineering: the step that turns a $200 model
  into a $200,000 system"*. Foco na **higiene do instrumento**: como não construir um
  medidor enviesado e depois agir sobre ele.

A tese central é a mesma que o ADR-0025 já adotou — teste verifica o determinístico, eval
verifica o não-determinístico, e sem os dois é sempre vibe coding. O que veio de novo não
foi a tese; foram três coisas que a `/avaliar` não tratava e uma que o `/revisar` tratava
pelo eixo errado.

**O que estava faltando, concretamente.** A skill `/avaliar` mandava usar juiz-LLM com
rubrica escrita, mas não dizia nada sobre **quem** é o juiz. Rodando dentro do Claude Code,
o default preguiçoso é Claude julgando Claude — e o viés por família é medido e grande: no
mesmo conjunto de saídas, um juiz devolveu 93,3% e outro 39,5%. Uma skill que exige rubrica
mas aceita autojulgamento tem a metade barata do rigor.

**E o gate do `/revisar` decidia pelo eixo errado.** O relatório trazia dimensões e
veredicto, mas o rigor era o mesmo para um texto de UI e para uma migration destrutiva. O
artigo da Hanako coloca a pergunta certa no lugar da usual: não *"quão confiante estou?"* —
que é a variável fraca, e ainda por cima é a que o modelo controla — mas **"quanto custa
desfazer se estiver errado?"**.

## Decisão

### A — Higiene do juiz na `/avaliar`

Cinco regras, na skill e na lista de "nunca":

1. **Família diferente da que gerou.** Modelo reconhece a própria escrita e a julga com
   outra régua, nas duas direções. Sem juiz de outra família disponível, **declare no
   relatório** e trate o número como piso de confiança, não como medida.
2. **Painel quando errar é caro.** Dois ou três juízes de fornecedores diferentes; o
   agregado entre famílias é o que quebra erro correlacionado.
3. **Objetivamente checável vai para código, nunca para o juiz.** Teste passou, arquivo
   existe, estado mudou, comando rodou — isso é `if`, não julgamento.
4. **Versão do juiz pinada e registrada.** Juiz é software com versão; um que atualiza em
   silêncio torna incomparável todo score de antes e depois, e a falha é **quieta**. É o
   irmão simétrico do digest do ADR-0030: um fixa *o que* foi avaliado, o outro *quem*
   avaliou.
5. **Nunca recompense a forma.** Zero pontos para comprimento, palavra-chave, contagem de
   citação, fraseado exato, número de chamadas de ferramenta ou similaridade com
   referência. Otimizar contra um juiz por tempo suficiente ensina a **parecer certo em vez
   de estar certo** — a defesa vira superfície de ataque.

O cabeçalho do relatório passa a carregar `Juiz` / `Família do gerador` / `Painel`.

**Tamanho reconciliado com teto de tempo.** Onde antes havia só "~30 casos", agora há a
distinção honesta: **~30 para ter sinal, ~500 para confiar no agregado** — entre os dois, o
resultado orienta decisão pontual ("esse caso quebrou"), não conclusão sobre o
comportamento inteiro; e **a suíte roda em menos que um café (~5 min)**, porque suíte que
passa disso deixa de ser rodada e vira ritual trimestral. Ritual trimestral não protege
nada. Se estourar, simule o que custa dinheiro ou escreve em produção.

### B — `evals/comportamento-fabrica/`

Gold set de 13 casos nos **cinco comportamentos** que separam harness de pasta de prompts —
cada um amarrado a uma promessa já escrita da fábrica, não a gosto:

| Eval | Promessa | Onde |
|---|---|---|
| `ferramenta-vazia` | Declarar o vazio em vez de inventar | ADR-0015 |
| `chamada-repetida` | Não insistir no que já falhou | ADR-0030 |
| `recusa-de-fronteira` | Declinar sem procurar rota alternativa | ADR-0022 |
| `integridade-de-handoff` | O que o nó anterior produziu é o que o próximo lê | ADR-0023 |
| `conclusao-verificada` | Pronto é sinal real, nunca a palavra do agente | ADR-0021 |

**Oito dos treze são determinísticos** — e é justamente a telemetria e o guardrail que
tornam isso possível: `recusa-de-fronteira` lê `tipo: recusa` em `.agents/execucoes/`,
`conclusao-verificada` chama `telemetria.py corroborar`, `chamada-repetida` usa o detector
do `execucao.py`. Três passam por juiz, dois são parciais. Aplicação literal da regra 3.

**A limitação está declarada no próprio README**, porque a skill manda declarar: dentro do
Claude Code o juiz dos casos semânticos é da mesma família do gerador. Enquanto for assim,
esses resultados valem como piso de confiança. Os oito determinísticos não têm o problema —
não passam por modelo nenhum.

Limiar: **0 falhas nos determinísticos** (falha ali é bug no guardrail ou na telemetria,
não no agente), ≥ 80% nos semânticos com a ressalva registrada. Roda no CI junto do eval de
roteamento da Laura.

### C — Faixa de raio de explosão no `/revisar` e `/entregar`

O `/revisar` ganha um passo antes de acionar revisor: classificar o diff por **custo de
desfazer**.

| Faixa | O que é | O que exige |
|---|---|---|
| 1 — reversível e contido | UI, teste, função isolada coberta, doc | Gates verdes |
| 2 — reversível mas amplo | Utilitário compartilhado, schema, contrato interno | Gates verdes **e** trajetória limpa |
| 3 — difícil de reverter | Migration destrutiva, deleção, produção, dinheiro, credencial | **Humano decide, sempre** |

A faixa vai no topo do relatório e no corpo do PR. O `/entregar` a consome no passo 5.5:
faixa 3 chama `ciclo.py escalar` e não existe pontuação que abra essa porta.

Isto é o ADR-0024 visto pelo outro lado. Lá: tarefa cujo revert você não consegue escrever
não é autônoma. Aqui: mudança cuja reversão é cara não fecha por evidência. Mesmo critério,
momentos diferentes.

**Taxa de reversão no `diagnostico.py`.** A parte atuarial: `reversao()` conta commits de
reversão na janela como percentual e reporta onde se concentram. Dos sinais que um gate
pode ler, este é dos poucos que **o modelo não consegue influenciar** — e por isso vale
mais que a autoavaliação dele, que é o input que deve pesar **menos**. Área que já voltou
atrás três vezes no trimestre sobe de faixa.

### D — Fundamentação externa explicada no anti-drift

A autocrítica estruturada do `templates/anti-drift.md` (§6.1) existe desde o ADR-0012, mas
sem dizer **por que** é contra critérios explícitos e não "revise seu trabalho". Agora diz:
autocorreção intrínseca — revisar o próprio trabalho sem fundamentação externa — não ajuda
de forma confiável e frequentemente piora (Huang et al., ICLR 2024). O que faz a etapa
funcionar é a âncora fora do modelo: o "Done when", o gate que roda, o `arquivo:linha`
citado. Tirada a âncora, sobra ruído com aparência de rigor.

Uma regra que se explica é uma regra que sobrevive à primeira pressa.

### E — Auto-merge fica de fora

O título da Hanako é *"the gate that lets your agents merge without you"*, e o artigo
termina em merge automático quando o gate passa. **Não adotamos.**

O ADR-0023 já decidiu que o arco `/entregar` para no PR aberto: integração é decisão do
dono do repositório, e um plugin não deve mover essa fronteira em nome de quem o instala. A
faixa de raio de explosão é o que a fábrica pode oferecer com honestidade — dizer *quanto
rigor esta mudança pede* — e quem decide o que fazer com isso é o CI e a política de branch
do projeto, onde essa decisão pertence.

Nada aqui impede um usuário de ligar auto-merge no próprio repositório para a faixa 1. O
que decidimos é não **embarcar** isso ligado.

## Consequências

**Positivas**

- A `/avaliar` deixa de ter a metade barata do rigor: rubrica sem higiene de juiz produzia
  número com cara de medida.
- O `evals/comportamento-fabrica/` dá à fábrica o que ela cobra dos outros — ela agora tem
  gold set do próprio comportamento, e 8 de 13 casos verificados sem modelo no caminho.
- O gate do `/revisar` passa a decidir pela variável forte. Um diff de 20 linhas na faixa 3
  recebe mais escrutínio que um de 400 na faixa 1, e isso agora está escrito.
- A taxa de reversão fecha o conjunto de sinais que o agente não controla — junto com
  trajetória, recusa e gate.

**Negativas e limites, declarados**

- **Nosso próprio eval semântico está fora da regra 1.** Não temos juiz de outra família no
  fluxo. Escolhemos declarar em vez de fingir, mas declarar não conserta — os três casos de
  juiz valem menos que os oito determinísticos, e o README diz isso.
- **Treze casos não são 500, nem 30 por capacidade.** O `comportamento-fabrica` está no
  regime "orienta decisão pontual", não no de "conclusão sobre o comportamento inteiro". A
  própria régua da skill reprova apresentá-lo como agregado confiável.
- **A faixa é classificada por julgamento.** Não há código decidindo se um utilitário é
  "amplo". O que existe é a tabela, os exemplos e a taxa de reversão como evidência — quem
  quiser subestimar a faixa consegue.
- **A taxa de reversão depende de convenção de commit.** Repositório que desfaz por
  `git reset` ou por commit chamado "ajuste" fica invisível ao contador. É sinal, não
  veredicto — mesma ressalva do churn de SPEC.
- **Teto de 5 minutos briga com 500 casos.** As duas regras podem entrar em conflito numa
  suíte real, e a skill resolve mandando simular o caro em vez de aumentar o teto. Quem
  precisar dos dois vai precisar de paralelismo, que a skill não fornece.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Embarcar auto-merge para a faixa 1 | Contraria o ADR-0023: integração é decisão do dono do repositório. A faixa informa; a política decide |
| Empacotar juiz de outra família (chamada externa a outro fornecedor) | Quebra stdlib-only e multi-CLI, e criaria dependência de chave de API que o plugin não tem como gerenciar |
| Deixar a faixa fora do `/entregar` e só no relatório do `/revisar` | Faixa que não muda comportamento é decoração. O passo 5.5 é o que a torna operante |
| Fazer o `diagnostico.py` classificar a faixa automaticamente | Classificação é julgamento com contexto de negócio. Script que julga dá aparência de objetividade a escolha subjetiva — mesma regra do ADR-0030 |
| Aumentar o teto de tempo da suíte para caber 500 casos | Suíte lenta não roda. Preferimos o conflito declarado ao teto que ninguém respeita |
| Colocar os cinco comportamentos como assertions no `guardrail.py` | Três deles são semânticos; guardrail determinístico não alcança. Os que alcançam **já estão lá** — o eval verifica que o guardrail funciona, não o substitui |
