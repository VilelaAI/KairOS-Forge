# ADR-0021 — Observabilidade do harness: registro de execução, telemetria e dimensão Autonomia

- **Status:** aceito
- **Data:** 2026-08-01
- **Versão:** v0.17.0

## Contexto

O whitepaper *The New SDLC With Vibe Coding* (Google, Day-1, maio/2026) lista seis
componentes de harness — instruções, tools, sandboxes, orquestração, guardrails/hooks e
**observabilidade** — e é categórico sobre o último: *"Without observability, there is no
way to tell whether the agent is doing well or quietly drifting."*

A análise em `docs/revisoes/2026-08-01-analise-whitepaper-novo-sdlc-e-caminho-l4.md` mediu
a fábrica contra os seis e encontrou observabilidade em ⭐ de 5. O que existia:

- o **ledger** do `/mobilizar` — tabela digitada pela Laura no encerramento, auto-reportada,
  não persistida, e honesta sobre o limite ("o plugin não mede tokens de dentro da sessão");
- o `/auditar`, que pontua o **setup** da fábrica em 5 dimensões e nunca olha as **execuções**.

A consequência é estrutural, não cosmética. O alvo declarado é o nível **L4 — Fábrica**, cuja
definição é *"o time confia mais no harness do que em revisão individual de código"*. Confiança
sem histórico é otimismo. Sem instrumento, a fábrica não consegue responder à única pergunta
que define o nível:

> que fração dos ciclos terminou sem intervenção humana?

E enquanto essa pergunta não tiver número, qualquer afirmação sobre L3/L4 é opinião — inclusive
uma afirmação otimista, que é exatamente como se produz um pipeline sem supervisão achando que
se produziu autonomia.

Havia ainda um segundo problema, apontado pelo mesmo paper na tese de *trajectory evaluation*:
*"a fluent output that skipped its verification steps is a more dangerous failure than one with
a visible error."* Toda a evidência da fábrica é auto-relatada — a célula `verificado:` da SPEC
é escrita pelo mesmo agente que fez o trabalho. O princípio que a Alice enuncia no próprio card
("o gerador nunca avalia a si mesmo") estava sendo violado no nível do harness.

## Decisão

Instrumentar o harness com registro **escrito por código, nunca pelo modelo**.

### 1. `scripts/execucao.py` — registro determinístico

Chamado pelos hooks em quatro pontos do ciclo de vida (`SessionStart`, `UserPromptSubmit`,
`PostToolUse` em `Write|Edit|Bash`, `Stop`). Recebe o payload do hook em stdin e anexa **um
evento** a `.agents/execucoes/YYYY-MM.jsonl`.

Três invariantes, nesta ordem:

1. **Nunca bloqueia e nunca falha a sessão.** Qualquer erro sai silencioso com código 0.
   Observabilidade que derruba a sessão é pior que nenhuma. Quem bloqueia é o `guardrail.py`
   (ADR-0022).
2. **Nunca escreve em stdout.** Em `SessionStart` e `UserPromptSubmit` o stdout do hook entra
   no contexto do modelo — poluir ali custa tokens em toda interação.
3. **Nunca registra segredo.** Comandos passam por redação (padrões rotulados, flags de senha,
   tokens longos) antes de gravar; prompts entram como contagem de caracteres e skill detectada,
   jamais como texto.

O evento-chave é o `prompt`: **cada prompt humano depois do primeiro é uma intervenção.** O
primeiro é o gatilho. Um ciclo com zero intervenções rodou sozinho. Essa é a definição
operacional de autonomia, e ela é medível deterministicamente — não depende de o modelo relatar
nada sobre si mesmo.

### 2. `scripts/telemetria.py` — agregação e corroboração

Três subcomandos:

- `resumo` — os números para o `/auditar`: taxa de autonomia, mediana de intervenções por ciclo,
  gates verdes de primeira, rodadas de correção, sessões com produção escrita sem gate nenhum.
- `sessoes` — uma linha por ciclo.
- `corroborar "<comando>"` — usado pelo `/validar`: aquele gate citado no `verificado:` realmente
  rodou? Com que resultado? Sai com código 1 quando a alegação não se sustenta, o que o torna
  usável em CI e pre-commit.

Resultado indeterminado é uma categoria de primeira classe. Quando a saída do comando não permite
afirmar sucesso nem falha, o registro grava `null` e a telemetria conta em separado — nunca vira
"verde" por otimismo. Métrica que arredonda a favor não mede nada.

### 3. `/validar` ganha a etapa de corroboração

