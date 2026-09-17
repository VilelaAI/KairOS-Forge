# ADR-0042 — Piso de execução, gate de parada e hooks no Cursor

- **Status:** aceito
- **Data:** 2026-09-17
- **Versão:** v0.35.0

## Contexto

Em 12 de setembro de 2026 Felipe Rodrigues apresentou o **harness-toolkit** do Tech Leads
Club: uma camada de hooks para Cursor e Claude Code com oito regras de piso que
configuração nenhuma desliga, três checagens sempre ativas e vinte e quatro rails
opcionais, governada por um `config.json` versionado no repositório. A tese é a mesma do
ADR-0022 ("prompt pede, hook garante") e o toolkit é fruto do mesmo diagnóstico: modelo
melhor erra menos, mas erra, e quando erra só importa o que está entre ele e as quatro
superfícies que não se desfazem sozinhas (shell, arquivos, git, subagentes).

A licença é Elastic 2.0, não OSI. Nada do código pode entrar num plugin MIT. As ideias
podem, e a auditoria do `guardrail.py` contra o piso deles encontrou lacunas concretas:

| Regra do toolkit | O que o `guardrail.py` tinha | A lacuna |
|---|---|---|
| `secret-access` — nega **ler** `.env`, `~/.ssh`, `*.pem`, credencial AWS; libera `grep` pelo nome da variável | `.env` protegido só contra **escrita**; `cat .env \| curl` bloqueado como exfiltração | `cat .env` sozinho passava, e o segredo entrava no transcript e na trajetória |
| `wiring-tamper` — protege o arquivo em que o editor registra os hooks | nada | O agente podia editar `.claude/settings.json` e silenciar guardrail e telemetria de uma vez |
| `unprovable-destruction` — `rm -rf` com alvo em variável ou substituição | nada | Não dá para provar o que `rm -rf "$DIR"` apaga antes de rodar |
| `outside-project-destruction` — destruição fora do repositório e fora de temp | só a raiz e o home | `rm -rf /opt/outro-projeto` passava |
| `machine-control` — `shutdown`, `reboot`, `poweroff` | nada | Barato, e num container é exatamente o que se quer negar |
| Ship gate e Grind — o "terminei" contra evidência de PASS recente, no `stop` | `verificado:`, `prova.py` e corroboração, tudo lido **depois**, pelo `/validar` | Nada rodava no hook `Stop`; a DoD "gate antes de encerrar" era prosa |
| Cursor e Claude Code com uma lógica de decisão | hooks só no Claude Code; a tabela de limitações dizia que o Cursor não tinha telemetria nem guardrail | O Cursor expõe `hooks.json` com os eventos de ciclo de vida; o forge não os usava |

O que o forge já tinha equivalente, e o ADR registra para não ser refeito: os caminhos
sagrados que o agente não escreve (o `policy-surface-write` deles), `curl|sh`, force-push
em branch protegida, PR fora de estado, recusa registrada na trajetória, e a patinação do
ADR-0030 (o "loop de três tentativas" deles). E o que o forge tem e o toolkit não tem, por
serem produtos de camadas diferentes: máquina de estados, orçamento, compensação, contrato
de relatório, grafo. Os dois convivem no mesmo Claude Code sem conflito; este ADR não
duplica rails do toolkit, fecha o piso.

## Decisão

**1. Cinco regras novas no piso do `guardrail.py`.** Piso é o que não tem `modos` nem
`liberados`: roda antes de a configuração importar, e a configuração é um dos arquivos
que o agente não alcança — a mesma garantia por ordem de execução que o toolkit descreve.

- **Leitura de segredo** (classe `segredo`): comando que **mostra** conteúdo (`cat`,
  `head`, `sed`, `base64`, `cp`…) sobre `.env*`, `~/.ssh`, `~/.aws`, `*.pem`, `id_rsa`,
  `.npmrc`, e chamada ao serviço de metadados da nuvem. `grep`, `rg`, `ls`, `stat`,
  `test`, `wc` e `find` não estão na lista de leitores: procurar o nome de uma variável
  não é ler o valor dela. `.env.example` e afins passam. A tool `Read` ganha o mesmo
  critério pelo hook novo `leitura`.
- **Fiação dos hooks** (sagrado): `.cursor/hooks.json` e `.codex/hooks.json` inteiros;
  em `.claude/settings*.json` só a escrita que **altera o bloco `hooks`** — o agente
  edita esse arquivo por motivos legítimos (permissões, variáveis) e continua podendo.
- **Destruição não provável**: `rm -rf` cujo alvo vem de variável ou substituição.
- **Destruição fora do projeto**: `rm` recursivo em caminho absoluto, `~` ou `..` que
  resolve fora do repositório e fora de temp.
- **Controle da máquina**: `shutdown`, `reboot`, `halt`, `poweroff`, no início de um
  segmento de comando (não dentro de um nome de arquivo).

O critério de desenho é o deles: **negar a cauda destrutiva sem negar o caminho legítimo
parecido**. Regra que bloqueia `grep DATABASE_URL .env` é regra que o time desinstala.

**2. Gate de parada** (classe `parada`, hook `Stop`). A sessão que escreveu código de
produção e não rodou nenhum gate verde **depois da última escrita** não encerra em
silêncio: o hook lista os arquivos sem prova, os gates de `contextos/testes.md` e os
últimos gates vermelhos, lidos da trajetória que o `execucao.py` já grava. É o ship gate
do toolkit com a evidência da fábrica. Recorte deliberado: só a sessão atual, só
produção (teste e doc não contam), só o que veio depois do último gate verde — regra que
dispara em sessão de leitura vira ruído. Nasce em `aviso` (ADR-0030); em `bloqueio` o
modelo recebe a lista e continua. Nunca dispara duas vezes na mesma parada
(`stop_hook_active` no Claude Code, `loop_count` no Cursor), porque gate vermelho
viraria laço infinito.

