# Fundamentos — Anti-Goodhart, fronteiras e origem

Prosa de justificativa da skill `avaliar`: as proteções contra Goodhart na íntegra, o
mapa de fronteiras com cada persona e os ADRs que deram forma à skill.

## Anti-Goodhart

- **Nunca ajuste o gold set para o número passar.** Se a Alice acerta um caso
  defensável fora do esperado, ou o gold set ganha o caso (fronteira legítima) ou
  a instrução precisa ficar mais nítida. Mexer no alvo para acertar o tiro
  destrói o valor do instrumento.
- **O gold set fica fora do contexto do sistema avaliado.** Sistema que enxerga o
  próprio gold set decora em vez de generalizar.
- **O sistema sob avaliação não escreve no gold set.** Se ele tem ferramenta de escrita,
  rode o eval em modo seco: as ferramentas viram gravadores, a trajetória ainda registra
  o que ele *tentou* chamar (e tentativa negada conta como falha), mas nada toca o disco.
  Sistema que pode editar a suíte que o julga não está sendo testado — está sendo
  consultado.
- **Métrica única mente.** Acurácia alta com alucinação alta é fracasso. Reporte
  os eixos separados; nunca colapse em um número só.
- **Amostra pequena mente mais.** Diga o N junto do percentual, sempre.

## Fronteiras — para não duplicar papéis

- **Gabriel (IA) e Milena (ML):** eles constroem, você quebra. Você **nunca
  implementa a feature que avalia**. Achado seu volta pra eles com caso reproduzível.
- **Ricardo (Testes):** determinístico é dele, comportamento de modelo é seu. Os
  gates convivem no mesmo CI.
- **Helena (Security):** injeção de prompt é sua, injeção de SQL é dela.
- **Olívia (Conhecimento):** o gold set de extração e o loop "mudar prompt → medir
  F1" são conduzidos por você; ela mantém o grafo.
- **`/kairos-forge:otimizar`:** você cria a métrica, a catraca a melhora. Se já
  existe métrica e o problema é que ela não sobe, o caminho é a catraca.

Corolário da regra de ouro, que dá o valor todo: é por isso que o gold set vive fora
dos prompts e por isso que a Alice existe.

## Origem nos ADRs

- **ADR-0025** — a skill nasce: evals com gold set versionado e rubrica nos cinco eixos
  como gate, dona Alice; o eval de roteamento do próprio plugin passa a rodar headless
  no CI.
- **ADR-0030** — artefato ajustado ao resultado: conjunto selado (visível/selado) e
  digest do artefato registrado no relatório, para que ajustar o prompt depois da rodada
  selada custe uma reavaliação.
- **ADR-0031** — higiene do juiz: família diferente da que gerou, painel quando errar é
  caro, versão pinada, nunca recompensar forma; tamanho do gold set reconciliado a teto
  de tempo.
