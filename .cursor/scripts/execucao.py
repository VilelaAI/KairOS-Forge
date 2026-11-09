#!/usr/bin/env python3
"""execucao.py — registro determinístico de execução da fábrica (ADR-0021).

Chamado pelos hooks do Claude Code em pontos do ciclo de vida. Lê o payload do
hook em stdin (JSON) e anexa UM evento a `.agents/execucoes/YYYY-MM.jsonl` no
projeto. O registro é escrito por código, não pelo modelo — é essa a diferença
entre trajetória e auto-relato (whitepaper Day-1, "trajectory evaluation").

Três invariantes, nesta ordem de prioridade:

  1. NUNCA bloqueia e NUNCA falha a sessão. Qualquer erro sai silencioso com
     código 0. Observabilidade que derruba a sessão é pior que sem observabilidade.
     Quem bloqueia é o guardrail.py.
  2. NUNCA escreve em stdout. Em `SessionStart` e `UserPromptSubmit` o stdout do
     hook entra no contexto do modelo — poluir ali custa tokens em toda interação.
  3. NUNCA registra segredo. Comandos passam pela regra do `segredos.py` (a mesma da
     saída de ferramenta, ADR-0056) antes de gravar; sem ela, o comando não é gravado.
     Prompts entram como contagem e skill detectada, jamais como texto.

Uso (nos hooks):
    execucao.py inicio      # SessionStart
    execucao.py prompt      # UserPromptSubmit   → o contador de autonomia
    execucao.py ferramenta  # PostToolUse (Write|Edit|Bash)
    execucao.py fim         # Stop

Camada episódica da memória (ADR-0009/0010): o bruto é local e descartável, o
durável sobe de camada — o agregado vira número no `/kairos-forge:auditar` e
fica em `decisoes/auditorias/`. Por isso o default é `.agents/execucoes/` no
`.gitignore`; o que se commita é a conclusão, não o log.

Só stdlib — sem dependências, igual ao grafo.py.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True   # não escrever __pycache__ no diretório do plugin
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from segredos import ocultar
except ImportError:              # cópia antiga sem o módulo: não grava o que não sabe ocultar
    ocultar = None

LIMITE_CMD = 300
LIMITE_ARQ = 200

# --- classificação de comando como gate -------------------------------------------
# É o que o /kairos-forge:validar corrobora contra a célula `verificado:` da SPEC.
GATES: list[tuple[str, str]] = [
    ("teste", r"(pytest|jest|vitest|mocha|go test|cargo test|mix test|rspec|phpunit"
              r"|dotnet test|(npm|pnpm|yarn|bun)( run)? test)"),
    ("lint", r"(eslint|ruff|flake8|pylint|golangci-lint|clippy|rubocop|biome"
             r"|(npm|pnpm|yarn|bun)( run)? lint)"),
    ("tipos", r"(tsc\b|mypy|pyright|(npm|pnpm|yarn|bun)( run)? typecheck)"),
    ("build", r"(go build|cargo build|docker build|\bmake\b"
              r"|(npm|pnpm|yarn|bun)( run)? build)"),
    ("migracao", r"(alembic|prisma migrate|knex migrate|rails db:migrate|supabase db)"),
]

# Marcadores de falha na saída — heurística honesta, não parsing de exit code.
FALHA = re.compile(
    r"(?i)(\b\d+ fail(ed|ing)?\b|\bFAIL\b|✗|✘|error TS\d+|Traceback \(most recent"
    r"|\bERROR\b|exit code [1-9]|command not found|AssertionError|panic:)"
)
SUCESSO = re.compile(
    r"(?i)(\b\d+ pass(ed|ing)\b|\ball tests? passed\b|✓|✔|\bOK\b|0 problems"
    r"|build succeeded|compiled successfully)"
)

# --- redação de segredo ------------------------------------------------------------
# A regra é a do `segredos.py`: só formatos de alta precisão. A regra antiga, daqui, deixava
# passar `DB_PASSWORD=…`, a senha na URL de conexão e as chaves com prefixo, e ao mesmo tempo
# apagava o hash de commit e o nome longo de teste, o que fazia o `corroborar` não achar o
# gate que rodou.
NAO_GRAVADO = "«comando não gravado: falta o segredos.py»"

EXT_PRODUCAO = re.compile(
    r"\.(py|ts|tsx|js|jsx|mjs|cjs|go|rs|java|rb|php|kt|kts|swift|cs|scala|ex|exs|vue|svelte)$"
)
EH_TESTE = re.compile(r"(^|/)(tests?|specs?|__tests__|e2e|playwright)/|\.(test|spec)\.")


def eh_producao(arquivo: str) -> bool:
    return bool(EXT_PRODUCAO.search(arquivo)) and not EH_TESTE.search(arquivo)

SKILLS = re.compile(
    r"/(?:kairos-forge:)?(onboardar|mapear-arquitetura|especificar|analisar-ameacas"
    r"|desenhar|mobilizar|rodar|validar|revisar|lancar|entregar|avaliar"
    r"|mapear-conhecimento|otimizar|migrar|auditar|evoluir)\b"
)


def redigir(texto: str) -> str:
    """O texto com cada segredo trocado pela marca, antes de qualquer gravação."""
    return ocultar(texto) if ocultar else NAO_GRAVADO


def _relativo(caminho: str, base) -> str | None:
    """`caminho` relativo a `base`; None quando fica fora dela (ou não dá para resolver)."""
    try:
        return str(Path(caminho).resolve().relative_to(Path(base or ".").resolve()))
    except Exception:
        return None


def relativizar(caminho: str, cwd: str | None) -> str:
    """Caminho relativo à raiz do projeto — mais legível e sem expor a árvore da máquina."""
    if not caminho:
        return ""
    rel = _relativo(caminho, cwd)
    return caminho[-LIMITE_ARQ:] if rel is None else rel


def raiz_do_checkout(cwd: str | None) -> Path:
    """A pasta mais próxima com `.git`, de `cwd` para cima; sem nenhuma, o próprio `cwd`."""
    try:
        inicio = Path(cwd or ".").resolve()
        return next((p for p in (inicio, *inicio.parents) if (p / ".git").exists()), inicio)
    except (OSError, RuntimeError):
        return Path(cwd or ".")


def no_projeto(caminho: str, cwd: str | None) -> bool:
    """Escrita fora do checkout (o scratchpad do Claude Code, `/tmp`) não é do projeto.

    O gate de parada contava o script de medição do scratchpad como produção sem gate
    verde depois — falso positivo numa sessão que não tinha tocado o código do projeto.
    """
    return bool(caminho) and _relativo(caminho, raiz_do_checkout(cwd)) is not None


def classificar_gate(cmd: str) -> str | None:
    alvo = cmd.lower()
    for nome, padrao in GATES:
        if re.search(padrao, alvo):
            return nome
    return None


def avaliar_saida(resposta) -> bool | None:
    """True/False quando dá para afirmar; None quando não dá. Nunca chuta."""
    if isinstance(resposta, dict):
        if resposta.get("interrupted"):
            return False
        for chave in ("exit_code", "exitCode", "returncode"):
            if isinstance(resposta.get(chave), int):
                return resposta[chave] == 0
        texto = " ".join(
            str(resposta.get(k, "")) for k in ("stdout", "stderr", "output", "content")
        )
    else:
        texto = str(resposta or "")
    if not texto.strip():
        return None
    tem_falha, tem_sucesso = bool(FALHA.search(texto)), bool(SUCESSO.search(texto))
    if tem_falha and not tem_sucesso:
        return False
    if tem_sucesso and not tem_falha:
        return True
    return None


def raiz_do_projeto(cwd: Path) -> Path:
    """O checkout principal quando `cwd` é um worktree ligado; senão, o próprio `cwd`.

    Teammate em worktree (ADR-0024) gravava a trajetória dentro do worktree, que é
    descartável: os eventos dele sumiam junto, e o quadro e o /auditar nunca os viam.
    Lido do arquivo `.git` (o `gitdir:` e o `commondir`), sem rodar git: hook roda em
    toda ferramenta e não pode pagar um processo a cada vez.
    """
    try:
        marca = cwd / ".git"
        if not marca.is_file():
            return cwd
        m = re.match(r"gitdir:\s*(.+)", marca.read_text(encoding="utf-8").strip())
        if not m:
            return cwd
        gitdir = (cwd / m.group(1).strip()).resolve()
        comum = gitdir / "commondir"
        if not comum.is_file():          # submódulo: não é worktree, fica onde está
            return cwd
        principal = (gitdir / comum.read_text(encoding="utf-8").strip()).resolve()
        return principal.parent if principal.name == ".git" else cwd
    except (OSError, ValueError):     # ValueError: `.git` com bytes que não são UTF-8
        return cwd


def estado_no_principal(relativa: Path) -> Path:
    """`relativa` no checkout principal quando o diretório atual é um worktree ligado; fora
    de worktree, ela mesma, relativa como sempre (emenda ao ADR-0024)."""
    aqui = Path.cwd()
    principal = raiz_do_projeto(aqui)
    return relativa if principal == aqui else principal / relativa


def pasta_do_projeto(raiz, nome: str) -> Path:
    """`.agents/<nome>` do checkout principal: a trajetória, o ciclo e o quadro moram lá
    mesmo quando a sessão roda num worktree ligado (ADR-0048; emenda ao ADR-0024)."""
    return raiz_do_projeto(Path(raiz).resolve()) / ".agents" / nome


def destino(payload: dict) -> Path:
    raiz = raiz_do_projeto(Path(payload.get("cwd") or ".").resolve())
    pasta = raiz / ".agents" / "execucoes"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / f"{datetime.now(timezone.utc):%Y-%m}.jsonl"


def anexar(payload: dict, evento: dict) -> None:
    evento = {
        "t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sessao": (payload.get("session_id") or "?")[:16],
        **evento,
    }
    with destino(payload).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(evento, ensure_ascii=False) + "\n")


# --- um construtor de evento por ponto do ciclo de vida ----------------------------

def ev_inicio(p: dict) -> dict:
    return {"tipo": "sessao_inicio", "origem": p.get("source") or "?", **_com_branch(p)}


# --- a chave entre sessão e SPEC (aula 5 do Tech Leads Club) -------------------------
# Cada CLI agrupa o trabalho pela própria sessão e nenhuma sabe a qual SPEC ele pertence.
# O branch é a chave comum: o `ciclo.py` grava o branch de cada ciclo, e o `telemetria.py
# por-spec` cruza os dois. Lido do `.git` sem rodar git (hook roda em toda ferramenta), e
# gravado no início e em cada `Stop`, porque o `/entregar` troca de branch no meio da sessão.
SPEC_CITADA = re.compile(r"\bSPEC-\d+\b", re.I)


def branch_atual(cwd: str | None) -> str | None:
    """O branch do checkout de `cwd`, lendo `HEAD`; None em HEAD destacado ou sem git."""
    try:
        marca = raiz_do_checkout(cwd) / ".git"
        if marca.is_file():
            m = re.match(r"gitdir:\s*(.+)", marca.read_text(encoding="utf-8").strip())
            marca = (marca.parent / m.group(1).strip()) if m else marca
        head = (marca / "HEAD").read_text(encoding="utf-8").strip()
    except (OSError, ValueError, AttributeError):
        return None
    return head[len("ref: refs/heads/"):] if head.startswith("ref: refs/heads/") else None


def _com_branch(p: dict) -> dict:
    """Sem `cwd` no payload, não adivinha: o diretório do processo pode ser outro repositório."""
    b = branch_atual(p["cwd"]) if p.get("cwd") else None
    return {"branch": b[:LIMITE_ARQ]} if b else {}


def ev_prompt(p: dict) -> dict:
    """O contador de autonomia: quantas vezes o humano precisou digitar."""
    texto = p.get("prompt") or ""
    achadas = SKILLS.findall(texto)
    specs = sorted({s.upper() for s in SPEC_CITADA.findall(texto)})
    return {
        "tipo": "prompt",
        "skill": achadas[0] if achadas else None,
        "chars": len(texto),
        **({"specs": specs[:5]} if specs else {}),   # só o id sai do prompt, nunca o texto
    }


def ev_comando(bruto: str, resposta) -> dict:
    """O comando sem o segredo, o gate pelo comando cru e o resultado quando dá para afirmar.

    O comando que vai para background volta sem saída e sem código: o `ok` fica `None`, e
    o id da tarefa (`backgroundTaskId`) vai junto, para o término lido do transcript lhe
    dar o resultado (`conclusoes_em_background`, emenda ao ADR-0042).
    """
    ev = {
        "tipo": "comando",
        "cmd": redigir(bruto)[:LIMITE_CMD],
        "gate": classificar_gate(bruto),             # o gate sai do comando, não da gravação
        "ok": avaliar_saida(resposta),
    }
    tarefa = resposta.get("backgroundTaskId") if isinstance(resposta, dict) else None
    if tarefa:
        ev["tarefa"] = str(tarefa)[:40]
    return ev


def ev_ferramenta(p: dict) -> dict | None:
    nome = p.get("tool_name") or "?"
    entrada = p.get("tool_input") or {}
    resposta = p.get("tool_response")

    if nome == "Bash":
        return ev_comando(str(entrada.get("command") or ""), resposta)

    if nome in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
        bruto = str(entrada.get("file_path") or entrada.get("notebook_path") or "")
        arquivo = relativizar(bruto, p.get("cwd"))
        return {
            "tipo": "escrita",
            "arquivo": arquivo,
            "producao": eh_producao(arquivo) and no_projeto(bruto, p.get("cwd")),
            "ferramenta": nome,
        }

    if nome in ("Skill", "Task", "Agent"):
        alvo = str(entrada.get("skill") or entrada.get("subagent_type") or "")[:80]
        return {"tipo": "delegacao", "ferramenta": nome, "alvo": alvo}

    return None


# --- tokens da sessão, como a CLI registrou (ADR-0048) -------------------------------
# Da Alethe: gasto relatado, nunca estimado. O transcript do Claude Code guarda o uso
# de cada resposta do modelo; o hook recebe o caminho dele em `transcript_path`.
CAMPOS_USO = (("entrada", "input_tokens"), ("cache_escrita", "cache_creation_input_tokens"),
              ("cache_leitura", "cache_read_input_tokens"), ("saida", "output_tokens"))


def _resposta(linha: str) -> tuple[dict, dict] | None:
    """(evento, mensagem) de uma linha de resposta do modelo; None nas demais."""
    if '"usage"' not in linha:
        return None
    try:
        ev = json.loads(linha)
    except Exception:
        return None
    msg = ev.get("message") if isinstance(ev, dict) and ev.get("type") == "assistant" else None
    return (ev, msg) if isinstance(msg, dict) and isinstance(msg.get("usage"), dict) else None


def _uso_da_linha(linha: str) -> tuple[str, dict, str] | None:
    """(id da resposta, uso, modelo) de uma linha de resposta do modelo; None nas demais."""
    lida = _resposta(linha)
    if lida is None:
        return None
    ev, msg = lida
    modelo = str(msg.get("model") or "")
    return (str(msg.get("id") or ev.get("uuid") or linha), msg["usage"],
            "" if modelo.startswith("<") else modelo)   # "<synthetic>" não é modelo


def _acumular(atual: dict[str, int], uso: dict) -> None:
    """Guarda o maior valor visto de cada campo: a última linha da resposta é a completa."""
    for nosso, deles in CAMPOS_USO:
        valor = uso.get(deles)
        if isinstance(valor, int) and not isinstance(valor, bool):
            atual[nosso] = max(atual[nosso], valor)


def _anotar_uso(linha: str, por_resposta: dict, modelos: set) -> None:
    lida = _uso_da_linha(linha)
    if lida is not None:
        chave, uso, modelo = lida
        _acumular(por_resposta.setdefault(chave, {n: 0 for n, _ in CAMPOS_USO}), uso)
        modelos.add(modelo)


def _total(por_resposta: dict, modelos: set) -> dict | None:
    if not por_resposta:
        return None
    total: dict = {n: sum(r[n] for r in por_resposta.values()) for n, _ in CAMPOS_USO}
    total["respostas"] = len(por_resposta)
    total["modelos"] = sorted(modelos - {""})
    return total


# --- perguntas por falta de fonte (aula 5 do Tech Leads Club) -----------------------
# "Antes de apagar vale olhar no PostHog, só que ele não está conectado." Quando o agente
# pergunta à pessoa o que uma ferramenta responderia, a pergunta traz uma linha
# `falta-fonte: <fonte>`. O Stop conta, na mesma leitura do transcript, as respostas do
# modelo que declaram cada fonte, e grava só o nome dela, nunca o texto. É a matéria do
# `/evoluir`: a fonte que mais faltou é a próxima a ligar.
MARCAS_FALTA = ("alta-fonte", "ALTA-FONTE")   # filtro barato: o Stop lê o transcript inteiro
FALTA_FONTE = re.compile(r"(?im)^[\s>*_`-]*falta-fonte:\s*`?([a-z0-9][\w.\-/]{1,39})")


def _textos(msg: dict) -> list[str]:
    conteudo = msg.get("content")
    blocos = conteudo if isinstance(conteudo, list) else [{"type": "text", "text": conteudo}]
    return [str(b.get("text") or "") for b in blocos
            if isinstance(b, dict) and b.get("type") == "text"]


def _anotar_falta(linha: str, por_resposta: dict) -> None:
    """Fontes que uma resposta do modelo declarou faltar; texto de usuário e de ferramenta
    não conta, e a mesma resposta em várias linhas conta uma vez."""
    lida = _resposta(linha) if any(m in linha for m in MARCAS_FALTA) else None
    if lida is None:
        return
    msg = lida[1]
    fontes = {f.lower().rstrip(".") for t in _textos(msg) for f in FALTA_FONTE.findall(t)}
    if fontes:   # sem `message.id`, cada linha é uma resposta
        por_resposta.setdefault(str(msg.get("id") or linha), set()).update(fontes)


def ler_transcript(caminho: str) -> tuple[dict | None, dict[str, int]]:
    """Uma passada só: o uso de cada resposta e as fontes que ela declarou faltar.

    Uma resposta vira várias linhas no transcript (uma por bloco de conteúdo), todas com
    o mesmo `message.id` e o mesmo uso. Somar linha a linha conta a mesma resposta duas,
    três vezes — num transcript real, 955 linhas eram 387 respostas. Conta-se cada id
    uma vez, com o maior valor visto em cada campo.
    """
    if not caminho or not Path(caminho).is_file():
        return None, {}
    por_resposta: dict[str, dict[str, int]] = {}
    modelos: set[str] = set()
    faltas: dict[str, set[str]] = {}
    with Path(caminho).open(encoding="utf-8", errors="replace") as fh:
        for linha in fh:
            _anotar_uso(linha, por_resposta, modelos)
            _anotar_falta(linha, faltas)
    contagem: dict[str, int] = {}
    for fontes in faltas.values():
        for fonte in fontes:
            contagem[fonte] = contagem.get(fonte, 0) + 1
    return _total(por_resposta, modelos), dict(sorted(contagem.items()))


def tokens_do_transcript(caminho: str) -> dict | None:
    """O uso acumulado da sessão: a soma de cada resposta do modelo, contada uma vez."""
    return ler_transcript(caminho)[0]


# --- o término do que rodou em background (emenda ao ADR-0042) ----------------------
# O `PostToolUse` de um comando em background chega quando ele começa, sem saída nem
# código. O término chega depois, como notificação que o próprio Claude Code põe no
# transcript: `<task-notification>` com o id da tarefa, o status e "exit code N" no
# resumo. Vale só a que traz `origin.kind == "task-notification"` — numa entrada `user`
# quando a sessão estava parada, num anexo `queued_command` quando chegou no meio de um
# turno (conferido no 2.1.319). O mesmo texto impresso por um comando volta como
# `tool_result`, sem essa origem: o agente não forja o próprio gate verde.

NOTIFICACAO = re.compile(r"<task-notification>(.*?)</task-notification>", re.S)


def _campo(bloco: str, nome: str) -> str:
    m = re.search(rf"<{nome}>([^<]*)</{nome}>", bloco)
    return m.group(1).strip() if m else ""


def _resultado(bloco: str) -> bool | None:
    """Verde só com "exit code 0"; `failed` sem código é vermelho; o resto não se afirma."""
    m = re.search(r"exit code (\d+)", _campo(bloco, "summary"))
    if m:
        return m.group(1) == "0"
    return False if _campo(bloco, "status") == "failed" else None


def _do_harness(origem) -> bool:
    return isinstance(origem, dict) and origem.get("kind") == "task-notification"


def _texto_da_mensagem(conteudo) -> str:
    if isinstance(conteudo, str):
        return conteudo
    return " ".join(str(b.get("text") or "") for b in conteudo or [] if isinstance(b, dict))


def _texto_do_harness(d: dict) -> str:
    """O texto da notificação, se foi o Claude Code que a pôs no transcript; senão, nada."""
    if d.get("type") == "user" and _do_harness(d.get("origin")):
        return _texto_da_mensagem((d.get("message") or {}).get("content"))
    anexo = d.get("attachment") or {}
    if d.get("type") == "attachment" and _do_harness(anexo.get("origin")):
        return str(anexo.get("prompt") or "")
    return ""


def _conclusoes_da_linha(linha: str) -> dict[str, bool | None]:
    if "task-notification" not in linha:              # filtro barato: o transcript é grande
        return {}
    try:
        d = json.loads(linha)
    except ValueError:
        return {}
    blocos = NOTIFICACAO.findall(_texto_do_harness(d)) if isinstance(d, dict) else []
    return {_campo(b, "task-id"): _resultado(b) for b in blocos if _campo(b, "task-id")}


def conclusoes_em_background(caminho: str) -> dict[str, bool | None]:
    """Id da tarefa → resultado, para cada comando em background que terminou na sessão.
    Sem transcript (arquivo que falta, pasta, ilegível), nada: o `OSError` cobre os três."""
    if not caminho:
        return {}
    conclusoes: dict[str, bool | None] = {}
    try:
        with Path(caminho).open(encoding="utf-8", errors="replace") as fh:
            for linha in fh:
                conclusoes.update(_conclusoes_da_linha(linha))
    except OSError:
        return {}
    return conclusoes


def ev_fim(p: dict) -> dict:
    """O `Stop` roda a cada turno: grava o acumulado da sessão até ali, não o do turno."""
    tokens, faltas = ler_transcript(str(p.get("transcript_path") or ""))
    return {"tipo": "sessao_fim", **({"tokens": tokens} if tokens else {}),
            **({"faltas_de_fonte": faltas} if faltas else {}), **_com_branch(p)}


CONSTRUTORES = {
    "inicio": ev_inicio,
    "prompt": ev_prompt,
    "ferramenta": ev_ferramenta,
    "fim": ev_fim,
}


# --- detecção de patinação em voo (ADR-0030) ---------------------------------------
# Medir depois não impede queimar orçamento agora. Estes três padrões são os que
# aparecem quando o agente está preso — e a regra é a mesma do guardrail: alarme que
# dispara errado é alarme que o usuário aprende a ignorar. Por isso todos exigem
# FALHA, não só repetição: rodar o mesmo teste 3× enquanto conserta é trabalho normal.
REPETICAO = 3      # mesmo comando, 3 falhas seguidas
ALTERNANCIA = 4    # dois comandos revezando, 4 falhas na janela
SEM_PROGRESSO = 8  # escritas em produção sem nenhum gate no meio
JANELA = 12


def _eventos_da_sessao(payload: dict, limite: int = JANELA) -> list[dict]:
    try:
        arq = destino(payload)
        if not arq.is_file():
            return []
        sessao = (payload.get("session_id") or "?")[:16]
        linhas = arq.read_text(encoding="utf-8").splitlines()[-400:]
        eventos = []
        for linha in linhas:
            try:
                ev = json.loads(linha)
            except Exception:
                continue
            if ev.get("sessao") == sessao:
                eventos.append(ev)
        return eventos[-limite:]
    except Exception:
        return []


def _norm(cmd: str) -> str:
    return " ".join((cmd or "").lower().split())


def detectar(eventos: list[dict]) -> str | None:
    """Devolve o alerta quando o padrão FECHA exatamente agora — nunca a cada turno."""
    comandos = [e for e in eventos if e.get("tipo") == "comando"]

    # 1. Mesmo comando falhando seguidamente.
    if len(comandos) >= REPETICAO:
        ultimo = _norm(comandos[-1].get("cmd", ""))
        corrida = 0
        for e in reversed(comandos):
            if _norm(e.get("cmd", "")) == ultimo and e.get("ok") is False:
                corrida += 1
            else:
                break
        if corrida == REPETICAO:  # exatamente agora, não a cada nova repetição
            return (f"o mesmo comando falhou {REPETICAO} vezes seguidas: "
                    f"`{comandos[-1].get('cmd', '')[:80]}`")

    # 2. Dois comandos revezando sem nenhum passar.
    recentes = comandos[-8:]
    if len(recentes) >= ALTERNANCIA:
        nomes = [_norm(e.get("cmd", "")) for e in recentes]
        distintos = set(nomes)
        alternando = len(distintos) == 2 and all(
            nomes[i] != nomes[i + 1] for i in range(len(nomes) - 1)
        )
        if alternando and len(recentes) == ALTERNANCIA and not any(
            e.get("ok") is True for e in recentes
        ):
            return (f"dois comandos estão se revezando há {ALTERNANCIA} rodadas sem "
                    f"nenhum passar: {' ⇄ '.join(sorted(distintos))[:120]}")

    # 3. Escrita em produção sem nenhum gate rodado no meio.
    # Progresso é comando que rodou, não arquivo que mudou — contador que zera a cada
    # escrita deixa o agente editar-falhar-editar parecendo saudável.
    desde_gate = 0
    for e in reversed(eventos):
        if e.get("tipo") == "comando" and e.get("gate"):
            break
        if e.get("tipo") == "escrita" and e.get("producao"):
            desde_gate += 1
    if desde_gate == SEM_PROGRESSO:
        return (f"{SEM_PROGRESSO} escritas em código de produção sem nenhum gate rodado "
                "no meio — nada foi verificado desde então")
    return None


def alertar(payload: dict) -> None:
    """PostToolUse: avisa o modelo quando ele está patinando. Nunca bloqueia."""
    achado = detectar(_eventos_da_sessao(payload))
    if achado:
        print(f"🔁 kairos-forge (trajetória): {achado}.\n"
              "   Duas falhas materialmente iguais nunca viram terceira tentativa — "
              "mude de abordagem ou escale (ADR-0030).")


# --- adaptador do Cursor (ADR-0042) -------------------------------------------------
# O `.cursor/hooks.json` gerado pelo sync chama `execucao.py cursor` em todo evento; a
# ação e a forma Claude Code do payload são derivadas do `hook_event_name`. Reconhecido
# pela FORMA (conversation_id sem tool_name), nunca por configuração.
EVENTOS_CURSOR = {
    "sessionStart": "inicio", "beforeSubmitPrompt": "prompt",
    "afterShellExecution": "ferramenta", "afterFileEdit": "ferramenta",
    "subagentStart": "ferramenta", "stop": "fim",
}


def adaptar_cursor(payload: dict) -> tuple[str | None, dict]:
    if "tool_name" in payload or "conversation_id" not in payload:
        return None, payload
    ev = str(payload.get("hook_event_name") or "")
    p = dict(payload)
    p["session_id"] = p.get("session_id") or p.get("conversation_id")
    raizes = p.get("workspace_roots") or []
    p["cwd"] = p.get("cwd") or (raizes[0] if raizes else ".")
    if ev == "afterShellExecution":
        p["tool_name"] = "Bash"
        p["tool_input"] = {"command": p.get("command", "")}
        p["tool_response"] = {k: p[k] for k in ("stdout", "stderr", "output", "exit_code") if k in p}
    elif ev == "afterFileEdit":
        p["tool_name"] = "Write"
        p["tool_input"] = {"file_path": p.get("file_path", "")}
    elif ev == "subagentStart":
        p["tool_name"] = "Task"
        p["tool_input"] = {"subagent_type": str(p.get("agent") or p.get("subagent_type") or "")}
    elif ev == "sessionStart":
        p["source"] = "cursor"
    return EVENTOS_CURSOR.get(ev), p


def main() -> int:
    try:
        acao = sys.argv[1] if len(sys.argv) > 1 else ""
        bruto = sys.stdin.read()
        payload = json.loads(bruto) if bruto.strip() else {}
        if acao == "cursor":
            acao, payload = adaptar_cursor(payload)
            if acao is None:
                return 0

        # `alerta` é o único modo que fala — e só em PostToolUse, onde stdout não
        # entra no contexto de toda interação (invariante 2 preservada nos demais).
        if acao == "alerta":
            alertar(payload)
            return 0

        construtor = CONSTRUTORES.get(acao)
        if construtor is None:
            return 0
        evento = construtor(payload)
        if evento is not None:
            anexar(payload, evento)
    except Exception:
        # Invariante 1: observabilidade jamais derruba a sessão.
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
