// Mod do painel do arco (ADR-0051): o `/kairos-forge:entregar` visível ao lado da
// conversa, sem gastar turno do modelo.
//
// Três peças, todas de leitura:
//   - o painel (`/forge-painel`): SPECs, o trilho do arco com a fase marcada, as fichas
//     de cada gate, os veredictos e as mobilizações;
//   - a faixa acima do prompt: aparece só quando algo espera por uma pessoa (a caixa
//     de entrada do ADR-0044), com um toast quando um gate humano chega;
//   - `/forge-caixa`, a caixa de entrada como texto, na hora, mesmo com um turno rodando.
//
// O mod só aperta, nunca afrouxa: não aprova chamada de ferramenta, não reescreve
// nenhuma, não escreve em `.agents/` nem em lugar nenhum. Os ganchos em `tool.call`
// deixam a chamada passar inteira e só pedem uma leitura nova depois dela. Os números
// vêm do `scripts/painel.py`, como em qualquer CLI sem mod.

import { atom, read, update } from 'claude-code'
import type { Elements, EngineInterface, Register } from 'claude-code'

import type { Caixa, CicloDoPainel, Leitura, QuadroDoPainel, Relatorio, SpecDoPainel } from '../types'
import {
  ICONE_CAIXA,
  RELATORIOS,
  ativo,
  barra,
  ciclosSemSpec,
  conteudoDaFaixa,
  explicarFalha,
  gatesDaCaixa,
  iconeDoEstado,
  linhaDeStatus,
  linhasDoQuadro,
  painelVazio,
  pedeGithub,
  resumirCaixa,
  resumirPainel,
  textoDaFicha,
  trilho,
} from './vista'
import type { Faixa } from './vista'

const PANE = 'kairos-forge-arco'
const TITULO = 'Arco da fábrica'
const VAZIA: Leitura = { painel: null, caixa: null, falha: null }

// Mude a tag quando o formato mudar: ela recusa o que a versão anterior guardou, que
// sobrevive a um reload.
const leitura = atom({ plugin: 'kairos-forge', key: 'leitura' } as const, VAZIA, { shape: 'leitura-1' })
const faixaOculta = atom({ plugin: 'kairos-forge', key: 'faixaOculta' } as const, null)
const avisados = atom({ plugin: 'kairos-forge', key: 'avisados' } as const, [], { shape: 'avisados-1' })

// O que muda o arco: o ciclo.py e o quadro.py pelo shell, ou um arquivo de SPEC ou de
// estado escrito. Só essas chamadas pedem leitura nova; as outras nem chegam ao gancho.
const MUDA_O_ARCO_PELO_SHELL = /\b(ciclo|quadro)\.py\b/
const MUDA_O_ARCO_POR_ARQUIVO = /(^|[\\/])(docs[\\/]specs|\.agents[\\/](ciclo|quadro))[\\/]/

type $ = EngineInterface

async function rodar($: $, argumentos: string[]) {
  return $.process.run(['python3', `${$.plugin.root}/scripts/painel.py`, ...argumentos], {
    cwd: await $.session.root(),
    timeoutMs: 20_000,
    env: { PYTHONDONTWRITEBYTECODE: '1' },
  })
}

async function lerJson($: $, argumentos: string[]): Promise<unknown> {
  const r = await rodar($, argumentos)
  if (r.exitCode !== 0) {
    const motivo = (r.stderr || r.stdout).trim().split('\n').pop() ?? ''
    throw new Error(`painel.py ${argumentos.join(' ')} saiu com código ${r.exitCode}: ${motivo}`)
  }
  return JSON.parse(r.stdout)
}

async function ler($: $, anterior: Leitura): Promise<Leitura> {
  try {
    const [painel, caixa] = await Promise.all([
      lerJson($, ['--json']),
      lerJson($, ['--caixa', '--json']),
    ])
    return { painel: resumirPainel(painel), caixa: resumirCaixa(caixa), falha: null }
  } catch (erro) {
    // A última leitura boa continua na tela, com a falha em cima dela.
    return { ...anterior, falha: explicarFalha(erro) }
  }
}

async function avisar($: $, l: Leitura) {
  const gates = gatesDaCaixa(l.caixa)
  const antes = await read($, avisados)
  const novos = gates.filter(g => !antes.includes(g))
  const primeiro = l.caixa?.itens.find(i => i.tipo === 'gate' && novos.includes(`${i.onde}|${i.o_que}`))
  if (primeiro) {
    const mais = novos.length > 1 ? ` (+${novos.length - 1})` : ''
    $.ui.toast(`🚦 ${primeiro.onde} espera você: ${primeiro.o_que}${mais}`, { timeoutMs: 8000 })
  }
  if (novos.length || antes.length !== gates.length) await update($, avisados, () => gates)
}

