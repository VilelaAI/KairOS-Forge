// Testes do mod do painel do arco (ADR-0051). Rode: claude plugin test .
//
// Os ganchos registrados com `on` aqui ficam embaixo do mod e fazem o papel do motor:
// o `$.process.run` responde com a saída do `painel.py` que um projeto de verdade deu
// (SPEC-007 em correção da validação, SPEC-008 parada no gate 1/3, um quadro com uma
// tarefa bloqueada), e o resto responde o mínimo.
import { expect, test } from 'claude-code/testing'

const PAINEL = {
  gerado_em: '2026-11-05T14:48:00+00:00',
  janela_dias: 14,
  specs: [
    {
      id: 'SPEC-007',
      total: 4,
      progresso: 50,
      p1_abertos: ['EX-02'],
      sem_prova: ['EX-03'],
      colunas: { 'A fazer': ['EX-04'], 'Em progresso': ['EX-02', 'EX-03'], Pronto: ['EX-01'] },
      relatorios: {
        validacao: { arquivo: 'VALIDACAO-SPEC-007-2026-11-05.md', veredicto: 'bloqueado', bloqueios: 2 },
      },
    },
  ],
  ciclos: [
    {
      spec: 'SPEC-007',
      estado: 'corrigindo_validacao',
      fase: 'validar',
      orcamento: { criticar: 2, validar: 2, revisar: 2 },
      rodadas: { criticar: 0, validar: 1, revisar: 0 },
      rodadas_totais: { criticar: 0, validar: 1, revisar: 0 },
      teto: { criticar: 6, validar: 6, revisar: 6 },
    },
    { spec: 'SPEC-008', estado: 'aguardando_entendimento', fase: 'especificar', orcamento: {}, rodadas: {} },
  ],
  quadros: [
    {
      slug: 'forge-007',
      spec: 'SPEC-007',
      total: 3,
      por_estado: { concluida: 1, em_progresso: 1, bloqueada: 1 },
      onda: 1,
      teto_onda: 6,
      encerrado: false,
      completo: false,
      em_voo: ['T1'],
      prontas: [],
      bloqueadas: ['T2'],
      vencidas: [],
      lacunas: [],
    },
  ],
  telemetria: {},
}

const GATE = {
  tipo: 'gate',
  onde: 'SPEC-008',
  o_que: 'gate 1/3 — confirmar o entendimento',
  como: 'responda e registre: ciclo.py registrar <resultado> SPEC-008',
}
const BLOQUEADA = {
  tipo: 'bloqueada',
  onde: 'forge-007',
  o_que: 'tarefa T2 bloqueada',
  como: 'resolva o bloqueio com a Laura; ela reabre com quadro.py reabrir',
}
const CAIXA = { itens: [GATE, BLOQUEADA], github: { estado: 'nao_consultado' } }
const VAZIA = { itens: [], github: { estado: 'nao_consultado' } }

const PANE = {
  plugin: 'kairos-forge',
  component: 'Pane',
  requestId: 'kairos-forge-arco',
  props: {
    title: 'Arco da fábrica',
    isFocused: false,
    bodyColumns: 60,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
} as const

const FAIXA = {
  plugin: 'kairos-forge',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isWorking: false,
    maxRows: 10,
    bodyColumns: 80,
    scroll: { offset: 0, bodyRows: 9 },
    view: {},
  },
} as const

type Motor = {
  painel?: unknown
  caixa?: unknown
  semPython?: boolean
  scriptFalha?: boolean
  placed?: boolean
}

type Registro = {
  argv: string[][]
  toasts: string[]
  status: (string | undefined)[]
  comandos: { name: string; immediate?: true }[]
}

