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
5. Listar próximos passos para o usuário

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

5. **Confirmar para o usuário:**

```
✅ Onboarding concluído.

Estrutura criada:
- CLAUDE.md (preenchido)
- contextos/ (inclui testes e gates)
- decisoes/log.md
- decisoes/estado-operacional.md
- docs/specs/ e docs/specs/validacoes/
- docs/adr/ (vazio, será preenchido pelo arquiteto)

Próximos passos sugeridos:
1. Revise o CLAUDE.md gerado e ajuste o que ficou impreciso
2. Para a próxima feature, rode: /kairos-forge:especificar <descrição>
3. Depois de implementar uma SPEC, rode: /kairos-forge:validar SPEC-NNN
4. Sexta-feira, rode: /kairos-forge:auditar para ver pontuação inicial
```

## Regras

- **Uma pergunta por vez.** Não enfileire as 7.
- **Não invente respostas.** Se o usuário não souber algo, deixe a seção do CLAUDE.md como `<a preencher>`.
- **PT-BR em tudo gerado.** Verifique acentuação antes de salvar.
- **Não rode `git init` sem perguntar.** Alguns projetos já estão em monorepo.
- **Não modifique `.gitignore` existente.** Apenas anexe linhas necessárias se faltar `.env`.
