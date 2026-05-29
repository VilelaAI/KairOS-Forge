# Contribuindo com o Embratur Skills

## Antes de abrir PR

1. **Leia uma skill existente** primeiro. As 19 skills deste repo são o estilo de referência — tom, tamanho, estrutura do frontmatter.
2. **Valide localmente** com a ferramenta-alvo (Lovable ou Replit). Skill que não dispara automaticamente não está pronta.
3. **PT-BR sempre.** Verifique acentuação (`solução`, não `solucao`).

## Estrutura mínima de uma skill nova

```
skills/<nome>/
└── SKILL.md
```

Material auxiliar pesado vai em `skills/<nome>/references/`.

### Naming híbrido

- **Skill temática** (ativa time de personas) → prefixo `squad-`. Ex.: `squad-backend`, `squad-qualidade`, `squad-arquitetura`.
- **Skill de processo** (ritual ou artefato textual) → substantivo descritivo. Ex.: `spec-rastreavel`, `modelo-de-ameacas`, `revisao-pre-pr`, `auditoria-do-setup`.
- **Evite verbo no infinitivo** (`especificar`, `validar`). Lovable e Replit descobrem skills pela `description`, e o `name` aparece em listas de catálogo — substantivo descreve melhor o que a skill É do que o que ela FAZ.

### Template de SKILL.md

```markdown
---
name: <nome>
description: Use when <gatilho concreto>. <O que produz>. <Quando NÃO usar>.
---

# <Nome legível> — <subtítulo curto>

## Quando usar

<lista de gatilhos, não definição genérica>

## Fluxo

### 1. <passo>

<instrução imperativa: "Faça X", não "Faz-se X">

### 2. <passo>

...

## Saída esperada

<arquivo, formato, evidência>

## Regras

- **Não <coisa que pode dar errado>.**
- **Sempre <invariante>.**
```

## Critérios pra entrar no catálogo

Toda skill nova precisa:

- [ ] Frontmatter com `name` e `description` começando com "Use when..."
- [ ] Descrição que diferencia: quando usar **e** quando NÃO usar
- [ ] Instruções imperativas (modo direto, não descritivo)
- [ ] ≤ 500 linhas (material pesado vai em `references/`)
- [ ] Caso de teste mínimo: 1 exemplo de gatilho que o agente pegou sozinho
- [ ] Funciona em pelo menos Lovable **ou** Replit (idealmente os dois)

## Quando NÃO adicionar skill

- A skill duplica algo que já existe. Prefira evoluir a skill existente.
- O comportamento é trivial e cabe em 1 prompt direto.
- A skill depende de ferramenta proprietária (Claude Code Teams, etc.) que não roda em Lovable/Replit.

## Personas

Este repo embute personas (Laura, Marina, Helena…) dentro das skills temáticas. Para adicionar persona nova:

1. Justifique por que as ~45 existentes não cobrem.
2. Adicione na skill temática mais próxima (não crie skill só pra persona).
3. Documente nome, papel, especialidade e quando acionar.

Colisões de nome (existem dois "Marcos", duas "Helenas", duas "Elisas") são intencionais — sempre desambigue com o sufixo do papel.

## Reportar bug ou propor mudança

Abra uma issue com:

- Skill envolvida
- Comportamento esperado vs observado
- Ferramenta usada (Lovable / Replit / outra)
- Trecho da conversa onde a skill falhou (se aplicável)
