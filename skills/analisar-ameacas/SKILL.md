---
name: analisar-ameacas
description: Produz um modelo de ameaças (threat model) para uma feature ou área do sistema. Use ANTES de implementar features sensíveis — auth, PII, multi-tenant, upload, integrações externas, IA, billing, RBAC. Coordenada por Helena. Identifica ativos, trust boundaries, capacidades realistas do atacante, abuse paths e mitigações por componente. Read-only: produz docs/seguranca/AMEACAS-<feature>-YYYY-MM-DD.md.
---

# Analisar ameaças — modelo de ameaças

Você está sendo invocado para mapear como um atacante real **provavelmente** atacaria esta parte do sistema, e que mitigações fazem sentido **antes** de a feature existir.

## Regra de ouro

Você não está corrigindo vulnerabilidades nesta skill. Você está antecipando. O artefato é um documento que vai para a SPEC ou para `decisoes/`. Mitigação concreta vira tarefa em `/kairos-forge:mobilizar` ou ressalva em `/kairos-forge:revisar` depois.

Não invente cenário improvável. Atacante real custa dinheiro e tempo, e ataca o que dá retorno.

## Quando usar

- Antes de implementar: login, registro, recuperação de senha, MFA, SSO, OAuth.
- Antes de qualquer feature que toca PII, dados financeiros, saúde, dados de menores.
- Antes de adicionar upload de arquivo, geração de assinaturas, exportação de dados.
- Antes de adicionar tenant novo em sistema multi-tenant.
- Antes de expor endpoint público novo.
- Antes de integrar IA com input de usuário ou de terceiros.
- Quando a SPEC marcar como "complexo" e tocar segurança/autorização.

Se a feature for trivial (mudança de cor, label), **não use**. Threat model em tudo vira ruído.

## Fluxo

### 1. Helena entra como líder

Invoque `helena-security`. Pergunte ao usuário:

- Qual feature ou área quer modelar? (link para SPEC se já existe)
- Quem são os usuários esperados? (autenticados? público? admin?)
- Há dados sensíveis envolvidos? Quais?
- Já houve incidente parecido neste projeto? (consultar `decisoes/log.md` e `decisoes/estado-operacional.md`)

Helena pode chamar:

- **Carlos** se tiver query, RLS, índice ou banco envolvido.
- **Marcos** se for sobre infraestrutura, secrets, deploy, network.
- **Thiago** se for integração externa.
- **Gabriel** se houver IA com input externo.
- **Renata** para sinais de monitoramento e detecção.

### 2. Listar ativos

Ativo é o que o atacante quer ou o que o usuário perde se for atacado. Não confunda ativo com componente.

| Ativo | Por que importa | Quem tem acesso hoje |
|---|---|---|

Exemplos: token de sessão, lista de e-mails de clientes, chave da API de pagamento, capacidade de enviar e-mail em nome da empresa, capacidade de aprovar transação.

### 3. Mapear trust boundaries

Trust boundary é onde um nível de confiança muda. Exemplos comuns:

- Browser ↔ backend
- Backend ↔ banco
- Backend ↔ serviço externo
- Tenant A ↔ tenant B
- Usuário comum ↔ admin
- Worker ↔ fila de jobs

Para cada boundary relevante: o que cruza? em que formato? com que validação?

### 4. Levantar entrypoints

Para cada ponto onde algo entra no sistema:

| Entrypoint | Quem chama | Auth requerida | Rate limit | Validação |
|---|---|---|---|---|

Cubra rotas HTTP, endpoints internos, jobs assíncronos, webhooks, uploads, importações.

### 5. Definir atacante realista

Não modele NSA. Modele:

| Perfil | Motivação | Capacidade típica |
|---|---|---|
| Usuário comum curioso | Ver dados de outro | Devtools, replay de request |
| Atacante oportunista | Monetizar via spam/credential stuffing | Ferramentas de massa, lista de senhas vazadas |
| Atacante motivado | Roubo direcionado, fraude | Scripts customizados, social engineering, tempo |
| Insider | Acessar/exfiltrar com login válido | Tudo que o login dele permite |
| Terceiro comprometido | Já tem acesso à integração X | Tudo que a integração X permite |

Escolha 2-3 perfis relevantes para esta feature. Se for billing, atacante motivado entra. Se for blog público, usuário curioso e oportunista bastam.

