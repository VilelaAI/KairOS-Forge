---
name: mapear-arquitetura
description: Faz inventário estrutural do código existente — componentes, acoplamento, duplicação de domínio, bounded contexts e plano incremental de decomposição. Use em projetos brownfield antes de refatorações grandes, antes de extrair serviço, ao herdar codebase ou quando o usuário disser "está virando um monolito". Read-only: produz mapa em docs/arquitetura/MAPA-YYYY-MM-DD.md. Não modifica código.
---

# Mapear arquitetura — inventário estrutural do código

Você está sendo invocado para produzir um mapa honesto da arquitetura **atual** do projeto, não a ideal. O objetivo é evidência para decidir o próximo passo de evolução, não recomendação genérica.

## Regra de ouro

Read-only. Você lê arquivos, roda comandos de inspeção (find, ls, git log, ferramentas de análise estática que **já existam** no projeto) e produz um único artefato: o mapa. Não refatore, não crie tickets, não rode build se não for necessário para o mapa.

Toda afirmação no mapa precisa de **evidência verificável** (`arquivo:linha`, comando rodado, métrica calculada). Sem evidência, marque como "hipótese a validar".

## Quando usar

- Antes de qualquer refatoração que toca 3+ módulos.
- Quando o usuário pedir "extrair serviço", "quebrar monolito", "modularizar".
- Ao herdar projeto desconhecido (segundo passo depois de `/kairos-forge:onboardar`).
- Quando `/kairos-forge:auditar` apontar "código sem dono" ou "acoplamento alto" como gap principal.
- Antes de decisões arquiteturais grandes que precisariam de ADR.

## Fluxo

### 1. Confirmar escopo

Pergunte ao usuário:

- O mapa cobre o repo inteiro ou só um diretório? (ex.: `apps/api/`)
- Há alguma área que **não** deve ser auditada? (ex.: vendor, generated, legacy congelado)
- Já existe uma hipótese ("acho que o módulo X está acoplado com Y") ou é exploração aberta?

Se o repo for grande (> 50k linhas), exija escopo. Mapear tudo em um passo só vira mapa inútil.

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
**Coordenado por:** Diego (com Fernanda/Thiago/Rafael conforme dimensões)
**Base analisada:** `<branch / commit>`

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
