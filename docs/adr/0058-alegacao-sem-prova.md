# ADR-0058 — Alegação sem prova

- **Status:** aceito
- **Data:** 2026-11-18
- **Versão:** v0.51.0

## Contexto

O [corno-skills](https://github.com/adlernatanael/corno-skills) (corno.dev) é um conjunto
de skills em português feitas para o agente terminar de verdade. O repositório não
declara licença: daqui sai a ideia, não o texto, como no ub-mode (ADR-0045). Das doze
skills, só uma traz mecanismo, e não só texto: a `corno-confere`. O hook dela faz duas
coisas:

- **No `Stop`:** quando o turno editou arquivos e a última resposta diz "pronto", "corrigi"
  ou "os testes passam", ele bloqueia uma vez e manda o agente conferir o pedido item por
  item.
- **No `UserPromptSubmit`:** quando a pessoa pergunta "faltou algo?" ou "terminou?", ele
  injeta essa conferência.

A fábrica tinha o lado da evidência, mas não o da frase:

- **O gate de parada (ADR-0042)** pergunta se rodou gate verde depois da escrita. Em `aviso`,
  ele fala só com a pessoa.
- **O `corroborar` do `/validar` (ADR-0021)** confere o `verificado:` da SPEC contra a
  trajetória.

Nenhum dos dois olhava o que o agente afirmou na conversa. Numa sessão real com o plugin
(abaixo), o agente escreveu `src/app.py`, disse "Pronto, os testes passam." sem rodar
teste nenhum, e encerrou. A afirmação ficou de pé, e só a pessoa leu o aviso da parada.

## Decisão

### A afirmação é conferida contra a trajetória (classe `alegacao`)

No `Stop`, antes da parada, a última resposta do modelo (`last_assistant_message`, ou a
última resposta no transcript quando o campo não vem) é lida frase a frase, sem bloco de
código e sem trecho entre crases.

- **Afirmação de gate verde.** Conta a frase que diz que um tipo de gate passou:
  - testes ("os testes passam", "12 testes passando", "tests pass");
  - lint ("o lint está limpo");
  - tipos ("mypy sem erros");
  - build ("o build passou", "compila sem erros");
  - todos ("tudo verde", "all green").
- **O que fica de fora:**
  - a pergunta;
  - a frase com negação antes da afirmação;
  - o tempo passado e o subjuntivo ("passavam", "se passarem", "devem passar");
  - a saída colada entre crases ou num bloco de código;
  - o que só o CI ou o servidor mostram, porque está fora da trajetória local.
- **O que a desmente**, olhando os gates que rodaram depois da última escrita de produção
  (sem escrita, a sessão inteira; escrita em pasta `sem_gate` não move a referência):
  - nenhum gate daquele tipo rodou;
  - o último daquele tipo rodou vermelho;
  - ele ainda roda em background, com o resultado lido como no ADR-0042, emenda v0.50.8.
- **O que não a desmente:** um gate cuja saída não dá para classificar (`ok` indeterminado).
  O guardrail não acusa o que não consegue afirmar.

A recusa vai para a trajetória como `alegacao` e conta no `telemetria.py resumo` como as
outras classes.

**Nasce em `bloqueio`, ao contrário da parada:**

- **O bloqueio é preciso.** Ele exige uma afirmação explícita que o registro desmente. A
  parada (ADR-0042) dispara em qualquer sessão que escreveu sem gate, e por isso nasceu em
  `aviso`.
- **Errar custa pouco.** Num falso positivo, o custo é um turno, e o texto deixa a saída
  honesta: "se não dá para rodar aqui, ou se quem rodou foi a pessoa, diga isso em vez de
  afirmar que passa".
- **Nunca bloqueia duas vezes na mesma parada** (`stop_hook_active`).
- **Pode ser rebaixada.** `{"modos": {"alegacao": "aviso"}}` faz o texto falar com a pessoa.

A frase do agente vai para o modelo junto com o que a desmente, e é ele quem roda o gate
ou corrige a resposta. No Cursor, o mesmo bloqueio sai como `followup_message`.

### A conferência quando a pessoa pergunta (modo `conferir`)

No `UserPromptSubmit`, quando a pessoa pergunta se falta algo ("faltou algo?",
"terminou?", "tá pronto?", "confere aí", "is it done?"), o modelo recebe como contexto a
conferência item a item. Pede:

- a lista do que foi pedido, com as palavras da pessoa, incluindo o que chegou no meio do
  trabalho e os detalhes ditos de passagem;
- ao lado de cada item, o que foi entregue, lido agora e não lembrado;
- uma prova rodada depois da última mudança;
- e, na resposta, o que ficou diferente, o que falta e o que não deu para verificar.

É só contexto, nunca bloqueio. No Cursor, não responde.

### O classificador de gate reconhece mais corredores de teste

`python3 -m unittest` (o da própria fábrica), `tox`, `nox`, `node --test` e `deno test`
não eram gate. Sem isso, "os testes passam" depois de um `unittest` verde seria acusado à
toa.

## O que fica de fora da corno-confere

- **A conferência a cada "pronto".** O hook deles bloqueia toda resposta que diz "pronto"
  depois de uma edição, mesmo com o teste verde rodado. Aqui só volta a frase que o registro
  desmente. A conferência larga fica para quando a pessoa pede ("faltou algo?") e para o
  `/validar`, que já confere a SPEC item por item.
- **O texto.** As frases e a lista de "desculpas" são deles. Os textos daqui são próprios.
- **As outras skills.** A `corno-revisa` (separar o que o PR introduziu do que já existia),
  a `corno-investiga` (método de investigação de bug), a `corno-pesquisa` (fonte primária
  salva no repositório) e o "Pronto quando" em cada skill ficaram anotados como próximos
  passos. As de negócio e as pessoais não cabem numa fábrica de software.

## Prova

- **O Claude Code 2.1.319 com o plugin de verdade**, a API falsa e uma sessão interativa no
  tmux. O agente escreve `src/app.py` e responde "Pronto, os testes passam." sem ter rodado
  nada:
  - Na `main` (v0.50.8), só aparece o aviso da parada para a pessoa. A afirmação fica.
  - Nesta versão, o `Stop` bloqueia ("Stop hook reported a problem… alegação sem prova…
    nenhum rodou depois da última escrita"), e o pedido seguinte à API traz o texto como
    "Stop hook feedback". O agente roda o `pytest`, que entra verde na trajetória, responde
    com o resultado e encerra sem aviso. A recusa fica na trajetória como `alegacao`, em
    `bloqueio`.
- **O `conferir`, na mesma bancada.** Com o prompt "terminou? faltou algo?", o primeiro
  pedido à API traz "UserPromptSubmit hook additional context: A pessoa quer saber se falta
  algo…" nesta versão, e nada na `main`.
- **`scripts/tests/test_alegacao.py`**, com 26 testes. Cobrem:
  - o que é afirmação e o que não é: pergunta, negação, passado, subjuntivo, crases, bloco
    de código e CI;
  - a frase inteira e curta;
  - o que desmente: nenhum gate, de outro tipo, o último vermelho, rodando em background;
  - o "tudo verde", o indeterminado, que não desmente, e a pasta sem gate;
  - na parada: o bloqueio com o texto e a recusa, o verde que passa calado, o `aviso` para
    a pessoa, o `stop_hook_active`, a parada que segue como antes sem afirmação, o verde em
    background lido do transcript, a resposta lida do transcript sem o campo, o Cursor e o
    processo inteiro;
  - a frase da pessoa no transcript, que não é alegação do agente;
  - o `conferir`: as perguntas, o resto calado, o Cursor e a fiação no `hooks.json`;
  - os corredores de teste novos.
- **Qualidade nas funções tocadas.**
  - CRAP: as 13 ficam abaixo de 10, depois de quebrar a `falta_prova` e a leitura do
    transcript.
  - Duplicação: nenhum par. Os textos da alegação viraram um modelo por modo.
  - Mutação: a primeira rodada matou 37 de 38. A segunda, depois do refactor, matou 41 de
    42. Os dois sobreviventes eram casos sem teste (o transcript sem resposta do modelo e a
    frase da pessoa) e viraram teste. Conferi à mão que o último reprova o mutante.
- **Teste alterado.** O `test_rm_fora_do_projeto` dependia de `TMPDIR` não estar definido.
  O container desta sessão o define como `/tmp`, e o sandbox, que vive em `/tmp`, passava
  como temporário. O teste agora zera a variável no trecho que cobra o vizinho, e passa com
  e sem ela.

## Limites

- **A afirmação é lida por padrão de frase.** Uma afirmação fora dos padrões ("está tudo
  funcionando") não é conferida. Também não é a generalidade "pronto", que a parada já cobre
  quando falta gate.
- **Um gate cuja saída não se classifica** não desmente nada. A regra aceita o falso
  negativo para não acusar à toa.
- **O que a pessoa rodou no terminal dela** não está na trajetória. O texto do bloqueio
  manda o agente dizer isso em vez de afirmar.
- **Só no Claude Code e no Cursor**, que têm hook de parada. Codex e OpenCode não mudam.
