// Testes do segredo ocultado na saída de ferramenta (ADR-0056). Rode: claude plugin test .
//
// Embaixo do mod, o motor: o `tool.call` do teste faz o papel da ferramenta (e do que o
// Claude Code põe no resultado), o `fs.read` o do arquivo onde a saída grande fica
// guardada, e o `$.process.run` o do `guardrail.py saida`, que acha e oculta o segredo.
// A regra em si (os formatos) é testada em Python (scripts/tests/test_segredo.py).
import { expect, test } from 'claude-code/testing'

const TOKEN = `ghp_${'a'.repeat(36)}`
const MARCA = '«segredo ocultado pelo kairos-forge: token GitHub»'
const AVISO = '🔒 kairos-forge: a saída de `Bash` tinha 1 segredo(s)'

type Motor = {
  resposta?: Record<string, unknown>
  guardada?: string
  semArquivo?: boolean
  semPython?: boolean
  saidaIlegivel?: boolean
  ocultar?: boolean
}

type Visto = {
  exames: { argv: string[]; payload: Record<string, unknown>; sessao?: string }[]
  lidos: string[]
  rodadas: number
}

const RODOU = { exitCode: 0, stderr: '', isStdoutTruncated: false, isStderrTruncated: false }

function motor(on: Parameters<Parameters<typeof test>[1]>[1], m: Motor = {}): Visto {
  const visto: Visto = { exames: [], lidos: [], rodadas: 0 }
  on('session.cwd', () => ({ value: '/projeto' }))
  on('session.id', () => ({ value: 'sessao-1' }))
  on('tool.call', () => (visto.rodadas++, m.resposta ?? {
    result: { stdout: `GITHUB_TOKEN=${TOKEN}\nfim`, stderr: '', interrupted: false }, ref: 7,
    text: `GITHUB_TOKEN=${TOKEN}\nfim` }))
  on('fs.read', (_, e) => (visto.lidos.push(e.path),
    m.semArquivo ? { deny: 'ENOENT: no such file or directory' } : { value: m.guardada ?? '' }))
  on('process.run', (_, e) => {
    // A pausa da faixa 3 também pergunta ao guardrail no Bash: aqui ela nunca para.
    if (e.argv[2] === 'faixa3') return { value: { ...RODOU, stdout: '{"pausa": false}' } }
    if (m.semPython) return { deny: 'spawn python3 ENOENT' }
    const payload = JSON.parse(e.init?.stdin ?? '{}') as { textos: Record<string, string> }
    visto.exames.push({ argv: [...e.argv], payload, sessao: e.init?.env?.CLAUDE_SESSION_ID })
    const textos = Object.fromEntries(Object.entries(payload.textos).map(([k, v]) => [k, v.split(TOKEN).join(MARCA)]))
    const achados = Object.values(payload.textos).filter(v => v.includes(TOKEN)).length
    const ocultar = m.ocultar ?? true
    const stdout = m.saidaIlegivel ? '' : JSON.stringify(achados
      ? { achados, ocultar, textos: ocultar ? textos : payload.textos, aviso: `${AVISO} — token GitHub (1)` }
      : { achados: 0 })
    return { value: { ...RODOU, stdout } }
  })
  return visto
}

const ENV = { tool: 'Bash', command: 'env' } as const

test('o Bash que respondeu volta com o segredo trocado pela marca, e o aviso junto', async ($, on) => {
  const visto = motor(on)
  const r = await $.tool.call(ENV)
  expect(r.result).toEqual({ stdout: `GITHUB_TOKEN=${MARCA}\nfim`, stderr: '', interrupted: false })
  // Objeto novo: com o `ref` ou o `text` de antes, o Claude Code reaproveitaria o original.
  expect(r.ref).toBeUndefined()
  expect(r.text).toBeUndefined()
  expect(r.context?.at(-1)?.startsWith(AVISO)).toBe(true)
  const [exame] = visto.exames
  expect(exame?.argv[0]).toBe('python3')
  expect(exame?.argv[1]?.endsWith('/scripts/guardrail.py')).toBe(true)
  expect(exame?.argv[2]).toBe('saida')
  expect(exame?.payload).toEqual({ cwd: '/projeto', tool_name: 'Bash', tool_input: { command: 'env' },
                                    textos: { stdout: `GITHUB_TOKEN=${TOKEN}\nfim`, stderr: '' } })
  expect(exame?.sessao).toBe('sessao-1')
})

