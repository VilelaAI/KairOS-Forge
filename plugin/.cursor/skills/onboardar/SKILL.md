---
name: onboardar
description: Entrevista de onboarding que prepara um projeto para usar a fábrica kairos-forge. Use na primeira vez em um projeto, depois de instalar o plugin. Faz 7 perguntas, gera CLAUDE.md preenchido, cria estrutura de pastas, contexto de testes, estado operacional e ativa o ciclo dos agentes. Leva ~15 minutos. Não use em projeto já onboardado — para reconfigurar, edite o CLAUDE.md direto ou rode auditar para ver o que falta.
---

# Onboardar — entrevista inicial do kairos-forge

Você está sendo invocado para preparar este projeto para a fábrica kairos-forge.

## O que você vai fazer

1. Conduzir uma entrevista de 7 perguntas com o usuário
2. Criar a estrutura de pastas mínima
3. Gerar o `CLAUDE.md` do projeto preenchido com as respostas
4. Criar `contextos/testes.md` e `decisoes/estado-operacional.md`
5. Listar próximos passos para o usuário

## Antes de começar

Verifique se o projeto já tem `CLAUDE.md`. Se sim, pergunte:

> "Já existe um CLAUDE.md neste projeto. Quer que eu (a) substitua, (b) faça merge das informações novas, ou (c) cancele o onboarding?"

Se não existir, prossiga.

## A entrevista — 7 perguntas

Faça **uma pergunta por vez**. Espere resposta antes de seguir. Não enfileire.

Para cada resposta, peça parágrafos, não frases. Sugira: "Use ditado por voz se preferir — quanto mais contexto, melhor."

### 1. O que este projeto é

> "Em 2 a 4 parágrafos: o que este projeto é, qual problema resolve, e quem é o usuário final. Escreva como se fosse explicar para um desenvolvedor sênior que vai entrar no time amanhã."

### 2. Stack técnica

> "Qual a stack? Linguagens, frameworks, banco de dados, hospedagem. Se houver escolhas técnicas que você fez por motivo específico (ex.: 'usamos Go porque latência crítica'), mencione o porquê."

### 3. Estrutura de pastas

> "Descreva a estrutura de pastas do projeto. Ou, se preferir, rode `ls` e me cole — eu interpreto. O que mora onde, e o que NÃO deveria morar onde."

### 4. Convenções não-óbvias

> "Que convenções existem neste projeto que não são óbvias só lendo o código? Estilo de commit, padrão de nomenclatura, regras sobre dependências, padrões de erro, anything que o time aprendeu na dor."

### 5. O que está em andamento

> "O que você está trabalhando agora? Qual feature, bug, refactor está aberto? Inclua qualquer decisão pendente que o time precisa tomar."

### 6. Restrições e o que evitar

> "Tem alguma restrição importante? Compliance (LGPD, HIPAA, PCI), performance crítica, dependências legadas que não dá para tocar, áreas do código consideradas 'aqui dragões habitam'?"

### 7. Como você quer que a fábrica trabalhe

> "Como você quer que os agentes operem? Quer que eu sempre rode o testador depois do codificador? Quer validação contra SPEC antes da revisão? Quais comandos reais de teste, lint e build eu devo usar? Tem padrão de mensagem de commit específico que devo respeitar?"

## Após a entrevista

1. **Criar estrutura de pastas** no projeto:

```bash
mkdir -p contextos decisoes docs/specs docs/specs/validacoes docs/adr .agents/memory .agents/grafo/perfis
```

2. **Gerar `CLAUDE.md`** na raiz do projeto, usando o template em `templates/CLAUDE.md.template` deste plugin como base, preenchido com as respostas da entrevista.

   Se o time também usa **Codex, Cursor ou OpenCode** (pergunte se não souber), gere junto um `AGENTS.md` na raiz com o mesmo conteúdo — esses CLIs leem `AGENTS.md` como instrução de projeto, não `CLAUDE.md`. Mantenha os dois em sincronia (uma linha no topo de cada um lembrando isso basta).

3. **Criar arquivos iniciais em `contextos/`:**
   - `contextos/sobre-o-projeto.md` — resposta 1 expandida
   - `contextos/stack.md` — resposta 2 expandida
   - `contextos/convencoes.md` — resposta 4 expandida
   - `contextos/restricoes.md` — resposta 6 expandida
   - `contextos/testes.md` — comandos e política de gates extraídos da resposta 7

Template para `contextos/testes.md`:

```markdown
# Testes e gates

## Comandos

| Gate | Comando | Quando usar |
|---|---|---|
| Lint | <a preencher> | Antes de PR |
| Unit | <a preencher> | Regra de negócio isolada |
| Integration | <a preencher> | API, banco, filas, integrações |
| E2E | <a preencher> | Fluxo crítico de usuário |
| Build | <a preencher> | Antes de release/PR |

## Política

- Toda tarefa com código de produção deve ter caminho feliz e pelo menos 1 erro coberto.
- Requisito P1 sem gate precisa de justificativa na SPEC.
- `/kairos-forge:validar` roda os gates relevantes antes de `/kairos-forge:revisar`.
```

