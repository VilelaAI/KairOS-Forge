# ADR-0008 — Squad de segurança vertical + automação da verificação de segurança

**Status:** Aceito
**Data:** 2026-06-22
**Autor:** Allyson Vilela

## Contexto

Um ataque ao sistema **Defesa Civil Alerta** (plataforma Idap), em 20/06/2026, permitiu que um terceiro disparasse um **alerta público falso** para várias regiões — um único acesso indevido com consequência ampla em infraestrutura crítica. A reportagem conecta o caso ao que o **TCU denuncia desde 2024**: auditoria em 229 órgãos federais (Sisp) mostrou que **nenhum** implementava integralmente os **controles mínimos de cibersegurança** (só 14 acima de 70%, só 2 acima de 90%); cibersegurança virou tema de **Alto Risco**.

No kairos-forge, até a v0.7, a segurança era **rasa e manual**:

- Uma única agente core (**Helena [Security]**) cobria tudo (OWASP, RLS, secrets, input).
- A skill `analisar-ameacas` (threat model, Helena-led) e a entrada da Helena no `revisar`/`auditar`.
- O hook `PostToolUse` era **genérico** (avisava sobre arquivo de produção, sem lente de segurança).

Faltava **profundidade** (AppSec, ofensiva, cloud-sec, DevSecOps, detecção/resposta, GRC), **avaliação de controles mínimos** e **verificação automática**.

## Decisão

### 1. Squad vertical `seguranca` (6 agentes), coordenado pela Helena

Seguindo o tier de squads verticais do **ADR-0007** (sob demanda, prefixo `seguranca-<nome>-<papel>.md`). Helena (core) continua a porta de entrada e coordenadora — puxa o squad como Laura puxa devs.

| Agente | Papel | Bash | model |
|---|---|---|---|
| seguranca-icaro-appsec | AppSec (SAST/SCA, OWASP ASVS, secure code) | ✅ | — |
| seguranca-mauro-ofensiva | Ofensiva & Vuln Mgmt (pentest, DAST, CVE) | ✅ | opus |
| seguranca-nara-cloud | Cloud & Infra Security (CSPM, IAM, hardening) | ✅ | — |
| seguranca-ravi-devsecops | DevSecOps & Supply Chain (CI/CD, SBOM, SLSA) | ✅ | — |
| seguranca-cibele-deteccao | Detecção & Resposta (SIEM, hunting, MITRE ATT&CK) | ✅ | — |
| seguranca-bernardo-grc | GRC & Controles (NIST CSF, CIS v8, risco) | ❌ | opus |

### 2. Automação da verificação (3 mecanismos + reforço)

- **Nova skill `/kairos-forge:auditar-seguranca`** — postura/maturidade pontuada (5 funções NIST CSF × 20, mapeadas a CIS Controls v8), read-only, salva `docs/seguranca/POSTURA-SEG-*.md`, **rodável semanalmente/em CI**. Resposta direta ao achado "controles mínimos não implementados".
- **Auto-escalação no `/revisar`** — o squad entra automaticamente quando o diff toca área sensível (auth/cripto/IAM/upload/IaC/deps), não só a Helena.
- **Hook de segurança no `PostToolUse`** (Claude Code) — alerta imediato ao editar arquivo sensível (`.env`, auth, Dockerfile, `*.tf`, jwt/secret).
- **Reforço da dimensão Guardrails no `/auditar`** — passa a checar postura de segurança recente e a apontar `/auditar-seguranca`. **Sem 6ª dimensão** (preserva o contrato de 5 dimensões do ADR-0006).

## Fronteira vs kairos-ai (posicionamento MIT)

O forge fica **genérico**: OWASP, NIST CSF, CIS Controls, MITRE ATT&CK, SLSA, ISO 27001 conceitual. O **regulado brasileiro** — Lei Geral de Cibersegurança, ANPD/LGPD, GSI, exigência setorial — é **deferido ao kairos-ai** via rodapé em cada agente e nota explícita na skill `auditar-seguranca`. Em especial, **Bernardo [GRC] não é agente de LGPD/ANPD**: ele mede controles técnicos genéricos; conformidade legal é o squad negocial/DPO do kairos-ai.

## Colisões de nome

**Nenhuma nova.** Ícaro, Mauro, Nara, Ravi, Cibele, Bernardo não colidem com os 80 agentes anteriores. Fronteiras anti-sobreposição documentadas no corpo de cada agente: Cibele (detecção de segurança) ≠ Sílvio (incidente operacional/SRE) ≠ Renata (observabilidade de app); Nara (postura de segurança de nuvem) ≠ Wagner (plataforma/IaC); Helena (coordenação + veredito pré-PR) puxa o squad para profundidade.

## Consequências

### Positivas
- Segurança deixa de ser uma pessoa só e ganha profundidade equivalente a um time real.
- Controles mínimos viram algo **medível e recorrente** (skill pontuada), endereçando o gap que o TCU aponta.
- Verificação passa a ser **automática** (hook + escalação no revisar + audit recorrente), não dependente de lembrança.

### Negativas
- +6 agentes e +1 skill aumentam a superfície (sync, espelhamento `plugin/`, contagens). Forge vai a **86 agentes / 11 skills**, bump **0.8.0**.
- Risco de sobreposição percebida com Helena/SRE/observabilidade — mitigado pelas fronteiras documentadas.

## Revisão futura

- Se o usuário precisar de conformidade regulada de fato (LGPD/ANPD, Lei de Cibersegurança), isso vira trabalho no **kairos-ai**, não aqui.
- Se a auditoria de segurança virar pesada demais para o `/auditar` referenciar, pode-se promover Segurança a dimensão própria (revisando o contrato do ADR-0006).
