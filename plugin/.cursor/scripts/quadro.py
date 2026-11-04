#!/usr/bin/env python3
"""quadro.py — quadro de tarefas determinístico do `/kairos-forge:mobilizar` (ADR-0035).

Até a v0.27 o `/mobilizar` era "exclusivo do Claude Code". O motivo declarado eram
quatro ferramentas nativas — `TeamCreate`, `TaskCreate`, `TaskUpdate`, `SendMessage`.
Três delas têm equivalente direto no Codex (`spawn_agent`, `send_message`/
`followup_task`, `list_agents`). A quarta não tem: **o quadro compartilhado de
tarefas com dependências.** Era essa, sozinha, que prendia a skill a um CLI.

A saída não é reimplementar Agent Teams em cada CLI. É tirar o quadro do CLI.

    O quadro é um arquivo do repositório, não um objeto da sessão.

O mesmo movimento que o `ciclo.py` fez com a máquina de estados do `/entregar`, pelo
mesmo motivo e com os mesmos ganhos:

  1. **Roda em qualquer CLI.** Claude Code, Codex, Cursor, OpenCode e CI leem o
     mesmo quadro. Cada CLI só precisa saber lançar worker em paralelo e esperar.
  2. **Sobrevive.** A reset de contexto, a troca de sessão e a troca de CLI. O
     quadro nativo do Claude Code morre com a sessão; este está no disco.
  3. **A decisão é de código, não de julgamento.** Quais tarefas podem entrar
     agora, quantas cabem na onda, quais colidem em posse de arquivo e se o
     encerramento pode se dizer completo — nada disso é opinião do modelo.

O ponto (3) é o que importa de verdade. As três regras abaixo existiam em prosa na
skill e valiam enquanto havia um humano lendo. Sem ninguém lendo, prosa não impõe:

  - **Teto de onda (ADR-0033).** "No máximo 6 teammates simultâneos" era um número
    numa tabela. Agora `prontas` não devolve o sétimo.
  - **Posse de arquivo (ADR-0024).** "Nunca paralelize escrita no mesmo arquivo"
    dependia do teammate obedecer o prompt. Agora duas tarefas com posse
    sobreposta não saem juntas — o quadro serializa antes de alguém escrever.
  - **Contagem antes de declarar pronto.** "Nunca sintetize por cima de resultado
    parcial" era um pedido. Agora `encerrar` recusa quadro com tarefa aberta que
    não tenha lacuna declarada.

E o estado vive em `.agents/quadro/<slug>.json`, protegido por guardrail
(ADR-0022): o agente não escreve o próprio quadro pela mesma razão que não escreve
a própria telemetria nem o próprio ciclo.

Uso:
    quadro.py abrir <slug> [--spec SPEC-001] [--teto-onda 6] [--max-tasks 20]
                           [--rodadas 2] [--cli claude-code|codex|cursor|opencode]
    quadro.py adicionar <slug> --id T1 --titulo "..." [--requisito EXP-01]
                           --dono <agente> (--posse "migrations/**,db/seed*" | --leitura)
                           --pronto-quando "..." [--gate "npm test"] [--depende T0,T2]
                           [--tier rapido|padrao|preciso] [--reverter "git revert <sha>"]
    quadro.py prontas <slug> [--json]          # a próxima onda, decidida por código
    quadro.py iniciar <slug> T1 [--agente <id/task_name do worker>] [--checkout <worktree>]
    quadro.py vincular <slug> T1               # o teammate roda, da própria sessão: liga a
                                                # sessão à tarefa na trajetória (tokens)
    quadro.py concluir <slug> T1 --evidencia "..." [--gate-ok | --gate-pulado "motivo"]
                           [--fora-da-posse "motivo"]   # confere no git o que a tarefa mudou
    quadro.py varrer <slug> [--dry-run]         # bloqueia quem venceu o tempo limite
    quadro.py compensar <slug> T1 --motivo "..." [--aplicar]   # Saga: desfaz T1 e o que
                                                # foi construído sobre ela, ordem inversa
    quadro.py depender <slug> T4 --de T1        # serializa uma colisão de posse
    quadro.py bloquear <slug> T1 --motivo "..."
    quadro.py reabrir <slug> T1                # bloqueio resolvido volta pra fila
    quadro.py estado <slug> [--json]
    quadro.py ledger <slug>                    # tabela do relatório final (ADR-0013)
    quadro.py encerrar <slug> [--lacuna "T7: motivo"]...
    quadro.py listar
    quadro.py contrato [--json]

Só stdlib.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True   # não escrever __pycache__ no diretório do plugin

sys.path.insert(0, str(Path(__file__).resolve().parent))
PASTA_RELATIVA = Path(".agents/quadro")

try:
    from execucao import estado_no_principal
except Exception:                     # cópia avulsa do script, sem o execucao.py ao lado
    def estado_no_principal(relativa: Path) -> Path:
        return relativa


def pasta_do_estado() -> Path:
    """`.agents/quadro` do checkout principal, também num worktree ligado (emenda ao ADR-0024)."""
    return estado_no_principal(PASTA_RELATIVA)

# --- contrato de integração (ADR-0034/0035) -----------------------------------------
# `estado --json` e `prontas --json` são CONTRATO PÚBLICO: o kairos-symphony, os
# templates de CI e qualquer runner headless dependem deles para saber o que lançar
# agora. Mudança de forma sem bump aqui quebra consumidor em silêncio — e o
# `release.py check` recusa, comparando o digest da declaração.
#
# MENOR (1.x): campo novo, estado novo. Consumidor antigo continua válido.
# MAIOR (x.0): campo removido/renomeado, semântica alterada.
CONTRATO_VERSAO = "1.2"

ESTADOS_TASK = ("planejada", "em_progresso", "concluida", "bloqueada")

# Tempo limite padrão de uma tarefa em voo, em minutos (ADR-0036). Não é estimativa de
# esforço — é o ponto em que "ainda trabalhando" e "morreu sem avisar" deixam de ser
# distinguíveis. Sem isso, worker que não responde segura a vaga da onda para sempre e
# a mobilização trava sem nunca dar erro.
TEMPO_LIMITE_PADRAO = 60
TERMINAIS_TASK = ("concluida",)
TIERS = ("rapido", "padrao", "preciso")

# Teto de teammates simultâneos por onda (ADR-0033). Coincide com o default do
# Codex (`agents.max_concurrent_threads_per_session = 6`) — não por acaso: acima de
# ~6 a consolidação dos outputs estoura contexto antes da síntese começar.
TETO_ONDA_PADRAO = 6
RODADAS_PADRAO = 2

CAMPOS_ESTADO = {
    "slug": "string",
    "spec": "string?",
    "cli": "string?",
    "encerrado": "boolean",
    "onda": "integer",
    "teto_onda": "integer",
    "total": "integer",
    "por_estado": "object<string,integer>",
    "completo": "boolean",          # todas as tarefas concluídas
    "pode_encerrar": "boolean",     # completo OU toda pendência com lacuna declarada
    "em_voo": "string[]",           # ids em_progresso
    "prontas": "string[]",          # ids que a próxima onda pode lançar
    "bloqueadas": "string[]",
    "vencidas": "string[]",         # em_progresso além do tempo limite (ADR-0036)
    "lacunas": "string[]",
    "tasks": "object",
}


# --- posse de arquivo ----------------------------------------------------------------
# Duas tarefas não podem escrever no mesmo arquivo ao mesmo tempo. Decidir isso exige
# saber se dois globs se sobrepõem, o que no caso geral não tem resposta barata. A
# heurística abaixo é declarada de propósito, com o viés escolhido de propósito:
#
#   falso positivo  → serializa duas tarefas que poderiam ter rodado juntas (custa tempo)
#   falso negativo  → dois workers escrevem o mesmo arquivo (custa o arquivo)
#
# Então ela erra para o lado conservador, e desempata só nos dois casos em que a
# precedência é inequívoca e é a convenção que todo mundo já usa (CODEOWNERS, gitignore,
# tsconfig paths): o caminho mais fundo manda, e o nome mais específico manda.
CURINGAS = "*?["


def _segmentos(padrao: str) -> list[str]:
    return [s for s in padrao.strip().strip("/").split("/") if s]


def _prefixo_estatico(padrao: str) -> list[str]:
    """Segmentos literais antes do primeiro curinga. `src/lib/**` → ['src','lib']."""
    saida: list[str] = []
    for seg in _segmentos(padrao):
        if any(c in seg for c in CURINGAS):
            break
        saida.append(seg)
    return saida


def _discrimina_nome(padrao: str) -> bool:
    """O último segmento restringe o NOME do arquivo? `**/*.test.*` sim, `api/**` não."""
    segs = _segmentos(padrao)
    if not segs:
        return False
    ultimo = segs[-1]
    if ultimo in ("*", "**"):
        return False
    return any(c in ultimo for c in CURINGAS) and any(ch.isalnum() for ch in ultimo)


def _cauda(padrao: str) -> str:
    """Sufixo literal depois do último curinga. `*.test.ts` → '.test.ts'; `*.spec.*` → ''."""
    segs = _segmentos(padrao)
    ultimo = segs[-1] if segs else ""
    corte = max(ultimo.rfind(c) for c in CURINGAS)
    return ultimo[corte + 1:] if corte >= 0 else ultimo


def colidem(a: str, b: str) -> bool:
    """Duas tarefas com estes padrões de posse podem escrever o mesmo arquivo?"""
    pa, pb = _prefixo_estatico(a), _prefixo_estatico(b)
    # Subárvores disjuntas: `api/**` vs `src/**`. Resposta definitiva, sem heurística.
    for sa, sb in zip(pa, pb):
        if sa != sb:
            return False
    # Refinamento por caminho: o mais fundo manda na própria subárvore.
    # `src/components/**` (Marina) vs `src/components/ui/**` (Pablo) → Pablo manda em ui/.
    if len(pa) != len(pb):
        return False
    da, db = _discrimina_nome(a), _discrimina_nome(b)
    # Refinamento por nome: quem restringe o nome manda nos arquivos daquele nome.
    # `src/components/**` (Marina) vs `**/*.test.*` (Ricardo) → Ricardo manda nos testes.
    if da != db:
        return False
    if da and db:
        ca, cb = _cauda(a), _cauda(b)
        # Extensões literais distintas não se cruzam: `*.test.ts` vs `*.spec.tsx`.
        if ca and cb and not (ca.endswith(cb) or cb.endswith(ca)):
            return False
    return True


def posses_colidem(a: list[str], b: list[str]) -> list[tuple[str, str]]:
    return [(x, y) for x in a for y in b if colidem(x, y)]


# --- posse exercida (ADR-0048) -------------------------------------------------------
# A posse declarada impede duas tarefas de SAÍREM juntas sobre o mesmo arquivo. Ela não
# diz nada sobre o que a tarefa de fato mudou: o `concluir` exigia evidência e gate e
# nunca olhava o checkout. Nos CLIs em que a allow-list do agente é só instrução — o
# Codex (o `apply_patch` sobrevive, e o perfil de agente não aceita `sandbox_mode`,
# ADR-0035), o Cursor (`readonly`) e o Tucano (preâmbulo, ADR-0047) —, "o consultivo
# não edita código" era um pedido.
#
# A conferência vem da Alethe (github.com/Kc1t/alethe-orchestrate-skill, MIT), que pega
# o worker só leitura que escreveu: uma foto do checkout no `iniciar` (o `git status`
# com o sha256 de cada arquivo listado, mais o HEAD) e outra no `concluir`. O que mudou
# entre as duas e não cabe na posse da tarefa recusa a conclusão.
#
# Num checkout compartilhado, outras tarefas escrevem ao mesmo tempo. A atribuição é
# pela posse: o que cabe na posse de uma tarefa que esteve em voo junto com esta é dela,
# não desta. Com worktree por teammate (ADR-0024), cada foto é do próprio worktree e a
# atribuição é exata.
LIMITE_FOTO = 5000                  # arquivos sujos acima disso: a foto não é tirada
LIMITE_IMPRESSAO = 32 * 1024 * 1024 # acima disso, tamanho e mtime no lugar do sha256
# Escritos por script e hook, não por tarefa: o próprio quadro muda entre as duas fotos.
FORA_DA_FOTO = (".agents/quadro/", ".agents/execucoes/", ".agents/ciclo/")


def _git(raiz: Path, *args: str, timeout: int = 60) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", "-C", str(raiz), *args], capture_output=True,
                              timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return None


def impressao(arquivo: Path) -> str:
    """O conteúdo de um arquivo reduzido a uma marca: muda quando o conteúdo muda."""
    try:
        if arquivo.is_symlink():
            return "link:" + str(arquivo.readlink())
        if arquivo.is_dir():
            return "dir"
        info = arquivo.stat()
        if info.st_size > LIMITE_IMPRESSAO:
            return f"tamanho:{info.st_size}:{info.st_mtime_ns}"
        return hashlib.sha256(arquivo.read_bytes()).hexdigest()
    except OSError:
        return "ausente"


def _fora_da_foto(rel: str) -> bool:
    return any(rel.startswith(p) for p in FORA_DA_FOTO)


def arquivos_do_status(bruto: bytes, raiz: Path) -> dict[str, str] | None:
    """Os arquivos do `git status -z`, cada um com a impressão. None acima do limite."""
    pedacos = bruto.decode("utf-8", errors="surrogateescape").split("\0")
    arquivos: dict[str, str] = {}
    i = 0
    while i < len(pedacos):
        item = pedacos[i]
        i += 1
        if len(item) < 4:
            continue
        codigo, rel = item[:2], item[3:]
        i += "R" in codigo or "C" in codigo   # renomeação: a origem vem no pedaço seguinte
        if len(arquivos) >= LIMITE_FOTO:
            return None                       # sujo demais: não vale hashear o resto
        if not _fora_da_foto(rel):
            arquivos[rel] = f"{codigo}:{impressao(raiz / rel)}"
    return arquivos


def foto_do_checkout(checkout: Path) -> dict | None:
    """HEAD e arquivos sujos do checkout, cada um com a sua impressão. None fora do git."""
    topo = _git(checkout, "rev-parse", "--show-toplevel")
    if topo is None or topo.returncode != 0:
        return None
    raiz = Path(topo.stdout.decode().strip())
    head = _git(raiz, "rev-parse", "--verify", "-q", "HEAD")
    status = _git(raiz, "status", "--porcelain=v1", "-z", "--untracked-files=all", timeout=120)
    if status is None or status.returncode != 0:
        return None
    arquivos = arquivos_do_status(status.stdout, raiz)
    if arquivos is None:
        return None
    return {"raiz": str(raiz),
            "head": head.stdout.decode().strip() if head and head.returncode == 0 else None,
            "arquivos": arquivos}


def caminhos_mudados(antes: dict, depois: dict) -> list[str]:
    """O que mudou entre duas fotos: sujeira nova ou alterada, mais o que entrou em commit."""
    a, d = antes["arquivos"], depois["arquivos"]
    mudados = {rel for rel in set(a) | set(d) if a.get(rel) != d.get(rel)}
    if antes.get("head") and depois.get("head") and antes["head"] != depois["head"]:
        r = _git(Path(depois["raiz"]), "diff", "--name-only", "-z", antes["head"], depois["head"])
        if r is not None and r.returncode == 0:
            mudados |= {x for x in r.stdout.decode("utf-8", errors="surrogateescape").split("\0") if x}
    return sorted(rel for rel in mudados if not _fora_da_foto(rel))


def _regex_da_posse(padrao: str) -> re.Pattern:
    """Glob de posse para regex: `**` atravessa pastas, `*` e `?` não, e um padrão que
    nomeia uma pasta cobre o que está dentro dela (a convenção do gitignore)."""
    p = padrao.strip()
    if p.startswith("./"):
        p = p[2:]
    p = p.strip("/")
    saida, i = "", 0
    while i < len(p):
        pedaco, avanco = _pedaco_do_glob(p, i)
        saida, i = saida + pedaco, i + avanco
    return re.compile(saida + "(?:/.*)?$")


def _pedaco_do_glob(p: str, i: int) -> tuple[str, int]:
    """O trecho de regex do glob que começa em `i`, e quantos caracteres ele consome."""
    for curinga, regex in (("**/", "(?:.*/)?"), ("**", ".*"), ("*", "[^/]*"), ("?", "[^/]")):
        if p.startswith(curinga, i):
            return regex, len(curinga)
    fim = p.find("]", i + 2) if p[i] == "[" else -1
    if fim < 0:
        return re.escape(p[i]), 1
    miolo = p[i + 1:fim]
    return "[" + ("^" + miolo[1:] if miolo.startswith("!") else miolo) + "]", fim + 1 - i


def cabe_na_posse(rel: str, posse: list[str]) -> bool:
    return any(_regex_da_posse(p).match(rel) for p in posse)


def trabalharam_junto(q: dict, tid: str, foto: dict) -> set[str]:
    """As tarefas que estiveram em voo em algum momento junto com `tid`.

    Pela ordem do histórico, não pelo relógio: o carimbo tem resolução de segundo, e uma
    tarefa que concluiu no mesmo segundo em que esta começou não trabalhou junto com ela.
    Junto é quem já estava em voo no `iniciar` desta, ou quem foi iniciado depois dele.
    """
    junto = set(foto.get("junto", []))
    for ev in q.get("historico", [])[foto.get("seq", 0):]:
        if ev.get("evento") == "iniciou":
            junto.add(ev.get("task"))
    junto.discard(tid)
    return {x for x in junto if x in q["tasks"]}


def fora_da_posse(q: dict, tid: str, mudados: list[str], junto: set[str]) -> list[str]:
    """Os arquivos mudados que não são desta tarefa nem de outra que trabalhava junto."""
    vizinhas = [p for outro in sorted(junto) for p in q["tasks"][outro]["posse"]]
    propria = q["tasks"][tid]["posse"]
    return [rel for rel in mudados
            if not cabe_na_posse(rel, propria) and not cabe_na_posse(rel, vizinhas)]


def caminho_da_foto(slug: str, tid: str) -> Path:
    limpo = re.sub(r"[^A-Za-z0-9_-]", "-", slug)
    return (pasta_do_estado() / "fotos") / limpo / f"{re.sub(r'[^A-Za-z0-9_.-]', '-', tid)}.json"


def guardar_foto(q: dict, tid: str, checkout: Path) -> dict | None:
    foto = foto_do_checkout(checkout)
    alvo = caminho_da_foto(q["slug"], tid)
    if foto is None:
        alvo.unlink(missing_ok=True)
        print(f"   ⚠️  sem foto do checkout ({checkout} fora do git ou sujo demais): o "
              "`concluir` não vai conferir o que a tarefa mudou.")
        return None
    foto["em"] = agora()
    foto["seq"] = len(q.get("historico", []))
    foto["junto"] = sorted(x for x, t in q["tasks"].items()
                           if t["estado"] == "em_progresso" and x != tid)
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(json.dumps(foto, ensure_ascii=False) + "\n", encoding="utf-8")
    return foto


def conferir_posse(q: dict, tid: str) -> tuple[bool, list[str], list[str]]:
    """(conferida, mudados, fora) da tarefa contra a foto do `iniciar`."""
    alvo = caminho_da_foto(q["slug"], tid)
    if not alvo.is_file():
        return False, [], []
    antes = json.loads(alvo.read_text(encoding="utf-8"))
    depois = foto_do_checkout(Path(antes["raiz"]))
    if depois is None:
        return False, [], []
    mudados = caminhos_mudados(antes, depois)
    return True, mudados, fora_da_posse(q, tid, mudados, trabalharam_junto(q, tid, antes))


# --- persistência --------------------------------------------------------------------
def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def minutos_desde(carimbo: str | None) -> float | None:
    """Minutos decorridos desde um ISO-8601 UTC. `None` quando não dá para saber."""
    if not carimbo:
        return None
    try:
        inicio = datetime.fromisoformat(carimbo)
    except ValueError:
        return None
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - inicio).total_seconds() / 60


def vencidas_de(q: dict) -> list[str]:
    """Tarefas em voo além do próprio tempo limite (ADR-0036).

    Só relata — quem age é o `varrer`. Separar as duas coisas é de propósito: o
    relato pode aparecer em qualquer render (painel, estado) sem efeito colateral.
    """
    saida = []
    for tid, t in q["tasks"].items():
        if t["estado"] != "em_progresso":
            continue
        limite = t.get("tempo_limite") or q.get("tempo_limite_padrao") or TEMPO_LIMITE_PADRAO
        decorrido = minutos_desde(t.get("iniciado_em"))
        if decorrido is not None and decorrido > limite:
            saida.append(tid)
    return saida


def caminho(slug: str) -> Path:
    return pasta_do_estado() / f"{re.sub(r'[^A-Za-z0-9_-]', '-', slug)}.json"


def carregar(slug: str) -> dict:
    p = caminho(slug)
    if not p.is_file():
        raise SystemExit(f"❌ quadro '{slug}' não existe. Abra com: quadro.py abrir {slug}")
    return json.loads(p.read_text(encoding="utf-8"))


def salvar(q: dict) -> None:
    pasta_do_estado().mkdir(parents=True, exist_ok=True)
    caminho(q["slug"]).write_text(
        json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def registrar(q: dict, evento: str, **dados) -> None:
    q.setdefault("historico", []).append({"em": agora(), "evento": evento, **dados})


# --- grafo de dependências -----------------------------------------------------------
def cria_ciclo(tasks: dict, novo: str, depende: list[str]) -> list[str] | None:
    """Adicionar `novo` com estas dependências fecharia um ciclo? Devolve o caminho."""
    arestas = {tid: list(t.get("depende", [])) for tid, t in tasks.items()}
    arestas[novo] = list(depende)

    caminho_atual: list[str] = []
    visitando: set[str] = set()
    fechados: set[str] = set()

    def desce(no: str) -> list[str] | None:
        if no in visitando:
            return caminho_atual[caminho_atual.index(no):] + [no]
        if no in fechados or no not in arestas:
            return None
        visitando.add(no)
        caminho_atual.append(no)
        for viz in arestas[no]:
            achado = desce(viz)
            if achado:
                return achado
        caminho_atual.pop()
        visitando.discard(no)
        fechados.add(no)
        return None

    return desce(novo)


def calcular_prontas(q: dict) -> tuple[list[str], dict[str, str]]:
    """As tarefas que a próxima onda pode lançar — e por que cada recusada ficou fora.

    Quatro filtros, nesta ordem, todos determinísticos:
      1. estado `planejada`;
      2. todas as dependências `concluida`;
      3. posse de arquivo livre — não colide com nada em voo nem com o que já foi
         selecionado nesta mesma passada;
      4. teto de onda — as vagas restantes depois de descontar quem está em voo.
    """
    tasks: dict = q["tasks"]
    em_voo = [tid for tid, t in tasks.items() if t["estado"] == "em_progresso"]
    vagas = max(0, q["teto_onda"] - len(em_voo))

    ocupadas = [p for tid in em_voo for p in tasks[tid]["posse"]]
    selecionadas: list[str] = []
    motivos: dict[str, str] = {}

    for tid, t in tasks.items():                     # ordem de declaração: determinística
        if t["estado"] != "planejada":
            motivos[tid] = f"estado {t['estado']}"
            continue
        pendentes = [d for d in t.get("depende", []) if tasks[d]["estado"] != "concluida"]
        if pendentes:
            motivos[tid] = "espera " + ", ".join(pendentes)
            continue
        choques = posses_colidem(t["posse"], ocupadas)
        if choques:
            motivos[tid] = f"posse ocupada ({choques[0][0]} × {choques[0][1]})"
            continue
        if len(selecionadas) >= vagas:
            motivos[tid] = f"teto de onda ({q['teto_onda']}) — entra na próxima"
            continue
        selecionadas.append(tid)
        ocupadas.extend(t["posse"])

    return selecionadas, motivos


def dependentes_de(tasks: dict, raiz: str) -> list[str]:
    """Tarefas que dependem de `raiz`, direta ou transitivamente."""
    atingidos: set[str] = set()
    fronteira = [raiz]
    while fronteira:
        atual = fronteira.pop()
        for tid, t in tasks.items():
            if atual in t.get("depende", []) and tid not in atingidos:
                atingidos.add(tid)
                fronteira.append(tid)
    return sorted(atingidos)


def plano_de_compensacao(q: dict, raiz: str) -> list[str]:
    """Quais tarefas desfazer, e em que ordem, quando a saída de `raiz` se revela inválida.

    O padrão Saga aplicado ao quadro: em vez de tratar a mobilização inteira como uma
    transação indivisível — reiniciar tudo por precaução — cada tarefa é uma transação
    com a própria ação de desfazer (o `--reverter`, que o ADR-0024 já exigia).

    Compensa-se `raiz` e o que foi construído SOBRE ela; o que não dependia dela
    permanece válido e intocado. É essa preservação que separa compensação de reinício.

    A ordem é a inversa da execução: os dependentes mais profundos primeiro, a raiz por
    último. Desfazer na ordem direta derrubaria a base antes do que se apoia nela.
    """
    tasks = q["tasks"]
    afetados = [t for t in dependentes_de(tasks, raiz) if tasks[t]["estado"] == "concluida"]

    def profundidade(tid: str) -> int:
        """Distância máxima até a raiz — quanto maior, mais tarde foi construído."""
        vistos, nivel, fronteira = {tid}, 0, [tid]
        while fronteira:
            proxima = []
            for atual in fronteira:
                for dep in tasks[atual].get("depende", []):
                    if dep == raiz:
                        return nivel + 1
                    if dep in tasks and dep not in vistos:
                        vistos.add(dep)
                        proxima.append(dep)
            fronteira = proxima
            nivel += 1
            if nivel > len(tasks):        # cinto de segurança; o grafo é acíclico
                break
        return nivel

    afetados.sort(key=lambda t: (-profundidade(t), t))
    return afetados + [raiz]


def lacunas_declaradas(q: dict) -> set[str]:
    """Ids citados nas lacunas. `encerrar --lacuna "T7: sem ambiente"` cobre T7."""
    ids = set()
    for texto in q.get("lacunas", []):
        m = re.match(r"\s*([A-Za-z0-9_.-]+)\s*[:\-]", texto)
        if m:
            ids.add(m.group(1))
    return ids


def vista_publica(q: dict) -> dict:
    """A saída de `estado --json`. Campos DERIVADOS para o consumidor não recalcular.

    `pode_encerrar` existe por isso: sem ele, cada runner reimplementa "posso dizer
    que acabou?" do lado dele — e reimplementação diverge na primeira regra nova.
    """
    tasks = q["tasks"]
    por_estado = {e: sum(1 for t in tasks.values() if t["estado"] == e) for e in ESTADOS_TASK}
    prontas, _ = calcular_prontas(q)
    abertas = [tid for tid, t in tasks.items() if t["estado"] != "concluida"]
    cobertas = lacunas_declaradas(q)
    completo = bool(tasks) and not abertas
    return {
        "contrato": CONTRATO_VERSAO,
        "slug": q["slug"],
        "spec": q.get("spec"),
        "cli": q.get("cli"),
        "encerrado": bool(q.get("encerrado_em")),
        "onda": q.get("onda", 0),
        "teto_onda": q["teto_onda"],
        "total": len(tasks),
        "por_estado": por_estado,
        "completo": completo,
        "pode_encerrar": completo or all(tid in cobertas for tid in abertas),
        "em_voo": [tid for tid, t in tasks.items() if t["estado"] == "em_progresso"],
        "prontas": prontas,
        "bloqueadas": [tid for tid, t in tasks.items() if t["estado"] == "bloqueada"],
        "vencidas": vencidas_de(q),
        "lacunas": list(q.get("lacunas", [])),
        "tasks": tasks,
    }


def contrato_publico() -> dict:
    """Declaração legível por máquina. `quadro.py contrato --json`."""
    return {
        "nome": "kairos-forge/quadro",
        "versao": CONTRATO_VERSAO,
        "comando": "quadro.py estado <slug> --json",
        "estados_task": list(ESTADOS_TASK),
        "terminais_task": list(TERMINAIS_TASK),
        "tiers": list(TIERS),
        "teto_onda_padrao": TETO_ONDA_PADRAO,
        "tempo_limite_padrao_min": TEMPO_LIMITE_PADRAO,
        "campos": CAMPOS_ESTADO,
        "regras": [
            "prontas: estado planejada + dependências concluídas + posse livre + vaga na onda",
            "posse: dois padrões colidem salvo refinamento por caminho ou por nome",
            "concluir exige evidência e resultado de gate (rodado ou pulado com motivo)",
            "concluir confere no git o que a tarefa mudou desde o iniciar: arquivo fora da "
            "posse dela e das que trabalhavam junto recusa, salvo --fora-da-posse com motivo",
            "tarefa --leitura tem posse vazia: qualquer arquivo mudado fica fora da posse",
            "encerrar exige quadro completo OU lacuna declarada para cada tarefa aberta",
            "dependência inexistente é recusada na inserção; ciclo é recusado em `depender`",
            "onda nova começa quando nada está em voo (fan-in), não a cada lançamento",
            "vencidas: em_progresso além do tempo limite; `varrer` as bloqueia e libera a vaga",
            "compensar: desfaz a tarefa e o que foi construído sobre ela, em ordem inversa",
            "compensar recusa o plano inteiro se alguma tarefa afetada não declara reverter",
            "concluir e encerrar são idempotentes — repetir não duplica efeito",
        ],
    }


# --- comandos ------------------------------------------------------------------------
def cmd_abrir(a) -> int:
    p = caminho(a.slug)
    if p.is_file():
        print(f"⚠️  quadro '{a.slug}' já existe — use `estado` ou `adicionar`.")
        return 1
    q = {
        "slug": a.slug,
        "spec": a.spec,
        "cli": a.cli,
        "aberto_em": agora(),
        "encerrado_em": None,
        "onda": 0,
        "teto_onda": a.teto_onda,
        "tempo_limite_padrao": a.tempo_limite,
        "orcamento": {"tasks": a.max_tasks, "rodadas_por_task": a.rodadas},
        "tasks": {},
        "lacunas": [],
        "historico": [],
    }
    registrar(q, "abriu", teto_onda=a.teto_onda, spec=a.spec, cli=a.cli)
    salvar(q)
    teto_tasks = f"{a.max_tasks} tasks" if a.max_tasks else "tasks sem teto"
    print(f"✅ quadro '{a.slug}' aberto · teto de onda {a.teto_onda} · "
          f"orçamento: {teto_tasks} / {a.rodadas} rodadas por task · "
          f"tempo limite {a.tempo_limite} min por tarefa")
    return 0


def posse_declarada(texto: str | None, leitura: bool) -> list[str] | None:
    """A posse da tarefa nova; None, com a recusa impressa, se a declaração não fecha."""
    posse = [x.strip() for x in (texto or "").split(",") if x.strip()]
    if bool(posse) != leitura:
        return posse
    if leitura:
        print("❌ --leitura e --posse juntas. Tarefa de leitura não escreve: a posse dela é "
              "vazia, e é isso que o `concluir` confere.")
    else:
        print("❌ --posse vazia. Tarefa sem posse de arquivo declarada não entra no "
              "quadro — é assim que dois workers acabam no mesmo arquivo.\n"
              "   Tarefa que só lê (pesquisa, crítica no canal): declare --leitura.")
    return None


def cmd_adicionar(a) -> int:
    q = carregar(a.slug)
    if q.get("encerrado_em"):
        print("❌ quadro encerrado — não aceita tarefa nova.")
        return 1
    if a.id in q["tasks"]:
        print(f"❌ tarefa '{a.id}' já existe no quadro.")
        return 1
    teto = q["orcamento"].get("tasks")
    if teto and len(q["tasks"]) >= teto:
        print(f"❌ orçamento de tarefas esgotado ({teto}). Amplie no `abrir` ou "
              "encerre com as lacunas declaradas — não estoure em silêncio.")
        return 1

    depende = [d.strip() for d in (a.depende or "").split(",") if d.strip()]
    faltando = [d for d in depende if d not in q["tasks"]]
    if faltando:
        print(f"❌ dependência inexistente: {', '.join(faltando)}. "
              "Adicione a tarefa de que esta depende antes dela.")
        return 1
    ciclo = cria_ciclo(q["tasks"], a.id, depende)
    if ciclo:
        print(f"❌ isso fecharia um ciclo: {' → '.join(ciclo)}")
        return 1

    posse = posse_declarada(a.posse, a.leitura)
    if posse is None:
        return 1
    if a.tier not in TIERS:
        print(f"❌ tier '{a.tier}' inválido — use {', '.join(TIERS)}.")
        return 1

    q["tasks"][a.id] = {
        "titulo": a.titulo,
        "requisito": a.requisito,
        "dono": a.dono,
        "tier": a.tier,
        "posse": posse,
        "leitura": bool(a.leitura),
        "gate": a.gate,
        "tempo_limite": a.tempo_limite,
        "pronto_quando": a.pronto_quando,
        "reverter": a.reverter,
        "depende": depende,
        "estado": "planejada",
        "agente": None,
        "iniciado_em": None,
        "onda": None,
        "rodadas": 0,
        "evidencia": None,
        "gate_resultado": None,
        "bloqueio": None,
        "compensacoes": [],
    }
    registrar(q, "adicionou", task=a.id, dono=a.dono, depende=depende)
    salvar(q)

    # Aviso, não recusa: colisão de posse é legítima (duas tarefas na mesma área),
    # o quadro só não deixa as duas saírem juntas.
    avisos = []
    for outro, t in q["tasks"].items():
        if outro == a.id:
            continue
        ch = posses_colidem(posse, t["posse"])
        if ch and a.id not in t.get("depende", []) and outro not in depende:
            avisos.append(f"{outro} ({ch[0][0]} × {ch[0][1]})")
    print(f"✅ {a.id} adicionada · dono {a.dono} · tier {a.tier}"
          + (" · só leitura" if a.leitura else "")
          + (f" · depende de {', '.join(depende)}" if depende else ""))
    if avisos:
        print(f"   ⚠️  posse sobreposta com {'; '.join(avisos)} — nunca sairão na mesma\n       onda. Para fixar a ordem: quadro.py depender {a.slug} {a.id} --de <outra>;\n       para soltar as duas, refine os padrões de posse.")
    if not a.reverter:
        print("   ⚠️  sem --reverter declarado. Tarefa cujo revert você não consegue "
              "escrever não é autônoma (ADR-0024): ela para no usuário.")
    return 0


def cmd_prontas(a) -> int:
    q = carregar(a.slug)
    prontas, motivos = calcular_prontas(q)
    if a.json:
        print(json.dumps({"prontas": prontas, "fora": motivos,
                          "teto_onda": q["teto_onda"], "onda": q.get("onda", 0) + 1},
                         ensure_ascii=False, indent=2))
        return 0
    if not prontas:
        vista = vista_publica(q)
        if vista["completo"]:
            print("✅ nada pronto: todas as tarefas concluídas. Rode `encerrar`.")
        else:
            print("⏸️  nada pronto agora.")
            for tid, m in motivos.items():
                if q["tasks"][tid]["estado"] in ("planejada", "bloqueada"):
                    print(f"   {tid}: {m}")
        return 0
    print(f"🚀 onda {q.get('onda', 0) + 1} — {len(prontas)} de até {q['teto_onda']}:")
    for tid in prontas:
        t = q["tasks"][tid]
        print(f"   {tid} · {t['dono']} · tier {t['tier']} · posse {', '.join(t['posse'])}")
        print(f"       {t['titulo']}")
    fora = {k: v for k, v in motivos.items()
            if q["tasks"][k]["estado"] == "planejada" and k not in prontas}
    if fora:
        print(f"   ⏳ fora desta onda: " + "; ".join(f"{k} ({v})" for k, v in fora.items()))
    return 0


def cmd_iniciar(a) -> int:
    q = carregar(a.slug)
    t = q["tasks"].get(a.task)
    if not t:
        print(f"❌ tarefa '{a.task}' não existe.")
        return 1
    if t["estado"] == "em_progresso":
        print(f"⚠️  {a.task} já está em progresso com {t['agente']}.")
        return 1
    if t["estado"] == "concluida":
        print(f"❌ {a.task} já está concluída.")
        return 1
    prontas, motivos = calcular_prontas(q)
    if a.task not in prontas:
        print(f"❌ {a.task} não pode entrar agora: {motivos.get(a.task, 'indisponível')}.")
        print("   O quadro decide a ordem — é para isso que ele existe.")
        return 1
    # Nova onda começa quando o quadro está vazio de trabalho em voo: a leva anterior
    # terminou e houve fan-in. Quem entra com gente ainda trabalhando entra na onda
    # corrente — senão "ondas" viraria só um contador de lançamentos.
    if not any(x["estado"] == "em_progresso" for x in q["tasks"].values()):
        q["onda"] = q.get("onda", 0) + 1
    t["estado"] = "em_progresso"
    t["agente"] = a.agente or t["dono"]
    t["iniciado_em"] = agora()
    t["onda"] = q["onda"]
    t["bloqueio"] = None
    registrar(q, "iniciou", task=a.task, agente=t["agente"], onda=q["onda"])
    salvar(q)
    limite = t.get("tempo_limite") or q.get("tempo_limite_padrao") or TEMPO_LIMITE_PADRAO
    print(f"▶️  {a.task} em progresso com {t['agente']} (onda {q['onda']}) · "
          f"tempo limite {limite} min.")
    guardar_foto(q, a.task, Path(a.checkout))
    print(f"   O worker roda, da própria sessão: quadro.py vincular {q['slug']} {a.task}")
    return 0


def cmd_vincular(a) -> int:
    """Liga a sessão do worker à tarefa, para os tokens da sessão contarem na tarefa.

    O script não sabe o id da sessão, mas o hook sabe: o `PostToolUse` grava este
    comando na trajetória com a sessão de quem o rodou. Por isso quem roda é o worker,
    da própria sessão, e não a líder, que é quem mexe no resto do quadro.
    """
    q = carregar(a.slug)
    if a.task not in q["tasks"]:
        print(f"❌ tarefa '{a.task}' não existe.")
        return 1
    print(f"🔗 sessão ligada a {a.task} na trajetória de {q['slug']}.")
    return 0


def cmd_concluir(a) -> int:
    q = carregar(a.slug)
    t = q["tasks"].get(a.task)
    if not t:
        print(f"❌ tarefa '{a.task}' não existe.")
        return 1
    if t["estado"] == "concluida":
        print(f"⚠️  {a.task} já estava concluída.")
        return 0
    if not a.evidencia.strip():
        print("❌ --evidencia vazia. Concluir sem evidência é exatamente o resumo "
              "fluente por cima de resultado parcial que o quadro existe para impedir.")
        return 1
    if not (a.gate_ok or a.gate_pulado):
        alvo = t.get("gate") or "(nenhum gate declarado)"
        print(f"❌ falta o resultado do gate — {alvo}.\n"
              "   Use --gate-ok se rodou e passou, ou --gate-pulado \"motivo\" "
              "se não foi possível. Silêncio sobre o gate não é opção.")
        return 1
    exercida = posse_exercida(q, a.task, a.fora_da_posse)
    if recusar_fora_da_posse(a.task, t, exercida):
        return 1
    t["estado"] = "concluida"
    t["iniciado_em"] = None
    t["concluida_em"] = agora()
    t["evidencia"] = a.evidencia
    t["gate_resultado"] = "ok" if a.gate_ok else f"pulado: {a.gate_pulado}"
    t["posse_exercida"] = exercida
    registrar(q, "concluiu", task=a.task, gate=t["gate_resultado"],
              fora_da_posse=len(exercida["fora"]))
    salvar(q)
    caminho_da_foto(q["slug"], a.task).unlink(missing_ok=True)
    vista = vista_publica(q)
    feitas = vista["por_estado"]["concluida"]
    print(f"✅ {a.task} concluída ({feitas} de {vista['total']}) · gate: {t['gate_resultado']}")
    print(resumo_da_posse(exercida))
    print(o_que_liberou(vista))
    return 0


def posse_exercida(q: dict, tid: str, motivo: str | None) -> dict:
    conferida, mudados, fora = conferir_posse(q, tid)
    return {"conferida": conferida, "mudados": len(mudados), "fora": fora[:50],
            "total_fora": len(fora), "motivo": (motivo or "").strip() or None}


def recusar_fora_da_posse(tid: str, t: dict, exercida: dict) -> bool:
    """Imprime a recusa e devolve True quando há arquivo fora da posse sem motivo escrito."""
    fora = exercida["fora"]
    if not fora or exercida["motivo"]:
        return False
    quem = "tarefa de leitura" if t.get("leitura") else f"posse {', '.join(t['posse'])}"
    print(f"❌ {tid} mudou {exercida['total_fora']} arquivo(s) fora da posse ({quem}):")
    print("\n".join(f"   · {rel}" for rel in fora[:10]))
    print("   A posse declarada era a promessa; o git mostra o que foi feito. Desfaça o\n"
          "   que não era desta tarefa, ou, se a mudança era necessária, conclua com\n"
          "   --fora-da-posse \"motivo\" — fica registrado e aparece no ledger.")
    return True


def resumo_da_posse(exercida: dict) -> str:
    if exercida["fora"]:
        return (f"   ⚠️  {exercida['total_fora']} arquivo(s) fora da posse, aceitos: "
                f"{exercida['motivo']}")
    if exercida["conferida"]:
        return (f"   posse conferida no git: {exercida['mudados']} arquivo(s) mudado(s), "
                "todos na posse.")
    return "   ⚠️  posse não conferida: não houve foto no `iniciar`."


def o_que_liberou(vista: dict) -> str:
    if vista["prontas"]:
        return f"   🔓 liberou: {', '.join(vista['prontas'])}"
    if vista["completo"]:
        return "   🏁 quadro completo — rode `encerrar`."
    return "   ⏳ nada liberado ainda."


def cmd_bloquear(a) -> int:
    q = carregar(a.slug)
    t = q["tasks"].get(a.task)
    if not t:
        print(f"❌ tarefa '{a.task}' não existe.")
        return 1
    t["estado"] = "bloqueada"
    t["iniciado_em"] = None
    t["bloqueio"] = a.motivo
    registrar(q, "bloqueou", task=a.task, motivo=a.motivo)
    salvar(q)
    teto = q["orcamento"].get("rodadas_por_task", RODADAS_PADRAO)
    print(f"⛔ {a.task} bloqueada: {a.motivo}")
    print(f"   rodadas usadas: {t['rodadas']} de {teto}")
    if t["rodadas"] >= teto:
        print("   🚨 orçamento de rodadas esgotado nesta tarefa. Não relance: "
              "escale ao usuário ou encerre com a lacuna declarada.")
    return 0


def cmd_varrer(a) -> int:
    """Bloqueia tarefas em voo além do tempo limite, liberando a vaga da onda (ADR-0036).

    A fábrica audita o sistema do usuário por timeout e retry na `/diagnosticar`, e o
    Murilo é dono do assunto — mas o próprio orquestrador não tinha nenhum dos dois.
    Worker que morre sem avisar segurava a vaga para sempre: o teto nunca liberava, a
    onda seguinte nunca saía, e nada nunca dava erro. Travar em silêncio é pior que
    falhar alto.

    Bloquear, e não concluir: o tempo estourou, não há evidência nenhuma de que a
    tarefa ficou pronta.
    """
    q = carregar(a.slug)
    vencidas = vencidas_de(q)
    if not vencidas:
        em_voo = [tid for tid, t in q["tasks"].items() if t["estado"] == "em_progresso"]
        print(f"✅ nada vencido · {len(em_voo)} em voo dentro do prazo.")
        return 0
    if a.dry_run:
        print(f"⏱️  {len(vencidas)} vencida(s) — simulação, nada alterado:")
    for tid in vencidas:
        t = q["tasks"][tid]
        limite = t.get("tempo_limite") or q.get("tempo_limite_padrao") or TEMPO_LIMITE_PADRAO
        decorrido = minutos_desde(t.get("iniciado_em")) or 0
        motivo = (f"tempo limite excedido: {decorrido:.0f} min em voo, limite {limite} min "
                  f"(agente {t.get('agente')})")
        print(f"   ⏱️  {tid} · {motivo}")
        if a.dry_run:
            continue
        t["estado"] = "bloqueada"
        t["iniciado_em"] = None
        t["bloqueio"] = motivo
        registrar(q, "venceu", task=tid, minutos=round(decorrido))
    if a.dry_run:
        print("\n(simulação — repita sem --dry-run para bloquear e liberar as vagas)")
        return 0
    salvar(q)
    vista = vista_publica(q)
    print(f"   → {len(vencidas)} vaga(s) liberada(s) na onda.")
    if vista["prontas"]:
        print(f"   🔓 pode lançar agora: {', '.join(vista['prontas'])}")
    print("   Antes de reabrir, decida: o worker morreu (relance) ou a tarefa é grande\n"
          "   demais para o limite (aumente o --tempo-limite dela). Relançar sem decidir\n"
          "   é como o orçamento de rodadas vira ficção.")
    return 0


def cmd_compensar(a) -> int:
    """Desfaz uma tarefa inválida e o que foi construído sobre ela — padrão Saga (ADR-0036).

    Até aqui, falha tardia só tinha duas saídas: declarar lacuna e parar, ou refazer
    tudo. A primeira desperdiça o trabalho ainda válido; a segunda desperdiça o trabalho
    todo. O que faltava era o meio-termo — e ele já estava quase pronto, porque o
    `--reverter` do ADR-0024 é exatamente a ação compensatória que o Saga pede.
    """
    q = carregar(a.slug)
    t = q["tasks"].get(a.task)
    if not t:
        print(f"❌ tarefa '{a.task}' não existe.")
        return 1
    if t["estado"] != "concluida":
        print(f"❌ {a.task} está '{t['estado']}' — só se compensa o que foi concluído. "
              "Para tarefa em aberto, use `bloquear`.")
        return 1

    plano = plano_de_compensacao(q, a.task)
    sem_reverter = [tid for tid in plano if not q["tasks"][tid].get("reverter")]
    if sem_reverter:
        print(f"❌ {len(sem_reverter)} tarefa(s) do plano não declaram como desfazer: "
              f"{', '.join(sem_reverter)}")
        print("   O plano inteiro é recusado: compensação parcial deixa o repositório num")
        print("   estado que ninguém desenhou — pior que não ter começado.")
        print("   Tarefa cujo revert você não consegue escrever é irreversível, e")
        print("   irreversível para no usuário (ADR-0024).")
        return 1

    preservadas = [tid for tid, x in q["tasks"].items()
                   if x["estado"] == "concluida" and tid not in plano]
    print(f"🔄 Plano de compensação de {a.task} — {len(plano)} tarefa(s), ordem inversa:")
    for i, tid in enumerate(plano, 1):
        x = q["tasks"][tid]
        papel = "raiz (saída inválida)" if tid == a.task else "construída sobre a raiz"
        print(f"   {i}. {tid} · {x['dono']} · {papel}")
        print(f"      desfazer: {x['reverter']}")
    if preservadas:
        print(f"   ✅ preservadas (não dependiam de {a.task}): {', '.join(preservadas)}")
    else:
        print("   ⚠️  nenhuma tarefa concluída sobrou preservada — neste caso compensar "
              "equivale a refazer tudo.")

    if not a.aplicar:
        print(f"\n(simulação — repita com --aplicar para executar o plano e devolver "
              f"as {len(plano)} tarefas à fila)")
        return 0

    for tid in plano:
        x = q["tasks"][tid]
        x.setdefault("compensacoes", []).append(
            {"em": agora(), "por": a.task, "motivo": a.motivo, "reverteu": x["reverter"]})
        x["estado"] = "planejada"
        x["evidencia"] = None
        x["gate_resultado"] = None
        x["iniciado_em"] = None
    # A rodada queima só na raiz: ela produziu a saída errada. As dependentes estavam
    # certas sobre uma base que mudou — cobrar orçamento delas seria punir o inocente.
    q["tasks"][a.task]["rodadas"] += 1
    registrar(q, "compensou", task=a.task, plano=plano, motivo=a.motivo)
    salvar(q)

    teto = q["orcamento"].get("rodadas_por_task", RODADAS_PADRAO)
    print(f"\n✅ {len(plano)} tarefa(s) de volta à fila. Execute os `desfazer` acima "
          "NESTA ORDEM antes de relançar.")
    print(f"   Rodada queimada só em {a.task} ({q['tasks'][a.task]['rodadas']} de {teto}) "
          "— as dependentes não erraram, foram invalidadas.")
    if q["tasks"][a.task]["rodadas"] >= teto:
        print("   🚨 orçamento da raiz esgotado. Se compensar de novo, escale ao usuário.")
    return 0


def cmd_reabrir(a) -> int:
    q = carregar(a.slug)
    t = q["tasks"].get(a.task)
    if not t:
        print(f"❌ tarefa '{a.task}' não existe.")
        return 1
    if t["estado"] != "bloqueada":
        print(f"❌ {a.task} está '{t['estado']}' — só tarefa bloqueada é reaberta.")
        return 1
    teto = q["orcamento"].get("rodadas_por_task", RODADAS_PADRAO)
    if t["rodadas"] >= teto:
        print(f"❌ {a.task} já usou {t['rodadas']} de {teto} rodadas. "
              "Mais uma rodadinha é como o orçamento vira ficção — escale.")
        return 1
    t["estado"] = "planejada"
    t["rodadas"] += 1          # a rodada de correção é esta reabertura, não o início
    registrar(q, "reabriu", task=a.task, rodada=t["rodadas"])
    salvar(q)
    restam = teto - t["rodadas"]
    print(f"↩️  {a.task} de volta à fila · rodada {t['rodadas']} de {teto}"
          + (f" · restam {restam}" if restam else " · última"))
    return 0

def cmd_depender(a) -> int:
    """Adiciona uma aresta depois da inserção — é assim que uma colisão vira serialização.

    É a única porta pela qual um ciclo pode entrar no grafo (na inserção, uma tarefa
    só depende do que já existe, então o grafo nasce acíclico). Por isso a checagem
    de ciclo mora aqui.
    """
    q = carregar(a.slug)
    t = q["tasks"].get(a.task)
    if not t:
        print(f"❌ tarefa '{a.task}' não existe.")
        return 1
    if a.de not in q["tasks"]:
        print(f"❌ tarefa '{a.de}' não existe.")
        return 1
    if a.de == a.task:
        print("❌ uma tarefa não depende de si mesma.")
        return 1
    if a.de in t["depende"]:
        print(f"⚠️  {a.task} já depende de {a.de}.")
        return 0
    if t["estado"] == "concluida":
        print(f"❌ {a.task} já está concluída — aresta nova não muda o passado.")
        return 1
    ciclo = cria_ciclo({k: v for k, v in q["tasks"].items() if k != a.task},
                       a.task, t["depende"] + [a.de])
    if ciclo:
        print(f"❌ isso fecharia um ciclo: {' → '.join(ciclo)}")
        print("   Ciclo no grafo é deadlock: nenhuma das duas jamais fica pronta.")
        return 1
    t["depende"].append(a.de)
    registrar(q, "dependeu", task=a.task, de=a.de)
    salvar(q)
    print(f"🔗 {a.task} agora depende de {a.de} — as duas deixam de disputar a mesma onda.")
    return 0


def _barra(feitas: int, total: int, largura: int = 20) -> str:
    pct = int(round(100 * feitas / total)) if total else 0
    cheio = int(round(largura * pct / 100))
    return f"[{'█' * cheio}{'·' * (largura - cheio)}] {pct}%"


def cmd_estado(a) -> int:
    q = carregar(a.slug)
    vista = vista_publica(q)
    if a.json:
        print(json.dumps(vista, ensure_ascii=False, indent=2))
        return 0
    pe = vista["por_estado"]
    alvo = f" · {vista['spec']}" if vista["spec"] else ""
    print(f"📋 {vista['slug']}{alvo} · onda {vista['onda']} · teto {vista['teto_onda']}"
          + (" · ENCERRADO" if vista["encerrado"] else ""))
    print(f"   {_barra(pe['concluida'], vista['total'])} "
          f"{pe['concluida']}/{vista['total']} concluídas")
    colunas = [("A fazer", "planejada"), ("Em progresso", "em_progresso"),
               ("Bloqueadas", "bloqueada"), ("Pronto", "concluida")]
    for rotulo, estado in colunas:
        ids = [tid for tid, t in vista["tasks"].items() if t["estado"] == estado]
        if not ids:
            continue
        itens = []
        for tid in ids:
            t = vista["tasks"][tid]
            marca = " ✓gate" if t["gate_resultado"] == "ok" else ""
            quem = f" ({t['agente']})" if t["agente"] and estado == "em_progresso" else ""
            itens.append(f"{tid}{quem}{marca}")
        print(f"   {rotulo}: {', '.join(itens)}")
    for tid in vista["bloqueadas"]:
        print(f"   ⛔ {tid}: {vista['tasks'][tid]['bloqueio']}")
    if vista["prontas"]:
        print(f"   🚀 pode lançar agora: {', '.join(vista['prontas'])}")
    if vista["lacunas"]:
        print("   ⚠️  lacunas declaradas: " + "; ".join(vista["lacunas"]))
    return 0


def _telemetria():
    """O telemetria.py, que lê a trajetória. None se não der para importar."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import telemetria
        return telemetria
    except Exception:
        return None


