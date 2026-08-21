# Mobilizar no OpenCode e no Cursor

Referência de `/kairos-forge:mobilizar` nesses dois CLIs. O OpenCode foi conferido
contra o código do `sst/opencode`; o Cursor, contra a documentação e o formato que o
próprio plugin já gera.

O quadro (`quadro.py`) é idêntico em todos os CLIs. O que muda aqui é só **como se
lança** e **como se espera**.

---

## OpenCode

### A ferramenta

A tool é `task`, e o campo que escolhe a persona é `subagent_type`:

| Campo | Uso no mobilizar |
|---|---|
| `subagent_type` | o id do agente: `carlos-dba`, `marina-frontend`, … |
| `description` | 3–5 palavras; vira o título da sub-sessão |
| `prompt` | o prompt do teammate (template do Passo 5 da skill) |
| `task_id` | devolvido no retorno; passe de volta para **retomar a mesma sessão** |
| `background` | `true` = assíncrono, notifica ao terminar (veja abaixo) |

### O paralelismo está na forma de chamar

Esta é a parte que se erra por descuido: **uma onda = uma mensagem com várias chamadas
de `task`**. Chamar, esperar o retorno, chamar de novo é execução sequencial com passos
a mais — o time vira fila e ninguém percebe, porque o resultado final é o mesmo, só mais
lento.

`background: true` exige `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true` no ambiente.
Ele serve para você seguir trabalhando enquanto a onda roda; **não é requisito para
paralelismo** — chamadas concorrentes numa mensagem já rodam juntas. Se o flag não
estiver ligado, não force: o modo padrão cobre o fluxo do mobilizar inteiro.

Com `background`, o próprio OpenCode avisa: não durma, não faça polling, não pergunte o
status. Espere a notificação. É a mesma regra do `wait_agent` do Codex — quem faz
polling em worker paralelo transforma coordenação em espera ocupada.

### Retomar em vez de relançar

Quando uma tarefa volta bloqueada e você resolve o bloqueio, **passe o `task_id` de
volta** em vez de abrir um subagent novo. O worker continua com o contexto que já tinha
— ele não precisa reler o que já leu. Subagent novo para a mesma tarefa é a rodada de
correção pagando o preço de um começo do zero.

### Instalação das personas

O OpenCode varre `{agent,agents}/**/*.md` no diretório de config e **só oferece à tool
`task` os agentes com `mode: subagent`**. Por isso não basta copiar `agents/` cru: a
persona carrega, mas não fica delegável, e a onda paralela simplesmente não acontece.

Use os arquivos gerados:

```bash
mkdir -p .opencode/agent
cp <plugin>/.opencode/agent/*.md .opencode/agent/     # ou no config global
```

### A allow-list atravessa inteira — e só aqui

Cada agente gerado traz a allow-list do canônico traduzida para `permission`, que o
OpenCode **aplica de fato**:

```yaml
mode: subagent
permission:
  edit: deny      # agente sem Write/Edit no canônico
  bash: allow
  task: deny      # decompor é da Laura
```

Vale registrar a diferença, porque muda o que você pode prometer ao usuário:

| CLI | "Helena não modifica código" é… |
|---|---|
| Claude Code | fronteira (allow-list enforced) |
| **OpenCode** | **fronteira (`edit: deny` enforced)** |
| Codex | instrução (`apply_patch` sobrevive a qualquer redução) |
| Cursor | instrução (`readonly` degrada a allow-list) |

`task: deny` em todos os teammates é deliberado: sub-time dentro de teammate é como o
file ownership vira ficção. É o mesmo efeito do `max_depth = 1` do Codex, aqui por
agente. O teto de aninhamento global do OpenCode é `subagent_depth` (default 1).

---

## Cursor

### O modelo é diferente: você não lança, você descreve

Cursor não expõe uma tool de spawn para você chamar. O agente principal lê a tarefa,
escolhe subagents de `.cursor/agents/` e os executa **em paralelo**, mostrando cada um na
barra lateral. Desde a 2.5 um subagent pode abrir filhos, mas o neto não abre bisneto.

Na prática, o laço do mobilizar vira:

1. `quadro.py prontas <slug>` — o quadro decide a onda, como sempre.
2. Descreva a onda inteira **de uma vez**, nomeando o subagent de cada tarefa e a posse
   de arquivo dela. Descrever uma tarefa por vez é o que faz o Cursor serializar.
3. `quadro.py iniciar` para cada uma.
4. Conforme os subagents respondem, `quadro.py concluir` / `bloquear`.

### O limite que muda o fluxo

**Não há canal para falar com um subagent em voo.** No Claude Code e no Codex você
corrige rota com uma mensagem; aqui, não. Duas consequências práticas:

- **Contexto incompleto custa a tarefa inteira, não uma mensagem.** Capriche no prompt
  inicial: posse, "Pronto quando", gate e o subgrafo das entidades que a tarefa toca.
- **Bloqueio resolvido = subagent novo** com o contexto completo, não uma correção no
  que está rodando. Registre a rodada no quadro (`bloquear` → `reabrir`) para o
  orçamento continuar valendo.

As personas já estão em `.cursor/agents/` (geradas pelo sync). A allow-list degrada para
`readonly: true` quando o canônico não tem ferramenta de escrita — é instrução, não
fronteira; onde a supervisão humana sai do caminho, use worktree (Passo 6.1 da skill).

---

## Erros comuns

| Sintoma | CLI | Causa |
|---|---|---|
| A onda roda em fila, não em paralelo | OpenCode | uma chamada `task` por mensagem — mande todas juntas |
| A onda roda em fila, não em paralelo | Cursor | uma tarefa descrita por vez — descreva a onda inteira |
| `Unknown agent type: <id>` | OpenCode | agentes sem `mode: subagent`, ou fora de `{agent,agents}/` |
| `background` recusado | OpenCode | falta `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true` — não é necessário |
| Rodada de correção começa do zero | OpenCode | relançou em vez de passar o `task_id` |
| Subagent ignora a posse de arquivo | Cursor | é instrução, não fronteira — worktree quando ninguém revisa |
