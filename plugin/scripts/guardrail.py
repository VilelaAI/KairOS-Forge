#!/usr/bin/env python3
"""guardrail.py — guardrails determinísticos da fábrica (ADR-0022).

O whitepaper Day-1 define hooks como *"deterministic code that runs at specific
lifecycle points... the place for things the agent should never forget but often
does"*. Até a v0.17 os hooks do kairos-forge só imprimiam texto: o PostToolUse
sugeria lembrar do Ricardo e não impedia nada. As regras duras da fábrica moravam
todas em prosa que o modelo pode driftar — a inversão exata do que o paper
recomenda.

Este script é a parte que **bloqueia**. Oito classes de risco:

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
  8. Fiação dos hooks        — escrita que mexe no bloco `hooks` de
                               `.claude/settings*.json`, ou em `.cursor/hooks.json`
                               e `.codex/hooks.json`: silenciaria o guardrail inteiro
                               de uma vez (ADR-0042). Piso, como os sagrados

Mais três regras de comando no piso (ADR-0042), inspiradas no harness-toolkit do
Tech Leads Club: destruição fora do projeto (`rm -rf` em caminho absoluto que não é
o repositório nem temp), destruição não provável (`rm -rf` cujo alvo vem de variável
ou substituição — não dá para provar o que apaga antes de rodar) e controle da
máquina (`shutdown`, `reboot`, `poweroff`).

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

Os mesmos modos servem ao Cursor (ADR-0042): `.cursor/hooks.json`, gerado pelo sync,
chama este script nos eventos `beforeShellExecution`, `beforeReadFile`, `afterFileEdit`
e `stop`. O payload do Cursor é reconhecido pela forma (`conversation_id` sem
`tool_input`) e normalizado; a resposta sai no dialeto dele (`permission`,
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
      "modos":           {"contrato": "aviso"}     // por classe (ADR-0030):
    }                                              // bloqueio (default) | aviso

Classes de regra, para o campo `modos`: `comando`, `protegido`, `gerado`, `spec`,
`contrato`, `teste`, `parada`. Todas nascem em `bloqueio`, menos `teste` e `parada`,
que nascem em `aviso` (refactor legítimo também edita teste, e sessão de leitura
também termina sem gate — a regra existe para deixar rastro; promova a `bloqueio`
quando a taxa de aviso cair).
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
    # --- piso do ADR-0042 ---
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
    # condicional (só o bloco `hooks` de settings*.json — ver `mexe_na_fiacao`).
    (".cursor/hooks.json", "a fiação dos hooks do Cursor — apagar isto silencia o guardrail (ADR-0042)"),
    (".codex/hooks.json", "a fiação dos hooks do Codex — apagar isto silencia o guardrail (ADR-0042)"),
]
FIACAO_CLAUDE = [".claude/settings.json", ".claude/settings.local.json"]


def mexe_na_fiacao(entrada: dict, alvo: Path) -> bool:
    """Escrita em settings*.json do Claude Code que altera o bloco `hooks`.

    O agente edita settings.json por motivos legítimos (permissões, env). O que não
    pode é mexer na fiação. Write: compara o `hooks` atual com o novo. Edit: se a
    string trocada toca `hooks`, `guardrail` ou `kairos-forge`, é fiação.
    """
    try:
        atual = json.loads(alvo.read_text(encoding="utf-8")) if alvo.is_file() else {}
    except Exception:
        atual = {}
    if "content" in entrada:  # Write
        try:
            novo = json.loads(str(entrada.get("content") or ""))
        except Exception:
            return bool(atual.get("hooks"))  # conteúdo ilegível sobre um arquivo com hooks
        return (atual.get("hooks") or {}) != (novo.get("hooks") or {})
    trecho = str(entrada.get("old_string") or "") + str(entrada.get("new_string") or "")
    return bool(re.search(r"hooks|guardrail|execucao\.py|kairos-forge", trecho))

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
MODO_PADRAO_POR_CLASSE = {"teste": "aviso", "parada": "aviso"}


def modo_de(cfg: dict, classe: str) -> str:
    padrao = MODO_PADRAO_POR_CLASSE.get(classe, MODO_PADRAO)
    modo = (cfg.get("modos", {}) or {}).get(classe) or cfg.get("modo") or padrao
    return modo if modo in ("bloqueio", "aviso") else padrao


def registrar_recusa(raiz: Path, classe: str, regra: str, alvo: str, modo: str) -> None:
    """Grava a tentativa na trajetória.

    O bloqueio funcionou e o agente segue em frente — mas *ter tentado* é sinal, e sinal
    que não é registrado não existe. Um agente que passa na validação alcançando ferramenta
    que não tem não está passando (ADR-0030).
    """
    try:
        pasta = raiz.resolve() / ".agents" / "execucoes"
        pasta.mkdir(parents=True, exist_ok=True)
        evento = {
            "t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sessao": (os.environ.get("CLAUDE_SESSION_ID") or "?")[:16],
            "tipo": "recusa",
            "classe": classe,
            "regra": regra[:120],
            "alvo": alvo[:200],
            "modo": modo,
        }
        with (pasta / f"{datetime.now(timezone.utc):%Y-%m}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(evento, ensure_ascii=False) + "\n")
    except Exception:
        pass  # registro nunca derruba o guardrail


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

def ciclo_aberto(raiz: Path) -> dict | None:
    """O ciclo do /entregar em andamento, se houver. None quando não há máquina rodando."""
    pasta = raiz / ".agents" / "ciclo"
    if not pasta.is_dir():
        return None
    for p in sorted(pasta.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("estado") not in ("encerrado", "escalado"):
            return d
    return None


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
    ciclo = ciclo_aberto(raiz)
    if ciclo:
        if FECHA_PR.search(cmd):
            registrar_recusa(raiz, "ciclo", "merge durante ciclo aberto", cmd[:200], "bloqueio")
            return bloquear(
                "merge de PR bloqueado durante um ciclo do /kairos-forge:entregar",
                f"Ciclo {ciclo['spec']} em '{ciclo['estado']}'.",
                "O arco termina no PR — a decisão de integrar é do dono do repositório "
                "(ADR-0023). Peça o merge ao usuário.",
            )
        if ABRE_PR.search(cmd) and ciclo.get("estado") != "pronto_para_pr":
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

    # Piso (ADR-0042): sem `modos`, sem `comandos_extra` que afrouxe.
    motivo = le_segredo(cmd)
    if motivo:
        registrar_recusa(raiz, "segredo", motivo, cmd[:200], "bloqueio")
        return bloquear(
            f"comando bloqueado — {motivo}",
            f"Comando: {cmd[:300]}",
            "Segredo lido pelo shell vai para o transcript e para a trajetória. Para saber "
            "se uma variável existe, `grep -c NOME .env` responde sem mostrar o valor; para "
            "usá-la, deixe o processo ler o arquivo (`source`, dotenv) sem imprimir.",
        )
    motivo = destroi_fora_do_projeto(cmd, str(raiz))
    if motivo:
        registrar_recusa(raiz, "comando", motivo, cmd[:200], "bloqueio")
        return bloquear(
            f"comando bloqueado — {motivo}",
            f"Comando: {cmd[:300]}",
            "Este guardrail só deixa apagar dentro do repositório ou em temp. Fora disso, "
            "quem apaga é o humano.",
        )

    regras = list(COMANDOS) + [(r, "regra do projeto") for r in cfg.get("comandos_extra", [])]
    modo = modo_de(cfg, "comando")
    for padrao, motivo in regras:
        try:
            if re.search(padrao, cmd):
                registrar_recusa(raiz, "comando", motivo, cmd[:200], modo)
                return bloquear(
                    f"comando bloqueado — {motivo}",
                    f"Comando: {cmd[:300]}",
                    "Se for realmente necessário, peça ao usuário para executar. "
                    "Ação irreversível não roda em fluxo autônomo (ADR-0024).",
                    modo,
                )
        except re.error:
            continue
    return 0


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

    # Sagrados NUNCA degradam para aviso: são o medidor e a regra. Guardrail que só
    # avisa sobre escrita no próprio medidor não é guardrail (ADR-0022).
    for padrao, motivo in SAGRADOS:
        if casa(rel, padrao):
            registrar_recusa(raiz, "sagrado", motivo, rel, "bloqueio")
            return bloquear(
                f"escrita bloqueada em `{rel}` — {motivo}",
                "Este caminho é inegociável: o agente não escreve o próprio medidor "
                "nem a própria regra. Corroboração que o agente reescreve não corrobora, "
                "e guardrail que o agente afrouxa não guarda.",
                "Quem edita este arquivo é o humano. Explique o que precisa mudar e por quê.",
            )

    # Fiação dos hooks do Claude Code (ADR-0042): só quando a escrita mexe em `hooks`.
    if rel in FIACAO_CLAUDE and mexe_na_fiacao(entrada, raiz / rel):
        registrar_recusa(raiz, "sagrado", "fiação dos hooks", rel, "bloqueio")
        return bloquear(
            f"escrita bloqueada em `{rel}` — mexe no bloco `hooks`",
            "É o arquivo em que o editor registra os hooks: alterar aqui silencia o "
            "guardrail e a telemetria de uma vez, sem que ninguém veja.",
            "Permissões e variáveis nesse arquivo continuam livres; o bloco `hooks` é do "
            "humano. Explique o que precisa mudar e por quê.",
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

    # Teste existente (ADR-0039). Só o que JÁ ESTAVA no HEAD: teste novo é o trabalho
    # esperado; teste antigo que muda no mesmo diff da feature é o medidor sendo
    # tocado. O rastro fica na trajetória sempre; o aviso, uma vez por arquivo na
    # sessão, para não virar ruído que o usuário aprende a ignorar.
    if not any(casa(rel, lib) for lib in liberados) and teste_existente(raiz, rel):
        modo_t = modo_de(cfg, "teste")
        registrar_recusa(raiz, "teste", "edição em teste existente", rel, modo_t)
        if modo_t == "bloqueio" or primeira_vez_na_sessao(payload, rel):
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
        return 0

    if any(casa(rel, exc) or casa(Path(rel).name, exc) for exc in EXCECOES):
        return 0

    protegidos = list(PROTEGIDOS_PADRAO) + [
        (p, "protegido pelo projeto") for p in cfg.get("protegidos", [])
    ]
    modo = modo_de(cfg, "protegido")
    for padrao, motivo in protegidos:
        if casa(rel, padrao) and not any(casa(rel, lib) for lib in liberados):
            registrar_recusa(raiz, "protegido", motivo, rel, modo)
            return bloquear(
                f"escrita bloqueada em `{rel}` — {motivo}",
                "Caminho protegido por guardrail determinístico.",
                "Peça a mudança ao usuário, ou libere o caminho em "
                "`.agents/guardrails.json` (campo `liberados`) — o que o usuário edita, "
                "não você.",
                modo,
            )
    return 0


def teste_existente(raiz: Path, rel: str) -> bool:
    """Arquivo de teste que existia ANTES do diff atual — não o que o diff está criando.

    "Antes" é o merge-base com a branch base (o teste novo da feature, já commitado,
    continua sendo novo); sem base conhecida, cai para o HEAD.
    """
    try:
        from prova import eh_teste, base_padrao, ponto_de_partida
    except Exception:
        return False
    if not eh_teste(rel):
        return False
    try:
        base = base_padrao(raiz)
        ponto = (ponto_de_partida(raiz, base) if base else None) or "HEAD"
        r = subprocess.run(["git", "-C", str(raiz), "cat-file", "-e", f"{ponto}:{rel}"],
                           capture_output=True, timeout=10)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


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
        return 0
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
    pasta = raiz / ".agents" / "execucoes"
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


def normalizar_payload(payload: dict) -> dict:
    if "tool_input" in payload or "conversation_id" not in payload:
        return payload
    p = dict(payload)
    p["_cursor"] = True
    p["session_id"] = p.get("session_id") or p.get("conversation_id")
    raizes = p.get("workspace_roots") or []
    p["cwd"] = p.get("cwd") or (raizes[0] if raizes else ".")
    p["tool_input"] = {k: p[k] for k in ("command", "file_path", "content", "edits") if k in p}
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

    for padrao, motivo in PROTEGIDOS_PADRAO[:5]:  # só os de segredo, não o de CI
        for achado in raiz.rglob(padrao.replace("**/", "")):
            if achado.is_file() and ".git/" not in str(achado):
                problemas.append(f"{achado}: {motivo} versionado no projeto?")

    if problemas:
        print(f"🛑 guardrail: {len(problemas)} achado(s)")
        for p in problemas:
            print(f"  ✗ {p}")
        return 1
    print("✅ guardrail: sem achados")
    return 0


MODOS = {"comando": checar_comando, "escrita": checar_escrita, "spec": checar_spec,
         "contrato": checar_contrato, "leitura": checar_leitura, "parada": checar_parada}


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__.strip())
        return 1

    if args[0] == "verificar":
        alvo = Path(args[1]) if len(args) > 1 else Path.cwd()
        return verificar(alvo)

    modo = MODOS.get(args[0])
    if modo is None:
        print(__doc__.strip())
        return 1
    try:
        bruto = sys.stdin.read()
        payload = normalizar_payload(json.loads(bruto) if bruto.strip() else {})
        return modo(payload)
    except Exception:
        # Guardrail quebrado nunca trava a sessão — falha aberta, mas silenciosa.
        # (Bloquear por bug próprio seria pior que a ausência do check.)
        return 0


if __name__ == "__main__":
    sys.exit(main())