// O motor embaixo do mod. Devolve o que ele viu: os argv rodados, os toasts e as
// linhas de status.
function motor(on: Parameters<Parameters<typeof test>[1]>[1], m: Motor = {}): Registro {
  const visto: Registro = { argv: [], toasts: [], status: [], comandos: [] }
  on('session.root', () => ({ value: '/projeto' }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('command.register', (_, e) => (visto.comandos.push(e), { value: { command: e.name } }))
  on('ui.open', () => ({ value: m.placed === false ? { isPlaced: false, reason: 'sem superfície' } : { isPlaced: true } }))
  on('ui.toast', (_, e) => (visto.toasts.push(e.text), { value: undefined }))
  on('ui.status', (_, e) => (visto.status.push(e.text), { value: undefined }))
  on('ui.log', () => ({ value: undefined }))
  // Devolve o que recebeu: uma chamada reescrita no caminho aparece aqui.
  on('tool.call', (_, e) => ({ result: { text: `feito: ${String(e.command ?? e.file_path)}` } }))
  on('process.run', (_, e) => {
    visto.argv.push([...e.argv])
    if (m.semPython) return { deny: 'spawn python3 ENOENT' }
    if (m.scriptFalha) {
      const stderr = 'Traceback (most recent call last):\nValueError: SPEC ilegível\n'
      return { value: { exitCode: 2, stdout: '', stderr, isStdoutTruncated: false, isStderrTruncated: false } }
    }
    const json = e.argv.includes('--json')
    const caixa = e.argv.includes('--caixa')
    const stdout = !json
      ? caixa
        ? '📥 Caixa de entrada — 2 item(ns) esperando uma pessoa'
        : '📋 Quadro da fábrica'
      : JSON.stringify(caixa ? (m.caixa ?? CAIXA) : (m.painel ?? PAINEL))
    return {
      value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
    }
  })
  return visto
}

const SUPERFICIES = ['terminal', 'desktop', 'vscode', 'mobile'] as const

test('o painel desenha o arco em toda superfície', async ($, on) => {
  const visto = motor(on)
  await $.session.start({ cwd: '/projeto', surface: 'desktop', isInteractive: true })
  const r = await $.command.run({ command: 'forge-painel' })
  expect(r.text).toBe('Painel do arco aberto ao lado da conversa.')
  // Os dois comandos rodam na hora, até com um turno em curso.
  expect(visto.comandos.map(c => [c.name, c.immediate])).toEqual([
    ['forge-painel', true],
    ['forge-caixa', true],
  ])

  // O python3 roda o painel.py do plugin, no projeto da sessão, só para ler.
  const rodados = visto.argv.map(a => a.slice(2).join(' '))
  expect(rodados).toContain('--json')
  expect(rodados).toContain('--caixa --json')
  expect(visto.argv.every(a => a[0] === 'python3' && a[1]!.endsWith('/scripts/painel.py'))).toBe(true)
  expect(rodados.some(a => a.includes('--html'))).toBe(false)

  for (const surface of SUPERFICIES) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect(await ui.find({ type: 'Text', text: /SPEC-007/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /50%/ })).toBeDefined()
    // O trilho com a fase marcada: especificar e construir feitos, validar em curso.
    const marcada = await ui.findAll({ type: 'Text', text: /^● validar/ })
    expect(marcada.length).toBe(1)
    expect(marcada[0]?.props.bold).toBe(true)
    expect((await ui.find({ type: 'Text', text: /^· revisar/ }))?.props.dimColor).toBe(true)
    expect((await ui.find({ type: 'Text', text: /^✓ especificar/ }))?.text).toBe(
      '✓ especificar  ✓ construir  ● validar  · revisar  · PR  ',
    )
    expect((await ui.find({ type: 'Text', text: /^● especificar/ }))?.text).toBe(
      '● especificar  · construir  · validar  · revisar  · PR  ',
    )
    expect(await ui.find({ type: 'Text', text: /SPEC-007 ████████░░░░░░░░ 50%/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /✓ construir/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /validar 1\/2 \(tot 1\/6\)/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /❌ Validação: bloqueado/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /concluído sem `verificado:` → EX-03/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Caixa — 2 esperando você/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /bloqueadas: T2/ })).toBeDefined()
    // O ciclo sem SPEC no disco aparece mesmo assim.
    expect(await ui.find({ type: 'Text', text: /sem SPEC no disco/ })).toBeDefined()
    await ui.unmount()
  }
})

test('a faixa mostra o que espera, e some ao ocultar até a caixa mudar', async ($, on) => {
  motor(on)
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>motor</Text>
  })
  await $.session.start({ cwd: '/projeto', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'forge-painel' })

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...FAIXA, surface })
    const linha = await ui.find({ type: 'Text', text: /SPEC-008: gate 1\/3/ })
    expect(linha?.text).toContain('(+1)')
    expect(await ui.find({ type: 'Button', key: 'forge-ver' })).toBeDefined()
    await ui.unmount()
  }

  const oculta = await $.ui.mount({ ...FAIXA, surface: 'terminal' })
  await oculta.press({ key: 'forge-ocultar' })
  await oculta.unmount()
  const depois = await $.ui.mount({ ...FAIXA, surface: 'terminal' })
  expect((await depois.find({ type: 'Text' }))?.text).toBe('motor')
  await depois.unmount()
})

