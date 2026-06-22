---
name: auditar-seguranca
description: Audita a postura de segurança do projeto e a maturidade dos controles. Use semanalmente, em CI, ou após incidente/mudança sensível. Pontua 0–100 nas 5 funções do NIST CSF — Identificar, Proteger, Detectar, Responder, Recuperar — mapeadas a controles mínimos (CIS Controls v8) e devolve as 3 lacunas de maior risco. Coordenada por Helena + Bernardo (GRC). Read-only: produz docs/seguranca/POSTURA-SEG-YYYY-MM-DD.md, não modifica código.
---

# Auditar segurança — postura e maturidade de controles

Você está sendo invocado para medir, com método, quão protegido este projeto realmente está — e quais **controles mínimos** faltam. É a resposta direta ao tipo de achado que o TCU repete desde 2024: "controles mínimos de cibersegurança não implementados integralmente".

## Posicionamento

Esta skill mede **controles técnicos genéricos** (NIST CSF, CIS Controls v8, OWASP, MITRE ATT&CK). Ela **não** mede conformidade regulatória brasileira (LGPD/ANPD, Lei Geral de Cibersegurança, GSI) — isso é território do [kairos-ai](https://github.com/VilelaAI/kairos-ai). Se o usuário pedir conformidade legal, registre como lacuna e recomende o kairos-ai.

## Como funciona

Audita as **5 funções do NIST CSF**. Cada uma vale 20 pontos. Total: 100.

| Função | O que mede |
|---|---|
| **Identificar** | Inventário de ativos/dados, mapa de superfície, registro de risco, threat models, donos |
| **Proteger** | AuthN/AuthZ, criptografia, gestão de segredos, IAM mínimo, hardening, validação de input, AppSec |
| **Detectar** | Logging de segurança, SIEM/alertas, threat hunting, varredura contínua (SAST/SCA/DAST), detecção de anomalia |
| **Responder** | Playbook de incidente de segurança, papéis, contenção, comunicação, gestão de vulnerabilidades |
| **Recuperar** | Backup testado, DR, rollback, lições de incidente viram controle |

Read-only: você só lê. Coordenada por **Helena** (segurança) e **Bernardo** (GRC/controles), que puxam **Ícaro** (AppSec), **Nara** (cloud), **Ravi** (DevSecOps), **Cibele** (detecção) e **Mauro** (ofensiva) por função.

## Fluxo

1. **Identificar o projeto.** Confirmar diretório raiz e stack com o usuário.
2. **Coletar evidências** (read-only) por função — comandos sugeridos abaixo.
3. **Pontuar 0–20 por função** seguindo a rubrica. Não inventar evidência: o que não dá pra verificar pontua 0 com "não verificado".
4. **Salvar resultado** em `docs/seguranca/POSTURA-SEG-YYYY-MM-DD.md`.
5. **Apresentar relatório** com top 3 lacunas ranqueadas por **risco** (exposição × impacto × facilidade de exploração).

## Rubrica detalhada (mapeada a CIS Controls v8)

### Identificar (20 pts) — CIS 1, 2, 3
| Critério | Pontos |
|---|---|
| Inventário de ativos/serviços expostos e de dados sensíveis (onde estão, quem acessa) | 5 |
| Pelo menos 1 threat model recente em `docs/seguranca/AMEACAS-*.md` para área sensível | 5 |
| Registro de risco com dono e tratamento (mitigar/aceitar/transferir) | 5 |
| Classificação de dados (público/interno/confidencial/pessoal) documentada | 5 |

### Proteger (20 pts) — CIS 3, 4, 5, 6, 16
| Critério | Pontos |
|---|---|
| AuthN/AuthZ robustos (sessão/JWT tratados, AuthZ no servidor, RLS quando multi-tenant) | 4 |
| Gestão de segredos: zero segredo no código/VCS/imagem; cofre + rotação | 4 |
| IAM de menor privilégio e recursos não públicos por padrão | 4 |
| Validação de input + escape de output (sem injection/XSS óbvios); deps sem CVE crítica conhecida | 4 |
| Criptografia em repouso e trânsito (TLS atual; hash de senha forte) | 4 |

### Detectar (20 pts) — CIS 8, 13, 17
| Critério | Pontos |
|---|---|
| Logging de segurança dos eventos que importam (auth, authz negada, ação admin, acesso a dado sensível), íntegro | 6 |
| SAST/SCA (e DAST quando aplicável) rodando no pipeline com gate | 6 |
| Alertas/SIEM ou detecção de anomalia com playbook acionável | 4 |
| Secret scanning no histórico/pré-commit | 4 |

### Responder (20 pts) — CIS 17, 7
| Critério | Pontos |
|---|---|
| Playbook de resposta a incidente de segurança (papéis, contenção, comunicação) documentado | 6 |
| Gestão de vulnerabilidades: processo de triagem por risco + prazo de correção | 6 |
| Caminho de rotação/revogação de credencial vazada definido | 4 |
| Canal/contato de segurança e severidades definidos | 4 |

### Recuperar (20 pts) — CIS 11
| Critério | Pontos |
|---|---|
| Backup com **restauração testada** (não só configurado) | 7 |
| Plano de DR com RTO/RPO definidos e exercitados | 7 |
| Lições de incidentes anteriores viraram controle (rastreável em `decisoes/` ou postmortem) | 6 |

## Coletar evidências (read-only, sugestões)

- Segredos no histórico: `git log -p | grep -iE 'api[_-]?key|secret|password|token' | head` (amostragem) ou rodar `gitleaks`/`trufflehog` se disponível.
- Deps vulneráveis: `npm audit`, `pip-audit`, `osv-scanner`, ou ler lockfile + checar CVEs.
- IaC/misconfig: `ls **/*.tf Dockerfile* docker-compose* .github/workflows/* 2>/dev/null`; procurar `0.0.0.0/0`, `privileged: true`, buckets públicos, `*:*` em IAM.
- Threat models / postura prévia: `ls docs/seguranca/AMEACAS-*.md docs/seguranca/POSTURA-SEG-*.md 2>/dev/null`.
- Logging/CI: procurar logs de auth e steps de SAST/SCA em `.github/workflows/`.
- **Não rode scanner ofensivo contra produção de terceiros.** Read-only no repositório; ferramentas só em ambiente autorizado (Mauro coordena).

## Formato do relatório

```markdown
# Postura de segurança — <projeto> — YYYY-MM-DD

**Pontuação total: NN/100**
**Coordenado por:** Helena + Bernardo (com <Ícaro/Nara/Ravi/Cibele/Mauro conforme>)

| Função NIST CSF | Pontos | % |
|---|---|---|
| Identificar | NN/20 | NN% |
| Proteger | NN/20 | NN% |
| Detectar | NN/20 | NN% |
| Responder | NN/20 | NN% |
| Recuperar | NN/20 | NN% |

## Controles mínimos ausentes (CIS Controls v8)
- [ ] <controle> — função <X> — dono sugerido <agente>

## Top 3 lacunas (ranqueadas por risco)

### 1. <título>
**Função:** <qual> · **Risco:** <alto/médio/baixo — exposição × impacto>
**Por que primeiro:** <1 frase> · **Como fechar:** <1-3 bullets, com agente sugerido>

### 2. ... ### 3. ...

## Histórico
| Data | Total | ID | PR | DE | RS | RC |
|---|---|---|---|---|---|---|
```

## Como ranquear lacunas por risco

Não é pela função mais baixa. É por:
1. **Exposição** — está acessível à internet / a um atacante realista?
2. **Impacto** — o que cai se for explorado (dado, integridade, disponibilidade de serviço crítico)?
3. **Facilidade** — quão barato é explorar? (CVE pública + endpoint exposto = topo da lista.)

Lembre do caso que originou esta skill: um **único acesso indevido** a um sistema crítico gerou um alerta público falso. Priorize o que evita o "um acesso → consequência ampla".

## Quando usar

- **Semanalmente** (junto ou após `/kairos-forge:auditar`) e **em CI** como verificação recorrente.
- **Após incidente** ou mudança sensível (nova auth, novo endpoint público, nova integração).
- Antes de ir a produção com sistema que vira **infraestrutura crítica**.

## Regras

- **Read-only.** Não modifique código nem configs. Correção concreta vira tarefa pro squad (`/kairos-forge:rodar seguranca` ou `/kairos-forge:revisar`).
- **Não invente evidência.** Não verificou? Pontue 0 e diga "não verificado".
- **Não suavize.** Primeira auditoria de segurança costuma dar baixo — como nos 229 órgãos do TCU. Isso é o ponto.
- **Salve o relatório.** É como se mede a tendência da postura ao longo do tempo.
- **PT-BR.**
