# Modo RFC — decisões arquiteturalmente significativas (ADR-0018)

Referência do passo 5.1 de `/kairos-forge:especificar`. Leia quando a mudança for
Complexa, cruzar 2+ times, tiver reversibilidade baixa ou o usuário invocar
`especificar rfc` — o RFC vem ANTES da SPEC.

## 5.1. Modo RFC — decisões arquiteturalmente significativas (ADR-0018)

Quando a mudança for **Complexa**, cruzar **2+ times**, ter **reversibilidade baixa** (migração, troca de tecnologia, contrato público) — ou o usuário invocar `especificar rfc` — as abordagens do passo 5 não morrem no chat: viram RFC em `docs/rfcs/RFC-<NNN>-<slug>.md` ANTES da SPEC:

```markdown
# RFC-NNN — <decisão em uma frase>

- **Status:** rascunho | em discussão | aceito | recusado
- **Drivers:** o que pesa na decisão (custo, prazo, reversibilidade, time)

## Contexto
## Decisão proposta
## Diagrama

(bloco Mermaid do fluxo proposto — se o grafo existir, parta de
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/grafo.py mermaid "<entidade>" --saltos 2`)

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|

## Consequências

Positivas e negativas — inclusive o que fica mais difícil.
```

Regras do modo RFC:

- **Rafael revisa todo RFC.** Decisão de tecnologia/padrão é o território dele.
- **RFC "em discussão" contestado** → `/kairos-forge:rodar debate` estrutura o confronto (Álvaro/Lúcia/Félix) e a síntese volta pro RFC.
- **RFC aceito** → vira ADR curto em `decisoes/` (o porquê, permanente) e a SPEC referencia ambos (`RFC-NNN` no Contexto). SPEC continua sendo o contrato do *o quê* — o RFC guarda o *porquê*.
- **RFC recusado fica no repo.** Alternativa descartada com o motivo registrado é o que impede a fábrica de redescobri-la daqui a 6 meses.
