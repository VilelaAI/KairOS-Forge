# Identidade do agente

A fábrica age com credencial própria, nunca com a de uma pessoa. A aula 5 do Tech Leads
Club (Fábricas Agênticas) dá os três motivos:

- **Dá para ver o que ela fez.** Commits, comentários, rótulos e PRs saem em nome dela, e o
  filtro por autor separa o trabalho da fábrica do trabalho do time.
- **Dá para dar permissões específicas a ela.** A fábrica recebe só o que cada gatilho
  precisa. Com o token de uma pessoa, ela herda toda a escrita que essa pessoa tem.
- **Dá para revogar.** Se algo der errado, suspender a fábrica é um clique, e ninguém do
  time perde acesso junto.

*"Se dá um problema, tu pode banir o agente, bloquear, tirar acesso. E não façam isso de
usar o mesmo acesso de uma pessoa: criem contas para eles."*

## Nos gatilhos de CI (`templates/ci/`)

Os quatro workflows tentam primeiro o **app da fábrica** e, sem ele, usam o **token do
workflow** (`github-actions[bot]`), que também não é uma pessoa e tem a permissão declarada
em cada arquivo. Nunca há terceira opção: token pessoal em workflow da fábrica é achado do
`check-agent-security.py`.

### Criar o app

1. **Settings → Developer settings → GitHub Apps → New GitHub App** (da organização, de
   preferência). Nome: `kairos-forge-<projeto>`. Desmarque o Webhook.
2. Permissões do repositório. O mínimo para os quatro gatilhos:

   | Permissão | Nível | Quem usa |
   |---|---|---|
   | Contents | Read and write | `corrigir` empurra a branch `forge/corrige-*` |
   | Pull requests | Read and write | `corrigir` abre o PR; `revisar` comenta |
   | Issues | Read and write | `triar` rotula e comenta; `auditar` abre a issue |
   | Actions | Read | `corrigir` baixa o log da execução que falhou |
   | Metadata | Read | obrigatória |

   Se só usa alguns gatilhos, dê só as permissões deles.
3. Gere a chave privada, instale o app **só nos repositórios da fábrica** e crie no
   repositório:
   - a variável `FORGE_APP_ID` (Settings → Secrets and variables → Actions → Variables);
   - o segredo `FORGE_APP_PRIVATE_KEY`, com o conteúdo do `.pem`.

Pronto. O passo "Identidade da fábrica" de cada workflow gera o token do app a cada
execução. Se a chave faltar ou falhar, o passo não derruba o job: cai no token do workflow.

### Por que vale mesmo com o token do workflow funcionando

O GitHub **não dispara workflows** a partir de ações feitas com o token do workflow. O PR que
o `corrigir` abre com ele não roda o CI sozinho, e o corpo do PR avisa: feche e reabra para o
CI rodar. Aberto pelo app, o PR dispara o CI como qualquer outro.

### O merge continua seu

Proteja a branch padrão: exija revisão aprovada e deixe o app **fora** da lista de quem pode
contornar a proteção. A fábrica abre PR, comenta e rotula, e quem mescla é uma pessoa. É a
mesma fronteira do ADR-0023 e do ADR-0031.

### Revogar

- **Pausar:** suspenda a instalação do app (Settings → GitHub Apps → Configure → Suspend).
  Os workflows passam a cair no token do workflow.
- **Cortar tudo:** remova o segredo `FORGE_APP_PRIVATE_KEY`, ou desinstale o app, e apague o
  segredo `ANTHROPIC_API_KEY`. Sem ele, os workflows pulam.

## Fora do GitHub

- **Tracker (Linear, Jira) e fontes de dados ligadas por MCP:** uma conta da fábrica, com
  acesso de leitura onde só precisa ler. Quando o `/evoluir` propõe ligar uma fonte que faltou
  (`falta-fonte:`), a credencial é desta conta.
- **Sessão assistida no seu terminal:** o agente usa a sua identidade de git e o seu `gh`,
  porque é você quem está ali, aprovando. O commit leva o trailer `Co-Authored-By` (e
  `Fabrica: kairos-forge` nos teammates), e é por ele que o `telemetria.py prs` separa o que é
  da fábrica (ADR-0044). Autonomia sem você no caminho (gatilho, rotina, worker 24/7) roda
  com a identidade da fábrica, não com a sua.

## Conferir

```bash
python3 <plugin>/scripts/check-agent-security.py .claude   # inclui os workflows do projeto
```

Workflow que cita `kairos-forge` e usa `secrets.GH_TOKEN`, `secrets.GH_PAT` ou qualquer
`secrets.*PAT*` aparece como achado `identidade da fábrica`.
