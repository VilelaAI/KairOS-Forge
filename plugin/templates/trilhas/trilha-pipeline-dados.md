# Trilha — Pipeline de dados

**Tema:** ingestão, transformação em zonas com contrato, qualidade como gate, linhagem e reprocessamento seguro.
**Feature sensível:** SIM quando o pipeline carrega dado pessoal, financeiro ou de saúde — nesses casos, rode `/kairos-forge:analisar-ameacas` antes de fechar a SPEC.

## O padrão, em uma frase

O dado atravessa **zonas com contrato entre elas** — bruto imutável → limpo e validado → modelado para consumo. Cada passagem é um **gate**, não um relatório: dado que não passa não avança.

Os nomes variam por projeto (bronze/silver/gold, raw/staging/curated, landing/trusted/refined). A trilha é sobre o padrão; adote o vocabulário que o projeto já usa.

## Requisitos típicos (rascunho — renumere e adapte na SPEC)

| ID | Requisito | Prioridade | Critério de aceite |
|---|---|---|---|
| PIP-01 | Como engenheiro, quero a zona bruta imutável, para poder reprocessar sem depender da origem. | P1 | WHEN ingestão roda THEN o dado bruto SHALL ser gravado sem transformação e nunca sobrescrito; reprocessar a partir dele SHALL ser possível. |
| PIP-02 | Como consumidor, quero regras de qualidade como gate, para não receber dado inválido. | P1 | WHEN uma regra crítica falha THEN o lote SHALL parar antes da zona seguinte; o relatório sozinho NÃO satisfaz o critério. |
| PIP-03 | Como analista, quero linha ruim em quarentena, não descartada, para investigar o que foi rejeitado. | P1 | WHEN linha viola regra THEN SHALL ir para quarentena com o motivo; contagem entrada = aprovadas + quarentenadas, sem sumiço silencioso. |
| PIP-04 | Como engenheiro, quero re-execução idempotente, para que retry não duplique dado. | P1 | WHEN a mesma janela roda duas vezes THEN o resultado SHALL ser idêntico (chave de deduplicação ou escrita por partição declarada). |
| PIP-05 | Como consumidor, quero contrato de schema explícito entre as zonas, para não quebrar em silêncio. | P1 | WHEN a origem muda o schema THEN o pipeline SHALL falhar alto (ou versionar), nunca gravar coluna faltante como nulo em silêncio. |
| PIP-06 | Como auditor, quero linhagem do campo até a origem, para responder "de onde veio esse número". | P2 | WHEN um campo derivado é questionado THEN SHALL existir rastro da fórmula e da fonte. |
| PIP-07 | Como operador, quero saber que o dado chegou e está fresco, para confiar no painel. | P2 | WHEN a carga atrasa além do limite THEN SHALL haver alerta; frescor SHALL ser visível a quem consome. |

## Tarefas e agentes sugeridos

| Tarefa | Agente | Gate sugerido |
|---|---|---|
| Desenho das zonas, contratos e modelo de consumo | Fernanda | contrato revisado antes de codar |
| Ingestão e escrita da zona bruta | Juliana | teste de idempotência: rodar 2× dá o mesmo resultado |
| Transformações entre zonas | Juliana (+ Carlos se SQL pesado) | teste por regra de negócio, não só "rodou" |
| Regras de qualidade e quarentena | Ricardo + Juliana | lote com linha ruim SHALL parar/quarentenar no teste |
| Modelagem e performance de consulta | Carlos | EXPLAIN nas queries do consumidor |
| Contratos de evento e entrega (se streaming) | Murilo | teste de reprocesso e de fora de ordem |
| Camada semântica / métricas | Bento | métrica bate com a fonte num caso conhecido |
| Orquestração, agendamento e alerta de atraso | Marcos (+ Renata para instrumentação) | falha e atraso disparam alerta no teste |

## Riscos típicos (insumo pro /analisar-ameacas)

- **Sumiço silencioso:** linha inválida descartada sem contagem — o painel fica bonito e errado.
- **Qualidade como relatório:** a regra roda, grava a métrica e deixa o dado passar mesmo assim.
- **Reprocessamento duplicando:** retry sem chave de deduplicação, com dado contado duas vezes.
- **Schema drift:** origem adiciona/renomeia coluna e o pipeline grava nulo sem falhar.
- **Dado pessoal atravessando zonas:** mascarar só na camada de consumo deixa o bruto exposto a quem tem acesso ao armazenamento.
- **Backfill destrutivo:** recarga histórica que sobrescreve o corrigido à mão.
- **Fuso e janela:** agregação diária em fuso diferente do da origem, com dia parcial contado como cheio.

## Perguntas que o arquiteto DEVE fazer antes de fechar a SPEC

1. **Cadência e volume:** lote diário, micro-lote ou streaming? Quantas linhas por janela? (Muda tudo, inclusive quem entra.)
2. **O que fazer com linha ruim:** parar o lote, quarentenar ou seguir? Quem decide o limiar?
3. **Reprocessar é possível?** Se a origem não guarda histórico, a zona bruta é a única cópia — isso muda a política de retenção.
4. **Quem consome e como:** ad-hoc, painel, modelo, API? Define a modelagem da última zona.
5. **Dado pessoal ou regulado?** Se sim, em que zona mascara — e por que não antes.
6. **Chave de deduplicação:** existe identificador natural estável, ou precisa ser derivado?
7. **Qual é a definição de "atrasado"?** Sem isso não há alerta de frescor, só reclamação de usuário.

## Fora do escopo desta trilha

Escolha de stack (Spark, dbt, Airflow, warehouse) — decisão de arquitetura à parte, via ADR do projeto. Treino e serving de modelo (é do time de Ciência de Dados). Migração de pipeline legado — use `/kairos-forge:migrar`, que tem o padrão de estrangulamento e o dono certo (Ivan).
