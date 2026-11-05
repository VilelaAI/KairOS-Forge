// Os mods da fábrica no Claude Code: o painel do arco (ADR-0051), a pausa da faixa 3 na
// execução (ADR-0052) e o segredo ocultado na saída de ferramenta (ADR-0056). Um módulo
// por plugin, então os três entram por aqui.
import type { Register } from 'claude-code'

import { registrarPainel } from './painel'
import { registrarPausa } from './pausa'
import { registrarSegredo } from './segredo'

export const register: Register = on => {
  registrarPainel(on)
  registrarPausa(on)
  registrarSegredo(on)
}
