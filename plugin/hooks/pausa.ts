// Pausa da faixa 3 na execução (ADR-0052): no arco do /entregar, a chamada cujo efeito
// um revert não desfaz para por uma pessoa — `terraform apply`, `npm publish`, migration
// em banco remoto, merge pelo MCP —, mesmo em modo automático ou com uma regra salva.
//
// Por que é um mod: o `ask` que um mod dá em `tool.check` é de uma pessoa. Nenhum
// classificador o aprova, a regra salva para a ferramenta inteira não o dispensa, e onde
// ninguém pode ser perguntado (o `-p`, um host sem pessoa) ele vira recusa com o motivo.
// O `ask` de um hook de settings vai para quem decide no modo, e no modo automático esse
// alguém pode ser o classificador.
//
// Só aperta, nunca afrouxa: a recusa de baixo continua recusa, e o mod nunca devolve
// `allow`. A regra (o que é irreversível, e se o arco está ligado) é do `guardrail.py
// faixa3`, que também grava a pausa na trajetória. Se ele não roda, vale a decisão de
// sempre, sem pausa: sem Python não há guardrail nenhum da fábrica.

import type { EngineInterface, On } from 'claude-code'

type Veredito = { pausa: false } | { pausa: true; razao: string }

async function classificar($: EngineInterface, tool: string, input: unknown): Promise<Veredito> {
  const r = await $.process.run(['python3', `${$.plugin.root}/scripts/guardrail.py`, 'faixa3'], {
    stdin: JSON.stringify({ cwd: await $.session.cwd(), tool_name: tool, tool_input: input ?? {} }),
    timeoutMs: 10_000,
    // A sessão vai junto para a pausa gravada na trajetória ficar na sessão certa.
    env: { PYTHONDONTWRITEBYTECODE: '1', CLAUDE_SESSION_ID: await $.session.id() },
  })
  const v: unknown = JSON.parse(r.stdout)
  if (v !== null && typeof v === 'object' && 'pausa' in v && v.pausa === true && 'razao' in v) {
    return { pausa: true, razao: String(v.razao) }
  }
  return { pausa: false }
}

export function registrarPausa(on: On) {
  on('tool.check', { tool: /^(Bash|mcp__.+)$/ }, async ($, e, next) => {
    const abaixo = await next(e)
    if (abaixo.decision === 'deny' || e.isReadOnly) return abaixo
    const v = await classificar($, e.tool, e.input)
    return v.pausa ? { decision: 'ask', reason: v.razao } : abaixo
  }).catch(($, e, next) => next(e))
}
