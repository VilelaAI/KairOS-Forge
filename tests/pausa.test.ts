// Testes da pausa da faixa 3 na execução (ADR-0052). Rode: claude plugin test .
//
// Embaixo do mod, o motor: o `tool.check` responde a decisão do modo (o que a sessão
// faria sem o mod) e o `$.process.run` faz o papel do `guardrail.py faixa3`, que diz se
// a chamada para. A regra em si é testada em Python (scripts/tests/test_faixa3.py).
import { expect, test } from 'claude-code/testing'

const RAZAO = '⏸️ kairos-forge, pausa da faixa 3: esta chamada aplica ou destrói infraestrutura'

type Motor = {
  decisao?: 'allow' | 'ask' | 'deny'
  semPython?: boolean
  saidaIlegivel?: boolean
  saida?: unknown
}

type Visto = {
  classificados: { argv: string[]; payload: Record<string, unknown>; sessao?: string }[]
  executados: string[]
}

function motor(on: Parameters<Parameters<typeof test>[1]>[1], m: Motor = {}): Visto {
  const visto: Visto = { classificados: [], executados: [] }
  on('session.cwd', () => ({ value: '/projeto' }))
  on('session.id', () => ({ value: 'sessao-1' }))
  on('tool.check', () => ({ decision: m.decisao ?? 'allow', reason: 'decisão do modo' }))
  on('tool.call', (_, e) => (visto.executados.push(String(e.command ?? e.tool)), { result: { text: 'rodou' } }))
  on('process.run', (_, e) => {
    if (m.semPython) return { deny: 'spawn python3 ENOENT' }
    const payload = JSON.parse(e.init?.stdin ?? '{}') as Record<string, unknown>
    visto.classificados.push({ argv: [...e.argv], payload, sessao: e.init?.env?.CLAUDE_SESSION_ID })
    const comando = String((payload.tool_input as { command?: string } | undefined)?.command ?? '')
    const pausa = /terraform apply/.test(comando) || String(payload.tool_name).includes('merge')
    const stdout = m.saidaIlegivel
      ? ''
      : JSON.stringify('saida' in m ? m.saida : pausa ? { pausa: true, razao: RAZAO } : { pausa: false })
    return { value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  return visto
}

const TERRAFORM = { tool: 'Bash', input: { command: 'terraform apply -auto-approve' } }

test('o que um revert não desfaz vira pergunta a uma pessoa, mesmo com o modo deixando', async ($, on) => {
  const visto = motor(on, { decisao: 'allow' })
  const r = await $.tool.check(TERRAFORM)
  expect(r.decision).toBe('ask')
  expect(r.reason).toBe(RAZAO)
  // Quem decide é o guardrail.py faixa3, com o payload dos hooks.
  const [c] = visto.classificados
  expect(c?.argv[0]).toBe('python3')
  expect(c?.argv[1]?.endsWith('/scripts/guardrail.py')).toBe(true)
  expect(c?.argv[2]).toBe('faixa3')
  expect(c?.payload).toEqual({ cwd: '/projeto', tool_name: 'Bash', tool_input: TERRAFORM.input })
  expect(c?.sessao).toBe('sessao-1')
})

test('a pergunta do modo também vira a da pausa, com o cartão dela', async ($, on) => {
  motor(on, { decisao: 'ask' })
  const r = await $.tool.check(TERRAFORM)
  expect(r.decision).toBe('ask')
  expect(r.reason).toBe(RAZAO)
})

test('a recusa de baixo continua recusa, sem nem perguntar ao guardrail', async ($, on) => {
  const visto = motor(on, { decisao: 'deny' })
  const r = await $.tool.check(TERRAFORM)
  expect(r.decision).toBe('deny')
  expect(r.reason).toBe('decisão do modo')
  expect(visto.classificados.length).toBe(0)
})

test('o que não para fica com a decisão do modo', async ($, on) => {
  motor(on, { decisao: 'allow' })
  const r = await $.tool.check({ tool: 'Bash', input: { command: 'npm test' } })
  expect(r.decision).toBe('allow')
  expect(r.reason).toBe('decisão do modo')
})

test('ferramenta de MCP passa pelo guardrail; as de arquivo nem chegam', async ($, on) => {
  const visto = motor(on, { decisao: 'allow' })
  const merge = await $.tool.check({ tool: 'mcp__github__merge_pull_request', input: { pullNumber: 51 } })
  expect(merge.decision).toBe('ask')
  expect(visto.classificados[0]?.payload.tool_name).toBe('mcp__github__merge_pull_request')
  const escrita = await $.tool.check({ tool: 'Write', input: { file_path: '/projeto/deploy.sh', content: 'x' } })
  expect(escrita.decision).toBe('allow')
  expect(visto.classificados.length).toBe(1)
})

test('sem python3 ou com saída ilegível, vale a decisão do modo: o mod nunca afrouxa nem trava', async ($, on) => {
  const m: Motor = { decisao: 'allow', semPython: true }
  motor(on, m)
  expect((await $.tool.check(TERRAFORM)).decision).toBe('allow')
  m.semPython = false
  m.saidaIlegivel = true
  expect((await $.tool.check(TERRAFORM)).decision).toBe('allow')
  m.decisao = 'deny'
  expect((await $.tool.check(TERRAFORM)).decision).toBe('deny')
})

test('sem ninguém para perguntar, a chamada é recusada com o cartão e não roda', async ($, on) => {
  const visto = motor(on, { decisao: 'allow' })
  const r = await $.tool.call({ tool: 'Bash', command: 'terraform apply -auto-approve' })
  expect(r.isError).toBe(true)
  expect(visto.executados).toEqual([])
  // O que não para roda como sempre.
  await $.tool.call({ tool: 'Bash', command: 'npm test' })
  expect(visto.executados).toEqual(['npm test'])
})

test('o que a ferramenta declara só leitura nem chega ao guardrail', async ($, on) => {
  const visto = motor(on, { decisao: 'allow' })
  const r = await $.tool.check({ ...TERRAFORM, isReadOnly: true })
  expect(r.decision).toBe('allow')
  expect(visto.classificados.length).toBe(0)
})

test('pausa sem cartão ainda pergunta; o que não é pausa, não', async ($, on) => {
  const m: Motor = { decisao: 'allow', saida: { pausa: true } }
  motor(on, m)
  const sem = await $.tool.check(TERRAFORM)
  expect(sem.decision).toBe('ask')
  expect(sem.reason).toContain('pausa da faixa 3')
  for (const saida of [{ pausa: 'sim', razao: 'x' }, { razao: RAZAO }, null]) {
    m.saida = saida
    expect((await $.tool.check(TERRAFORM)).decision).toBe('allow')
  }
})
