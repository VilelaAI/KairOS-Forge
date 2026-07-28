# ADR-0014 — Squads de apoio: Engenharia de Requisitos e Gestão de Projetos & Entregas

**Status:** Aceito
**Data:** 2026-07-25

## Contexto

Pedido direto do usuário: dois squads novos — um para **engenharia de requisitos** e outro para **gestão de projetos e gestão de entregas**. As lacunas são reais no catálogo atual:

1. **Requisitos.** O `/especificar` produz SPECs rastreáveis e a Camila (PM) decide escopo/MVP, mas ninguém é dono das disciplinas de engenharia de requisitos em si: **elicitação** (escavar a necessidade real por trás do pedido — hoje o arquiteto interroga, mas sem técnica dedicada), **verificabilidade** (transformar desejo em critério de aceite testável, caçar ambiguidade) e **requisitos não-funcionais/consistência** (NFRs esquecidos, conflitos entre requisitos). O apoio-marcos-specs estrutura a *narrativa* da spec; o conteúdo dos requisitos ficava sem especialista.
2. **Gestão.** Laura coordena a execução técnica (tasks, teammates, DoD) e o quadro vivo (ADR-0013) mostra progresso, mas ninguém é dono da camada de gestão de projeto: **planejamento por marcos** com estimativas e caminho crítico, **gestão contínua de riscos e dependências** (RAID) e **gestão de entregas** (status honesto para stakeholder, follow-ups com dono, comunicação de atraso). O apoio-hugo prioriza por valor e a apoio-sofia cuida do lançamento — o meio (planejar → acompanhar → entregar) ficava descoberto.

## Decisão

A partir da **v0.11.0**, dois squads de apoio novos (tipo `apoio`: **nunca implementam código**, produzem artefatos textuais, máximo 1 squad de apoio ativo por sessão). A fábrica passa de 52 para **58 agentes** (31 core + **27 apoio em 9 squads**), em **18 times**.

### Squad `apoio-requisitos` — Engenharia de Requisitos

| Agente | Papel | Especialidade |
|---|---|---|
| 🎤 **Joana** (`apoio-joana-elicitacao`) | Analista de Elicitação | 5 Porquês, Jobs-to-be-Done, entrevista de descoberta, separar necessidade de solução, mapa de stakeholders |
| ✔️ **Caio** (`apoio-caio-aceite`) | Engenheiro de Critérios de Aceite | WHEN/THEN/SHALL (o formato da SPEC do forge), caça à ambiguidade ("rápido"/"fácil"/"seguro" viram números), INVEST, cenários de erro obrigatórios |
| 📏 **Norma** (`apoio-norma-nfr`) | Engenheira de Requisitos Não-Funcionais | Checklist NFR (desempenho, segurança, usabilidade, confiabilidade, observabilidade, custo), detecção de conflito entre requisitos, completude da SPEC |

**Complementa:** Camila (PM decide escopo e valor; o squad transforma necessidade em requisito verificável), apoio-marcos-specs (ele estrutura a narrativa; o squad produz o conteúdo dos requisitos) e o `/especificar` (o squad alimenta a interrogação do arquiteto — as trilhas do ADR-0013 são o caso pré-embalado; o squad cobre o caso aberto).

### Squad `apoio-gestao` — Gestão de Projetos & Entregas

| Agente | Papel | Especialidade |
|---|---|---|
| 🗓️ **Iara** (`apoio-iara-planejamento`) | Planejadora de Projeto | Marcos verificáveis (entregável + critério, não data solta), estimativa por faixa com buffer explícito, dependências e caminho crítico, risco-primeiro no sequenciamento |
| ⚠️ **Breno** (`apoio-breno-riscos`) | Gestor de Riscos | Registro RAID vivo (Riscos, Assunções, Issues, Dependências), probabilidade × impacto com dono e gatilho, dependências externas com data |
| 📦 **Talita** (`apoio-talita-entregas`) | Gestora de Entregas | Status report a partir de evidência (Status/Verificação da SPEC, validações, quadro vivo — nunca "90% pronto" sem gate), follow-ups com dono e data, comunicação de atraso cedo e com opções |

