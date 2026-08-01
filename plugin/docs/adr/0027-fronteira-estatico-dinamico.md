# ADR-0027 — Fronteira estático/dinâmico e orçamento de contexto

- **Status:** aceito
- **Data:** 2026-08-01
- **Versão:** v0.19.0

## Contexto

O whitepaper Day-1 dedica a seção de engenharia de contexto à separação entre o que o
agente carrega sempre e o que ele carrega sob demanda:

> *"Static context is always loaded... **Static context is expensive because every token is
> present in every interaction, regardless of relevance.** Dynamic context is loaded on
> demand... The design decision of what belongs in static context versus dynamic context is
> a genuine engineering trade-off. Too much static context wastes tokens and dilutes
> signals. Too little means the agent forgets critical rules. **The best systems treat this
> boundary as a first-class architectural decision, reviewed and versioned like any other
> configuration.**"*

E fecha ligando isso a dinheiro: *"in the token economy, context engineering is not just a
technical skill — it is a financial strategy."*

O kairos-forge acerta o padrão — skills carregam no match, `references/` carrega mais fundo
ainda — mas acertava **por bom gosto, não por decisão registrada**. Não havia ADR, não havia
orçamento, e a única regra escrita ("skills ≤ 500 linhas no SKILL.md", regra 3 do CLAUDE.md)
era convenção verificada por revisor humano, quando lembrava.

A medição do estado atual mostrou por que valia a pena travar em vez de reescrever:

| Camada | Tamanho | Quando custa |
|---|---|---|
| Banner `SessionStart` | 347 chars | toda sessão |
| Rule Cursor (`alwaysApply`) | 1.474 chars | toda interação no Cursor |
| `templates/CLAUDE.md.template` | 5.777 chars | toda sessão no projeto do usuário |
| **Total estático** | **~7.600 chars (~1,9k tokens)** | sempre |
| 17 SKILL.md somados | ~161.000 chars | **só o que casa com a tarefa** |

A proporção é boa: o custo permanente é pequeno e a capacidade é enorme e sob demanda. O
risco não era o estado — era a **deriva**, que acontece linha a linha e sem ninguém notar.

## Decisão

Declarar a fronteira e verificá-la no CI.

### O que é estático (pago sempre) e por quê

| Item | Justificativa para estar sempre presente |
|---|---|
| Banner `SessionStart` | Diz que a fábrica existe e como invocá-la. Sem ele, o usuário não descobre as skills |
| Rule Cursor `alwaysApply` | Papel do banner num editor sem hooks; carrega também a resolução de `${CLAUDE_PLUGIN_ROOT}` |
| `CLAUDE.md` do projeto | Stack, convenções e regras duras do projeto — é o "novo membro do time precisa saber isto" |

### O que é dinâmico (pago quando casa)

| Item | Gatilho |
|---|---|
| `SKILL.md` | Match da tarefa com a `description` da skill |
| `references/` da skill | Chamada explícita dentro da skill |
| Definição de agente | Invocação daquela persona |
| Subgrafo do conhecimento | Consulta `grafo.py subgrafo` |
| Trilha por tema | Reconhecimento do tema no `/especificar` |
| Squad de apoio | Um por vez, sob demanda (`/rodar apoio-<x>`) |

### Orçamento verificado no `release.py check`

```python
ORCAMENTO_ESTATICO = {
    "banner SessionStart": 600,
    "rule Cursor (alwaysApply)": 2500,
    "templates/CLAUDE.md.template": 8000,
}
LIMITE_LINHAS_SKILL = 500
```

Tetos com folga sobre o estado atual: o objetivo não é apertar, é **impedir a deriva**.
Estourar o teto não é bug a contornar — é sinal de que aquele conteúdo pertence ao contexto
dinâmico. A mensagem de erro diz isso: *"mova o detalhe para contexto dinâmico (skill ou
references/)"*.

A regra 3 do CLAUDE.md (skills ≤ 500 linhas) deixa de ser convenção e vira check. Era a
regra mais fácil de violar sem ninguém perceber, porque skills crescem por adição
incremental e cada adição parece pequena.

## Consequências

**Positivas**

- A fronteira vira decisão versionada, revisada em PR como qualquer configuração — que é
  literalmente o que o paper pede.
- A deriva silenciosa fica impossível: quem estourar o teto descobre no CI, não seis meses
  depois quando a conta subiu.
- O check dá um lugar objetivo para a pergunta "isso deveria estar sempre carregado?", que
  antes dependia do gosto de quem revisava.

**Negativas e limites, declarados**

- **Chars não são tokens.** A proporção varia com o conteúdo (PT-BR acentuado gasta mais
  por char que inglês). Medir chars é aproximação; a alternativa seria depender de um
  tokenizador, e o repositório é deliberadamente só-stdlib.
- **O orçamento não cobre tudo que é estático de fato.** O system prompt do CLI, as
  descriptions das 17 skills carregadas como metadados na largada e as dos 71 agentes também
  são pagas sempre e não entram no check. As descriptions em particular são um custo real e
  crescente — cada skill nova soma. Fica registrado como limitação conhecida.
- **Teto arbitrário.** 600/2500/8000 são folga sobre o atual, não derivados de análise de
  custo. Servem como catraca, não como ótimo.
- **17 skills × ~9,5k chars é bastante material** para manter em disclosure progressivo.
  Só uma skill (`mapear-conhecimento`) usa `references/` hoje; conforme as skills crescerem,
  o limite de 500 linhas vai forçar a extração — que é o comportamento desejado.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Não registrar e confiar no bom gosto | Era o estado até a v0.19. Bom gosto não sobrevive a dez contribuidores e vinte PRs |
| Orçamento em tokens com tokenizador real | Traria dependência externa ao repositório, que é só-stdlib por desenho. Chars com folga resolvem o problema real, que é deriva |
| Apertar os tetos até o mínimo atual | Transformaria toda edição legítima em falha de CI. Catraca serve para impedir crescimento silencioso, não para congelar |
| Mover o `CLAUDE.md.template` para carregamento dinâmico | O `CLAUDE.md` é o contexto que o paper mais defende como estático: é exatamente o "o que um novo membro do time precisaria saber" |
