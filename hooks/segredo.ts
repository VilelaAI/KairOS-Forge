// Segredo na saída de ferramenta (ADR-0056): o token que o `env` imprime, a senha que o
// teste vermelho mostra na `DATABASE_URL`, a chave que o `kubectl get secret` devolve.
// A leitura de segredo pelo shell e pela `Read` já é negada antes (ADR-0042); a saída
// passava. E o que entra no contexto vai à API na resposta seguinte e fica no transcript.
//
// Por que é um mod: o resultado que um gancho em `tool.call` devolve é o que o modelo lê
// e o transcript grava, no lugar do original. Um hook de settings no PostToolUse só
// acrescenta texto depois, com o segredo já lido.
//
// Só aperta: a chamada roda inteira, uma vez, e nenhum mod decide se ela roda. O que
// muda é o texto que volta, e só o valor que o `guardrail.py saida` reconhece como
// segredo, trocado por uma marca. A regra (os formatos de segredo) é dele, que também
// grava o achado na trajetória, sem o valor. Se ele não roda, a saída passa como veio:
// sem Python não há guardrail nenhum da fábrica.
//
// O Bash que respondeu volta com stdout e stderr trocados. Saída grande, que o Claude Code
// guarda inteira num arquivo, é examinada inteira e volta inteira, já sem o segredo e sem
// o caminho daquele arquivo: o Claude Code guarda de novo a versão oculta. O erro e a ferramenta de MCP, cujo resultado não
// tem uma forma que dê para reescrever, voltam como resultado retido: o modelo lê que a
// ferramenta rodou e o texto já sem o segredo.

import type { EngineInterface, On, ToolCallResult } from 'claude-code'

type Exame = { ocultar: boolean; textos: Record<string, string>; aviso: string }
type SaidaDoBash = { stdout?: unknown; stderr?: unknown; [campo: string]: unknown }
type Respondido = Exclude<ToolCallResult, { deny: string }>

async function examinar($: EngineInterface, tool: string, input: unknown,
                        textos: Record<string, string>): Promise<Exame | null> {
  const r = await $.process.run(['python3', `${$.plugin.root}/scripts/guardrail.py`, 'saida'], {
    stdin: JSON.stringify({ cwd: await $.session.cwd(), tool_name: tool, tool_input: input ?? {}, textos }),
    timeoutMs: 10_000,
    env: { PYTHONDONTWRITEBYTECODE: '1', CLAUDE_SESSION_ID: await $.session.id() },
  })
  const v = JSON.parse(r.stdout) as Partial<Exame> & { achados?: unknown } | null
  if (!v || !v.achados || typeof v.aviso !== 'string' || typeof v.textos !== 'object' || !v.textos) return null
  return { ocultar: v.ocultar === true, textos: v.textos, aviso: v.aviso }
}

// O Bash que respondeu tem stdout e stderr; o resto (erro, MCP) tem só o texto que o
// modelo leria.
function respondeuComoBash(tool: string, r: Respondido): r is Respondido & { result: SaidaDoBash } {
  return tool === 'Bash' && !r.isError && typeof r.result === 'object' && r.result !== null
}

// Saída grande o Claude Code guarda inteira num arquivo e põe no `stdout` só o começo,
// com o caminho: o segredo do fim só aparece lendo o arquivo.
async function saidaInteira($: EngineInterface, r: { result: SaidaDoBash }): Promise<string> {
  const guardada = r.result.persistedOutputPath
  return typeof guardada === 'string' ? await $.fs.read(guardada) : String(r.result.stdout ?? '')
}

async function textosDe($: EngineInterface, tool: string, r: Respondido): Promise<Record<string, string> | null> {
  if (respondeuComoBash(tool, r)) {
    return { stdout: await saidaInteira($, r), stderr: String(r.result.stderr ?? '') }
  }
  return typeof r.text === 'string' && r.text ? { texto: r.text } : null
}

function reescrever(tool: string, r: Respondido, exame: Exame): ToolCallResult {
  const context = [...(r.context ?? []), exame.aviso]
  if (!exame.ocultar) return { ...r, context }
  if (respondeuComoBash(tool, r)) {
    // Objeto novo, sem `ref` e sem `text`: com eles, o Claude Code reaproveitaria as
    // mensagens que já montou, com o segredo dentro.
    const { persistedOutputPath: _guardada, rawOutputPath: _bruta, ...resto } = r.result
    return { result: { ...resto, stdout: exame.textos.stdout ?? '', stderr: exame.textos.stderr ?? '' }, context }
  }
  return { deny: `${exame.textos.texto ?? ''}\n\n${exame.aviso}` }
}

export function registrarSegredo(on: On) {
  on('tool.call', { tool: /^(Bash|mcp__.+)$/ }, async ($, e, next) => {
    const r = await next(e)
    if (r.deny !== undefined) return r                 // recusada: nada rodou, nada a ler
    try {
      const textos = await textosDe($, e.tool, r)
      if (!textos || !Object.values(textos).some(Boolean)) return r
      // Só o comando vai junto, para a trajetória dizer de onde veio o achado.
      const exame = await examinar($, e.tool, 'command' in e ? { command: e.command } : {}, textos)
      return exame ? reescrever(e.tool, r, exame) : r
    } catch {
      return r                // sem Python ou sem o arquivo da saída: ela passa como veio
    }
  }).catch(($, e, next) => next(e))
}
