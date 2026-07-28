# ADR-0018 — Skill `migrar`, modo RFC, diagramas Mermaid e modo debate

- **Status:** aceito
- **Data:** 2026-07-28
- **Versão:** v0.14.0

## Contexto

O roadmap do v0.14 prometia quatro capacidades que fecham lacunas do ciclo:

1. Modernização de legado ganhou dono no v0.13 (Ivan, ADR-0017), mas não
   ganhou **processo**. O `/mapear-arquitetura` entrega o plano de
   decomposição e para ali — não há skill que transforme o plano em programa
   incremental com rollback por fatia.
2. Decisões arquiteturalmente significativas nascem dentro da SPEC e morrem
   lá: as alternativas descartadas e os porquês não ficam registrados num
   formato discutível antes do compromisso (o ADR chega *depois* da decisão).
3. SPECs e ADRs descrevem fluxo entre componentes só em prosa. O repo já tem
   grafo de conhecimento (ADR-0009) mas nenhuma ponte visual — e todos os
   CLIs-alvo renderizam Mermaid nativamente.
4. O squad apoio-revisao-arquitetural (Álvaro, Lúcia, Félix) opina em
   paralelo, cada um no seu framework, mas sem estrutura de **confronto**:
   pre-mortem, red team e inversão não se respondem, e a síntese fica por
   conta do usuário. O modo debate estava planejado desde o ADR-0002 como a
   versão simplificada do `--workflow debate` do kairos-ai.

## Decisão

Quatro entregas, todas dentro do contrato "plugin, não runtime" (ADR-0001):

### 1. Skill `migrar` (13ª skill, dona: Ivan)

`/kairos-forge:migrar` conduz modernização por **estrangulamento** (strangler
fig): inventário (reusa `/mapear-arquitetura`), fatiamento por capacidade,
testes de caracterização ANTES de tocar o legado (Ricardo), camada
anti-corrupção e rota de corte com rollback (Diego/Thiago), uma SPEC por
fatia via `/especificar`, medição com a régua do ciclo de catraca (ADR-0012)
e decisão explícita manter-ou-reverter. Descomissionamento é etapa
obrigatória — "estrangulado" sem remoção é dois sistemas para sempre.

### 2. Modo RFC no `/especificar`

Quando a mudança é **Complexa**, cruza 2+ times ou tem reversibilidade baixa
(ou o usuário pede `especificar rfc`), o arquiteto produz
`docs/rfcs/RFC-NNN-<slug>.md` antes da SPEC: decisão proposta, alternativas
consideradas com o porquê do descarte, drivers, consequências e diagrama.
RFC em discussão pode ser levado ao modo debate; RFC aceito vira ADR curto
em `decisoes/` e a SPEC referencia os dois. RFC registra o *porquê* antes do
compromisso; SPEC continua sendo o contrato do *o quê*.

### 3. Diagramas Mermaid como cidadão do fluxo

- `scripts/grafo.py` ganha o subcomando `mermaid` — exporta o subgrafo de
  uma entidade (mesmo BFS do `subgrafo`) como bloco `flowchart LR` pronto
  para colar em SPEC/RFC/ADR, com predicados nas arestas.
- `/especificar` (SPECs Médias+ com fluxo entre componentes), o modo RFC e o
  `/migrar` (antes/depois de cada fatia) passam a incluir bloco Mermaid.
- Regra: diagrama **deriva** do texto/grafo, nunca o substitui — quem diverge
  do diagrama é o diagrama.

### 4. Modo debate no `/rodar`

`/kairos-forge:rodar debate <decisão>` estrutura o confronto:
enquadramento pela Laura (decisão como pergunta fechada + opções), rodada de
ataque (Álvaro pre-mortem, Lúcia red team com fatos/princípios, Félix
inversão de Munger defendendo a alternativa), uma réplica só com argumento
novo, e síntese da Laura com recomendação, **dissenso registrado** e
condições de reversão. Máximo 2 rodadas; artefato sai em
`docs/decisoes/DEBATE-<slug>.md` ou no RFC de origem. Formato deliberadamente
mais simples que o `--workflow debate` do kairos-ai (sem advisor regulatório,
sem assertions) — confronto estruturado, não tribunal.

## Consequências

- 12 → **13 skills**. Nenhum agente novo — as quatro entregas usam personas
  existentes (Ivan, Rafael, Laura, Álvaro, Lúcia, Félix, Ricardo).
- `migrar` entra "fora do fluxo, sob demanda" na ordem natural das skills,
  ao lado de `otimizar` — ambas são ciclos com métrica e reversão.
- O modo debate dá ao squad de revisão arquitetural o mecanismo de confronto
  que faltava; RFC dá à decisão um lugar antes do compromisso.
- Fica de fora (registrado para o futuro): renderização de Mermaid a partir
  do grafo inteiro (só subgrafo com semente — grafo completo vira spaghetti),
  e debate com mais de 3 posições.