### 6. Construir abuse paths

Para cada perfil escolhido, escreva um caminho concreto. Exemplo:

**Perfil:** usuário comum curioso
**Objetivo:** ver fatura de outro usuário
**Caminho:**
1. Abre devtools, vê URL `GET /invoices/123`.
2. Tenta `GET /invoices/124`.
3. Backend retorna fatura sem checar `userId == invoice.userId`.
4. Atacante itera IDs.

Por path, registrar:

- Quais ativos caem
- Que controle existente (se houver) impede
- Que controle **deveria** existir

### 7. Mitigação por componente

Para cada abuse path com controle insuficiente, propor mitigação na **camada mais barata e mais perto da origem**:

| Camada | Exemplos de mitigação |
|---|---|
| UI | Esconder caminho não-autorizado (não é proteção, é UX) |
| Borda (proxy/WAF) | Rate limit, bloqueio por IP, normalização |
| Aplicação | AuthZ check, validação de input, escape de output, idempotência |
| Banco | RLS, constraint, índice de unicidade, audit log |
| Infra | Secret manager, network policy, IAM mínimo |
| Observabilidade | Alerta de tentativa, log estruturado, fingerprint |

UI nunca é mitigação real. Borda é defesa em profundidade. Aplicação e banco são onde a decisão vive.

### 8. Salvar artefato

Em `docs/seguranca/AMEACAS-<feature-slug>-YYYY-MM-DD.md`:

```markdown
# Modelo de ameaças — <feature> — YYYY-MM-DD

**Coordenado por:** Helena (com <outros se houver>)
**SPEC relacionada:** <SPEC-NNN ou "não há ainda">
**Escopo:** 1-2 frases.

## Resumo executivo

- Ameaça principal em 1 frase
- 3 mitigações com maior alavancagem
- Custo de não mitigar

## Ativos

| Ativo | Por que importa | Acesso atual |
|---|---|---|

## Trust boundaries

| Boundary | O que cruza | Formato | Validação atual |
|---|---|---|---|

## Entrypoints

| Entrypoint | Caller esperado | Auth | Rate limit | Validação |
|---|---|---|---|---|

## Perfis de atacante considerados

| Perfil | Por que entra neste modelo |
|---|---|

## Abuse paths

### AP-01: <título>
**Perfil:** ...
**Objetivo:** ...
**Caminho:** passos numerados.
**Ativos atingidos:** ...
**Controle atual:** existente / parcial / inexistente.
**Mitigação proposta:** camada + ação concreta.
**Severidade:** baixa / média / alta / crítica.

(repetir AP-02, AP-03...)

## Mitigações priorizadas

| ID | Mitigação | Camada | Custo | Alavancagem | Cobre |
|---|---|---|---|---|---|

## Detecção e resposta

| Sinal | Onde monitorar | Quem responde |
|---|---|---|

## Decisões aceitas

Riscos aceitos explicitamente (com data e justificativa).

## Próximo passo

- Mitigações P1 viram tarefas em SPEC-NNN.
- Mitigações P2 vão como ressalvas em `/kairos-forge:revisar`.
- Reavaliar este modelo se: <gatilhos>.
```

### 9. Responder ao usuário

Resumo curto:

```markdown
Modelo de ameaças salvo em `docs/seguranca/AMEACAS-<slug>-YYYY-MM-DD.md`.

Coordenado por Helena (+ <outros se houver>).

Ameaça principal: <1 frase>.
Mitigações de maior alavancagem:
1. <mitigação>
2. <mitigação>
3. <mitigação>

Próximo passo: <atualizar SPEC-NNN | abrir SPEC | aceitar risco>.
```

## Regras

- **Não invente atacante.** Escolha perfis que fazem sentido para o ativo. NSA não entra em modelo de feature de blog público.
- **UI não é mitigação.** Esconder botão não impede chamada direta.
- **Sempre escolha a camada mais barata e mais próxima da origem.** AuthZ no banco (RLS) é melhor que AuthZ só na aplicação quando dá.
- **Risco aceito é decisão registrada.** Não some um risco — registre que foi aceito e por quê.
- **PT-BR.**
- **Read-only.** Nada de patch, nada de migration, nada de mudar config.
- **Se a feature tiver SPEC, este modelo referencia a SPEC e vira insumo para revisão.** Não duplique a SPEC.