def gasto_do_quadro(q: dict, tel) -> dict | None:
    """Os tokens da mobilização, lidos da trajetória (ADR-0048). None se não foram medidos."""
    if tel is None:
        return None
    try:
        gasto = tel.tokens_da_mobilizacao(tel.carregar(Path.cwd(), None), q)
    except Exception:
        return None
    return gasto if gasto["medido"] else None


def por_dono_do_quadro(q: dict, gasto: dict | None, tel) -> dict[str, dict]:
    por_dono: dict[str, dict] = {}
    por_tarefa = gasto["por_tarefa"] if gasto else {}
    for tid, t in q["tasks"].items():
        d = por_dono.setdefault(t["dono"], {"tier": t["tier"], "tasks": 0, "concluidas": 0,
                                            "rodadas": 0, "fora": 0, "tokens": {}})
        d["tasks"] += 1
        d["concluidas"] += t["estado"] == "concluida"
        d["rodadas"] += t["rodadas"]
        d["fora"] += (t.get("posse_exercida") or {}).get("total_fora", 0)
        for uso in por_tarefa.get(tid, {}).values():
            d["tokens"] = d["tokens"] or tel.zero()
            tel.somar(d["tokens"], uso)
    return por_dono


def linhas_por_dono(q: dict, gasto: dict | None, tel) -> list[str]:
    """A tabela por teammate. A coluna de tokens só aparece quando houve medida."""
    por_dono = por_dono_do_quadro(q, gasto, tel)
    coluna = " Tokens novos |" if gasto else ""
    saida = [f"| Teammate | Tier | Tasks | Concluídas | Rodadas de correção | Fora da posse |{coluna}",
             "|---|---|---|---|---|---|" + ("---|" if gasto else "")]
    for dono in sorted(por_dono):
        d = por_dono[dono]
        extra = f" {tel.formatar(tel.novos(d['tokens']))} |" if gasto else ""
        saida.append(f"| {dono} | {d['tier']} | {d['tasks']} | {d['concluidas']} | "
                     f"{d['rodadas']} | {d['fora']} |{extra}")
    return saida


