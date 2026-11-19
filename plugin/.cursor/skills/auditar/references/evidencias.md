# Coleta de evidências — auditar

Material de apoio da skill `auditar`. Leia ao coletar: detalhe de cada comando read-only e como converter a saída em pontos.

## Coletar evidências para Estrutura

Comandos sugeridos (read-only, sem dependências fora do projeto):

- Existência de `CODEOWNERS`: `ls CODEOWNERS .github/CODEOWNERS docs/CODEOWNERS 2>/dev/null`.
- Mapa recente: `ls docs/arquitetura/MAPA-*.md 2>/dev/null` e checar data no nome.
- Modelo de ameaças: `ls docs/seguranca/AMEACAS-*.md 2>/dev/null`.
- Top-10 churn 90d: `git log --since='90 days ago' --pretty=format: --name-only | sort | uniq -c | sort -rn | head -10`. Cruzar com `CODEOWNERS`.
- Acoplamento e duplicação: amostragem manual. Marque como hipótese se não houver mapa.

Helena, Rafael ou Diego podem ser citados no relatório como responsáveis sugeridos por fechar lacunas desta dimensão.

## Coletar evidências para Conhecimento: grafo

Para o critério do grafo de conhecimento (read-only, sem dependências):

- Existência: `ls .agents/grafo/entidades.jsonl .agents/grafo/relacoes.jsonl .agents/grafo/esquema.md 2>/dev/null`.
- Contrato: `python3 <plugin>/scripts/grafo.py validar` — exit 0 = +2 pts; erros = 0 nesse subcritério e liste os 3 primeiros no relatório. Entidade sem `fontes` e relação sem `fonte` são erro de contrato. Sem grafo, ele sai 1 e o subcritério vale 0: sem a pasta, diz que ela não existe; sem nenhuma entidade (a pasta só com `codigo.jsonl`, por exemplo: a camada de código não é o grafo de conhecimento), diz "Sem grafo de conhecimento", ou lista as arestas órfãs se houver relação. Até a v0.53.0, a pasta só com `codigo.jsonl` saía 0 (ADR-0061).
- Frescor: data de "Última construção" em `.agents/grafo/GRAFO.md` ≤ 30 dias = +1 pt.
- Bônus de diagnóstico (não pontua, mas entra no relatório): `grafo.py diagnosticar` — mais de 1 componente conexo ou densidade < 0.5 são lacunas candidatas ao top 3.
- Memória de sessão (não pontua — ADR-0010): se as tools MCP `memory_*` (ai-memory) estiverem disponíveis, registre no relatório "memória de sessão ativa" (com `memory_status` se quiser detalhe); se não, registre "inativa — camada opcional, ver docs/memoria-persistente.md".

Olívia é a responsável sugerida por lacunas deste critério.

## Coletar evidências para Guardrails: segurança do setup

O kairos-forge embarca `scripts/check-agent-security.py`, que audita a *configuração de agentes/hooks* — não o código do produto. Para o critério de setup customizado, rode-o apontando para a config do projeto:

- `python3 <plugin>/scripts/check-agent-security.py .claude` — varre `.claude/agents/`, hooks, segredos e os workflows da fábrica em `.github/workflows/` (token de pessoa é achado).
- Nos hooks, lê o bloco `hooks` de `.claude/settings.json` e `.claude/settings.local.json`, e o `.codex/hooks.json` e o `.cursor/hooks.json` da pasta do projeto. Do settings, só o bloco `hooks` conta: o `deny` de `curl | sh` nas permissões é proteção, não achado; settings que não é JSON válido é varrido inteiro. Até a v0.53.0, com a raiz em `.claude`, ele não lia os settings nem o `.codex/hooks.json` e o `.cursor/hooks.json` do projeto, então a auditoria anterior que pontuou cheio aqui não olhou esses hooks (ADR-0061).
- Nenhum achado = pontue cheio (4). Achado ALTA (allow-list ausente, vazia ou curinga, segredo hardcoded) sai 1; achado MEDIA (injeção em hook, workflow da fábrica com token de pessoa) sai 0. Os dois pontuam 0 e entram no relatório: leia a saída, não só o exit.
- Projeto sem agentes nem hooks customizados (em `.claude/`, `.codex/` ou `.cursor/`) = pontue cheio (não há superfície de risco a auditar). O comando roda também sem a pasta `.claude/`.

Helena é a responsável sugerida por achados desta verificação.
