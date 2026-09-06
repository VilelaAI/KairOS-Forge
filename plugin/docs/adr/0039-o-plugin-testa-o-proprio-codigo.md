# ADR-0039 — O plugin testa o próprio código: suíte, hooks executados, telemetria de subagente e leitura de segredo

- **Status:** aceito
- **Data:** 2026-09-06
- **Versão:** v0.32.0

## Contexto

A análise do [pwdev-claude-marketplace](../revisoes/2026-09-06-analise-pwdev-claude-marketplace.md)
chegou a uma conclusão desconfortável. O forge está à frente em tudo que é **decidido por
código no caminho do agente** — `ciclo.py`, `quadro.py`, `guardrail.py` em hook,
`contrato.py`, mirrors gerados, tetos verificados no CI. E está atrás na única coisa que
separa esses mecanismos de promessas: **provar que o próprio código faz o que promete**.

Os números, medidos:

| O que | Estado até a v0.31 |
|---|---|
| Linhas de Python em `scripts/` decidindo transição, orçamento, bloqueio, contrato, compensação | 6.157 |
| Testes unitários dessas linhas | 0 |
| O que o CI verificava | consistência de contagens e versão, paridade dos mirrors, **forma** dos contratos (digest), boa-formação dos gold sets |
| Casos "determinísticos" do eval de comportamento (ADR-0031) | 8 declarados, nenhum runner |

A assinatura do contrato (ADR-0034) pega mudança de **forma**. Nada pegava mudança de
**comportamento**: uma aresta a menos na tabela de transições, um orçamento que deixa de
escalar, um guardrail que passa a liberar — tudo isso chegaria a `main` verde.

Três achados menores vieram da mesma comparação, e os três são do tipo que só um teste
pega:

1. **Ramo morto na telemetria.** O `execucao.py` tinha um construtor para `delegacao`
   (lançamento de subagente) desde o ADR-0021 — e nenhum matcher de hook incluía `Agent`,
   `Task` ou `Skill`. Nunca disparou. A trajetória de uma mobilização com seis teammates
   não registrava nenhum deles.
2. **Leitura de segredo não era coberta.** O guardrail bloqueava *escrever* em `.env`
   desde o ADR-0022 e pegava exfiltração por rede. *Ler* `.env` com `Read` ou `Grep`
   passava — e é lendo que o segredo vai para o transcript, para a memória episódica e
   para o próximo prompt.
3. **Falso positivo no próprio guardrail.** `git push --force-with-lease origin main` era
   bloqueado com a mensagem "use `--force-with-lease`". O lookahead negativo do regex
   olhava depois do trecho já consumido. Descoberto pelo primeiro teste da classe
   `comando`.

O vizinho tem 297 testes e ensina duas coisas por contraste. A positiva: **hook
executado, não grepado** — "a asserção de string passa mesmo quando o dispatcher define
uma função que nunca chama, que foi exatamente como um caminho de frota no-op foi
publicado". A negativa: a suíte dele não roda em CI, o `discover` acha zero testes por
falta de `__init__.py`, e o comando documentado nos planos não funciona. Suíte excelente
que ninguém executa é a mesma coisa que não ter.

## Decisão

### 1. Suíte `unittest`, só stdlib, no CI ao lado do `release.py check`

`tests/` com `__init__.py` (o `discover` precisa dele), rodada por
`python3 -m unittest discover -s tests -t .` em todo PR. Sem pytest: dependência que falta
vira teste que se pula em silêncio.

Cinco padrões, cada um com o modo de falha que caça:

| Padrão | Arquivo | O que pega |
|---|---|---|
| **Script como CLI em repositório temporário** — argv, exit code, JSON no stdout, efeito no disco; após o caso negativo, o estado é byte a byte o mesmo | `test_ciclo.py`, `test_quadro.py`, `test_guardrail.py` | aresta que some, orçamento que não escala, recusa que passou a aceitar, recusa que escreveu antes de recusar |
| **Hook executado com payload sintético** — cada comando de `hooks/hooks.json` roda com o mesmo stdin que o Claude Code mandaria | `test_hooks.py` | script citado que não existe, matcher que não cobre a ferramenta, hook de telemetria que fala no stdout (e poluiria o contexto), lembrete que repete |
| **Injeção de falha na publicação** — `os.replace` falha; o estado anterior permanece válido e nenhum `.tmp` sobra | `test_ciclo.py`, `test_quadro.py` | estado meio escrito; e revelou que o `quadro.salvar` **não era atômico** — corrigido junto |
| **Saneamento da trajetória como invariante** — prompt, segredo, `agent prompt` e caminho absoluto no payload; nada disso chega ao `.jsonl` | `test_execucao.py` | vazamento por construtor novo; o filtro passa a ser por **nome de campo** no `anexar`, não por lembrar de não gravar |
| **Somente-leitura por hash da árvore** — `painel.py`, `telemetria.py`, `grafo.py validar`, `diagnostico.py coletar`, `estado`, `ledger`, `esquema`, `verificar` | `test_somente_leitura.py` | "renderização, nunca estado" deixa de ser frase do CLAUDE.md |