def linha_de_tokens(gasto: dict | None, tel) -> str:
    if gasto is None:
        return ("Tokens: não medidos — nenhuma leitura do hook Stop durante o quadro (hoje só "
                "o Claude Code grava). Custo real: /cost.")
    cat = gasto["categorias"]

    def n(uso: dict) -> str:
        return tel.formatar(tel.novos(uso))

    return (f"Tokens novos (relatados pelo transcript, {gasto['sessoes']} sessão(ões)): "
            f"{n(gasto['total'])} — em tarefa concluída {n(cat['concluida'])} · desfeita "
            f"{n(cat['desfeita'])} · em aberto {n(cat['aberta'])} · sem tarefa vinculada "
            f"{n(cat['sem_tarefa'])}. Cache lido à parte: "
            f"{tel.formatar(gasto['total']['cache_leitura'])}.")


def cmd_ledger(a) -> int:
    """A tabela do relatório final (ADR-0013), montada do quadro em vez de na lembrança."""
    q = carregar(a.slug)
    tel = _telemetria()
    gasto = gasto_do_quadro(q, tel)
    print("\n".join(linhas_por_dono(q, gasto, tel)))
    vista = vista_publica(q)
    teto = q["orcamento"].get("rodadas_por_task", RODADAS_PADRAO)
    total_rodadas = sum(t["rodadas"] for t in q["tasks"].values())
    print(f"\nOrçamento: {total_rodadas} rodadas usadas · teto {teto} por task · "
          f"ondas: {vista['onda']} · teto de onda {vista['teto_onda']}")
    print(f"Entrega: {vista['por_estado']['concluida']} de {vista['total']} tarefas planejadas.")
    if not vista["completo"]:
        abertas = [tid for tid, t in vista["tasks"].items() if t["estado"] != "concluida"]
        print(f"Lacunas: {', '.join(abertas)} — declare cada uma, nunca omita.")
    excedidas = [f"{tid} ({(t.get('posse_exercida') or {}).get('motivo')})"
                 for tid, t in q["tasks"].items()
                 if (t.get("posse_exercida") or {}).get("total_fora")]
    if excedidas:
        print(f"Fora da posse, aceito com motivo: {'; '.join(excedidas)}")
    print(linha_de_tokens(gasto, tel))
    return 0


