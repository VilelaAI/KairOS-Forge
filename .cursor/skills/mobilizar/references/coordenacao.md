# Coordenação avançada — isolamento, memória compartilhada e o ciclo de ondas

Referência dos Passos 6.1, 6.2, 6.5 e 7 de `/kairos-forge:mobilizar`: quando a posse por
prompt deixa de bastar e vira worktree, o que cada tarefa precisa declarar para ser
desfeita, como o grafo serve de memória compartilhada do
time, e a prosa completa do ciclo de coordenação — por que `varrer`, `compensar`,
`reabrir` e `encerrar` recusam o que recusam, fan-in em camadas e o modelo do relatório
final. Leia ao decidir isolamento (antes de lançar) e ao fechar cada onda.

## Passo 6.1 — Isolamento: prompt ou worktree? (ADR-0024)

File ownership por prompt é **disciplina**, não fronteira: o teammate obedece porque foi
instruído. Isso basta enquanto um humano lê o diff antes do merge. Não basta quando
ninguém lê.

| Situação | Isolamento exigido |
|---|---|
| Humano vai revisar o PR antes do merge (L3) | **Prompt** — posse declarada no template |
| Execução autônoma sem revisão humana (L4), ou 3+ teammates em áreas adjacentes | **Worktree** — fronteira física |

```bash
git worktree add .worktrees/<teammate> -b forge/<slug>-<teammate>
# ... teammate trabalha e commita só ali ...
git merge --no-ff forge/<slug>-<teammate>     # Laura integra, uma de cada vez
git worktree remove .worktrees/<teammate>
```

Conflito deixa de ser violação de disciplina e vira **impossibilidade física**. O custo
é real (setup por teammate, merges sequenciais, `.worktrees/` no `.gitignore`) e por
isso o default não é worktree: pague quando a supervisão humana sair do caminho.

## Passo 6.2 — Reversibilidade declarada por tarefa

Toda task carrega **como se desfaz**, no `--reverter`, anotado **antes** de executar:

- Código: o commit é a unidade de revert (`git revert <sha>`).
- Migration: o rollback precisa existir e ter sido **rodado** em ambiente não produtivo.
- Config ou infra: o valor anterior anotado na tarefa.

Tarefa cujo revert você não consegue escrever **não é autônoma**: é irreversível, e
irreversível para no usuário. O quadro avisa quando falta — descobrir o comando de volta
durante o incidente é o anti-padrão que essa anotação existe para matar.

## Passo 6.5 — Grafo como memória compartilhada (se existir)

Se o projeto tem `.agents/grafo/`, ele é a memória compartilhada do time — o análogo
estrutural do *shared memory* no padrão orquestrador–workers (ADR-0009):

- **Na largada:** inclua no prompt de cada teammate o subgrafo k=2 das entidades que a
  tarefa dele toca. Substitui parágrafos de contexto por fatos com proveniência.
- **Durante:** teammate que precisa de fato fora do próprio contexto consulta o grafo em
  vez de pedir que você repasse contexto de outro. Seu contexto fica pequeno; o estado
  compartilhado vive no grafo.
- **No encerramento:** consolide os fatos novos reportados e rode
  `/kairos-forge:mapear-conhecimento atualizar`.

## Passo 7 — Coordenar como Tech Lead

1. **Registre o que voltar.** Teammate concluiu:

   ```bash
   quadro.py concluir forge-<slug> T1 --evidencia "<arquivos, requisitos, gate>" --gate-ok
   ```

   Sem evidência, ou sem dizer o que houve com o gate (`--gate-ok` ou
   `--gate-pulado "motivo"`), o quadro recusa. Concluir em silêncio sobre o gate é
   exatamente o resumo fluente por cima de resultado parcial que ele existe para impedir.
   Ao concluir, ele já diz o que a conclusão liberou — essa é a sua próxima onda.