Para cada requisito Concluído, o comando citado em `verificado:` é conferido contra a trajetória.
`nao_corroborado` em requisito P1 **bloqueia**, exatamente como "sem evidência" — a alegação pode
ser verdadeira, mas então a prova está fora do alcance da validação e o autor precisa dizer onde.
Trajetória parcial (telemetria instalada no meio do trabalho) não penaliza retroativamente.

Isso não substitui rodar os gates: a corroboração olha para trás, rodar o gate olha para agora.

### 4. `/auditar` ganha a 6ª dimensão — Autonomia

Total passa de 100 para 120 pontos. A dimensão nova é a única que **não se pontua por leitura de
arquivo** — sai da telemetria. Pontua telemetria ativa, taxa de autonomia em escala, gates verdes
de primeira, uso do arco fechado, guardrails determinísticos ativos e gatilho por evento. Penaliza
duro sessões com código de produção escrito sem nenhum gate.

Sem telemetria no projeto: **zero na dimensão e "não medida" no relatório.** Não estime.

A skill também ganha a tabela que traduz telemetria em nível (L2/L3/L4), com a regra de que L4
exige **todos** os critérios da linha, não a média — uma fábrica com 90% de autonomia e nenhum
guardrail determinístico não é L4, é pipeline sem supervisão, e o relatório deve dizer isso com
essas palavras.

## Onde o registro vive, e por quê

`.agents/execucoes/` é **camada episódica** (ADR-0009/0010) e entra no `.gitignore` por default.
O bruto é local, volumoso e descartável; o que sobe de camada é a conclusão — os números agregados
ficam em `decisoes/auditorias/AUDIT-*.md`, versionados. É o mesmo princípio de memória que a
fábrica já aplica: sessão → arquivo → grafo, o durável sobe.

O efeito colateral prático é bem-vindo: nenhum PR fica poluído por log de telemetria.

## Consequências

**Positivas**

- A autonomia da fábrica vira número, o que torna L4 uma meta verificável em vez de uma
  aspiração. É a pré-condição de todas as ondas seguintes.
- A evidência da SPEC deixa de ser auto-relato puro — o `verificado:` passa a ser alegação
  conferível, fechando o modo de falha de *trajectory* que o paper nomeia como o mais perigoso.
- O ledger do `/mobilizar` ganha base factual em vez de memória da Laura.
- `gates verdes de primeira` é um sinal de **qualidade de contexto**: quando cai, o problema
  costuma ser SPEC vaga ou `contextos/testes.md` velho, não o modelo. Isso dá ao `/evoluir` um
  alvo mensurável em vez de impressão.

**Negativas e limites, declarados**

- **Só Claude Code tem a instrumentação completa.** O Codex CLI suporta apenas `SessionStart`;
  OpenCode e Cursor não têm hooks equivalentes. Nesses CLIs a telemetria fica parcial ou vazia,
  e a dimensão Autonomia pontua 0 — o que é honesto, não um bug: sem hook não há trajetória.
  O caminho para esses CLIs é rodar os checks equivalentes no CI (ADR-0026).
- **`ok` é heurístico.** Sem exit code confiável no payload de `PostToolUse`, o sucesso do
  comando é inferido de marcadores na saída. Por isso existe o estado indeterminado — a
  alternativa (chutar) seria pior que a incerteza declarada.
- **Um hook por tool call** adiciona latência mínima e um arquivo que cresce. Partição mensal
  e ausência de rotação automática são escolha consciente: apagar `.agents/execucoes/` é seguro
  a qualquer momento, e o agregado já subiu de camada.
- **A telemetria mede a sessão, não o custo.** Tokens continuam fora do alcance do plugin
  (`/cost` segue sendo a fonte). O que se mede é o que dá para medir de fora do modelo — e isso
  é dito no lugar de fingir cobertura completa.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| O modelo registra a própria execução (Laura escreve o ledger em arquivo) | É auto-relato — exatamente o problema que o ADR existe para resolver. O agente que pulou a verificação é o mesmo que escreveria "verifiquei" |
| Parsear o transcript da sessão em vez de usar hooks | Formato instável entre versões, e não funciona em tempo real. Hook é a interface pública para isso |
| Commitar `.agents/execucoes/` | Polui todo PR com log de sessão e cria conflito em qualquer trabalho paralelo. O agregado versionado entrega o mesmo valor sem o custo |
| Manter o total do `/auditar` em 100 redistribuindo pontos | Mexeria na pontuação de cinco dimensões estáveis só para caber uma sexta. Mudar a escala e comparar por percentual é mais honesto que reescrever a régua |
