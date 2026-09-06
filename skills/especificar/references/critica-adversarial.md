# Crítica adversarial antes da aprovação (ADR-0033)

Referência do passo 7 de `/kairos-forge:especificar`. Leia quando a SPEC estiver escrita
e for a hora de escolher os críticos, redigir o arquivo de crítica e fechar a fence
`kairos-critica` que o `ciclo.py` lê.

## 7. Crítica adversarial antes da aprovação (ADR-0033)

A SPEC escrita **não vai direto para o usuário**. Antes, ao menos **dois críticos que
não a escreveram** atacam o documento.

Por que dois, e por que não os autores: um olhar só é revisão, não crítica. E quem
escreveu já decidiu que está bom — pedir para ele reler sem âncora externa é o mesmo
autocorreção intrínseca que o anti-drift recusa (Huang et al., ICLR 2024). O que
funciona é olhar independente com critério explícito.

Escolha entre as personas que **não participaram da redação**, pelo eixo de risco:

| Eixo | Quem ataca | Pergunta |
|---|---|---|
| Requisito | Joana, Norma | Requisito ambíguo, sem critério de aceite verificável, ou inventado sem fonte? |
| Arquitetura | Diego, Fernanda, Thiago | Abordagem cria acoplamento, contradiz o que existe, ou ignora carga real? |
| Testabilidade | Ricardo, Patrícia | Dá para provar cada P1? Comando existe? Evidência é observável? |
| Segurança | Helena | Toca auth, PII, autorização ou input externo sem mitigação declarada? |
| Escopo | Camila, Hugo | O apetite comporta? O P1 é mesmo P1? |

Cada crítico produz achados **com localização** — seção, ID do requisito, linha do
plano. "A SPEC parece boa" não é crítica; se não achou nada, diga qual seção leu e
contra qual critério.

Salve em `docs/specs/criticas/CRITICA-SPEC-NNN-YYYY-MM-DD.md`:

```markdown
# Crítica — SPEC-NNN — YYYY-MM-DD

**Críticos:** Joana (requisitos), Ricardo (testabilidade)
**Veredicto:** aprovado / bloqueado

## Achados

| # | Onde | Crítico | Achado | Severidade |
|---|---|---|---|---|
| 1 | EXP-03 | Joana | Critério de aceite não é verificável ("rápido o bastante") | 🔴 |

## O que foi examinado

- Objetivo e não-objetivos · Requisitos EXP-01..EXP-08 · Plano (7 tarefas) · Matriz de testes

```kairos-critica
{
  "spec": "SPEC-NNN",
  "veredicto": "aprovado | bloqueado",
  "achados": 0,
  "criticado_por": ["Joana", "Ricardo"],
  "examinado": ["objetivo", "EXP-01..EXP-08", "plano de implementação", "matriz de testes"]
}
```
```

O bloco é o contrato lido pelo `ciclo.py` — **três regras verificadas por código**
(`contrato.py`), as duas primeiras iguais às dos outros relatórios e a terceira só
daqui:

1. **Coerência** — `bloqueado` exige `achados ≥ 1`; qualquer outro veredicto exige 0.
2. **Prova de cobertura** — `achados: 0` exige `examinado` não-vazio.
3. **Independência** — ao menos **2 críticos distintos** em `criticado_por`. Um só é
   recusado pelo parser, não pelo bom senso.

Achado 🔴 volta para a SPEC (`registrar com_achados`); corrigido, a crítica **reabre**,
igual ao arco de validação. Achado que você discorda: corrija ou **escreva na SPEC por
que não** — deixar sem resposta não é opção.
