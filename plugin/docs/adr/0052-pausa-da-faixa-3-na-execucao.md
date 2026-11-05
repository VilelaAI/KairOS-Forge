# ADR-0052 — A pausa da faixa 3 na execução

- **Status:** aceito
- **Data:** 2026-11-05
- **Versão:** v0.45.0

## Contexto

A faixa 3 do ADR-0031 é a mudança difícil de reverter: migration destrutiva, deleção de
dados, escrita em produção, dinheiro, credencial. A regra é "humano decide, sempre".

Até aqui, essa decisão acontecia depois do fato:
- o `/revisar` classifica o diff;
- o `/entregar` escala o ciclo com `ciclo.py escalar --motivo "faixa 3: ..."`;
- o corpo do PR põe a faixa no topo.

O que a revisão vê é o código. Mas na fase `construindo` o agente do arco também executa.
Em modo automático, ou com uma regra salva como `Bash(terraform:*)`, ele podia aplicar
infraestrutura, publicar um pacote ou migrar um banco remoto antes de qualquer revisão. O
ADR-0024 já dizia que "tarefa cujo revert você não consegue escrever não é autônoma", mas
nada segurava a ação na hora.

O guardrail (ADR-0022/0042) bloqueia de vez o que é destrutivo sem discussão: `DROP TABLE`,
`rm -rf /`, force-push na `main`. Faltava o meio-termo: a ação legítima numa entrega de
faixa 3, que não se bloqueia mas também não roda sem uma pessoa ver.

## Decisão

No arco, a chamada cujo efeito um revert não desfaz **para por uma pessoa**, mesmo em
`bypassPermissions` e mesmo com uma regra salva que a liberaria.

### A regra mora no Python: `guardrail.py faixa3`

Um modo novo do guardrail. Lê o mesmo payload dos hooks e responde em JSON se a chamada
para e por quê. Nunca bloqueia sozinho e sai sempre com exit 0.

- **O que para.** O efeito sai do repositório de um jeito que um revert não desfaz. São 37
  padrões, cada um com o efeito escrito por extenso:
  - infraestrutura aplicada (`terraform apply`, `pulumi up`, `kubectl apply`, `helm upgrade`);
  - deploy (Fly, Vercel `--prod`, Netlify `--prod`, Heroku, `gcloud run deploy`, `make deploy`,
    `npm run deploy`, `./scripts/deploy.sh`);
  - pacote, imagem ou tag publicados;
  - push direto na branch principal, que pula o PR que fecha o arco;
  - segredo mudado (`gh secret set`, Vault);
  - recurso de nuvem criado, mudado ou apagado (AWS, Google Cloud, Azure, DigitalOcean);
  - chave de pagamento de produção, ou dinheiro movido no Stripe;
  - `prisma migrate deploy` e `supabase db push`.

  Também para: migration com marca de produção ou banco remoto, cliente de banco
  conectado fora da máquina e ferramenta de MCP cujo nome diz deploy, migration,
  `execute_sql`, delete, merge, refund ou mensagem enviada.
- **O que passa.** Precisão vale mais que cobertura: pausa que pergunta toda hora é pausa
  que a pessoa aprende a aprovar sem ler.
  - Ensaio: `--dry-run`, `--check`, `terraform plan`.
  - Migration em banco local, como `alembic upgrade head`, `bin/rails db:migrate` ou
    `prisma migrate dev`.
  - Leitura, comando comum e push para branch própria.
  - A análise é trecho a trecho: em `npm publish --dry-run && npm publish`, o segundo trecho
    para.
- **Quando.** Só com a autonomia ligada:
  - com um ciclo do `/entregar` aberto (fora de `encerrado` e `escalado`);
  - ou com um quadro do `/mobilizar` em andamento.

  Fora do arco, a pessoa já está no circuito pelas permissões de sempre.
  `"faixa_3": "sempre"` em `.agents/guardrails.json` estende a pausa para fora dele. Esse é
  o arquivo que só o humano escreve.
- **O cartão.** A pergunta explica o que a chamada faz e por que parou, antes de pedir a
  decisão. A ideia é do PDD Kit (GitHub Next, nov/2026). O texto diz:
  - o efeito, e que um revert no código não o desfaz;
  - o ciclo e o estado em que ele está;
  - o que a fábrica faz se a pessoa recusar: registra o `ciclo.py escalar` com o motivo e
    espera.
- **A trajetória.** Cada pausa vira um evento `tipo: pausa` com o efeito, o comando e a
  SPEC. O `telemetria.py resumo` conta as pausas por efeito, à parte das recusas.

### Quem pergunta é um mod: `hooks/pausa.ts`

A pausa engancha `tool.check` no Bash e nas ferramentas de MCP.

1. Primeiro lê a decisão de baixo: o modo e as regras.
2. Se for recusa, ela fica como está, e o guardrail nem é chamado.
3. Se não for recusa, pergunta ao `guardrail.py faixa3`. Se a chamada para, a resposta vira
   `ask` com o cartão.
4. O mod nunca devolve `allow`.

Tem de ser um mod porque, pelos tipos do Claude Code, o `ask` de um mod é de uma pessoa:
- nenhum classificador do modo automático o aprova;
- uma regra salva para a ferramenta inteira não o dispensa;
- onde ninguém pode ser perguntado (o `-p`, um host sem pessoa), ele vira recusa, e o
  motivo chega ao modelo.

