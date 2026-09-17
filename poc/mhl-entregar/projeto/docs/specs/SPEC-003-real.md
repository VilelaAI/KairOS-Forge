# SPEC-003 — Saudação real

**Origem:** POC do MHL dirigindo o arco (ADR-0040, `rodar explorar`)

## Contexto e problema

Projeto de brinquedo para provar o runner externo. Uma função, um teste, um arco inteiro.

## Objetivo

Uma função `saudar(nome)` que devolve a saudação em PT-BR e recusa nome vazio.

## Não-objetivos

Internacionalização, UI, persistência.

## Invariantes

Função pura; nenhuma entrada externa.

## Requisitos rastreáveis

| ID | Requisito | Prioridade | Critério de aceite | Status | Verificação |
|---|---|---|---|---|---|
| SAU-01 | Como usuário, quero ser saudado pelo nome, para confirmar que o sistema me reconhece. | P1 | WHEN `saudar("Ana")` THEN retorna exatamente `"Bom dia, Ana!"`; WHEN nome vazio ou só espaços THEN levanta `ValueError`. | Concluído | verificado: python3 -m unittest tests.test_saudacao (17/09) |

## Plano de implementação

| Tarefa | Agente | Requisito(s) | Arquivos/áreas | Depende de | Done when | Gate |
|---|---|---|---|---|---|---|
| T1 | [Lucas] | SAU-01 | `saudacao.py`, `tests/` | - | **Fatia fim a fim:** função + teste do caminho feliz e do erro. | `python3 -m unittest tests.test_saudacao` |

## Matriz de testes

| Requisito | Tipo | Responsável | Comando/gate | Evidência esperada |
|---|---|---|---|---|
| SAU-01 | unit | [Ricardo] | `python3 -m unittest tests.test_saudacao` | Caminho feliz + 1 erro cobertos; o teste novo falha sem a mudança. |

## Riscos e mitigações

Nenhum.

## Perguntas abertas

Nenhuma.

## Validação

`/kairos-forge:validar SPEC-003`

## Próximo passo

`/kairos-forge:mobilizar SPEC-003`