2. **Worker que não responde tem prazo.** Antes de cada onda nova, varra:

   ```bash
   quadro.py varrer forge-<slug>        # --dry-run para só ver
   ```

   Tarefa em voo além do tempo limite vira `bloqueada` e **devolve a vaga da onda**.
   Sem isso, um worker que morreu sem avisar segura a vaga para sempre: o teto nunca
   libera, a onda seguinte nunca sai, e nada nunca dá erro — travar em silêncio é pior
   que falhar alto. Ao reabrir, decida antes: o worker morreu (relance) ou a tarefa é
   grande demais para o limite (aumente o `--tempo-limite` dela).

3. **Falha tardia compensa, não reinicia (ADR-0036).** Quando uma tarefa **já
   concluída** se revela inválida — mudou a premissa, o requisito, o schema — não
   declare lacuna nem refaça tudo:

   ```bash
   quadro.py compensar forge-<slug> T1 --motivo "..."            # mostra o plano
   quadro.py compensar forge-<slug> T1 --motivo "..." --aplicar   # executa
   ```

   O quadro devolve **T1 e só o que foi construído sobre ela**, na ordem inversa da
   execução, cada uma com o `--reverter` que você declarou no Passo 4. O que não
   dependia de T1 permanece concluído — é essa preservação que separa compensação de
   reinício. Execute os `desfazer` **nessa ordem** antes de relançar: derrubar a base
   antes do que se apoia nela deixa o repositório num estado que ninguém desenhou.

   Se alguma tarefa do plano não declarou `--reverter`, o plano inteiro é recusado.
   Compensação pela metade é pior que não ter começado, e tarefa irreversível para no
   usuário (ADR-0024).

4. **Bloqueio é estado, não conversa.** `quadro.py bloquear <slug> T3 --motivo "..."`.
   Resolvido, `reabrir` devolve à fila e **queima uma rodada**. Esgotado o orçamento de
   rodadas daquela tarefa, `reabrir` recusa: escale ou encerre com a lacuna declarada.
   Não existe "mais uma rodadinha".

5. **Checkpoint ao fim de cada onda.** A onda é a unidade que o quadro já controla
   (`prontas` decide a próxima). Valide alinhamento com a SPEC e renderize:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/painel.py SPEC-NNN   # SPEC + ciclo + quadro
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/quadro.py estado forge-<slug>
   ```

   O quadro é **renderização do estado canônico**, nunca estado paralelo. Card só entra
   em "Pronto" com gate rodado — os cards andam porque os agentes construíram e
   provaram, não porque alguém arrastou.

6. **Fan-in em camadas.** Com mais de ~6 teammates, não consolide todos os outputs crus
   de uma vez. Agrupe por domínio, resuma cada grupo, e sintetize **os resumos**.

7. **Encerramento.** Quando o quadro disser completo:

   ```bash
   quadro.py ledger forge-<slug>       # a tabela do relatório, montada do estado
   quadro.py encerrar forge-<slug>
   ```

   `encerrar` **recusa** quadro com tarefa aberta sem lacuna declarada
   (`--lacuna "T7: motivo"`). Em cadeia, uma falha para tudo e todo mundo vê; em grafo,
   o nó que falhou some num relatório que parece completo — é esse relatório que a
   recusa impede. Depois, encerre os workers (`shutdown_request` / `close_agent`) e
   reporte:

   ```
   ✅ Time forge-<slug>: N de N tarefas planejadas concluídas em M ondas.
   (Se N < planejado: liste cada tarefa faltante e por quê — nunca omita lacuna.)

   📋 Quadro final: Pronto: N ✓gate | Em progresso: N | A fazer: N (NN%)
   💳 Ledger: <saída de `quadro.py ledger`>

   Resumo:
   - Migrations: 1 nova (Carlos)   - Endpoints: 2 (Lucas)
   - Componentes: 3 (Marina + Pablo) - Testes: 5 (Ricardo)

   Pendências:
   - Validação contra SPEC ainda não rodou. Recomendo: /kairos-forge:validar SPEC-NNN
   - Auditoria de segurança não rodou. Depois da validação: /kairos-forge:revisar
   - Grafo sem os fatos deste ciclo: /kairos-forge:mapear-conhecimento atualizar
   - PR ainda não aberto. Quer que eu chame o Marcos pra abrir?
   ```
