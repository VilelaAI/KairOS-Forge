---
name: auditar
description: Pontua o estado da fábrica no projeto em seis dimensões (0–120) e devolve as 3 lacunas de maior alavancagem. Semanal, read-only. Diff é o revisar; aceite de SPEC, o validar.
---

# Auditar — pontuação da fábrica

Você está sendo invocado para auditar quão bem a fábrica kairos-forge está montada neste projeto.

## Como funciona

Audita 6 dimensões. Cada uma vale 20 pontos. Total: 120.

| Dimensão | O que mede | Máx. |
|---|---|---|
| **Fundação** | CLAUDE.md, contextos/, decisoes/, ADRs | 20 |
| **Pipeline** | Skills, SPECs rastreáveis, validações e agentes em uso | 20 |
| **Guardrails** | Hooks, lints, testes, CI, gates e security checks | 20 |
| **Conhecimento** | Grafo de conhecimento, memória persistente, estado operacional, references/, documentação | 20 |
| **Estrutura** | Arquitetura modular, ownership, acoplamento, threat model | 20 |
| **Autonomia** | Quanto a fábrica anda sozinha — medido da telemetria, não da impressão (ADR-0021) | 20 |

Read-only: você só lê arquivos e roda comandos de leitura. Não modifica nada.

> **Nota de escala.** Até a v0.16 a auditoria tinha 5 dimensões e total 100. A partir da
> v0.17 são 6 e o total é 120. Compare auditorias antigas com novas **pelo percentual**,
> nunca pelo número absoluto — e registre a mudança de escala no histórico.

## Fluxo

1. **Identificar o projeto.** Confirmar diretório raiz com o usuário.
2. **Coletar evidências.** Para cada dimensão, rode os checks de "O que medir" abaixo.
3. **Pontuar 0–20 por dimensão** seguindo a rubrica (`references/rubrica.md`).
4. **Salvar resultado** em `decisoes/auditorias/AUDIT-YYYY-MM-DD.md` no projeto.
5. **Apresentar relatório** ao usuário com top 3 lacunas ranqueadas por alavancagem.

### O que medir

Comandos read-only, sem dependências fora do projeto. Os critérios sem comando (CLAUDE.md,
`contextos/`, `decisoes/log.md`, SPECs, lint, testes, CI, README, memórias de incidente) se
verificam lendo os caminhos citados na rubrica. Detalhe de cada coleta em `references/evidencias.md`.

**Guardrails — segurança do setup** (critério de 4 pts; audita a config de agentes/hooks, não o código do produto):

```bash
python3 <plugin>/scripts/check-agent-security.py .claude   # varre .claude/agents/, hooks, segredos e workflows da fábrica
```

Nos hooks, ele lê o bloco `hooks` de `.claude/settings.json` e `.claude/settings.local.json` e o
`.codex/hooks.json` e o `.cursor/hooks.json` da pasta do projeto (ADR-0061). Nenhum achado =
pontue cheio (4). Achado ALTA (allow-list ausente/curinga, segredo hardcoded, sai 1) ou MEDIA
(injeção em hook, token de pessoa em workflow, sai 0 — leia a saída, não só o exit) = 0 e liste
no relatório. Projeto sem agentes nem hooks customizados (em `.claude/`, `.codex/` ou
`.cursor/`) = pontue cheio; o comando roda também sem a pasta `.claude/`.

**Conhecimento — grafo** (critério 0-5):

```bash
ls .agents/grafo/entidades.jsonl .agents/grafo/relacoes.jsonl .agents/grafo/esquema.md 2>/dev/null
python3 <plugin>/scripts/grafo.py validar   # exit 0 = +2 pts; erros = 0 no subcritério, liste os 3 primeiros
```

Sem grafo, o `validar` sai 1 e o subcritério vale 0: sem a pasta, diz que ela não existe; sem
nenhuma entidade (a pasta só com `codigo.jsonl`, por exemplo), diz "Sem grafo de conhecimento", ou
lista as arestas órfãs se houver relação. Até a v0.53.0, a pasta só com `codigo.jsonl` saía 0 (ADR-0061).