test('caixa vazia não ocupa a faixa', async ($, on) => {
  motor(on, { caixa: VAZIA })
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>motor</Text>
  })
  await $.session.start({ cwd: '/projeto', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'forge-painel' })
  const ui = await $.ui.mount({ ...FAIXA, surface: 'desktop' })
  expect((await ui.find({ type: 'Text' }))?.text).toBe('motor')
  await ui.unmount()
})

test('o gate humano avisa uma vez, e a linha de status diz o arco', async ($, on) => {
  const visto = motor(on)
  await $.session.start({ cwd: '/projeto', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'forge-painel' })
  await $.command.run({ command: 'forge-painel' })
  expect(visto.toasts.length).toBe(1)
  expect(visto.toasts[0]).toBe('🚦 SPEC-008 espera você: gate 1/3 — confirmar o entendimento')
  expect(visto.status.at(-1)).toBe('kairos-forge · SPEC-007 corrigindo_validacao +1 · 📥 2')
})

test('/forge-caixa responde na hora, com --github só quando pedido', async ($, on) => {
  const visto = motor(on)
  await $.session.start({ cwd: '/projeto', surface: 'terminal', isInteractive: true })
  const sem = await $.command.run({ command: 'forge-caixa' })
  expect(sem.text).toContain('Caixa de entrada')
  expect(visto.argv.some(a => a.includes('--caixa') && !a.includes('--json') && a.includes('--github'))).toBe(false)
  await $.command.run({ command: 'forge-caixa', args: '--github' })
  expect(visto.argv.some(a => a.slice(2).join(' ') === '--caixa --github')).toBe(true)
})

test('sem superfície que desenhe, /forge-painel devolve o quadro como texto', async ($, on) => {
  motor(on, { placed: false })
  await $.session.start({ cwd: '/projeto', surface: null, isInteractive: false })
  const r = await $.command.run({ command: 'forge-painel' })
  expect(r.text).toBe('📋 Quadro da fábrica')
})

test('sem python3, o painel diz o porquê e a faixa e o status se calam', async ($, on) => {
  const visto = motor(on, { semPython: true })
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>motor</Text>
  })
  await $.session.start({ cwd: '/projeto', surface: 'desktop', isInteractive: true })
  const r = await $.command.run({ command: 'forge-caixa' })
  expect(r.text).toContain('Python 3')

  const pane = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await pane.find({ type: 'Text', text: /precisa do Python 3/ })).toBeDefined()
  await pane.unmount()
  const faixa = await $.ui.mount({ ...FAIXA, surface: 'desktop' })
  expect((await faixa.find({ type: 'Text' }))?.text).toBe('motor')
  await faixa.unmount()
  expect(visto.status.every(s => s === undefined)).toBe(true)
  expect(visto.toasts.length).toBe(0)
})

test('o python3 some no meio: a última leitura fica, com a falha em cima, e o status se cala', async ($, on) => {
  const m: Motor = {}
  const visto = motor(on, m)
  on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>motor</Text>
  })
  await $.session.start({ cwd: '/projeto', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'forge-painel' })
  expect(visto.status.at(-1)).toContain('SPEC-007')

  m.semPython = true
  await $.command.run({ command: 'forge-painel' })
  expect(visto.status.at(-1)).toBeUndefined()
  const pane = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await pane.find({ type: 'Text', text: /precisa do Python 3/ })).toBeDefined()
  expect(await pane.find({ type: 'Text', text: /SPEC-007/ })).toBeDefined()
  await pane.unmount()
  // A faixa não chama a pessoa com uma caixa que pode estar velha.
  const faixa = await $.ui.mount({ ...FAIXA, surface: 'terminal' })
  expect((await faixa.find({ type: 'Text' }))?.text).toBe('motor')
  await faixa.unmount()
})