def cmd_encerrar(a) -> int:
    q = carregar(a.slug)
    if q.get("encerrado_em"):
        print("⚠️  quadro já encerrado.")
        return 0
    if a.lacuna:
        q["lacunas"] = list(dict.fromkeys(q.get("lacunas", []) + a.lacuna))
    vista = vista_publica(q)
    if not vista["pode_encerrar"]:
        abertas = [tid for tid, t in vista["tasks"].items() if t["estado"] != "concluida"]
        sem_lacuna = [tid for tid in abertas if tid not in lacunas_declaradas(q)]
        print(f"❌ {len(abertas)} tarefa(s) aberta(s) sem lacuna declarada: "
              f"{', '.join(sem_lacuna)}")
        print("   Em cadeia, uma falha para tudo e todo mundo vê. Em grafo, o nó que")
        print("   falhou some num relatório que parece completo — é esse relatório que")
        print("   esta recusa existe para impedir.")
        print(f"   Declare: quadro.py encerrar {a.slug} --lacuna \"{sem_lacuna[0]}: motivo\"")
        return 1
    q["encerrado_em"] = agora()
    registrar(q, "encerrou", completo=vista["completo"], lacunas=len(vista["lacunas"]))
    salvar(q)
    pe = vista["por_estado"]
    print(f"🏁 {q['slug']} encerrado · {pe['concluida']} de {vista['total']} tarefas "
          f"planejadas concluídas em {vista['onda']} onda(s).")
    for texto in vista["lacunas"]:
        print(f"   ⚠️  lacuna: {texto}")
    return 0


