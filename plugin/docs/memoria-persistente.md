# Memória persistente da fábrica — guia de integração

A fábrica kairos-forge trabalha com **três camadas de memória** (ADR-0010). Este guia explica cada uma, como ativar a camada opcional de sessão via [ai-memory](https://github.com/akitaonrails/ai-memory), e como as skills usam tudo isso.

## As três camadas

| Camada | O que guarda | Onde vive | Quem mantém |
|---|---|---|---|
| **1. Episódica (sessão)** | O que aconteceu em cada sessão: prompts, ferramentas rodadas, tentativas que falharam, handoff "onde parei" | Servidor ai-memory do usuário (wiki markdown + SQLite, **fora do repo**) | Hooks automáticos — zero cerimônia. **Opcional** |
| **2. Curada (arquivos)** | Decisões (`decisoes/log.md`), incidentes caros (`.agents/memory/`), convenções e restrições (`contextos/`), ADRs | No repo do projeto | Humano + agentes, deliberadamente |
| **3. Estrutural (grafo)** | Entidades e relações com proveniência; responde pergunta multi-hop | `.agents/grafo/` no repo | Olívia, via `/kairos-forge:mapear-conhecimento` (ADR-0009) |

**Regra de fluxo:** a camada 1 é matéria-prima. O que for durável **sobe de camada**: decisão técnica vira linha em `decisoes/log.md` (e ADR se arquitetural); lição cara de incidente vira memória em `.agents/memory/`; fato estrutural vira aresta no grafo. O **repo é a fonte da verdade do projeto** — a memória de sessão nunca substitui os arquivos curados.

**Regra anti-duplicação:** as skills não fazem double-write. Captura de sessão é trabalho dos hooks do ai-memory (automática); escrita durável é nos arquivos do repo. A tool `memory_write_page` fica reservada para **preferências pessoais/globais do usuário** (`scope: global` — estilo de código, escolhas de stack pessoais), que não pertencem a nenhum repo.

## Ativando a camada de sessão (opcional)

O ai-memory é um projeto MIT independente: um binário Rust que roda servidor MCP/HTTP local (loopback por default) e instala hooks de ciclo de vida nos CLIs. O forge **não** o embarca — apenas o detecta e usa quando presente.

Instalação resumida (Docker; detalhes e alternativas em [`docs/install.md` do ai-memory](https://github.com/akitaonrails/ai-memory/blob/main/docs/install.md)):

```bash
# 1. Wrapper CLI
mkdir -p ~/.local/bin
curl -fsSL https://raw.githubusercontent.com/akitaonrails/ai-memory/main/bin/ai-memory \
    -o ~/.local/bin/ai-memory && chmod +x ~/.local/bin/ai-memory

# 2. Servidor local (loopback; omita as linhas de LLM pra modo zero-LLM)
docker run -d --name ai-memory --restart unless-stopped \
    -p 127.0.0.1:49374:49374 -v ai-memory-data:/data \
    akitaonrails/ai-memory:latest

# 3. Conectar o(s) CLI(s) que você usa
ai-memory install-mcp   --client claude-code --apply
ai-memory install-hooks --agent  claude-code --apply
# Codex:    --client codex    / --agent codex
# OpenCode: --client opencode / --agent opencode
# Cursor:   --client cursor   / --agent cursor
```

Num projeto com meses de história antes do ai-memory, rode uma vez:

```bash
cd /caminho/do/projeto && ai-memory bootstrap
```

### Como as skills detectam

Simples: **as tools MCP `memory_*` existem na sessão?** (`memory_query`, `memory_briefing`, `memory_handoff_accept`, `memory_status`, …). Se existem, a camada 1 está ativa e as skills a usam. Se não existem, as skills seguem sem ela — nenhuma skill exige ai-memory, nenhuma falha na ausência dele.

## O que cada skill faz com a memória de sessão

| Skill | Com `memory_*` disponível |
|---|---|
| `/onboardar` | Informa a camada opcional; se ativa, sugere `ai-memory bootstrap` |
| `/rodar` e `/mobilizar` | Laura abre com `memory_handoff_accept` (handoff pendente) e `memory_briefing` — "onde paramos" entra na triagem sem o usuário recontar |
| `/especificar` | Arquiteto roda `memory_query` sobre as entidades da feature: tentativas passadas, abordagens descartadas, decisões de sessões anteriores |
| `/evoluir` | `memory_recent` + `memory_query` viram evidência das 5 perguntas (repetição, atrito…) em vez de depender só da lembrança do usuário |
| `/auditar` | `memory_status` entra no relatório como informação ("memória de sessão ativa/inativa") — sem pontuar |
| `/mapear-conhecimento` | Páginas relevantes da wiki (`memory_query` → `memory_read_page`) entram como corpus opcional de extração, com fonte `ai-memory:<workspace>/<projeto>/<path>` |

Frases que acionam naturalmente: "onde paramos?", "já discutimos X?", "o que decidimos sobre Y semana passada?", "me atualiza do projeto".

## Continuidade entre CLIs

O forge é multi-CLI por design (ADR-0004/ADR-0011) e o ai-memory fecha o ciclo: saia do Claude Code no meio de uma SPEC, abra o Codex ou o Cursor no mesmo diretório — o hook de SessionStart injeta o handoff ("onde você parou, perguntas abertas, próximos passos") antes do primeiro prompt. Para continuidade de maior fidelidade (retomada nativa de sessão por harness), existe o modo opcional `ai-memory run claude` / `ai-memory run codex` — decisão do usuário, fora do escopo do plugin.

## Segurança

- **Loopback por default.** O quick start liga o servidor em `127.0.0.1` — nada fora da máquina alcança. Só exponha além de loopback com bearer token (`ai-memory generate-auth-token`) e `AI_MEMORY_ALLOWED_HOSTS`.
- **Exclusões de captura.** Caminhos sensíveis (segredos, dados de cliente) podem ser excluídos da captura por política `[capture] ignore_paths` num `.ai-memory.toml` — o evento descartado nunca entra em spool, transporte ou armazenamento. Configure antes de trabalhar em área sensível.
- **O servidor é do usuário.** Self-hosted, dado não sai da infraestrutura de quem opera. Em projeto com compliance forte, avalie com o time de segurança (Helena tem opinião) antes de ativar captura — e lembre: a fábrica funciona sem a camada 1.

## Relação com o grafo de conhecimento

As camadas 1 e 3 são complementares, não concorrentes:

- **ai-memory** responde "o que aconteceu / o que discutimos" (episódico, busca FTS5, volume alto, decaimento natural).
- **Grafo** responde "o que depende de quê / o que é verdade sobre X" (estrutural, proveniência obrigatória, multi-hop, precisão > recall).

No `/mapear-conhecimento atualizar`, a Olívia pode usar a wiki do ai-memory como fonte adicional de extração — sessões antigas frequentemente contêm decisões que nunca chegaram aos arquivos curados. A extração aplica o filtro normal de precisão: só entra no grafo o que tiver fonte citável.