test('a chamada de ferramenta passa inteira; só a que mexe no arco pede leitura', async ($, on) => {
  const visto = motor(on)
  await $.session.start({ cwd: '/projeto', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'forge-painel' })
  const leituras = () => visto.argv.filter(a => a.includes('--json') && !a.includes('--caixa')).length

  // O /forge-painel faz uma leitura e espera a que estiver em voo: depois de uma
  // chamada que não mexe no arco ele soma uma; depois de uma que mexe, duas.
  let antes = leituras()
  const outra = await $.tool.call({ tool: 'Bash', command: 'npm test' })
  expect(outra.result).toEqual({ text: 'feito: npm test' })
  expect(outra.deny).toBeUndefined()
  await $.command.run({ command: 'forge-painel' })
  expect(leituras()).toBe(antes + 1)

  antes = leituras()
  const doArco = await $.tool.call({ tool: 'Bash', command: 'python3 scripts/ciclo.py registrar pronto SPEC-007' })
  expect(doArco.result).toEqual({ text: 'feito: python3 scripts/ciclo.py registrar pronto SPEC-007' })
  expect(doArco.deny).toBeUndefined()
  await $.command.run({ command: 'forge-painel' })
  expect(leituras()).toBe(antes + 2)

  antes = leituras()
  await $.tool.call({ tool: 'Write', file_path: '/projeto/src/app.ts', content: 'x' })
  await $.command.run({ command: 'forge-painel' })
  expect(leituras()).toBe(antes + 1)

  antes = leituras()
  const escrita = await $.tool.call({ tool: 'Write', file_path: '/projeto/docs/specs/SPEC-007-exportar.md', content: 'x' })
  expect(escrita.result).toEqual({ text: 'feito: /projeto/docs/specs/SPEC-007-exportar.md' })
  await $.command.run({ command: 'forge-painel' })
  expect(leituras()).toBe(antes + 2)
})

const PAINEL_PARADO = {
  gerado_em: '2026-11-05T15:10:00+00:00',
  specs: [],
  ciclos: [
    {
      spec: 'SPEC-009',
      estado: 'escalado',
      fase: 'validar',
      motivo_escalacao: 'orçamento de validar esgotado',
      orcamento: { validar: 2 },
      rodadas: { validar: 2 },
      rodadas_totais: { validar: 2 },
    },
    { spec: 'SPEC-010', estado: 'encerrado', fase: 'encerrado', orcamento: {}, rodadas: {} },
  ],
  quadros: [
    { ...PAINEL.quadros[0], slug: 'forge-010', spec: null, completo: true, em_voo: [], bloqueadas: [] },
    { ...PAINEL.quadros[0], slug: 'forge-009', encerrado: true, completo: true, em_voo: [], bloqueadas: [] },
  ],
  telemetria: {},
}
const SO_ESCALADO = {
  itens: [{ tipo: 'escalado', onde: 'SPEC-009', o_que: 'orçamento de validar esgotado', como: 'decida' }],
}

