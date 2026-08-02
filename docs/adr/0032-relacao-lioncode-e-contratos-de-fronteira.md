# ADR-0032 — Relação com o LionCode e três mecanismos adotados dele

- **Status:** aceito
- **Data:** 2026-08-02
- **Versão:** v0.24.0

## Contexto

Análise do [LionCode](https://github.com/LionLabsCommunity/LionCodeLabs) (v1.2, MIT,
brasileiro) a pedido do usuário, com a pergunta explícita: *"e se a gente transformar o
KairOS-Forge num projeto como esse?"*

O LionCode é um **IDE desktop Electron para orquestrar agentes** — multi-provider
(Claude, Codex, GLM, MiniMax, Grok, Kimi), local-first, com cofre cifrado, servidor
HTTP/WS embutido, SQLite com 64 migrations, CodeGraph por projeto, worktree paralelo com
integração determinística e métricas de custo congeladas no uso. 216 mil linhas de
TypeScript, 220 specs Playwright. Não é demo.

A comparação que decide quase sozinha:

| | LionCode | kairos-forge |
|---|---|---|
| Código | 216.261 linhas | 6.783 |
| Camada de agente | 19 subagents + 26 skills + 12 do pipeline | 71 agentes + 18 skills |
| Categoria | **harness** (app) | **doutrina** (plugin) |

**Eles têm 32× o nosso código; nós temos 2,3× os agentes deles.** São coisas
complementares, não concorrentes — e a proporção diz onde cada projeto gastou.

### A convergência que importa

O pipeline `/featdevelop` + `/featbuild` do LionCode é, arquiteturalmente, o nosso
`/entregar` + `ciclo.py`. Não parecido — o mesmo, com as mesmas palavras:

> *"a sequencia e do codigo, nao do modelo"* — `shared/src/feature-pipeline.ts`
> *"validado por CÓDIGO (nunca por prompt)"* — `runner/build-contracts.ts`

Isso é o ADR-0029 escrito de forma independente por quem não nos conhece. Duas equipes
chegando na mesma regra por caminhos separados é a evidência mais forte disponível de
que a regra está certa — e mostra que o custo de 216 mil linhas não está na doutrina,
está no runtime.

## Decisão

### A — Não viramos um app. Passamos a caber dentro de um.

O ADR-0001 escolheu plugin em vez de runtime; o ADR-0029 recusou portar o runtime do
IAO pelo mesmo motivo. A resposta não muda, e agora tem alvo concreto:

**O caminho de maior retorno não é construir o que o LionCode construiu — é rodar
dentro dele.** O catálogo do LionCode é uma estrutura de dados (`db/seeds/dev-catalog-*/
subagents.ts` e `skills.ts`), o mesmo formato de problema que o ADR-0004 já resolve para
Codex e Cursor. Um alvo de sync a mais, não um produto a mais.

Três opções foram avaliadas:

| Opção | Custo | Decisão |
|---|---|---|
| **1. Sync para o LionCode** — gerar o seed a partir de `agents/` + `skills/` | semanas; um alvo em `sync-multi-cli.py` | **Direção adotada.** Fica para uma versão própria, quando houver acordo com o projeto — mas é o rumo |
| **2. Renderizador do estado da fábrica** — HTML/terminal sobre `.agents/ciclo/`, `.agents/execucoes/` e status da SPEC | dias | **Aceita como próximo passo natural.** O ADR-0013 já decidiu que o quadro é *renderização* do estado canônico, nunca estado novo — falta construir |
| **3. Produto separado** (app com licença/economia próprias, forge como camada MIT que o alimenta) | anos-pessoa | **Recusada por ora.** É o molde do ADR-0002 (kairos-ai), e continua disponível — mas seria um projeto novo, não uma evolução deste |

O que a opção 3 custaria em troca é concreto: hoje a fábrica entra com
`/plugin install` em quatro CLIs onde o usuário já mora. Um app começa do zero na parte
mais difícil, que é fazer alguém abrir.

### B — Três mecanismos adotados, que valem por si

**B1. Progresso real devolve a ficha (`ciclo.py`).**

O LionCode tem `FEATURE_BUILD_MAX_INTERVENTIONS = 3` com uma regra que o nosso orçamento
plano não tinha: *"PROGRESSO real zera o contador — real = uma sprint SUPERA o ponto
adotado; o re-percorrer de checkpoints de toda retomada NÃO conta."*

O orçamento plano confundia duas coisas diferentes. Cinco bloqueios que viram três e
depois um é convergência — escalar na segunda rodada interrompe quem estava resolvendo.
Cinco bloqueios que continuam cinco é patinação, e a segunda rodada já foi uma a mais do
que precisava.

Agora o `ciclo.py` compara a contagem de achados com a **melhor marca já atingida** no
gate: baixou, a ficha volta; não baixou, queima. A contagem vem do bloco de contrato do
relatório, **nunca da alegação do agente** — mesma regra do veredicto (ADR-0029).

Um **teto absoluto** (default 3× o orçamento) segue valendo por cima: quem baixa de 40
para 39 a cada rodada está "progredindo" e mesmo assim precisa de gente.

