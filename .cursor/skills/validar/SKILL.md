---
name: validar
description: Valida uma implementação contra uma SPEC rastreável antes da revisão pré-PR. Use depois de /kairos-forge:mobilizar ou /kairos-forge:rodar e antes de /kairos-forge:revisar. Compara requisitos, tarefas, critérios de aceite, gates de teste e evidências. Produz relatório em docs/specs/validacoes/. Não é code review — segurança, performance e qualidade do diff são o revisar; aqui a pergunta é só "cumpre o contrato da SPEC?".
---

# Validar — aceite contra SPEC

Você está sendo invocado para verificar se o trabalho implementado cumpre o contrato da SPEC.

## Regra de ouro

Não implemente correções nesta skill. Você pode ler arquivos, analisar diff, rodar comandos de teste/lint/build e salvar relatório. Se encontrar falha, registre objetivamente e recomende qual agente deve corrigir.

## Quando usar

- Depois de implementar uma SPEC com `/kairos-forge:mobilizar`.
- Depois de executar uma feature por `/kairos-forge:rodar`.
- Antes de `/kairos-forge:revisar`, para separar aceite funcional de code review.
- Quando o usuário perguntar "isso cumpre a spec?".

## Quando NÃO usar

- **Code review do diff** — segurança, performance, legibilidade →
  `/kairos-forge:revisar`. Aqui a pergunta é só *"cumpre o contrato da SPEC?"*.
- **Sem SPEC.** Sem contrato não há aceite. **Não infira requisitos do código**: é
  exatamente o modo de falha que esta skill existe para impedir — o código vira ao
  mesmo tempo a proposta e o gabarito. Rode `/kairos-forge:especificar` antes.
- **Antes de a implementação existir.** Validar SPEC recém-escrita só produz uma
  matriz de "não implementado".
- **Julgar a SPEC em si** — está boa? cobre o problema? Isso é a crítica adversarial
  dentro do `/kairos-forge:especificar`, com dois críticos que não a escreveram
  (ADR-0033).
- **Medir a fábrica** → `/kairos-forge:auditar`.

## Fluxo

### 1. Localizar a SPEC

Aceite entradas como:

- `/kairos-forge:validar SPEC-001`
- `/kairos-forge:validar docs/specs/SPEC-001-exportar-csv.md`
- `/kairos-forge:validar` com uma única SPEC modificada na branch

Se houver ambiguidade, pergunte qual SPEC validar.

### 2. Ler contrato e contexto

Leia:

- `docs/specs/SPEC-<NNN>-<slug>.md`
- `contextos/testes.md`, se existir
- `decisoes/estado-operacional.md`, se existir
- Diff atual contra a base (`git diff origin/main...HEAD`, ou base equivalente)

Extraia:

- Requisitos rastreáveis e prioridades
- Critérios de aceite
- Tarefas planejadas
- Gates e comandos esperados
- Perguntas abertas

### 3. Validar rastreabilidade

Monte uma matriz:

| Requisito | Prioridade | Evidência no diff | Teste/gate | Status SPEC | Verificação SPEC | Status validação |
|---|---|---|---|---|---|---|
| EXP-01 | P1 | arquivo/linha ou commit | comando rodado | Concluído | `verificado: pnpm test (12/06)` | aprovado/falhou/sem evidência |

Regras:

- P1 sem evidência no diff bloqueia validação.
- P1 sem teste/gate exige justificativa explícita.
- Pergunta aberta não resolvida bloqueia se impactar P1.
- P2 pode virar follow-up se o relatório registrar a decisão.
- P3 não bloqueia, mas deve aparecer como pendência.
- **Status "Concluído" na SPEC sem célula Verificação iniciando com `verificado:` = "sem evidência" automático.** Não importa se o código está no diff: marcar pronto sem prova de execução é o anti-padrão que o ritual existe para impedir. Inspirado no `briefing.md` do Replit-Orchestrator.
- **Status "Em progresso" sem célula Verificação iniciando com `em progresso:` = falha de contrato.** O autor da SPEC deve listar o que ainda falta. Conta 0.5 no percentual da SPEC se o conteúdo for plausível.
- SPECs antigas (anteriores à coluna Verificação) ficam fora dessas duas últimas regras — registrar como "SPEC anterior ao ritual de verificação" no veredicto.

### 3.5. Fundamentar afirmações no grafo (se existir)

Se o projeto tem `.agents/grafo/entidades.jsonl`, use o grafo como base de fatos do avaliador (ADR-0009) — validação deixa de ser "parece certo" e vira checagem de fato:

