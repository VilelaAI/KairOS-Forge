# POC — o MHL dirigindo o arco `/entregar` pelo contrato do `ciclo.py`

- **Modo:** `rodar explorar` (ADR-0040) · branch `poc/mhl-entregar` · worktree fora do repo
- **Missão:** provar que um runner externo consegue conduzir o arco `especificar → construir → validar → revisar → PR` lendo **só** o contrato público `ciclo.py estado --json` (ADR-0034, v1.1), sem reimplementar a máquina de estados, com os gates humanos como `pause()` e retomada por `--resume`.
- **Tempo-box:** uma tarde (2 h). Consumido: ~35 min de relógio (14:30 → 15:05 UTC), a maior parte lendo a referência do MHL e os samples; as execuções em si somam menos de 5 min.
- **Limites declarados:** nada aqui vira PR. O código desta pasta é descartável por contrato; o que sobrevive são estas notas.
- **Ferramentas:** `mhl` compilado da branch `develop` de `mh-language/mhl-core-runtime` (Go 1.25, `go build ./cmd/mhl`), `claude` 2.1.274 headless, `ciclo.py` v0.34.1.

## O que foi construído

```
poc/mhl-entregar/
├── entregar.mh        # o runner: loop pipeline de 1 step, 93 linhas
├── simulado.sh        # agente sem modelo: faz o mínimo de cada estado e responde no schema
└── projeto/           # projeto de brinquedo: SPEC-001/002/003, contextos/testes.md, .claude/ com as skills do plugin
```

O `entregar.mh` tem um `agent Forge` (`engine: "cli/claude-code"`, `claude -p … --output-format json --json-schema {resultado, nota}`), um `agent ForgeSimulado` (o shell script, mesmo JSON de saída), um `tool Ciclo` que embrulha `cmd.exec` sobre `ciclo.py estado <spec> --json` e `registrar <resultado> <spec>`, uma `memory Trilha` (jsonl) e um `loop pipeline Entregar` com `max_iterations: 10`. O único step faz o laço mínimo de `docs/contrato-de-integracao.md`:

1. `Ciclo.estado(spec)` → objeto do contrato.
2. `terminal` → `break`.
3. `spec_alterada == true` → `pause("reaprovar ou voltar a SPEC")`.
4. `aguardando_humano` → `pause(proximo_passo)`.
5. `estado == "pronto_para_pr"` → `pause` (abrir PR ficou fora do tempo-box — **a única comparação de nome de estado do runner, declarada**).
6. Monta o prompt com `estado`, `proximo_passo` e `resultados_validos`; roda o agente; `json.parse` → `structured_output.resultado`.
7. Recusa resultado fora de `resultados_validos` (`fail`); `Ciclo.registrar`; `fail` se o `ciclo.py` recusar.

## O que funcionou

| Experimento | Resultado |
|---|---|
| Arco `construindo → validando → revisando → pronto_para_pr` em modo simulado, a partir de `abrir --spec-aprovada` | 4 iterações, 1 s. O `ciclo.py` leu os relatórios do disco (fences `kairos-validacao` e `kairos-revisao`) e aceitou `pronto`, `aprovado`, `limpo`; pausou em `pronto_para_pr` |
| `spec_alterada` continua `false` depois de o agente preencher Status/Verificação com `verificado:` | Confirmado na prática: o digest do contrato ignora as células de progresso, como desenhado na v0.34.1 |
| Humano registra `pr_aberto`; `mhl run --resume` | Reentra o step, lê `terminal: true`, `break "arco terminou em encerrado"` |
| Ciclo completo desde `enquadrando` (SPEC-002): três gates humanos | Cada `aguardando_*` virou um `pause` com o `proximo_passo` do contrato como motivo; humano registra `confirmado`/`escolhida`/`aprovada` e `--resume` continua. 18 passos no total, histórico do `ciclo.py`: `abrir → entendimento_pronto → confirmado → abordagens_prontas → escolhida → spec_pronta → limpa → aprovada → pronto → aprovado → limpo → pr_aberto` |
| SPEC-003 aprovada, critério de aceite alterado depois, runner retomado | Pausou na primeira iteração com "SPEC mudou depois da aprovação"; `ciclo.py reaprovar` (humano) e o runner seguiu |
| Modo real (`claude -p` de verdade) em `construindo`, `validando`, `revisando` (SPEC-003, a partir de `--spec-aprovada`) | 4 iterações, 3 min 19 s de relógio, pausou em `pronto_para_pr`. O Claude Code headless, com as skills do plugin em `.claude/`, **rodou as skills de verdade**: em `construindo` criou `saudacao.py` e o teste, rodou o gate e marcou `verificado:` na SPEC; em `validando` rodou `/kairos-forge:validar`, incluindo o `prova.py` (o teste novo saiu `falhou_na_base`), e salvou o relatório com a fence; em `revisando` rodou `/kairos-forge:revisar` com Helena e Patrícia, faixa 1, zero 🔴. O `ciclo.py` leu os três relatórios do disco e aceitou `pronto`, `aprovado`, `limpo`. Cada resposta veio no schema, com `resultado` dentro de `resultados_validos` |

**A tese central se sustenta:** o runner nunca precisou saber o nome de um estado para decidir o próximo passo, com uma exceção que a própria POC escolheu (`pronto_para_pr`). Os quatro campos derivados do ADR-0034 (`terminal`, `aguardando_humano`, `resultados_validos`, `proximo_passo`) mais o `spec_alterada` da v0.34.1 bastaram.

## O que não funcionou, e o que revelou

