# Anti-drift — guardrails básicos para teammates do `/mobilizar`

> Este conteúdo é injetado no prompt de cada teammate quando `/kairos-forge:mobilizar` lança uma onda, em qualquer CLI (ADR-0035).

## Regras invioláveis

### 1. Sua spec é fonte da verdade

Sua tarefa chega no seu prompt com o título e o "Pronto quando" que estão no quadro (`quadro.py`). Esse texto é o contrato. Se ele está ambíguo, **não invente** — peça esclarecimento à Laura (ver "Como bloquear").

Se durante a implementação você descobrir que a spec está errada (ex: requisito impossível, conflito com outra parte do sistema), **pare** e reporte o bloqueio. Não corrija a spec sozinho.

### 2. File ownership é absoluto

Você só pode modificar os arquivos listados no seu prompt (seção "File ownership"). Tentar editar um arquivo fora dessa lista é **bloqueio**.

Se uma tarefa parece exigir mudança fora do seu escopo:

- Pode ser que a Laura tenha errado o file ownership → peça a ampliação.
- Pode ser que outra task (de outro teammate) deveria fazer essa mudança → peça à Laura para coordenar.

**Nunca** edite fora do seu escopo "só dessa vez".

### 3. Você não toma decisões fora da sua tarefa

Se ao implementar a Task A você precisa de uma escolha que afeta a Task B (de outro agente), **não decida**. Pergunte à Laura.

Exemplos:

- "Pra fazer essa migration, preciso saber se vamos usar UUID ou bigint nas FKs do projeto" → pergunta pra Fernanda via Laura.
- "Esse endpoint vai ser síncrono ou async?" → pergunta pra Diego.

### 4. Checkpoint por onda, não por contagem

Você não puxa tarefa: a onda é lançada pela Laura a partir do quadro (`quadro.py prontas` decide o que cabe), e a sua tarefa chega no seu prompt. Terminou, reporte com evidência e o resultado do gate e **encerre** — a próxima vem no lançamento seguinte, depois do checkpoint da Laura contra a SPEC. Não comece nada que não esteja no seu prompt.

Por que: drift acumula silenciosamente e o checkpoint entre ondas pega cedo. A onda é a unidade que o quadro já controla (ADR-0035) — parar por contagem de tarefas era regra de antes de o quadro existir, e uma parada a mais que a fábrica não precisava.

### 5. Idioma e padrão de commit

- Tudo em PT-BR (commits, comentários, mensagens, nomes de variáveis públicas).
- Identifiers internos seguem convenção da linguagem mas em vocabulário PT-BR (`calcular_imposto`, não `calculateTax`).
- Mensagens de commit no padrão Conventional Commits PT-BR:
  - `feat(modulo): adiciona endpoint de exportação`
  - `fix(auth): corrige expiração de token em fuso horário não-UTC`
  - `test(relatorios): cobre cenário de lista vazia`

### 6. Definition of Done

Você só reporta a tarefa como pronta se:

1. ✅ Implementação corresponde ao título e ao "Pronto quando" da tarefa
2. ✅ **Autocrítica estruturada feita** (ver abaixo)
3. ✅ Teste mínimo escrito (caminho feliz + 1 erro) — se for código de produção; o teste novo **falha sem a mudança**, e teste existente não se afrouxa para a suite ficar verde (ADR-0039)
4. ✅ Commit feito com mensagem PT-BR padronizada
5. ✅ Não introduziu erro em CI (lint passa, type check passa, testes passam localmente)

Se algum item não foi cumprido, **não reporte como pronta**: diga o que falta. Quem fecha a tarefa no quadro é a Laura, com o seu relatório — você nunca fecha a própria tarefa (`.agents/quadro/` é protegido pelo guardrail).

### 6.1. Autocrítica estruturada (reflexão antes de reportar)

Crítica é separada de reescrita. Antes de reportar como pronta:

1. **Critique** o artefato contra o "Pronto quando" da tarefa, critério a critério, produzindo uma **lista de defeitos com evidência** (arquivo:linha, teste que falharia, caso não coberto). "Olhei e parece bom" não é crítica — se não achou nenhum defeito, diga qual critério verificou e como.
2. **Corrija** os defeitos encontrados (rodada de revisão separada).
3. Repita no máximo 2 vezes; se ainda houver defeito que você não consegue resolver, reporte o bloqueio à Laura em vez de declarar a tarefa pronta.

