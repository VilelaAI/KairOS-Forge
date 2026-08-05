# Contrato de integração do kairos-forge

> Para quem **dirige** a fábrica de fora: [kairos-symphony](https://github.com/VilelaAI/kairos-symphony),
> um runner próprio, um job de CI, um bot. Decisão: [ADR-0034](adr/0034-contrato-de-integracao.md).

O kairos-forge é um plugin: quem executa é o CLI, quem decide o próximo passo é o
`ciclo.py`, e quem consome pode ser um daemon lá fora. Este documento define **o que é
estável** nessa fronteira — e, por consequência, o que não é.

A regra que organiza tudo:

> **Se não está aqui, é interno e pode mudar sem aviso.** Se está aqui, só muda com bump
> de versão, e o CI recusa mudança silenciosa.

## Os dois contratos

| Contrato | Comando | Versão | Para quê |
|---|---|---|---|
| `kairos-forge/ciclo` | `ciclo.py estado --json` | 1.0 | Qual o próximo passo, precisa de humano, o que registrar |
| `kairos-forge/contrato` | `contrato.py <gate> <arquivo>` | 1.0 | Ler o veredicto dos relatórios sem parsear prosa |

Ambos se publicam sozinhos, legíveis por máquina:

```bash
python3 scripts/ciclo.py contrato      # estados, terminais, gates, TRANSIÇÕES, campos
python3 scripts/contrato.py esquema    # as três fences, campos e regras de aceitação
```

**Leia a declaração em vez de repetir a máquina do seu lado.** O `ciclo.py contrato`
publica o grafo inteiro de transições; reimplementar por fora é garantir que os dois
discordem na primeira aresta nova.

## Contrato 1 — o estado do arco

```bash
python3 scripts/ciclo.py estado SPEC-001 --json
```

Campos garantidos:

| Campo | Tipo | O que faz por você |
|---|---|---|
| `contrato` | string | Versão deste contrato |
| `spec` | string | Qual SPEC |
| `estado` | string | Um de `estados` |
| `terminal` | boolean | Nada mais a registrar — pare |
| `aguardando_humano` | boolean | **Precisa de gente, não de agente** |
| `gate` | string\|null | Gate em jogo (`criticar`/`validar`/`revisar`) |
| `proximo_passo` | string | Instrução legível para o agente |
| `resultados_validos` | string[] | O que `registrar` aceita **neste** estado |
| `orcamento`/`rodadas`/`rodadas_totais`/`teto`/`marca` | object | Fichas por gate |
| `historico` | object[] | Toda transição, com horário e contagem |

Os quatro derivados no topo existem para você **não comparar string de estado**. Um
consumidor que faz `if estado == "aguardando_aprovacao"` quebra quando um estado é
renomeado; `if aguardando_humano` não.

### O laço mínimo

```
1. ciclo.py estado --json
2. terminal?           → pare
3. aguardando_humano?  → leve ao humano pelo SEU canal (issue, chat, PR)
                          e registre a resposta quando vier
4. senão               → invoque o CLI com `proximo_passo`
5. ciclo.py registrar <um de resultados_validos>
6. volte ao 1
```

**O `ciclo.py` já faz o que um runner precisaria fazer sozinho:** recusa resultado
inválido no estado, cobra o veredicto do artefato, conta ficha com devolução por
progresso, impõe teto absoluto e escala sozinho. Não reimplemente nada disso — chame.

E o estado vive em `.agents/ciclo/<spec>.json`, atômico via `os.replace`: sobrevive a
restart do seu daemon, troca de CLI e reset de contexto. Não guarde cópia.

## Contrato 2 — os relatórios

Três gates, **três fences distintas**, nunca compartilhadas:

| Gate | Fence | Onde | Contagem |
|---|---|---|---|
| `criticar` | ` ```kairos-critica ` | `docs/specs/criticas/` | `achados` |
| `validar` | ` ```kairos-validacao ` | `docs/specs/validacoes/` | `bloqueios` |
| `revisar` | ` ```kairos-revisao ` | `docs/specs/revisoes/` | `criticos` |

A separação é o ponto: os três relatórios carregam a mesma linha `**Veredicto:**`, e
fence compartilhada deixaria um ser lido como o outro no dia errado.

Três regras que o parser cobra, e que o seu lado deve cobrar igual se reimplementar:

1. **Coerência** — `bloqueado` ⟺ contagem ≥ 1.
2. **Prova de cobertura** — contagem 0 exige a lista do que foi olhado não-vazia.
3. **Independência** (só na crítica) — ao menos 2 nomes distintos em `criticado_por`.

Códigos de erro, e o que fazer com cada um:

| Código | Significado | Ação |
|---|---|---|
| `ausente` | Sem bloco com a fence | Relatório legado — degrade, não falhe |
| `json_invalido` | Bloco não é JSON | Cabe **1 retry** com a mensagem de erro |
| `estrutural` | Campo/tipo/coerência | Cabe **1 retry** |
| `sem_cobertura` | Limpo sem lista | **Achado**, não retry — o relatório está errado |

## Versionamento

| Mudança | Bump |
|---|---|
| Campo novo, estado novo, aresta nova, fence nova | **MENOR** (1.x) — consumidor antigo segue válido |
| Campo removido/renomeado, semântica alterada, regra mais estrita | **MAIOR** (x.0) |

`contratos/ASSINATURA.json` guarda versão + `sha256` de cada declaração, e o
`release.py check` recalcula em todo PR. Mudou a forma sem reassinar → **CI vermelho**,
com a mensagem dizendo qual bump considerar.

Isso existe porque contrato que ninguém verifica é promessa: sem o digest, um campo
renomeado passa no code review, é espelhado no `plugin/`, sai numa release, e quem
descobre é o consumidor em produção.

Ao mudar de propósito:

```bash
python3 scripts/release.py assinar-contratos   # depois de ajustar CONTRATO_VERSAO
```

## O que **não** é contrato

- Formato do `.agents/ciclo/<spec>.json` em disco — leia via `estado --json`.
- Saída de terminal de qualquer script — é para humano.
- Nomes de estado como string comparável — use os derivados.
- `telemetria.py`, `painel.py`, `diagnostico.py`, `guardrail.py` — úteis, sem promessa
  de estabilidade. Peça promoção a contrato se precisar.
- Nomes e quantidade das 71 personas. São estáveis por convenção do projeto
  (`CLAUDE.md`), não por contrato versionado.

## Pré-requisito do outro lado

Antes de dirigir a fábrica, o repositório precisa estar **harness-ready**: plugin
instalado, `CLAUDE.md`/`AGENTS.md` preenchidos, `contextos/` populado, gates conhecidos,
e telemetria ativa se você quiser corroboração de evidência.

`/kairos-forge:onboardar` faz isso, e `/kairos-forge:auditar` mede. Orquestrador sobre
repositório sem harness não produz autonomia — produz N PRs ruins em paralelo.
