# SPEC-054 — Mutante por critério de aceite

**Origem:** conversa · **Faixa:** 1

## Requisitos rastreáveis

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| CRI-01 | Ler o comando de cada critério da Matriz de testes | P1 | WHEN a matriz nomeia as colunas em qualquer ordem THEN o comando entre crases é o do requisito; manual e texto livre não rodam | Concluído | verificado: `cd scripts && python3 -m unittest -q tests.test_criterios.Celula tests.test_criterios.Matriz tests.test_criterios.CriteriosDaSpec` (05/11) |
| CRI-02 | Julgar critério por critério com rodízio e segunda passada | P1 | WHEN um critério passa com todos os mutantes THEN sai fachada; WHEN percebe um THEN sai descarta com o mutante | Concluído | verificado: `cd scripts && python3 -m unittest -q tests.test_criterios.Motor` (05/11) |
| CRI-03 | O caminho inteiro num git de verdade | P1 | WHEN a SPEC tem os seis casos THEN cada um sai com o seu veredicto e o original fica intocado | Concluído | verificado: `cd scripts && python3 -m unittest -q tests.test_criterios.CriteriosNoDiff` (05/11) |
| CRI-04 | Linha de comando e impressão | P2 | WHEN há fachada THEN sai 1 e imprime o mutante sem critério | Concluído | verificado: `cd scripts && python3 -m unittest -q tests.test_criterios.Cli` (05/11) |
| CRI-05 | A mutação de antes segue igual | P1 | WHEN a suíte confere a fronteira THEN mata todos os mutantes, como antes | Concluído | verificado: `cd scripts && python3 -m unittest -q tests.test_qualidade.MutacaoNoDiff` (05/11) |