def cmd_listar(a) -> int:
    if not pasta_do_estado().is_dir():
        print("Nenhum quadro em .agents/quadro/.")
        return 0
    achou = False
    for p in sorted(pasta_do_estado().glob("*.json")):
        try:
            vista = vista_publica(json.loads(p.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"  ⚠️  {p.name}: ilegível — {e}")
            continue
        achou = True
        pe = vista["por_estado"]
        marca = "🏁" if vista["encerrado"] else "🔄"
        print(f"  {marca} {vista['slug']} · {pe['concluida']}/{vista['total']} · "
              f"onda {vista['onda']}" + (f" · {vista['spec']}" if vista["spec"] else ""))
    if not achou:
        print("Nenhum quadro em .agents/quadro/.")
    return 0


def cmd_contrato(a) -> int:
    decl = contrato_publico()
    if a.json:
        print(json.dumps(decl, ensure_ascii=False, indent=2))
        return 0
    print(f"{decl['nome']} v{decl['versao']} — {decl['comando']}")
    print(f"  estados de task: {', '.join(decl['estados_task'])}")
    print(f"  campos: {', '.join(decl['campos'])}")
    for r in decl["regras"]:
        print(f"  · {r}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="quadro.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("abrir", help="abre um quadro de mobilização")
    p.add_argument("slug")
    p.add_argument("--spec")
    p.add_argument("--cli")
    p.add_argument("--teto-onda", type=int, default=TETO_ONDA_PADRAO)
    p.add_argument("--max-tasks", type=int, default=0)
    p.add_argument("--rodadas", type=int, default=RODADAS_PADRAO)
    p.add_argument("--tempo-limite", type=int, default=TEMPO_LIMITE_PADRAO,
                   help="minutos que uma tarefa pode ficar em voo (default: 60)")
    p.set_defaults(fn=cmd_abrir)

    p = sub.add_parser("adicionar", help="adiciona uma tarefa atômica")
    p.add_argument("slug")
    p.add_argument("--id", required=True)
    p.add_argument("--titulo", required=True)
    p.add_argument("--requisito", default=None)
    p.add_argument("--dono", required=True)
    p.add_argument("--posse", default="", help="globs separados por vírgula")
    p.add_argument("--leitura", action="store_true",
                   help="tarefa que não escreve: posse vazia, conferida no concluir")
    p.add_argument("--pronto-quando", required=True)
    p.add_argument("--gate", default=None)
    p.add_argument("--depende", default="")
    p.add_argument("--tier", default="padrao")
    p.add_argument("--reverter", default=None)
    p.add_argument("--tempo-limite", type=int, default=None,
                   help="minutos em voo só desta tarefa (default: o do quadro)")
    p.set_defaults(fn=cmd_adicionar)

    p = sub.add_parser("prontas", help="o que a próxima onda pode lançar")
    p.add_argument("slug")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_prontas)

    p = sub.add_parser("iniciar", help="marca a tarefa em progresso")
    p.add_argument("slug")
    p.add_argument("task")
    p.add_argument("--agente", default=None)
    p.add_argument("--checkout", default=".",
                   help="onde a tarefa escreve, se for num worktree próprio (default: aqui)")
    p.set_defaults(fn=cmd_iniciar)

    p = sub.add_parser("vincular", help="o worker liga a própria sessão à tarefa")
    p.add_argument("slug")
    p.add_argument("task")
    p.set_defaults(fn=cmd_vincular)

    p = sub.add_parser("concluir", help="marca a tarefa concluída com evidência")
    p.add_argument("slug")
    p.add_argument("task")
    p.add_argument("--evidencia", required=True)
    p.add_argument("--gate-ok", action="store_true")
    p.add_argument("--gate-pulado", default=None)
    p.add_argument("--fora-da-posse", default=None,
                   help="motivo para aceitar arquivo mudado fora da posse")
    p.set_defaults(fn=cmd_concluir)

    p = sub.add_parser("varrer", help="bloqueia tarefas em voo além do tempo limite")
    p.add_argument("slug")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_varrer)

    p = sub.add_parser("compensar", help="desfaz uma tarefa inválida e o que veio sobre ela")
    p.add_argument("slug")
    p.add_argument("task")
    p.add_argument("--motivo", required=True)
    p.add_argument("--aplicar", action="store_true", help="sem isso, só mostra o plano")
    p.set_defaults(fn=cmd_compensar)

    p = sub.add_parser("depender", help="adiciona aresta: serializa uma colisão")
    p.add_argument("slug")
    p.add_argument("task")
    p.add_argument("--de", required=True, help="tarefa que precisa terminar antes")
    p.set_defaults(fn=cmd_depender)

    p = sub.add_parser("bloquear", help="registra bloqueio reportado pelo teammate")
    p.add_argument("slug")
    p.add_argument("task")
    p.add_argument("--motivo", required=True)
    p.set_defaults(fn=cmd_bloquear)

    p = sub.add_parser("reabrir", help="devolve tarefa bloqueada à fila")
    p.add_argument("slug")
    p.add_argument("task")
    p.set_defaults(fn=cmd_reabrir)

    p = sub.add_parser("estado", help="o quadro vivo")
    p.add_argument("slug")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_estado)

    p = sub.add_parser("ledger", help="tabela do relatório final")
    p.add_argument("slug")
    p.set_defaults(fn=cmd_ledger)

    p = sub.add_parser("encerrar", help="fecha o quadro")
    p.add_argument("slug")
    p.add_argument("--lacuna", action="append", default=[])
    p.set_defaults(fn=cmd_encerrar)

    p = sub.add_parser("listar", help="quadros existentes")
    p.set_defaults(fn=cmd_listar)

    p = sub.add_parser("contrato", help="contrato de integração (ADR-0034)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_contrato)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