// Uma leitura por vez; um pedido que chega durante uma leitura faz mais uma depois dela.
let emVoo: Promise<void> | null = null
let deNovo = false // reescrito no começo de cada volta do laço

function atualizar($: $): Promise<void> {
  if (emVoo) {
    deNovo = true
    return emVoo
  }
  emVoo = (async () => {
    try {
      do {
        deNovo = false
        const nova = await ler($, await read($, leitura))
        await update($, leitura, () => nova)
        $.ui.status(nova.falha ? undefined : linhaDeStatus(nova.painel, nova.caixa))
        if (!nova.falha) await avisar($, nova)
      } while (deNovo)
    } catch (erro) {
      $.ui.log(`kairos-forge: ${explicarFalha(erro)}`, { to: 'debug' })
    }
  })().finally(() => {
    emVoo = null
  })
  return emVoo
}

function abrirPainel($: $) {
  void atualizar($)
  return $.ui.open({ id: PANE, title: TITULO })
}

async function texto($: $, argumentos: string[]): Promise<string> {
  try {
    const r = await rodar($, argumentos)
    return (r.exitCode === 0 ? r.stdout : r.stderr || r.stdout).trimEnd()
  } catch (erro) {
    return `kairos-forge: ${explicarFalha(erro)}`
  }
}

// --- desenho -------------------------------------------------------------------------
// Funções de desenho fora do `register`: cada uma recebe a tabela de elementos da
// superfície e os dados, e devolve a árvore. O mesmo código serve às quatro superfícies.

type Tabela = Pick<Elements['terminal'], 'Box' | 'Text' | 'Button'>
type Ciclo = CicloDoPainel

function blocoDoCiclo({ Box, Text }: Tabela, c: Ciclo) {
  return (
    <Box flexDirection="column">
      <Text>
        {trilho(c.fase).map(parada => (
          <Text bold={parada.marca === '●'} dimColor={parada.marca === '·'}>
            {parada.marca} {parada.rotulo}{'  '}
          </Text>
        ))}
      </Text>
      <Text>
        {iconeDoEstado(c.estado)} {c.estado}
        <Text dimColor> · {c.fichas.map(textoDaFicha).join(' · ')}</Text>
      </Text>
      {c.motivo ? <Text color="warning">⏸️ {c.motivo}</Text> : null}
    </Box>
  )
}

function linhaDoRelatorio({ Text }: Tabela, rotulo: string, r: Relatorio | undefined) {
  if (!r) return null
  if (r.erro) return <Text color="error">🛑 {rotulo}: contrato inválido [{r.erro}]</Text>
  return (
    <Text>
      {r.achados ? '❌' : '✅'} {rotulo}: {r.veredicto}
      <Text dimColor> ({r.achados} achado(s))</Text>
    </Text>
  )
}

function blocoDaSpec(t: Tabela, s: SpecDoPainel, c: Ciclo | undefined) {
  const { Box, Text } = t
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text>
        <Text bold>{s.id}</Text> {barra(s.progresso)} {s.progresso}%
        <Text dimColor> ({s.total} req)</Text>
      </Text>
      {c ? blocoDoCiclo(t, c) : null}
      <Text dimColor>
        A fazer {s.colunas.aFazer.length} · Em progresso {s.colunas.emProgresso.length} · Pronto{' '}
        {s.colunas.pronto.length}
      </Text>
      {s.semProva.length ? (
        <Text color="warning">⚠️ concluído sem `verificado:` → {s.semProva.join(', ')}</Text>
      ) : null}
      {RELATORIOS.map(([chave, rotulo]) => linhaDoRelatorio(t, rotulo, s.relatorios[chave]))}
    </Box>
  )
}

function blocoDoCicloSemSpec(t: Tabela, c: Ciclo) {
  const { Box, Text } = t
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text>
        <Text bold>{c.spec}</Text>
        <Text dimColor> (sem SPEC no disco)</Text>
      </Text>
      {blocoDoCiclo(t, c)}
    </Box>
  )
}

function blocoDoQuadro({ Box, Text }: Tabela, q: QuadroDoPainel) {
  return (
    <Box flexDirection="column">
      <Text>
        {q.encerrado ? '🏁' : '🔄'} {q.slug}
        {q.spec ? ` · ${q.spec}` : ''}{' '}
        <Text dimColor>
          {q.concluidas}/{q.total} · onda {q.onda} (teto {q.tetoOnda})
        </Text>
      </Text>
      {linhasDoQuadro(q).map(linha => (
        <Text dimColor>   {linha}</Text>
      ))}
      {q.lacunas.map(lacuna => (
        <Text color="warning">   ⚠️ lacuna: {lacuna}</Text>
      ))}
      {!q.encerrado && q.completo ? <Text>   🏁 completo — falta encerrar</Text> : null}
    </Box>
  )
}

