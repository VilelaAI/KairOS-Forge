# ADR-0034 — Contrato de integração público e versionado

- **Status:** aceito
- **Data:** 2026-08-05
- **Versão:** v0.27.0

## Contexto

Análise do [kairos-symphony](https://github.com/VilelaAI/kairos-symphony) a pedido do
usuário, depois de eu propor construir um runtime que **já existia**.

O Symphony é a camada de orquestração persistente do ecossistema: daemon Node/TS, 8.576
linhas, 161 testes, M1–M5 prontos e conformidade SPEC v0.3 fechada. Issue tracker como
máquina de estados, worktree por issue, spawn de CLI via `child_process` — sem SDK, sem
chave de API. É ponto por ponto a forma que eu tinha proposto, só que construída.

Três achados organizam este ADR.

**1. As duas máquinas de estado se aninham, não colidem.** O Symphony tem 6 estados de
ciclo de vida do item de trabalho (`triage → ready → in_progress → blocked →
review_pending → done`); o `ciclo.py` tem 17 estados do arco de uma entrega. O
`in_progress` do Symphony é exatamente onde o arco inteiro mora. Um decide *qual trabalho
roda*, o outro *como uma entrega anda por dentro*.

**2. A costura tem um defeito, e é o nosso.** O §17 da SPEC do Symphony (loop autônomo)
para lendo a última linha de um `checkpoint.md` **escrito pelo agente**: `DONE` fecha,
`BLOCKED:` bloqueia. É precisamente o que o Forge passou da v0.21 à v0.26 removendo — o
ADR-0029 tirou o veredicto da palavra do agente, o ADR-0032 fechou a metade que faltava,
o ADR-0033 estendeu aos três gates.

O Symphony não errou: ele reimplementou porque **do nosso lado não havia contrato**. O
`estado --json` existia como detalhe de implementação, sem versão, sem garantia, sem
nada que dissesse "pode depender disto".

**3. Acoplar a detalhe interno é pior que não acoplar.** Se o Symphony começasse a ler o
`estado --json` hoje, qualquer refatoração nossa — renomear um estado, mudar a forma de
um campo — quebraria o consumidor em produção, sem sinal nenhum no nosso CI.

## Decisão

Promover a **duas superfícies** de detalhe de implementação a contrato público
versionado, e fazer o CI recusar mudança silenciosa.

### A — `kairos-forge/ciclo` v1.0

`ciclo.py estado --json` passa a garantir uma lista fechada de campos, e ganha quatro
**derivados** que não existiam:

| Campo | Por que existe |
|---|---|
| `terminal` | O consumidor não precisa conhecer `TERMINAIS` |
| `aguardando_humano` | Precisa de gente, não de agente — sem comparar nome de estado |
| `gate` | Qual gate está em jogo, sem mapear estado→gate por fora |
| `resultados_validos` | O que `registrar` aceita **agora** |

Os quatro existem para uma coisa só: **impedir comparação de string de estado**. Um
consumidor com `if estado == "aguardando_aprovacao"` quebra quando renomearmos; com
`if aguardando_humano`, não. Sem os derivados, publicar o contrato só formalizaria o
acoplamento ruim.

E `ciclo.py contrato` publica o grafo inteiro — estados, terminais, gates e **todas as
transições** — para que o consumidor leia a máquina em vez de repeti-la. Máquina
repetida do outro lado diverge na primeira aresta nova.

### B — `kairos-forge/contrato` v1.0

As três fences (`kairos-critica`, `kairos-validacao`, `kairos-revisao`), seus campos
obrigatórios, as regras de aceitação (coerência, cobertura, independência) e os quatro
códigos de erro viram declaração publicada por `contrato.py esquema`.

Os códigos ganham semântica de ação declarada, que antes existia só na cabeça de quem
escreveu: `json_invalido` e `estrutural` cabem um retry; **`sem_cobertura` é achado, não
retry** — o relatório está errado, e insistir só produz o mesmo relatório errado.

### C — Assinatura verificada no CI

`contratos/ASSINATURA.json` guarda versão + `sha256` da declaração de cada contrato. O
`release.py check` recalcula em todo PR: mudou a forma sem reassinar, **vermelho**, com
a mensagem dizendo qual bump considerar. `release.py assinar-contratos` reassina de
propósito.

Mais uma verificação viva: a saída real de `vista_publica()` precisa conter todo campo
prometido. Declaração sem verificação é promessa — e este repositório já decidiu, no
ADR-0030, que promessa não basta.

É o digest de certificação do ADR-0030 aplicado à fronteira em vez do artefato avaliado.

### D — Regra de versionamento declarada

**MENOR** (1.x): campo novo, estado novo, aresta nova, fence nova — consumidor antigo
segue válido. **MAIOR** (x.0): campo removido ou renomeado, semântica alterada, regra de
aceitação mais estrita.

E a fronteira **negativa**, que importa tanto quanto: o formato do
`.agents/ciclo/<spec>.json` em disco, a saída de terminal de qualquer script, e
`telemetria.py`/`painel.py`/`diagnostico.py`/`guardrail.py` **não** são contrato. Úteis,
sem promessa. Promoção se alguém precisar, por ADR.

## Consequências

**Positivas**

- O Symphony pode trocar o `checkpoint.md` por `ciclo.py estado --json` e herdar de
  graça: transição que recusa movimento inválido, veredicto vindo de artefato, ficha
  devolvida por progresso, teto absoluto e escalação automática.
- Os três `aguardando_*` do Forge encontram no `blocked` do Symphony o canal humano que
  faltava. Eu havia dito que um runner precisaria de "um canal para perguntar"; o
  Symphony já tem o melhor possível — a issue.
- O `.agents/ciclo/` resolve o pause/resume que o §17.6 da SPEC do Symphony lista como
  fora de escopo: o estado já sobrevive a restart de daemon e troca de CLI.
- Refatorar por dentro fica **mais** livre, não menos: com a fronteira declarada, o que
  está fora dela é seguro mexer.

**Negativas e limites, declarados**

- **Contrato é compromisso.** Renomear um estado agora custa um MAIOR e uma conversa com
  o consumidor. Era grátis; deixou de ser. É o preço de alguém poder depender.
- **O digest pega forma, não semântica.** Trocar o significado de um campo mantendo nome
  e tipo passa no check. Nenhuma verificação automática cobre isso — cobre revisão.
- **Nada foi construído do lado do Symphony.** Este ADR abre a porta; atravessar é
  trabalho no outro repositório, e lá o `factory-kairos-forge` hoje lê só `agents/*.md`
  — não conhece skills, `ciclo.py` nem `contrato.py`. O README dele ainda diz "45
  agentes" e "24+21 personas"; estamos em 71 (40 core + 31 apoio).
- **Duas versões para acompanhar.** A do plugin (`0.27.0`) e as dos contratos (`1.0`)
  andam em ritmos diferentes de propósito, e alguém vai confundir as duas pelo menos uma
  vez.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Criar um repositório novo de runtime | O runtime já existe e é o Symphony. Um terceiro orquestrador (com a ponte Hermes, seriam três) seria a primeira coisa a ficar desatualizada |
| Deixar o Symphony ler o `.agents/ciclo/*.json` direto | Acopla ao formato em disco, que é interno. `estado --json` é a camada que pode absorver mudança |
| Publicar o contrato sem os campos derivados | Só formalizaria o acoplamento ruim: o consumidor continuaria comparando nome de estado, e todo rename viraria MAIOR |
| Documentar em prosa, sem assinatura no CI | Contrato que ninguém verifica é promessa. Sem digest, um rename passa no review, é espelhado, sai numa release, e quem descobre é o consumidor |
| Versionar junto com o plugin (0.27.0 ⇒ contrato 0.27) | Amarra a fronteira ao ritmo interno: bump de patch em prompt de agente viraria "versão nova de contrato" sem nada ter mudado ali |
| Promover `telemetria.py` e `painel.py` a contrato agora | Ninguém consome ainda. Contrato sem consumidor é peso morto que só descobre estar errado tarde demais |
