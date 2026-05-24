---
name: mapear-arquitetura
description: Faz inventário estrutural do código existente — componentes, acoplamento, duplicação de domínio, bounded contexts e plano incremental de decomposição. Use em projetos brownfield antes de refatorações grandes, antes de extrair serviço, ao herdar codebase ou quando o usuário disser "está virando um monolito". Aceita modo --incremental para re-analisar só o que mudou desde o mapa anterior, e usa tree-sitter (CLI) quando disponível para precisão maior no inventário. Read-only: produz mapa em docs/arquitetura/MAPA-YYYY-MM-DD.md. Não modifica código.
---

# Mapear arquitetura — inventário estrutural do código

Você está sendo invocado para produzir um mapa honesto da arquitetura **atual** do projeto, não a ideal. O objetivo é evidência para decidir o próximo passo de evolução, não recomendação genérica.

## Regra de ouro

Read-only. Você lê arquivos, roda comandos de inspeção (find, ls, git log, ferramentas de análise estática que **já existam** no projeto) e produz um único artefato: o mapa. Não refatore, não crie tickets, não rode build se não for necessário para o mapa.

Toda afirmação no mapa precisa de **evidência verificável** (`arquivo:linha`, comando rodado, métrica calculada). Sem evidência, marque como "hipótese a validar".

## Modos de execução

- **Full scan (default).** Mapeia tudo dentro do escopo. Use na primeira execução, ao mudar de branch significativa, ou quando suspeitar que muita coisa drift-ou desde o último mapa.
- **`--incremental`.** Herda o mapa mais recente em `docs/arquitetura/MAPA-*.md` e re-analisa apenas módulos tocados desde o commit-base daquele mapa. Use em re-mapeamentos frequentes (semanal/quinzenal). Recomendação: a cada 4 execuções incrementais, faça um full para evitar drift acumulado.

Se o usuário pedir `--incremental` mas não existir mapa anterior, avise e caia para full.

## Quando usar

- Antes de qualquer refatoração que toca 3+ módulos.
- Quando o usuário pedir "extrair serviço", "quebrar monolito", "modularizar".
- Ao herdar projeto desconhecido (segundo passo depois de `/kairos-forge:onboardar`).
- Quando `/kairos-forge:auditar` apontar "código sem dono" ou "acoplamento alto" como gap principal.
- Antes de decisões arquiteturais grandes que precisariam de ADR.

## Fluxo

### 1. Confirmar escopo e modo

Pergunte ao usuário:

- O mapa cobre o repo inteiro ou só um diretório? (ex.: `apps/api/`)
- Há alguma área que **não** deve ser auditada? (ex.: vendor, generated, legacy congelado)
- Já existe uma hipótese ("acho que o módulo X está acoplado com Y") ou é exploração aberta?

Se o repo for grande (> 50k linhas), exija escopo. Mapear tudo em um passo só vira mapa inútil.

**Se o usuário pediu `--incremental`:**

1. Liste mapas existentes: `ls -1 docs/arquitetura/MAPA-*.md 2>/dev/null | sort | tail -1`.
2. Se não houver, avise e caia para full scan.
3. Se houver, leia o cabeçalho do mapa anterior para extrair o **commit-base** (campo "Base analisada"). Se não houver, peça pro usuário ou caia para full.
4. Calcule arquivos tocados: `git diff <commit-base>...HEAD --name-only` (ou `git log <commit-base>..HEAD --pretty=format: --name-only | sort -u`).
5. Liste os módulos afetados: os próprios + os que importam deles (mapa de imports anterior, ou grep cruzado).
6. Conte quantas execuções incrementais consecutivas existem em `docs/arquitetura/` desde o último full scan. Se ≥ 4, avise no início: "Considere um full scan na próxima execução para evitar drift acumulado."

### 2. Laura escolhe os arquitetos

Invoque `laura-tech-lead`. Ela decide quem entra com base no que o usuário descreveu:

| Sinal | Arquiteto |
|---|---|
| Fluxo entre serviços/módulos, eventos, filas | **Diego** (sistemas) |
| Banco, schema, dados, performance de query | **Fernanda** (dados) |
| API pública, integração externa, contratos | **Thiago** (integrações) |
| Decisão de padrão, trade-off de tecnologia, dívida estrutural | **Rafael** (Staff) |

