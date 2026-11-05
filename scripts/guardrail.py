#!/usr/bin/env python3
"""guardrail.py — guardrails determinísticos da fábrica (ADR-0022).

O whitepaper Day-1 define hooks como *"deterministic code that runs at specific
lifecycle points... the place for things the agent should never forget but often
does"*. Até a v0.17 os hooks do kairos-forge só imprimiam texto: o PostToolUse
sugeria lembrar do Ricardo e não impedia nada. As regras duras da fábrica moravam
todas em prosa que o modelo pode driftar — a inversão exata do que o paper
recomenda.

Este script é a parte que **bloqueia**. Onze classes de risco:

  1. Comando destrutivo      — apagar a raiz, force-push em branch protegida,
                               DROP/TRUNCATE fora de migration, curl|sh, chmod 777;
                               e `gh pr create` em branch `poc/*` (ADR-0040)
  2. Arquivo protegido       — segredos, config de CI, e os arquivos que o
                               agente NUNCA pode escrever (ver "Goodhart" abaixo)
  3. Artefato gerado         — mirror por CLI e manifesto: editar ali não dá erro,
                               dá silêncio (ADR-0037). Edite o canônico e sincronize
  4. Integridade da SPEC     — status "Concluído" sem célula `verificado:`
  5. Contrato de relatório   — bloco ```kairos-validacao / ```kairos-revisao
                               malformado, incoerente, ou limpo sem prova de
                               cobertura (ADR-0032)
  6. Teste existente         — edição em arquivo de teste que já existia no HEAD.
                               Suite verde que o agente afrouxou não é evidência
                               (ADR-0039). Default `aviso`: registra na trajetória
                               e avisa uma vez por arquivo na sessão; o
                               `/validar` cobra a justificativa por arquivo
  7. Leitura de segredo      — `cat .env`, `~/.ssh`, `*.pem`, credencial AWS e o
                               serviço de metadados, pelo shell ou pela tool Read
                               (ADR-0042). `grep`, `ls`, `stat`, `test` passam: o
                               caminho legítimo parecido não é negado. Piso: sem
                               `modos`, sem `liberados`
  8. Fiação dos hooks        — escrita que muda o que o Claude Code roda fora das
                               ferramentas em qualquer `.claude/settings*.json`
                               (`hooks`, `disableAllHooks`, plugins, marketplaces e
                               comandos de status), ou em `.cursor/hooks.json` e
                               `.codex/hooks.json`, pela tool ou pelo shell: silenciaria
                               o guardrail inteiro de uma vez (ADR-0042 e emenda). Piso
  9. Régua                   — edição em config existente de lint, formatter,
                               typecheck, cobertura ou hooks do git, e supressão
                               inline nova em produção (`# noqa`, `@ts-ignore`,
                               `# pragma: no cover`): baixar a régua em vez de
                               consertar o código (ADR-0046). Default `aviso`
 10. Checkout principal     — código de produção escrito no checkout principal
                               enquanto um ciclo aberto constrói no branch dele: a
                               construção autônoma roda em worktree (emenda ao
                               ADR-0024). Default `aviso`, uma vez por sessão;
                               `"checkout_principal": "sempre"` vale fora do ciclo
 11. Intenção               — requisito da SPEC sem origem no `## Mapa de intenção`
                               (ADR-0053): inventado, pelo ADR-0015. SPEC nova
                               sem o mapa também conta. Default `aviso`, uma vez
                               por arquivo na sessão

Mais três regras de comando no piso (ADR-0042), inspiradas no harness-toolkit do
Tech Leads Club: destruição fora do projeto (`rm -rf` em caminho absoluto que não é
o repositório nem temp), destruição não provável (`rm -rf` cujo alvo vem de variável
ou substituição — não dá para provar o que apaga antes de rodar) e controle da
máquina (`shutdown`, `reboot`, `poweroff`). E uma quarta (ADR-0046, do ECC): pular os
hooks do git — `--no-verify`, `git commit -n`, `core.hooksPath` trocado, `HUSKY=0`.

E um gate de PARADA (ADR-0042, hook `Stop`): sessão que escreveu código de produção
e não rodou nenhum gate verde depois da última escrita não encerra em silêncio.
Default `aviso`; em `bloqueio` o modelo recebe a lista do que ficou sem prova e
continua. Nunca dispara duas vezes na mesma parada (`stop_hook_active`).

## Goodhart: o agente não escreve o próprio medidor

Quatro caminhos são bloqueados sem possibilidade de configuração:

    .agents/execucoes/**    a trajetória que o /validar usa para corroborar
    .agents/guardrails.json a configuração destes próprios guardrails
    .agents/ciclo/**        o estado da máquina do arco /entregar
    .agents/quadro/**       o quadro de tarefas que decide o que o time lança

É o mesmo princípio que o `/kairos-forge:otimizar` já aplica ("a métrica é
sagrada — otimizar o medidor é o modo de falha clássico"), aplicado ao harness.
Corroboração que o agente pode reescrever não corrobora nada, e guardrail que o
agente pode afrouxar não guarda nada. Quem edita esses arquivos é o humano.

## Modos

Hook (payload do hook em stdin, exit 2 = bloqueia e o motivo vai para o modelo):

    guardrail.py comando    # PreToolUse  matcher Bash
    guardrail.py escrita    # PreToolUse  matcher Write|Edit
    guardrail.py leitura    # PreToolUse  matcher Read           (ADR-0042)
    guardrail.py spec       # PostToolUse matcher Write|Edit
    guardrail.py contrato   # PostToolUse matcher Write|Edit
    guardrail.py parada     # Stop                               (ADR-0042)

E um modo que não bloqueia: `faixa3` (ADR-0052) recebe o mesmo payload e responde em
JSON se a chamada para por uma pessoa — efeito que um revert não desfaz, com o arco
ligado. Quem pergunta é o mod do Claude Code (`hooks/pausa.ts`); o modo sai sempre 0.
No Cursor (ADR-0055), o mesmo modo responde direto no dialeto dele: `deny` com o cartão,
porque o `ask` de um hook do Cursor não chega a uma pessoa no Auto-review; `ask` só com
`"faixa_3_cursor": "perguntar"` no projeto; e `allow` quando não para, porque resposta
fora do esquema bloqueia a ação.

    guardrail.py faixa3     # chamado pelo mod em tool.check, e no Cursor em
                            # beforeShellExecution e beforeMCPExecution

E o modo `saida` (ADR-0056), que também não bloqueia: recebe `textos` (o que uma
ferramenta devolveu) e responde com eles já sem os segredos — token com prefixo próprio,
chave privada, JWT, senha em URL, valor de variável secreta —, o aviso para o modelo e o
achado gravado na trajetória sem o valor. Quem troca o resultado é o mod do Claude Code
(`hooks/segredo.ts`), antes de o modelo ler; o modo sai sempre 0.

    guardrail.py saida      # chamado pelo mod em tool.call, depois que a chamada roda

Os gatilhos de CI usam a mesma regra no texto que publicam (ADR-0057): `ocultar` troca o
segredo pela marca no próprio arquivo, antes de o comentário ou o PR sair.

    guardrail.py ocultar ARQUIVO...

Os mesmos modos servem ao Cursor (ADR-0042): `.cursor/hooks.json`, gerado pelo sync,
chama este script nos eventos `beforeShellExecution`, `beforeMCPExecution`,
`beforeReadFile`, `afterFileEdit` e `stop`. O payload do Cursor é reconhecido pela forma
(`conversation_id` sem `tool_input` em objeto: o `beforeMCPExecution` o manda em texto
JSON) e normalizado, com a ferramenta no nome do Claude Code (`Bash`,
`mcp__<servidor>__<ferramenta>`); a resposta sai no dialeto dele (`permission`,
`additional_context`, `followup_message`) em vez de exit 2.

CLI, sem hook — o caminho para Codex/OpenCode/Cursor e para CI/pre-commit,
onde não existe PreToolUse (exit 1 se houver achado):

    guardrail.py verificar [CAMINHO]

O modo CLI cobre as mesmas classes, com uma assimetria deliberada em `gerado`: o hook
conhece a INTENÇÃO de escrita e recusa; o CLI roda depois do fato e só consegue observar
que o arquivo mudou — o que um sync legítimo também faz. Por isso ali o default é
`aviso`. Quem quer o check duro no CI põe `{"modos": {"gerado": "bloqueio"}}`.

## Configuração (opcional)

`.agents/guardrails.json` no projeto:

    {
      "protegidos":      ["infra/terraform/**"],   // além dos defaults
      "comandos_extra":  ["kubectl delete"],       // regex, além dos defaults
      "liberados":       [".github/workflows/**"], // abre mão de um default
      "modos":           {"contrato": "aviso"},    // por classe (ADR-0030):
                                                   // bloqueio (default) | aviso
      "faixa_3":         "sempre",                 // pausa da faixa 3 fora do arco
                                                   // também (ADR-0052)
      "faixa_3_cursor":  "perguntar"               // no Cursor, `ask` em vez de recusa
    }                                              // (ADR-0055; só fora do Auto-review)

Classes de regra, para o campo `modos`: `comando`, `protegido`, `gerado`, `spec`,
`contrato`, `teste`, `parada`, `regua`, `checkout`, `intencao`, `saida` (em `bloqueio`, o
segredo da saída é ocultado; em `aviso`, fica e o modelo é avisado). Todas nascem em `bloqueio`, menos
`teste`, `parada`, `regua`, `checkout` e `intencao`, que nascem em `aviso` (refactor legítimo também edita teste,
sessão de leitura também termina sem gate, e migração de versão também mexe na config
do linter — a regra existe para deixar rastro; promova a `bloqueio` quando a taxa de
aviso cair).
Os caminhos sagrados, a leitura de segredo e a fiação dos hooks nunca degradam — não
há `modos` nem `liberados` que os afrouxem. É o piso: roda antes de a configuração
importar, e a configuração é um dos arquivos que o agente não alcança.

Só stdlib.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True   # não escrever __pycache__ no diretório do plugin
sys.path.insert(0, str(Path(__file__).resolve().parent))  # para importar contrato.py

# --- 1. comandos destrutivos --------------------------------------------------------
# Precisão importa mais que cobertura: guardrail com falso positivo é guardrail que o
# usuário desliga, e aí não guarda nada. `rm -rf node_modules` passa; `rm -rf /` não.
COMANDOS = [
    (r"\brm\s+(-\w+\s+)*-\w*[rf]\w*\s+(/|~|\$HOME|/\*|~/\*)(\s|$|;)",
     "apagar a raiz do sistema ou o home inteiro"),
    (r"\bgit\s+push\b.*(--force|-f)\b(?!.*--force-with-lease).*\b(main|master|develop|production|prod)\b",
     "force-push em branch protegida (use --force-with-lease em branch própria)"),
    (r"\bgit\s+push\b.*\b(origin\s+)?(main|master|production|prod)\b.*(--force|-f)\b",
     "force-push em branch protegida"),
    (r"(?i)\bdrop\s+(table|database|schema)\b", "DROP de tabela/banco/schema"),
    (r"(?i)\btruncate\s+table\b", "TRUNCATE de tabela"),
    (r"(?i)\bdelete\s+from\s+\w+\s*(;|'|\"|`|$)", "DELETE sem WHERE"),
    (r"\b(curl|wget)\b[^|;]*\|\s*(sudo\s+)?(ba|z|k)?sh\b",
     "baixar-e-executar (curl|sh) — vetor de supply chain"),
    (r"\bchmod\s+(-\w+\s+)*777\b", "chmod 777"),
    (r"(?i)\b(cat|dotenv|source)\b[^;|]*\.env\b[^;]*\|\s*(curl|nc|wget)",
     "exfiltração de .env por rede"),
    (r"\bgit\s+checkout\s+(.*\s)?--\s+\.(\s|$)", "descartar TODAS as mudanças não commitadas"),
]

# Piso do ADR-0042: regras de comando que NÃO obedecem a `modos` — ficavam na lista de
# cima e um `{"modos": {"comando": "aviso"}}` as rebaixava junto com o resto.
PISO_COMANDOS = [
    (r"(^|[;&|]\s*)(sudo\s+)?(shutdown|reboot|halt|poweroff)\b|\bsystemctl\s+(poweroff|reboot|halt)\b",
     "controle da máquina (desligar/reiniciar)"),
    (r"\brm\s+(-\w+\s+)*-\w*[rf]\w*\s+[^;&|]*(\$\{?\w|\$\(|`)",
     "rm -rf com alvo em variável ou substituição — destruição não provável antes de rodar"),
]

# Leitura de segredo (ADR-0042). Nega o comando que MOSTRA o conteúdo; `grep`, `rg`,
# `ls`, `stat`, `test`, `wc`, `file` e `find` não estão na lista de leitores e passam —
# procurar o nome de uma variável não é ler o valor dela.
LEITORES = re.compile(
    r"^\s*(sudo\s+)?(cat|less|more|head|tail|bat|strings|xxd|od|hexdump|base64|sed|awk"
    r"|cp|scp|rsync|python3?|node|ruby|perl|tee|nl|tac|rev|cut|paste)\b")
ALVOS_SEGREDO = re.compile(
    r"(^|[\s/\"'=])\.env(\.(?!example|sample|template|dist)[\w.-]+)?(?=[\s\"';|&)]|$)"
    r"|(~|\$HOME|/root|/home/[\w.-]+)/\.(ssh|aws|gnupg)(/|\b)"
    r"|/\.ssh/|\.aws/credentials|\bid_(rsa|ed25519|ecdsa|dsa)\b"
    r"|\.(pem|p12|pfx|jks)\b|\.(npmrc|pypirc|netrc|git-credentials)\b")
METADADOS = re.compile(r"169\.254\.169\.254|metadata\.google\.internal|100\.100\.100\.200")
SEGREDO_EXCECAO = re.compile(r"\.(example|sample|template|dist)$")
TEMP = ("/tmp", "/var/tmp", "/private/tmp", "/private/var")


def le_segredo(cmd: str) -> str | None:
    """Motivo, se algum segmento do comando mostra um segredo; None se passa."""
    if METADADOS.search(cmd) and re.search(r"\b(curl|wget|http|fetch|nc)\b", cmd):
        return "chamada ao serviço de metadados da nuvem — credencial temporária"
    for seg in re.split(r"\|\||&&|;|\|", cmd):
        if LEITORES.match(seg) and ALVOS_SEGREDO.search(seg):
            return "leitura de segredo pelo shell (o valor entraria no transcript)"
    return None


# Pular os hooks do git (ADR-0046, do block-no-verify do ECC). O pre-commit e o pre-push
# do projeto são gates; o agente que os desliga para o commit passar está escrevendo o
# próprio medidor, como quem edita `.agents/execucoes/`. Antes de procurar, sai o texto
# livre que pode *mencionar* a flag sem usá-la: o corpo dos heredocs e o valor de
# `-m`/`--message`. Aspas em geral ficam — `bash -c "git commit --no-verify"` continua
# sendo o comando.
HEREDOC = re.compile(r"(<<-?\s*(['\"]?)(\w+)\2[^\n]*)\n.*?\n[ \t]*\3[ \t]*(?=\n|$)", re.S)
MENSAGEM = re.compile(r"(\s-[a-zA-Z]*m|\s--message)(=|\s*)('[^']*'|\"(?:\\.|[^\"\\])*\")")
COMMIT = re.compile(r"\bgit\s+(?:-\S+\s+)*commit\b([^;&|\n]*)")
# Agrupamento de opções curtas até a primeira que leva valor colado (`-uno`, `-cmain`,
# `-Fnotas.txt`): dali em diante é valor, e um `n` ali não é `--no-verify`.
AGRUPAMENTO = re.compile(r"-(?!-)([^mFCctSu]*)")
PULA_HOOKS = [
    (re.compile(r"\bgit\b[^;&|\n]*\s--no-verify\b"), "--no-verify"),
    (re.compile(r"(?i)\bgit\b[^;&|\n]*\s(-c\s*|--config-env=)core\.hookspath\s*="),
     "`core.hooksPath` trocado na linha de comando"),
    (re.compile(r"(?i)\bgit\s+config\b[^;&|\n]*\score\.hookspath\s+[^\s-]"),
     "`git config core.hooksPath` apontando os hooks para outro lugar"),
    (re.compile(r"(^|[;&|\n]\s*|\s)(HUSKY=0|HUSKY_SKIP_HOOKS=1|LEFTHOOK=0|SKIP=\S+)\s+"
                r"(\w+=\S*\s+)*git\b"),
     "variável que desliga o gerenciador de hooks (husky, lefthook, pre-commit)"),
]


def _commit_com_n(limpo: str) -> bool:
    """`git commit -n` é `--no-verify` — também dentro de um agrupamento como `-an`."""
    agrupamentos = (AGRUPAMENTO.match(tok) for m in COMMIT.finditer(limpo)
                    for tok in m.group(1).split())
    return any(a is not None and "n" in a.group(1) for a in agrupamentos)


def pula_hooks_do_git(cmd: str) -> str | None:
    """Motivo, se o comando desliga os hooks do git; None se passa."""
    limpo = MENSAGEM.sub(r"\1\2''", HEREDOC.sub(r"\1", cmd))
    if _commit_com_n(limpo):
        return "pula os hooks do git (`git commit -n`)"
    for padrao, forma in PULA_HOOKS:
        if padrao.search(limpo):
            return f"pula os hooks do git ({forma})"
    return None


def destroi_fora_do_projeto(cmd: str, cwd: str) -> str | None:
    """`rm -rf` (ou -r/-R) em caminho absoluto fora do repositório e fora de temp."""
    m = re.search(r"\brm\s+((?:-\w+\s+)*)(.+)$", cmd)
    if not m or not re.search(r"-\w*[rR]", m.group(1)):
        return None
    try:
        raiz = Path(cwd or ".").resolve()
    except OSError:
        return None
    for tok in re.split(r"\s+", m.group(2).strip()):
        tok = tok.strip("\"'")
        if not tok or tok.startswith("-"):
            continue
        if tok.startswith("$"):
            continue  # a regra de destruição não provável já cuida de variável
        if tok.startswith("~"):
            alvo = os.path.expanduser(tok)
        elif tok.startswith("/"):
            alvo = tok
        elif ".." in tok:
            alvo = str((raiz / tok).resolve())
        else:
            continue
        alvo_n = alvo.rstrip("/") or "/"
        dentro = alvo_n == str(raiz) or alvo_n.startswith(str(raiz) + "/")
        temp = any(alvo_n == t or alvo_n.startswith(t + "/") for t in TEMP) or \
            alvo_n.startswith((os.environ.get("TMPDIR") or "/nonexistent").rstrip("/"))
        if not dentro and not temp:
            return f"rm recursivo fora do projeto (`{tok}` não está em {raiz} nem em temp)"
    return None

# --- 2. arquivos protegidos ---------------------------------------------------------
# Inegociáveis: o agente não escreve o próprio medidor nem a própria regra.
SAGRADOS = [
    (".agents/execucoes/**", "a trajetória que o /kairos-forge:validar usa para corroborar evidência"),
    (".agents/guardrails.json", "a configuração destes guardrails"),
    (".agents/ciclo/**", "o estado da máquina do arco /kairos-forge:entregar (ADR-0029)"),
    (".agents/quadro/**", "o quadro de tarefas do /kairos-forge:mobilizar (ADR-0035)"),
    # Fiação dos hooks (ADR-0042): o arquivo em que o editor registra os hooks é o que
    # silenciaria este guardrail inteiro de uma vez. Para o Claude Code a proteção é
    # condicional (só as `CHAVES_FIACAO` de settings*.json — ver `mexe_na_fiacao`).
    (".cursor/hooks.json", "a fiação dos hooks do Cursor — apagar isto silencia o guardrail (ADR-0042)"),
    (".codex/hooks.json", "a fiação dos hooks do Codex — apagar isto silencia o guardrail (ADR-0042)"),
]
FIACAO_CLAUDE = ("settings.json", "settings.local.json")   # dentro de uma pasta `.claude/`

# O que, num settings do Claude Code, decide o que ele roda fora das ferramentas — e por
# isso fora deste guardrail (emenda ao ADR-0042). `disableAllHooks` desliga os hooks de
# plugin, este guardrail incluído; `enabledPlugins` e os marketplaces ligam ou desligam
# plugins, e um plugin com mod pode responder no lugar de um hook; `statusLine`,
# `subagentStatusLine` e `fileSuggestion` são comandos que o Claude Code roda sozinho.
CHAVES_FIACAO = ("hooks", "disableAllHooks", "enabledPlugins", "extraKnownMarketplaces",
                 "additionalMarketplaces", "statusLine", "subagentStatusLine",
                 "fileSuggestion", "syncClaudeAiPlugins")
TRECHO_FIACAO = re.compile(r"hooks|plugins|marketplaces|statusline|filesuggestion|guardrail"
                           r"|execucao\.py|kairos-forge", re.I)


def eh_settings_do_claude(rel: str) -> bool:
    """`.claude/settings*.json` do projeto, do usuário ou de qualquer pasta."""
    partes = Path(rel).parts
    return len(partes) >= 2 and partes[-2] == ".claude" and partes[-1] in FIACAO_CLAUDE


def _fiacao(cfg: dict) -> dict:
    """As chaves de fiação com valor: ausente, vazio e `false` contam igual."""
    return {k: cfg[k] for k in CHAVES_FIACAO if cfg.get(k)}


def _como_objeto(texto: str | None) -> dict | None:
    try:
        dado = json.loads(texto) if texto is not None else None
    except ValueError:
        return None
    return dado if isinstance(dado, dict) else None


def _depois_do_edit(texto: str, entrada: dict) -> str | None:
    """O arquivo como fica depois do Edit; None quando o trecho não está nele."""
    velho, novo = str(entrada.get("old_string") or ""), str(entrada.get("new_string") or "")
    if not velho or velho not in texto:
        return None
    return texto.replace(velho, novo, -1 if entrada.get("replace_all") else 1)


def _texto_do_alvo(alvo: Path) -> str:
    try:
        return alvo.read_text(encoding="utf-8") if alvo.is_file() else "{}"
    except (OSError, ValueError):   # sem acesso ou não é UTF-8: lido como vazio, sem quebrar
        return "{}"


def _chaves_mudadas(antes: dict, depois: dict) -> list[str]:
    return sorted(k for k in set(antes) | set(depois) if antes.get(k) != depois.get(k))


def _trecho_na_fiacao(entrada: dict) -> list[str]:
    """Edit que não dá para aplicar e comparar: decide pelo texto trocado."""
    trecho = str(entrada.get("old_string") or "") + str(entrada.get("new_string") or "")
    return ["trecho"] if TRECHO_FIACAO.search(trecho) else []


def mexe_na_fiacao(entrada: dict, alvo: Path) -> list[str]:
    """As chaves de fiação que a escrita em settings*.json do Claude Code mudaria.

    O agente edita settings.json por motivos legítimos (permissões, env). O que não pode é
    mudar o que o Claude Code roda fora das ferramentas. Write e Edit são comparados pelo
    arquivo que resultaria; Write ilegível conta como fiação se o arquivo tinha alguma, e
    Edit que não se aplica ou deixa o JSON ilegível cai na busca pelo trecho trocado.
    """
    texto = _texto_do_alvo(alvo)
    antes = _fiacao(_como_objeto(texto) or {})
    eh_write = "content" in entrada
    novo = _como_objeto(str(entrada["content"]) if eh_write else _depois_do_edit(texto, entrada))
    if novo is not None:
        return _chaves_mudadas(antes, _fiacao(novo))
    return sorted(antes) if eh_write else _trecho_na_fiacao(entrada)


# Pelo shell, a mesma fiação: escrita nos arquivos dela por redirecionamento, `tee`,
# `sed -i`, `cp`/`mv` como destino, `rm` ou um interpretador. Ler (`cat`, `jq .`, `grep`)
# e copiar para fora passam.
ARQUIVO_FIACAO = r"[^\s;&|]*(\.claude/settings(\.local)?\.json|\.cursor/hooks\.json|\.codex/hooks\.json)"
ESCRITA_NA_FIACAO = [
    re.compile(rf">\|?\s*[\"']?{ARQUIVO_FIACAO}"),
    re.compile(rf"\b(tee|truncate|rm|dd)\b[^;&|]*{ARQUIVO_FIACAO}"),
    re.compile(rf"\b(sed|perl)\b[^;&|]*\s(-[a-zA-Z]*i\S*|--in-place\S*)[^;&|]*{ARQUIVO_FIACAO}"),
    re.compile(rf"\b(cp|mv|ln|install|rsync)\b[^;&|]*\s[\"']?{ARQUIVO_FIACAO}[\"']?\s*($|[;&|])"),
    re.compile(rf"\b(python3?|node|ruby)\b.*{ARQUIVO_FIACAO}"),   # o `;` do código não corta
]


def escreve_na_fiacao(cmd: str) -> str | None:
    if any(r.search(cmd) for r in ESCRITA_NA_FIACAO):
        return "escrita pelo shell num arquivo de fiação dos hooks (settings do Claude Code, hooks do Cursor ou do Codex)"
    return None

# --- 2b. artefato gerado (ADR-0037) -------------------------------------------------
# Os mirrors por CLI, as skills espelhadas e o manifesto de ativos são GERADOS por
# `sync-multi-cli.py` a partir dos canônicos `agents/` e `skills/`. Até aqui a proteção
# era um comentário dentro do arquivo dizendo "não edite aqui" — e a lição recorrente
# deste repositório é que prosa não impõe.
#
# Editar um gerado não dá erro: dá um silêncio. A mudança sobrevive até o próximo sync,
# some sem aviso, e o CI acusa "diff pendente" — sintoma que não aponta para a causa.
#
# A regra é por CONTEÚDO, não por caminho, e é isso que a torna precisa em qualquer
# projeto: bloqueia sobrescrever arquivo que JÁ CARREGA a marca de gerado. O grafo do
# usuário em `.agents/grafo/`, um agente próprio em `.cursor/agents/` e qualquer arquivo
# novo continuam livres — nenhum deles tem a marca.
MARCA_GERADO = "GERADO por scripts/sync-multi-cli.py (kairos-forge)"

# Dois sinais, e a divisão entre eles não é arbitrária — ela segue quem PODE ter
# arquivo próprio ali:
#
#   marca (conteúdo) → diretórios de agente: `.cursor/agents/`, `.codex/agents/`,
#       `.opencode/agent/`. O `sync-multi-cli.py instalar` PRESERVA arquivo do usuário
#       nesses caminhos, então bloquear por caminho contradiria a promessa do
#       instalador. Só o que carrega a marca é nosso.
#
#   caminho → mirrors puros: cópias byte a byte do canônico (`.agents/<id>/AGENT.md`,
#       `.cursor/skills/`) e artefatos derivados. Marcar a cópia faria ela divergir do
#       original que existe para espelhar, e ninguém guarda arquivo próprio ali.
GERADOS_PADRAO = [
    ".agents/*/AGENT.md",
    ".cursor/skills/**",
    ".cursor/scripts/**",
    ".cursor/templates/**",
    ".cursor/rules/kairos-forge.mdc",
    ".cursor/hooks.json",
    ".claude-plugin/ativos.manifest.json",
    ".tucano/**",                    # o time do Tucano (ADR-0047)
    ".kairos-forge/scripts/**",      # os scripts que `tucano.py instalar` copia ao projeto
    ".kairos-forge/templates/**",
]

# --- 4. abertura de PR fora de estado (ADR-0029) -------------------------------------
ABRE_PR = re.compile(r"\bgh\s+pr\s+create\b")
FECHA_PR = re.compile(r"\bgh\s+pr\s+merge\b")
# Branch de POC (ADR-0040): o código é descartável por contrato — vira notas, nunca PR.
PREFIXO_POC = "poc/"

PROTEGIDOS_PADRAO = [
    (".env", "arquivo de segredos"),
    (".env.*", "arquivo de segredos"),
    ("**/*.pem", "chave privada"),
    ("**/*.key", "chave privada"),
    ("**/id_rsa*", "chave SSH"),
    (".github/workflows/**", "configuração de CI — mexer nos próprios gates é Goodhart"),
]

# Casam com um padrão protegido mas existem para ser versionados e editados.
EXCECOES = ["*.example", "*.sample", "*.template", "*.dist", "*.md"]

# --- 3. integridade da SPEC ---------------------------------------------------------
LINHA_TABELA = re.compile(r"^\s*\|.*\|\s*$")


def carregar_config(raiz: Path) -> dict:
    arq = raiz / ".agents" / "guardrails.json"
    if not arq.is_file():
        return {}
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except Exception:
        return {}


# --- modo por classe de regra (ADR-0030) --------------------------------------------
# Regra que falha demais é regra que o time desliga na semana seguinte. `aviso` deixa
# a regra rodar e medir antes de morder; `bloqueio` é o default e o destino.
# Promoção não é por gosto: migre para `bloqueio` quando a taxa de aviso cair — o
# `telemetria.py resumo` mostra o número.
MODO_PADRAO = "bloqueio"
# Classe que nasce em observação (ADR-0039): editar teste existente é legítimo com
# frequência demais para bloquear por default — o valor está no rastro.
MODO_PADRAO_POR_CLASSE = {"teste": "aviso", "parada": "aviso", "regua": "aviso",
                          "checkout": "aviso", "intencao": "aviso"}


def modo_de(cfg: dict, classe: str) -> str:
    padrao = MODO_PADRAO_POR_CLASSE.get(classe, MODO_PADRAO)
    modo = (cfg.get("modos", {}) or {}).get(classe) or cfg.get("modo") or padrao
    return modo if modo in ("bloqueio", "aviso") else padrao


def raiz_principal(raiz: Path) -> Path:
    """O checkout principal quando `raiz` é um worktree ligado; senão, a própria `raiz`."""
    try:
        from execucao import raiz_do_projeto
        return raiz_do_projeto(raiz.resolve())
    except Exception:
        return raiz.resolve()


def pasta_do_estado(raiz: Path, nome: str) -> Path:
    """`.agents/<nome>` do checkout principal, onde o execucao.py, o ciclo.py e o quadro.py
    gravam mesmo num worktree ligado (ADR-0048; emenda ao ADR-0024)."""
    return raiz_principal(raiz) / ".agents" / nome


def pasta_da_trajetoria(raiz: Path) -> Path:
    """Gate de parada que lesse outra pasta que não a do execucao.py não veria a escrita."""
    return pasta_do_estado(raiz, "execucoes")


def registrar_evento(raiz: Path, evento: dict) -> None:
    try:
        pasta = pasta_da_trajetoria(raiz)
        pasta.mkdir(parents=True, exist_ok=True)
        evento = {"t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "sessao": (os.environ.get("CLAUDE_SESSION_ID") or "?")[:16], **evento}
        with (pasta / f"{datetime.now(timezone.utc):%Y-%m}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(evento, ensure_ascii=False) + "\n")
    except Exception:
        pass  # registro nunca derruba o guardrail


def registrar_recusa(raiz: Path, classe: str, regra: str, alvo: str, modo: str) -> None:
    """Grava a tentativa na trajetória.

    O bloqueio funcionou e o agente segue em frente — mas *ter tentado* é sinal, e sinal
    que não é registrado não existe. Um agente que passa na validação alcançando ferramenta
    que não tem não está passando (ADR-0030).
    """
    registrar_evento(raiz, {"tipo": "recusa", "classe": classe, "regra": regra[:120],
                            "alvo": alvo[:200], "modo": modo})


def bloquear(motivo: str, detalhe: str, saida: str, modo: str = "bloqueio") -> int:
    """exit 2 bloqueia e manda o motivo ao modelo; exit 1 avisa e deixa passar."""
    if _EDITOR["cursor"]:
        return responder_cursor(1 if modo == "aviso" else 2, motivo, detalhe, saida)
    if modo == "aviso":
        print(f"⚠️  kairos-forge (guardrail, modo aviso): {motivo}\n\n{detalhe}\n\n{saida}\n"
              "Esta regra está em observação — hoje ela avisa, não bloqueia.", file=sys.stderr)
        return 1
    print(f"🛑 kairos-forge (guardrail): {motivo}\n\n{detalhe}\n\n{saida}", file=sys.stderr)
    return 2


def relativo(caminho: str, raiz: Path) -> str:
    try:
        return str(Path(caminho).resolve().relative_to(raiz.resolve()))
    except Exception:
        return caminho


def casa(rel: str, padrao: str) -> bool:
    rel = rel.replace("\\", "/")
    if fnmatch.fnmatch(rel, padrao):
        return True
    # `dir/**` deve casar com o próprio dir e com tudo abaixo
    if padrao.endswith("/**") and (rel == padrao[:-3] or rel.startswith(padrao[:-2])):
        return True
    return False


# --- modo hook: comando -------------------------------------------------------------

def ciclos_abertos(raiz: Path) -> list[dict]:
    """Os ciclos do /entregar em andamento, em ordem de nome. Vazio sem máquina rodando."""
    pasta = pasta_do_estado(raiz, "ciclo")
    if not pasta.is_dir():
        return []
    abertos = []
    for p in sorted(pasta.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("estado") not in ("encerrado", "escalado"):
            abertos.append(d)
    return abertos


def ciclos_do_pr(raiz: Path, abertos: list[dict]) -> list[dict]:
    """Os ciclos que um `gh pr create` daqui pode estar fechando.

    O `ciclo.py abrir` grava a branch do ciclo. Os desta branch são os do PR — com dois
    ciclos abertos, o PR do que está pronto não espera o outro sair do gate. Se nenhum é
    desta branch (ciclo antigo sem `branch`, ou branch criada para o PR), valem todos:
    trocar de branch não pode ser o jeito de contornar o estado de um ciclo aberto.
    """
    branch = branch_atual(raiz)
    daqui = [c for c in abertos if branch and c.get("branch") == branch]
    return daqui or abertos


def branch_atual(raiz: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(raiz), "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def checar_comando(payload: dict) -> int:
    cmd = str((payload.get("tool_input") or {}).get("command") or "")
    if not cmd.strip():
        return 0
    raiz = Path(payload.get("cwd") or ".")
    cfg = carregar_config(raiz)

    # Abertura/merge de PR obedecem à máquina de estados, quando ela está rodando.
    abertos = ciclos_abertos(raiz)
    if abertos:
        if FECHA_PR.search(cmd):
            registrar_recusa(raiz, "ciclo", "merge durante ciclo aberto", cmd[:200], "bloqueio")
            return bloquear(
                "merge de PR bloqueado durante um ciclo do /kairos-forge:entregar",
                "Ciclo(s) aberto(s): " + ", ".join(
                    f"{c.get('spec')} em '{c.get('estado')}'" for c in abertos) + ".",
                "O arco termina no PR — a decisão de integrar é do dono do repositório "
                "(ADR-0023). Peça o merge ao usuário.",
            )
        fora = []
        if ABRE_PR.search(cmd):
            fora = [c for c in ciclos_do_pr(raiz, abertos) if c.get("estado") != "pronto_para_pr"]
        if fora:
            ciclo = fora[0]
            registrar_recusa(raiz, "ciclo", "PR fora de estado", cmd[:200], "bloqueio")
            return bloquear(
                f"abertura de PR fora de estado — o ciclo {ciclo['spec']} está em "
                f"'{ciclo['estado']}', não em 'pronto_para_pr'",
                f"Rodadas: validar {ciclo['rodadas']['validar']}/{ciclo['orcamento']['validar']} · "
                f"revisar {ciclo['rodadas']['revisar']}/{ciclo['orcamento']['revisar']}.",
                "PR com P1 bloqueado ou 🔴 aberto transfere para o revisor humano exatamente o "
                "trabalho que o arco existe para absorver. Rode `ciclo.py estado` e siga o "
                "próximo passo que ele indica.",
            )

    if ABRE_PR.search(cmd) and branch_atual(raiz).startswith(PREFIXO_POC):
        registrar_recusa(raiz, "comando", "PR de branch de POC", cmd[:200], "bloqueio")
        return bloquear(
            f"abertura de PR bloqueada — a branch atual é de POC (`{branch_atual(raiz)}`)",
            "POC é descartável por contrato (ADR-0040): o /kairos-forge:especificar lê as "
            "notas em `docs/pocs/`, não o código.",
            "Escreva/complete `docs/pocs/POC-<slug>.md` com o que a tentativa revelou e "
            "reconstrua o que sobreviver com SPEC, teste e revisão numa branch normal.",
        )

    # Piso (ADR-0042/0046): sem `modos`, sem `comandos_extra` que afrouxe.
    for regra, classe, orientacao in PISO:
        motivo = regra(cmd, str(raiz))
        if motivo:
            registrar_recusa(raiz, classe, motivo, cmd[:200], "bloqueio")
            return bloquear(f"comando bloqueado — {motivo}", f"Comando: {cmd[:300]}", orientacao)

    regras = list(COMANDOS) + [(r, "regra do projeto") for r in cfg.get("comandos_extra", [])]
    modo = modo_de(cfg, "comando")
    for padrao, motivo in regras:
        try:
            if re.search(padrao, cmd):
                registrar_recusa(raiz, "comando", motivo, cmd[:200], modo)
                return bloquear(f"comando bloqueado — {motivo}", f"Comando: {cmd[:300]}",
                                IRREVERSIVEL, modo)
        except re.error:
            continue
    return 0


def piso_por_padrao(cmd: str) -> str | None:
    return next((motivo for padrao, motivo in PISO_COMANDOS if re.search(padrao, cmd)), None)


IRREVERSIVEL = ("Se for realmente necessário, peça ao usuário para executar. "
                "Ação irreversível não roda em fluxo autônomo (ADR-0024).")

# As regras de comando do piso, na ordem em que são checadas: (regra, classe, orientação).
PISO = [
    (lambda cmd, _cwd: le_segredo(cmd), "segredo",
     "Segredo lido pelo shell vai para o transcript e para a trajetória. Para saber "
     "se uma variável existe, `grep -c NOME .env` responde sem mostrar o valor; para "
     "usá-la, deixe o processo ler o arquivo (`source`, dotenv) sem imprimir."),
    (destroi_fora_do_projeto, "comando",
     "Este guardrail só deixa apagar dentro do repositório ou em temp. Fora disso, "
     "quem apaga é o humano."),
    (lambda cmd, _cwd: pula_hooks_do_git(cmd), "comando",
     "O hook do git é um gate do projeto: desligá-lo para o commit passar é escrever o "
     "próprio medidor (ADR-0046). Conserte o que o hook acusa e rode de novo; se o hook "
     "estiver quebrado, peça ao usuário."),
    (lambda cmd, _cwd: piso_por_padrao(cmd), "comando", IRREVERSIVEL),
    (lambda cmd, _cwd: escreve_na_fiacao(cmd), "sagrado",
     "A fiação decide o que o Claude Code roda fora das ferramentas, este guardrail "
     "incluído: um `disableAllHooks` ou um plugin ligado ali o desliga sem ninguém ver "
     "(emenda ao ADR-0042). Quem edita esses arquivos é o humano. Explique o que precisa "
     "mudar e por quê."),
]


# --- modo hook: escrita -------------------------------------------------------------

def checar_escrita(payload: dict) -> int:
    entrada = payload.get("tool_input") or {}
    caminho = str(entrada.get("file_path") or entrada.get("notebook_path") or "")
    if not caminho:
        return 0
    raiz = Path(payload.get("cwd") or ".")
    rel = relativo(caminho, raiz)
    cfg = carregar_config(raiz)
    liberados = cfg.get("liberados", [])
    # Num worktree ligado, o medidor e o estado moram no checkout principal (ADR-0048,
    # emenda ao ADR-0024): o caminho conta também relativo a ele, ou uma escrita por
    # caminho absoluto, de dentro do worktree, passaria.
    alvos = {rel, relativo(caminho, raiz_principal(raiz))}

    # Sagrados NUNCA degradam para aviso: são o medidor e a regra. Guardrail que só
    # avisa sobre escrita no próprio medidor não é guardrail (ADR-0022).
    for padrao, motivo in SAGRADOS:
        if any(casa(alvo, padrao) for alvo in alvos):
            registrar_recusa(raiz, "sagrado", motivo, rel, "bloqueio")
            return bloquear(
                f"escrita bloqueada em `{rel}` — {motivo}",
                "Este caminho é inegociável: o agente não escreve o próprio medidor "
                "nem a própria regra. Corroboração que o agente reescreve não corrobora, "
                "e guardrail que o agente afrouxa não guarda.",
                "Quem edita este arquivo é o humano. Explique o que precisa mudar e por quê.",
            )

    # Fiação do Claude Code (ADR-0042, emenda): só quando a escrita muda uma das
    # `CHAVES_FIACAO`, em qualquer `.claude/settings*.json`, do projeto ou do usuário.
    mudadas = mexe_na_fiacao(entrada, raiz / rel) if eh_settings_do_claude(rel) else []
    if mudadas:
        registrar_recusa(raiz, "sagrado", "fiação dos hooks", rel, "bloqueio")
        return bloquear(
            f"escrita bloqueada em `{rel}` — muda a fiação ({', '.join(f'`{k}`' for k in mudadas)})",
            "É o arquivo que decide o que o Claude Code roda fora das ferramentas: os hooks, "
            "os plugins e os comandos de status. `disableAllHooks` ou um plugin ligado aqui "
            "silencia o guardrail e a telemetria de uma vez, sem que ninguém veja.",
            "Permissões e variáveis nesse arquivo continuam livres; a fiação é do humano. "
            "Explique o que precisa mudar e por quê.",
        )

    # Artefato gerado (ADR-0037), por dois sinais: a marca dentro do arquivo (o que o
    # sync escreve) e o caminho (o que ele copia byte a byte).
    if not any(casa(rel, lib) for lib in liberados):
        alvo = raiz / rel
        try:
            ja_gerado = alvo.is_file() and MARCA_GERADO in alvo.read_text(
                encoding="utf-8", errors="replace")
        except OSError:
            ja_gerado = False
        if ja_gerado or any(casa(rel, g) for g in GERADOS_PADRAO):
            modo_g = modo_de(cfg, "gerado")
            registrar_recusa(raiz, "gerado", "artefato gerado pelo sync", rel, modo_g)
            return bloquear(
                f"escrita bloqueada em `{rel}` — arquivo GERADO por `sync-multi-cli.py`",
                "Editar aqui não dá erro, dá silêncio: sua mudança some no próximo sync "
                "e o CI acusa só um 'diff pendente', que não aponta para a causa.",
                "Edite o canônico (`agents/<id>.md` ou `skills/<nome>/SKILL.md`) e rode "
                "`python3 scripts/sync-multi-cli.py`. Se este arquivo é seu e não do "
                "plugin, remova a linha de marca ou libere o caminho em "
                "`.agents/guardrails.json` (campo `liberados`).",
                modo_g,
            )

    # O que bloqueia vem antes do que só avisa: teste existente num caminho protegido
    # pelo projeto é protegido, não "edição em teste" (ADR-0046).
    for checagem in (checar_protegido, checar_teste, checar_regua, checar_checkout):
        r = checagem(payload, raiz, rel, entrada, cfg)
        if r is not None:
            return r
    return 0


def checar_protegido(payload: dict, raiz: Path, rel: str, entrada: dict,
                     cfg: dict) -> int | None:
    if any(casa(rel, exc) for exc in EXCECOES):  # `*` do fnmatch também casa `/`
        return None
    protegidos = list(PROTEGIDOS_PADRAO) + [
        (p, "protegido pelo projeto") for p in cfg.get("protegidos", [])
    ]
    modo = modo_de(cfg, "protegido")
    for padrao, motivo in protegidos:
        if casa(rel, padrao) and not liberado(cfg, rel):
            registrar_recusa(raiz, "protegido", motivo, rel, modo)
            return bloquear(
                f"escrita bloqueada em `{rel}` — {motivo}",
                "Caminho protegido por guardrail determinístico.",
                "Peça a mudança ao usuário, ou libere o caminho em "
                "`.agents/guardrails.json` (campo `liberados`) — o que o usuário edita, "
                "não você.",
                modo,
            )
    return None


def checar_teste(payload: dict, raiz: Path, rel: str, entrada: dict, cfg: dict) -> int | None:
    """Teste existente (ADR-0039). Só o que JÁ ESTAVA na base: teste novo é o trabalho
    esperado; teste antigo que muda no mesmo diff da feature é o medidor sendo tocado. O
    rastro fica na trajetória sempre; o aviso, uma vez por arquivo na sessão, para não
    virar ruído que o usuário aprende a ignorar."""
    if liberado(cfg, rel) or not teste_existente(raiz, rel):
        return None
    modo_t = modo_de(cfg, "teste")
    registrar_recusa(raiz, "teste", "edição em teste existente", rel, modo_t)
    if modo_t != "bloqueio" and not primeira_vez_na_sessao(payload, rel):
        return None  # já avisou nesta sessão: o rastro ficou, o aviso não se repete
    return bloquear(
        f"edição em teste existente `{rel}`",
        "Teste que já existia é a prova do comportamento anterior. Afrouxar "
        "asserção, pular caso ou apagar teste deixa a suite verde sem provar "
        "nada — e o `/kairos-forge:validar` lista todo teste existente alterado "
        "no diff (`prova.py testes-alterados`) e cobra o porquê, arquivo a arquivo.",
        "Se a mudança é legítima (refactor, contrato que mudou de propósito), "
        "diga o motivo no commit e no relatório. Se o teste está certo e o "
        "código errado, conserte o código.",
        modo_t,
    )


def checar_regua(payload: dict, raiz: Path, rel: str, entrada: dict, cfg: dict) -> int | None:
    """Régua (ADR-0046): config de gate existente ou supressão inline nova."""
    motivo = None if liberado(cfg, rel) else afrouxa_a_regua(raiz, rel, entrada)
    if not motivo:
        return None
    modo_r = modo_de(cfg, "regua")
    registrar_recusa(raiz, "regua", motivo, rel, modo_r)
    if modo_r != "bloqueio" and not primeira_vez_na_sessao(payload, rel):
        return None  # já avisou nesta sessão: o rastro ficou, o aviso não se repete
    return bloquear(
        f"{motivo} em `{rel}`",
        "Com um check vermelho há dois caminhos: consertar o código ou baixar a "
        "régua — e o segundo cabe numa linha. É o mesmo motivo de a config de CI "
        "ser protegida: mexer no próprio gate é Goodhart.",
        "Se a mudança é legítima (regra nova do time, migração de versão, falso "
        "positivo do linter), diga o porquê no commit e, na supressão, no próprio "
        "comentário. Se o código viola a regra, conserte o código.",
        modo_r,
    )


# --- 2d. construção no checkout principal (aula 5 do Tech Leads Club) -----------------
# "O Rodrigo tem um hook que não deixa implementar nada no clone principal." Com o arco
# construindo, ninguém olha cada escrita em voo, e o ADR-0024 pede worktree quando a
# supervisão sai do caminho: a entrega se desfaz removendo a pasta, e o checkout principal
# fica livre para a pessoa seguir trabalhando. A regra olha a escrita de código de
# produção num checkout principal (não num worktree ligado) enquanto um ciclo aberto
# constrói no branch dele. Nasce em `aviso`, uma vez por sessão. `"checkout_principal":
# "sempre"` no guardrails.json estende a regra a toda escrita de produção ali, ciclo ou
# não, que é o hook da aula; `{"modos": {"checkout": "bloqueio"}}` a torna dura.
CONSTRUINDO = {"construindo", "corrigindo_validacao", "corrigindo_revisao", "provando",
               "atacando_premissa_validacao", "atacando_premissa_revisao"}


def checkout_principal(arquivo: Path) -> Path | None:
    """A raiz do checkout principal que contém `arquivo`; None num worktree ligado, num
    submódulo ou fora de git — onde `.git` é arquivo, ou não existe."""
    try:
        from execucao import raiz_do_checkout
    except Exception:
        return None
    raiz = raiz_do_checkout(str(arquivo.parent))
    return raiz if (raiz / ".git").is_dir() else None


def ciclo_construindo_em(raiz: Path) -> str | None:
    """A SPEC do ciclo aberto que constrói no branch hoje no checkout `raiz`."""
    try:
        from execucao import branch_atual
    except Exception:
        return None
    branch = branch_atual(str(raiz))
    for c in ciclos_abertos(raiz):
        if branch and c.get("estado") in CONSTRUINDO and c.get("branch") == branch:
            return str(c.get("spec") or "?")
    return None


def _eh_producao(rel: str) -> bool:
    try:
        from execucao import eh_producao
    except Exception:
        return False
    return eh_producao(rel)


def motivo_do_checkout(principal: Path | None, cfg: dict) -> str | None:
    """Por que avisar: o ciclo que constrói aqui, ou a regra `sempre` do projeto."""
    spec = ciclo_construindo_em(principal) if principal else None
    if spec:
        return f"o ciclo {spec} está construindo aqui"
    sempre = principal is not None and cfg.get("checkout_principal") == "sempre"
    return "a regra do projeto pede worktree" if sempre else None


def checar_checkout(payload: dict, raiz: Path, rel: str, entrada: dict, cfg: dict) -> int | None:
    if liberado(cfg, rel) or not _eh_producao(rel):
        return None
    quem = motivo_do_checkout(checkout_principal((raiz / rel).resolve()), cfg)
    if quem is None:
        return None
    modo = modo_de(cfg, "checkout")
    registrar_recusa(raiz, "checkout", "produção escrita no checkout principal", rel, modo)
    if modo != "bloqueio" and not primeira_vez_na_sessao(payload, "checkout-principal"):
        return None  # já avisou nesta sessão: o rastro ficou, o aviso não se repete
    return bloquear(
        f"código de produção escrito no checkout principal (`{rel}`): {quem}",
        "Com o arco construindo, ninguém olha cada escrita em voo (ADR-0024). Num worktree, a "
        "entrega inteira se desfaz removendo a pasta, e o checkout principal fica livre para "
        "a pessoa seguir trabalhando enquanto a fábrica implementa.",
        "Nas próximas entregas, abra o arco num worktree (Passo 0 do /kairos-forge:entregar): "
        "`git worktree add .worktrees/<SPEC> -b forge/<SPEC>`. O estado do ciclo e do quadro "
        "continua no checkout principal. Para a regra valer sempre, `\"checkout_principal\": "
        "\"sempre\"` em `.agents/guardrails.json`; para bloquear, "
        "`{\"modos\": {\"checkout\": \"bloqueio\"}}`.",
        modo,
    )

def liberado(cfg: dict, rel: str) -> bool:
    return any(casa(rel, lib) for lib in cfg.get("liberados", []))


def ponto_da_base(raiz: Path) -> str:
    """O merge-base com a branch base; sem base conhecida, o HEAD."""
    try:
        from prova import base_padrao, ponto_de_partida
    except ImportError:
        return "HEAD"  # sem o prova.py ao lado (cópia avulsa do script)
    base = base_padrao(raiz)
    return (ponto_de_partida(raiz, base) if base else None) or "HEAD"


def existia_na_base(raiz: Path, rel: str) -> bool:
    """Arquivo que existia ANTES do diff atual — não o que o diff está criando.

    "Antes" é o merge-base com a branch base (o teste novo da feature, já commitado,
    continua sendo novo); sem base conhecida, cai para o HEAD. Erro do git sobe: no hook,
    vira `guardrail_erro` na trajetória em vez de um "não existia" calado (ADR-0046).
    """
    from prova import git
    return git(raiz, "cat-file", "-e", f"{ponto_da_base(raiz)}:{rel}", timeout=10).returncode == 0


def teste_existente(raiz: Path, rel: str) -> bool:
    try:
        from prova import eh_teste
    except Exception:
        return False
    return eh_teste(rel) and existia_na_base(raiz, rel)


# --- 2c. afrouxar a régua (ADR-0046) ------------------------------------------------
# A config do linter, do formatter, do typecheck, da cobertura e dos hooks do git é a
# régua que o gate usa. O agente com um check vermelho tem dois caminhos: consertar o
# código ou baixar a régua — e o segundo é uma linha. É o mesmo motivo de
# `.github/workflows/**` ser protegido, levado às réguas que moram fora do CI (a lista
# vem do config-protection do ECC, MIT). Nasce em `aviso`, como `teste`: migração de
# versão e regra nova do time também editam essas configs, e o valor está no rastro.
# Criar a primeira config é setup, não afrouxamento: só conta o que já existia na base.
REGUA = [
    ".eslintrc", ".eslintrc.*", "eslint.config.*", ".eslintignore",
    ".prettierrc", ".prettierrc.*", "prettier.config.*", ".prettierignore",
    "biome.json", "biome.jsonc", ".biome.json", ".biome.jsonc",
    ".stylelintrc", ".stylelintrc.*", "stylelint.config.*", ".stylelintignore",
    ".markdownlint*", ".markdownlint-cli2.*",
    "ruff.toml", ".ruff.toml", ".flake8", ".pylintrc", "pylintrc",
    "mypy.ini", ".mypy.ini", "pyrightconfig.json", "tsconfig.json", "tsconfig.*.json",
    ".golangci.yml", ".golangci.yaml", ".golangci.toml", ".golangci.json",
    ".rubocop.yml", ".shellcheckrc", ".hadolint.yaml",
    ".coveragerc", ".nycrc", ".nycrc.*", ".c8rc", ".c8rc.*", "codecov.yml", ".codecov.yml",
    ".pre-commit-config.yaml", "lefthook.yml", ".lefthook.yml",
    ".lintstagedrc", ".lintstagedrc.*", "lint-staged.config.*",
]
REGUA_CAMINHO = [".husky/**"]

# A régua também se afrouxa no varejo: o comentário que cala o linter, o typecheck ou a
# cobertura numa linha. `# pragma: no cover` tira a linha do relatório que o `crap` do
# `qualidade.py` lê (ADR-0045). Só conta em código de produção, fora de literal de string.
SUPRESSAO = re.compile(
    r"eslint-disable|@ts-(ignore|nocheck|expect-error)|#\s*noqa\b|#\s*type:\s*ignore"
    r"|pylint:\s*disable|//\s*nolint\b|#\s*nosec\b|pragma:\s*no\s*cover"
    r"|\b(istanbul|c8|v8)\s+ignore\b|prettier-ignore|rubocop:disable|@SuppressWarnings"
    r"|#!?\[allow\(")
LITERAL = re.compile(r"'[^'\n]*'|\"(?:\\.|[^\"\\\n])*\"|`[^`\n]*`")
CODIGO = {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".go",
          ".rb", ".java", ".kt", ".rs", ".php", ".cs", ".swift", ".scala"}


def eh_regua(rel: str) -> bool:
    nome = Path(rel).name.lower()
    return any(fnmatch.fnmatch(nome, p) for p in REGUA) or \
        any(casa(rel, p) for p in REGUA_CAMINHO)


def supressoes(texto: str) -> int:
    return sum(len(SUPRESSAO.findall(LITERAL.sub("", linha))) for linha in texto.splitlines())


def supressao_conta(rel: str) -> bool:
    """Código de produção — teste usa `@ts-expect-error` de propósito."""
    try:
        from prova import eh_teste
    except Exception:
        return False
    return Path(rel).suffix.lower() in CODIGO and not eh_teste(rel)


def antes_e_depois(entrada: dict, alvo: Path) -> tuple[str, str]:
    """O texto que a escrita tira e o que ela põe: Edit, MultiEdit ou Write."""
    if "content" in entrada:
        try:
            atual = alvo.read_text(encoding="utf-8", errors="replace") if alvo.is_file() else ""
        except OSError:
            atual = ""
        return atual, str(entrada.get("content") or "")
    trocas = entrada.get("edits") or [entrada]
    return ("\n".join(str(t.get("old_string") or "") for t in trocas),
            "\n".join(str(t.get("new_string") or "") for t in trocas))


def arquivo_do_cabecalho(origem: str, destino: str) -> str | None:
    """O caminho do arquivo pelo par `---`/`+++`; removido (`+++ /dev/null`) vale a origem."""
    alvo = origem if destino == "/dev/null" else destino
    return alvo[2:] if alvo[:2] in ("a/", "b/") else None


def ler_diff(texto: str) -> dict[str, dict]:
    """Por arquivo do `git diff -U0`: se é novo, as linhas que saíram e as que entraram."""
    arquivos: dict[str, dict] = {}
    atual = None
    origem = ""
    for linha in texto.splitlines():
        if linha.startswith("--- "):
            origem = linha[4:]
        elif linha.startswith("+++ "):
            atual = arquivo_do_cabecalho(origem, linha[4:])
            if atual:
                arquivos[atual] = {"novo": origem == "/dev/null", "mais": [], "menos": []}
        elif atual and linha[:1] in "+-":
            arquivos[atual]["mais" if linha[0] == "+" else "menos"].append(linha[1:])
    return arquivos


def achados_da_regua(arquivos: dict[str, dict]) -> list[str]:
    achados = []
    for rel, d in sorted(arquivos.items()):
        if eh_regua(rel) and not d["novo"]:
            achados.append(f"{rel} — config da régua alterada ou removida")
        elif supressao_conta(rel):
            n = supressoes("\n".join(d["mais"])) - supressoes("\n".join(d["menos"]))
            if n > 0:
                achados.append(f"{rel} — {n} supressão(ões) inline nova(s)")
    return achados


def regua_no_diff(raiz: Path) -> list[str]:
    """A régua no diff contra a base, para o modo CLI: o mesmo critério do hook."""
    from prova import git
    r = git(raiz, "diff", "-U0", "--no-color", ponto_da_base(raiz), "--", timeout=60)
    arquivos = ler_diff(r.stdout) if r.returncode == 0 else {}
    try:  # espelho `linguist-generated` repete o canônico: contaria a mesma régua duas vezes
        from qualidade import gerados
    except ImportError:
        return achados_da_regua(arquivos)
    for rel in gerados(raiz, sorted(arquivos)):
        arquivos.pop(rel, None)
    return achados_da_regua(arquivos)


def afrouxa_a_regua(raiz: Path, rel: str, entrada: dict) -> str | None:
    """Motivo, se a escrita mexe numa régua existente ou adiciona supressão inline."""
    if eh_regua(rel) and existia_na_base(raiz, rel):
        return "edição na régua do projeto (config de lint, formatter, typecheck, " \
               "cobertura ou hooks do git)"
    if supressao_conta(rel):
        antes, depois = antes_e_depois(entrada, raiz / rel)
        if supressoes(depois) > supressoes(antes):
            return "supressão inline adicionada (comentário que cala linter, typecheck " \
                   "ou cobertura)"
    return None


def primeira_vez_na_sessao(payload: dict, rel: str) -> bool:
    """Marcador em $TMPDIR por (sessão, arquivo) — mesma técnica do lembrete de DoD."""
    sid = str(payload.get("session_id") or "sem-sessao")[:32]
    chave = re.sub(r"[^A-Za-z0-9_.-]", "_", rel)[-80:]
    marca = Path(os.environ.get("TMPDIR") or "/tmp") / f"kairos-forge-teste-{sid}-{chave}"
    if marca.exists():
        return False
    try:
        marca.touch()
    except OSError:
        pass
    return True


# --- modo hook: integridade da SPEC -------------------------------------------------

def linhas_incoerentes(texto: str) -> list[str]:
    """Linhas de tabela com Status 'Concluído' e Verificação sem `verificado:`.

    O ritual da fábrica: marcar pronto sem prova de execução é o anti-padrão que a
    coluna Verificação existe para impedir. Aqui isso vira check, não lembrete.
    """
    achados = []
    for linha in texto.splitlines():
        if not LINHA_TABELA.match(linha):
            continue
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        if len(celulas) < 2:
            continue
        if not any(c.lower() == "concluído" or c.lower() == "concluido" for c in celulas):
            continue
        if any(c.lower().startswith("verificado:") for c in celulas):
            continue
        achados.append(linha.strip()[:160])
    return achados


def checar_spec(payload: dict) -> int:
    entrada = payload.get("tool_input") or {}
    caminho = str(entrada.get("file_path") or "")
    if "docs/specs/" not in caminho.replace("\\", "/") or not caminho.endswith(".md"):
        return 0
    try:
        texto = Path(caminho).read_text(encoding="utf-8")
    except Exception:
        return 0
    achados = linhas_incoerentes(texto)
    if not achados:
        return checar_intencao(payload, caminho, texto)
    raiz = Path(payload.get("cwd") or ".")
    modo = modo_de(carregar_config(raiz), "spec")
    registrar_recusa(raiz, "spec", "Concluído sem verificado:", caminho, modo)
    lista = "\n".join(f"  · {a}" for a in achados[:5])
    return bloquear(
        f"SPEC com status inconsistente — {len(achados)} requisito(s) marcado(s) "
        f"'Concluído' sem célula `verificado:`",
        f"Em {relativo(caminho, Path(payload.get('cwd') or '.'))}:\n{lista}",
        "Corrija agora: rode o gate e escreva `verificado: <como confirmei> (<dd/mm>)`, "
        "ou volte o status para 'Em progresso' com `em progresso: <o que falta>`. "
        "O /kairos-forge:validar trataria isso como 'sem evidência' e bloquearia P1.",
        modo,
    )


# --- intenção da SPEC (ADR-0053) -------------------------------------------------------
# Do PDD Kit: requisito que não aponta para quem pediu foi inventado (ADR-0015), e o lugar
# de ver isso é quando a SPEC é escrita, não no PR. Nasce em `aviso`, uma vez por arquivo na
# sessão: o rastro fica sempre. SPEC que já estava na base sem o mapa é de antes da regra e
# passa; com o mapa, vale para ela também.

def requisitos_sem_origem(raiz: Path, rel: str, texto: str) -> list[str]:
    try:
        from painel import intencao_da_spec
    except Exception:
        return []
    i = intencao_da_spec(texto)
    if i["tem_mapa"]:
        return i["sem_origem"]
    return [] if existia_na_base(raiz, rel) else i["ids"]


def checar_intencao(payload: dict, caminho: str, texto: str) -> int:
    raiz = Path(payload.get("cwd") or ".")
    rel = relativo(caminho, raiz)
    faltam = requisitos_sem_origem(raiz, rel, texto)
    if not faltam:
        return 0
    modo = modo_de(carregar_config(raiz), "intencao")
    registrar_recusa(raiz, "intencao", "requisito sem origem no mapa de intenção", rel, modo)
    if modo != "bloqueio" and not primeira_vez_na_sessao(payload, f"intencao:{rel}"):
        return 0
    return bloquear(
        f"requisito sem origem em `{rel}` — {', '.join(faltam[:8])}"
        + (f" e mais {len(faltam) - 8}" if len(faltam) > 8 else ""),
        "Cada requisito aponta, no `## Mapa de intenção`, para de onde veio: o pedido, a "
        "issue, a resposta de um gate, a varredura, um ADR — nas palavras de quem pediu. "
        "Requisito sem origem foi inventado (ADR-0015).",
        "Complete o mapa. O que a fábrica deduziu fica como `inferido`, e a pessoa confirma "
        "na aprovação; o que ninguém pediu e ninguém confirma sai da SPEC ou vira pergunta "
        "aberta.",
        modo,
    )


# --- modo hook: contrato do relatório (ADR-0032) ------------------------------------
# Só morde quando o bloco EXISTE e está errado. Relatório sem bloco passa — o
# `ciclo.py` degrada sozinho (sem contagem, toda rodada queima ficha), e um guardrail
# que exigisse o bloco em todo `.md` de validação quebraria relatório legado.

ALVOS_CONTRATO = [
    ("docs/specs/criticas/", "criticar", "kairos-critica"),
    ("docs/specs/validacoes/", "validar", "kairos-validacao"),
    ("docs/specs/revisoes/", "revisar", "kairos-revisao"),
]


def checar_contrato(payload: dict) -> int:
    entrada = payload.get("tool_input") or {}
    caminho = str(entrada.get("file_path") or "")
    norm = caminho.replace("\\", "/")
    if not norm.endswith(".md"):
        return 0
    alvo = next((a for a in ALVOS_CONTRATO if a[0] in norm), None)
    if alvo is None:
        return 0
    try:
        from contrato import LEITORES
        texto = Path(caminho).read_text(encoding="utf-8")
    except Exception:
        return 0

    _, comando, fence = alvo
    r = LEITORES[comando](texto)
    if r.ok or r.codigo == "ausente":
        return 0

    raiz = Path(payload.get("cwd") or ".")
    modo = modo_de(carregar_config(raiz), "contrato")
    registrar_recusa(raiz, "contrato", r.codigo or "invalido", caminho, modo)

    if r.codigo == "sem_cobertura":
        saida = ("Liste em `verificado`/`examinado` o que você realmente conferiu — "
                 "requisito, gate rodado, arquivo lido. Se a lista está vazia porque você "
                 "não conferiu nada, o veredicto não é limpo: é 'não verificado'.")
    elif "críticos distintos" in (r.erro or ""):
        saida = ("Crítica adversarial exige mais de um olhar, e de quem NÃO escreveu a "
                 "SPEC. Acione um segundo crítico de outra especialidade e liste os dois "
                 "em `criticado_por` — um crítico só é revisão.")
    else:
        saida = (f"Corrija o bloco ```{fence}: ele alimenta o `ciclo.py`, que decide a "
                 "transição e o orçamento por código. Bloco quebrado = decisão cega.")

    return bloquear(
        f"contrato do relatório inválido em `{relativo(caminho, raiz)}` [{r.codigo}]",
        r.erro or "bloco de contrato não passou na validação",
        saida,
        modo,
    )


# --- modo hook: leitura de segredo pela tool Read (ADR-0042) -----------------------

def checar_leitura(payload: dict) -> int:
    entrada = payload.get("tool_input") or {}
    caminho = str(entrada.get("file_path") or "")
    if not caminho:
        return 0
    raiz = Path(payload.get("cwd") or ".")
    rel = relativo(caminho, raiz)
    nome = Path(rel).name
    if SEGREDO_EXCECAO.search(nome):
        return 0
    if not ALVOS_SEGREDO.search(" " + rel) and not ALVOS_SEGREDO.search(" " + caminho):
        return 0
    registrar_recusa(raiz, "segredo", "leitura de segredo pela tool Read", rel, "bloqueio")
    return bloquear(
        f"leitura bloqueada de `{rel}` — arquivo de segredo",
        "O conteúdo entraria no contexto do modelo e no transcript.",
        "Para saber quais variáveis existem, `grep -o '^[A-Z_]*=' .env` lista os nomes "
        "sem os valores. O valor em si é do humano e do processo que o consome.",
    )


# --- modo hook: gate de parada (ADR-0042) -------------------------------------------
# A DoD da fábrica diz "gate rodado antes de encerrar". Até aqui era prosa. Aqui vira
# hook `Stop`: a sessão que escreveu código de produção e não rodou nenhum gate verde
# DEPOIS da última escrita não encerra sem que isso seja dito. É o "ship gate" do
# harness-toolkit com a evidência que a fábrica já grava: a trajetória do execucao.py.
#
# Recorte deliberado: só a sessão atual, só escrita em produção (teste e doc não
# contam), só o que veio depois do último gate verde. Regra que dispara em sessão de
# leitura vira ruído, e ruído vira regra desligada.

def eventos_da_sessao(raiz: Path, sessao: str) -> list[dict]:
    pasta = pasta_da_trajetoria(raiz)
    if not pasta.is_dir():
        return []
    eventos: list[dict] = []
    for arq in sorted(pasta.glob("*.jsonl"))[-2:]:
        try:
            linhas = arq.read_text(encoding="utf-8").splitlines()[-3000:]
        except OSError:
            continue
        for linha in linhas:
            try:
                ev = json.loads(linha)
            except Exception:
                continue
            if ev.get("sessao") == sessao:
                eventos.append(ev)
    return eventos


def pendencia_de_parada(eventos: list[dict]) -> dict | None:
    """Arquivos de produção escritos depois do último gate verde; None se nada pende."""
    ultimo_gate_ok = -1
    for i, ev in enumerate(eventos):
        if ev.get("tipo") == "comando" and ev.get("gate") and ev.get("ok") is True:
            ultimo_gate_ok = i
    pendentes: list[str] = []
    for ev in eventos[ultimo_gate_ok + 1:]:
        if ev.get("tipo") == "escrita" and ev.get("producao"):
            arq = str(ev.get("arquivo") or "?")
            if arq not in pendentes:
                pendentes.append(arq)
    if not pendentes:
        return None
    gates_depois = [ev for ev in eventos[ultimo_gate_ok + 1:]
                    if ev.get("tipo") == "comando" and ev.get("gate")]
    return {"arquivos": pendentes,
            "gates_vermelhos": [g.get("cmd", "")[:80] for g in gates_depois if g.get("ok") is False][-3:],
            "houve_gate_verde": ultimo_gate_ok >= 0}


def gates_declarados(raiz: Path) -> list[str]:
    arq = raiz / "contextos" / "testes.md"
    if not arq.is_file():
        return []
    achados = []
    for linha in arq.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"`([^`]+)`", linha)
        if m and linha.lstrip().startswith(("-", "*")):
            achados.append(m.group(1))
    return achados[:5]


def checar_parada(payload: dict) -> int:
    # Nunca duas vezes na mesma parada: o Claude Code marca `stop_hook_active`; o
    # Cursor conta `loop_count`. Sem isso, gate vermelho viraria laço infinito.
    if payload.get("stop_hook_active") or (payload.get("loop_count") or 0) > 0:
        return 0
    raiz = Path(payload.get("cwd") or ".")
    sessao = str(payload.get("session_id") or "?")[:16]
    pend = pendencia_de_parada(eventos_da_sessao(raiz, sessao))
    if pend is None:
        return 0
    cfg = carregar_config(raiz)
    modo = modo_de(cfg, "parada")
    registrar_recusa(raiz, "parada", "encerrar sem gate verde", ", ".join(pend["arquivos"])[:200], modo)
    lista = "\n".join(f"  · {a}" for a in pend["arquivos"][:8])
    if len(pend["arquivos"]) > 8:
        lista += f"\n  · … e mais {len(pend['arquivos']) - 8}"
    declarados = gates_declarados(raiz)
    dica = ("Gates do projeto (contextos/testes.md): " + " · ".join(f"`{g}`" for g in declarados)
            if declarados else
            "Rode o teste/lint do projeto (o comando de `contextos/testes.md`, ou o padrão do ecossistema).")
    vermelhos = ("\nÚltimos gates, todos vermelhos: " + " · ".join(pend["gates_vermelhos"])
                 if pend["gates_vermelhos"] else "")
    return bloquear(
        f"parada sem prova — {len(pend['arquivos'])} arquivo(s) de produção escrito(s) "
        "sem nenhum gate verde depois",
        f"Escritos depois do último gate verde nesta sessão:\n{lista}{vermelhos}",
        f"{dica}\nDepois, encerre de novo. Se não há gate que cubra isso, diga ao usuário "
        "por quê — a ausência declarada é aceitável; a silenciosa, não (ADR-0042).",
        modo,
    )


# --- adaptador do Cursor (ADR-0042) -------------------------------------------------
# O Cursor manda `command`/`file_path` na raiz do payload, `conversation_id` em vez de
# `session_id` e `workspace_roots` em vez de `cwd`; e espera JSON no stdout, não exit 2.
# Reconhecido pela FORMA, nunca por configuração — o mesmo princípio do harness-toolkit.

_EDITOR: dict = {"cursor": False, "evento": ""}
EVENTOS_PERMISSAO = {"beforeShellExecution", "beforeReadFile", "beforeMCPExecution", "subagentStart"}
EVENTOS_AUDITORIA = {"afterFileEdit", "afterShellExecution", "postToolUse"}


def _entrada_do_cursor(p: dict) -> dict:
    """O `beforeMCPExecution` manda `tool_input` como texto JSON (e, em servidor stdio, a
    linha que lança o servidor em `command`, que não é o que a ferramenta recebe); os
    outros eventos mandam o que importa na raiz do payload."""
    if isinstance(p.get("tool_input"), str):
        try:
            entrada = json.loads(p["tool_input"])
        except ValueError:
            entrada = {}
        return entrada if isinstance(entrada, dict) else {}
    return {k: p[k] for k in ("command", "file_path", "content", "edits") if k in p}


def _ferramenta_do_cursor(p: dict) -> str:
    """O nome no formato do Claude Code, para a mesma regra servir aos dois."""
    if isinstance(p.get("tool_input"), str):
        return f"mcp__{p.get('mcp_server_name') or 'desconhecido'}__{p.get('tool_name') or ''}"
    return "Bash" if "command" in p else str(p.get("tool_name") or "")


def normalizar_payload(payload: dict) -> dict:
    if "conversation_id" not in payload or isinstance(payload.get("tool_input"), dict):
        return payload
    p = dict(payload)
    p["_cursor"] = True
    p["session_id"] = p.get("session_id") or p.get("conversation_id")
    raizes = p.get("workspace_roots") or []
    p["cwd"] = p.get("cwd") or (raizes[0] if raizes else ".")
    p["tool_name"] = _ferramenta_do_cursor(p)
    p["tool_input"] = _entrada_do_cursor(p)
    _EDITOR["cursor"] = True
    _EDITOR["evento"] = str(p.get("hook_event_name") or "")
    return p


def responder_cursor(codigo: int, motivo: str, detalhe: str, saida: str) -> int:
    """Traduz a decisão para o dialeto do Cursor. Sempre exit 0 com JSON no stdout."""
    ev = _EDITOR["evento"]
    texto = f"kairos-forge (guardrail): {motivo}\n\n{detalhe}\n\n{saida}"
    if ev in EVENTOS_PERMISSAO:
        resp = {"permission": "deny" if codigo == 2 else "allow",
                "agent_message": texto, "user_message": motivo}
    elif ev == "stop":
        resp = {"followup_message": texto} if codigo == 2 else {}
    else:
        resp = {"additional_context": texto}
    print(json.dumps(resp, ensure_ascii=False))
    return 0


# --- modo CLI (Codex/OpenCode/Cursor, CI, pre-commit) -------------------------------

def gerados_modificados(raiz: Path) -> list[str]:
    """Artefatos gerados alterados em relação ao HEAD, segundo o git.

    No hook dá para bloquear com precisão porque existe INTENÇÃO de escrita para
    interceptar. Aqui não: o modo CLI roda depois do fato, e o que sobra é observar
    estado. O git é o registro desse estado.

    Fora de um repositório git (ou sem git instalado) devolve vazio — silêncio honesto
    é melhor que achado inventado.
    """
    try:
        r = subprocess.run(["git", "-C", str(raiz), "diff", "--name-only", "HEAD"],
                           capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return []
        nomes = [linha.strip() for linha in r.stdout.splitlines() if linha.strip()]
    except (OSError, subprocess.SubprocessError):
        return []

    achados = []
    for rel in nomes:
        if any(casa(rel, g) for g in GERADOS_PADRAO):
            achados.append(rel)
            continue
        alvo = raiz / rel
        try:
            if alvo.is_file() and MARCA_GERADO in alvo.read_text(
                    encoding="utf-8", errors="replace"):
                achados.append(rel)
        except OSError:
            continue
    return achados


def avisar_regua(raiz: Path) -> list[str]:
    """Régua (ADR-0046) no modo CLI: config de gate alterada ou supressão inline nova no
    diff. Mesma assimetria do `teste`: avisa; endurece com `{"modos": {"regua": "bloqueio"}}`.
    Devolve o problema que reprova, se houver."""
    regua = regua_no_diff(raiz)
    if not regua:
        return []
    duro = (carregar_config(raiz).get("modos", {}) or {}).get("regua") == "bloqueio"
    print(f"{'🛑' if duro else '⚠️ '} {len(regua)} afrouxamento(s) da régua no diff:")
    for achado in regua[:10]:
        print(f"   {achado}")
    print("   Migração de versão e regra nova também mexem aqui — a diferença é o porquê "
          "escrito no commit.")
    return [f"{len(regua)} afrouxamento(s) da régua — `modos.regua` está em bloqueio "
            "neste projeto"] if duro else []


def verificar(alvo: Path) -> int:
    """Sem PreToolUse não há bloqueio prévio — então o mesmo contrato roda depois."""
    problemas: list[str] = []
    raiz = alvo if alvo.is_dir() else alvo.parent

    specs = sorted(raiz.rglob("docs/specs/*.md")) if alvo.is_dir() else (
        [alvo] if "docs/specs/" in str(alvo).replace("\\", "/") else []
    )
    for spec in specs:
        for linha in linhas_incoerentes(spec.read_text(encoding="utf-8")):
            problemas.append(f"{spec}: 'Concluído' sem `verificado:` — {linha}")

    # Contratos de relatório (ADR-0032) — mesmo contrato do hook, rodado depois.
    try:
        from contrato import LEITORES
        for pasta, comando, _ in ALVOS_CONTRATO:
            for rel in sorted(raiz.rglob(f"{pasta}*.md")) if alvo.is_dir() else []:
                r = LEITORES[comando](rel.read_text(encoding="utf-8"))
                if not r.ok and r.codigo != "ausente":
                    problemas.append(f"{rel}: contrato [{r.codigo}] — {r.erro}")
    except Exception:
        pass

    # Artefato gerado (ADR-0037) nos CLIs sem hook e no CI. Default `aviso`, não
    # `bloqueio`, e a assimetria é deliberada: o hook conhece a intenção e por isso
    # pode recusar; aqui só se observa que o arquivo mudou, e mudou por sync legítimo
    # é indistinguível de mudou por edição à mão. Avisar é o que a evidência sustenta.
    # Projeto que quer o check duro põe `{"modos": {"gerado": "bloqueio"}}`.
    if alvo.is_dir():
        modificados = gerados_modificados(raiz)
        if modificados:
            # `modo_de` cai em MODO_PADRAO ("bloqueio"), que é o certo no hook e o
            # errado aqui. No CLI só endurece com opt-in EXPLÍCITO do projeto.
            escolhido = (carregar_config(raiz).get("modos", {}) or {}).get("gerado")
            duro = escolhido == "bloqueio"
            cabeca = "🛑" if duro else "⚠️ "
            print(f"{cabeca} {len(modificados)} artefato(s) gerado(s) modificado(s) "
                  "desde o HEAD:")
            for rel in modificados[:10]:
                print(f"   {rel}")
            if len(modificados) > 10:
                print(f"   … e mais {len(modificados) - 10}")
            print("   Se veio de `sync-multi-cli.py` ou de `instalar`, é esperado — "
                  "commite.\n   Se foi edição à mão, ela some no próximo sync: edite o "
                  "canônico\n   (`agents/<id>.md` ou `skills/<nome>/SKILL.md`) e sincronize.")
            if duro:
                problemas.append(f"{len(modificados)} artefato(s) gerado(s) modificado(s) "
                                 "— `modos.gerado` está em bloqueio neste projeto")

    # Teste existente alterado (ADR-0039) — mesma assimetria do `gerado`: aqui só se
    # observa o diff, e refactor legítimo é indistinguível de afrouxamento pelo git.
    # Avisa com os sinais (asserção removida, caso pulado, arquivo apagado); endurece
    # só com `{"modos": {"teste": "bloqueio"}}`.
    if alvo.is_dir():
        try:
            from prova import testes_alterados
            r = testes_alterados(raiz, None)
        except Exception:
            r = {"testes": []}
        suspeitos = [t for t in r.get("testes", []) if t.get("sinal")]
        if suspeitos:
            duro = (carregar_config(raiz).get("modos", {}) or {}).get("teste") == "bloqueio"
            print(f"{'🛑' if duro else '⚠️ '} {len(suspeitos)} teste(s) existente(s) com sinal "
                  f"de afrouxamento no diff contra {r.get('base')}:")
            for t in suspeitos[:10]:
                if t["status"] == "D":
                    print(f"   {t['arquivo']} — arquivo removido")
                else:
                    print(f"   {t['arquivo']} — {len(t['assercoes_removidas'])} asserção(ões) "
                          f"removida(s), {len(t['casos_removidos'])} caso(s) removido(s), "
                          f"{len(t['pulos_adicionados'])} pulo(s) adicionado(s)")
            print("   Refactor legítimo também muda teste — a diferença é a justificativa "
                  "escrita.\n   Detalhe: `python3 scripts/prova.py testes-alterados`.")
            if duro:
                problemas.append(f"{len(suspeitos)} teste(s) existente(s) com sinal de "
                                 "afrouxamento — `modos.teste` está em bloqueio neste projeto")
        problemas += avisar_regua(raiz)  # a régua no diff (ADR-0046)

    for padrao, motivo in PROTEGIDOS_PADRAO[:5]:  # só os de segredo, não o de CI
        for achado in raiz.rglob(padrao.replace("**/", "")):
            if not achado.is_file() or ".git/" in str(achado):
                continue
            # As mesmas exceções do hook de escrita: `.env.example` existe para ser versionado.
            if any(casa(achado.name, exc) for exc in EXCECOES):
                continue
            problemas.append(f"{achado}: {motivo} versionado no projeto?")

    if problemas:
        print(f"🛑 guardrail: {len(problemas)} achado(s)")
        for p in problemas:
            print(f"  ✗ {p}")
        return 1
    print("✅ guardrail: sem achados")
    return 0


# --- faixa 3 na execução (ADR-0052) --------------------------------------------------
# A faixa 3 do ADR-0031 é "difícil de reverter: humano decide, sempre". Até aqui ela era
# decidida na revisão e no PR, depois do fato: o agente do arco, em modo automático, podia
# aplicar infraestrutura, publicar um pacote ou migrar um banco de verdade na fase
# `construindo`, e a revisão só via o código. Este modo diz, para uma chamada de
# ferramenta, se o efeito dela sai do repositório de um jeito que um revert não desfaz.
# Quem pergunta à pessoa é o mod do Claude Code (`hooks/pausa.ts`): o `ask` de um mod é
# sempre de uma pessoa, nenhum classificador o aprova, e onde ninguém pode ser perguntado
# ele vira recusa. Aqui só a regra, que nunca bloqueia sozinha: sai JSON, exit 0.
#
# Precisão importa mais que cobertura, como nos comandos destrutivos: pausa que pergunta
# toda hora é pausa que a pessoa aprende a aprovar sem ler. Ensaio (`--dry-run`,
# `terraform plan`, `--check`) passa, migration em banco local passa, leitura passa.

IRREVERSIVEIS = [
    (r"\b(terraform|tofu|terragrunt)\b.*\b(apply|destroy|import|state\s+(rm|mv|push))\b",
     "aplica ou destrói infraestrutura"),
    (r"\bpulumi\b.*\b(up|update|destroy|import|state\s+delete)\b", "aplica ou destrói infraestrutura"),
    (r"\b(cdk|sam|serverless|sls)\b.*\b(deploy|destroy|remove)\b", "faz deploy ou remove uma stack"),
    (r"\bkubectl\b.*\b(apply|create|delete|replace|patch|scale|drain|edit|rollout\s+(restart|undo)"
     r"|set\s+image)\b", "muda um cluster Kubernetes"),
    (r"\bhelm\b.*\b(install|upgrade|uninstall|delete|rollback)\b", "muda um release do Helm"),
    (r"\bargocd\b.*\bapp\s+(sync|delete|rollback)\b", "sincroniza ou apaga uma aplicação no Argo CD"),
    (r"\bansible-playbook\b", "roda um playbook do Ansible contra máquinas"),
    (r"\b(fly|flyctl)\s+(deploy|destroy|apps\s+destroy|scale|secrets\s+(set|unset))\b",
     "faz deploy ou muda o app no Fly"),
    (r"\bvercel\b.*(--prod\b|\b(promote|remove|rm|rollback)\b|\benv\s+(add|rm)\b)",
     "publica em produção na Vercel"),
    (r"\bnetlify\b.*\bdeploy\b.*--prod\b", "publica em produção na Netlify"),
    (r"\bheroku\b.*\b(releases:rollback|ps:scale|pg:reset|apps:destroy|config:(set|unset))\b",
     "muda o app no Heroku"),
    (r"\bgit\s+push\b.*\b(heroku|dokku)\b", "faz deploy por git push"),
    (r"\b(firebase|railway|eb)\b.*\b(deploy|up|down|terminate)\b", "faz deploy ou derruba um ambiente"),
    (r"\b(docker|podman)(\s+compose)?\s+(image\s+)?push\b", "publica uma imagem num registry"),
    (r"\b(npm|pnpm|yarn|bun)\b.*\b(publish|unpublish|deprecate)\b", "publica um pacote"),
    (r"\bcargo\s+(publish|yank|owner)\b", "publica um pacote"),
    (r"\b(twine|flit)\s+(upload|publish)\b|\b(poetry|uv|hatch|pdm)\s+publish\b", "publica um pacote"),
    (r"\bgem\s+(push|yank)\b|\bdotnet\s+nuget\s+(push|delete)\b|\bmvn\b.*\bdeploy\b",
     "publica um pacote"),
    (r"\bgh\s+release\s+(create|delete|edit|upload)\b", "publica ou muda um release"),
    (r"\bgit\s+push\b.*(--tags\b|\brefs/tags/)", "publica tags"),
    (r"\bgit\s+push\b.*[\s:](main|master|production|prod)(\s|$)",
     "empurra direto para a branch principal, sem o PR que fecha o arco"),
    (r"\bgh\s+(secret|variable)\s+(set|delete|remove)\b", "muda segredo ou variável do repositório"),
    (r"\bvault\b.*\b(write|delete|destroy|kv\s+(put|patch|delete|destroy)|token\s+revoke)\b",
     "muda segredo no Vault"),
    (r"\bdoppler\s+secrets\s+(set|delete)\b|\bop\s+item\s+(create|edit|delete)\b",
     "muda segredo num cofre"),
    (r"\baws\s+(?!configure\b)\S+\s+(create|delete|put|update|modify|terminate|run|start|stop|reboot|attach|detach"
     r"|associate|disassociate|authorize|revoke|deregister|register|rotate|restore|reset|cancel"
     r"|invoke|publish|send|set|import|replace|enable|disable|apply)-?\S*", "muda recursos na AWS"),
    (r"\baws\s+s3\s+(rm|rb|mv)\b|\baws\s+s3\s+(sync|cp)\b.*\s(s3://\S+)\s*$|\baws\s+s3\s+sync\b.*--delete",
     "escreve ou apaga num bucket S3"),
    (r"\bgcloud\s+(?!components\b|config\b|auth\b)\S.*\b(create|delete|deploy|update|patch|import|restore|reset|set-iam-policy"
     r"|add-iam-policy-binding|remove-iam-policy-binding)\b", "muda recursos no Google Cloud"),
    (r"\bgsutil\s+(rm|rb|mv)\b|\bgsutil\b.*\brsync\b.*\s-d\b", "escreve ou apaga num bucket"),
    (r"\baz\s+(?!account\b|login\b|config\b|extension\b)\S.*\b(create|delete|update|deploy|purge|restart"
     r"|stop)\b", "muda recursos no Azure"),
    (r"\bdoctl\b.*\b(create|delete|deploy|update)\b", "muda recursos na DigitalOcean"),
    (r"\b(sk|rk)_live_\w+", "usa uma chave de produção de pagamento"),
    (r"\bstripe\b.*(--live\b|\b(refunds|payouts|transfers|charges|payment_intents|subscriptions)"
     r"\s+(create|cancel|update|capture|confirm|delete)\b)", "movimenta dinheiro no Stripe"),
    (r"\bprisma\s+migrate\s+deploy\b", "aplica migrations no banco de destino"),
    (r"\bsupabase\s+db\s+push\b(?!.*--local)|\bsupabase\s+db\s+reset\b.*--linked",
     "aplica migrations no projeto remoto do Supabase"),
    (r"(^|[\s/])(make|just|task|rake|mage|cap|invoke)\s+(\S+\s+)*?(deploy\S*|publish\S*|release"
     r"|rollout|promote|ship|production|prod)(\s|$)", "roda um alvo de deploy ou release"),
    (r"\b(npm|pnpm|yarn|bun)\s+(run\s+)?(deploy\S*|publish\S*|release|promote|ship)(\s|$)",
     "roda um script de deploy ou release"),
    (r"^((\w+=\S*|sudo|bash|sh|zsh|python3?|node|ruby|bun|npx|tsx)\s+)*(\S*/)?(deploy|release|publish)\w*"
     r"(\.(sh|py|rb|ts|js|mjs))?(\s|$)", "roda um script de deploy ou release"),
]
IRREVERSIVEIS = [(re.compile(p, re.I), efeito) for p, efeito in IRREVERSIVEIS]

# Ensaio não muda nada: o mesmo comando com um destes passa.
ENSAIO = re.compile(r"(?<![\w-])(--dry-run(=\S+)?|--check|--what-if|--preview|--diff|--help)(?![\w-])")
TRECHOS = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")

# Migration em banco local é trabalho de `construindo`; em produção ou banco remoto, não.
MIGRACAO = re.compile(
    r"\balembic\s+(upgrade|downgrade|stamp)\b|\b(rails|rake|bin/rails)\s+db:(migrate|rollback|drop"
    r"|reset|schema:load|seed|setup)\b|\bmanage\.py\s+(migrate|flush|loaddata)\b|\bknex\s+migrate:"
    r"|\bsequelize(-cli)?\s+db:|\btypeorm\b.*\b(migration:(run|revert)|schema:(drop|sync))\b"
    r"|\b(goose|dbmate)\s+(up|down|reset|drop|migrate|rollback)\b|\batlas\s+(migrate|schema)\s+apply\b"
    r"|\bflyway\s+(migrate|clean|undo|repair)\b|\bliquibase\s+(update|rollback|drop-all)\b"
    r"|\bprisma\s+(migrate\s+(dev|reset|resolve)|db\s+(push|execute|seed))\b"
    r"|\bmix\s+ecto\.(migrate|rollback|drop|reset)\b|\b(diesel|sqlx)\b.*\b(run|revert|redo|drop|reset)\b"
    r"|\bdrizzle-kit\s+(push|migrate|drop)\b", re.I)
PRODUCAO = re.compile(
    r"\b(RAILS_ENV|RACK_ENV|NODE_ENV|APP_ENV|MIX_ENV|FLASK_ENV|ENVIRONMENT|STAGE|ENV)=['\"]?"
    r"(prod|production)\b|--(env|environment|stage|profile)[= ](prod|production)\b"
    r"|(?<![\w-])-e\s+(prod|production)\b|\b(settings|config)[./_-]prod(uction)?\b", re.I)
CLIENTE_DE_BANCO = re.compile(r"(^|[\s/])(psql|pg_restore|mysql|mariadb|mongosh|mongo|redis-cli"
                              r"|sqlcmd|cqlsh|clickhouse-client)(\s|$)")
HOST = re.compile(r"(?:^|\s)(?:-h\s*|--host[= ])([^\s'\";]+)"
                  r"|\b[a-z][a-z0-9+.-]*://(?:[^@/\s'\"]*@)?(\[[^\]]+\]|[^/:\s?'\"]+)", re.I)
HOSTS_LOCAIS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]", "host.docker.internal",
                "db", "database", "postgres", "postgresql", "mysql", "mariadb", "mongo",
                "mongodb", "redis"}


def _host_remoto(trecho: str) -> str | None:
    for m in HOST.finditer(trecho):
        host = (m.group(1) or m.group(2) or "").lower()
        if host and host not in HOSTS_LOCAIS and not host.endswith((".local", ".localhost")):
            return host
    return None


def _efeito_de_banco(trecho: str, cmd: str) -> str | None:
    """Migration com marca de produção ou banco remoto, e cliente de banco fora da máquina.
    O `cmd` inteiro vale para a marca de produção, que costuma vir num `export` antes do `&&`."""
    remoto = _host_remoto(trecho)
    if MIGRACAO.search(trecho) and (PRODUCAO.search(cmd) or remoto):
        return "aplica migration num banco de produção ou remoto"
    if CLIENTE_DE_BANCO.search(trecho) and remoto:
        return f"conecta a um banco fora da máquina ({remoto})"
    return None


def _efeito_do_trecho(trecho: str, cmd: str) -> str | None:
    if not trecho.strip() or ENSAIO.search(trecho):
        return None
    return (next((e for padrao, e in IRREVERSIVEIS if padrao.search(trecho)), None)
            or _efeito_de_banco(trecho, cmd))


def efeito_irreversivel(cmd: str) -> str | None:
    """O efeito fora do repositório que um revert não desfaz, ou None. Trecho a trecho:
    `npm publish --dry-run && npm publish` pausa pelo segundo."""
    return next((e for t in TRECHOS.split(cmd) if (e := _efeito_do_trecho(t, cmd))), None)


# Ferramenta de MCP pelo nome: o servidor é de fora, e o `isReadOnly` que ele declara não
# prova nada. Só os verbos que um revert não desfaz.
MCP_IRREVERSIVEL = re.compile(
    r"deploy|apply_migration|execute_sql|run_sql|execute_query|delete|drop|destroy|purge|truncate"
    r"|publish|release|promote|rollback|merge|transfer|refund|payout|charge|capture|send_(email|message|sms)"
    r"|post_message|secret|credential|rotate|revoke", re.I)


def efeito_da_ferramenta(ferramenta: str, entrada: dict) -> str | None:
    if ferramenta == "Bash":
        return efeito_irreversivel(str(entrada.get("command") or ""))
    if ferramenta.startswith("mcp__"):
        nome = ferramenta.split("__", 2)[-1]
        if MCP_IRREVERSIVEL.search(nome):
            return f"chama `{nome}` num serviço de fora"
    return None


def quadros_abertos(raiz: Path) -> list[str]:
    pasta = pasta_do_estado(raiz, "quadro")
    if not pasta.is_dir():
        return []
    abertos = []
    for p in sorted(pasta.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not d.get("encerrado_em"):
            abertos.append(str(d.get("slug") or p.stem))
    return abertos


def contexto_da_pausa(raiz: Path, cfg: dict) -> tuple[str, str | None] | None:
    """Por que a autonomia está ligada aqui, e a SPEC do ciclo (para o `escalar`), ou None.

    Fora do arco a pessoa já está no circuito pelas permissões de sempre; a pausa existe
    para quando ela saiu dele. `"faixa_3": "sempre"` em `.agents/guardrails.json` estende
    a pausa para fora do arco — o arquivo que só o humano escreve.
    """
    ciclos = ciclos_abertos(raiz)
    if ciclos:
        c = ciclos[0]
        return (f"o ciclo {c.get('spec')} está em `{c.get('estado')}`", c.get("spec"))
    quadros = quadros_abertos(raiz)
    if quadros:
        return (f"a mobilização `{quadros[0]}` está em andamento", None)
    if cfg.get("faixa_3") == "sempre":
        return ("o projeto pediu a pausa da faixa 3 sempre (`.agents/guardrails.json`)", None)
    return None


# No Cursor (ADR-0055), o `ask` de um hook não chega a uma pessoa em todo modo: no
# Auto-review, quando o classificador do próprio Cursor acha o comando seguro, a pergunta
# é ignorada e o comando roda (fórum do Cursor, 3.21.16, confirmado pela equipe). `deny`
# vale em todos os modos. Pergunta que um classificador responde não é a pausa da faixa 3,
# então ali ela nasce como recusa com o cartão; quem não usa o Auto-review e quer a
# pergunta liga `"faixa_3_cursor": "perguntar"` em `.agents/guardrails.json`.

def cartao(efeito: str, porque: str, escalar: str, recusa: bool) -> str:
    inicio = (f"⏸️ kairos-forge, pausa da faixa 3: esta chamada {efeito}, e um revert no código "
              f"não desfaz isso. Ela para por uma pessoa porque {porque}: a autonomia da fábrica "
              f"não cobre ação irreversível (ADR-0024, ADR-0031).")
    if not recusa:
        return (f"{inicio} Permita só se você conferiu o alvo. Recusada, a fábrica não "
                f"contorna: registra {escalar} e espera.")
    return (f"{inicio} No Cursor, a pergunta de um hook não chega a uma pessoa em todo modo "
            f"(no Auto-review, o classificador a libera), então a chamada foi recusada aqui "
            f"(ADR-0055). Não contorne: não troque o comando, não o embrulhe num script. "
            f"Registre {escalar}, mostre o comando à pessoa e espere: quem roda é ela, no "
            f"terminal dela, ou ela liga `\"faixa_3_cursor\": \"perguntar\"` em "
            f"`.agents/guardrails.json`.")


def _responder_pausa(pausa: dict | None) -> int:
    """No Claude Code, o JSON que o mod lê; no Cursor, a decisão no dialeto dele, que
    recusa a ação inteira se a resposta não bate com o esquema."""
    if not _EDITOR["cursor"]:
        print(json.dumps(pausa or {"pausa": False}))
    elif pausa is None:
        print(json.dumps({"permission": "allow"}))
    else:
        print(json.dumps({"permission": pausa["decisao"],
                          "user_message": (pausa["razao"] if pausa["decisao"] == "ask" else
                                           f"kairos-forge recusou (faixa 3): {pausa['efeito']}"),
                          "agent_message": pausa["razao"]}))
    return 0


def raiz_da_chamada(payload: dict) -> Path:
    """A pasta com `.git` mais próxima do `cwd` do payload. O comando pode rodar numa
    subpasta (`cd infra && terraform apply`, ou o `cwd` que o Cursor manda), e o ciclo
    aberto mora na raiz: procurar só no `cwd` deixaria a pausa passar."""
    cwd = str(payload.get("cwd") or ".")
    try:
        from execucao import raiz_do_checkout
        return raiz_do_checkout(cwd)
    except Exception:
        return Path(cwd)


def _decidir_pausa(efeito: str, contexto: tuple[str, str | None], cfg: dict) -> dict:
    porque, spec = contexto
    escalar = (f"`ciclo.py escalar {spec} --motivo \"faixa 3: {efeito}\"`" if spec
               else "o quadro bloqueado com o motivo")
    recusa = _EDITOR["cursor"] and cfg.get("faixa_3_cursor") != "perguntar"
    return {"pausa": True, "efeito": efeito, "contexto": porque, "spec": spec,
            "decisao": "deny" if recusa else "ask",
            "razao": cartao(efeito, porque, escalar, recusa)}


def checar_faixa3(payload: dict) -> int:
    """Modo `faixa3`: diz se a chamada para por uma pessoa — ao mod do Claude Code ou, no
    Cursor, direto como `deny` (ou `ask`, se o projeto pediu). Sempre exit 0."""
    raiz = raiz_da_chamada(payload)
    ferramenta = str(payload.get("tool_name") or "")
    entrada = payload.get("tool_input") or {}
    cfg = carregar_config(raiz)
    efeito = efeito_da_ferramenta(ferramenta, entrada)
    contexto = contexto_da_pausa(raiz, cfg) if efeito else None
    if not efeito or not contexto:
        return _responder_pausa(None)
    pausa = _decidir_pausa(efeito, contexto, cfg)
    registrar_evento(raiz, {"tipo": "pausa", "classe": "faixa3", "regra": efeito,
                            "alvo": str(entrada.get("command") or ferramenta)[:200],
                            "spec": pausa["spec"], "decisao": pausa["decisao"],
                            "cli": "cursor" if _EDITOR["cursor"] else "claude"})
    return _responder_pausa(pausa)


# --- segredo na saída de ferramenta (ADR-0056) ----------------------------------------
# A leitura de segredo pelo shell e pela `Read` é negada antes (ADR-0042). Mas o segredo
# também chega pela saída: `env`, `docker inspect`, `kubectl get secret -o yaml`, o teste
# que imprime a `DATABASE_URL`, o `git log -p` com uma chave antiga. O que entra no
# contexto vai à API na resposta seguinte e fica no transcript. O mod `hooks/segredo.ts`
# passa a saída do Bash e das ferramentas de MCP por aqui, e o valor vira uma marca antes
# de o modelo ver. Só formatos de alta precisão: o falso positivo esconde um valor da
# saída; o falso negativo manda o segredo para fora.

MARCA_SEGREDO = "«segredo ocultado pelo kairos-forge: {tipo}»"
# Valor de variável secreta: um token inteiro, terminado por espaço, aspas ou pontuação,
# que não começa como referência (`$X`, `<seu-token>`, `{{ }}`, `***`). Assim
# `api_key = os.environ["API_KEY"]` e `token = get_token()` não são valor.
VALOR = r"(?![$<{%*])([A-Za-z0-9_\-+/=.:@!#^&~]{8,})(?=[\s'\",;}\]]|$)"
SEGREDOS_NA_SAIDA: list[tuple[re.Pattern, str, int]] = [    # (padrão, tipo, grupo do valor)
    (re.compile(r"-----BEGIN ([A-Z ]*)PRIVATE KEY-----[\s\S]*?(?:-----END \1PRIVATE KEY-----|\Z)"),
     "chave privada", 0),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "chave de acesso AWS", 0),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b"), "token GitHub", 0),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"), "token GitLab", 0),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "token Slack", 0),
    (re.compile(r"\b[rs]k_(?:live|test)_[A-Za-z0-9]{16,}\b"), "chave Stripe", 0),
    (re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"), "chave de API de modelo", 0),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "chave de API Google", 0),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "JWT", 0),
    (re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:([^\s@/]{3,})@"), "senha em URL de conexão", 1),
    (re.compile(r"\b[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_KEY|ACCESS_KEY)"
                r"[A-Z0-9_]*['\"]?\s*[=:]\s*['\"]?" + VALOR), "valor de variável secreta", 1),
    (re.compile(r"\b(?:password|passwd|secret|token|api_?key|access_?key|private_?key"
                r"|client_?secret|auth_?token)['\"]?\s*[=:]\s*['\"]?" + VALOR), "valor de chave secreta", 1),
]


def ocultar_segredos(texto: str) -> tuple[str, list[str]]:
    """O texto com cada segredo trocado pela marca, e o tipo de cada um, em ordem."""
    tipos: list[str] = []
    for padrao, tipo, grupo in SEGREDOS_NA_SAIDA:
        def trocar(m: re.Match, tipo: str = tipo, grupo: int = grupo) -> str:
            tipos.append(tipo)
            inteiro, base = m.group(0), m.start()
            return (inteiro[:m.start(grupo) - base] + MARCA_SEGREDO.format(tipo=tipo)
                    + inteiro[m.end(grupo) - base:])
        texto = padrao.sub(trocar, texto)
    return texto, tipos


def aviso_de_segredo(ferramenta: str, tipos: list[str], ocultar: bool) -> str:
    contagem = ", ".join(f"{t} ({tipos.count(t)})" for t in dict.fromkeys(tipos))
    inicio = f"🔒 kairos-forge: a saída de `{ferramenta}` tinha {len(tipos)} segredo(s) — {contagem}"
    if not ocultar:
        return (f"{inicio}, deixados como estão (`\"modos\": {{\"saida\": \"aviso\"}}` em "
                f"`.agents/guardrails.json`). Não copie o valor para arquivo, commit, PR ou "
                f"mensagem, e avise a pessoa: ele pode ter de ser trocado (ADR-0056).")
    return (f"{inicio}, ocultados antes de chegar a você (ADR-0056). Não tente recuperar o valor: "
            f"não rode o comando de outro jeito nem leia o arquivo da saída. Se a tarefa precisa "
            f"dele, peça à pessoa. E avise que ele apareceu no terminal: pode ter de ser trocado.")


def checar_saida(payload: dict) -> int:
    """Modo `saida`: oculta o segredo que apareceu na saída de uma ferramenta, antes de o
    modelo ver, e grava o achado na trajetória sem o valor. Sempre exit 0."""
    raiz = raiz_da_chamada(payload)
    textos = payload.get("textos") if isinstance(payload.get("textos"), dict) else {}
    ocultos, tipos = {}, []
    for campo, texto in textos.items():
        ocultos[campo], achados = ocultar_segredos(str(texto))
        tipos += achados
    if not tipos:
        print(json.dumps({"achados": 0}))
        return 0
    ferramenta = str(payload.get("tool_name") or "")
    ocultar = modo_de(carregar_config(raiz), "saida") == "bloqueio"
    comando = ocultar_segredos(str((payload.get("tool_input") or {}).get("command") or ferramenta))[0]
    registrar_evento(raiz, {"tipo": "segredo_na_saida", "classe": "saida",
                            "regra": ", ".join(dict.fromkeys(tipos)), "quantos": len(tipos),
                            "alvo": comando[:200], "modo": "bloqueio" if ocultar else "aviso"})
    print(json.dumps({"achados": len(tipos), "ocultar": ocultar,
                      "textos": ocultos if ocultar else textos,
                      "aviso": aviso_de_segredo(ferramenta, tipos, ocultar)}))
    return 0


def ocultar_arquivos(arquivos: list[Path]) -> int:
    """Modo CLI `ocultar` (ADR-0057): troca, no próprio arquivo, cada segredo pela marca.

    Para o texto que um gatilho de CI vai publicar — o parecer da revisão, a triagem, a
    auditoria, o diagnóstico da correção. O agente que leu um segredo no repositório
    pode repeti-lo no relatório, e o comentário é público. Sai 0 sempre: publicar a
    versão oculta é o que se quer; o achado vai para o stderr, que fica no log do job.
    """
    for arq in arquivos:
        try:
            texto = arq.read_text(encoding="utf-8")
        except OSError as erro:
            print(f"⚠️  kairos-forge: {arq}: {erro.strerror or erro}", file=sys.stderr)
            continue
        oculto, tipos = ocultar_segredos(texto)
        if tipos:
            arq.write_text(oculto, encoding="utf-8")
            contagem = ", ".join(f"{t} ({tipos.count(t)})" for t in dict.fromkeys(tipos))
            print(f"🔒 kairos-forge: {arq}: {len(tipos)} segredo(s) ocultado(s) antes de "
                  f"publicar — {contagem}", file=sys.stderr)
    return 0


MODOS = {"comando": checar_comando, "escrita": checar_escrita, "spec": checar_spec,
         "contrato": checar_contrato, "leitura": checar_leitura, "parada": checar_parada,
         "faixa3": checar_faixa3, "saida": checar_saida}


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__.strip())
        return 1

    if args[0] == "verificar":
        alvo = Path(args[1]) if len(args) > 1 else Path.cwd()
        return verificar(alvo)
    if args[0] == "ocultar":
        return ocultar_arquivos([Path(a) for a in args[1:]])

    modo = MODOS.get(args[0])
    if modo is None:
        print(__doc__.strip())
        return 1
    payload: dict = {}
    try:
        bruto = sys.stdin.read()
        payload = normalizar_payload(json.loads(bruto) if bruto.strip() else {})
        return modo(payload)
    except Exception as erro:
        return falhar_aberto(args[0], payload, erro)


def falhar_aberto(modo: str, payload: dict, erro: Exception) -> int:
    """Guardrail quebrado nunca trava a sessão: bloquear por bug próprio seria pior que a
    ausência do check. Mas falhar aberto em silêncio é o guardrail sumir sem ninguém ver
    (ADR-0046, do ECC): o erro vai para a trajetória, que o `/auditar` lê, e para o stderr.
    """
    raiz = Path(payload.get("cwd") or os.getcwd())
    descricao = f"{type(erro).__name__}: {erro}"[:200]
    registrar_evento(raiz, {"tipo": "guardrail_erro", "modo": modo, "erro": descricao})
    print(f"⚠️  kairos-forge: o guardrail ({modo}) falhou e deixou passar — {descricao}. "
          "Registrado em .agents/execucoes/.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
