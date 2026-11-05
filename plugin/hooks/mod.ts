// Os mods da fábrica no Claude Code: o painel do arco (ADR-0051) e a pausa da faixa 3 na
// execução (ADR-0052). Um módulo por plugin, então os dois entram por aqui.
import type { Register } from 'claude-code'

import { registrarPainel } from './painel'
import { registrarPausa } from './pausa'

export const register: Register = on => {
  registrarPainel(on)
  registrarPausa(on)
}
