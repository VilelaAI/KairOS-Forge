# Lacunas e alavancagem — auditar

Material de apoio da skill `auditar`. Leia ao montar o top 3: follow-ups típicos por dimensão, ordem obrigatória em Autonomia e critério de ranqueamento.

## Lacunas de Estrutura: follow-ups típicos

Se a dimensão Estrutura ficar baixa, as ações naturais costumam ser:

- Sem mapa arquitetural ou acoplamento alto → rodar `/kairos-forge:mapear-arquitetura`.
- Sem modelo de ameaças em área sensível → rodar `/kairos-forge:analisar-ameacas`.
- Sem grafo de conhecimento, grafo quebrando `validar` ou parado > 30 dias → rodar `/kairos-forge:mapear-conhecimento` (construir ou atualizar).
- Sem CODEOWNERS → abrir tarefa para Rafael/Diego definirem fronteiras de propriedade.
- Hotspots órfãos → registrar em `decisoes/estado-operacional.md` e atribuir.

## Lacunas de Autonomia: follow-ups típicos

A ordem importa — instrumentar antes de conter, conter antes de disparar. Recomendar gatilho
por evento a um projeto sem guardrail determinístico é recomendar pipeline sem supervisão:

1. Sem telemetria → instalar os hooks do plugin (ou rodar `execucao.py` via CI). Sem isso, as outras lacunas desta dimensão nem são mensuráveis.
2. Autonomia baixa com muitas intervenções → o ciclo está sendo conduzido à mão; rodar `/kairos-forge:entregar` em vez de encadear skills manualmente.
3. Gates verdes de primeira abaixo de 70% → problema de **contexto**, não de modelo: SPEC vaga, `contextos/testes.md` desatualizado ou ausência de trilha. Vale um `/kairos-forge:evoluir` focado nisso.
4. Produção escrita sem gate → lacuna de Guardrails antes de Autonomia; ativar `guardrail.py` e exigir gate na SPEC.
5. Tudo verde e ainda sem gatilho por evento → copiar `templates/ci/` para o projeto (ADR-0026).

## Como ranquear lacunas por alavancagem

Não é por dimensão mais baixa. É por:

1. **Multiplicador.** Lacuna que destrava muitas outras (ex.: sem CLAUDE.md, todo o resto fica fraco).
2. **Custo de adiar.** Lacuna que vai doer mais a cada semana sem (ex.: sem testes, dívida cresce exponencial).
3. **Esforço para fechar.** Empate entre duas lacunas? Recomende a de menor esforço primeiro.
