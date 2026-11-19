# O hook UserPromptSubmit do Claude Code acha as skills usadas na sessão, e quanto texto ele pode devolver?

- **Data da pesquisa:** 2026-11-19
- **Para:** ADR-0060, o `guardrail.py conferir` com o `## Pronto quando` das skills usadas
- **Versão no projeto:** Claude Code 2.1.328 na prova; o CI da fábrica fixa a 2.1.318

**Resposta:** Sim. Todo evento de hook recebe o `transcript_path`, e os turnos anteriores estão
no arquivo quando a pessoa manda o prompt seguinte. A skill chamada pelo modelo aparece como
`tool_use` da tool `Skill`, e a digitada como `<command-name>`. O `additionalContext` aceita até
10.000 caracteres.

## Fatos

| # | Fato | Fonte | Versão | Data da fonte |
|---|---|---|---|---|
| 1 | Todo evento de hook recebe, além dos campos próprios, `session_id`, `transcript_path`, `cwd` e outros campos comuns. | [Hooks reference, Common input fields](https://code.claude.com/docs/en/hooks#common-input-fields) | sem versão | 2026-11 |
| 2 | O transcript é gravado de forma assíncrona e pode não ter ainda as mensagens mais recentes do turno corrente quando o hook roda. | [Hooks reference, Common input fields](https://code.claude.com/docs/en/hooks#common-input-fields) | sem versão | 2026-11 |
| 3 | O `UserPromptSubmit` recebe o `prompt` além dos campos comuns, e devolve contexto para o modelo em `hookSpecificOutput.additionalContext`. | [Hooks reference, UserPromptSubmit](https://code.claude.com/docs/en/hooks#userpromptsubmit) | sem versão | 2026-11 |
| 4 | O `UserPromptSubmit` tem tempo limite padrão de 30 segundos; ao estourar, o `additionalContext` é descartado e o prompt segue sem ele. | [Hooks reference, UserPromptSubmit](https://code.claude.com/docs/en/hooks#userpromptsubmit) | sem versão | 2026-11 |
| 5 | O `additionalContext` de cada hook tem teto de 10.000 caracteres, medido campo a campo. | [Hooks reference, saída JSON](https://code.claude.com/docs/en/hooks#json-output) | sem versão | 2026-11 |
| 6 | A skill chamada pelo modelo fica no transcript como `tool_use` de nome `Skill` com `input.skill` igual a `kairos-forge:<nome>`; a digitada pela pessoa, como `<command-name>/kairos-forge:<nome></command-name>` na mensagem dela. | `docs/pesquisa/anexos/claude-code-2.1.328-skill-no-transcript.jsonl` (as duas linhas, só com `type`, `version` e `message`, do transcript de uma sessão com o plugin e uma API falsa) | Claude Code 2.1.328 | 2026-11-19 |

## Inferências

- Pelos fatos 1 e 2, as skills de turnos anteriores estão no transcript quando a pessoa pergunta
  "faltou algo?"; só uma skill chamada no mesmo prompt da pergunta poderia não estar, e ela ainda
  não teria trabalho a conferir.
- Pelos fatos 4 e 5, ler o transcript linha a linha cabe nos 30 segundos, e a conferência fica
  abaixo dos 10.000 caracteres se a lista do `## Pronto quando` couber no que sobra: entram blocos
  inteiros, da skill usada por último para a primeira, e a que não cabe vira uma linha que aponta
  o `SKILL.md` dela.
- Pelo fato 6, o leitor precisa das duas formas, e só aceita o nome que existe em `skills/`.

## Em aberto

- O formato do `tool_use` da `Skill` (fato 6) não está na referência de hooks: foi observado no
  2.1.328, e o `test_pronto.py` lê o anexo para notar se o leitor deixar de reconhecê-lo. Uma
  mudança nele faz a lista sumir da conferência, sem quebrar o resto.
- Codex, OpenCode e Cursor não têm o mesmo hook com transcript; lá a conferência não traz a lista.
