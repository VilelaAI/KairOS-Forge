# Análise do pwdev-claude-marketplace — o que adotar para dar robustez ao forge

- **Data:** 2026-09-06
- **Fonte:** [pwdev-solucoes/pwdev-claude-marketplace](https://github.com/pwdev-solucoes/pwdev-claude-marketplace), commit `5b18e5c` (único commit público, 2026-09-05), Apache-2.0
- **Método:** clone completo; leitura integral dos 15 plugins, dos 3 protocolos em `shared/`, dos 10 módulos de teste e dos 10 documentos de design; execução da suíte de testes, dos guardas de shell e do servidor MCP contra payloads reais. Toda afirmação abaixo aponta o arquivo-fonte.

## 1. O que é

Marketplace de 15 plugins Claude Code da PWDEV (GovTech, PT-BR), 572 arquivos, ~50k linhas.
Quatro famílias:

| Família | Plugins | Linhas | O que carrega |
|---|---|---|---|
| Workflow de engenharia | `pwdev-power` (3 runtimes), `pwdev-flow` (Claude+Codex), `pwdev-code`, `pwdev-feat`, `pwdev-prd`, `pwdev-uiux` | 35k | Spec-driven, subagentes reais, frotas headless em worktree, auditoria SQLite/JSONL |
| Integração via MCP embutido | `pwdev-glpi`, `pwdev-postgres`, `pwdev-obsidian`, `pwdev-youtrack`, `pwdev-brain` | 5k | `.mcp.json` no plugin, `check-setup.sh` com handshake real, segredo no Keychain |
| Marketing | `pwdev-copy`, `pwdev-social-media` | 7k | Skills de criação e revisão adversarial; wrappers de API com "trava de gasto" |
| Operação | `pwdev-devops`, `pwdev-statusline` | 3k | 19 skills de infra com "execução segura" |

Mais `tests/` com 297 métodos `unittest` (7.206 linhas) e `docs/superpowers/` com pares spec+plan por marco.

**Contexto que enquadra tudo:** um só commit, **sem CI**, e a suíte só roda nomeando o módulo (`unittest discover` acha zero testes; `pytest` falha em 4 de 8 módulos por falta de `tests/__init__.py`). A suíte é excelente e nada a executa automaticamente. Três casos falham em sandbox por assumirem init que colhe zumbis, sem `skipUnless`.

## 2. Comparação direta com o forge

| Dimensão | pwdev | forge | Quem está na frente |
|---|---|---|---|
| Máquina de estados do arco | prosa em `state.md` editado pelo modelo; só o runner de frota (`fleet-run.sh`) conta ciclos por código (teto 2) | `ciclo.py` decide transição, orçamento e escalação; contrato v1.0 assinado (ADR-0029/0034) | forge |
| Quadro de tarefas | `ledger.md` criado por script, lido só pelo modelo | `quadro.py`: dependências, teto de onda, colisão de posse, prazo, compensação Saga (ADR-0035/0036) | forge |
| Guardrail de comando destrutivo | `guard.sh` do devops **não está em hook**: o modelo decide chamá-lo e passa `--confirm` sozinho; libera `kubectl -n x delete`, `rm -rf <path>`, `terraform apply -destroy`; `--env` ausente é tratado como não-prod | `guardrail.py` em `PreToolUse`, exit 2, classes com modo por projeto (ADR-0022/0030) | forge |
| Guardrail de segredo | `guard-secrets.sh` em `PreToolUse Read\|Bash` bloqueia `.env`, `.pem`, `.key`, `id_rsa`; furos: `.envrc`, `prod.env`, `printenv`, `Grep`/`Glob` fora do matcher, fail-open se o `jq` falhar | `guardrail.py escrita` protege escrita e `comando` pega exfiltração por rede; **leitura via `Read`/`Grep` não é coberta** | empate; gap dos dois lados |
| Contrato de relatório | `fleet-result.schema.json` (Codex valida nativamente; Claude/Hermes leem como prosa) com `status` do estágio separado de `verdict` sobre o trabalho | fences `kairos-*` com prova de cobertura e independência dos críticos, verificadas por `contrato.py` (ADR-0032/0033) | forge, mas ver §4.D |
| Telemetria | SQLite opt-in; hooks em `SubagentStart/Stop` com `duration_ms`; `audit-log.sh` rejeita `prompt`/`model`/segredo e path absoluto; colisão de chave com dois subagentes do mesmo tipo em paralelo | `.agents/execucoes/*.jsonl` inegociável, redação de segredo; **sem `SubagentStart/Stop`**, e o ramo `delegacao` do `execucao.py` nunca dispara (nenhum matcher inclui `Agent\|Task\|Skill`) | pwdev nos eventos; forge na inegociabilidade |
| Multi-CLI | skills neutras + adaptador fino por runtime; tabela de tools por runtime lida em tempo de execução pelo bootstrap Hermes | canônico Claude Code + mirrors gerados por `sync-multi-cli.py` para Codex/OpenCode/Cursor (ADR-0035) | empate; abordagens diferentes |
| Protocolos compartilhados | `shared/*.md` "sincronizados à mão"; zero referências dos plugins ao canônico; já divergiram (papéis fantasmas no uiux, versão 2.4.0 vs 2.3.1 vs 2.2.0 vs 2.0.0 no mesmo plugin) | contagens e versão injetadas por `release.py`, mirrors gerados, paridade verificada no CI | forge |
| Testes do próprio plugin | 297 testes: contrato estrutural, argv literal de cada adaptador, PATH fechado com binários falsos, injeção de falha na N-ésima escrita, SIGTERM no comando exato, sanitização da trilha | `release.py check` (consistência), assinatura de contrato, eval de roteamento (precisa de modelo); **6.157 linhas de Python sem nenhum teste unitário**; os 8 casos determinísticos do eval de comportamento não têm runner | **pwdev, com folga** |
| Progressive disclosure | sem regra escrita; skills curtas por convenção; teste exige description começando com "Use when" | teto de 500 linhas, raiz como roteador e teto de description verificados no CI (ADR-0027/0038) | forge |
| Portabilidade Windows | `run-hook.cmd` poliglota + script sem extensão (Claude Code no Windows prefixa `bash` a qualquer comando com `.sh`) | hooks assumem `python3` e um hook usa `jq`/`grep`/`touch` | pwdev |

Leitura honesta: o forge está à frente em tudo que é **decidido por código no caminho do agente**. O pwdev está à frente em **provar que o próprio código faz o que promete**, e em dois detalhes de telemetria. É exatamente o inverso do que os READMEs de cada lado sugerem.

## 3. Onde a robustez deles é código (vale estudar)

1. **Frota headless** (`pwdev-power/scripts/fleet-*.sh`, ~1.900 linhas): identidade do runtime exportada em **um** arquivo (`fleet-launch-core.sh:12-19`) e recusada no runner se o membro registrado discorda (`fleet-run.sh:87-102`); hash SHA-256 dos contratos sobre os **bytes da working tree**, conferido antes e depois de cada estágio, com regra explícita para o estágio que legitimamente reescreve o próprio artefato (`fleet-run.sh:129-157, 554-558`); preflight que recusa lançar com contrato gitignored, porque "fez trabalho?" é perguntado ao git e git nunca vê path ignorado (`fleet-up.sh:104-106`, `fleet-run.sh:405-411`); posse do grupo de processos com `setsid`, TERM → KILL, e **retenção do lock** quando não se prova que o grupo morreu (`fleet-run.sh:245-293`); `--resume` como única forma de tocar `NEEDS_HUMAN`.
2. **`review-package.sh` exit 3 quando `base == head`** (`pwdev-power/scripts/review-package.sh:24-27`): o único ponto do ciclo em sessão que recusa mecanicamente um "DONE" sem commit.
3. **`run-agent.sh`** (`pwdev-code/scripts/run-agent.sh`): delegação a CLI externa com allowlist de binários, lock por `mkdir`, snapshot `git status` para provar modo somente-leitura, `stdin=/dev/null`, prompt como argumento único (sem `eval`), e no `pwdev-flow` um **token de confirmação = SHA-256 do argv expandido** (mudou o modelo no config, o token antigo não vale).
4. **`audit-log.sh` / `flow_audit.py`**: vocabulário fechado de ações, rejeição de qualquer chave `prompt|model|token|secret`, path normalizado para relativo ao repo (com o alias `/private` do macOS), append com `O_NOFOLLOW`, gravação **só depois** do fato durável.
5. **Servidor MCP somente-leitura em Node puro** (`pwdev-brain/server/tools.mjs:63-95`): prefixo permitido, denylist de diretório, `realpath` contra a raiz (symlink para fora é negado — testado), só texto, truncamento, `read_only: true` no info, nunca falha no boot.
6. **`check-setup.sh` dos integradores**: `stty -echo` + Keychain com fallback declarado, máscara 5+4, e handshake real classificando o erro (`initSession`/`killSession` no GLPI; `/api/users/me` no YouTrack; exit 7/28 vs 401 no Obsidian).
7. **Bootstrap reinjetado em `startup|clear|compact`** (`pwdev-power/hooks/session-start`): a disciplina sobrevive à compactação de contexto, emitindo exatamente um campo por plataforma.
8. **A suíte de testes** (§5), que é o que separa os itens acima de promessas.

## 4. Onde é só prosa (não copiar, e onde o forge já resolveu por código)

| Alegação do pwdev | Realidade | Equivalente no forge |
|---|---|---|
| "guard.sh: instrução falha, trava não" | não é hook; modelo chama e passa `--confirm` | `guardrail.py` em hook (ADR-0022) |
| "auditor somente-leitura por construção" | tem `Write` e `Bash` no frontmatter | allow-list explícita, `check-agent-security.py` |
| TDD / causa raiz / "rode e leia a saída" | 100% prosa reinjetada + separação de papéis | DoD com autocrítica ancorada, `verificado:` cobrado pelo guardrail |
| Ciclo de correção ≤ 5 rodadas, 1 conselho por task | `state.md` editado pelo modelo | `ciclo.py` (ADR-0029/0032) |
| Roteamento de modelo por complexidade | prosa; a trilha nem grava o modelo; auto-relato auditando auto-relato | ledger por tier (ADR-0013), ainda em prosa também |
| "Trava de gasto" dos wrappers de API | bug de `$@`: bloqueiam **sempre**, até com `--confirm`; ninguém rodou | n/a |
| "Passe 0 anti-slop determinístico", "contraste medido vs exigido" | o modelo contando; nenhum instrumento | eval com juiz independente (ADR-0025/0031) |
| Lint OKF de 26 regras, proveniência por afirmação | LLM lendo a tabela; nenhum parser | `grafo.py validar` com proveniência (ADR-0009) |
| Driver headless por marcadores `FLEET_*` em texto livre | `grep` na saída do modelo | `ciclo.py estado --json` (ADR-0034) |
| `hooks.json` idêntico nos 4 plugins de workflow | 4 instalados = 4 gravações por evento, guard 4× | um plugin, um conjunto |

## 5. Recomendações, em ordem

Critério: o que fecha um gap real do forge com o menor custo, com o arquivo-fonte de referência do pwdev para quem for implementar.

### A. Suíte `unittest` para os scripts — o maior gap (ADR próprio, minor)

6.157 linhas de Python decidem transição, orçamento, bloqueio, contrato e compensação, e nenhuma linha tem teste. A assinatura do contrato (ADR-0034) pega mudança de **forma**; nada pega mudança de **comportamento**. Padrões a copiar, todos só-stdlib:

- `tests/__init__.py` para `discover` funcionar (o pwdev não tem e admite no docstring que `discover` "silently runs zero tests, which looks like success" — `tests/test_pwdev_power.py:7-10`). Job no `ci.yml` ao lado do `release.py check`.
- **Scripts como CLI em repo temporário**: `subprocess.run([sys.executable, script, ...])`, asserção sobre exit code + JSON no stdout + efeito no disco; após o caso negativo, `assertFalse(estado.exists())` ou bytes idênticos antes/depois (`tests/test_flow_operations.py:14-20, 101-142, 278-288`). Alvos: `ciclo.py` (toda transição da tabela, orçamento, escalação, `registrar aprovado` sem relatório), `quadro.py` (teto, colisão, `varrer`, `compensar` em ordem inversa, `encerrar` com lacuna), `guardrail.py` (cada classe, cada modo), `contrato.py` (cada fence, prova de cobertura, independência).
- **Hooks executados, não grepados**: rodar cada comando de `hooks/hooks.json` com JSON sintético de `PreToolUse` no stdin e afirmar exit 2 — a tese do pwdev: "the string assertions pass even when a dispatcher defines a function it never calls, which is exactly how a silently no-op fleet path shipped" (`tests/test_flow_claude_compat.py:155-162`).
- **PATH fechado com binários falsos**: um `gh`/`git push` falso que grava argv e sai 97 prova que o guardrail bloqueou *antes* da invocação (`tests/flow_m5_fixtures.py:161-169`, `tests/test_flow_fleet_lifecycle.py:65-88, 242-246`).
- **Injeção de falha na N-ésima escrita**: `unittest.mock.patch("os.replace", side_effect=...)` sobre `ciclo.py`/`quadro.py`/`execucao.py`, afirmando que o estado anterior permanece válido, nenhum `.tmp` sobra e a saída **diz** que falhou (`tests/test_flow_fleet_runner.py:144-173, 1069-1182`). Idem SIGTERM no meio de `compensar`.
- **Sanitização da trajetória como invariante**: gravar eventos com `prompt`, `api_key`, path absoluto e `.env` no payload; afirmar redação antes do append e que `telemetria.py resumo` nunca os serializa (`tests/test_flow_operations.py:101-142`).
- **Invariantes de prompt**: description começa por gatilho, flag perigosa aparece em exatamente um arquivo, todo path `${CLAUDE_PLUGIN_ROOT}/...` citado existe e não contém `..`, toda mensagem de erro citada na doc é emitida pelo script (`tests/test_pwdev_power.py:179, 290, 643`). Os 8 casos determinísticos de `evals/comportamento-fabrica/` viram testes aqui.
- **Somente-leitura por snapshot**: hash recursivo antes/depois para `painel.py`, `diagnostico.py`, `grafo.py validar`, `telemetria.py resumo` — transforma "renderização, nunca estado" do CLAUDE.md em teste.

### B. Telemetria: subagentes e delegação (patch)

- Adicionar `Agent|Task|Skill` ao matcher de `execucao.py ferramenta` — hoje o ramo `delegacao` (`execucao.py:196-197`) é código morto — ou os hooks `SubagentStart`/`SubagentStop`, com `duration_ms` chaveado por **id da instância**, não por tipo: a colisão que o pwdev tem (`pwdev-code/scripts/audit-hook.sh:50,61`) quebraria com 6 teammates por onda. Alimenta o `varrer` com dado real.
- Rejeição explícita de chaves `prompt|model` e normalização de path (com `/private`) no `execucao.py`, além da redação que já existe (`audit-log.sh:36-69`).

### C. "DONE sem commit" e "fez trabalho?" (patch em `contrato.py`/`quadro.py`)

`quadro.py concluir` exige evidência em texto; adotar a checagem mecânica: range de commits não vazio (`git rev-parse`) **ou** diretório da tarefa sujo (`review-package.sh:24-27`, `fleet-run.sh:405-411`), e o preflight `git check-ignore` sobre `.agents/` e o diretório da SPEC no `abrir` (`fleet-up.sh:104-106`).

### D. `status` do gate separado de `verdict` sobre o trabalho (minor no contrato)

Nas fences `kairos-validacao`/`kairos-revisao`, um campo "o gate rodou" independente de "o gate aprovou" (`templates/fleet-result.schema.json:12-25`). Evita que uma reprovação legítima seja lida como gate quebrado e trave a máquina fora do laço de correção, que existe para ela. Muda a forma → reassinar o contrato (ADR-0034).

### E. Posse do processo no `varrer` (minor)

Worker lançado como líder de grupo (`setsid`), TERM → espera → KILL, e a vaga só volta quando se prova que o grupo morreu; sem prova, a vaga fica retida como sinal para o humano (`fleet-run.sh:245-293`). Hoje o `varrer` devolve a vaga por prazo com o processo possivelmente vivo.

### F. Guardrail de leitura de segredo (patch)

Matcher `Read|Grep|Glob|WebFetch` para uma classe `leitura` no `guardrail.py`, reaproveitando `PROTEGIDOS_PADRAO`. E os 30 payloads do pwdev viram casos de teste: falsos negativos (`.envrc`, `prod.env`, `printenv`, base64) e falsos positivos (`ls .env*`, `api.key.ts`, `id_rsa.pub`) — com a regra de nunca liberar quando o parser do payload falha (`guard-secrets.sh:15` faz o contrário).

### G. `disable-model-invocation: true` no `lancar` (patch)

O pwdev exige por teste que `fleet` e `delegate` só sejam invocados por humano (`tests/test_flow_claude_compat.py:76-82`). No forge, `lancar` (deploy) é a skill que nunca deveria ser acionada pelo modelo por conta própria; `entregar` merece a mesma discussão.

### H. Consulta ao modelo forte como estado (minor + ADR)

Padrão `NEEDS_ADVICE` → pedido estruturado → advisor Opus somente-leitura decide **uma** direção → re-spawn com o conselho e proibição de repetir → conselho `high` vira memória (`pwdev-code/references/spawn-contracts.md:47-78`, `agents/advisor.md`). No forge vira estado `aguardando_conselho` no `ciclo.py` com orçamento próprio, e Rafael como advisor. No pwdev o cap "1 por task" é prosa; aqui seria código.

### I. Validação estrita com duas lentes (patch na skill + contrato)

`/validar --estrito`: um validador FUNCIONAL e um de CONFORMIDADE na mesma onda, cada um com fence própria, veredito = o pior (`pwdev-code/commands/verify.md:55-73`). É o ADR-0033 estendido ao gate de validação.

### J. Runner endurecido para delegar a outro CLI (minor)

`scripts/delegar.py` com allowlist, lock, snapshot de somente-leitura, token de confirmação amarrado ao argv expandido, saída espelhada em arquivo, exit codes com significado (`pwdev-code/scripts/run-agent.sh`, `pwdev-flow/scripts/run-agent.sh`). Dá ao adaptador do `/mobilizar` (ADR-0035) um canal uniforme para lançar worker Codex/OpenCode a partir do Claude Code. Corrigir de saída as duas lacunas deles: checar `git log` (commit indevido) e não deixar segundo caminho sem runner.

### K. Portabilidade Windows dos hooks (patch, quando houver usuário)

`hooks/run-hook.cmd` poliglota + script sem extensão (`pwdev-power/hooks/run-hook.cmd`, `hooks/session-start:5-6`), trocando o `exit /b 0` silencioso por erro visível.

### L. Práticas de design

ADR com seção "Testes exigidos" em tabela nome → setup → asserção literal, e o primeiro passo do plano sendo o teste em RED com a razão da falha registrada (`docs/superpowers/plans/2026-08-16-pwdev-flow-m5.md:98-110`). E a lição negativa: os planos deles listam arquivos que nunca existiram e checkboxes `[ ]` eternos — o teste virou a fonte da verdade e o plano apodreceu. Plano que não é atualizado quando o teste muda deve ser marcado como superado.

## 6. O que explicitamente não adotar

- `guard.sh` por instrução, `--confirm` vindo do modelo, ambiente indeterminado tratado como seguro.
- Protocolos `shared/` sincronizados à mão (o forge gera; continuar gerando).
- Auditoria por `INSERT` que o modelo executa; qualquer contador que vive em arquivo editado pelo modelo.
- Driver por marcadores em texto livre.
- Hooks duplicados entre plugins irmãos: `plugin/` espelhado precisa continuar disparando um único conjunto por sessão.
- "Anatomia de skill" como regra de tamanho: ela não fala de tamanho nem de disclosure; o forge já verifica os dois.

## 7. Sequência sugerida

1. **A + B + F + G** num único ADR-0039 ("o plugin testa o próprio código"): suíte, hooks executados, telemetria de subagente, guardrail de leitura, `disable-model-invocation` no `lancar`. Minor.
2. **C + D + E** num ADR-0040 sobre evidência mecânica de trabalho e posse de processo. Minor, reassina contrato.
3. **H, I, J** como ADRs separados quando houver demanda; **K** quando houver usuário Windows.