| Achado | Onde | O que fazer |
|---|---|---|
| `ciclo.py estado --json` **sem a SPEC** falha em ciclo encerrado ("nenhum ciclo aberto"): stdout vazio, o runner não consegue ler `terminal` | contrato do `ciclo.py` | Documentar em `docs/contrato-de-integracao.md`: consumidor passa a SPEC sempre. Sem mudança de código: a resolução implícita é conveniência de sessão, não contrato |
| O `--resume` do MHL **não restaura os `input`s** do pipeline (`undefined variable "spec"`); é preciso repassar `--input` no resume | MHL | Achado de ergonomia do MHL; o exemplo da referência deles de fato repassa `--input`. Workaround no runner: sempre repassar. Reportável como issue lá |
| `ciclo.py reaprovar` aceita selar em estado **anterior à aprovação** (`desenhando`, `criticando`) — sela um digest que ainda não significa contrato | `ciclo.py` v0.34.1 | Restringir `reaprovar` a ciclos que já têm `spec_digest` (isto é, depois de `construindo`); antes disso, recusar com mensagem. Patch pequeno |
| O agente simulado descobria a SPEC listando `docs/specs/` e pegava sempre a primeira | POC | Erro meu, corrigido: lê `SPEC-NNN` do prompt. Registro porque é o erro que um agente real também comete quando o prompt não diz a SPEC — o `proximo_passo` do contrato não cita a SPEC, o runner precisa citar |
| `.run()` do MHL devolve o stdout **bruto** do `claude` (por decisão deles, para não acoplar ao formato do CLI); com `--output-format json` é um objeto só e `json.parse` basta, mas com `stream-json` seria NDJSON para filtrar em `.mh` | MHL | Ficar em `--output-format json` + `--json-schema`; o `structured_output` é a única superfície estável |
| `claude -p --permission-mode bypassPermissions` **recusa rodar como root** ("cannot be used with root/sudo privileges"); o runner caiu na primeira chamada real | Claude Code × container | Em sandbox descartável, `IS_SANDBOX=1` no ambiente do `mhl` libera. Em máquina de gente, rodar como usuário comum ou usar `--allowedTools` explícito em vez do bypass. O `templates/ci/` do plugin não sofre disso (runner do Actions não é root) |
| Semântica at-least-once: se o step morre depois de `registrar` e antes do checkpoint, o `--resume` repete o step e tenta registrar de novo | MHL × `ciclo.py` | Não aconteceu na POC, mas o `ciclo.py` recusa o resultado repetido porque ele deixa de ser válido no estado novo (`TRANSICOES`), e o runner trata a recusa como `fail`. Vale um teste explícito no `ciclo.py`: registrar duas vezes o mesmo resultado nunca avança dois estados |

## Custo

- Modo simulado: 18 iterações em ~2 s. Zero tokens.
- Modo real, 3 chamadas do `claude -p` (uma por estado), lidas do log do agente:

| Estado | Tempo | Custo | Turnos internos |
|---|---|---|---|
| `construindo` | 72 s | US$ 0,58 | 16 |
| `validando` | 61 s | US$ 0,39 | 16 |
| `revisando` | 60 s | US$ 0,53 | 19 |
| **Total** | **3 min 13 s** | **US$ 1,50** | 51 |

Para uma feature de brinquedo. Uma feature real multiplica os turnos de `construindo`; `validando` e `revisando` tendem a ficar nessa ordem de grandeza porque leem o diff, não o repositório inteiro.

## Decisões que a tentativa revelou

1. **O contrato 1.1 basta para um runner externo.** Não apareceu necessidade de campo novo. O que apareceu foi documentação: "passe a SPEC" e "o `proximo_passo` não nomeia a SPEC".
2. **`pause` do MHL mapeia um a um nos `aguardando_*` do ciclo**, e o `--resume` reentra o step e relê o estado, que é exatamente o que o ADR-0033 pede de um runner headless. O `ciclo.py` continua sendo a fonte da verdade; o checkpoint do MHL guarda só o contador de passos.
3. **O MHL é candidato real a consumidor de `forge:construir`** (ADR-0040), ao lado do kairos-symphony, com uma ressalva de maturidade: projeto de 6 estrelas em branch `develop`, sem trace por step no runtime (a trilha aqui foi escrita pelo próprio pipeline numa `memory`). Adotar seria ADR próprio, e não antes de a triagem por issue ter trajetória.
4. **O runner é 93 linhas.** Se o kairos-symphony ou o Hermes precisarem do mesmo laço, é este.

## O que jogar fora

Tudo em `poc/mhl-entregar/`, inclusive o `simulado.sh`: ele existe para provar o runner, não para ser usado. O `entregar.mh` pode ser reescrito do zero em minutos a partir destas notas; o que vale é a lista de achados acima.

## Encaminhamentos

- [ ] `ciclo.py`: recusar `reaprovar` antes de a SPEC ter sido selada (patch).
- [ ] `ciclo.py`: teste explícito de idempotência — registrar o mesmo resultado duas vezes não avança dois estados.
- [ ] `docs/contrato-de-integracao.md`: "passe a SPEC explicitamente" e "o `proximo_passo` não cita a SPEC; o consumidor cita".
- [ ] Issue no `mh-language/mhl-core-runtime`: `--resume` não restaura `input`s (ou documentar que precisa repassar).
- [ ] Quando o `triar.yml` (ADR-0040) tiver trajetória: decidir por ADR o consumidor de `forge:construir` — MHL, kairos-symphony ou Hermes.