**3. Hooks no Cursor, gerados pelo sync.** O `sync-multi-cli.py` passa a escrever
`.cursor/hooks.json` ligando `sessionStart`, `beforeSubmitPrompt`, `beforeShellExecution`,
`beforeReadFile`, `afterShellExecution`, `afterFileEdit`, `subagentStart` e `stop` aos
mesmos `execucao.py` e `guardrail.py` já espelhados em `.cursor/scripts/`. O payload do
Cursor é reconhecido **pela forma** (`conversation_id` sem `tool_input`), nunca por
configuração, e a resposta sai no dialeto dele (`permission`, `additional_context`,
`followup_message`) em vez de exit 2. O arquivo gerado é sagrado (fiação) e gerado
(ADR-0037) ao mesmo tempo. Duas linhas da tabela de limitações por CLI mudam de ❌ para ✅:
telemetria de execução e guardrails no Cursor. O que **não** muda: o Cursor não expõe
hook antes de uma edição de arquivo, então as classes de escrita (sagrados, gerado,
teste existente) ali dependem do modo CLI `guardrail.py verificar` no CI do projeto.

**4. Suíte de testes do guardrail** em `scripts/tests/test_guardrail.py`, no CI: dezesseis
casos cobrindo cada regra do piso (o que nega e o que libera), a fiação condicional do
Claude Code, o gate de parada nos dois modos e o adaptador do Cursor.

## Consequências

| O que | Antes | Depois |
|---|---|---|
| `cat .env` | passava | negado; `grep` passa |
| Editar `hooks` em `.claude/settings.json` | passava | negado; permissões continuam livres |
| `rm -rf "$DIR"`, `rm -rf /outro`, `reboot` | passavam | negados |
| Encerrar sessão com produção sem gate | silêncio | aviso com a lista; `bloqueio` devolve o trabalho |
| Cursor | sem telemetria, sem guardrail | `hooks.json` gerado; trajetória e piso iguais aos do Claude Code |
| Classes do guardrail | 6 | 8, mais 3 regras de comando no piso |

**Positivas**

- O piso do forge passa a cobrir as quatro superfícies do diagrama do toolkit.
- A DoD deixa de depender de o modelo lembrar: quem cobra o gate é o hook.
- A dimensão Autonomia do `/auditar` passa a ser medida no Cursor.

**Negativas e limites, declarados**

- **Os hooks do Cursor seguem a documentação de setembro de 2026 e foram testados com
  payloads sintéticos**, não num Cursor real nesta sessão. Campos de `afterShellExecution`
  (saída, código de saída) são lidos de forma tolerante; se o nome for outro, a trajetória
  registra o comando com `ok: null`, nunca um resultado inventado.
- **Leitura de segredo é regex sobre o comando.** `python3 -c "print(open('.env').read())"`
  é pego pelo leitor `python3` mais o alvo; um leitor fora da lista não é. A lista cresce
  por evidência, não por antecipação.
- **Fiação condicional no Claude Code é heurística no `Edit`**: bloqueia quando a string
  trocada toca `hooks`, `guardrail`, `execucao.py` ou `kairos-forge`. Uma edição que
  reescreve o arquivo inteiro por `Write` é comparada por estrutura, que é o caminho
  exato.
- **O gate de parada só vê o que a trajetória viu.** Gate rodado fora do hook (CI,
  outra máquina) não conta; a saída é o autor declarar, que é o mesmo contrato do
  `verificado:`. E `ok: null` (saída indeterminada) não conta como verde — o gate que
  "rodou mas não se sabe" é exatamente o que a regra existe para expor.
- **`aviso` depende de alguém olhar.** Como no ADR-0039: taxa baixa e estável de
  recusas em `parada` é o sinal para promover a `bloqueio`.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Instalar o harness-toolkit e não mexer no `guardrail.py` | Licença Elastic 2.0 impede levar o piso deles para dentro do plugin; e um usuário do forge sem o toolkit ficaria sem piso. Os dois convivem, mas o forge precisa do próprio |
| Bloquear `source .env` e `. .env` também | Carregar variáveis para rodar o processo não mostra o valor; negar isso é negar o caminho legítimo, e a regra seria desligada |
| Proteger `.claude/settings.json` inteiro, como o toolkit | O agente edita permissões e variáveis ali com frequência (há skill oficial para isso); a fiação é só o bloco `hooks` |
| Gate de parada rodando lint e teste sozinho (o Grind deles) | Exige saber o comando do projeto e rodá-lo no hook, com tempo e efeito colateral; a fábrica já grava o que rodou, então cobrar a evidência é mais barato e não inventa gate |
| Gate de parada em `bloqueio` por default | Sessão de refactor sem gate declarado viraria laço de reclamação; `aviso` primeiro, promoção por taxa (ADR-0030) |
| Comment gate, duplication gate, supply-chain gate | São rails, não piso, e a Patrícia no `/revisar` e o `grafo.py codigo` (ADR-0041) cobrem parte disso por leitura; entram por ADR próprio se a trajetória pedir |
| Varredura proibindo os nomes `cursor`/`claude` nos scripts, como o `check-boundaries` deles | Os scripts do forge são o adaptador e o core ao mesmo tempo, e conhecem os caminhos dos mirrors por desenho (ADR-0037); a regra não se aplica sem separar camadas, que é outro ADR |
