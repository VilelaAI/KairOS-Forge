// Funções puras do mod do painel do arco (ADR-0051): leem a saída do `painel.py` e
// dizem o que desenhar. Nenhuma regra da fábrica mora aqui — a coluna de cada
// requisito, a fase de cada ciclo e o que entra na caixa vêm prontos do Python, que é
// a fonte (painel.py: "se o número aqui está errado, o bug está na fonte").

import type {
  Caixa,
  CicloDoPainel,
  Ficha,
  ItemCaixa,
  Leitura,
  Painel,
  QuadroDoPainel,
  Relatorio,
  SpecDoPainel,
} from '../types'

type Bruto = Record<string, unknown>

const objeto = (x: unknown): Bruto =>
  x !== null && typeof x === 'object' && !Array.isArray(x) ? (x as Bruto) : {}
const texto = (x: unknown): string => (x == null ? '' : String(x))
const numero = (x: unknown): number => (Number.isFinite(x) ? (x as number) : 0)
const lista = (x: unknown): unknown[] => (Array.isArray(x) ? x : [])
const textos = (x: unknown): string[] => lista(x).map(texto)

export const FASES = ['especificar', 'construir', 'validar', 'revisar', 'pr'] as const
const ROTULO_DA_FASE: Record<string, string> = { pr: 'PR' }
export const GATES = ['criticar', 'validar', 'revisar'] as const
const RELATORIOS = [
  ['critica', 'Crítica'],
  ['validacao', 'Validação'],
  ['revisao', 'Revisão'],
] as const
export { RELATORIOS }

// Os mesmos ícones do painel.py (ICONE_ESTADO e ICONE_CAIXA), para o terminal e o mod
// falarem a mesma língua.
export const ICONE_CAIXA: Record<string, string> = {
  gate: '🚦',
  escalado: '🧯',
  spec_alterada: '✍️',
  bloqueada: '⛔',
  vencida: '⏰',
  falta_informacao: '❓',
  pr_da_fabrica: '🔀',
}

export function iconeDoEstado(estado: string): string {
  if (estado === 'escalado') return '⏸️'
  if (estado === 'encerrado') return '✅'
  if (estado === 'pronto_para_pr') return '🎯'
  return estado.startsWith('aguardando_') ? '🙋' : '🔁'
}

function relatorio(x: unknown): Relatorio | undefined {
  const r = objeto(x)
  if (!r.arquivo) return undefined
  const achados = numero(r.achados ?? r.bloqueios ?? r.criticos)
  return {
    arquivo: texto(r.arquivo),
    ...(r.erro ? { erro: texto(r.erro) } : { veredicto: texto(r.veredicto) }),
    achados,
  }
}

function spec(x: unknown): SpecDoPainel {
  const s = objeto(x)
  const col = objeto(s.colunas)
  const rel = objeto(s.relatorios)
  const relatorios: SpecDoPainel['relatorios'] = {}
  for (const [chave] of RELATORIOS) {
    const r = relatorio(rel[chave])
    if (r) relatorios[chave] = r
  }
  return {
    id: texto(s.id),
    progresso: numero(s.progresso),
    total: numero(s.total),
    colunas: {
      aFazer: textos(col['A fazer']),
      emProgresso: textos(col['Em progresso']),
      pronto: textos(col['Pronto']),
    },
    semProva: textos(s.sem_prova),
    p1Abertos: textos(s.p1_abertos),
    relatorios,
  }
}

function fichas(c: Bruto): Ficha[] {
  const orc = objeto(c.orcamento)
  const rod = objeto(c.rodadas)
  const tot = objeto(c.rodadas_totais)
  const teto = objeto(c.teto)
  return GATES.filter(g => typeof orc[g] === 'number').map(g => ({
    gate: g,
    rodadas: numero(rod[g]),
    orcamento: numero(orc[g]),
    ...(typeof tot[g] === 'number' && typeof teto[g] === 'number'
      ? { total: numero(tot[g]), teto: numero(teto[g]) }
      : {}),
  }))
}

function ciclo(x: unknown): CicloDoPainel {
  const c = objeto(x)
  return {
    spec: texto(c.spec) || '?',
    estado: texto(c.estado) || '?',
    fase: typeof c.fase === 'string' ? c.fase : null,
    fichas: fichas(c),
    motivo: c.motivo_escalacao ? texto(c.motivo_escalacao) : null,
  }
}

function quadro(x: unknown): QuadroDoPainel {
  const q = objeto(x)
  return {
    slug: texto(q.slug),
    spec: q.spec ? texto(q.spec) : null,
    total: numero(q.total),
    concluidas: numero(objeto(q.por_estado).concluida),
    onda: numero(q.onda),
    tetoOnda: numero(q.teto_onda),
    encerrado: q.encerrado === true,
    completo: q.completo === true,
    emVoo: textos(q.em_voo),
    bloqueadas: textos(q.bloqueadas),
    vencidas: textos(q.vencidas),
    lacunas: textos(q.lacunas),
  }
}

/** A saída do `painel.py --json`, só com o que o mod desenha. */
export function resumirPainel(bruto: unknown): Painel {
  const d = objeto(bruto)
  return {
    geradoEm: texto(d.gerado_em),
    specs: lista(d.specs).map(spec),
    ciclos: lista(d.ciclos).map(ciclo),
    quadros: lista(d.quadros).map(quadro),
  }
}

