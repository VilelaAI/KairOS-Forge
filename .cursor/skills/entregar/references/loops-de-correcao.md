# Loops de correção — crítica, validação e revisão

Material de apoio da skill `entregar`. Leia quando o `ciclo.py estado` devolver
`criticando`, `corrigindo_spec`, `corrigindo_validacao`, `corrigindo_revisao` ou
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

### 7.5. Evidência proporcional à faixa (ADR-0031)

O `/revisar` classificou o diff em faixa de raio de explosão. A faixa decide o que basta:

- **Faixa 1** — gates verdes fecham.
- **Faixa 2** — gates verdes **e** trajetória limpa: sem alerta de patinação, sem recusa
  de guardrail registrada, `verificado:` corroborado (`telemetria.py`).
- **Faixa 3** — **para e pergunta.** Escale com `ciclo.py escalar --motivo "faixa 3:
  <o que é irreversível>"`. Não existe pontuação que abra essa faixa; é a mesma fronteira
  do ADR-0024.

Diga a faixa no corpo do PR. Quem revisa precisa saber onde olhar antes de abrir o diff.