test('a saída grande é lida inteira do arquivo e volta inteira, sem o caminho dele', async ($, on) => {
  const inteira = `${'log comum\n'.repeat(3)}GITHUB_TOKEN=${TOKEN}\n`
  const visto = motor(on, {
    guardada: inteira,
    resposta: { result: { stdout: 'log comum\n', stderr: '', interrupted: false,
                          persistedOutputPath: '/cfg/tool-results/x.txt', rawOutputPath: '/cfg/raw.txt' } },
  })
  const r = await $.tool.call(ENV)
  expect(visto.lidos).toEqual(['/cfg/tool-results/x.txt'])
  expect(visto.exames[0]?.payload.textos).toEqual({ stdout: inteira, stderr: '' })
  expect(r.result).toEqual({ stdout: inteira.split(TOKEN).join(MARCA), stderr: '', interrupted: false })
})

test('o erro e a ferramenta de MCP voltam como resultado retido, já sem o segredo', async ($, on) => {
  motor(on, { resposta: { isError: true, result: 'falhou', text: `Exit code 1\nDB=${TOKEN}` } })
  const erro = await $.tool.call(ENV)
  expect(erro.deny?.startsWith(`Exit code 1\nDB=${MARCA}\n\n${AVISO}`)).toBe(true)
  expect(erro.deny?.includes(TOKEN)).toBe(false)
})

test('a ferramenta de MCP também passa pelo exame', async ($, on) => {
  const visto = motor(on, { resposta: { result: [{ type: 'text', text: `chave ${TOKEN}` }], text: `chave ${TOKEN}` } })
  const r = await $.tool.call({ tool: 'mcp__vault__ler_segredo', path: 'app' })
  expect(visto.exames[0]?.payload.textos).toEqual({ texto: `chave ${TOKEN}` })
  expect(visto.exames[0]?.payload.tool_input).toEqual({})
  expect(r.deny?.startsWith(`chave ${MARCA}`)).toBe(true)
})

test('saída vazia nem chega ao guardrail', async ($, on) => {
  const visto = motor(on, { resposta: { result: { stdout: '', stderr: '', interrupted: false } } })
  await $.tool.call(ENV)
  expect(visto.exames.length).toBe(0)
})

test('o arquivo da saída grande que sumiu deixa a saída passar como veio', async ($, on) => {
  const visto = motor(on, { semArquivo: true, resposta: { result: { stdout: 'começo', stderr: '', interrupted: false,
                                                                    persistedOutputPath: '/cfg/sumiu.txt' } } })
  const r = await $.tool.call(ENV)
  expect(visto.exames.length).toBe(0)
  expect(r.result).toEqual({ stdout: 'começo', stderr: '', interrupted: false, persistedOutputPath: '/cfg/sumiu.txt' })
})

test('sem segredo, o resultado volta como veio', async ($, on) => {
  motor(on, { resposta: { result: { stdout: 'tudo certo', stderr: '', interrupted: false }, ref: 3, text: 'tudo certo' } })
  const r = await $.tool.call(ENV)
  expect(r.result).toEqual({ stdout: 'tudo certo', stderr: '', interrupted: false })
  expect(r.ref).toBe(3)
  expect(r.context).toBeUndefined()
})

test('no modo aviso, o segredo fica e o aviso vai junto', async ($, on) => {
  motor(on, { ocultar: false })
  const r = await $.tool.call(ENV)
  expect(r.result).toEqual({ stdout: `GITHUB_TOKEN=${TOKEN}\nfim`, stderr: '', interrupted: false })
  expect(r.ref).toBe(7)
  expect(r.context?.at(-1)?.startsWith(AVISO)).toBe(true)
})

for (const [nome, m] of [['sem Python', { semPython: true }], ['com resposta ilegível', { saidaIlegivel: true }]] as const) {
  test(`${nome}, a saída passa como veio, e a chamada roda uma vez`, async ($, on) => {
    const visto = motor(on, m)
    const r = await $.tool.call(ENV)
    expect(r.result).toEqual({ stdout: `GITHUB_TOKEN=${TOKEN}\nfim`, stderr: '', interrupted: false })
    expect(visto.rodadas).toBe(1)
  })
}

test('a chamada recusada embaixo não é examinada, e a Read nem chega ao mod', async ($, on) => {
  const visto = motor(on, { resposta: { deny: 'recusado pelo modo' } })
  const r = await $.tool.call(ENV)
  expect(r.deny).toBe('recusado pelo modo')
  const lida = await $.tool.call({ tool: 'Read', file_path: '/projeto/a.txt' })
  expect(lida.deny).toBe('recusado pelo modo')
  expect(visto.exames.length).toBe(0)
})