/** A saída do `painel.py --caixa --json`. */
export function resumirCaixa(bruto: unknown): Caixa {
  const d = objeto(bruto)
  const itens: ItemCaixa[] = lista(d.itens).map(x => {
    const i = objeto(x)
    return {
      tipo: texto(i.tipo),
      onde: texto(i.onde),
      o_que: texto(i.o_que),
      como: texto(i.como),
      ...(i.url ? { url: texto(i.url) } : {}),
    }
  })
  return { itens }
}

export type Parada = { nome: string; rotulo: string; marca: '✓' | '●' | '·' }

/** O trilho especificar → construir → validar → revisar → PR, com a fase marcada. */
export function trilho(fase: string | null): Parada[] {
  const aqui = fase === 'encerrado' ? FASES.length : FASES.indexOf(fase as (typeof FASES)[number])
  return FASES.map((nome, i) => ({
    nome,
    rotulo: ROTULO_DA_FASE[nome] ?? nome,
    marca: aqui < 0 ? '·' : i < aqui ? '✓' : i === aqui ? '●' : '·',
  }))
}

export function textoDaFicha(f: Ficha): string {
  const total = f.total !== undefined && f.teto !== undefined ? ` (tot ${f.total}/${f.teto})` : ''
  return `${f.gate} ${f.rodadas}/${f.orcamento}${total}`
}

export function barra(pct: number, largura = 16): string {
  const cheio = Math.max(0, Math.min(largura, Math.round((pct / 100) * largura)))
  return '█'.repeat(cheio) + '░'.repeat(largura - cheio)
}

export const ativo = (c: CicloDoPainel): boolean => c.estado !== 'encerrado'

/** A linha de status da fábrica, ou undefined quando não há o que dizer. */
export function linhaDeStatus(painel: Painel | null, caixa: Caixa | null): string | undefined {
  const ciclos = (painel?.ciclos ?? []).filter(ativo)
  const n = caixa?.itens.length ?? 0
  const partes: string[] = []
  const primeiro = ciclos[0]
  if (primeiro) {
    partes.push(`${primeiro.spec} ${primeiro.estado}` + (ciclos.length > 1 ? ` +${ciclos.length - 1}` : ''))
  }
  if (n) partes.push(`📥 ${n}`)
  return partes.length ? `kairos-forge · ${partes.join(' · ')}` : undefined
}

/** O que identifica a caixa: muda quando entra ou sai um item. */
export function assinaturaDaCaixa(caixa: Caixa | null): string {
  return (caixa?.itens ?? []).map(i => `${i.tipo}|${i.onde}|${i.o_que}`).join('\n')
}

/** Os gates humanos da caixa, um por ciclo e gate. */
export function gatesDaCaixa(caixa: Caixa | null): string[] {
  return (caixa?.itens ?? []).filter(i => i.tipo === 'gate').map(i => `${i.onde}|${i.o_que}`)
}

/** Explica numa linha por que a leitura não veio. */
export function explicarFalha(erro: unknown): string {
  const msg = erro instanceof Error ? erro.message : texto(erro)
  return /ENOENT|not found|cannot start|spawn/i.test(msg)
    ? 'não deu para rodar o `python3`: o painel lê `scripts/painel.py` do plugin e precisa do Python 3 no PATH'
    : `a leitura do painel falhou: ${msg.split('\n')[0] ?? ''}`
}

export type Faixa = { icone: string; onde: string; oQue: string; mais: string; assinatura: string }

/**
 * O que a faixa acima do prompt mostra, ou null para ela ficar com quem vem embaixo:
 * caixa vazia, leitura com falha (a caixa pode estar velha) ou faixa ocultada para esta
 * mesma caixa.
 */
export function conteudoDaFaixa(l: Leitura, ocultaPara: string | null): Faixa | null {
  const itens = l.caixa?.itens ?? []
  const assinatura = assinaturaDaCaixa(l.caixa)
  const [primeiro] = itens
  if (!primeiro || l.falha || ocultaPara === assinatura) return null
  return {
    icone: ICONE_CAIXA[primeiro.tipo] ?? '·',
    onde: primeiro.onde,
    oQue: primeiro.o_que,
    mais: itens.length > 1 ? ` (+${itens.length - 1})` : '',
    assinatura,
  }
}

export const painelVazio = (p: Painel): boolean => !p.specs.length && !p.ciclos.length && !p.quadros.length

/** Os ciclos cuja SPEC não está em docs/specs/: aparecem mesmo assim. */
export function ciclosSemSpec(p: Painel | null): CicloDoPainel[] {
  return (p?.ciclos ?? []).filter(c => !p?.specs.some(s => s.id === c.spec))
}

export function linhasDoQuadro(q: QuadroDoPainel): string[] {
  const linhas: string[] = []
  if (q.emVoo.length) linhas.push(`em voo: ${q.emVoo.join(', ')}`)
  if (q.bloqueadas.length) linhas.push(`bloqueadas: ${q.bloqueadas.join(', ')}`)
  if (q.vencidas.length) linhas.push(`⏱️ vencidas: ${q.vencidas.join(', ')}`)
  return linhas
}

/** `--github` só quando a pessoa pediu; o resto dos argumentos não passa ao script. */
export const pedeGithub = (args: string | undefined): string[] =>
  (args ?? '').split(/\s+/).includes('--github') ? ['--github'] : []
