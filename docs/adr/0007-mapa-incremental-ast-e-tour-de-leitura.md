# ADR-0007 — Mapa incremental, coleta opcional via AST e tour de leitura ordenado

**Status:** Proposto
**Data:** 2026-05-24

## Contexto

O `Understand-Anything` (https://github.com/Lum1104/Understand-Anything) é um plugin Claude Code que transforma codebase em grafo de conhecimento interativo (JSON + dashboard) combinando **tree-sitter** (estático, determinístico) com **LLM** (semântico). Tem 6 agentes (`project-scanner`, `file-analyzer`, `architecture-analyzer`, `tour-builder`, `graph-reviewer`, `domain-analyzer`) e features como busca semântica, tours ordenados por dependência, análise de impacto de diff e updates incrementais.

A análise comparativa com a v0.6.0 do `kairos-forge` mostrou três sobreposições conceituais com `mapear-arquitetura` e `onboardar`, mas três lacunas operacionais que vale fechar sem importar o paradigma de dashboard interativo:

1. **Coleta de evidência hoje é só `grep`/`find` + leitura LLM.** Em repos grandes (200k+ linhas), isso perde precisão e é caro em tokens. AST parsing dá inventário de símbolos, imports e call graph com baixo ruído.
2. **`mapear-arquitetura` regenera o mapa do zero a cada execução.** Em projetos onde o mapa é mensal, re-ler tudo é desperdício — a maior parte do código não mudou desde a última base.
3. **`onboardar` em brownfield termina apontando para `mapear-arquitetura`**, mas não oferece um caminho de leitura ordenado para o dev novo. Saber que existe um mapa não é o mesmo que saber por onde começar a ler.

O `Understand-Anything` resolve os três pontos, mas o faz no paradigma "JSON + dashboard interativo + servidor local", que conflita com a filosofia markdown-first/CLI-native/diffável-em-PR já firmada nas ADRs anteriores.

## Decisão

A partir da v0.7.0, estender `mapear-arquitetura` e `onboardar` (sem criar skill nova) com três capacidades:

### 1. Modo `--incremental` em `/kairos-forge:mapear-arquitetura`

Quando invocada com `--incremental`, a skill:

- Lê o mapa mais recente em `docs/arquitetura/MAPA-YYYY-MM-DD.md` como base.
- Calcula `git diff <commit-base-do-mapa>...HEAD --name-only` para identificar arquivos tocados.
- Re-analisa apenas módulos afetados (próprio módulo + módulos que importam dele).
- Gera um novo mapa `MAPA-YYYY-MM-DD.md` que herda as seções não tocadas e marca explicitamente o que foi re-analisado vs. herdado (`<!-- herdado de MAPA-AAAA-BB-CC -->`).
- Hotspots de mudança são recalculados sempre (são baratos via `git log`).

Sem `--incremental`, o comportamento atual (full scan) permanece como default — preserva o contrato existente.

### 2. Coleta opcional via tree-sitter na fase "3.1 Inventário de componentes"

A skill passa a detectar se `tree-sitter` (CLI) está disponível no `PATH`. Se sim, Diego pode usar para extrair:

- Lista de símbolos exportados por arquivo
- Grafo de imports/requires resolvido (não só por grep textual)
- Contagem de funções/classes/métodos por arquivo

Se não estiver instalado, a skill cai no comportamento atual (`grep`/`find`/leitura LLM) e marca no mapa: `"Inventário via grep — instalar tree-sitter melhora precisão."`

**Não é dependência obrigatória.** É um upgrade opt-in. Manter o caminho sem AST garante que a skill continua funcionando em qualquer ambiente (inclusive sandboxes restritas como o próprio Claude Code on the web).

### 3. Output complementar "tour de leitura" em `/kairos-forge:onboardar` para brownfield

Quando o onboarding detecta projeto brownfield (existe código real além de boilerplate) **e** existe um `MAPA-*.md` recente em `docs/arquitetura/`, a skill gera adicionalmente `docs/arquitetura/TOUR-LEITURA.md` com:

- Ordem de leitura pedagógica baseada no grafo de imports do mapa (módulos folha primeiro, depois orquestradores, depois entrypoints).
- Por arquivo: 1 frase explicando "o que é" e "por que ler isso agora".
- Tempo estimado de leitura por seção (5/15/30 min) para o dev escolher escopo.
- Marcação clara do que pular em primeira leitura.

Se não houver mapa, a skill sugere rodar `/kairos-forge:mapear-arquitetura` primeiro e não gera o tour.

### 4. Dimensão Estrutura em `/auditar` ganha critério "mapa fresco"

Critério novo (3 dos 20 pts da dimensão Estrutura): "Mapa arquitetural existe e foi atualizado nos últimos 90 dias OU o repo tem menos de 90 dias OU não houve commits desde o último mapa." Incentiva o uso do modo incremental sem virar burocracia.

## Consequências

Boas:

- Mapas em projetos grandes ficam baratos de manter (re-mapear semanal vira viável).
- Tree-sitter quando disponível reduz token cost e aumenta precisão sem quebrar nada quando ausente.
- Dev novo em brownfield ganha caminho concreto de leitura, não só "leia o mapa de 40 páginas".
- Auditoria pressiona suavemente para o mapa não envelhecer.
- Nenhuma skill nova entra no catálogo — a curva de aprendizado não cresce.

Custos:

- `mapear-arquitetura` ganha branching de fluxo (`--incremental` vs. full, com vs. sem tree-sitter). SKILL.md vai crescer — manter abaixo de 500 linhas pode exigir mover detalhes para `references/`.
- Detecção de tree-sitter precisa ser robusta (CLI vs. binding de linguagem — só o CLI conta como detectado).
- Mapa incremental pode esconder drift se o usuário nunca rodar full. Mitigação: documentar que a cada N execuções incrementais (sugestão: 4) o próximo `--incremental` aviso "considere full scan".
- Tour de leitura pode ficar desatualizado se mapa envelhecer. Aceitável — ele é gerado a partir do mapa, então tem a mesma janela de validade.

## Alternativas consideradas

1. **Importar o `Understand-Anything` inteiro como dependência opcional.**
   Rejeitado: paradigma incompatível (dashboard interativo + JSON como artefato primário). Markdown é diffável em PR, sobrevive sem servidor, é auditável. Grafo interativo é mais um sistema pra manter sem ganho proporcional pro usuário do `kairos-forge`.

2. **Criar skill nova `/kairos-forge:explorar` com dashboard local.**
   Rejeitado: adiciona skill ao catálogo (já são 10), introduz dependência de servidor HTTP, e o ganho real é dos 3 pontos acima, não da visualização. Markdown bem estruturado + tour de leitura cobre 80% do valor com 10% do custo.

3. **Tornar tree-sitter dependência obrigatória.**
   Rejeitado: quebra a portabilidade. O plugin precisa rodar em qualquer Claude Code/Codex/OpenCode, inclusive em ambientes que não têm permissão para instalar binários (Claude Code on the web, sandboxes corporativas).

4. **Embutir tour de leitura dentro de `mapear-arquitetura` em vez de `onboardar`.**
   Rejeitado: o tour é artefato de onboarding (consumido por dev novo), não de decisão arquitetural (consumido por Diego/Rafael). Misturar os públicos polui o mapa.

5. **Análise de impacto de diff como skill separada.**
   Avaliado e adiado: já existe sobreposição parcial com `revisar` (que olha PR pré-merge). Antes de criar `impactar` ou similar, faz sentido medir se o gap real existe — possível ADR-0008 depois de duas releases de uso da v0.7.0.

## Não-objetivos

- **Dashboard interativo.** Não vai existir. Se um dia for necessário, ADR separada.
- **JSON como artefato primário.** Markdown continua sendo a fonte da verdade. Se gerarmos JSON intermediário (cache do tree-sitter, por exemplo), ele vai em `.cache/` e fica fora do controle de versão.
- **Análise semântica de domínio via LLM separada do mapa.** O `Understand-Anything` tem `domain-analyzer` específico — no `kairos-forge`, isso já está coberto pelo passo "3.4 Bounded contexts" do `mapear-arquitetura` (Diego com apoio de Fernanda quando vira dado).

## Roadmap subsequente

P2 (ainda em 0.7.0):

- Documentar no README a ordem brownfield: `onboardar` → `mapear-arquitetura` (full) → `onboardar` re-roda e gera `TOUR-LEITURA.md` → `mapear-arquitetura --incremental` recorrente.
- `templates/` ganha exemplo de `MAPA-*.md` herdado e de `TOUR-LEITURA.md`.

P3 (0.8.0 ou depois, dependendo de demanda real):

- Skill `impactar` para análise de ripple effect de diff (avaliar gap real primeiro).
- Cache de tree-sitter compartilhável entre execuções (`.cache/kairos-forge/ast/`).
- Modo `--explain` em `mapear-arquitetura` que aceita pergunta em linguagem natural sobre o mapa salvo.
