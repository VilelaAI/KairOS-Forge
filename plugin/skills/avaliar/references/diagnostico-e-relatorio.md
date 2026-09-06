# Diagnóstico por agrupamento e relatório

Detalhe dos Passos 6 e 8 da skill `avaliar`: modelo da tabela de agrupamento por causa
raiz, modelo do relatório e o volante de qualidade que liga as rodadas.

## 6. Diagnosticar por agrupamento — o passo que quase todo mundo pula

Não corrija caso a caso. **Agrupe as falhas por causa raiz** e trate a causa:

```markdown
| Grupo de falha | Casos | Causa provável | Ação |
|---|---|---|---|
| Cita política inexistente | 7 | Sem instrução de recusa quando a base não cobre | Prompt: exigir "não encontrei" |
| Responde em inglês | 3 | Idioma não fixado no prompt | Prompt: fixar PT-BR |
| Ignora a base e responde de memória | 4 | Ferramenta de busca opcional no fluxo | Tornar a consulta obrigatória |
```

Sete casos com a mesma causa são **um** problema, não sete. Corrigir caso a caso
é ajustar o sistema ao gold set — Goodhart pela porta dos fundos.

## 8. Registrar

`evals/<slug>/RELATORIO-YYYY-MM-DD.md`:

```markdown
# Eval — <comportamento> — YYYY-MM-DD

**Veredicto:** acima / abaixo do limiar
**Limiar:** <número + o que ele protege>
**Baseline → atual:** <n>% → <n>%
**Visível:** <n>% (<N> casos) · **Selado:** <n>% (<N> casos) · **Divergência:** <n> pts
**Gold set:** <N> casos (versão/commit) · **Digest do artefato:** `<sha256 curto>`
**Juiz:** <modelo e versão pinada> · **Família do gerador:** <modelo> · **Painel:** sim/não
**Eixos avaliados:** <quais> · **descartados:** <quais e por quê>

## Resultado por eixo
## Falhas agrupadas por causa raiz
## Ações recomendadas (e para quem)
## Casos de fronteira em discussão
```

## O volante de qualidade

Cada volta compõe — é assim que o eval deixa de ser evento e vira prática:

```
avaliar → agrupar causas → corrigir a causa → verificar contra o gold set
   ↑                                                          │
   └────────── monitorar produção por falha nova ◀────────────┘
```

Falha nova encontrada em produção **vira caso no gold set** antes de ser
corrigida. É o que impede a mesma regressão de voltar — e o que faz o gold set
crescer no lugar certo em vez de crescer por invenção.
