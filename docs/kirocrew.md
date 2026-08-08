# A fábrica dentro do Kiro Crew

> Guia de integração entre o kairos-forge e o [Kiro Crew](https://github.com/kirodotdev/KiroCrew)
> (Apache 2.0, AWS/Kiro). Decisão em [ADR-0035](adr/0035-suporte-kiro-e-fronteira-kirocrew.md).

## A divisão

O nome "KiroCrew" junta duas coisas que respondem a perguntas diferentes:

| | O que é | Como o forge trata |
|---|---|---|
| **kiro-cli** | O agente (terminal e ACP) | **Um CLI** — alvo do sync, como Claude Code e Codex |
| **Kiro Crew** | O Gateway: sessões, memória, agenda, aprovações, política, dashboard, Slack/Telegram | **Um orquestrador** — consome o contrato, como Hermes e kairos-symphony |

A regra que organiza tudo:

> **O Gateway é o *quando/onde*. A fábrica é o *como*.**
> Ele responde "o agente continua depois que você fecha o terminal".
> Ela responde "o que ele fez presta".

São ortogonais. Usar os dois juntos não é redundância — é cada um fazendo o que
o outro deliberadamente não faz.

## Instalação

```bash
git clone https://github.com/VilelaAI/kairos-forge.git

# Global — o Crew procura configs de agente em ~/.kiro/agents/
cp -R kairos-forge/plugin/.kiro/* ~/.kiro/
```

Confira que as personas apareceram:

```bash
ls ~/.kiro/agents/ | head          # laura-tech-lead.json, rafael-staff.json, …
kiro-cli chat --agent laura-tech-lead
```

No Crew, cada agente roda como `kiro-cli acp --agent <id>`. Laura
(`laura-tech-lead`) é o ponto de entrada: ela analisa a tarefa e decide quem entra.

## Os encaixes que valem a pena

| Gatilho do Crew | Skill da fábrica | Para quê |
|---|---|---|
| `kirocrew cron` | `/auditar` | Auditoria semanal em 6 dimensões |
| Webhook de PR | `/revisar` | Revisão com faixa de raio de explosão |
| CI vermelho | `/entregar` (retomada) | Correção roteada ao agente responsável |
| `kirocrew run TASK.md` | `/entregar` | O arco fechado com orçamento declarado |

É o mesmo desenho de `templates/ci/` (ADR-0026), com um Gateway no lugar do
GitHub Actions — e melhor num ponto: a fronteira humana vira interativa
(aprovação no Slack/Telegram) em vez de virar um PR parado.

## O ponto de amarração: o contrato, não a prosa

O Crew **não** deve inferir estado lendo o que o agente escreveu. O arco expõe
uma superfície pública versionada (ADR-0034):

```bash
python3 ~/.kiro/scripts/ciclo.py estado --json
```

```json
{
  "spec": "SPEC-014",
  "estado": "aguardando_aprovacao",
  "terminal": false,
  "aguardando_humano": true,
  "gate": "revisao",
  "resultados_validos": ["limpo", "ajustes"]
}
```

Use os campos **derivados**, não o nome do estado:

- `aguardando_humano: true` → o Gateway segura e pede aprovação na superfície
  de chat. É aqui que a fronteira de aprovação do ADR-0023 se materializa.
- `terminal: true` → o arco acabou; encerre a sessão.
- `resultados_validos` → as únicas transições aceitas. Não invente nomes.

Comparar string de estado (`if estado == "revisando"`) é o acoplamento que o
ADR-0034 existe para evitar: o conjunto de estados muda, os campos derivados não.

## Guardrails: dois gates, camadas diferentes

O Crew avalia **todo** tool call no gate de PreToolUse *dele* antes de deixar o
kiro-cli rodar. O forge tem o `guardrail.py`. Não competem:

| Camada | Quem | O que barra |
|---|---|---|
| Runtime / OS | Kiro Crew | Padrões de deny, caminhos sensíveis, sandbox, redação de credencial |
| Semântica | `guardrail.py` | Integridade da SPEC, PR fora de estado, contrato de relatório, caminho sagrado |

O segundo não existe no Crew porque depende de saber o que é uma SPEC e o que é
um veredicto — conhecimento da fábrica, não do Gateway.

**Montagem recomendada:** pendure o modo CLI no gate do Gateway.

```bash
python3 ~/.kiro/scripts/guardrail.py verificar .
```

Isso vale independente de os hooks do kiro-cli dispararem sob ACP — ver a
ressalva abaixo.

## Memória: quem manda em quê

O Crew mantém memória, lições e **sintetiza skills de padrões repetidos**. O
forge tem três camadas (ADR-0009/0010) com o repositório como fonte da verdade.
Se os dois escrevem, há duas verdades — e a versionada perde para a que o
Gateway reescreve sozinho.

A fronteira, decidida no ADR-0035:

| Camada | Dono | Onde vive |
|---|---|---|
| Episódica (sessão, handoff) | **Kiro Crew** | Estado do Gateway |
| Curada (decisões, contextos) | **forge** | `decisoes/`, `.agents/`, `contextos/` no repo |
| Estrutural (grafo) | **forge** | `.agents/grafo/` |

Skill sintetizada pelo Gateway **não** entra em `skills/`. Lá se entra por ADR,
com teto de 500 linhas (ADR-0027). Se quiser promover um padrão que o Crew
descobriu, abra o ADR — é barato e mantém uma verdade só.

## Ressalva honesta

Não foi confirmado em execução se os hooks do kiro-cli disparam em sessões
**ACP** — que é exatamente como o Crew dirige o CLI. Há
[issue aberta](https://github.com/kirodotdev/Kiro/issues/8465) afirmando que não.

Se não dispararem: `.agents/execucoes/` fica vazio, a dimensão **Autonomia** do
`/auditar` pontua 0 e o `/validar` pula a corroboração de trajetória —
degradação honesta, igual a Codex e Cursor. Nesse caso o caminho é o gate do
próprio Gateway (acima) e os checks no CI do projeto.

Verifique no seu ambiente com:

```bash
kiro-cli chat --agent laura-tech-lead   # peça qualquer edição de arquivo
ls .agents/execucoes/                  # apareceu .jsonl? então os hooks rodam
```

## O que ainda está aberto

- **`/mobilizar` em paralelo.** Continua exigindo Agent Teams do Claude Code. O
  Kiro tem subagents e o Crew tem `spawn_run` — é o candidato mais promissor a
  um segundo caminho, mas não foi testado. Por ora use `rodar`.
- **Duas pontes com o mesmo papel.** `hermes/` e Kiro Crew ocupam o mesmo lugar
  na arquitetura. Manter as duas tem custo; escolher é uma decisão em aberto.