Para mapa estrutural completo, Diego coordena e chama os outros conforme as evidências aparecem.

### 3. Coletar evidências

Para cada dimensão abaixo, gere evidência com comando real. **Não pule etapas inventando o que provavelmente está lá.**

#### 3.1. Inventário de componentes

- Diretórios de primeiro e segundo nível: `find . -maxdepth 2 -type d -not -path '*/node_modules*' -not -path '*/.git*'`
- Linhas por módulo: use `cloc`, `tokei` ou `find ... -name '*.ts' | xargs wc -l` conforme stack
- Número de arquivos por módulo
- Pontos de entrada (`main`, `index`, `server`, `app`, rotas)

Registre os 10 maiores módulos por linhas.

**Tree-sitter (opt-in).** Detecte se o CLI está disponível com `command -v tree-sitter`. Se estiver:

- Use para extrair símbolos exportados, contagem de funções/classes/métodos por arquivo e imports resolvidos por AST (não só grep textual).
- Anote no mapa: `"Inventário via tree-sitter <versão>."`

Se não estiver, caia para `grep`/`find` e anote no mapa: `"Inventário via grep — instalar tree-sitter melhora precisão (https://tree-sitter.github.io/tree-sitter/cli)."`

**Não tente instalar tree-sitter** durante a execução da skill. Se faltar, é decisão do usuário se quer adicionar à toolchain. A skill funciona sem.

**Modo `--incremental`:** rode o inventário apenas para os módulos afetados (passo 1). Para os demais, marque a seção com `<!-- herdado de MAPA-AAAA-BB-CC -->` e copie o conteúdo da seção equivalente no mapa anterior.

#### 3.2. Acoplamento

Para cada módulo grande, levantar:

- **Quem importa esse módulo:** grep por path do módulo nos `import`/`require`/`use`.
- **O que esse módulo importa:** ler arquivos de barril (`index.ts`, `__init__.py`, `mod.rs`).
- **Direção dos imports:** se módulo A importa B e B importa A, registrar como **acoplamento bidirecional**.
- **Volatilidade:** `git log --since='90 days ago' --pretty=format: --name-only -- <módulo>/ | sort | uniq -c | sort -rn` mostra hotspots de mudança.

Dimensões para classificar acoplamento:

| Dimensão | Pergunta |
|---|---|
| Força | Quantos símbolos cruzam a fronteira? |
| Distância | Estão na mesma camada ou atravessam camadas (UI ↔ DB)? |
| Volatilidade | Mudam juntos com frequência? (`git log` em pares) |

#### 3.3. Duplicação de domínio

Procure por:

- Mesmos conceitos modelados em dois lugares (`UserDTO`, `User`, `UserModel`, `IUser`).
- Validação repetida (mesma regra de negócio em UI, API e DB).
- Funções utilitárias com nome quase igual em módulos diferentes.

Se houver ferramenta de detecção de duplicação no projeto (`jscpd`, `pmd`, `simian`), use. Se não houver, faça amostragem manual e marque como "indício, não medição".

#### 3.4. Bounded contexts

Agrupe módulos por **contexto de negócio**, não por camada técnica. Pergunte:

- Que mudanças tendem a tocar este grupo de arquivos juntos?
- Existe linguagem ubíqua diferente entre módulos? (ex.: "Cliente" no faturamento, "Lead" no marketing — mesma entidade?)
- Onde o `git log` mostra commits que tocam módulos aparentemente sem relação?

Saída esperada: 3 a 7 contextos. Mais que isso, refine. Menos que isso, provavelmente o projeto ainda não diferencia domínios.

#### 3.5. Pontos de tensão

Para cada contexto, registre 1-2 pontos onde a estrutura atual **vai doer** se a feature roadmap continuar:

- Camadas misturadas (regra de negócio em controller, query em template).
- Configuração espalhada (envs lidas em N lugares).
- Falta de fronteira clara entre camadas.

### 4. Plano de decomposição incremental

