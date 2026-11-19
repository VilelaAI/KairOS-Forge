# Modelo da pesquisa

Salve em `docs/pesquisa/<assunto>.md`. O `prova.py fontes` lê a data, a resposta e as seções
pelo nome, então mantenha os títulos e a ordem das colunas da tabela de fatos. Os campos
**Para** e **Versão no projeto** são para quem lê: o verificador não os confere.

```markdown
# <a pergunta, em uma frase>

- **Data da pesquisa:** AAAA-MM-DD
- **Para:** <SPEC-NNN, ADR-NNNN, issue ou conversa>
- **Versão no projeto:** <a versão lida no lockfile ou no manifesto>

**Resposta:** <a resposta curta à pergunta do título, ou "não encontrada">

## Fatos

| # | Fato | Fonte | Versão | Data da fonte |
|---|---|---|---|---|
| 1 | <o fato, com as suas palavras> | [<título>](https://…) | <v4.2.0 ou sem versão> | <AAAA-MM-DD ou AAAA-MM> |
| 2 | <o fato> | `<caminho/do/repositório>:<linha>` | sem versão | <AAAA-MM-DD> |

## Inferências

- <o que se deduz, citando os fatos: "pelos fatos 1 e 2, …">

## Em aberto

- <a dúvida que sobrou e os lugares já consultados>
```

## Como o `prova.py fontes` lê

| Parte | Regra |
|---|---|
| título | um título `# ` |
| **Data da pesquisa** | AAAA-MM-DD, nunca no futuro |
| **Resposta** | preenchida; "não encontrada" exige `## Em aberto` preenchida |
| `## Fatos` | ao menos uma linha, menos quando a resposta é "não encontrada" |
| cada fato | o fato; a fonte (um link `http(s)://` ou um caminho do repositório que exista, com `:linha` ou não); a versão (`sem versão` quando a fonte não tem); a data da fonte em AAAA-MM-DD ou AAAA-MM |
| o arquivo inteiro | sem segredo (a regra do `segredos.py`); se houver, `guardrail.py ocultar <arquivo>` troca o valor pela marca |
| a idade | mais de 180 dias vira aviso, não erro (`--idade-max` muda) |

E em todo `.md` do repositório, cada citação a `docs/pesquisa/` aponta para um arquivo que
existe. O `README.md` da pasta, se houver, não é conferido como pesquisa.

## O que o verificador não sabe

Se a fonte é mesmo primária, se o fato está certo e se o link ainda responde: ele não acessa a
rede. Isso fica com quem revisa, e vale a regra do `/avaliar`: nunca recompense a forma.