function blocoDaCaixa({ Box, Text }: Tabela, caixa: Caixa) {
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text bold>
        {caixa.itens.length ? `📥 Caixa — ${caixa.itens.length} esperando você` : '📥 Nada esperando por você.'}
      </Text>
      {caixa.itens.map(i => (
        <Box flexDirection="column">
          <Text>
            {ICONE_CAIXA[i.tipo] ?? '·'} {i.onde} <Text dimColor>{i.o_que}</Text>
          </Text>
          <Text dimColor>   → {i.como}</Text>
        </Box>
      ))}
    </Box>
  )
}

function desenharPainel($: $, t: Tabela, l: Leitura) {
  const { Box, Button, Text } = t
  const p = l.painel
  const ciclos = p?.ciclos ?? []
  return (
    <Box flexDirection="column">
      {l.falha ? <Text color="error">⚠️ {l.falha}</Text> : null}
      {!p && !l.falha ? <Text dimColor>Lendo o painel…</Text> : null}
      {l.caixa ? blocoDaCaixa(t, l.caixa) : null}
      {p && painelVazio(p) ? (
        <Text dimColor>
          Nada para mostrar: sem SPEC em docs/specs/, sem ciclo em .agents/ciclo/ e sem quadro em
          .agents/quadro/. Comece com /kairos-forge:especificar ou /kairos-forge:entregar.
        </Text>
      ) : null}
      {(p?.specs ?? []).map(s => blocoDaSpec(t, s, ciclos.find(c => c.spec === s.id)))}
      {ciclosSemSpec(p).map(c => blocoDoCicloSemSpec(t, c))}
      {p?.quadros.length ? (
        <Box flexDirection="column" marginBottom={1}>
          <Text bold>Mobilizações</Text>
          {p.quadros.map(q => blocoDoQuadro(t, q))}
        </Box>
      ) : null}
      <Box flexDirection="row">
        <Text dimColor>{p ? `lido ${p.geradoEm.slice(11, 16)} UTC · ${ciclos.filter(ativo).length} ciclo(s) ativo(s) ` : ''}</Text>
        <Button key="forge-atualizar" label="Atualizar" onPress={() => atualizar($)} />
      </Box>
    </Box>
  )
}

function desenharFaixa($: $, { Box, Button, Text }: Tabela, f: Faixa) {
  return (
    <Box flexDirection="row">
      <Box flexShrink={1}>
        <Text wrap="truncate-end">
          📥 {f.icone} {f.onde}: {f.oQue}
          <Text dimColor>{f.mais}</Text>
        </Text>
      </Box>
      <Button key="forge-ver" label="Ver" variant="primary" onPress={() => abrirPainel($)} />
      <Button key="forge-ocultar" label="Ocultar" onPress={() => update($, faixaOculta, () => f.assinatura)} />
    </Box>
  )
}

// --- ganchos ---------------------------------------------------------------------------

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'forge-painel',
      description: 'kairos-forge: abre o painel do arco (SPECs, fase, fichas, veredictos) ao lado da conversa',
      immediate: true,
    })
    await $.command.register({
      name: 'forge-caixa',
      description: 'kairos-forge: o que espera por você (gates, escalados, bloqueios), sem turno do modelo',
      argumentHint: '[--github]',
      immediate: true,
    })
    void atualizar($)
    return next(e)
  })

  on('command.run', { command: 'forge-painel' }, async $ => {
    await atualizar($)
    const aberto = await $.ui.open({ id: PANE, title: TITULO })
    if (aberto.isPlaced) return { text: 'Painel do arco aberto ao lado da conversa.' }
    // Onde nenhuma superfície desenha o painel, o mesmo quadro sai como texto.
    return { text: await texto($, []) }
  })

  on('command.run', { command: 'forge-caixa' }, async ($, e) => {
    void atualizar($)
    return { text: await texto($, ['--caixa', ...pedeGithub(e.args)]) }
  })

  // Depois de cada turno e de cada chamada que mexe no arco, uma leitura nova. A
  // chamada passa inteira: o gancho não decide nada, nem quando falha.
  on('turn.complete', async ($, e, next) => {
    const fim = await next(e)
    void atualizar($)
    return fim
  })
  on('tool.call', { tool: 'Bash', command: MUDA_O_ARCO_PELO_SHELL }, async ($, e, next) => {
    const feito = await next(e)
    void atualizar($)
    return feito
  }).catch(($, e, next) => next(e))
  on('tool.call', { tool: ['Write', 'Edit'], file_path: MUDA_O_ARCO_POR_ARQUIVO }, async ($, e, next) => {
    const feito = await next(e)
    void atualizar($)
    return feito
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const faixa = conteudoDaFaixa(await read($, leitura), await read($, faixaOculta))
    return faixa ? desenharFaixa($, $.ui.resolve(e), faixa) : next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) =>
    desenharPainel($, $.ui.resolve(e), await read($, leitura)),
  )
}