4. **Criar `decisoes/log.md`** com cabeçalho:

```markdown
# Log de decisões

Append-only. Toda decisão técnica significativa entra aqui com data, contexto e justificativa.

## YYYY-MM-DD — Adoção da fábrica kairos-forge

Iniciado o uso do plugin kairos-forge neste projeto via /kairos-forge:onboardar.
```

5. **Criar `decisoes/estado-operacional.md`** com cabeçalho:

```markdown
# Estado operacional

Memória leve da fábrica neste projeto. Atualize quando uma execução revelar decisão, bloqueio, aprendizado ou follow-up recorrente.

## Decisões recentes

## Bloqueios ativos

## Aprendizados

## Ideias adiadas
```

6. **Criar `.agents/memory/MEMORY.md`** (índice de memórias de incidente — ver ADR-E003):

```markdown
# Memória de incidentes

Lições caras aprendidas neste projeto, uma por arquivo em `.agents/memory/<slug>.md`.
Diferente de ADR (decisão) e estado-operacional (running notes): aqui mora a
ratoeira específica que mordeu o time e pode morder de novo.

Quando criar uma memória nova: ver regras em ADR-E003 (resumo — bug levou >2h
pra entender, causa-raiz não-óbvia, solução contraintuitiva, anti-padrão volta
fácil em outro lugar). Cada arquivo tem frontmatter (name, description) + corpo
em formato "Por que (o incidente)" + "Como aplicar".

## Memórias deste projeto

(Vazio inicialmente — adicione uma linha por memória conforme criar:)

- [Título da memória](slug-kebab-case.md) — hook de uma linha do que vai aprender.
```

7. **Criar `.agents/grafo/GRAFO.md`** (índice do grafo de conhecimento — ver ADR-0009) e o `esquema.md` inicial:

```markdown
# Grafo de conhecimento

Modelo de mundo persistente da fábrica neste projeto: entidades e relações com
proveniência, extraídas de SPECs, ADRs, decisões e memórias. A memória de cada
agente morre com a janela de contexto — o grafo não.

Construa/atualize com `/kairos-forge:mapear-conhecimento` (Olívia coordena).
O grafo alimenta `/mobilizar` (memória compartilhada entre teammates),
`/validar` (checagem de afirmações contra arestas) e consultas multi-hop.

## Estado

- Última construção: (ainda não construído)
- Versão do esquema: 1
- Diagnóstico: —

## Amostras humanas

(Registre aqui cada `grafo.py amostrar` conferida: data, nó, veredicto.)
```

Para o `esquema.md`, use o modelo da seção 2 de `${CLAUDE_PLUGIN_ROOT}/skills/mapear-conhecimento/references/playbook-grafo.md` (tipos e predicados default, `versão: 1`).

8. **Verificar a camada de memória de sessão (opcional — ADR-0010):**

Cheque se as tools MCP `memory_*` (ai-memory) estão disponíveis na sessão.

- **Disponíveis:** informe que a memória de sessão está ativa e, se o projeto tem histórico, sugira rodar `ai-memory bootstrap` uma vez para semear a wiki.
- **Ausentes:** mencione como opcional, em uma frase, apontando para `docs/memoria-persistente.md` do plugin ("captura automática de sessões + handoff entre CLIs; instalação em 3 comandos"). Não insista — a fábrica funciona sem.

9. **Confirmar para o usuário:**

```
✅ Onboarding concluído.

Estrutura criada:
- CLAUDE.md (preenchido)
- AGENTS.md (se o time usa Codex/Cursor/OpenCode — espelho do CLAUDE.md)
- contextos/ (inclui testes e gates)
- decisoes/log.md
- decisoes/estado-operacional.md
- docs/specs/ e docs/specs/validacoes/
- docs/adr/ (vazio, será preenchido pelo arquiteto)
- .agents/memory/MEMORY.md (índice — capture lições de incidente conforme aparecerem)
- .agents/grafo/ (esquema + índice — o grafo em si nasce no primeiro mapear-conhecimento)

Próximos passos sugeridos:
1. Revise o CLAUDE.md gerado e ajuste o que ficou impreciso
2. Para a próxima feature, rode: /kairos-forge:especificar <descrição>
3. Depois de implementar uma SPEC, rode: /kairos-forge:validar SPEC-NNN
4. Sexta-feira, rode: /kairos-forge:auditar para ver pontuação inicial
5. Quando viver um incidente caro (bug >2h, causa-raiz não-óbvia), capture em .agents/memory/
6. Quando SPECs/ADRs/decisões acumularem, rode: /kairos-forge:mapear-conhecimento construir
```

## Regras

- **Uma pergunta por vez.** Não enfileire as 7.
- **Não invente respostas.** Se o usuário não souber algo, deixe a seção do CLAUDE.md como `<a preencher>`.
- **PT-BR em tudo gerado.** Verifique acentuação antes de salvar.
- **Não rode `git init` sem perguntar.** Alguns projetos já estão em monorepo.
- **Não modifique `.gitignore` existente.** Apenas anexe linhas necessárias se faltar `.env`.
