# ADR-0022 — Guardrails determinísticos: hooks que bloqueiam, com fallback por script

- **Status:** aceito
- **Data:** 2026-08-01
- **Versão:** v0.18.0

## Contexto

O whitepaper Day-1 define guardrails como *"deterministic code that runs at specific
lifecycle points: before a tool call, after a file edit, before a commit. **Hooks are the
place for things the agent should never forget but often does.**"*

Até a v0.17 o kairos-forge tinha dois hooks e ambos só imprimiam texto. O `PostToolUse`
detectava arquivo de produção modificado e sugeria lembrar do Ricardo — não impedia nada.

Enquanto isso, as regras **duras** da fábrica moravam todas em prosa que o modelo pode
driftar: file ownership, `verificado:` obrigatório antes de "Concluído", Pare e Pergunte,
proibição de inventar conteúdo. É a inversão exata do que o paper recomenda, e a mesma
observação que ele resume em *"most agent failures, examined honestly, are configuration
failures"*.

Em L3 isso é tolerável: existe um humano lendo o diff antes do merge, e ele pega o que o
prompt não segurou. No L4 alvo — *"o time confia mais no harness do que em revisão
individual de código"* — não existe essa rede. Regra que só vive no prompt não é regra;
é sugestão com tom imperativo.

## Decisão

`scripts/guardrail.py` e três hooks que **bloqueiam** (exit 2 no `PreToolUse`, com o motivo
indo para o modelo via stderr).

### Três classes de risco

**1. Comando destrutivo** (`PreToolUse`, matcher `Bash`). Apagar raiz ou home, force-push em
branch protegida, `DROP`/`TRUNCATE`/`DELETE` sem `WHERE`, baixar-e-executar (`curl | sh`),
`chmod 777`, exfiltração de `.env` por rede, `git checkout -- .`.

O critério de desenho aqui é **precisão acima de cobertura**: `rm -rf node_modules` passa,
`rm -rf /` não. Guardrail com falso positivo é guardrail que o usuário desliga — e aí não
guarda nada. A bateria de teste do desenvolvimento cobre 13 casos que devem bloquear e 13
que devem passar, incluindo os pares perigosos (`git push --force-with-lease` em branch
própria passa; `--force` em `main` não).

**2. Arquivo protegido** (`PreToolUse`, matcher `Write|Edit|NotebookEdit`). Segredos
(`.env`, `*.pem`, `*.key`, `id_rsa*`) e configuração de CI. Exceções para `*.example`,
`*.sample`, `*.template` e `*.md`, que existem para ser versionados. Configurável por
projeto em `.agents/guardrails.json` (campos `protegidos`, `comandos_extra`, `liberados`).

**3. Integridade da SPEC** (`PostToolUse`, matcher `Write|Edit`). Linha de tabela com status
"Concluído" e nenhuma célula começando com `verificado:` → o modelo recebe o bloqueio e
corrige na hora, em vez de o problema aparecer no `/validar` depois. O ritual que a fábrica
já tinha em prosa vira check.

### Goodhart: o agente não escreve o próprio medidor

Dois caminhos são bloqueados **sem possibilidade de configuração**:

    .agents/execucoes/**      a trajetória que o /validar usa para corroborar
    .agents/guardrails.json   a configuração destes próprios guardrails

Corroboração que o agente pode reescrever não corrobora nada; guardrail que o agente pode
afrouxar não guarda nada. É o mesmo princípio que o `/kairos-forge:otimizar` já aplica
desde o ADR-0012 — *"a métrica é sagrada; o comando que a mede fica nos protegidos, porque
otimizar o medidor é o modo de falha clássico"* — agora aplicado ao harness em vez de ao
experimento. Quem edita esses dois arquivos é o humano.

O `templates/anti-drift.md` ganha a regra correspondente: contornar guardrail (reescrever o
comando para escapar do padrão, copiar o arquivo para outro caminho, gerar script que o
edite) é o comportamento mais grave da lista, precisamente porque em execução autônoma
ninguém lê o diff a tempo.

### Fallback por CLI

`PreToolUse` só existe no Claude Code. Para Codex, OpenCode e Cursor — e para CI e
pre-commit em qualquer lugar — o mesmo contrato roda como CLI:

```bash
python3 scripts/guardrail.py verificar [CAMINHO]
```

Não é equivalente (checa depois, não antes), e o ADR diz isso em vez de fingir paridade.
Mas fecha o buraco onde ele é mais caro: o CI do projeto.

## Consequências

**Positivas**

- As regras que não podem falhar deixam de depender de o modelo lembrar delas.
- O `verificado:` passa a ser cobrado no momento da escrita, não só na validação —
  ciclo de feedback muito mais curto e barato.
- A integridade da trajetória fica garantida por construção, o que é pré-condição para a
  corroboração do ADR-0021 significar alguma coisa.
- Guardrail é o componente que torna a autonomia **segura**. Sem ele, os gatilhos por
  evento do ADR-0026 seriam pipeline sem supervisão.

**Negativas e limites, declarados**

- **Falso positivo é possível** e o custo dele é alto (usuário desliga o hook). Mitigado por
  bateria de teste e por `liberados` na configuração, mas é um risco permanente que exige
  disciplina em toda regra nova.
- **Falha aberta por desenho.** Se o `guardrail.py` quebrar por bug próprio, ele sai com 0
  e permite a ação. Bloquear por bug interno seria pior que a ausência do check — mas
  significa que o guardrail não é uma garantia forte de segurança, e sim uma rede.
  Segurança de verdade continua sendo Helena, `/analisar-ameacas` e `/revisar`.
- **Regex sobre comando não é sandbox.** Um agente adversário contornaria (base64, variável
  de ambiente, script intermediário). O modelo de ameaça aqui é **erro**, não malícia: o
  agente que ia rodar `DROP TABLE` achando que era seguro. Sandbox de verdade é o worktree
  do ADR-0024 e o isolamento do ambiente de execução, fora do alcance de um plugin.
- **Latência** de um processo Python por tool call de escrita ou Bash. Medida em dezenas de
  milissegundos; aceita.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Manter as regras só na prosa das skills e reforçar o texto | É o que já existia. O paper e a prática dizem que o modelo drifta em regra longa; a v0.16 tinha as regras escritas e mesmo assim nada impedia a violação |
| Enforcar file ownership por teammate no hook | O hook não sabe qual teammate fez a chamada — não há atribuição no payload. Ownership físico é resolvido por worktree (ADR-0024); tentar no hook geraria falso positivo em série |
| Bloquear em vez de falhar aberto quando o script quebra | Um bug no guardrail travaria toda a sessão do usuário. O custo assimétrico manda falhar aberto |
| Deixar o `verificado:` só para o `/validar` | Ciclo de feedback longo: o erro só aparece etapas depois, quando corrigir é mais caro e o contexto já mudou |
