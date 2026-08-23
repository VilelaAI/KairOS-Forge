# ADR-0037 — Artefato gerado é inegociável, e a trajetória volta para quem melhora

- **Status:** aceito
- **Data:** 2026-08-23
- **Versão:** v0.30.0

## Contexto

Revisão do [ADOP](https://github.com/aws-samples/sample-Agentic-Ai-Data-Operations)
(AWS), uma plataforma agêntica de operações de dados. Não é um artigo de arquitetura:
é um **par direto deste repositório** — plugin do Claude Code com `.claude/hooks`,
comandos, skills e sete agentes especializados, aplicado ao domínio de dados.

Dois mecanismos de lá não têm equivalente aqui, e nenhum dos dois é sobre dados.

### 1. O agente pode reescrever à mão o que um script gera

O ADOP tem um hook `PreToolUse` que **bloqueia** escrita direta nos artefatos gerados,
com a mensagem "altere o spec e re-renderize".

Auditando o mesmo ponto aqui: **mais de trezentos arquivos gerados** — os mirrors por CLI
(`.agents/`, `.cursor/`, `.codex/agents/`, `.opencode/`) e o manifesto de ativos —
protegidos por um comentário dentro do arquivo dizendo *"GERADO — não edite aqui"*.

Prosa não impõe. É a mesma lição que o ADR-0029 aprendeu sobre orçamento, o ADR-0033
sobre teto de onda e o ADR-0035 sobre posse de arquivo — e ela ainda não tinha sido
aplicada aos próprios artefatos gerados do repositório.

O modo de falha é pior que um erro, porque **não é um erro**: a edição funciona, sobrevive
até o próximo `sync-multi-cli.py`, some sem aviso, e o CI acusa "diff pendente" — um
sintoma que não aponta para a causa. Quem editou nunca descobre por quê.

### 2. O instrumento existe, o consumidor do lado da melhoria não

O ADR-0021 construiu a trajetória (`.agents/execucoes/*.jsonl`). Quem consome é o
`/kairos-forge:auditar` — que **relata**. O `/kairos-forge:evoluir`, que é quem
**melhora**, conduz uma entrevista de cinco perguntas e nunca abre o arquivo: sua única
fonte de evidência era o `ai-memory`, um companion externo e opcional.

Medir e não usar na melhoria é meio laço. O ADOP fecha o dele lendo os próprios traços
para propor mudança de prompt.

## Decisão

**1. Artefato gerado entra no `guardrail.py` como classe própria.** Editar um gerado é
bloqueado; a saída aponta o canônico e o comando de sync.

A detecção usa **dois sinais**, e a divisão entre eles segue quem pode ter arquivo
próprio no diretório:

| Sinal | Onde | Por quê |
|---|---|---|
| **Marca no conteúdo** | `.cursor/agents/`, `.codex/agents/`, `.opencode/agent/` | O `sync-multi-cli.py instalar` **preserva** arquivo do usuário nesses caminhos (ADR-0035). Bloquear por caminho contradiria a promessa do instalador — só o que carrega a marca é nosso |
| **Caminho** | `.agents/<id>/AGENT.md`, `.cursor/skills/`, `.cursor/scripts/`, `.cursor/templates/`, a rule, o manifesto | São cópias byte a byte do canônico. Marcar a cópia faria ela divergir do original que existe para espelhar — e ninguém guarda arquivo próprio ali |

A classe é `gerado`, degradável para `aviso` e liberável por caminho em
`.agents/guardrails.json` — diferente dos sagrados, que nunca degradam. A diferença é
proposital: escrever no próprio medidor é sempre Goodhart; editar um gerado é quase
sempre engano, e engano merece uma saída.

**2. O `/evoluir` passa a ler a trajetória antes da entrevista**, com
`telemetria.py resumo --dias 7`, e a skill traz uma tabela de leitura — autonomia baixa,
gate verde de primeira baixo, muitas rodadas, recusas por classe — que transforma cada
número em **pergunta**, não em diagnóstico.

**3. Nova trilha `trilha-pipeline-dados.md`** (ADR-0013). O forge tem o time de dados
completo — Fernanda, Carlos, Juliana, Murilo, Bento — e nenhuma trilha de pipeline. Ela
captura o padrão que o ADOP formaliza: zonas com contrato, qualidade como gate e não
relatório, quarentena em vez de descarte silencioso, idempotência de re-execução,
linhagem e frescor. Sem nomes de stack: o padrão, não o Glue.

## Consequências

**O `/evoluir` fica honesto quando não há trajetória.** Sem hooks no CLI,
`.agents/execucoes/` está vazio e o resumo vem zerado. A skill manda **dizer isso** e
seguir para a entrevista — nunca inventar tendência a partir de nada. É a mesma regra que
a dimensão Autonomia do `/auditar` já segue ao pontuar 0 (ADR-0021).

**A evidência sugere, não decide.** A tabela de leitura provoca as cinco perguntas; a
escolha do que a fábrica vira continua sendo do usuário. Isso é deliberado — ver abaixo.

## Alternativas descartadas

**Auto-graft de patch de prompt (o `evolve --auto-graft` do ADOP).** O ADOP fecha o laço
até o fim: patches com confiança ≥ 0,80 são enxertados automaticamente no `SKILLS.md`,
entre 0,60 e 0,79 vão para revisão humana.

Descartado, e vale dizer por quê: é **o agente reescrevendo a própria instrução com base
no próprio traço**. Colide de frente com o ADR-0022 — o agente não escreve o próprio
medidor nem a própria regra — e com o ADR-0031, que proíbe recompensar forma. Um limiar
de confiança não resolve o conflito; a confiança também é auto-reportada.

Adotamos a metade que não tem esse problema: a trajetória vira **evidência para o
humano**, não patch automático.

**Políticas Cedar por agente.** O ADOP declara autorização por agente em arquivos
`.cedar` (`forbid quality WriteData`), mais fino que uma allow-list de ferramentas.
Descartado por dois motivos. Primeiro, **não está enforced nem lá**: existe um
`cedar_validator.py`, mas nenhum hook configurado o chama — o Cedar guarda o pipeline de
dados, não as chamadas de ferramenta do agente. Segundo, a allow-list do forge já é
fronteira real onde importa (Claude Code e OpenCode, ADR-0035); trocar por um motor de
políticas custaria uma dependência para ganhar precisão onde já temos enforcement.

**Renderizador de código por template (o núcleo do hook do ADOP).** Lá funciona porque o
domínio é fechado: job de ETL, DAG, DDL. O forge é genérico — não existe template
universal para "o código". Adotamos o **princípio** (há uma classe de arquivos que só um
script escreve) sem o mecanismo que depende de domínio fechado.

**Prompts por regulação (GDPR, HIPAA, PCI, SOX).** ADR-0002: é kairos-ai.