**Complementa:** Laura (ela coordena a execução técnica; o squad produz os artefatos de gestão por cima) e Camila. O quadro vivo (ADR-0013) e a régua de rastreabilidade (ADR-0012) são as **fontes de evidência** da Talita — status nunca vem de otimismo.

### Fronteiras (para não duplicar)

- **Joana × Camila:** Camila decide *o que entra* (escopo, MVP, métrica de sucesso); Joana escava *o que o pedido significa* (necessidade real, stakeholders). Elicitação alimenta decisão, não a substitui.
- **Caio × Patrícia:** Patrícia valida critérios *na entrega* (QA); Caio escreve critérios verificáveis *antes*, na SPEC. Mesma régua, pontas opostas.
- **Norma × Helena/Vinícius/Ada:** os especialistas core são donos dos *temas* (segurança, performance, acessibilidade); Norma garante que os temas *viraram requisitos com número e gate* na SPEC — e chama o core pelo nome quando o tema aparece.
- **Iara × Laura:** Laura decompõe e coordena *execução* (tasks, teammates, checkpoints); Iara planeja *o projeto* (marcos, estimativas, caminho crítico) — o plano da Iara é insumo do mobilizar, não concorrente.
- **Breno × Álvaro (apoio-revisao-arquitetural):** Álvaro faz pre-mortem/red team *pontual de uma decisão*; Breno mantém a *gestão contínua* de riscos do projeto (RAID vivo, gatilhos, donos).
- **Breno × Sérgio (SRE):** Sérgio responde a *incidente em produção*; Breno gere *risco de projeto/entrega* antes de virar incidente.
- **Talita × Sofia (apoio-valor):** Sofia cuida do *lançamento* (release notes, anúncio, go-to-market); Talita gere a *entrega até estar pronta* (status, follow-ups, atraso).

### Colisões de nome

Nenhuma: Joana, Caio, Norma, Iara, Breno e Talita são primeiros nomes inéditos no catálogo — os três pares existentes (Marcos, Helena, Elisa) continuam sendo os únicos.

## Versão

Agentes novos → bump **minor**: 0.10.2 → **0.11.0**. O roadmap aspiracional da v0.11 (`/migrar`, modo RFC, Mermaid, debate) desloca para o minor seguinte — precedência dos ADRs 0007/0011/0012.

## Consequências

Boas:

- O ciclo ganha as duas pontas que faltavam: requisito bem-formado *antes* do `/especificar` fechar, e gestão de projeto *por cima* da execução da Laura — sem inflar o core.
- Os artefatos dos squads (mapa de stakeholders, matriz de aceite, RAID, status report) alimentam SPECs, `/analisar-ameacas` e o grafo de conhecimento.
- Status de entrega herda a cultura de evidência da fábrica (verificado:/quadro/gates) em vez de criar uma paralela de gerência.

Custos:

- 6 personas a mais para conhecer. Mitigado: Laura roteia por `sinais_ativacao`; 1 squad de apoio por sessão continua valendo.
- Risco de sobreposição percebida com Camila/Laura/Hugo/Sofia/Álvaro. Mitigado: fronteiras explícitas acima, repetidas nos prompts dos agentes.

## Alternativas consideradas

1. **Ampliar Camila e Laura para cobrir os temas.** Rejeitado: acumularia papéis e esconderia as fronteiras — mesmo racional dos ADRs 0007/0008 (especialista com dono explícito).
2. **Um squad só de "requisitos e gestão".** Rejeitado: disciplinas diferentes com consumidores diferentes (requisitos alimenta `/especificar`; gestão acompanha `/mobilizar`/entrega). Squads têm foco único por design (ADR-0003).
3. **Agentes core em vez de apoio.** Rejeitado: as duas disciplinas produzem artefatos textuais e nunca código — a definição exata de squad de apoio (ADR-0003).
4. **Skill nova de gestão.** Rejeitado: gestão não é um fluxo com começo e fim — é papel contínuo; persona serve melhor que skill.
