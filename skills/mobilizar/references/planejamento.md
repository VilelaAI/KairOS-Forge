# Planejar o time e o grafo de tarefas

Referência dos Passos 1, 2 e 4 de `/kairos-forge:mobilizar`: como agrupar tarefas por
domínio, quantos teammates chamar, o teto de onda e o orçamento que o quadro impõe, o
tier de modelo de cada um e as duas regras que separam grafo de dependências de cadeia
disfarçada. Leia ao decompor a SPEC e antes de escrever os `--depende`.

## Agrupar por domínio (Passo 1)

Identifique tarefas atômicas e agrupe por domínio:

- **dados**: migrations, RLS, índices, schema (Carlos, Fernanda)
- **backend**: APIs, services, validação (Lucas, Gabriel se IA)
- **frontend**: componentes, telas, hooks (Marina, Pablo, Ada)
- **testes**: unit, integration, e2e (Ricardo)
- **infra**: CI/CD, deploy, secrets (Marcos)
- **docs**: README, OpenAPI, changelog (Beatriz, Felipe)

## Passo 2 — Selecionar teammates

Aplique a regra de acionamento de Laura (em `${CLAUDE_PLUGIN_ROOT}/agents/laura-tech-lead.md`):

| Tamanho da tarefa | Teammates |
|---|---|
| Bug simples | 2 (1 dev + Ricardo) |
| Feature pequena | 3-4 (2-3 devs + Ricardo) |
| Feature média | 5-6 (Diego + 4-5 devs + Patrícia + Ricardo) |
| Feature grande | Time completo (Rafael + Diego + 6+ devs + Helena + Patrícia + Beatriz) |

Mais teammates ≠ melhor. Mais teammates = mais coordenação, mais tokens, mais drift.

**Teto de onda: 6 simultâneos (ADR-0033).** Time maior não é proibido — ele roda em
**ondas**: 6 entram, você faz o fan-in, e só então a próxima leva começa. Acima de ~6 a
consolidação estoura contexto antes da síntese começar, e cada teammate a mais
multiplica os pares que podem colidir em posse de arquivo.

Você não precisa contar: **o quadro não devolve o sétimo.** Era julgamento, virou
número, e agora o número é imposto — julgamento funciona enquanto tem alguém olhando,
e o ponto de mobilizar é justamente ninguém precisar olhar. O default 6 coincide com o
do Codex (`agents.max_concurrent_threads_per_session`), o que ajuda: os dois tetos não
brigam.

**Declare o orçamento de complexidade antes de abrir o quadro** (ADR-0012) e inclua no
relatório de abertura: máximo de teammates e tasks, máximo de rodadas de correção por
task (default 2), evidência mínima para encerrar, e teto de tempo/tokens se houver.

**Avisa-e-pausa (ADR-0013):** ao cruzar ~80% de qualquer limite, avise no próximo
checkpoint. Ao atingir 100%, **pause** — não lance tasks novas — e pergunte: encerrar
com as lacunas declaradas ou ampliar o orçamento? Sem susto.

**Roteamento de modelo por teammate (ADR-0013):** anuncie na largada o tier de cada um —
**rápido** (mecânico: seeds, fixtures, docs de rotina), **padrão** (implementação) e
**preciso** (arquitetura, segurança, revisão final). O tier vai no quadro (`--tier`) e
vira parâmetro real no lançamento (`model`/`reasoning_effort` no Codex). Rodar o modelo
certo em cada etapa em vez de jogar o mais caro em tudo é o que faz o orquestrador se
pagar.

## Passo 4 — grafo de dependências, não fila

**Você está desenhando um grafo de dependências, não uma fila.** Duas regras separam
grafo bom de cadeia disfarçada:

1. **Teste da aresta real.** Para cada `--depende` candidato: *a próxima tarefa lê a
   saída da anterior?* Se sim, é aresta. Se não, "e depois" não é dependência —
   **derrube a aresta e deixe as duas rodarem em paralelo.** Cada par independente em
   série é tempo jogado fora.
2. **Independência falsa.** Duas tarefas sem dependência de dados podem ter **aresta
   oculta**: escrevem no mesmo arquivo, mexem na mesma migration, disputam o mesmo
   recurso limitado (API com rate limit, ambiente de teste único).

A segunda o quadro audita por você: `--posse` sobreposta é detectada na inserção e as
duas nunca saem na mesma onda. Recurso compartilhado que **não** é arquivo (rate limit,
ambiente único) o quadro não vê — essa aresta é sua, declare com `--depende` ou
`quadro.py depender <task> --de <outra>`.

Dependência inexistente e ciclo são recusados. Tarefa sem `--posse` não entra: é assim
que dois workers acabam no mesmo arquivo.