Frescor: "Última construção" em `.agents/grafo/GRAFO.md` ≤ 30 dias = +1 pt. Bônus que não pontua
mas entra no relatório: `grafo.py diagnosticar` (mais de 1 componente conexo ou densidade < 0.5 são
lacunas candidatas ao top 3). Memória de sessão (não pontua — ADR-0010): tools MCP `memory_*`
disponíveis → registre "memória de sessão ativa"; senão "inativa — camada opcional, ver docs/memoria-persistente.md".

**Estrutura:**

```bash
ls CODEOWNERS .github/CODEOWNERS docs/CODEOWNERS 2>/dev/null
ls docs/arquitetura/MAPA-*.md 2>/dev/null     # checar data no nome (≤ 90 dias)
ls docs/seguranca/AMEACAS-*.md 2>/dev/null
git log --since='90 days ago' --pretty=format: --name-only | sort | uniq -c | sort -rn | head -10   # cruzar com CODEOWNERS
```

Acoplamento e duplicação: amostragem manual. Marque como hipótese se não houver mapa.

**Autonomia** — a única dimensão que não se pontua por leitura de arquivo; sai da telemetria:

```bash
python3 <plugin>/scripts/telemetria.py resumo --dias 30
python3 <plugin>/scripts/telemetria.py ruido --dias 90    # achados de revisão descartados, por revisor (ADR-0039);
                                                          # --github soma a revisão do gatilho no PR
python3 <plugin>/scripts/telemetria.py prs --dias 30      # PRs da fábrica mesclados sem commit humano (ADR-0044)
python3 <plugin>/scripts/telemetria.py comparar --dias 90 # o que a fábrica entrega volta mais que o das pessoas?
python3 <plugin>/scripts/telemetria.py espera --dias 30   # quanto do tempo de ciclo foi esperando uma pessoa (não pontua)
python3 <plugin>/scripts/painel.py --dias 30      # o mesmo estado com as SPECs ao lado
```

Sem telemetria no projeto: pontue 0 na dimensão inteira e registre *"telemetria não instalada —
autonomia não medida"*. Não estime. A autonomia de PR sai do histórico, não da trajetória, então
existe mesmo sem hook: ela não pontua, mas entra no relatório (`references/rubrica.md`).

### Como pontuar

- Critério a critério, pela tabela de cada dimensão em `references/rubrica.md`. Some por dimensão.
- Autonomia: penalidade dura de **−2 por sessão** em `sessoes_com_producao_sem_gate`, até zerar a
  dimensão; recusa **crescente** (`recusas_total`) não pontua; regra em modo aviso é regra em
  observação, não cumprida. O nível é o **menor** que ainda descreve a evidência — L4 exige
  **todos** os critérios da linha, não a média.
- `falhas_do_guardrail` acima de zero não pontua, mas entra no relatório e é candidata ao top 3:
  naquelas chamadas o guardrail falhou aberto e não guardou nada (ADR-0046).
- Critério não verificável = 0 e "não foi possível verificar" no relatório.
- **O total soma; a fábrica é do tamanho da dimensão mais baixa.** Além do NN/120, diga qual
  dimensão tem o menor percentual: é ela que limita, e pontos altos em outra não a compensam
  (a régua pelo piso do AMM da Factory.ai, como a aula 5 do Tech Leads Club a aplica). E cruze
  as dimensões; cada cruzamento verdadeiro entra no relatório e é candidato ao top 3:
  - **Autonomia acima de Guardrails:** velocidade sem freio.
  - **Gatilho por evento instalado** (`templates/ci/`) **com Fundação abaixo de 50%:** o agente
    trabalha sem testes e instruções que lhe permitam conferir o próprio trabalho.
  - **Pipeline acima de 50% com Autonomia não medida:** a fábrica produz sem saber quanto custa
    nem quanto espera.

### Como devolver as 3 lacunas

Ranquear por **alavancagem**, não por dimensão mais baixa: (1) multiplicador — destrava muitas
outras; (2) custo de adiar; (3) esforço — em empate, a de menor esforço primeiro. Em Autonomia a
ordem é obrigatória: instrumentar antes de conter, conter antes de disparar. Follow-ups típicos por
dimensão em `references/lacunas.md`.

Responsáveis sugeridos: Renata (Autonomia), Marcos (gatilhos de CI), Olívia (grafo), Helena
(segurança do setup), Helena/Rafael/Diego (Estrutura).

## Formato do relatório

Template completo em `references/relatorio.md`. Seções, nesta ordem:

1. `# Auditoria — <projeto> — YYYY-MM-DD` e **Pontuação total: NN/120 (NN%)**.
2. Tabela por dimensão (`NN/20` e `%`), com a **dimensão que limita** marcada e os cruzamentos
   verdadeiros logo abaixo.
3. **Autonomia medida (últimos 30 dias)**: ciclos registrados, ciclos sem intervenção, intervenções
   por ciclo (mediana), gates verdes de primeira, rodadas de correção, produção escrita sem gate,
   falhas do guardrail, tempo de ciclo esperando pessoa (`telemetria.py espera`); e
   **Nível estimado: L<N>** com justificativa ancorada nos números. Sem telemetria: "não medida" em
   todas as linhas — nunca preencher por estimativa. Mais a **autonomia de PR** (taxa, N e fonte
   `gh`/`git`), ou "não medida" se nenhum PR mesclado tem commit da fábrica, e a **entrega da
   fábrica × humana** (`telemetria.py comparar`: quanto de cada grupo voltou, revertido ou
   corrigido), ou "não comparável" com o N de cada grupo.
4. **Top 3 lacunas**: para cada uma, dimensão, esforço (pequeno/médio/grande), por que esta
   primeiro e como fechar em 1-3 bullets.
5. **Histórico** com as auditorias anteriores de `decisoes/auditorias/` (anteriores à v0.17 têm
   total /100 e sem coluna Autonomia — marque com `*` e compare pelo percentual).

## Regras

- **Read-only.** Não modifique código, configs, nem nada do projeto.
- **Não invente evidência.** Se não conseguiu verificar um critério, pontue 0 e mencione "não foi possível verificar" no relatório.
- **Não suavize.** A primeira auditoria de quem nunca fez isso costuma dar 30/100 ou menos. Isso é normal e útil.
- **Salve o relatório.** Mesmo se o usuário não pedir explicitamente. É como você mede progresso ao longo do tempo.

## Pronto quando

- O único arquivo escrito é `decisoes/auditorias/AUDIT-YYYY-MM-DD.md`, com as cinco seções de "Formato do relatório" na ordem e o Histórico pelo percentual (antes da v0.17 com `*`) ou "primeira auditoria"; no gatilho de CI, sem escrita, ele sai na resposta.
- Cada dimensão pontua pela tabela de `references/rubrica.md`, com o total NN/120 (NN%), a dimensão que limita marcada e os cruzamentos verdadeiros abaixo, ou "nenhum"; critério não verificado vale 0 com "não foi possível verificar".
- A segurança do setup só leva os 4 pontos sem achado ALTA nem MEDIA de `check-agent-security.py .claude`; no grafo, os três arquivos valem 2, o exit 0 de `grafo.py validar` +2 e o frescor em `GRAFO.md` +1.
- A Autonomia pontua com `telemetria.py resumo --dias 30`, lendo hooks e `.github/workflows/`, −2 por sessão com produção sem gate, falhas do guardrail no relatório e nível L<N> o menor que os números descrevem; sem telemetria, vale 0 e as linhas do `resumo` dizem "não medida".
- Autonomia de PR com taxa, N e fonte (gh ou git), espera e entrega da fábrica × humana vêm de `telemetria.py prs --dias 30`, `telemetria.py espera --dias 30` e `telemetria.py comparar --dias 90`, ou dizem "não medida" ou "não comparável" com os N.
- Em "Top 3 lacunas" do `AUDIT-YYYY-MM-DD.md`, cada uma tem dimensão, esforço, por que esta primeiro e como fechar, ranqueadas por alavancagem, e em Autonomia instrumentar vem antes de conter, e conter antes de disparar.
- Em sessão, a pessoa confirmou no passo 1 a raiz auditada (gate humano).

## Referências

| Arquivo | Quando ler |
|---|---|
| `references/rubrica.md` | Ao pontuar: tabelas critério a critério das seis dimensões, penalidades de Autonomia e tabela de níveis L2/L3/L4. |
| `references/evidencias.md` | Ao coletar: detalhe dos comandos de Estrutura, grafo e segurança do setup, e como converter a saída em pontos. |
| `references/relatorio.md` | Ao salvar: template completo do relatório em markdown. |
| `references/lacunas.md` | Ao montar o top 3: follow-ups típicos de Estrutura e Autonomia e o critério de alavancagem. |
