// Contrato do estado do mod do painel do arco (ADR-0051).
//
// O mod só desenha: os números saem do `scripts/painel.py --json` e do
// `painel.py --caixa --json`, e o que fica guardado aqui é a última leitura deles,
// para o desenho não rodar Python a cada quadro. Nada aqui é estado da fábrica: o
// estado do arco continua em `.agents/ciclo/` e `.agents/quadro/`, que o mod nunca
// escreve.

export type ItemCaixa = {
  tipo: string
  onde: string
  o_que: string
  como: string
  url?: string
}

export type Caixa = {
  itens: ItemCaixa[]
}

export type Relatorio = {
  arquivo: string
  veredicto?: string
  erro?: string
  achados: number
}

export type SpecDoPainel = {
  id: string
  progresso: number
  total: number
  colunas: { aFazer: string[]; emProgresso: string[]; pronto: string[] }
  semProva: string[]
  p1Abertos: string[]
  relatorios: { critica?: Relatorio; validacao?: Relatorio; revisao?: Relatorio }
}

// `totais`: as rodadas de todas as voltas e o teto absoluto, quando o ciclo registra os dois.
export type Ficha = { gate: string; rodadas: number; orcamento: number; totais?: { feitas: number; teto: number } }

export type CicloDoPainel = {
  spec: string
  estado: string
  fase: string | null
  fichas: Ficha[]
  motivo: string | null
}

export type QuadroDoPainel = {
  slug: string
  spec: string | null
  total: number
  concluidas: number
  onda: number
  tetoOnda: number
  encerrado: boolean
  completo: boolean
  emVoo: string[]
  bloqueadas: string[]
  vencidas: string[]
  lacunas: string[]
}

export type Painel = {
  geradoEm: string
  specs: SpecDoPainel[]
  ciclos: CicloDoPainel[]
  quadros: QuadroDoPainel[]
}

export type Leitura = {
  painel: Painel | null
  caixa: Caixa | null
  falha: string | null
}

declare module 'claude-code' {
  interface PluginState {
    'kairos-forge': {
      leitura: Shaped<Leitura>
      // A assinatura da caixa quando a pessoa ocultou a faixa: a faixa volta quando
      // a caixa muda, nunca antes.
      faixaOculta: string | null
      // Os gates humanos já avisados por toast, para não avisar de novo o mesmo.
      avisados: Shaped<string[]>
    }
  }
}
