# Loops de correção — crítica, validação e revisão

Material de apoio da skill `entregar`. Leia quando o `ciclo.py estado` devolver
`criticando`, `corrigindo_spec`, `corrigindo_validacao`, `provando`, `corrigindo_revisao` ou
`revisando` — aqui está o detalhe de cada loop: quem entra na correção, o que reabre,
o que nunca vira workaround e quanta evidência a faixa de raio de explosão exige.

### 3. `especificando` → `criticando` — a crítica adversarial

Escreva a SPEC (passo 6). Depois, **antes de mostrar ao usuário**, ao menos dois
críticos que não a escreveram atacam premissa, requisito, plano e testabilidade
(passo 7). Relatório em `docs/specs/criticas/`, com bloco `kairos-critica`.

`registrar limpa` ou `registrar com_achados` — e o veredicto vem do artefato: o
`ciclo.py` recusa `limpa` contra um relatório que diz o contrário, igual aos
outros dois gates. Achado volta para `corrigindo_spec`, e a crítica reabre.

Por que antes do usuário: um gate humano que recebe SPEC com premissa furada
gasta a atenção dele achando o que dois agentes achariam de graça.

### 6. `validando` / `corrigindo_validacao` — o primeiro loop

Rode `/kairos-forge:validar SPEC-NNN` e registre o veredicto do relatório:
`registrar aprovado`, `registrar aprovado_com_ressalvas` ou `registrar bloqueado`.

Em `corrigindo_validacao`, **não devolva o problema ao usuário**:

1. Para cada achado bloqueante, identifique o agente que o relatório indicou (o
   `/validar` já nomeia: Ricardo em cobertura, Helena em segurança, Carlos em
   dados, e assim por diante).
2. Acione **só os agentes dos achados** — corrigir é cirurgia, não mutirão.
3. Rode o gate do requisito afetado e atualize a célula `verificado:`.
4. `registrar pronto` — o script devolve `validando`.

Quantas rodadas cabem não é decisão sua: o `ciclo.py` conta e escala sozinho.

**`provando` — falta de prova não é falha (ADR-0048).** Quando o bloco da validação diz
`sem_evidencia` igual a `bloqueios`, nenhum bloqueio mostrou falha: o que falta é rodar a
checagem. O ciclo vai para `provando`, e a ordem é a contrária da correção:

1. Rode o comando que prova cada requisito sem evidência, ou acione o Ricardo para
   escrever o teste que o prova. Não mexa no código de produção antes.
2. Atualize a célula `verificado:` com o comando que rodou.
3. `registrar pronto` — a validação reabre. Se a prova falhou, ela mostra a falha, e aí
   sim o próximo bloqueio vai para `corrigindo_validacao`.

A rodada conta no orçamento da validação como qualquer bloqueio.

**Atacar a premissa (ADR-0045).** Se o `ciclo.py` devolver `atacando_premissa_*` — neste
loop ou nos outros dois —, duas correções seguidas falharam sem baixar os achados — e a terceira, escrita no mesmo
embalo, repetiria a mesma suposição. Antes de acionar agente: escreva em uma frase a
premissa que as duas correções compartilharam ("o saldo vem do cache", "a validação roda
no cliente"), diga quais agentes ou componentes sustentam essa suposição e o que muda na
atribuição. Depois, `registrar premissa_escrita --nota "<a premissa>"`; a correção seguinte
parte de outra premissa. Premissa repetida na mesma sequência é recusada.

### 7. `revisando` / `corrigindo_revisao` — o segundo loop

Rode `/kairos-forge:revisar`. Depois: `registrar limpo` (zero 🔴) ou
`registrar critico`. Achados 🟠 e 🟡 viram follow-up no corpo do PR.

Correção de segurança **nunca vira workaround** — se o único caminho for
contornar em vez de corrigir, use `ciclo.py escalar --motivo "..."`.

Depois de corrigir um 🔴, `registrar pronto` leva a **`validando`**, não a
`revisando`. Correção que quebra requisito já validado é o modo de falha
silencioso deste arco — e agora ele está fechado por construção, não por
lembrança.

**A re-revisão presta contas (ADR-0048).** Os 🔴 da revisão bloqueada ficam no estado
como `pendentes_revisao`. Na rodada seguinte, os revisores olham primeiro o diff da
correção e marcam cada pendente em `anteriores` (`resolvido` ou `nao_resolvido`). O
`ciclo.py` recusa `limpo` com pendente sem marca ou ainda `nao_resolvido`; um `critico`
carrega adiante os não resolvidos junto com os 🔴 novos.

### 7.5. Evidência proporcional à faixa (ADR-0031)

O `/revisar` classificou o diff em faixa de raio de explosão. A faixa decide o que basta:

- **Faixa 1** — gates verdes fecham.
- **Faixa 2** — gates verdes **e** trajetória limpa: sem alerta de patinação, sem recusa
  de guardrail registrada, `verificado:` corroborado (`telemetria.py`).
- **Faixa 3** — **para e pergunta.** Escale com `ciclo.py escalar --motivo "faixa 3:
  <o que é irreversível>"`. Não existe pontuação que abra essa faixa; é a mesma fronteira
  do ADR-0024.

A faixa 3 também vale na hora de executar (ADR-0052). No Claude Code, o mod da fábrica faz
a chamada irreversível parar por uma pessoa enquanto o ciclo está aberto, mesmo em modo
automático ou com a ferramenta liberada. O cartão da pausa diz o efeito e o `ciclo.py
escalar` com o motivo. Recusada (ou sem ninguém para perguntar, como no `-p`), a chamada
não roda, e o caminho é esse `escalar`, nunca um comando parecido, um script que embrulhe
a ação ou uma permissão mais larga: o embrulho é exatamente o que a classificação não vê.
No Cursor, a mesma regra chega como recusa com o cartão (ADR-0055): a pergunta de um hook
não chega a uma pessoa no Auto-review, então a chamada já vem recusada. Registre o
`escalar`, mostre o comando à pessoa e espere. Quem roda é ela, no terminal dela, ou ela
liga a pergunta em `.agents/guardrails.json`. Nos outros CLIs não há pausa; a regra é a
mesma, cumprida por você.

A faixa sai no topo do corpo do PR (`painel.py --pr`). Quem revisa precisa saber onde olhar antes de abrir o diff.