Não recomende reescrita. Sempre incremental:

1. **Movimentos baratos primeiro** — renomear, mover arquivo, extrair função. Reversíveis em horas.
2. **Movimentos médios** — extrair módulo interno, isolar interface, introduzir camada de adapter.
3. **Movimentos grandes** — extrair serviço, trocar banco, romper dependência cíclica.

Cada movimento precisa de:

- Pré-condição (o que tem que estar verde antes)
- Critério de sucesso (como saber que terminou)
- Rollback (como reverter se der ruim)

### 5. Salvar mapa

Em `docs/arquitetura/MAPA-YYYY-MM-DD.md`:

```markdown
# Mapa arquitetural — <projeto> — YYYY-MM-DD

**Escopo:** <repo inteiro / apps/api / etc.>
**Modo:** full | incremental (herdado de MAPA-AAAA-BB-CC)
**Coordenado por:** Diego (com Fernanda/Thiago/Rafael conforme dimensões)
**Base analisada:** `<branch / commit-sha>`
**Coleta:** tree-sitter <versão> | grep (sem AST)

## Resumo executivo

- 3 bullets de no máximo 2 linhas cada
- Risco principal em 1 frase

## Inventário

### Componentes de primeiro nível

| Módulo | Linhas | Arquivos | Hotspot 90d | Dono (CODEOWNERS) |
|---|---|---|---|---|

### Pontos de entrada

| Tipo | Path | Observação |
|---|---|---|

## Acoplamento

### Mapa de imports relevantes

| De | Para | Símbolos | Força | Distância | Bidirecional? |
|---|---|---|---|---|---|

### Hotspots de mudança conjunta

| Par de módulos | Commits conjuntos 90d | Hipótese |
|---|---|---|

## Duplicação de domínio

| Conceito | Implementações | Evidência | Severidade |
|---|---|---|---|

## Bounded contexts identificados

### Contexto: <nome>
**Responsabilidade:** 1 frase.
**Módulos:** lista.
**Linguagem ubíqua:** termos centrais.
**Fronteira hoje:** clara / borrada / inexistente.

## Pontos de tensão

| ID | Tensão | Onde | Por que dói no roadmap |
|---|---|---|---|

## Plano de decomposição incremental

### Movimentos baratos (próximos 7 dias)
1. **<título>** — pré-condição / critério / rollback.

### Movimentos médios (1-4 semanas)
1. **<título>** — idem.

### Movimentos grandes (> 1 mês)
1. **<título>** — idem.

## ADRs sugeridas

Liste decisões que merecem ADR formal antes de execução.

## Próximo passo

- Discutir mapa com time
- Abrir ADR para movimento grande #1
- Rodar `/kairos-forge:especificar` para movimentos médios que viram features
```

### 6. Responder ao usuário

Resumo curto (máximo 10 linhas):

```markdown
Mapa salvo em `docs/arquitetura/MAPA-YYYY-MM-DD.md`.

Escopo: <X>. Coordenado por: Diego (+ <outros>).

Achados principais:
1. <achado>
2. <achado>
3. <achado>

Movimento mais barato com maior alavancagem: <título>.
Maior risco se nada for feito: <risco em 1 frase>.

Próximo passo sugerido: <ADR / SPEC / nada por agora>.
```

## Regras

- **Read-only.** Não edite código, nem reorganize arquivos como "demonstração".
- **Evidência ou hipótese.** Tudo que não foi medido vai marcado como hipótese.
- **Sem reescrita.** Plano é incremental. Se reescrita for mesmo necessária, isso é um ADR, não um item de plano.
- **PT-BR.**
- **Não rode comandos destrutivos.** Nada de `git clean`, `rm`, migrations. Inspeção apenas.
- **Pare cedo se o escopo não foi delimitado.** Mapear repo de 200k linhas sem foco vira ruído.
- **Não tente instalar tree-sitter.** Se faltar, anote no mapa e siga com grep.
- **Modo incremental herda, não inventa.** Seções não tocadas vêm do mapa anterior com marcador `<!-- herdado de ... -->`. Nunca reescreva uma seção herdada — ou re-analisa, ou copia tal qual.
