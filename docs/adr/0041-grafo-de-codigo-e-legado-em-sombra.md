# ADR-0041 — Grafo de código por AST, escada de prontidão do legado e corte em sombra

- **Status:** aceito
- **Data:** 2026-09-17
- **Versão:** v0.34.0

## Contexto

Terceiro e último ADR da auditoria contra o material do Tech Leads Club (ADR-0039 verificação,
ADR-0040 porta de entrada). Este cobre dois quadros do workshop que falam de **estrutura**:
o paper *The Navigation Paradox* e o quadro *Legado com IA*.

**O paper.** 30 tarefas × 3 condições × 3 execuções num repositório FastAPI, Claude Sonnet 4.5.
Hipótese: janela de contexto maior não elimina a navegação estrutural — o problema muda de
capacidade para saliência. Resultado que importa: quando o arquivo certo **não compartilha
vocabulário** com a pergunta (o grupo "oculto"), o agente com grafo de dependências via MCP
(arestas IMPORTS, INHERITS, INSTANTIATES extraídas por AST) encontra 99% dos arquivos
necessários contra 76% da busca textual — 23 pontos. Nos outros dois grupos, busca por
palavra-chave (BM25) empata ou ganha. A leitura honesta: grafo de código não substitui
grep; cobre o caso em que grep é cego, e esse caso é o que mais custa (regressão em
chamador que ninguém viu). Ressalva do próprio desenho: um repositório, um modelo, 30
tarefas — sinal, não lei.

**O que o forge tinha.** O grafo de conhecimento (ADR-0009) é extraído de **documentos**
pelo modelo, com precisão > recall e julgamento em cada etapa. Não tem aresta de código:
"quem importa este arquivo" era grep na `mapear-arquitetura` e nada no `/mobilizar`, no
`/validar` e no `/revisar` — o teammate editava um utilitário sem saber quantos chamadores
tinha, e a faixa de raio de explosão (ADR-0031) dizia "muitos chamadores" sem número. O
`diagnostico.py` conta dependências de manifesto (pacotes externos), não de arquivo.

**O quadro de legado.** Cinco camadas em que cada uma depende da anterior — build
reprodutível em um comando → padronização (formatter, linter, código morto fora) → contexto
para o agente (CLAUDE.md, mapa de módulos, glossário) → testes de caracterização → harness
(o agente verifica sozinho) — e a tese que dá nome ao quadro: *o trabalho não é impedir a
IA de errar; é transformar erro silencioso em erro visível*. Mais um mecanismo que o
`/migrar` não tinha: **strangler fig com comparação diferencial** — mesma entrada nas duas
rotas, saídas comparadas, divergências registradas, e o legado só desliga depois de
divergência zero por tempo suficiente. O `/migrar` tinha caracterização (cenários fixos,
escritos antes) e corte por flag com métrica agregada (erro, latência, custo). Faltava o
comparador em tráfego real, que é o que pega a regra de 2009 que ninguém lembrava.

## Decisão

**1. `grafo.py codigo` — a camada de código, determinística.** Novo subcomando que percorre
os arquivos rastreados pelo git (`.py`, `.js/.ts/.jsx/.tsx/.mjs/.cjs`, `.go`) e grava
`codigo.jsonl` no diretório do grafo com arestas `importa`, `herda` e `instancia`, no
**mesmo formato** de `relacoes.jsonl` (`origem`, `predicado`, `destino`, `fonte` =
`arquivo:linha`). Python por `ast` (imports absolutos e relativos, layout `src/`, herança
por `ClassDef.bases`, instanciação por `Call` de nome importado com inicial maiúscula);
JS/TS por regex (`import`/`export from`/`require`/`import()`, resolução de extensão e
`index`, aliases `@/` e `~/` e os `paths` do `tsconfig`; `extends` e `new`); Go por bloco
de `import` contra o `module` do `go.mod`, com destino no pacote. Import que não resolve
para arquivo do projeto é contado, nunca inventado. `codigo.meta.json` registra quando foi
construída, quantos arquivos e arestas, e os hubs (mais importados). É a **única escrita**
do `grafo.py`, e é regenerável: a camada é derivada do código, não curada — rodar de novo
substitui.

Por que camada separada e não `relacoes.jsonl`: o grafo de conhecimento passa por
extração, resolução e perfil com modelo, e o `atualizar` reescreve por documento. Aresta de
código não tem julgamento e é regenerada inteira. Misturar as duas obrigaria o pipeline do
modelo a preservar o que ele não produziu.

**2. `grafo.py contexto <arquivo>` — a vizinhança de 1 salto.** É o
`get_architectural_context` do paper: quem importa o arquivo, o que ele importa, quem herda
dele, quem o instancia, com `--saltos` para ir além e `--json` para ferramenta. E a
**ponte com o conhecimento**: as entidades de `entidades.jsonl` que citam o arquivo em
`fontes` aparecem no fim — o arquivo liga a camada estrutural à SPEC e ao ADR que falam
dele. Arquivo que ninguém importa é dito com essas palavras: ponto de entrada, script,
teste — ou código morto.

**3. Quem passa a usar.**

- `/mobilizar` — o prompt do teammate ganha a regra: antes de editar arquivo fora da sua
  posse imediata ou com chamadores, `contexto` primeiro; chamador fora da posse é pedido à
  Laura, não edição.
- `/revisar` — "muitos chamadores" na faixa 2 vira número: `contexto` com 5+ importadores
  sobe de faixa. O sinal que o modelo não influencia vale mais que a impressão dele.
- `/validar` — para cada arquivo do diff, chamadores **fora do diff** são a lista de
  regressão escondida; a validação cita quantos e se o gate os cobre.