test('o ciclo escalado, o encerrado e o quadro completo', async ($, on) => {
  const visto = motor(on, { painel: PAINEL_PARADO, caixa: SO_ESCALADO })
  await $.session.start({ cwd: '/projeto', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'forge-painel' })

  // Só o escalado conta como ativo; sem "+0" quando é um só.
  expect(visto.status.at(-1)).toBe('kairos-forge · SPEC-009 escalado · 📥 1')
  expect(visto.toasts.length).toBe(0)

  const pane = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await pane.find({ type: 'Text', text: /^⏸️ escalado/ })).toBeDefined()
  expect((await pane.find({ type: 'Text', text: /^⏸️ orçamento/ }))?.props.color).toBe('warning')
  expect((await pane.find({ type: 'Text', text: /^ · validar/ }))?.text).toBe(' · validar 2/2')
  expect(await pane.find({ type: 'Text', text: /^✅ encerrado/ })).toBeDefined()
  // O escalado fica na fase de onde parou; o encerrado tem o trilho todo feito.
  expect((await pane.findAll({ type: 'Text', text: /^✓ especificar.* PR/ })).map(x => x.text)).toEqual([
    '✓ especificar  ✓ construir  ● validar  · revisar  · PR  ',
    '✓ especificar  ✓ construir  ✓ validar  ✓ revisar  ✓ PR  ',
  ])
  expect(await pane.find({ type: 'Text', text: /^🔄 forge-010/ })).toBeDefined()
  expect(await pane.find({ type: 'Text', text: /^🏁 forge-009/ })).toBeDefined()
  expect((await pane.findAll({ type: 'Text', text: /completo — falta encerrar/ })).length).toBe(1)
  expect(await pane.find({ type: 'Text', text: /Nada para mostrar/ })).toBeUndefined()
  await pane.unmount()

  const faixa = await $.ui.mount({ ...FAIXA, surface: 'terminal' })
  expect((await faixa.find({ type: 'Text', text: /SPEC-009/ }))?.text).toBe(
    '📥 🧯 SPEC-009: orçamento de validar esgotado',
  )
  await faixa.unmount()
})

test('pronto para PR tem o seu ícone', async ($, on) => {
  const pronto = { ...PAINEL_PARADO, ciclos: [{ spec: 'SPEC-011', estado: 'pronto_para_pr', fase: 'pr' }] }
  motor(on, { painel: pronto, caixa: { itens: [] } })
  await $.session.start({ cwd: '/projeto', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'forge-painel' })
  const pane = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await pane.find({ type: 'Text', text: /^🎯 pronto_para_pr/ })).toBeDefined()
  expect(await pane.find({ type: 'Text', text: /Nada esperando por você/ })).toBeDefined()
  await pane.unmount()
})

test('painel vazio diz por onde começar; meio vazio não', async ($, on) => {
  const m: Motor = { painel: { gerado_em: '', specs: [], ciclos: [], quadros: [] }, caixa: { itens: [] } }
  motor(on, m)
  const antes = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await antes.find({ type: 'Text', text: /Lendo o painel/ })).toBeDefined()
  await antes.unmount()

  await $.session.start({ cwd: '/projeto', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'forge-painel' })
  const vazio = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await vazio.find({ type: 'Text', text: /Nada para mostrar/ })).toBeDefined()
  expect(await vazio.find({ type: 'Text', text: /Lendo o painel/ })).toBeUndefined()
  await vazio.unmount()

  for (const painel of [{ ...PAINEL, quadros: [] }, { ...PAINEL_PARADO, ciclos: [] }]) {
    m.painel = painel
    await $.command.run({ command: 'forge-painel' })
    const meio = await $.ui.mount({ ...PANE, surface: 'desktop' })
    expect(await meio.find({ type: 'Text', text: /Nada para mostrar/ })).toBeUndefined()
    await meio.unmount()
  }
})

test('o script que falha: o comando mostra o erro, e o painel diz o código e a última linha', async ($, on) => {
  motor(on, { scriptFalha: true })
  await $.session.start({ cwd: '/projeto', surface: 'desktop', isInteractive: true })
  const r = await $.command.run({ command: 'forge-caixa' })
  expect(r.text).toBe('Traceback (most recent call last):\nValueError: SPEC ilegível')
  const pane = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await pane.find({ type: 'Text', text: /saiu com código/ }))?.text).toBe(
    '⚠️ a leitura do painel falhou: painel.py --json saiu com código 2: ValueError: SPEC ilegível',
  )
  await pane.unmount()
})

test('o gate que sai e volta avisa de novo', async ($, on) => {
  const m: Motor = {}
  const visto = motor(on, m)
  await $.session.start({ cwd: '/projeto', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'forge-painel' })
  expect(visto.toasts.length).toBe(1)
  m.caixa = { itens: [BLOQUEADA] }
  await $.command.run({ command: 'forge-painel' })
  expect(visto.toasts.length).toBe(1)
  m.caixa = CAIXA
  await $.command.run({ command: 'forge-painel' })
  expect(visto.toasts.length).toBe(2)
})
