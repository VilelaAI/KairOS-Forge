# ADR-0010 — Memória persistente em camadas: integração opcional com ai-memory

**Status:** Aceito
**Data:** 2026-07-24

## Contexto

Duas fontes motivaram esta decisão:

1. O artigo *Graph Engineering: How to Run 1,000 AI Agents in Parallel From One Prompt* (wast3, jul/2026), que reforça o desenho de trabalho como **grafo de dependências reais** em vez de cadeia sequencial — e nomeia os três modos de falha previsíveis: colapso de contexto no fan-in, independência falsa (recurso compartilhado sem dependência de dados) e falha silenciosa de nó. Essas lições entram direto no `/mobilizar` (ver Decisão, item 3).
2. O projeto [`akitaonrails/ai-memory`](https://github.com/akitaonrails/ai-memory) (MIT): memória de longo prazo para agentes de código. Um binário Rust roda um servidor MCP/HTTP com hooks de ciclo de vida que capturam observações sanitizadas de cada sessão, compilam uma **wiki markdown git-versionada** (padrão "Karpathy LLM wiki": compilar, não recuperar log cru), fazem busca FTS5 e entregam **handoffs entre CLIs** — sair do Claude Code no meio da tarefa e continuar no Codex no mesmo diretório, sem re-explicar nada.

A fábrica hoje tem memória em **arquivos curados** (`decisoes/`, `.agents/memory/`, `contextos/`) e memória **estrutural** (`.agents/grafo/`, ADR-0009). Falta a camada mais barata e mais volumosa: a **memória episódica de sessão** — o que foi tentado, o que falhou, onde a sessão parou. Hoje ela morre quando a sessão fecha, e a continuidade entre CLIs (que o forge suporta por design multi-CLI, ADR-0004) depende do humano recontar o contexto.

### O ai-memory cabe dentro do forge?

Não como código. É um **runtime** (servidor + SQLite + Docker/systemd + instalador de hooks) — exatamente o que o ADR-0001 decidiu que o forge não é, e a lista "não portar" (worker headless 24/7) reforça. Vendorizar contrariaria a arquitetura do plugin.

Mas como **companion externo opcional**, o encaixe é quase perfeito:

- Suporta nativamente os 3 CLIs do forge (Claude Code, Codex, OpenCode), com MCP + hooks.
- MIT, self-hosted, loopback por default (sem dado de sessão saindo da máquina do usuário).
- Filosofia compatível: markdown git-versionado como fonte da verdade, "o agente esquece, o repo não" — a mesma do forge.
- Zero cerimônia: os hooks capturam sozinhos; as skills só precisam **consultar** (`memory_query`, `memory_briefing`, `memory_handoff_accept`) quando as tools existirem na sessão.

## Decisão

### 1. Modelo de memória em três camadas (documentado, com dono)

| Camada | O que guarda | Onde | Mantida por | Custo |
|---|---|---|---|---|
| **Episódica (sessão)** | O que aconteceu em cada sessão: prompts, tentativas, handoffs "onde parei" | Servidor ai-memory (wiki + SQLite, fora do repo) | Hooks automáticos — **opcional** | Zero cerimônia |
| **Curada (arquivos)** | Decisões, incidentes, convenções, estado operacional | `decisoes/`, `.agents/memory/`, `contextos/` (no repo) | Humano + agentes | Manual, deliberada |
| **Estrutural (grafo)** | Entidades e relações com proveniência, multi-hop | `.agents/grafo/` (no repo) | Olívia via `/mapear-conhecimento` | Pipeline ADR-0009 |

Regra de fluxo entre camadas: a episódica é matéria-prima; o que for durável **sobe** — decisão vira `decisoes/log.md` (e ADR se for arquitetural), lição cara vira `.agents/memory/`, fato estrutural vira aresta no grafo. **O repo continua a fonte da verdade do projeto.**

### 2. Integração por detecção, com degradação graciosa

Nenhuma skill passa a **exigir** ai-memory. O contrato é: *se* as tools MCP `memory_*` estiverem disponíveis na sessão, as skills as usam nos pontos certos; se não estiverem, tudo funciona como antes.

| Skill | Uso quando `memory_*` existir |
|---|---|
| `/onboardar` | Detecta o ai-memory; se ausente, apresenta como opcional (1 comando por CLI); se presente, sugere `ai-memory bootstrap` para semear a wiki com o histórico do projeto |
| `/rodar`, `/mobilizar` | Na largada, Laura aceita handoff pendente (`memory_handoff_accept`) e pede briefing (`memory_briefing`) — "onde paramos" sem recontar contexto |
| `/especificar` | Arquiteto consulta `memory_query` junto do subgrafo: tentativas passadas e abordagens descartadas sobre as entidades da feature |
| `/evoluir` | As 5 perguntas da entrevista ganham evidência: `memory_recent`/`memory_query` sobre a semana, em vez de depender só da lembrança do usuário |
| `/auditar` | Registra no relatório (sem pontuar) se a memória de sessão está ativa (`memory_status`) |
| `/mapear-conhecimento` | Páginas da wiki (via `memory_query`/`memory_read_page`) entram como corpus opcional de extração, com fonte `ai-memory:<path>` |

Anti-duplicação: as skills **não** fazem double-write (gravar a mesma decisão em `decisoes/log.md` **e** `memory_write_page`). Captura de sessão é dos hooks; escrita durável é nos arquivos do repo. `memory_write_page` fica reservado para preferências pessoais/globais do usuário (`scope: global`), que não pertencem a repo nenhum.

### 3. Lições do artigo aplicadas ao `/mobilizar`

- **Teste da aresta real:** todo `depends_on` de task responde "a próxima tarefa **lê a saída** da anterior?". Se não lê, a dependência cai — "e depois" não é aresta.
- **Independência falsa:** duas tarefas sem dependência de dados que escrevem no mesmo arquivo ou disputam o mesmo recurso limitado têm aresta oculta — serializar (o file ownership já cobre arquivos; a regra generaliza para recursos).
- **Fan-in em camadas:** com mais de ~6 teammates, Laura consolida por lotes (resumo por lote, depois síntese dos resumos), nunca todos os outputs crus de uma vez.
- **Falha silenciosa de nó:** no encerramento, Laura confere contagem de tasks concluídas × planejadas e **declara lacunas explicitamente** — relatório "completo" com nó faltando é o modo de falha mais caro do paralelismo.

### 4. Guia dedicado

`docs/memoria-persistente.md` documenta as camadas, a instalação opcional por CLI, a detecção, o uso por skill e as regras de segurança (loopback por default, bearer token fora de loopback, `[capture] ignore_paths` para caminhos sensíveis).

## Posicionamento (limite deliberado)

O forge **não embarca, não instala e não configura** o ai-memory — apenas o detecta e o usa quando presente, e documenta a instalação oficial. O servidor é infraestrutura do usuário (mesma lógica da migração de armazenamento do grafo no ADR-0009). Não há dependência de rede em nenhuma skill: sem as tools `memory_*`, o comportamento é o de antes. Isso mantém o forge plugin puro (ADR-0001) e evita acoplar o ciclo da fábrica a um serviço externo.

## Versão

Sem skill nova e sem agente novo — mudanças de prompt em skills existentes + docs: bump **patch** 0.8.0 → **0.8.1** (mesmo precedente do ADR de segurança do setup, v0.6.1).

## Consequências

Boas:

- Continuidade entre sessões e entre CLIs ("sair do Claude Code, continuar no Codex") vira capacidade da fábrica, sem o forge virar runtime.
- `/evoluir` deixa de depender da memória do usuário para achar as dores da semana.
- O modelo de camadas dá dono e critério pra cada tipo de memória — acaba a ambiguidade entre "anotar onde".
- `/mobilizar` herda a disciplina de grafo de dependências do artigo (menos espera desperdiçada, menos falha silenciosa).

Custos:

- Mais um serviço opcional para o usuário operar (Docker/systemd). Mitigado: opcional de verdade, com degradação graciosa e instalação de 3 comandos.
- Risco de conteúdo de sessão sensível ir pro servidor. Mitigado: loopback por default, guia cobre `ignore_paths` e bearer token; e o servidor é do próprio usuário.
- Duas fontes de "memória" podem confundir. Mitigado: regra de fluxo entre camadas (episódico → curado → estrutural) documentada no guia e no CLAUDE.md.

## Alternativas consideradas

1. **Vendorizar o ai-memory no plugin.** Rejeitado: é runtime (servidor Rust + SQLite + hooks instalados fora do repo) — contra ADR-0001 e a lista "não portar".
2. **Implementar memória de sessão própria em arquivos.** Rejeitado: recriaria mal (sem captura automática por hooks, sem handoff cross-CLI, sem FTS5) o que um projeto MIT maduro já faz — e viraria manutenção permanente do forge fora do seu core (personas + skills).
3. **Usar o grafo (ADR-0009) como memória de sessão.** Rejeitado: camadas diferentes. O grafo é estrutural e curado (precisão > recall, proveniência obrigatória); sessão é episódica e volumosa. Misturar encheria o grafo de ruído.
4. **Não integrar nada.** Rejeitado: a perda de contexto entre sessões é a dor número 1 de continuidade da fábrica, e a solução externa compatível com os 3 CLIs já existe, é MIT e é self-hosted.