O `ask` de um hook de settings vai para quem decide no modo, e no modo automático esse
alguém pode ser o classificador.

Se o Python não roda ou devolve algo ilegível, vale a decisão de sempre, sem pausa. Sem
Python não há guardrail nenhum da fábrica, e um mod que travasse tudo por falha própria
seria pior.

O `hooks/hooks.json` passa a nomear `./mod.ts`, que liga o painel (ADR-0051) e a pausa.

### No `/entregar`

A skill ganha uma regra: chamada parada ou recusada pela pausa não se contorna. O agente não
troca de comando, não embrulha a ação num script e não escala a permissão. Ele registra o
`ciclo.py escalar` que o cartão traz e espera. O embrulho num script é justamente o que a
classificação não vê, e por isso a regra está escrita.

## Prova

Rodei um Claude Code 2.1.318 de verdade com uma API falsa local, que responde como um modelo
pedindo `terraform apply -auto-approve`, e um `terraform` falso no PATH que grava uma marca
quando roda:

| Cenário | O `terraform` rodou? | O que o modelo recebeu |
|---|---|---|
| Sem ciclo, `bypassPermissions` | sim | `Apply complete!` |
| Ciclo em `construindo`, `bypassPermissions` | **não** | o cartão, inteiro |
| Ciclo em `construindo`, modo padrão com `--allowedTools "Bash(terraform:*)"` | **não** | o cartão |
| Ciclo em `construindo`, `terraform plan` | sim | normal |
| Ciclo em `construindo`, `npm publish` com `--allowedTools "Bash(npm:*)"` | **não** | o cartão ("publica um pacote") |

O evento de cada pausa saiu na trajetória com a sessão e a SPEC.

A pergunta numa superfície interativa, com uma pessoa respondendo, não foi exercitada. O kit
de teste não deixa um teste fazer o papel de uma pessoa que libera a chamada.

## Consequências

- **Guardrail.** O `guardrail.py` ganha o modo `faixa3` e a chave `"faixa_3": "sempre"`.
  `test_faixa3.py` tem 17 testes:
  - 48 comandos que param e 43 que passam;
  - o contexto (ciclo, quadro, `sempre`, encerrado, escalado, o `cwd` do payload);
  - o cartão, o evento, a falha aberta e a contagem no `resumo`.
- **Mod.** `tests/pausa.test.ts` tem 9 testes:
  - o `ask` por cima do `allow` e do `ask` do modo;
  - a recusa que fica recusa;
  - o MCP que passa pelo guardrail e as ferramentas de arquivo que nem chegam;
  - o atalho do `isReadOnly`;
  - a pausa sem cartão, que ainda pergunta, com um texto padrão;
  - a falha do Python e a chamada recusada sem pessoa.

  O `test_mod_painel.py` passa a exigir, no código, que nenhum mod devolva `allow` e que a
  pausa só diga `ask`.
- **Mutação.** Os 7 estragos plantados à mão na pausa são acusados. A mutação automática
  do `qualidade.py`, com o `claude plugin test` e as suítes Python como comando, deixou 9 de
  51 mutantes vivos na primeira rodada. Os que eram lacuna viraram teste. A rodada final
  mata 42 de 46, e os 4 que sobram são equivalentes: dois literais de tipo apagados na
  compilação, um `[]` que o chamador lê como `None` e o `ensure_ascii` do JSON.
- **Pausa a mais.** Tudo o que a classificação acha irreversível pergunta, durante o arco,
  mesmo quando a pessoa já tinha liberado a ferramenta. É o preço da regra "humano decide,
  sempre", pago só dentro do arco.
- **O que a classificação não vê.** Ação irreversível escondida atrás de um nome sem pista
  (`make all`, `./ci.sh`, um script Python) não para. O alvo de make ou npm com
  deploy/publish/release no nome e o script chamado `deploy`, `release` ou `publish` param.
  O resto fica para a regra da skill e para a revisão.
- **Só no Claude Code.** Codex, OpenCode, Cursor e Tucano não carregam mods. O Cursor tem
  `permission: "ask"` no dialeto de hooks dele, e o mesmo `faixa3` poderia alimentá-lo: fica
  para um próximo passo.

## Alternativas consideradas

- **Bloquear de vez, no guardrail.** Recusado. São ações legítimas numa entrega de faixa 3,
  e o bloqueio empurraria a pessoa a desligar a regra (ADR-0030).
- **`permissionDecision: "ask"` no hook de settings.** Recusado como caminho principal.
  Esse `ask` vai para quem decide no modo, e no modo automático pode ser o classificador.
- **Pausar sempre, fora do arco também.** Recusado como padrão. Fora do arco, a pessoa já
  responde às permissões. Fica disponível com `"faixa_3": "sempre"`.
- **A classificação em TypeScript, dentro do mod.** Recusado. Seria uma segunda regra fora
  dos testes em Python, sem cobertura medida e longe do guardrail que já conhece o ciclo,
  o quadro e o checkout principal.
- **Confiar no `isReadOnly` das ferramentas de MCP.** Só como atalho para pular a consulta.
  O `isReadOnly` é a palavra do servidor, então a pausa decide pelo nome da ferramenta.