- `/mapear-arquitetura` — o passo de acoplamento parte do `codigo` (hubs, bidirecionais)
  em vez de grep, e o grep fica para o que a camada não cobre (linguagens fora das três).
- `/diagnosticar` — hubs e arquivos órfãos entram na evidência de nível 1.
- `/migrar` — o inventário da fatia usa `contexto` para saber o que a rota de corte
  precisa preservar.

**4. Escada de prontidão do legado, como pré-condição do `/migrar` e saída do
`/diagnosticar`.** Cinco degraus, cada um dependente do anterior: (1) build reprodutível em
um comando; (2) padronização — formatter, linter, código morto fora; (3) contexto para o
agente — CLAUDE.md, mapa de módulos, glossário; (4) testes de caracterização; (5) harness —
o agente verifica sozinho. Ivan declara em que degrau o sistema está antes de fatiar, e
não pula degrau: caracterizar (4) sem build reprodutível (1) é caracterizar o que não se
consegue rodar duas vezes igual. O `/diagnosticar` reporta o degrau atual na seção nova
"Prontidão para trabalhar com IA", com o próximo degrau como encaminhamento.

**5. Corte em sombra no `/migrar`.** O passo "Cortar" ganha o modo **sombra** antes do
percentual: a rota nova recebe **cópia** do tráfego real, o comparador confronta a saída
das duas rotas para a mesma entrada, e cada divergência é registrada com entrada, as duas
saídas e a decisão (bug do legado preservado? bug da rota nova? diferença aceita?). O
critério de virar tráfego de verdade é **divergência zero por tempo suficiente** —
declarado por fatia, nunca "parece estável". Caracterização continua obrigatória (é o
contrato antes de tocar); a sombra é o que pega o cenário que ninguém escreveu. Fatia sem
sombra possível (efeito colateral não idempotente, custo dobrado inaceitável) diz isso na
SPEC e corta por percentual com caracterização reforçada — a ausência é declarada, não
silenciosa.

## Consequências

| O que | Antes | Depois |
|---|---|---|
| "Quem importa este arquivo" | grep na `mapear-arquitetura` | `grafo.py contexto`, em 6 skills |
| Faixa 2 por "muitos chamadores" | impressão | contagem de importadores |
| Regressão em chamador fora do diff | invisível ao `/validar` | listada por arquivo |
| Pré-condição do `/migrar` | mapa + ADR | mapa + ADR + degrau declarado da escada |
| Corte de fatia | flag + métrica agregada | sombra com comparador → flag |
| Escrita do `grafo.py` | nenhuma | `codigo.jsonl` + `codigo.meta.json`, regeneráveis |

**Positivas**

- O caso em que grep é cego passa a ter instrumento, e o instrumento não passa pelo modelo.
- A faixa de raio de explosão e a validação ganham um dado que o agente não consegue
  inflar nem esconder.
- O `/migrar` deixa de depender só dos cenários que alguém lembrou de escrever.

**Negativas e limites, declarados**

- **Três linguagens.** Ruby, Rust, Java, C#, PHP, Elixir ficam de fora nesta versão; a
  `mapear-arquitetura` mantém o grep para elas. Adicionar linguagem é função nova no
  script, sem mudança de formato.
- **Resolução é heurística onde a linguagem permite.** Python com `sys.path` manipulado,
  JS com bundler que reescreve caminhos, Go com `replace` no `go.mod` — imports que não
  resolvem são contados como não resolvidos, e o número aparece. Instanciação em Python é
  "chamada de nome importado com inicial maiúscula": pega o caso comum, perde fábrica em
  minúscula.
- **Grafo de código não é grafo de chamadas.** Importar não é usar; a aresta diz que o
  acoplamento existe, não quanto. Para "quantos símbolos cruzam a fronteira" a
  `mapear-arquitetura` continua lendo.
- **A camada envelhece.** `codigo.meta.json` carrega a data e o `contexto` a mostra; o
  `/mapear-conhecimento atualizar` regenera junto. Camada de um mês atrás num repositório
  quente vale menos, e o leitor vê a data.
- **Sombra tem custo e pré-requisito.** Dobra o processamento da fatia durante o período,
  e exige que a rota nova possa rodar sem efeito colateral duplicado (dual-write com
  idempotência, ou leitura pura). É por isso que a ausência é declarada em vez de a sombra
  ser obrigatória.
- **A escada é declaração, não medição.** O `diagnostico.py` mede parte do degrau 1 e 2
  (build, lint, teste existem?); os degraus 3 a 5 são leitura do Rafael com evidência
  citada.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Servidor MCP com Neo4j, como o CodeCompass do paper | O plugin não roda serviço; um JSONL regenerável no repo e um subcomando dão a mesma vizinhança de 1 salto sem infraestrutura, e o arquivo é lido por qualquer CLI |
| Arestas de código dentro de `relacoes.jsonl` | O pipeline do modelo (`atualizar`) reescreve por documento e não saberia preservar o que não produziu; camada separada é regenerável sem tocar o curado |
| Grafo de chamadas (call graph) em vez de imports | Exige análise por linguagem muito mais cara e frágil; o paper mostra que imports + herança + instanciação já entregam o ganho no caso cego |
| Extração por modelo, como o resto do grafo | Import está no texto; não há julgamento. Passar pelo modelo custaria tokens para ficar menos preciso |
| Exigir sombra em toda fatia do `/migrar` | Fatia com efeito colateral não idempotente não tem sombra barata; obrigar produziria sombras falsas. Declarar a ausência é mais honesto |
| Pontuar a escada do legado no `/diagnosticar` | Os degraus 3 a 5 não são medidos por código; pontuar seria a confiança falsa que o ADR-0028 proíbe. Reportar o degrau com evidência citada é o que a escada de evidência permite |
