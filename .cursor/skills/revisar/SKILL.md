---
name: revisar
description: Revisa o diff atual da branch antes de PR ou push. Use sempre antes de abrir PR, antes de fazer push para branch protegida, ou quando quiser segunda opinião sobre código recém-escrito. Aciona equipe de revisão da fábrica — Helena (segurança), Patrícia (QA), Vinícius (performance) e Marcos (infra) conforme o que foi modificado. Cada uma produz parecer em primeira pessoa com severidade (crítico/alto/médio/baixo).
---

# Revisar — análise pré-PR pela equipe de qualidade

Você está sendo invocado para revisar o que está prestes a virar PR.

## Quem revisa o quê

A revisão é **multi-agente**, com cada especialista olhando sua dimensão:

| Agente | O que revisa | Sempre roda |
|---|---|---|
| **Helena** (Security) | OWASP, secrets, auth, RLS, input validation, PII | ✅ Sempre |
| **Patrícia** (QA Lead) | Cobertura de teste, edge cases não cobertos, regressão | ✅ Sempre |
| **Vinícius** (Performance) | Queries N+1, bundle bloat, latência, profiling | Se diff toca código de produção |
| **Marcos** (DevOps) | CI/CD, Dockerfile, secrets em config, rollback plan | Se diff toca `.github/`, `Dockerfile`, `docker-compose`, scripts de deploy |
| **Carlos** (DBA) | Migrations, índices, EXPLAIN ANALYZE, RLS na prática | Se diff toca migrations ou queries SQL |
| **Ada** (Acessib.) | ARIA, contraste, navegação por teclado | Se diff toca componentes JSX/TSX |

Helena e Patrícia são obrigatórios. Os demais entram conforme o escopo do diff.

## Fluxo

### 1. Detectar contexto de revisão

Em ordem de preferência:

1. PR aberto no GitHub → `gh pr diff` ou ler via API
2. Branch ativa diferente de `main`/`master`/`develop` → `git diff <base>...HEAD`
3. Arquivos específicos citados pelo usuário
4. Caso contrário: pergunte ao usuário o que revisar

Se o diff implementa uma SPEC em `docs/specs/` e não houver relatório correspondente em `docs/specs/validacoes/`, avise:

> "Antes da revisão pré-PR, recomendo rodar `/kairos-forge:validar SPEC-NNN` para checar aceite contra a SPEC. Posso continuar a revisão mesmo assim, mas validação e revisão respondem perguntas diferentes."

Continue se o usuário pediu revisão explicitamente.

### 2. Verificar tamanho do diff

```bash
git diff --stat <base>...HEAD
```

Se passar de **500 linhas adicionadas**, pare e devolva:

> "O diff tem N linhas adicionadas. Revisões eficazes ficam abaixo de 500 linhas. Recomendo fatiar este PR antes de eu chamar a equipe. Quer ajuda da Camila (PM) pra fatiar?"

### 3. Detectar áreas tocadas

Use `git diff --name-only` e classifique os arquivos modificados:

- `migrations/`, `*.sql` → +Carlos
- `Dockerfile*`, `.github/`, `docker-compose*`, `scripts/deploy*` → +Marcos
- `*.tsx`, `*.jsx` (componentes) → +Ada
- Código de produção em geral → +Vinícius

### 4. Acionar revisores em paralelo (se possível)

Cada revisor lê o diff **na sua dimensão** e produz parecer em primeira pessoa:

> "**Helena aqui** — fiz a passada de segurança no diff. 1 achado 🔴 crítico, 2 🟠 altos."
>
> 🔴 **Crítico** — `api/users.ts:42` concatena `req.body.email` direto na query SQL. Risk: SQL injection.
> 🟠 **Alto** — `lib/auth.ts:18` não rotaciona JWT em logout. Token revogado fica válido até expirar.
> 🟠 **Alto** — `api/upload.ts` não limita tamanho de arquivo. Risk: DoS por upload gigante.

> "**Patrícia aqui** — analisei cobertura. Veredicto: ⚠️ aprovado com ressalvas."
>
> 🟡 **Médio** — `services/relatorio.ts` adicionou função `gerarPDF` sem teste.
> 🔵 **Baixo** — `components/RelatorioForm.tsx` tem 3 caminhos de erro mas só 1 tem teste.

### 5. Consolidar veredicto

Ao final, **você (a skill)** consolida os pareceres em um único relatório com veredicto agregado:

```markdown
# Revisão pré-PR — <branch>

**Escopo:** N arquivos, M linhas adicionadas, K linhas removidas
**Revisores acionados:** Helena, Patrícia[, Vinícius, Marcos, Carlos, Ada conforme]
**Veredicto agregado:** ✅ aprovado / ⚠️ aprovado com ressalvas / ❌ bloqueado

## 🔴 Crítico (qualquer revisor) → bloqueia merge
- [Helena] api/users.ts:42 — SQL injection. Use prepared statement.

## 🟠 Alto → corrigir antes do merge
- [Helena] lib/auth.ts:18 — Logout não invalida JWT.
- [Helena] api/upload.ts — Sem limite de upload.
- [Vinícius] queries/relatorios.sql — N+1 no loop, EXPLAIN mostra 200x escalonamento.

## 🟡 Médio → corrigir nesta PR ou abrir issue
- [Patrícia] services/relatorio.ts — Função sem teste.

## 🔵 Baixo → comentar e seguir
- [Patrícia] components/RelatorioForm.tsx — Cobertura parcial de erro.

## ✅ O que está bom
- Migrations reversíveis (Carlos aprovou)
- Acessibilidade preservada (Ada checou contraste e ARIA)

## Próximos passos
- 🔴 + 🟠: invocar Lucas (backend) e Marina (frontend) pra corrigir
- 🟡 cobertura: invocar Ricardo (test-automation)
```

### 6. Regras de bloqueio

- **Qualquer 🔴** de qualquer revisor → veredicto agregado é ❌ bloqueado.
- **2+ 🟠** → ⚠️ aprovado com ressalvas, com recomendação forte de corrigir antes.
- Só 🟡 ou 🔵 → ✅ aprovado.

## Regras

- **Não revise você mesmo.** Delegue aos agentes especialistas. Esta skill é orquestradora.
- **Não suprima achados.** Se Helena marcou 🔴, não suavize pra 🟡 porque o usuário tem pressa.
- **Não aprove cegamente.** Mesmo PR pequeno passa por Helena + Patrícia.
- **Não sugira workaround pra 🔴.** Sugira correção. Workaround vira dívida.

## Quando NÃO usar esta skill

- Code review humano em PR de outro dev → use ferramentas do GitHub/GitLab
- Auditoria de segurança da aplicação inteira (escopo maior) → invoque Helena diretamente com escopo amplo
- Discussão sobre design antes de codar → use `/kairos-forge:especificar`