Mais `test_estrutura.py` com as invariantes que o `release.py check` não cobre: todo
`${CLAUDE_PLUGIN_ROOT}/…` citado existe e não contém `..`; toda `references/` citada
existe e toda existente é citada; allow-lists só com ferramentas conhecidas; consultivos
sem `Write`/`Edit`; apoio sem `Bash`; estados citados na skill `entregar` existem no
`ciclo.py`; sagrados do guardrail escritos no anti-drift.

**Os 8 casos determinísticos do gold set de comportamento viram testes**, cada um citando
o id no docstring — e um teste garante que todo caso `deterministica` do JSONL é citado
por algum teste. O gold set e a suíte não podem divergir em silêncio.

### 2. Telemetria de subagente, por instância

`SubagentStart`/`SubagentStop` entram nos hooks (`execucao.py subagente_inicio|fim`), e o
matcher do `ferramenta` ganha `Agent|Task|Skill` — o ramo morto passa a disparar. A
duração é chaveada por `agent_id`, nunca por tipo: o vizinho chaveia por tipo e dois
subagentes iguais em paralelo trocam de duração; aqui seis teammates da mesma persona
numa onda (ADR-0033) é o caso normal. O `telemetria.py resumo` passa a somar subagentes
lançados e tempo.

Saneamento: `CHAVES_PROIBIDAS` (`prompt`, `description`, `model`, `token`, `secret`…)
filtradas por nome no `anexar`, e caminho fora do projeto reduzido a `…/pasta/arquivo`.

### 3. Classe `leitura` no guardrail

`PreToolUse` com matcher `Read|Grep|Glob` → `guardrail.py leitura`. `Read` e `Grep` com
`path` em arquivo de segredo bloqueiam; `Glob` só lista nomes e passa; `Grep` com `path`
em diretório passa — limite declarado, inspecionar exigiria replicar o Grep. Padrões:
`.env`, `.env.*`, `.envrc` (direnv, novo), `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`
(novo); exceções `.example`/`.sample`/`.template`. Degradável para `aviso` e liberável
por caminho, como `protegido`.

Os falsos positivos que fariam o usuário desligar a regra (`src/api.key.ts`, `.env.example`)
e os falsos negativos do vizinho (`.envrc`, `id_ed25519`) são casos de teste.

**Payload ilegível bloqueia nos modos de PreToolUse.** Até aqui qualquer erro saía
silencioso com 0. Um guardrail que libera o que não conseguiu ler é decoração. Bug do
próprio script continua falhando aberto; o que muda é o caso em que o *input* não é o
que o contrato do hook promete.

### 4. `disable-model-invocation: true` no `lancar`

Deploy é a skill que constrói o vetor irreversível. O modelo não a aciona por conta
própria; só o humano invoca. `entregar` fica fora desta decisão: seu gate humano é
interno ao arco (aprovação da SPEC, PR sem merge), e a skill inteira acionada pelo modelo
é o caso de uso do Hermes (ADR-0019).

## Consequências

**Positivas**

- Regressão de comportamento em `ciclo.py`, `quadro.py`, `guardrail.py`, `contrato.py`
  e `execucao.py` cai no PR, não em produção. A primeira rodada da suíte já pagou o
  custo: dois defeitos reais (`--force-with-lease` bloqueado; `salvar` não atômico).
- Hook que deixa de disparar por matcher errado é impossível de novo: o teste executa o
  hook.
- A trajetória passa a ver quem foi lançado e por quanto tempo — o `varrer` (ADR-0036)
  ganha dado real para o prazo.

**Negativas e limites, declarados**

- **Nenhum teste tem modelo no caminho.** Se o modelo obedece à skill continua sendo o
  eval (ADR-0025/0031). A suíte prova o harness, não a fábrica.
- **Teste de processo depende do host.** O caso "worker que ignora TERM morre no KILL"
  usa `subprocess` real. Em sandbox cujo init não colhe órfãos, o zumbi aparece
  "vivo" para `kill(pid, 0)` — por isso `processo_vivo` lê `/proc/<pid>/stat` (ou `ps`)
  e trata `Z` como morto (ADR-0040). Portabilidade fora de Linux/macOS não foi testada.
- **~20 segundos por rodada.** É o preço de subprocessos e repositórios git reais; a
  alternativa (importar e mockar) testaria outra coisa.
- **`Grep` em diretório** continua um buraco declarado da classe `leitura`.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| pytest | Dependência; e teste que se pula por falta dela some do radar. O vizinho mostrou o custo: `discover` com zero testes verde |
| Testar importando os módulos e chamando funções | Testa a função, não o contrato — e o contrato é argv + exit code + disco, que é o que hook, CI e symphony consomem |
| Só grepar `hooks.json` | Exatamente o que deixou o ramo `delegacao` morto por 15 versões |
| Bloquear `Grep` em diretório também | Replicar o Grep no guardrail para decidir; falso positivo em toda busca no repo. Não vale o buraco que fecha |
| `disable-model-invocation` também no `entregar` | Tira o Hermes do arco. O gate humano do `entregar` é interno e já existe |