**B2. Prova de cobertura (`contrato.py` + guardrail).**

Do LionCode: *"`findings=[]` EXIGE `searched` não-vazio (prova de cobertura)"*. Um
validador que não achou nada precisa provar o que olhou — **no parser**, não no prompt.

A regra já existia na fábrica, em prosa, no `anti-drift.md`: *"olhei e parece bom não é
crítica"*. Agora é código que recusa:

```
bloqueios == 0  ⇒  `verificado` não pode ser vazio
criticos  == 0  ⇒  `examinado`  não pode ser vazio
```

"Não achei nada" sem dizer onde procurou não é ausência de defeito, é ausência de busca
— e as duas coisas produzem exatamente o mesmo texto tranquilizador.

**B3. Fence própria por tipo de relatório.**

Do LionCode: fences ` ```lioncode-pipeline ` e ` ```lioncode-build ` deliberadamente
distintas, porque *"um validador de build que emitisse um bloco do pipeline seria aceito
por engano se a fence fosse compartilhada"*.

Até a v0.23 o `ciclo.py` lia o veredicto com um regex sobre prosa (`**Veredicto:** …`).
O relatório de **revisão** tem exatamente a mesma linha. Funcionava porque só a validação
era lida do disco — uma coincidência, não um desenho.

Agora existem duas fences, nunca a mesma: ` ```kairos-validacao ` e ` ```kairos-revisao `.

### C — A revisão passa a ser lida do disco

Consequência necessária de B3, e correção de uma assimetria do ADR-0029: a validação
vinha de artefato, mas `registrar limpo` / `registrar critico` ainda era aceito na
palavra do agente, porque o `/revisar` não salvava relatório nenhum.

O `/kairos-forge:revisar` agora salva em `docs/specs/revisoes/REVISAO-<id>-<data>.md`
com bloco de contrato, e o `ciclo.py` lê os dois gates do disco.

## Consequências

**Positivas**

- O arco deixa de punir convergência. Era o incentivo errado mais caro que restava: o
  orçamento plano empurrava para "resolver tudo na primeira rodada ou escalar".
- Relatório limpo passa a custar alguma coisa — a lista do que foi olhado. É o antídoto
  direto contra o relatório tranquilizador de quem não procurou.
- As duas metades do arco agora vêm de artefato. A palavra do agente não move mais
  nenhuma aresta da máquina.
- A pergunta "devemos virar o LionCode?" fica respondida com direção, não com "não":
  o alvo é caber dentro dele.

**Negativas e limites, declarados**

- **A contagem de bloqueios é escrita pelo agente.** O contrato verifica coerência e
  cobertura, não veracidade — um relatório que subconta achados compra ficha que não
  ganhou. Mitigações existentes: o guardrail recusa incoerência, a telemetria corrobora
  os gates, e a SPEC continua exigindo `verificado:`. Nenhuma delas fecha o buraco; é
  disciplina, como o conjunto selado do ADR-0030.
- **Relatório sem bloco de contrato degrada em silêncio parcial.** O `ciclo.py` avisa em
  stderr e volta ao comportamento da v0.23 (toda rodada queima). É honesto — sem número
  não há como afirmar progresso — mas quem não ler o aviso não vai entender por que o
  ciclo escalou cedo.
- **O guardrail só morde quando o bloco existe e está errado.** Relatório legado sem
  bloco passa. Exigir o bloco quebraria projetos que já usam a fábrica; o preço é que
  a regra não alcança quem simplesmente não a adota.
- **A opção 1 é uma direção, não uma entrega.** Nada foi construído para o LionCode
  nesta versão, e um sync exige acordo com o projeto sobre formato e versionamento do
  seed — não é decisão só nossa.
- **Teto absoluto pode interromper convergência genuína.** Uma feature grande e honesta
  que precise de 8 rodadas vai escalar em 6. Preferimos escalar cedo demais a rodar sem
  fim; o teto é configurável por isso.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Reconstruir a fábrica como app Electron | 32× o código atual, e joga fora a distribuição por marketplace nos quatro CLIs — o único ativo que o LionCode não tem |
| Fork do LionCode com os 71 agentes dentro | Herdaríamos 216 mil linhas de manutenção de runtime para entregar uma camada de dados. O seed resolve o mesmo com três ordens de grandeza a menos |
| Exigir o bloco de contrato em todo relatório | Quebra relatório legado e transforma uma melhoria em migração forçada. Bloco presente-e-errado é subconjunto seguro |
| Contar progresso pela diferença de achados que o agente **relata na mensagem** | É exatamente o juiz em causa própria que o ADR-0029 tirou do caminho. Se não vem do artefato, não conta |
| Fence única (`kairos-relatorio`) com campo `tipo` | Um campo pode vir errado; uma fence errada não abre. O erro que queremos impedir é justamente o de tipo trocado |
| Deixar a revisão sem relatório em disco | Metade do arco continuaria decidida por alegação, e o teste da faixa de raio (ADR-0031) não teria onde morar |