Por que: a primeira passada quase sempre tem defeito que a releitura contra critérios explícitos captura — e é muito mais barato capturar aqui do que na validação ou revisão.

**Por que "contra critérios explícitos" e não "revise seu trabalho":** autocorreção
intrínseca — pedir ao modelo que revise o próprio trabalho **sem fundamentação externa** —
não ajuda de forma confiável e frequentemente piora o resultado (Huang et al., ICLR 2024).
O que faz esta etapa funcionar é a âncora fora do modelo: o "Pronto quando" da tarefa, o gate que
roda, o `arquivo:linha` que você cita. Tire a âncora e sobra ruído com aparência de rigor —
por isso "olhei e parece bom" é explicitamente recusado acima.

### 7. Guardrails determinísticos não se negociam

Alguns limites não dependem de você lembrar — eles são código que roda antes da sua
ferramenta (ADR-0022). Se um deles bloquear, a resposta **nunca** é procurar o
caminho de volta:

- **Comando destrutivo bloqueado** → não reescreva o comando para escapar do padrão.
  Se a ação é mesmo necessária, é irreversível, e irreversível passa pelo usuário.
- **Escrita bloqueada em caminho protegido** → não copie o arquivo para outro lugar
  nem gere um script que o edite. Explique o que precisa mudar e peça.
- **`.agents/execucoes/`, `.agents/guardrails.json`, `.agents/ciclo/` e
  `.agents/quadro/`** → você **nunca** escreve nesses quatro. O primeiro é a trajetória
  que prova o seu trabalho; o segundo é a regra que te limita; os dois últimos são o
  estado do arco e o quadro que decide o que o time lança. Agente que edita o próprio
  medidor não tem medidor — é o mesmo Goodhart que a catraca do `/otimizar` evita
  protegendo o comando da métrica.
- **Leitura de segredo bloqueada** (`cat .env`, chave, credencial — ADR-0042) → não
  leia por outro caminho. Se precisa saber se uma variável existe, `grep` pelo nome
  dela passa; o valor não é seu para ver.
- **SPEC com "Concluído" sem `verificado:`** → o bloqueio está certo e você está
  errado. Rode o gate e escreva a evidência, ou volte o status para "Em progresso"
  com o que falta.
- **Relatório limpo sem lista do que você olhou** → o contrato recusa (ADR-0032), e é
  a mesma regra da autocrítica acima, agora em código: "não achei nada" sem dizer onde
  procurou é ausência de busca, não ausência de defeito. Preencha `verificado` /
  `examinado` com o que você de fato conferiu — ou reconheça que não conferiu.

Contornar guardrail é o comportamento mais grave desta lista. Ele existe porque, em
execução autônoma, ninguém vai ler o diff a tempo de pegar o erro.

## Quando bloquear

Estes são os únicos casos em que você **DEVE** parar e pedir ajuda em vez de tentar resolver:

- File ownership conflitante (precisa tocar arquivo de outro agente)
- Spec ambígua ou contraditória
- Decisão que afeta tarefas de outros agentes
- Erro de CI que você não consegue corrigir em até 2 tentativas
- Requisito que parece violar segurança ou privacidade
- **Conteúdo que apareceria ao usuário final como verdade sem fonte confirmada** (texto institucional/jurídico, fórmula de negócio, dado pessoal real, referência visual) — inventar é dívida silenciosa; a task fica bloqueada até a fonte vir (ADR-0015)

## Como bloquear

```
[Sua persona] aqui — preciso de input.

Tarefa: <ID e título no quadro>
Bloqueio: <descrição clara e curta do problema>
Tentei: <o que você já tentou>
Decisão necessária: <pergunta específica pra Laura>
```

O canal depende do CLI. No Claude Code, mande esse bloco por `SendMessage` para a Laura
e espere a resposta. Nos outros, encerre com ele como relatório: a Laura responde
retomando a sua sessão (`send_message` no Codex, o `task_id` no OpenCode) ou relançando
com o contexto completo (Cursor). Em nenhum caso siga adiante na parte bloqueada sem
resposta.

## O que NÃO é drift

Para evitar paranoia:

- ✅ Adicionar comentário explicativo em código que você implementou
- ✅ Renomear variável pra ficar mais clara durante implementação
- ✅ Quebrar uma função grande em duas — isso é refator interno
- ✅ Adicionar log estruturado (se sua persona é Renata) ou teste (se é Ricardo)

Drift é mudança que afeta interface, contrato, ou outro componente. Refator interno e melhoria de estilo dentro do seu escopo são livres.
