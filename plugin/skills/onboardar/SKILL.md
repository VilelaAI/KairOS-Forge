---
name: onboardar
description: Entrevista de onboarding que prepara um projeto para usar a fábrica kairos-forge. Use na primeira vez em um projeto, depois de instalar o plugin. Faz 7 perguntas, gera CLAUDE.md preenchido, cria estrutura de pastas, contexto de testes, estado operacional e ativa o ciclo dos agentes. Leva ~15 minutos.
---

# Onboardar — entrevista inicial do kairos-forge

Você está sendo invocado para preparar este projeto para a fábrica kairos-forge.

## O que você vai fazer

1. Conduzir uma entrevista de 7 perguntas com o usuário
2. Criar a estrutura de pastas mínima
3. Gerar o `CLAUDE.md` do projeto preenchido com as respostas
4. Criar `contextos/testes.md` e `decisoes/estado-operacional.md`
5. Em projeto brownfield com mapa arquitetural existente, gerar `docs/arquitetura/TOUR-LEITURA.md`
6. Listar próximos passos para o usuário

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
mkdir -p contextos decisoes docs/specs docs/specs/validacoes docs/adr
```

2. **Gerar `CLAUDE.md`** na raiz do projeto, usando o template em `templates/CLAUDE.md.template` deste plugin como base, preenchido com as respostas da entrevista.

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

6. **Detectar brownfield e oferecer tour de leitura.**

O projeto é brownfield se houver código real além de boilerplate. Heurística simples:

- Conta arquivos de código (extensões da stack respondida): `find . -type f \( -name '*.ts' -o -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.java' \) -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/vendor/*' | wc -l`. Ajuste extensões conforme a stack.
- Se > 30 arquivos de código **e** existe `docs/arquitetura/MAPA-*.md`, gere `docs/arquitetura/TOUR-LEITURA.md`.
- Se > 30 arquivos de código **mas não há mapa**, recomende rodar `/kairos-forge:mapear-arquitetura` antes — não gere o tour sem mapa.
- Se ≤ 30 arquivos, pule este passo silenciosamente (greenfield ou projeto pequeno demais).

Conteúdo do `TOUR-LEITURA.md` (gerado a partir do mapa mais recente):

```markdown
# Tour de leitura — <projeto>

**Gerado a partir de:** `docs/arquitetura/MAPA-YYYY-MM-DD.md`
**Para:** dev novo no projeto. Leia nesta ordem.

## Como usar

Ordem é pedagógica: começa pelos módulos folha (sem dependências internas), sobe para orquestradores, termina nos entrypoints. Cada item tem tempo estimado para você escolher escopo.

- **5 min** — só o cabeçalho e função principal
- **15 min** — leitura completa do arquivo
- **30 min** — arquivo + um teste relacionado

## Passo 1 — Fundações (módulos folha)

### `<caminho/arquivo>` — 15 min
**O que é:** 1 frase.
**Por que ler agora:** 1 frase (geralmente: "tudo o resto depende disto").

## Passo 2 — Camada de domínio

(idem)

## Passo 3 — Orquestradores e serviços

(idem)

## Passo 4 — Entrypoints (API, CLI, jobs)

(idem)

## O que pular em primeira leitura

- `<caminho>` — útil, mas não bloqueia entendimento.
- `<caminho>` — config/infra, leia quando precisar mexer.

## Próximo passo

Depois do tour, rode `/kairos-forge:mapear-arquitetura --incremental` se algo mudou desde a base do mapa.
```

Se o mapa anterior não tiver inventário de imports suficiente para inferir ordem, marque os arquivos com `<ordem a refinar>` e avise no resumo final.

7. **Confirmar para o usuário:**

```
✅ Onboarding concluído.

Estrutura criada:
- CLAUDE.md (preenchido)
- contextos/ (inclui testes e gates)
- decisoes/log.md
- decisoes/estado-operacional.md
- docs/specs/ e docs/specs/validacoes/
- docs/adr/ (vazio, será preenchido pelo arquiteto)
<- docs/arquitetura/TOUR-LEITURA.md (se brownfield com mapa)>

Próximos passos sugeridos:
1. Revise o CLAUDE.md gerado e ajuste o que ficou impreciso
2. <Se brownfield sem mapa: rode /kairos-forge:mapear-arquitetura para gerar o mapa, depois re-rode /kairos-forge:onboardar para ganhar o TOUR-LEITURA.md>
3. Para a próxima feature, rode: /kairos-forge:especificar <descrição>
4. Depois de implementar uma SPEC, rode: /kairos-forge:validar SPEC-NNN
5. Sexta-feira, rode: /kairos-forge:auditar para ver pontuação inicial
```

## Regras

- **Uma pergunta por vez.** Não enfileire as 7.
- **Não invente respostas.** Se o usuário não souber algo, deixe a seção do CLAUDE.md como `<a preencher>`.
- **PT-BR em tudo gerado.** Verifique acentuação antes de salvar.
- **Não rode `git init` sem perguntar.** Alguns projetos já estão em monorepo.
- **Não modifique `.gitignore` existente.** Apenas anexe linhas necessárias se faltar `.env`.
- **TOUR-LEITURA.md só com mapa.** Não invente ordem de leitura sem o mapa como evidência. Se faltar, peça pra rodar `/kairos-forge:mapear-arquitetura` primeiro.