1. Para cada entidade central da SPEC, serialize o contexto: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/grafo.py subgrafo "<entidade>" --saltos 2`.
2. Cheque as afirmações da SPEC e das células `verificado:` contra as arestas. Afirmação confirmada cita a aresta: `(A) --[predicado]--> (B) [fonte: arquivo]`.
3. Afirmação **contradita** pelo grafo entra nos achados com a evidência específica: "a tripla (X, depende de, Y) não existe no grafo; o que existe é (X, substitui, Z), da fonte W".
4. Afirmação **ausente** do grafo não é aprovada nem rejeitada em silêncio: registre como "sem aresta no grafo" e **escale ao usuário** — pode ser erro da SPEC ou lacuna de cobertura do grafo (nesse caso, recomende `/kairos-forge:mapear-conhecimento atualizar`).
5. Declare no relatório a data da última construção do grafo (de `.agents/grafo/GRAFO.md`) — fundamentação em grafo velho vale menos e o leitor precisa saber.

Sem grafo no projeto, pule esta etapa sem penalizar o veredicto.

### 3.6. Corroborar a evidência contra a trajetória (ADR-0021)

A célula `verificado:` é escrita **pelo mesmo agente que fez o trabalho**. Isso é auto-relato, e o modo de falha mais perigoso de agente não é o erro visível — é a saída fluente que pulou a etapa de verificação e diz que não pulou. Se o projeto tem `.agents/execucoes/`, você não precisa acreditar: dá para conferir.

Para cada requisito com Status **Concluído**, extraia o comando citado na célula `verificado:` e cheque contra a trajetória registrada pelos hooks:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/telemetria.py corroborar "<comando citado no verificado:>"
```

Os quatro veredictos e o que cada um faz com a linha da matriz:

| Veredicto | Significado | Efeito na validação |
|---|---|---|
| `corroborado` | O comando rodou e passou | Evidência confirmada — o mais forte que existe aqui |
| `corroborado_com_falha` | Rodou e **falhou** em todas as execuções registradas | **Bloqueia.** A SPEC afirma verificado sobre um gate vermelho |
| `corroborado_indeterminado` | Rodou, saída não permite afirmar resultado | Vale como "gate executado", mas cite a incerteza na ressalva |
| `nao_corroborado` | Nenhuma execução registrada daquele comando | **Evidência não corroborada** — trata como "sem evidência" para P1 |

Regras:

- **`nao_corroborado` em requisito P1 bloqueia**, exatamente como "sem evidência". A alegação pode até ser verdadeira (rodou em outra máquina, antes dos hooks, no CI), mas então a prova está fora do alcance da validação — e o autor precisa dizer onde. Registre a alegação e o que falta.
- **Você ainda roda os gates do passo 4.** A corroboração olha para trás (o que aconteceu); rodar o gate olha para agora. As duas coisas respondem perguntas diferentes e nenhuma substitui a outra.
- **Trajetória parcial não penaliza retroativamente.** Se o registro começa depois da data citada no `verificado:`, ou se a telemetria foi instalada no meio do trabalho, registre "fora da janela de telemetria" e não bloqueie por isso. Diga a janela coberta no relatório.
- **Sem `.agents/execucoes/` no projeto**, pule esta etapa inteira sem penalizar o veredicto — e recomende instalar a telemetria (ADR-0021), porque sem ela a fábrica não consegue medir a própria autonomia.

### 4. Rodar gates

Rode apenas comandos relevantes e seguros:

- gates declarados na SPEC
- comandos de `contextos/testes.md`
- comandos padrão evidentes do projeto (`npm test`, `npm run lint`, `pytest`, `go test ./...`) quando não houver contexto

Se um comando for destrutivo, exigir segredo, depender de serviço externo ou tiver custo alto, não rode; registre como "não executado" e explique.

### 5. Acionar especialistas conceitualmente

Produza parecer em primeira pessoa, sem criar código:

- **Ricardo** valida cobertura e gates.
- **Patrícia** valida critérios de aceite e regressões.
- **Helena** entra se a SPEC tocar auth, PII, autorização, input externo ou segurança.
- **Carlos** entra se houver migration, SQL, índice, RLS ou dados persistentes.
- **Ada** entra se houver UI acessível.

### 6. Salvar relatório

Salve em:

`docs/specs/validacoes/VALIDACAO-<SPEC-NNN>-YYYY-MM-DD.md`

Formato:

```markdown
# Validação — SPEC-NNN — YYYY-MM-DD

**Veredicto:** aprovado / aprovado com ressalvas / bloqueado
**Base analisada:** <branch/base>
**Gates rodados:** <lista>

## Matriz de rastreabilidade

| Requisito | Prioridade | Evidência | Gate | Corroboração | Status |
|---|---|---|---|---|---|

(Coluna Corroboração: `corroborado` / `não corroborado` / `fora da janela` / `sem telemetria`.)

## Achados bloqueantes

## Ressalvas

## Evidências de teste

## Fundamentação no grafo

(Se `.agents/grafo/` existir: afirmações confirmadas com aresta citada, contradições com a evidência do grafo, e afirmações sem aresta escaladas ao usuário. Data da última construção do grafo.)

## Follow-ups aceitos

## Próximo passo

- Se bloqueado: corrigir com <agente(s)> e rodar `/kairos-forge:validar SPEC-NNN` de novo.
- Se aprovado: rodar `/kairos-forge:revisar`.

```kairos-validacao
{
  "spec": "SPEC-NNN",
  "veredicto": "aprovado | aprovado_com_ressalvas | bloqueado",
  "bloqueios": 0,
  "verificado": ["REQ-01 (npm test -- exportar)", "REQ-02 (gate lint)", "critério de aceite 3"]
}
```
```

### 6.1. O bloco de contrato — por que ele existe (ADR-0032)

O bloco ` ```kairos-validacao ` no fim do relatório é o que o `ciclo.py` lê. Não é
decoração de formato: **é a fronteira entre a sua leitura e a decisão da máquina.**

Três regras, todas verificadas por código (`contrato.py`), não por lembrança:

1. **Fence própria.** Validação usa `kairos-validacao`; revisão usa `kairos-revisao`.
   Nunca a mesma. Os dois relatórios têm a linha `**Veredicto:**` — sem fence
   separada, um seria lido como o outro no dia errado.
2. **Coerência.** `bloqueado` exige `bloqueios ≥ 1`; qualquer outro veredicto exige
   `bloqueios = 0`. Achado bloqueante não vira ressalva por escolha de palavra.
3. **Prova de cobertura.** `bloqueios: 0` **exige** `verificado` não-vazio. "Não achei
   nada" sem dizer onde procurou não é ausência de defeito — é ausência de busca, e as
   duas produzem o mesmo texto tranquilizador. Liste requisito, gate rodado e arquivo
   lido. O guardrail recusa a escrita do relatório se a lista estiver vazia.

E `bloqueios` tem uma segunda função: o `ciclo.py` compara a contagem com a melhor
marca já atingida. **Baixou, a ficha do orçamento volta**; não baixou, queima. Por isso
a contagem precisa ser honesta nos dois sentidos — inflar esconde progresso, esvaziar
compra rodada que você não ganhou.

### 7. Responder ao usuário

Resumo curto:

```markdown
Validação da SPEC-NNN: <veredicto>.

P1: X/Y aprovados.
Gates: A passaram, B falharam, C não rodaram.
Relatório salvo em `docs/specs/validacoes/VALIDACAO-SPEC-NNN-YYYY-MM-DD.md`.

Próximo passo: <corrigir com agente X | rodar /kairos-forge:revisar>.
```

## Veredictos

- **Aprovado**: todos os P1 têm evidência, critérios de aceite cobertos e gates relevantes passaram.
- **Aprovado com ressalvas**: P1 ok, mas há P2/P3 pendentes ou gate não rodado com justificativa aceitável.
- **Bloqueado**: qualquer P1 sem evidência, critério de aceite falhando, gate essencial falhando ou pergunta aberta bloqueante.

## Regras

- **Não confunda validação com revisão.** Validação responde "cumpre a SPEC?". Revisão responde "o código está seguro, testado, performático e pronto para PR?".
- **Não aprove no escuro.** Sem evidência, status é "sem evidência", não "aprovado".
- **Veredicto limpo exige lista do que foi conferido.** O bloco de contrato recusa
  `bloqueios: 0` com `verificado` vazio, e está certo em recusar (ADR-0032).
- **Não esconda P2/P3.** O usuário pode aceitar follow-up, mas precisa aparecer.
- **Marca "Concluído" na SPEC só com `verificado:` na coluna Verificação.** Diff existe + teste passou + arquivo/comando/URL citado no `verificado:`. Confiança em "código está aí" não é evidência.
- **Evidência auto-relatada vale menos que evidência corroborada.** Quando houver trajetória, o `verificado:` é uma alegação a conferir, não um fato a aceitar. Alegação sem lastro na trajetória é "não corroborada" — e em P1 isso bloqueia.
- **Régua de rastreabilidade (ADR-0012).** Toda saída importante precisa rastrear a cadeia completa: requisito da SPEC → artefato/diff → fonte (gate executado, e aresta do grafo quando houver) → decisão de avaliador. Elo quebrado em requisito P1 = veredicto no máximo "aprovado com ressalvas", nunca "aprovado". É essa cadeia que separa validação de opinião.
- **PT-BR em tudo.**
